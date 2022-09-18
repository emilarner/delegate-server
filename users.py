from typing import Any
from unittest.util import strclass
import uuid
import time
import json
import passlib
import passlib.hash
import psycopg2
import messages
import queue
import threading

from settings import *
from config import UserSettingRegulations

class UserStatuses:
    Online = 0
    Away = 1
    Offline = 2

# Store setting regulations within an easily accessible dictionary
setting_infos = {
    "name": SettingInfo(str, UserSettingRegulations.NameLength, True),
    "dnd": SettingInfo(bool, None, True),
    "status_text": SettingInfo(str, UserSettingRegulations.StatusLength, True),
    "description": SettingInfo(str, UserSettingRegulations.DescriptionLength, True),
    "avatar": SettingInfo(str, UserSettingRegulations.AvatarLength, True),
    "invisible": SettingInfo(bool, None, False),
    "asocial": SettingInfo(bool, None, False),
    "friends_only": SettingInfo(bool, None, False),
    "lone": SettingInfo(bool, None, False),
    "skeptic": SettingInfo(bool, None, False),
    "&pager": SettingInfo(str, UserSettingRegulations.PagerLength, False),
    "&pager_level": SettingInfo(int, None, False)
}


def generate_user_state(creation: int, bot: bool) -> dict:
    default_state = {
        "subscriptions": [],
        "settings": {
            "name": None,
            "dnd": False,
            "status_text": None,
            "description": None,
            "avatar": None,
            "$creation": creation,
            "!channels": [],
            "!gchannels": [],
            "!blocked": [],
            "!friends": [],
            "!friendreqs": [],
            "$bot": bot,
            "perms": [],
            "invisible": True,
            "asocial": False,
            "friends_only": False,
            "lone": False,
            "skeptic": False,
            "$status": UserStatuses.Online,
            "&pager": None,
            "&pager_level": 0
        }
    }

    return default_state


def user_database_queue(q: queue.Queue):
    "Handle users that need their state written to the database"

    while (user := q.get()) != None:
        u: User = user
        u.queued = False

        # Store the state into the database
        u.udb.setsettings(u.get_state())

        # Wait 
        time.sleep(.5)



class User:
    def __init__(self, username, connection, instance, users):
        self.instance = instance
        self.username: str = username
        self.connection = connection
        self.users: Users = users
        self.udb: UserDb = UserDb(self.instance, self.username)

        # Whether or not to continually add to the database queue.
        self.queued: bool = False

        # Here is a list of active connections for live events.
        self.connections: list = [
            connection
        ]

        # This is where all user settings will be stored.
        self.settings: dict = {

        }

        # What users are receiving their events of special setting updates?
        # The protocol prohibits the user from knowing who. 
        self.subscriptions = [

        ]

        # Some internal settings that are extremely important
        # We will expose them through our beautiful abstraction
        self.friends: list = self.settings["!friends"]
        self.blocked: list = self.settings["!blocked"]
        self.channels: list = self.settings["!channels"]
        self.gchannels: list = self.settings["!gchannels"]
        self.friend_requests: list = self.settings["!friendreqs"]

        # Load the user state from the database.
        self.load_state()


    def queue_state_change(self):
        if (not self.queued):
            self.queued = True
            self.users.userdb_queue.put(self)


    def load_state(self):
        "Load the user state from the database store."

        # Because I am lazy, I named the database method .getsettings()
        # This does more than get actual Delegate Protocol user settings.
        # For example, it will also get user subscriptions.

        udb = UserDb(self.instance, self.username)
        self.fields = json.loads(udb.getsettings())

        self.settings = self.fields["settings"]
        self.subscriptions = self.fields["subscriptions"]

    def set_setting(self, setting: str, value: Any):
        "Change a user setting and push a database write onto the queue."

        self.settings[setting] = value
        self.queue_state_change()



    def get_setting(self, setting: str) -> Any:
        "Obtain a user setting. If it does not exist, return None (null in JSON)."

        if (setting not in self.settings):
            return None

        return self.settings[setting]

    def add_connection(self, connection):
        "Adds a connection to the pool of connections already associated with this user."

        self.connections.append(connection)

    async def sendall(self, msg):
        "Send a WebSockets message to all parties. [DO NOT USE ALONE!]"

        for conn in self.connections:
            await conn.websocket.send(msg)

    async def event(self, name, body, connid = None):
        "Send an event to all parties."

        result = {
            "event": name,
        }
        
        result.update(body)

        if (connid == None):
            await self.sendall(json.dumps(result))

        else:
            await self.connections[connid].send(json.dumps(result))


    async def send_message(self, to, message: messages.Message):
        "Send a private message to another connected user."

        await to.event("message", message.to_dict())


    def get_state(self) -> dict:
        "Get the user state as a dictionary. Useful for storing in a database somewhere!"

        result = {
            "subscriptions": self.subscriptions,
            "settings": self.settings
        }

        return result

    def __str__(self) -> str:
        "Convert User object to JSON state that goes into the database"

        return json.dumps(self.get_state())




class Users:
    def __init__(self, instance):
        self.instance = instance
        self.users: dict = {}

        # Perhaps a bit inefficient
        self.userdb_queue: queue.Queue = queue.Queue()
        self.userdb_queue_t = threading.Thread(
            target = user_database_queue, 
            args = (self.userdb_queue,)
        ).start()

        self.settings_cache = {

        }


    def get_user_settings(self, username: str) -> dict:
        # An online user
        if (username in self.users):
            return self.users[username].settings

        # Returned cached user settings state.
        if (username in self.settings_cache):
            return self.settings_cache[username]

        # Gotta ask the database, now. 
        u: UserDb = UserDb(self.instance, username)

        if (not u.exists()):
            raise Exception("Uhh... the user does not exist????")

        self.settings_cache[username] = u.getsettings()["settings"]
        return self.settings_cache[username]

    


    def add_user(self, username, connection) -> User:
        "Add a username or a connection (by username) to the pool of currently connected users."

        if (username not in self.users):
            if (username in self.settings_cache):
                del self.settings_cache[username]

            self.users[username] = User(username, connection, self.instance, self)
            return self.users[username]

        self.users[username].add_connection(connection)
        return self.users[username]

    def get_user(self, username) -> User:
        "Obtain a currently connected user. If they are not currently connected, return None."

        if (username not in self.users):
            return None

        return self.users[username]




class UserDb:
    def __init__(self, instance, username: str):
        self.instance = instance
        self.username: str = username
        self.database: psycopg2.cursor = instance.cursor

    def exists(self) -> bool:
        "Does the user exist?"

        self.database.execute("SELECT username FROM Users WHERE username = %s;", (self.username,))
        return self.database.fetchone() != None

    def register(self, password, bot = False):
        "Register the username"

        creation = round(time.time())

        self.database.execute(
            "INSERT INTO Users (username, created, settings, passhash) VALUES (%s, %s, %s, %s);",
            (
                self.username,
                creation,
                json.dumps(generate_user_state(creation, bot)),
                passlib.hash.argon2.hash(password)
            )
        )

        self.instance.database.commit()
    
    def verify(self, password, tfa = ""):
        "Verify the login credentials"

        self.database.execute("SELECT passhash FROM Users WHERE username = %s;", (self.username,))
        passhash = self.database.fetchone()[0]

        return passlib.hash.argon2.verify(password, passhash)

    def getsettings(self) -> dict:
        "Get the user settings"

        self.database.execute("SELECT settings FROM Users WHERE username = %s;", (self.username,))
        settings = json.loads(self.database.fetchone()[0])

    def setsettings(self, settings: dict):
        "Set the user settings"

        self.database.execute("UPDATE Users SET settings = %s WHERE username = %s;", (
            json.dumps(settings),
            self.username
        ))

        self.instance.database.commit()

