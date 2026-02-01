import telebot
from db_attribute import connector, db_work, DbAttribute, DbAttributeMetaclass
from db_attribute.db_types import DbField, NotSet
from typing import Dict, Optional
import datetime
import collections

import tele_menu.data as data
import tele_menu.scenes as scenes
import tele_menu.handler as handler
from tele_menu.logger import Log

__all__ = ["User", "bot_register", "sql_register", "data", "scenes", "handler"]
__version__ = '3.0'

class BaseMeta:
    __skip_dbworkobj__ = True

class User(DbAttribute, metaclass=DbAttributeMetaclass):
    Meta = BaseMeta
    nameuser: str = DbField(default="")
    tgUsername: str = DbField(default="")
    registerData: datetime.date = DbField(default=datetime.date.today(), repr=False)
    # Administrated
    ban: bool = DbField(default=False)
    rank: str = DbField(default="User")
    banInfo: dict = DbField(
        default_factory=lambda: {'which': -1, 'text': '', 'when': datetime.datetime(1, 1, 1), 'rank': 'User'},
        repr=False)
    doDict: dict = DbField(default_factory=lambda: {'MuteSelf': [], 'BanSelf': []}, repr=False)
    # Antispam
    mute: bool = DbField(default=False, repr=False)
    unmuteTime: datetime.datetime = DbField(default=datetime.datetime.now() - datetime.timedelta(seconds=9999), repr=False)
    #TimeMess: collections.deque[datetime.datetime] = dataclasses.field(default_factory=lambda: collections.deque(
    #    [datetime.datetime.now() - datetime.timedelta(seconds=i * 5) for i in range(10)]), repr=False)
    # scene module
    current_scene: scenes.Scene = DbField(default=data.Data.EmptyScene, repr=False)
    previous_scene: scenes.Scene = DbField(default=data.Data.EmptyScene, repr=False)
    activeInputFunction: bool = DbField(default=False, repr=False)

    def set_scene(self, scene_name: str, context: Optional[Dict] = None):
        self.previous_scene = self.current_scene
        self.current_scene = scenes.SceneManager.create_scene(scene_name, self, context)
        return self.current_scene

    def clear_scene(self):
        self.current_scene = data.Data.EmptyScene

def bot_register(bot: telebot.TeleBot):
    data.Data.bot = bot
    handler.register_handlers(bot)

def sql_register(host="127.0.0.1", user="", password="", database=None):
    Log.debug(title="sql register", msg=f"{host=} {user=} password=*** {database=}")
    data.Data.sql_config = dict(host=host, user=user, password=password, database=database)
    data.Data.connect_object = connector.Connection(**data.Data.sql_config)
    db_work_obj = db_work.Db_work(data.Data.connect_object)
    User.register_dbworkobj(db_work_obj)

data.Data.User = User