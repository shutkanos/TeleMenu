import time
import threading
from typing import Dict, Optional, Any
from io import BytesIO
import secrets

class MemoryMediaStorage:
    """
    Singleton storage for temporary media files in RAM.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._storage_lock = threading.Lock()
        self._cleanup_thread = None
        self._stop_cleanup = False
        self._start_cleanup_thread()
        self._initialized = True

    def _start_cleanup_thread(self):
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup = False
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()

    def _cleanup_loop(self):
        while not self._stop_cleanup:
            time.sleep(30)
            self.cleanup_expired()

    def cleanup_expired(self):
        current_time = time.time()
        with self._storage_lock:
            expired_keys = [
                media_id for media_id, data in self._storage.items()
                if data['expires_at'] <= current_time
            ]
            for media_id in expired_keys:
                del self._storage[media_id]

    def add(self, data: BytesIO, ttl_seconds: int = 300, name: str = 'file') -> str:
        """
        Add media to storage.

        Args:
            data: BytesIO object with media data
            ttl_seconds: Time to live in seconds (default 5 minutes)
            name: Optional filename for the media

        Returns:
            media_id: Unique identifier for stored media
        """
        media_id = secrets.token_urlsafe(16)
        expires_at = time.time() + ttl_seconds

        with self._storage_lock:
            self._storage[media_id] = {
                'data': data,
                'name': name,
                'created_at': time.time(),
                'expires_at': expires_at,
                'last_access': time.time(),
                'ttl_seconds': ttl_seconds
            }

        return media_id

    def get(self, media_id: str, refresh_ttl: bool = True) -> Optional[BytesIO]:
        """
        Get media from storage.

        Args:
            media_id: Unique identifier
            refresh_ttl: If True, refresh expiration time on access

        Returns:
            BytesIO object or None if not found/expired
        """
        current_time = time.time()

        with self._storage_lock:
            entry = self._storage.get(media_id)

            if entry is None:
                return None

            if entry['expires_at'] <= current_time:
                del self._storage[media_id]
                return None

            entry['last_access'] = current_time

            if refresh_ttl:
                entry['expires_at'] = current_time + entry['ttl_seconds']

            # Return a copy of BytesIO to avoid position issues
            data = entry['data']
            data.seek(0)
            copy = BytesIO(data.read())
            copy.name = entry['name']
            data.seek(0)
            return copy

    def get_info(self, media_id: str) -> Optional[Dict[str, Any]]:
        with self._storage_lock:
            entry = self._storage.get(media_id)
            if entry is None:
                return None

            return {
                'name': entry['name'],
                'created_at': entry['created_at'],
                'expires_at': entry['expires_at'],
                'last_access': entry['last_access'],
                'ttl_seconds': entry['ttl_seconds']
            }

    def remove(self, media_id: str) -> bool:
        """
        Manually remove media from storage.

        Returns:
            True if removed, False if not found
        """
        with self._storage_lock:
            if media_id in self._storage:
                del self._storage[media_id]
                return True
            return False

    def exists(self, media_id: str) -> bool:
        current_time = time.time()
        with self._storage_lock:
            entry = self._storage.get(media_id)
            if entry is None:
                return False
            return entry['expires_at'] > current_time

    def clear(self):
        with self._storage_lock:
            self._storage.clear()

    def stats(self) -> Dict[str, Any]:
        current_time = time.time()
        with self._storage_lock:
            total = len(self._storage)
            expired = sum(1 for entry in self._storage.values() if entry['expires_at'] <= current_time)
            return {
                'total_entries': total,
                'expired_entries': expired,
                'active_entries': total - expired
            }

    def stop_cleanup(self):
        self._stop_cleanup = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)


class MemoryMedia:
    """
    Reference to media stored in MemoryMediaStorage.
    """
    def __init__(self, media_id: str, name: str = 'file'):
        self.media_id = media_id
        self.name = name
        self._storage = MemoryMediaStorage()

    @classmethod
    def from_bytesio(cls, data: BytesIO, ttl_seconds: int = 300, name: str = 'file'):
        """
        Create MemoryMedia from BytesIO object.

        Args:
            data: BytesIO object with media data
            ttl_seconds: Time to live in seconds (default 5 minutes)
            name: Optional filename

        Returns:
            MemoryMedia instance
        """
        storage = MemoryMediaStorage()
        media_id = storage.add(data, ttl_seconds=ttl_seconds, name=name)
        return cls(media_id=media_id, name=name)

    def get_data(self, refresh_ttl: bool = True) -> Optional[BytesIO]:
        """
        Get the stored BytesIO object.

        Args:
            refresh_ttl: If True, refresh expiration time on access

        Returns:
            BytesIO object or None if expired/not found
        """
        return self._storage.get(self.media_id, refresh_ttl=refresh_ttl)

    def exists(self) -> bool:
        return self._storage.exists(self.media_id)

    def remove(self) -> bool:
        return self._storage.remove(self.media_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'memory',
            'media_id': self.media_id,
            'name': self.name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            media_id=data['media_id'],
            name=data.get('name', 'file')
        )
