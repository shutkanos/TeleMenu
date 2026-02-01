import functools, datetime

import tele_menu
from tele_menu.logger import Log
from tele_menu.data import Data

def allmesege(func=None, /, ThisCall=False, MinRank='User', Logging=True, RankForLogging='User'):
    def actual_decorator(func):
        @functools.wraps(func)
        def allmesege_decor(mess):
            user = Data.User.get(mess.from_user.id)
            if user is None or user.tgUsername == "":
                user = Data.User(id=mess.from_user.id,
                                 nameuser=(mess.from_user.first_name if mess.from_user.first_name else mess.from_user.username),
                                 tgUsername = mess.from_user.username,
                                 registerData = datetime.datetime.now())

            #if user.ban or AntiSpam(user, mess, ThisCall): return

            text = eval("mess.data" if ThisCall else "mess.text")

            if not ThisCall:
                try:
                    Data.bot.delete_message(mess.from_user.id, mess.id)
                except:
                    pass

            if Data.Ranks[user.rank] < Data.Ranks[MinRank]:
                if Data.Ranks[user.rank] > 0:
                    Log.info(title='Access is denied. Insufficient rank', msg=f'{user} try to "{text}"')
                return

            if Logging and Data.Ranks[user.rank] >= Data.Ranks[RankForLogging] or Data.Ranks[MinRank] >= 2:
                Log.debug(title='Logging mess', msg=f'msg "{text}" from {user}')

            func(mess, text, user)
        return allmesege_decor
    if func is None:
        return actual_decorator
    return actual_decorator(func)

def register_handlers(bot):
    @bot.message_handler(commands=['start'])
    @allmesege
    def CommandStart(message, text, user):
        user.clear_scene()
        user.set_scene("main_menu")
        user.current_scene.send()

    @bot.callback_query_handler(func=lambda call: call.data.split('|')[0] == "tele_menu")
    @allmesege(ThisCall=True)
    def call_all(call, text, user):
        temp = text.split('|')[1:]
        # tele_menu.Log.info(f"Click: '{text}' from from User(id={user.id}, tgUsername={user.tgUsername})") ||||||||||||||||
        if len(temp) != 5 or any(not i.isdecimal() for i in temp):
            bot.answer_callback_query(call.id, text="Error, try send /start")
            return
        user_id, scene_id, message_num, button_i, button_j = map(int, temp)
        user_scene: tele_menu.scenes.Scene = user.current_scene
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