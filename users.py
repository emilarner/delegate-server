# Phase 1 

from platform import python_version_tuple
from typing import Any

import asyncio
import uuid
import time
import json
import passlib
import passlib.hash
import psycopg2
import messages
import queue
import threading
import pyotp

from settings import *
from config import UserSettingRegulations
from config import UserSettings
from config import UserRegulations

from definitions import *

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
            "!subscriptionsto": [],
            "!subscriptionstome": [],
            "!privatesettings": [],
            "$bot": bot,
            "perms": [],
            "invisible": True,
            "asocial": False,
            "friends_only": False,
            "lone": False,
            "skeptic": False,
            "$status": UserStatuses.Online,
            "&pager": None,
            "&pager_level": 0,
            "&2fa": False
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

        # For determining when someone is 'away'
        self.last_meaningful_action: int = round(time.time())

        # Load the user state from the database.
        self.load_state()

        # Some internal settings that are extremely important
        # We will expose them through our beautiful abstraction
        self.friends: list = self.settings["!friends"]
        self.blocked: list = self.settings["!blocked"]
        self.channels: list = self.settings["!channels"]
        self.gchannels: list = self.settings["!gchannels"]
        self.friend_requests: list = self.settings["!friendreqs"]
        self.subscriptions: list = self.settings["!subscriptionstome"]
        self.subscriptionsto: list = self.settings["!subscriptionsto"]



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


    def set_settings(self, settings: dict):
        "Set settings by an object."

        self.settings.update(settings)
        self.queue_state_change()


    def add_user_subscriber(self, username: str):
        "Add a user to the subscription list."

        self.subscriptions.append(username)
        self.queue_state_change()

    
    def subscribe_to(self, username: str):
        "Subscribe to a user"

        self.users.append_user_settings(username, "!subscribedto", [self.username])
        self.subscriptionsto.append(username)
        self.queue_state_change()

    def unsubscribe_to(self, username: str):
        "Unsubscribe to a user"

        self.users.append_user_settings(username, "!subscribedto", [self.username], remove = True)
        self.subscriptionsto.append(username)
        self.queue_state_change()


    def is_subscribedto(self, username: str) -> bool:
        "Check whether subscribed to a user or not."

        return username in self.subscriptionsto
    

    def has_me_blocked(self, username: str) -> bool:
        "Am I blocked by the user or not...?"

        return self.username in self.users.get_user_settings(username)["!blocked"]


    async def special_settings_emit(self, special: dict):
        "Emit events to all subscribers when a special setting has changed."

        for subscription in set(self.subscriptions + self.friends):

            if ((user := self.users.get_user(subscription) == None)):
                continue

            await user.event("uspecial", {
                "settings": special
            })
            

    async def send_friendreq(self, other: str, msg: str):
        usrsettings: dict = self.users.get_user_settings(other)

        # Detect if such a friend request already exists
        if (other in usrsettings["!friendreqs"]):
            raise KeyError("Friend request already exists.")

        self.users.append_user_settings(other, "!friendreqs", [self.username])


        # Send the friend request event to the other user, only if they are online.
        user = None
        if ((user := self.users.get_user(other)) == None):
            return

        await user.event("friend", {
            "username": self.username,
            "message": msg
        })



    async def handle_friendreq(self, username: str, accept: bool, notify: bool):
        "Handle a friend request."

        if (username not in self.friend_requests):
            raise KeyError("Friend request does not exist")

        # If the friend request is accepted, add each other to friends list.
        if (accept):
            self.friends.append(username)
            user = self.users.append_user_settings(username, "!friends", self.username)
            self.queue_state_change()

        # If notifying is turned on, notify them of whether it was accepted or not.
        if (notify):
            user = self.users.get_user(username)
            if (user == None):
                return

            # Send the event.
            await user.event("frequest", {
                "username": self.username,
                "accepted": accept
            })

        


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

        self.tfa_cache = {

        }

        asyncio.get_event_loop().create_task(self.away_checker())


    async def away_checker(self):
        "Function which checks which users have gone away or not, dependent on settings."

        while True:
            for user in self.users:
                # If they have been inactive for a certain amount of time...
                if ((round(time.time()) - user.last_meaningful_action) 
                    >= UserSettings.UserAwayTime):

                    await self.change_user_settings(user.username, {
                        "$status": UserStatuses.Away
                    }, special = True)

                time.sleep(0.5)

            time.sleep(5 * MINUTE)

    def two_users_in_channel(self, username1, username2) -> bool:
        "Are two users within mutual channels?"

        channels1 = set(self.get_user_settings(username1)["!channels"])
        channels2 = set(self.get_user_settings(username2)["!channels"])

        return channels1.intersection(channels2) != set()


    async def change_user_settings(self, username: str, settings: dict, special = False):
        "Modify the user settings of any given user (whether they are online or not)"

        # If an online user
        if (username in self.users):
            self.users[username].set_settings(settings)
            return

        # Going to have to set it via database now.
        udb: UserDb = UserDb(self.instance, username)
        if (not udb.exists()):
            raise Exception("The user should exist???!?!?!?!?!?!?!?!")

        
        # Get existing settings so that we can modify them in place.
        sets: dict = self.get_user_settings(username)
        sets["settings"].update(settings)

        # Set them.
        udb.setsettings(sets)

        if (special):
            await self.users[username].special_settings_emit(settings)


    def append_user_settings(self, username: str, setting: str, values: list, remove: bool = False):
        "Add or remove (append negative) vector values from settings, whether the user is online or not"

        # They're online
        if (username in self.users):
            for value in values:
                if (remove):
                    self.users[username].settings[setting].remove(value)
                    continue

                self.users[username].settings[setting].append(value)

            return

        # Have to use the database now.
        udb: UserDb = UserDb(self.instance, username)
        if (not udb.exists()):
            raise Exception("Why doesn't the user exist?!?!??!?!?!?!")

        settings: dict = udb.getsettings()["settings"]

        for value in values:
            if (remove):
                settings[setting].remove(value)
                continue

            settings[setting].append(value)


    def get_user_settings(self, username: str) -> dict:
        "Get the user account settings (protocol-defined settings) whether or not they're online"

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

    
    def has_2fa(self, username: str) -> bool:
        return self.get_user_settings(username)["&2fa"]


    def verify_2fa(self, username: str, code: str) -> bool:
        udb: UserDb = UserDb(username)
        secret_key = udb.get_tfa()
        totp = pyotp.TOTP(secret_key)

        return totp.verify(code)
        


    async def add_user(self, username, connection) -> User:
        "Add a username or a connection (by username) to the pool of currently connected users."

        if (username not in self.users):
            # Delete the cached settings once the user comes online.
            if (username in self.settings_cache):
                del self.settings_cache[username]

            # Declare that they are online through the $status user setting.
            await self.change_user_settings(username, {
                "$status": UserStatuses.Online
            }, special = True)

            self.users[username] = User(username, connection, self.instance, self)
            return self.users[username]


        self.users[username].add_connection(connection)
        return self.users[username]

    def get_user(self, username) -> User:
        "Obtain a currently connected user. If they are not currently connected, return None."

        if (username not in self.users):
            return None

        return self.users[username]


    def user_exists(self, username) -> bool:
        "An efficient way to check if a username exists. "

        if (username in self.users):
            return True

        udb: UserDb = UserDb(username)
        return udb.exists()


    def user_online(self, username) -> bool:
        return (username in self.users)

    async def user_logoff(self, connection, username):
        if (username not in self.users):
            raise KeyError("User is not online??!?!?!?!?!?!?!?")

        # Remove the active connection
        self.users[username].connections.remove(connection)

        # If there are no more connections, mark the user's status as offline
        # then declare it a special setting, so that it will be sent as an event
        # to all subscribers and friends.
        if (self.users[username].connections == []):
            await self.change_user_settings(username, {
                "$status": UserStatuses.Offline
            }, special = True)
        

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

    def getsettings(self) -> str:
        "Get the user settings"

        self.database.execute("SELECT settings FROM Users WHERE username = %s;", (self.username,))
        settings = self.database.fetchone()[0]
        return settings

    def setsettings(self, settings: dict):
        "Set the user settings"

        self.database.execute("UPDATE Users SET settings = %s WHERE username = %s;", (
            json.dumps(settings),
            self.username
        ))

        self.instance.database.commit()


    def get_tfa(self) -> str:
        "Receive the 2fa secret key that the user has."

        self.database.execute("SELECT 2fa FROM Users WHERE username = %s;", (self.username,))
        return self.database.fetchone()[0]


    def update_2fa(self) -> str:
        "Add or change TOPT 2FA onto the user. Returns the secret key generated"

        tfa_secret = pyotp.random_base32()
        self.database.execute("UPDATE Users SET tfa = %s WHERE username = %s;", (
            tfa_secret,
            self.username
        ))

        self.instance.database.commit()
        return tfa_secret

