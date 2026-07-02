Telegram menu
=========================

A toolkit for creating scene-based Telegram bots using `pyTelegramBotAPI`. This module simplifies the management of user states, menus, and database interactions using `db_attribute` as the ORM.

# Table of contents

* [Table of contents](#table-of-contents)
* [Installation](#installation)
* [Setup](#setup)
* [Usage Example](#usage-example)
* [Scenes](#scenes)
    * [Redirecting from build](#redirecting-from-build)
    * [In-memory media](#in-memory-media-memorymedia)
* [Database & User Management (ORM)](#database--user-management-orm)
    * [The User Class](#the-user-class)
    * [Using a custom User class](#using-a-custom-user-class)
    * [Using User class](#using-user-class)

# Installation

```bash
pip install tele_menu
```
or
```bash
pip install git+https://github.com/shutkanos/TeleMenu.git
```

[Back to table of contents](#table-of-contents)

# Setup

To start, you need to configure the database connection and register the bot instance.

`sql_register` accepts a `db_attribute` connector class (defaults to `MySQLConnection`) plus any positional/keyword arguments required by that connector, so the same function works for MySQL, SQLite, or any other supported connector.

```python
import telebot
from tele_menu import sql_register, bot_register
from db_attribute import connector as db_connector

token = "YOUR_BOT_TOKEN"

# 1. Initialize Database Connection

# MySQL (connector defaults to MySQLConnection, so it can be omitted)
sql_register(host="localhost", user="root", password="password", database="my_bot_db")
# PostgreSQL
sql_register(db_connector.PostgreSQLConnection, host="localhost", user="root", password="password", database="my_bot_db")

# SQLite
sql_register(db_connector.SQLiteConnection, path="database.db")
# In-memory SQLite
sql_register(db_connector.SQLiteConnection, path=":memory:")

# 2. Register Bot Instance
bot_register(telebot.TeleBot(token))
```

[Back to table of contents](#table-of-contents)

# Usage Example

Below is a complete example of a bot with a Main Menu, a Profile scene, and a Nickname change scene.

```python
import random
import traceback
import requests.exceptions
from tele_menu import (
    SceneManager, Scene, TextMessage, PhotoMessage, Button,
    SendSceneAction, CallMethodAction, Data, Log, User
)

# Assume setup (sql_register, bot_register) is done here

@SceneManager.decorator_register(name="main_menu")
class MainMenuScene(Scene):
    def build(self):
        self.add_message(TextMessage(
            content=f"Hello, {self.user.nameuser}!",
            buttons=[
                [
                    Button("Profile", action=SendSceneAction(scene_name='profile', context="Navigated from Main Menu!")),
                ],
                [
                    Button("About Bot", action=SendSceneAction(scene_name='bot_info'))
                ]
            ]
        ))

@SceneManager.decorator_register(name="profile")
class ProfileScene(Scene):
    def build(self):
        self.add_message(TextMessage(
            content=f"👤 User Profile:\n"
                    f"ID: {self.user.id}\n"
                    f"Nickname: {self.user.nameuser}\n"
                    f"{self.context if self.context else ''}",
            buttons=[
                [
                    Button("Change Nickname", action=SendSceneAction(scene_name='change_nickname')),
                    Button("Set random Nickname", action=CallMethodAction(method_name='random_nick', kwargs={'salt': '(auto)'}))
                ],
                [
                    Button("Back", action=SendSceneAction(scene_name='main_menu'))
                ]
            ]
        ))

    def random_nick(self, salt=""):
        self.user.nameuser = f"User{salt}#{random.randint(1000, 9999)}"
        # Refresh the scene to show changes
        self.user.set_scene("profile")

@SceneManager.decorator_register(name="change_nickname")
class ChangeNickname(Scene):
    def build(self):
        self.add_message(TextMessage(
            content=f"{self.context if self.context else ''}Please enter your new nickname:",
            buttons=[[Button("Cancel", action=SendSceneAction(scene_name='profile'))]]
        ))

    def input(self, text):
        if len(text) > 64:
            self.user.set_scene("change_nickname", context="Nickname length is limited to 64 characters. ")
            return

        self.user.nameuser = text
        self.user.set_scene("profile", context="Nickname changed successfully!")

@SceneManager.decorator_register(name="bot_info")
class InfoScene(Scene):
    def build(self):
        self.add_message(PhotoMessage(content=open("test_photo.png", 'rb')))
        self.add_message(TextMessage(
            content="Bot developed using tele_menu.",
            buttons=[[Button("Back", action=SendSceneAction(scene_name='main_menu'))]]
        ))

# Start Polling
while True:
    try:
        Data.bot.polling(none_stop=True, interval=0)
    except Exception as e:
        Log.error(traceback.format_exc())
        break
    except requests.exceptions.SSLError:
        pass
    else:
        break
```

[Back to table of contents](#table-of-contents)

# Scenes

## Redirecting from `build`

`Scene.build()` may return a `BaseAction` (e.g. `SendSceneAction`, `CallMethodAction`) instead of `None`. When an action is returned, it is activated immediately and the scene itself is never shown to the user. This is the way to do access checks or redirects from inside `build`, since calling `user.set_scene(...)` directly is not allowed there.

```python
@SceneManager.decorator_register(name="vip_gate")
class VipGateScene(Scene):
    def build(self):
        if self.user.rank in ("Vip", "Owner"):
            return SendSceneAction('vip_content')          # declarative redirect
        return CallMethodAction('deny_access', args=['VIP only'])

    def deny_access(self, text="Access denied"):
        # user.set_scene is required (and only allowed) in regular methods, not in build()
        self.user.set_scene('access_denied', context={'reason': text})
```

## In-memory media (`MemoryMedia`)

`MemoryMedia` stores a `BytesIO` object in a temporary, in-RAM cache (with a TTL) and can be used as the `content` of any `MediaMessage` subclass (`PhotoMessage`, `VideoMessage`, `DocumentMessage`, etc.) in place of a file path or an `OpenMedia`/`open()` object. This is useful for content generated on the fly (charts, screenshots, rendered images) that doesn't need to be written to disk.

```python
from io import BytesIO
from tele_menu import PhotoMessage, MemoryMedia

bio = BytesIO()
image.save(bio, format='PNG')   # e.g. a PIL Image
bio.seek(0)

memory_media = MemoryMedia.from_bytesio(bio, ttl_seconds=120, name='chart.png')

self.add_message(PhotoMessage(content=memory_media))
```

If the entry has expired, or was never found in storage, sending or replacing the message raises an exception.

[Back to table of contents](#table-of-contents)

# Database & User Management (ORM)

`tele_menu` uses **db_attribute** as its ORM. The base `UserBase` class inherits from `DbAttribute`; `User` is an alias that always points to whichever class is currently registered (`UserBase` by default). Changes to user attributes are automatically synchronized with the database (unless manual dump mode is enabled).

## The User Class
The internal `UserBase` class structure includes these basic fields:
- `nameuser` (str)
- `tgUsername` (str)
- `registerData` (date)
- `rank` (str)
- `ban` (bool)
- `unbanTime` (int)
- `banInfo` (dict)
- *other system fields: doDict, numMessagesPerSec, current_scene, previous_scene*

## Using a custom User class

To add your own fields (currency, level, inventory, references to other `DbAttribute`/`DbClass` tables, etc.), subclass `UserBase` and register it with `user_register(...)`.

```python
import datetime
from tele_menu import UserBase, user_register
from db_attribute.db_types import DbField

class CustomUser(UserBase):
    coins: int = DbField(default=0)
    level: int = DbField(default=1)
    inventory: dict = DbField(default_factory=dict)
    last_login: datetime.datetime = DbField(default=datetime.datetime.now)
    def __build_init__(self):
        if self.rank == "Owner":
            self.coins = 100

user_register(CustomUser)
```

Custom fields are then available on `self.user` inside any scene, just like the built-in ones:

```python
@SceneManager.decorator_register(name="shop")
class ShopScene(Scene):
    def build(self):
        self.add_message(TextMessage(
            content=f"🛍️ You have {self.user.coins} coins.\nLevel up costs 50 coins.",
            buttons=[
                [Button("⬆️ Buy level", action=CallMethodAction(method_name="buy_level"))],
                [Button("⬅️ Back", action=SendSceneAction(scene_name='main_menu'))]
            ]
        ))

    def buy_level(self):
        if self.user.coins >= 50:
            self.user.coins -= 50
            self.user.level += 1
            self.user.set_scene("shop", context="Level up successful!")
        else:
            self.user.set_scene("shop", context="Not enough coins.")
```

You can also reference other `DbAttribute`/`DbClass` tables from your custom `User` (<a href="https://github.com/shutkanos/Db-Attribute">For more information</a>)

```python
from db_attribute import DbAttribute, DbAttributeMetaclass
from db_attribute.db_types import DbField, TableType, TableObject

class CustomUser(UserBase):
    active_player: TableType("Player") = TableObject("Player", kwargs={id: -1})
    players: list = DbField(default=[])

class Player(DbAttribute, metaclass=DbAttributeMetaclass):
    __dbworkobj__ = UserBase.__dbworkobj__
    user: CustomUser
    EXP: int = 0
    inventory: list = DbField(default_factory=list)

user_register(CustomUser)
```

## Using User class

**1. Finding a User**
You can retrieve a user by ID or by searching specific fields using Python logical operators (`&`, `|` instead of `and`, `or`).

```python
# Get user by Telegram ID (Primary Key)
owner_id = 123456789
user = User.get(owner_id)

# Find user by specific attribute
found_user = User.get(User.nameuser == "JohnDoe")

# Find user with complex logic
admin_user = User.get((User.rank == "Admin") & (User.nameuser == "noname"))

# Get all users with rank 'User'
users_list = User.gets(User.rank == "User")
```

**2. Modifying Data**
Simply assign values to attributes. The ORM handles the SQL `UPDATE` operations automatically.

```python
# Update a simple field
user.nameuser = "NewName"
user.rank = "Owner"

# If the field is a mutable container (like a list or dict defined as DbField)
# modifications are tracked automatically.
```
[Back to table of contents](#table-of-contents)