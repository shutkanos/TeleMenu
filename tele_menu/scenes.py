from typing import Any
import telebot

from logger import Log
import menu, data

def eval_fstr(s, glo=None, loc=None):
    return eval(f'''(f"""{s}""", locals())''', glo, loc)

def eval_func(s, glo=None, loc=None):
    return eval(f'''({s}, locals())''', glo, loc)

def exec_func(s, glo=None, loc=None):
    exec(s, glo, loc)

def cheak_eval(var, glo=None, loc=None):
    err = None
    try:
        if isinstance(var, menu.fstr):
            var, loc = eval_fstr(var, glo=glo, loc=loc)
        if isinstance(var, menu.evalstr):
            var, loc = eval_func(var, glo=glo, loc=loc)
    except Exception as e:
        err = f'{e}'
        Log.error(msg=f'Exception in eval func: {e}')
    return var, loc, err

"""
@dataclass
class Button:
    text: str
    call: None | str = None
    info: Any = None
    commands: None | list = None
"""

class SceneBuilder:
    name: str | menu.fstr | menu.evalstr
    sends: list | menu.fstr | menu.evalstr
    buttons: None | list[list[dict[str, Any]]] | menu.fstr | menu.evalstr = None
    commandsAIF: None | list[str] | menu.fstr | menu.evalstr = None

    def __new__(cls, user, info=None, glo=None):
        return cls.generate_scene(user=user, info=info, glo=glo)

    @classmethod
    def generate_this_scene(cls, user, info=None, glo=None):
        return PostScene(user=user, name=cls.name, sends=cls.sends, buttons=cls.buttons, commandsAIF=cls.commandsAIF, info=info, glo=glo)

    @classmethod
    def generate_scene(cls, scene_name, user, info=None, glo=None):
        return SceneMetaclass.ScenesDict[scene_name].generate_this_scene(user=user, info=info, glo=glo)

class PostScene(menu.JsonConverter):
    name: str
    sends: list
    buttons: list[list[dict[str, Any]]]
    commandsAIF: list[str]

    def __init__(self, user, name, sends, buttons=None, commandsAIF=None, info=None, glo=None):
        self.user = user
        self.name = name
        self.sends = sends
        self.buttons = list() if buttons is None else buttons
        self.commandsAIF = list() if commandsAIF is None else commandsAIF
        self.info = dict() if info is None else info
        loc = self.info | {'user': user}
        #sends
        self.sends, loc, err = cheak_eval(self.sends, glo=glo, loc=loc)
        for i in range(len(self.sends)):
            self.sends[i], loc, err = cheak_eval(self.sends[i], glo=glo, loc=loc)
            if not isinstance(self.sends[i], menu.PostClass):
                self.sends[i] = self.sends[i]._post_cls(self.sends[i], glo=glo, loc=loc)
        #buttons
        self.buttons, loc, err = cheak_eval(self.buttons, glo=glo, loc=loc)
        for i in range(len(self.buttons)):
            self.buttons[i], loc, err = cheak_eval(self.buttons[i], glo=glo, loc=loc)
            for j in range(len(self.buttons[i])):
                self.buttons[i][j], loc, err = cheak_eval(self.buttons[i][j], glo=glo, loc=loc)
                if 'text' not in self.buttons[i][j]:
                    self.buttons[i][j]['text'] = ' '
                    Log.warning(title='SceneBuilder', msg=f'The button don\'t have the "text" (obligatory) key in scene={self.name} info={self.info} button={self.buttons[i][j]}')
                temp = set(self.buttons[i][j]) - {'text', 'call', 'info', 'commands'}
                if temp:
                    Log.warning(title='SceneBuilder', msg=f'Warning! The button have the not support key\'s: {temp} in scene={self.name} info={self.info} button={self.buttons[i][j]}')
                for key in temp:
                    del self.buttons[i][j][key]
        #commandsAIF
        self.commandsAIF, loc, err = cheak_eval(self.commandsAIF, glo=glo, loc=loc)
        for i in range(len(self.commandsAIF)):
            self.commandsAIF[i], loc, err = cheak_eval(self.commandsAIF[i], glo=glo, loc=loc)
        #set user nowscene
        self.user.nowscene = self

    def send_scene(self, glo=None):
        loc = self.info | {'user': self.user}
        Markup = telebot.types.InlineKeyboardMarkup()

        for i in range(len(self.buttons)):
            Markup.row(*[telebot.types.InlineKeyboardButton(text=self.buttons[i][j]['text'], callback_data=f'telemenu|button_click|{i}|{j}') for j in range(len(self.buttons[i]))])

        if self.user.menumess:
            try:
                data.Data.bot.edit_message_text(chat_id=self.user.id, message_id=self.user.menumess.id, text=scene.text)
                data.Data.bot.edit_message_reply_markup(chat_id=self.user.id, message_id=self.user.menumess.id, reply_markup=Markup)
            except:
                self.user.menumess = data.Data.bot.send_message(self.user.id, text=scene.text, reply_markup=Markup)
        else:
            self.user.menumess = data.Data.bot.send_message(self.user.id, text=scene.text, reply_markup=Markup)

        data.Data.bot.edit_

        if self.commandsAIF and not self.user.activeInputFunction:
            self.user.activeInputFunction = True
            data.Data.bot.register_next_step_handler(self.user.menumess, data.inputFunction)

    def button_click(self, i, j, glo=None):
        """
        :param i: first coordinate of button
        :param j: second coordinate
        :param glo: globals dict
        :param loc: locals dict
        """
        loc = self.info | {'user': self.user}
        if len(self.buttons) >= i or len(self.buttons[0]) >= j:
            Log.warning(msg=f'not found buttons! {loc=}, scene={self.name}, buttons={self.buttons}, {i=}, {j=}')
            return {'status_code': 400, 'data': 'not found button'}
        button = self.buttons[i][j]
        if 'command' in button:
            for i in button['command']:
                exec_func(i, glo=glo, loc=loc)
        if 'call' in button:
            if button['call'] not in SceneMetaclass.ScenesDict:
                Log.warning(msg=f'Scene {button["call"]} not found, scene={self.name}')
                return {'status_code': 400, 'data': 'not found scene'}
            SceneBuilder.generate_scene(scene_name=button['call'], user=self.user, info=button.get('info', None), glo=glo).send_scene(glo=glo)

class SceneMetaclass(type):
    ScenesDict = dict()
    def __new__(cls, name, bases, attrs):
        if set(attrs) & {'name', 'sends'} != {'name', 'sends'}:
            raise Exception(f'Error when create class: {name} - need "name" and "sends" attributes')
        obj = super().__new__(cls, name, (SceneBuilder,) + bases, attrs)
        cls.ScenesDict[attrs['name']] = obj
        return obj
