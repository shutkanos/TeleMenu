import sys
import time
import datetime
import subprocess
from typing import Dict, Optional, Type

from db_attribute import DbAttribute, DbAttributeMetaclass
from db_attribute.db_types import DbField, Id, DbWorkMarker

from .data import Data
from .scenes import Scene, SceneManager
from .logger import Log


class BaseMeta:
    __dbworkobj__ = DbWorkMarker('main')


class UserBase(DbAttribute, metaclass=DbAttributeMetaclass):
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

    def set_scene(self, scene_name: str, context: Optional[Dict] = None, send_scene=True):
        self.previous_scene = self.current_scene
        temp = SceneManager.create_scene(scene_name, self, context)

        if temp._build_result is not None:
            temp._build_result.activate(self, temp)
            return temp

        self.current_scene = temp
        if send_scene:
            temp.send()
        return temp

    def clear_scene(self):
        self.current_scene = Data.EmptyScene


def user_register(user_class: Type[UserBase] = None):
    """
    Register custom User class.

    Args:
        user_class: Custom user class that inherits from UserBase.
                   If None, uses UserBase as default.

    Example:
        class CustomUser(UserBase):
            coins: int = DbField(default=0)
            level: int = DbField(default=1)

        user_register(CustomUser)
    """
    if user_class is None:
        user_class = UserBase
    Data.User = user_class


user_register()

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
        self.store = TimestampStore({i: int(user.unbanTime) for i in self.ban_ids if (user := Data.User.get(i))})

    def update(self):
        if self.last_update != time.time():
            removed = self.store.remove_timestamp(int(time.time()))
            if removed:
                for i in removed:
                    if i in self.ban_ids:
                        self.unban(i)
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
            user.banInfo = {'which': which, 'text': '' if text is None else text, 'start': int(time.time()),
                            'end': timestamp}

        Log.info(f"Banning user(id={target_Id}, tgUsername={user.tgUsername}, banInfo={user.banInfo})")

        self.store.add(target_Id, timestamp)
        self.ban_ids.add(target_Id)

        try:
            from .scenes import SceneManager
            user.set_scene("ban_notification", context={'ban_info': user.banInfo})
        except Exception as e:
            Log.error(f"Failed to send ban notification: {e}")

    def unban(self, Id):
        if Id not in self.ban_ids:
            return
        user = Data.User.get(Id)
        Log.info(f"Unbanning user(id={Id}, tgUsername={user.tgUsername})")

        temp = user.doDict
        if temp.get('BanSelf', None) is None:
            temp['BanSelf'] = [user.banInfo]
        else:
            temp['BanSelf'].append(user.banInfo)

        ban_info = user.banInfo.copy()

        user.ban = False
        user.unbanTime = 0

        if Id in self.store:
            self.store.remove(Id)
        self.ban_ids.discard(Id)

        try:
            from .scenes import SceneManager
            user.set_scene("unban_notification", context={'ban_info': ban_info})
        except Exception as e:
            Log.error(f"Failed to send unban notification: {e}")


BanUsers = BanUsersClass()
Data.BanUsers = BanUsers