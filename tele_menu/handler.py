import functools
import datetime
import time

import db_attribute
from db_attribute.db_types import DbWorkManager
import telebot

from .logger import Log
from .data import Data
from . import scenes

def bot_register(bot: telebot.TeleBot):
    Data.bot = bot
    register_handlers(bot)

def sql_register(connector=db_attribute.connector.MySQLConnection, *args, **kwargs):
    """
    Connecting to the DB via db_attribute.

    Args:
        connector: Connector class (default MySQLConnection). * MySQL:
                   * MySQL: sql_register(host="127.0.0.1", user="root", password="...", database="mybot")
                   * SQLite: sql_register(connector.SQLiteConnection, path=":memory:")
        *args, **kwargs: Passed to connector.
    """
    Log.debug(title="sql register", msg=f"connector={connector.__name__} {args=} {kwargs=}")
    Data.sql_config = (args, kwargs)
    Data.connect_object = connector(*args, **kwargs)
    db_work_obj = db_attribute.db_work.Db_work(Data.connect_object)
    DbWorkManager.connect('main', db_work_obj)
    Data.BanUsers.loaded()

def allmesege(func=None, /, ThisCall=False, MinRank='User', Logging=True, RankForLogging='User'):
    def actual_decorator(func):
        @functools.wraps(func)
        def allmesege_decor(mess):
            user_id = mess.from_user.id
            if Data.BanUsers.check_ban(user_id):
                return

            user = Data.User.get(user_id)
            if user is None or user.tgUsername == "":
                user = Data.User(id=user_id,
                                 nameuser=(mess.from_user.first_name if mess.from_user.first_name else mess.from_user.username),
                                 tgUsername = mess.from_user.username,
                                 registerData = datetime.datetime.now())

            if Data.BanUsers.deep_cheak_ban(user_id) or Antiddos(user, mess, ThisCall): return

            text = eval("mess.data" if ThisCall else "mess.text")

            if not ThisCall:
                try:
                    Data.bot.delete_message(user_id, mess.id)
                except:
                    pass
            rank = user.rank
            if Data.Ranks[rank] < Data.Ranks[MinRank]:
                if Data.Ranks[rank] > 0:
                    Log.info(title='Access is denied. Insufficient rank', msg=f'{user} try to "{text}"')
                return

            if Logging and Data.Ranks[rank] >= Data.Ranks[RankForLogging] or Data.Ranks[MinRank] >= 2:
                Log.debug(title='Logging mess', msg=f'msg "{text}" from {user}')

            func(mess, text, user)
        return allmesege_decor
    if func is None:
        return actual_decorator
    return actual_decorator(func)

def Antiddos(user, mess, ThisCall):
    numMessagesPerSec = user.numMessagesPerSec
    timer, count = numMessagesPerSec // 1000, numMessagesPerSec % 1000
    if timer != int(time.time()) // 10:
        timer = int(time.time()) // 10
        count = 1
    else:
        count += 1
    if count >= 10:
        Data.BanUsers.ban(user.id, timestamp=int(time.time()) + 10*60, which=1, text="banned by antiddos system")
        return True
    user.numMessagesPerSec = timer * 1000 + count
    return False

def register_handlers(bot):
    @bot.message_handler(commands=['start'])
    @allmesege
    def CommandStart(message, text, user):
        user.clear_scene()
        user.set_scene("main_menu")

    @bot.message_handler(func=lambda message: True)
    @allmesege
    def messages(message, text, user):
        try:
            user_scene: scenes.Scene = user.current_scene
        except:
            return
        user_scene.input(text)

    @bot.callback_query_handler(func=lambda call: call.data.split('|')[0] == "tele_menu")
    @allmesege(ThisCall=True)
    def call_all(call, text, user):
        temp = text.split('|')[1:]
        # tele_menu.Log.info(f"Click: '{text}' from from User(id={user.id}, tgUsername={user.tgUsername})") ||||||||||||||||
        if len(temp) != 5 or any(not i.isdecimal() for i in temp):
            bot.answer_callback_query(call.id, text="Error, try send /start")
            return
        user_id, scene_id, message_num, button_i, button_j = map(int, temp)
        user_scene: scenes.Scene = user.current_scene
        if user.id != user_id or user_scene.id != scene_id:
            bot.answer_callback_query(call.id, text="Error, try send /start")
            return
        if len(user_scene.messages) <= message_num or \
                len(user_scene.messages[message_num].buttons) <= button_i or \
                len(user_scene.messages[message_num].buttons[button_i]) <= button_j:
            bot.answer_callback_query(call.id, text="Error, try send /start")
            return
        user_scene.messages[message_num].buttons[button_i][button_j].action.activate(user, user_scene)
        bot.answer_callback_query(call.id)