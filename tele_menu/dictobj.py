import sortedcontainers, time, threading

class DictObj:
    def __init__(self, cls, times=3600):
        self.cls = cls
        self.times = times
        self._events = sortedcontainers.SortedList()
        self._times_of_events = dict()
        self._dict = dict()
        self.stop_thread = False
        self._thread = threading.Thread(target=self._thread_loop, args=(), daemon=True)
        self._thread.start()

    def get_obj(self, ID):
        obj = self._dict.get(ID, None)
        if obj is None:
            obj = self.cls(ID)
            self._dict[ID] = obj
        self._obj_update(ID)
        return obj

    def find_objs(self, *args, **kwargs):
        IDs = self.cls.db_attribute_found_ids(**kwargs) if kwargs else args[0]
        for i in args:
            IDs &= i
        return [self.get_obj(ID) for ID in IDs]

    def _obj_update(self, ID:int):
        timing = int(time.time()) + self.times
        if ID in self._times_of_events:
            self._events.discard((self._times_of_events[ID], ID))
        self._events.add((timing, ID))
        self._times_of_events[ID] = timing

    def _remove_obj(self, ID:int):
        if ID in self._dict:
            del self._dict[ID]
        if ID in self._times_of_events:
            self._events.discard((self._times_of_events[ID], ID))
            del self._times_of_events[ID]

    def _thread_loop(self):
        while not self.stop_thread:
            if self._events:
                times = int(time.time())
                C = []
                for i in self._events:
                    if i[0] > times:
                        break
                    C.append(i)
                for i in C:
                    self._remove_obj(i[1])
            time.sleep(1)
