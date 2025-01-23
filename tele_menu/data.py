import telebot

import dictobj

class Data:
    UserCls: type
    Users: dictobj.DictObj
    Scenes: dict = dict()
    bot: telebot.TeleBot
    Ranks: dict = {'User': 0, 'Vip': 1, 'Admin': 2, 'Owner': 3}
