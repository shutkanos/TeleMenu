import random, json, base64
import traceback, inspect
from typing import Dict, List, Type, Optional, Any
from io import BytesIO

import db_attribute, telebot
from db_attribute import db_class

import tele_menu
from .data import Data
from .memory_storage import MemoryMedia

effects_ids = {
    '🔥': "5104841245755180586",
    '👍': "5107584321108051014",
    '👎': "5104858069142078462",
    '❤️': "5044134455711629726",
    '🎉': "5046509860389126442",
    '💩': "5046589136895476101"
}


class BaseManager:
    _registry: Optional[Dict[str, Type]] = None
    type_attribute: str = "type"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry = {}

    @classmethod
    def register(cls, target_class: Type, **kwargs) -> Type:
        if cls._registry is None:
            cls._registry = {}
        key = cls._get_class_type(target_class, **kwargs)
        if key is None:
            raise Exception(f"{cls.__name__}. Type name for '{target_class.__name__}' is not registered")
        temp = cls._set_class_type(target_class, key)
        if temp is not None:
            key = temp
        cls._registry[key] = target_class
        return target_class

    @classmethod
    def get(cls, class_name: str) -> Type:
        if cls._registry is None or (temp := cls._registry.get(class_name, None)) is None:
            raise Exception(f"{cls.__name__} type '{class_name}' is not registered")
        return temp

    @classmethod
    def names(cls) -> List[str]:
        if cls._registry is None:
            return []
        return list(cls._registry.keys())

    @classmethod
    def _get_class_type(cls, target_class, **kwargs) -> Optional[str]:
        type_val = kwargs.get(cls.type_attribute, None)
        if type_val is None:
            type_val = getattr(target_class, cls.type_attribute, None)
            if type_val is None:
                type_val = target_class.__name__
        return type_val

    @classmethod
    def _set_class_type(cls, target_class: Type, type_value: Optional[str]) -> str:
        if type_value is not None:
            setattr(target_class, cls.type_attribute, type_value)
            return type_value
        return getattr(target_class, cls.type_attribute)

    @classmethod
    def decorator_register(cls, target_class=None, /, **kwargs):
        is_direct_call = target_class is not None and inspect.isclass(target_class)

        def wrapper(cls_obj: Type) -> Type:
            return cls.register(cls_obj, **kwargs)

        if is_direct_call:
            return wrapper(target_class)
        return wrapper


class BaseAction:
    type: str = 'base'

    def __init__(self, target=None):
        self.target = target

    def activate(self, user, scene):
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {'t': self.type, 'ta': self.target}

    @classmethod
    def from_dict(cls, json_data):
        if json_data.get('t', None) != cls.type:
            raise Exception("Use the ActionManager Class to call 'restore_from_dict'")
        return cls(json_data.get('ta', None))


class ActionManager(BaseManager):
    @classmethod
    def restore_from_dict(cls, json_data):
        action_cls: BaseAction = cls.get(json_data.get('t', None))
        return action_cls.from_dict(json_data)


@ActionManager.decorator_register(type='SendScene')
class SendSceneAction(BaseAction):
    def __init__(self, scene_name, context=None):
        self.scene_name = scene_name
        self.context = context

    def activate(self, user, scene):
        user.set_scene(self.scene_name, self.context)

    def to_dict(self) -> Dict[str, Any]:
        temp = {'t': self.type, 's': self.scene_name}
        if self.context:
            temp['c'] = self.context
        return temp

    @classmethod
    def from_dict(cls, json_data):
        if json_data.get('t', None) != cls.type:
            raise Exception("Use the ActionManager Class to call 'restore_from_dict'")
        return cls(scene_name=json_data.get('s', None), context=json_data.get('c', None))


@ActionManager.decorator_register(type='CallMethod')
class CallMethodAction(BaseAction):
    def __init__(self, method_name, args=None, kwargs=None):
        super().__init__(method_name)
        self.args = [] if args is None else args
        self.kwargs = {} if kwargs is None else kwargs

    def activate(self, user, scene):
        method = getattr(scene, self.target, None)
        if method is None:
            raise Exception(f"The '{scene.name}' Scene has not '{self.target}' method")
        method(*self.args, **self.kwargs)

    def to_dict(self) -> Dict[str, Any]:
        temp = {'t': self.type, 'm': self.target}
        if self.args:
            temp['a'] = self.args
        if self.kwargs:
            temp['k'] = self.kwargs
        return temp

    @classmethod
    def from_dict(cls, json_data: dict, need_call_sub_class=True):
        if json_data.get('t', None) != cls.type:
            raise Exception("Use the BaseAction Class to call 'from_dict'")
        return cls(method_name=json_data["m"], args=json_data.get("a", None), kwargs=json_data.get("k", None))


class OpenMedia:
    def __init__(self, file, mode="rb", encoding=None):
        self.file = file
        self.mode = mode
        self.encoding = encoding

    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'open', 'file': self.file, 'mode': self.mode, 'encoding': self.encoding}

    @classmethod
    def from_dict(cls, data):
        return cls(file=data['file'], mode=data.get('mode', 'rb'), encoding=data.get('encoding', None))

    @classmethod
    def convert_from_open(cls, obj):
        return cls(file=obj.name, mode=getattr(obj, 'mode', 'rb'), encoding=getattr(obj, 'encoding', None))

    def create_open(self):
        return open(file=self.file, mode=self.mode, encoding=self.encoding)


from .media_caching import SourceManager, wrap_source, BaseSource, MediaObject, FileIdCache


class Button:
    def __init__(self, text: str, action: BaseAction = None):
        self.text = text
        self.action = action

    def to_dict(self) -> Dict[str, Any]:
        return {'text': self.text, 'action': self.action.to_dict()}

    @classmethod
    def from_dict(cls, data):
        action = data.get('action', None)
        if action is not None:
            action = ActionManager.restore_from_dict(action)
        return cls(text=data['text'], action=action)


class BaseMessage:
    type: str = 'base'
    cheak_readble_content: bool = False

    def __init__(self, content: Any, buttons: List[List[Button]] = None, effect_id: str = None):
        """
        :param content: content of the message, example: TextMessage('text'), ContactMessage('+00000'), PhotoMessage(open("example.png")), PhotoMessage("https://")
        :param buttons: buttons, example: [[
                    Button("Profile", action=SendSceneAction(scene_name='profile', context={'come_from': 'main_menu', 'mykey': 'mydata'})),
                    Button("Random nick", action=CallMethodAction(method_name='random_nick', kwargs={'salt': '(random_nick) or other salt'}))
                ]]
        :type buttons: List[List[Button]]
        :param effect_id: id of message effect, example: '5104841245755180586' - id of fire effect (you can see all ids here: tele_menu.scenes.effects_ids)
        :param **kwargs: metadata, example: ContactMessage('+00000', first_name='Iriya', last_name='Genexpe'), PhotoMessage(photo, caption='text')
        """
        if self.cheak_readble_content and hasattr(content, 'read') and hasattr(content, 'name'):
            content = OpenMedia.convert_from_open(content)
        self.content = content
        self.buttons = buttons or []
        self.effect_id = effect_id
        self.message_num = -1
        self._messages_ids = []

    def send(self, scene):
        raise NotImplementedError

    def delete(self, scene):
        for msg_id in self._messages_ids:
            try:
                Data.bot.delete_message(chat_id=scene.user.id, message_id=msg_id)
            except:
                tele_menu.Log.error(f"error delete message: {traceback.format_exc()}")
        self._messages_ids = []

    def replace(self, scene, new_message) -> bool:
        """
        Try to edit this message in-place so it becomes new_message.

        Returns:
            True: the message was successfully synced (edited OR safely left untouched
                  because content/markup was already identical) - new_message._messages_ids
                  is guaranteed to hold valid, still-alive message ids.
            False: could not sync the message in-place (real, unrecoverable API error) -
                   caller MUST fall back to delete(old) + send(new) itself, since
                   new_message._messages_ids might not be populated/valid here.
        """
        raise NotImplementedError

    @staticmethod
    def _is_not_modified_error(e: "telebot.apihelper.ApiTelegramException") -> bool:
        return 'message is not modified' in str(e).lower()

    def _create_markup(self, scene):
        keyboard = []
        for i, row in enumerate(self.buttons):
            kb_row = []
            for j, btn in enumerate(row):
                callback_data = f"tele_menu|{scene.user.id}|{scene.id}|{self.message_num}|{i}|{j}"
                kb_row.append(telebot.types.InlineKeyboardButton(
                    text=btn.text,
                    callback_data=callback_data
                ))
            keyboard.append(kb_row)
        return telebot.types.InlineKeyboardMarkup(keyboard)

    def to_dict(self) -> Dict[str, Any]:
        json_data = {'type': self.type, 'content': self.content}
        if self.buttons:
            json_data['buttons'] = [[btn.to_dict() for btn in row] for row in self.buttons]
        if self.effect_id:
            json_data['effect_id'] = self.effect_id
        json_data['_messages_ids'] = self._messages_ids
        return json_data

    @classmethod
    def from_dict(cls, json_data):
        # message_class = MessageManager.get(json_data['type'])
        obj = cls(
            content=json_data['content'],
            buttons=[[Button.from_dict(btn) for btn in row] for row in json_data.get('buttons', [])],
            effect_id=json_data.get('effect_id', None)
        )
        obj._messages_ids = json_data.get('_messages_ids', [])
        return obj


class MessageManager(BaseManager):
    @classmethod
    def restore_from_dict(cls, json_data):
        action_cls: BaseMessage = cls.get(json_data['type'])
        return action_cls.from_dict(json_data)


@MessageManager.decorator_register(type="text")
class TextMessage(BaseMessage):
    MAX_TEXT_LENGTH = 4096

    def send(self, scene):
        text = self.content
        parts = []
        while text:
            parts.append(text[:self.MAX_TEXT_LENGTH])
            text = text[self.MAX_TEXT_LENGTH:]

        message_ids = []
        for i, part in enumerate(parts):
            reply_markup = self._create_markup(scene) if (i == len(parts) - 1 and self.buttons) else None
            effect_id = self.effect_id if (i == len(parts) - 1) else None

            msg = Data.bot.send_message(
                chat_id=scene.user.id,
                text=part,
                reply_markup=reply_markup,
                message_effect_id=effect_id
            )
            message_ids.append(msg.message_id)

        self._messages_ids = message_ids

    def replace(self, scene, new_message) -> bool:
        if not isinstance(new_message, TextMessage):
            return False

        new_text = new_message.content
        new_parts = []
        while new_text:
            new_parts.append(new_text[:self.MAX_TEXT_LENGTH])
            new_text = new_text[self.MAX_TEXT_LENGTH:]

        if len(new_parts) != len(self._messages_ids):
            return False

        for i, msg_id in enumerate(self._messages_ids):
            reply_markup = new_message._create_markup(scene) if (i == len(new_parts) - 1 and new_message.buttons) else None

            try:
                Data.bot.edit_message_text(
                    chat_id=scene.user.id,
                    message_id=msg_id,
                    text=new_parts[i],
                    reply_markup=reply_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if not self._is_not_modified_error(e):
                    return False

        new_message._messages_ids = self._messages_ids
        return True


@MessageManager.decorator_register(type="media")
class MediaMessage(BaseMessage):
    cheak_readble_content: bool = True

    def send(self, scene):
        reply_markup = self._create_markup(scene) if self.buttons else None
        send_method = getattr(Data.bot, f'send_{self.type}')

        if isinstance(self.content, MediaObject):
            msg = self._send_via_media_object(self.content, scene.user.id, send_method, reply_markup)
            self._messages_ids = [msg.message_id]
            return

        if isinstance(self.content, OpenMedia):
            content = self.content.create_open()
        elif isinstance(self.content, MemoryMedia):
            content = self.content.get_data(refresh_ttl=True)
            if content is None:
                raise Exception(f"MemoryMedia with id={self.content.media_id} expired or not found")
        else:
            content = self.content

        msg = send_method(
            chat_id=scene.user.id,
            **{self.type: content},
            reply_markup=reply_markup,
            message_effect_id=self.effect_id
        )

        if isinstance(self.content, OpenMedia):
            content.close()

        self._messages_ids = [msg.message_id]

    def _send_via_media_object(self, media_obj: "MediaObject", chat_id, send_method, reply_markup):
        """
        Sends a MediaObject, transparently using a cached file_id when available.
        Falls back to uploading the raw source and re-caching if there is no cache
        entry yet, or if a previously cached file_id turned out to be invalid.
        """
        media_obj.media_type = self.type
        cache_key = media_obj.get_cache_key() if media_obj.cache_enabled else None

        if cache_key:
            file_id = FileIdCache().get(self.type, cache_key)
            if file_id:
                try:
                    return send_method(
                        chat_id=chat_id,
                        **{self.type: file_id},
                        reply_markup=reply_markup,
                        message_effect_id=self.effect_id
                    )
                except telebot.apihelper.ApiTelegramException as e:
                    if not FileIdCache.is_invalid_file_id_error(e):
                        raise
                    FileIdCache().remove(self.type, cache_key)
                    # fall through to raw upload below

        raw = media_obj.open_for_send()
        msg = send_method(
            chat_id=chat_id,
            **{self.type: raw},
            reply_markup=reply_markup,
            message_effect_id=self.effect_id
        )
        media_obj.source.close_sent(raw)

        if cache_key:
            file_id = msg.photo[-1].file_id if self.type == "photo" else getattr(msg, self.type).file_id
            FileIdCache().set(self.type, cache_key, file_id)

        return msg

    def replace(self, scene, new_message) -> bool:
        if not isinstance(new_message, MediaMessage) or self.type != new_message.type:
            return False

        try:
            media_obj = None
            cache_key = None
            raw_for_close = None

            if isinstance(new_message.content, MediaObject):
                media_obj = new_message.content
                media_obj.media_type = self.type
                cache_key = media_obj.get_cache_key() if media_obj.cache_enabled else None
                file_id = FileIdCache().get(self.type, cache_key) if cache_key else None
                if file_id:
                    content = file_id
                else:
                    content = media_obj.open_for_send()
                    raw_for_close = content
            elif isinstance(new_message.content, OpenMedia):
                content = new_message.content.create_open()
                raw_for_close = content
            elif isinstance(new_message.content, MemoryMedia):
                content = new_message.content.get_data(refresh_ttl=True)
                if content is None:
                    raise Exception(f"MemoryMedia with id={new_message.content.media_id} expired or not found")
            else:
                content = new_message.content

            media = telebot.types.InputMedia(
                type=self.type,
                media=content
            )

            sent = None
            try:
                sent = Data.bot.edit_message_media(
                    chat_id=scene.user.id,
                    message_id=self._messages_ids[0],
                    media=media
                )
            except telebot.apihelper.ApiTelegramException as e:
                if media_obj is not None and cache_key and isinstance(content, str) and FileIdCache.is_invalid_file_id_error(e):
                    FileIdCache().remove(self.type, cache_key)
                    raw_for_close = media_obj.open_for_send()
                    media = telebot.types.InputMedia(type=self.type, media=raw_for_close)
                    sent = Data.bot.edit_message_media(
                        chat_id=scene.user.id,
                        message_id=self._messages_ids[0],
                        media=media
                    )
                elif not self._is_not_modified_error(e):
                    raise

            if raw_for_close is not None:
                if media_obj is not None:
                    media_obj.source.close_sent(raw_for_close)
                elif hasattr(raw_for_close, 'close'):
                    try:
                        raw_for_close.close()
                    except Exception:
                        pass

            if media_obj is not None and cache_key and sent is not None:
                file_id = sent.photo[-1].file_id if self.type == "photo" else getattr(sent, self.type).file_id
                FileIdCache().set(self.type, cache_key, file_id)

            reply_markup = new_message._create_markup(scene) if new_message.buttons else None
            try:
                Data.bot.edit_message_reply_markup(
                    chat_id=scene.user.id,
                    message_id=self._messages_ids[0],
                    reply_markup=reply_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if not self._is_not_modified_error(e):
                    raise

            new_message._messages_ids = self._messages_ids
            return True
        except telebot.apihelper.ApiTelegramException:
            return False

    def to_dict(self) -> Dict[str, Any]:
        json_data: Dict[str, Any] = {'type': self.type}

        content = self.content
        if content is None:
            pass
        elif isinstance(content, str):
            json_data['content'] = {'type': 'str', 'text': content}
        elif isinstance(content, bytes):
            json_data['content'] = {'type': 'bytes', 'data': base64.b64encode(content).decode('utf-8')}
        elif isinstance(content, BytesIO):
            content.seek(0)
            json_data['content'] = {'type': 'BytesIO', 'data': base64.b64encode(content.read()).decode('utf-8'), 'name': getattr(content, 'name', 'file')}
            content.seek(0)
        elif isinstance(content, OpenMedia):
            json_data['content'] = content.to_dict()
        elif isinstance(content, MemoryMedia):
            json_data['content'] = content.to_dict()
        elif isinstance(content, MediaObject):
            json_data['content'] = content.to_dict()
        else:
            json_data['content'] = content

        if self.buttons:
            json_data['buttons'] = [[btn.to_dict() for btn in row] for row in self.buttons]
        if self.effect_id:
            json_data['effect_id'] = self.effect_id
        json_data['_messages_ids'] = self._messages_ids

        return json_data

    @classmethod
    def from_dict(cls, json_data):
        content_data = json_data.get('content', None)
        content = None

        if content_data is not None:
            if isinstance(content_data, dict) and 'type' in content_data:
                content_type = content_data['type']

                if content_type == 'str':
                    content = content_data['text']
                elif content_type == 'bytes':
                    content = base64.b64decode(content_data['data'])
                elif content_type == 'BytesIO':
                    data = base64.b64decode(content_data['data'])
                    bio = BytesIO(data)
                    if 'name' in content_data:
                        bio.name = content_data['name']
                    content = bio
                elif content_type == 'open':
                    content = OpenMedia.from_dict(content_data)
                elif content_type == 'memory':
                    content = MemoryMedia.from_dict(content_data)
                elif content_type == 'media_object':
                    content = MediaObject.from_dict(content_data)
                else:
                    content = content_data
            else:
                content = content_data

        obj = cls(
            content=content,
            buttons=[[Button.from_dict(btn) for btn in row] for row in json_data.get('buttons', [])],
            effect_id=json_data.get('effect_id', None)
        )

        obj._messages_ids = json_data.get('_messages_ids', [])

        return obj

@MessageManager.decorator_register(type="photo")
class PhotoMessage(MediaMessage): pass

@MessageManager.decorator_register(type="video")
class VideoMessage(MediaMessage): pass

@MessageManager.decorator_register(type="animation")
class AnimationMessage(MediaMessage): pass

@MessageManager.decorator_register(type="document")
class DocumentMessage(MediaMessage): pass

@MessageManager.decorator_register(type="audio")
class AudioMessage(MediaMessage): pass

@MessageManager.decorator_register(type="contact")
class ContactMessage(BaseMessage):
    def __init__(self, content: Any, first_name: str = "", last_name: str = None, buttons: List[List[Button]] = None, effect_id: str = None):
        super().__init__(content=content, buttons=buttons, effect_id=effect_id)
        self.first_name = first_name
        self.last_name = last_name

    def send(self, scene):
        reply_markup = self._create_markup(scene) if self.buttons else None
        msg = Data.bot.send_contact(
            chat_id=scene.user.id,
            phone_number=self.content,
            first_name=self.first_name,
            last_name=self.last_name,
            reply_markup=reply_markup,
            message_effect_id=self.effect_id
        )
        self._messages_ids = [msg.message_id]

    def replace(self, scene, new_message) -> bool:
        return False

    def to_dict(self) -> Dict[str, Any]:
        json_data = super().to_dict()
        json_data['first_name'] = self.first_name
        json_data['last_name'] = self.last_name
        return json_data

    @classmethod
    def from_dict(cls, json_data):
        obj = super().from_dict(json_data)
        obj.first_name = json_data.get('first_name', "")
        obj.last_name = json_data.get('last_name', "")
        return obj


def create_dbscene(scene):
    @db_class.DbClassDecorator(list_of_non_replaceable_methodes=['__setattr__'])
    class DbScene(db_class.DbClass, scene):
        user: Data.User

        def __init__(self, user, context: Optional[Dict] = None, id: int = None, messages=None, handlers=None, call_build=True, **kwargs):
            super().__init__(_call_init=False, **kwargs)
            self.__dict__['id'] = random.randint(1, 10 ** 5) if id is None else id
            self.__dict__['user'] = user
            self.__dict__['context'] = {} if context is None else context
            self.__dict__['messages']: List[BaseMessage] = [] if messages is None else messages
            self.__dict__['handlers']: Dict[str, Any] = dict() if handlers is None else handlers

        @classmethod
        def __convert_to_db__(cls, obj, _obj_dbattribute=None, _name_attribute=None, _first_container=None, **kwargs):
            if type(obj) is Scene:
                return cls(_use_db=True, user=obj.user, context=obj.context, id=obj.id, call_build=False, **kwargs)
            if cls.__name__ == "DbScene_Scene":
                return db_attribute.db_class.DbClassConverter.convert_to_db(obj, _obj_dbattribute=_obj_dbattribute, _name_attribute=_name_attribute, _first_container=_first_container)

            return cls(_use_db=True, user=obj.user, context=obj.context,
                       id=obj.id, messages=obj.messages, handlers=obj.handlers,
                       _obj_dbattribute=_obj_dbattribute, _name_attribute=_name_attribute,
                       _first_container=_first_container, **kwargs)

        def dumps(self, _return_json=True):
            if _return_json:
                return json.dumps({'t': self.__class__.__name__, 'u': self.user.id, 'd': db_class.DbDict(self.to_dict(), _use_db=True).dumps()})
            return {'t': self.__class__.__name__, 'u': self.user.id, 'd': db_class.DbDict(self.to_dict(), _use_db=True).dumps()}

        @classmethod
        def _loads(cls, tempdata: dict, **kwargs):
            temp = db_class.DbDict.loads(tempdata['d'])
            user = Data.User.get(tempdata['u']) if tempdata['u'] else Data.EmptyUser
            return cls.__convert_to_db__(cls.from_dict(temp, user))

    DbScene.__name__ = f"DbScene_{scene.__name__}"
    db_class.DbClassManager.add_db_class(scene, DbScene)


class SceneManager(BaseManager):
    type_attribute: str = "name"

    @classmethod
    def register(cls, target_class: Type, **kwargs) -> Type:
        target_class = super().register(target_class, **kwargs)
        create_dbscene(target_class)
        return target_class

    @classmethod
    def create_scene(cls, scene_name: str, user: Data.User, context: Optional[Dict] = None):
        scene_class = cls.get(scene_name)
        return scene_class(user, context)

    @classmethod
    def decorator_register(cls, target_class=None, /, name: str = None):
        is_direct_call = target_class is not None and inspect.isclass(target_class)

        def wrapper(cls_obj: Type) -> Type:
            return cls.register(cls_obj, name=name)

        if is_direct_call:
            return wrapper(target_class)
        return wrapper


@SceneManager.decorator_register
class Scene:
    name: str = "base"

    def __init__(self, user, context: Optional[Dict] = None, id: int = None, messages: List[BaseMessage] = None, handlers: Dict[str, Any] = None, call_build=True):
        self.id = random.randint(1, 10 ** 5) if id is None else id
        self.user = user
        self.context = {} if context is None else context
        self.messages: List[BaseMessage] = [] if messages is None else messages
        self.handlers: Dict[str, Any] = dict() if handlers is None else handlers
        self._build_result = None

        if call_build:
            self._build_result = self.build()

        for i in range(len(self.messages)):
            self.messages[i].message_num = i

    def __repr__(self):
        return f"{self.name}(id={self.id}, user={self.user}, context={self.context}, messages={self.messages}, handlers={self.handlers})"

    def __get_repr__(self, Objs: set, now: int = 0):
        return f"{self.name}(" + ', '.join([f'{i}=' + (temp.__get_repr__(Objs, now + 1) if hasattr((temp := getattr(self, i)), '__get_repr__') else repr(temp)) for i in ['id', 'user', 'context', 'messages', 'handlers']]) + ")"

    def build(self) -> Optional[BaseAction]:
        """
        Build the scene content (messages, buttons, handlers, etc.).

        Returns:
            BaseAction: Action to execute instead of showing this scene (e.g., redirect to another scene).
                       Use this for simple, declarative redirects.
            None: Show this scene normally.

        Example:
            def build(self) -> Optional[BaseAction]:
                # Quick check - redirect if not authorized
                if not self.user.nameuser:
                    return SendSceneAction('registration')

                # Build scene content
                self.add_message(TextMessage("Welcome!"))
                return None
        """
        raise NotImplementedError

    def input(self, text):
        pass

    def add_message(self, message: BaseMessage):
        self.messages.append(message)

    def add_messages(self, messages: List[BaseMessage]):
        self.messages.extend(messages)

    def send(self):
        temp = self.user.previous_scene
        if not temp:
            for msg in self.messages:
                msg.send(self)
            self.user.current_scene = self
            return

        old_messages = temp.messages
        new_messages = self.messages

        n_old = len(old_messages)
        n_new = len(new_messages)

        can_replace_all = (n_old == n_new) and all(
            self._can_replace(old, new)
            for old, new in zip(old_messages, new_messages)
        )

        if can_replace_all:
            for old_msg, new_msg in zip(old_messages, new_messages):
                if not old_msg.replace(self, new_msg):
                    old_msg.delete(temp)
                    new_msg.send(self)
        else:
            for old_msg in old_messages:
                old_msg.delete(temp)
            for new_msg in new_messages:
                new_msg.send(self)

        self.user.current_scene = self

    def _can_replace(self, old_msg: BaseMessage, new_msg: BaseMessage) -> bool:
        if type(old_msg) != type(new_msg):
            return False
        if isinstance(old_msg, TextMessage):
            old_parts = (len(old_msg.content) + TextMessage.MAX_TEXT_LENGTH - 1) // TextMessage.MAX_TEXT_LENGTH
            new_parts = (len(new_msg.content) + TextMessage.MAX_TEXT_LENGTH - 1) // TextMessage.MAX_TEXT_LENGTH
            return old_parts == new_parts
        if isinstance(old_msg, MediaMessage):
            return old_msg.type == new_msg.type
        return False

    def to_dict(self) -> Dict[str, Any]:
        temp = {
            'id': self.id,
            'name': self.name,
            'messages': [msg.to_dict() for msg in self.messages],
            'handlers': self.handlers,
            'context': self.context
        }
        return temp

    @classmethod
    def from_dict(cls, json_data, user):
        if json_data['name'] == "base":
            scene_class = Scene
        else:
            scene_class = SceneManager.get(json_data['name'])
        scene = scene_class.__new__(scene_class)
        scene.id = json_data['id']
        scene.user = user
        scene.context = json_data['context']
        scene.messages = [MessageManager.restore_from_dict(msg) for msg in json_data['messages']]
        scene.handlers = json_data['handlers']
        scene._build_result = None
        scene._after_build_called = False
        for i in range(len(scene.messages)):
            scene.messages[i].message_num = i
        return scene


class EmptyUser:
    id = 0

    def __repr__(self):
        return "UserNotSet"


Data.EmptyUser = EmptyUser()
Data.EmptyScene = Scene(EmptyUser(), call_build=False)