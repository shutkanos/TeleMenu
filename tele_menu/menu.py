from dataclasses import dataclass, field
from telebot import types as teletypes, REPLY_MARKUP_TYPES
import json

def eval_fstr(s, glo=None, loc=None):
    return eval(f'''(f"""{s}""", locals())''', glo, loc)

def eval_func(s, glo=None, loc=None):
    return eval(f'''({s}, locals())''', glo, loc)

class fstr(str): pass

class evalstr(str): pass

class JsonConverter:
    def to_dict(self):
        """This function must be overridden by subclasses."""
        return NotImplementedError

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def de_json(cls, json_string):
        if json_string is None: return None
        obj = cls.check_json(json_string)
        for i in cls.__annotations__:
            obj[i] = obj.get(i, None)
        return cls(**obj)

    @staticmethod
    def check_json(json_type, dict_copy=True):
        if isinstance(json_type, dict):
            return json_type.copy() if dict_copy else json_type
        elif isinstance(json_type, str):
            return json.loads(json_type)
        else:
            raise ValueError("json_type should be a json dict or string.")

    def _standart_to_dict(self, convert_to_dict=None, convert_to_json=None):
        if convert_to_json is None:
            convert_to_json = list()
        if convert_to_dict is None:
            convert_to_dict = list()
        res = self.__dict__.copy()
        for i in convert_to_dict:
            res[i] = res[i].to_dict()
        for i in convert_to_json:
            res[i] = res[i].to_json()
        temp = list()
        for i in res:
            if res[i] is None:
                temp.append(i)
        for i in temp:
            del res[i]
        return res

class PostClass(JsonConverter):
    def __init__(self, PreObj, glo=None, loc=None, **kwargs):
        self.__dict__ |= PreObj.__dict__ | kwargs
        for i in self.__dict__:
            if isinstance(self.__dict__[i], fstr):
                self.__dict__[i], loc = eval_fstr(self.__dict__[i], glo=glo, loc=loc)
            if isinstance(self.__dict__[i], evalstr):
                self.__dict__[i], loc = eval_func(self.__dict__[i], glo=glo, loc=loc)

@dataclass
class Message:
    text: evalstr | fstr | str
    parse_mode: evalstr | fstr | str = field(default=None, repr=False)
    entities: evalstr | fstr | list[teletypes.MessageEntity] = field(default=None, repr=False)
    disable_notification: evalstr | fstr | bool = field(default=None, repr=False)
    protect_content: evalstr | fstr | bool = field(default=None, repr=False)
    #reply_markup: post_eval | fstr | REPLY_MARKUP_TYPES = field(default=None, repr=False) не все типы данных JsonDeserializable
    timeout: evalstr | fstr | int = field(default=None, repr=False)
    reply_parameters: evalstr | fstr | teletypes.ReplyParameters = field(default=None, repr=False)
    link_preview_options: evalstr | fstr | teletypes.LinkPreviewOptions = field(default=None, repr=False)
    business_connection_id: evalstr | fstr | str = field(default=None, repr=False)
    message_effect_id: evalstr | fstr | str = field(default=None, repr=False)
    def send(self, chat_id, message_id=None, reply_markup=None):
        pass

class PostMessage(PostClass, Message):
    def to_dict(self):
        res = self._standart_to_dict(convert_to_dict=['reply_parameters', 'link_preview_options'])
        if 'entities' in res and isinstance(res['entities'], list):
            for i in range(len(res['entities'])):
                res['entities'][i] = res['entities'][i].to_dict()

Message._post_cls = PostMessage