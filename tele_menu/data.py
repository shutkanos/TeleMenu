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
    sql_config: tuple[tuple, dict] = ((), dict())
    connect_object: db_attribute.connector.MySQLConnection | db_attribute.connector.SQLiteConnection = None
    Ranks: dict = {'User': 0, 'Vip': 1, 'Admin': 2, 'Owner': 3}
    language: str = 'en'

    translations: dict = {
        'en': {
            'ban_title': '🚫 YOU ARE BANNED',
            'ban_reason': 'Reason',
            'ban_start': 'Started',
            'ban_end': 'Ends',
            'ban_duration': 'Duration',
            'ban_footer': 'You cannot use the bot until the ban expires.',
            'unban_title': '✅ YOU ARE UNBANNED',
            'unban_header': 'Your ban has been lifted.',
            'unban_info': 'Ban information:',
            'unban_footer': 'You can now use the bot. Send /start to begin.',
            'unknown': 'Unknown',
            'violation': 'Rule violation',
            'days': 'd.',
            'hours': 'h.',
            'minutes': 'min.',
        },
        'ru': {
            'ban_title': '🚫 ВЫ ЗАБЛОКИРОВАНЫ',
            'ban_reason': 'Причина',
            'ban_start': 'Начало',
            'ban_end': 'Окончание',
            'ban_duration': 'Длительность',
            'ban_footer': 'Вы не сможете использовать бота до окончания срока блокировки.',
            'unban_title': '✅ ВЫ РАЗБЛОКИРОВАНЫ',
            'unban_header': 'Ваша блокировка была снята.',
            'unban_info': 'Информация о блокировке:',
            'unban_footer': 'Теперь вы можете использовать бота. Отправьте /start для начала работы.',
            'unknown': 'Неизвестно',
            'violation': 'Нарушение правил',
            'days': 'дн.',
            'hours': 'ч.',
            'minutes': 'мин.',
        }
    }

    @classmethod
    def get_text(cls, key: str) -> str:
        return cls.translations.get(cls.language, cls.translations['en']).get(key, key)
