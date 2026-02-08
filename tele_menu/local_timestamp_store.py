from sortedcontainers import SortedList
from typing import List, Tuple, Optional, Union, Dict

class TimestampStore:
    def __init__(self, data: Optional[Union[List[Tuple[int, int]], Dict[int, int]]] = None, *, lib_path: Optional[str] = None):
        self._id_to_ts: Dict[int, int] = {}

        if data is not None:
            if isinstance(data, dict):
                pairs = list(data.items())
            else:
                pairs = list(data)

            for id_, ts in pairs:
                self._id_to_ts[id_] = ts

            self._sorted: SortedList = SortedList((ts, id_) for id_, ts in self._id_to_ts.items())
        else:
            self._sorted = SortedList()

    def add(self, id: int, timestamp: int) -> None:
        old_ts = self._id_to_ts.get(id)
        if old_ts is not None:
            if old_ts == timestamp:
                return
            self._sorted.remove((old_ts, id))
        self._id_to_ts[id] = timestamp
        self._sorted.add((timestamp, id))

    def remove(self, id: int) -> bool:
        if id not in self._id_to_ts:
            return False

        ts = self._id_to_ts.pop(id)
        self._sorted.remove((ts, id))
        return True

    def remove_timestamp(self, timestamp: int) -> List[int]:
        removed_ids: List[int] = []

        while self._sorted and self._sorted[0][0] < timestamp:
            ts, id_ = self._sorted.pop(0)
            del self._id_to_ts[id_]
            removed_ids.append(id_)

        return removed_ids

    def get_timestamp(self, id: int) -> Optional[int]:
        return self._id_to_ts.get(id)

    def get_min_timestamp(self) -> Optional[int]:
        if not self._sorted:
            return None
        return self._sorted[0][0]

    def __len__(self) -> int:
        return len(self._id_to_ts)

    def __bool__(self) -> bool:
        return bool(self._id_to_ts)

    def __contains__(self, id: int) -> bool:
        return id in self._id_to_ts