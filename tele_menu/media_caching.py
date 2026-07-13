import atexit
import base64
import hashlib
import json
import os
import threading
import time
from io import BytesIO
from typing import Any, Dict, Optional, Union

from .scenes import BaseManager, OpenMedia
from .memory_storage import MemoryMedia

class FileIdCache:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, backup_path: Optional[str] = "file_id_cache.json", backup_interval: int = 3600):
        if self._initialized:
            return

        self._data: Dict[str, str] = {}
        self._data_lock = threading.Lock()
        self._dirty = False

        self._backup_path = backup_path
        self._backup_interval = backup_interval
        self._stop_backup = False
        self._backup_thread: Optional[threading.Thread] = None

        if self._backup_path:
            self._load_backup()
            self._start_backup_thread()
            # Best-effort dump on normal interpreter shutdown. Does NOT fire on
            # SIGKILL/hard crashes - that is fine, see class docstring.
            atexit.register(self.flush)

        self._initialized = True

    def get(self, media_type: str, cache_key: str) -> Optional[str]:
        row_key = f"{media_type}:{cache_key}"
        with self._data_lock:
            return self._data.get(row_key)

    def set(self, media_type: str, cache_key: str, file_id: str) -> None:
        row_key = f"{media_type}:{cache_key}"
        with self._data_lock:
            self._data[row_key] = file_id
            self._dirty = True

    def remove(self, media_type: str, cache_key: str) -> None:
        row_key = f"{media_type}:{cache_key}"
        with self._data_lock:
            if self._data.pop(row_key, None) is not None:
                self._dirty = True

    _INVALID_FILE_ID_MARKERS = (
        "wrong file identifier",
        "file identifier",
        "file is too big",
        "file_reference_expired",
    )

    @classmethod
    def is_invalid_file_id_error(cls, e: Exception) -> bool:
        text = str(e).lower()
        return any(marker in text for marker in cls._INVALID_FILE_ID_MARKERS)

    def _load_backup(self) -> None:
        try:
            with open(self._backup_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self._data = {}

    def _save_backup(self) -> None:
        with self._data_lock:
            if not self._dirty:
                return
            snapshot = dict(self._data)
            self._dirty = False

        try:
            tmp_path = f"{self._backup_path}.tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False)
            os.replace(tmp_path, self._backup_path)
        except OSError:
            pass

    def _start_backup_thread(self) -> None:
        def loop():
            while not self._stop_backup:
                time.sleep(self._backup_interval)
                self._save_backup()

        self._backup_thread = threading.Thread(target=loop, daemon=True)
        self._backup_thread.start()

    def flush(self) -> None:
        if self._backup_path:
            self._save_backup()

    def stop_backup_thread(self) -> None:
        self._stop_backup = True
        if self._backup_thread and self._backup_thread.is_alive():
            self._backup_thread.join(timeout=5)


class SourceManager(BaseManager):
    pass


class BaseSource:
    type: str = 'base'

    def read_bytes(self) -> bytes:
        """Read full content, used only when hashing is required for the cache key."""
        raise NotImplementedError

    def open_for_send(self):
        """Return whatever telebot's send_* method expects (a file-like object, bytes, etc.)."""
        raise NotImplementedError

    def close_sent(self, obj):
        if hasattr(obj, 'close'):
            try:
                obj.close()
            except Exception:
                pass

    def default_cache_mode(self) -> Optional[str]:
        """Which cache_mode MediaObject should use if the developer didn't specify one. None means "do not cache by default" (safe default for dynamic content)."""
        return 'hash'

    def stat_key(self) -> Optional[str]:
        """Cheap key without reading file content (used for cache_mode='mtime'). Return None if this source type has no notion of "last modified"."""
        return None

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseSource":
        raise NotImplementedError


@SourceManager.decorator_register(type='path')
class PathSource(BaseSource):
    """A file living on disk, referenced by path."""

    def __init__(self, path: str):
        self.path = path

    def read_bytes(self) -> bytes:
        with open(self.path, 'rb') as f:
            return f.read()

    def open_for_send(self):
        return open(self.path, 'rb')

    def default_cache_mode(self) -> Optional[str]:
        return 'mtime'

    def stat_key(self) -> Optional[str]:
        st = os.stat(self.path)
        return f"{st.st_mtime_ns}:{st.st_size}"

    def to_dict(self) -> Dict[str, Any]:
        return {'type': self.type, 'path': self.path}

    @classmethod
    def from_dict(cls, data):
        return cls(path=data['path'])


@SourceManager.decorator_register(type='open')
class OpenMediaSource(BaseSource):
    """Wraps tele_menu's own OpenMedia (lazy-reopened file handle)."""

    def __init__(self, open_media: OpenMedia):
        self.open_media = open_media

    def read_bytes(self) -> bytes:
        with self.open_media.create_open() as f:
            return f.read()

    def open_for_send(self):
        return self.open_media.create_open()

    def default_cache_mode(self) -> Optional[str]:
        return 'mtime'

    def stat_key(self) -> Optional[str]:
        try:
            st = os.stat(self.open_media.file)
            return f"{st.st_mtime_ns}:{st.st_size}"
        except OSError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {'type': self.type, 'data': self.open_media.to_dict()}

    @classmethod
    def from_dict(cls, data):
        return cls(open_media=OpenMedia.from_dict(data['data']))


@SourceManager.decorator_register(type='memory')
class MemoryMediaSource(BaseSource):
    """Wraps a MemoryMedia (dynamically generated, TTL-bound RAM content)."""

    def __init__(self, memory_media: MemoryMedia):
        self.memory_media = memory_media

    def read_bytes(self) -> bytes:
        data = self.memory_media.get_data(refresh_ttl=False)
        if data is None:
            raise Exception(f"MemoryMedia with id={self.memory_media.media_id} expired or not found")
        return data.read()

    def open_for_send(self):
        data = self.memory_media.get_data(refresh_ttl=True)
        if data is None:
            raise Exception(f"MemoryMedia with id={self.memory_media.media_id} expired or not found")
        return data

    def default_cache_mode(self) -> Optional[str]:
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {'type': self.type, 'data': self.memory_media.to_dict()}

    @classmethod
    def from_dict(cls, data):
        return cls(memory_media=MemoryMedia.from_dict(data['data']))


@SourceManager.decorator_register(type='bytes')
class BytesSource(BaseSource):
    """Raw in-memory bytes (e.g. produced once and reused), with no natural mtime."""

    def __init__(self, data: bytes, name: str = 'file'):
        self.data = data
        self.name = name

    def read_bytes(self) -> bytes:
        return self.data

    def open_for_send(self):
        bio = BytesIO(self.data)
        bio.name = self.name
        return bio

    def default_cache_mode(self) -> Optional[str]:
        return 'hash'

    def to_dict(self) -> Dict[str, Any]:
        return {'type': self.type, 'data': base64.b64encode(self.data).decode('utf-8'), 'name': self.name}

    @classmethod
    def from_dict(cls, data):
        return cls(data=base64.b64decode(data['data']), name=data.get('name', 'file'))


def wrap_source(raw) -> BaseSource:
    if isinstance(raw, BaseSource):
        return raw
    if isinstance(raw, str):
        return PathSource(raw)
    if isinstance(raw, OpenMedia):
        return OpenMediaSource(raw)
    if isinstance(raw, MemoryMedia):
        return MemoryMediaSource(raw)
    if isinstance(raw, bytes):
        return BytesSource(raw)
    if isinstance(raw, BytesIO):
        raw.seek(0)
        data = raw.read()
        raw.seek(0)
        return BytesSource(data, name=getattr(raw, 'name', 'file'))
    raise TypeError(f"Unsupported source for MediaObject: {type(raw)}")


class MediaObject:
    """
    Universal wrapper for anything that can be sent as media (path / OpenMedia /
    MemoryMedia / bytes / BytesIO), with transparent file_id caching handled
    entirely by the framework - the developer never touches file_id or FileIdCache.

    :param source: path string, OpenMedia, MemoryMedia, bytes, BytesIO, or a
                   ready-made BaseSource instance.
    :param cache_mode: 'hash'  - cache key is sha256 of file content (always correct,
                                 but requires reading the whole file into RAM once).
                       'mtime' - cache key is (mtime, size) of the underlying file,
                                 no content read needed on a cache hit at all
                                 (fast path for static assets on disk).
                       'key'   - developer-provided stable key, nothing computed.
                                 Requires key=... to be set.
                       None    - caching disabled for this object.
                       'auto' (default) - use the source's own recommended default
                                 (mtime for files/OpenMedia, hash for raw bytes,
                                 disabled for MemoryMedia).
    :param key: required only when cache_mode='key'.

    Example:
        PhotoMessage(content=MediaObject("assets/sword_icon.png"))
        PhotoMessage(content=MediaObject(chart_memory_media))               # not cached
        PhotoMessage(content=MediaObject(chart_memory_media,
                                          cache_mode='key', key='sword_lvl3'))  # cached explicitly
    """

    def __init__(self, source: Union[str, BaseSource, Any],
                 cache_mode: Optional[str] = "auto", key: Optional[str] = None):
        self.source: BaseSource = wrap_source(source)
        self.cache_mode = self.source.default_cache_mode() if cache_mode == "auto" else cache_mode
        self.explicit_key = key
        self.media_type: Optional[str] = None  # filled in by MediaMessage.send()/replace()
        self._hash_cache: Optional[str] = None

        if self.cache_mode == 'key' and not key:
            raise ValueError("MediaObject(cache_mode='key', ...) requires key=... to be set")

    @property
    def cache_enabled(self) -> bool:
        return self.cache_mode is not None

    def get_cache_key(self) -> Optional[str]:
        if self.cache_mode is None:
            return None
        if self.cache_mode == 'key':
            return f"key:{self.explicit_key}"
        if self.cache_mode == 'mtime':
            stat_key = self.source.stat_key()
            if stat_key is not None:
                return f"mtime:{stat_key}"
        if self._hash_cache is None:
            self._hash_cache = hashlib.sha256(self.source.read_bytes()).hexdigest()
        return f"hash:{self._hash_cache}"

    def open_for_send(self):
        return self.source.open_for_send()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'media_object',
            'source': self.source.to_dict(),
            'cache_mode': self.cache_mode,
            'key': self.explicit_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaObject":
        source = SourceManager.get(data['source']['type']).from_dict(data['source'])
        return cls(source=source, cache_mode=data.get('cache_mode', 'auto'), key=data.get('key'))