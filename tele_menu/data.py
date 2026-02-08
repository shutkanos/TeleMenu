import typing
import telebot
import db_attribute

class Data:
    User: typing.Type[db_attribute.DbAttribute] = None
    Scenes: dict = dict()
    EmptyScene: typing.Any = None
    EmptyUser: typing.Any = None
    BanUsers: typing.Any = None
    bot: telebot.TeleBot = None
    sql_config: dict = dict()
    connect_object: db_attribute.connector.Connection = None
    Ranks: dict = {'User': 0, 'Vip': 1, 'Admin': 2, 'Owner': 3}
