import sys
import time
import datetime
import subprocess
from typing import Dict, Optional

from db_attribute import DbAttribute, DbAttributeMetaclass
from db_attribute.db_types import DbField, Id

from .data import Data
from .scenes import Scene, SceneManager

class BaseMeta:
    __skip_dbworkobj__ = True

class User(DbAttribute, metaclass=DbAttributeMetaclass):
    Meta = BaseMeta
    nameuser: str = DbField(default="")
    tgUsername: str = DbField(default="")
    registerData: datetime.date = DbField(default=datetime.date.today(), repr=False)
    # Administrated
    rank: str = DbField(default="User")
    ban: bool = DbField(default=False)
    unbanTime: int = DbField(default=0, repr=False)
    banInfo: dict = DbField(default_factory=lambda: {'which': -1, 'text': '', 'start': 0, 'end': 0}, repr=False)
    doDict: dict = DbField(default_factory=lambda: {'BanSelf': []}, repr=False)
    # Antispam
    numMessagesPerSec: int = DbField(default=100, repr=False)
    # scene module
    current_scene: Scene = DbField(default=Data.EmptyScene, repr=False)
    previous_scene: Scene = DbField(default=Data.EmptyScene, repr=False)
    # activeInputFunction: bool = DbField(default=False, repr=False)

    def set_scene(self, scene_name: str, context: Optional[Dict] = None, send_scene = True):
        self.previous_scene = self.current_scene
        temp = SceneManager.create_scene(scene_name, self, context)
        self.current_scene = temp
        if send_scene:
            temp.send()
        return temp

    def clear_scene(self):
        self.current_scene = Data.EmptyScene

Data.User = User

try:
    from timestamp_store import TimestampStore
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "timestamp_store"])
        from timestamp_store import TimestampStore
    except Exception:
        from .local_timestamp_store import TimestampStore

class BanUsersClass:
    def __init__(self):
        self.store = TimestampStore()
        self.ban_ids = set()
        self.last_update = 0

    def loaded(self):
        self.ban_ids = {i.Id if isinstance(i, Id) else i for i in (Data.User.ban == True).found()}
        self.store = TimestampStore({i: int(user.unbanTime) for i in self.ban_ids if (user:=User.get(i))})

    def update(self):
        if self.last_update != time.time():
            removed = self.store.remove_timestamp(int(time.time()))
            if removed:
                self.ban_ids.difference_update(set(removed))
                for i in removed:
                    user = User.get(i)
                    if user:
                        user.ban = False
            self.last_update = int(time.time())

    def check_ban(self, Id):
        if Id in self.ban_ids:
            self.update()
            return Id in self.ban_ids
        return False

    def deep_cheak_ban(self, Id):
        user = Data.User.get(Id)
        temp = user.ban
        if temp and user.unbanTime <= time.time():
            self.unban(Id)
            return False
        return temp

    def ban(self, target_Id, timestamp=0, which=0, text=None):
        is_update = True if target_Id in self.ban_ids else False
        user = Data.User.get(target_Id)
        if is_update:
            temp = dict()
            if timestamp:
                temp['end'] = timestamp
                user.unbanTime = int(timestamp)
            if which:
                temp['which'] = which
            if text is not None:
                temp['text'] = text
            user.banInfo |= temp
        else:
            if timestamp < time.time():
                return
            user.unbanTime = int(timestamp)
            user.ban = True
            user.banInfo = {'which': which, 'text': '' if text is None else text, 'start': int(time.time()), 'end': timestamp}

        self.store.add(target_Id, timestamp)
        self.ban_ids.add(target_Id)

    def unban(self, Id):
        if Id not in self.ban_ids:
            return
        user: User = Data.User.get(Id)
        temp = user.doDict
        if temp.get('BanSelf', None) is None:
            temp['BanSelf'] = [user.banInfo]
        else:
            temp['BanSelf'].append(user.banInfo)
        user.ban = False
        user.unbanTime = 0
        self.store.remove(Id)
        self.ban_ids.remove(Id)

BanUsers = BanUsersClass()
Data.BanUsers = BanUsers