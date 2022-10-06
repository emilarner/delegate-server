import json
import time
import psycopg2
import users


from definitions import *
from util import *
from config import *

def generate_user_field(role = "default") -> dict:
    result = {
        "role": role,
        "settings": {
            "$join": round(time.time()),
            "nickname": None,
            "~labels": [],
            "image": None,
            "labels": [],
            "$sent": 0,
            "$level": 0
        }
    }

    return result

def generate_channel_settings(created: int, owner: str, group: bool) -> dict:
    default_channel_settings = {
        "$creation": created,
        "$owner": owner,
        "$roles": {
            "owner": [
                None
            ],

            "default": [
                [ChannelPermissions.Talk, ChannelPermissions.Read]
            ]
        },
        "$order": ["owner", "default"],
        "$banned": {},
        "$muted": {},
        "$subchannels": {
            "main": generate_subchannel_state()
        },
        "$userno": 1,
        "$userlist": [owner],
        "$group": group,
        "name": None,
        "description": None,
        "image": None,
        "categories": {},
        "default_role": "default",
        "auto_roles": {},
        "auto_labels": {},
        "invisible": True,
        "lockdown": False,
        "invite": False,
        "password": False,
        "tor": True,
        "captcha": True,
        "captcha_count": 2,
        "tor_captcha_count": 5,
        "concealed_captcha_count": 3,
        "join_message": ChannelDefaults.JoinMessage,
        "leave_message": ChannelDefaults.LeaveMessage
    }

    return default_channel_settings


def generate_subchannel_state():
    result = {
        "$creation": round(time.time()),
        "$roles": {},
        "description": None,
        "image": None,
        "private": False,
        "allowed_users": [],
        "allowed_roles": []
    }

    return result

def generate_default_channel_state(settings: dict, owner: str) -> dict:
    result = {
        "auxiliary": {
            "users": {owner: generate_user_field(role = "owner")}
        },
        "settings": settings
    }

    return result



class BannedEntity:
    def __init__(self, username, ip):
        self.username = username
        self.ip = ip

    def to_dict(self) -> dict:
        return {"username": self.username, "ip": self.ip}

    def __str__(self) -> str:
        return json.dumps(self.to_dict())

class ChannelPermissions:
    Talk = "talk"
    Read = "read"
    Remove = "remove"
    Subchannel = "subchannel"
    Metadata = "metadata"
    Set = "set"
    Kick = "kick"
    Ban = "ban"
    Mute = "mute"
    Role = "role"
    Invite = "invite"
    Password = "password"
    Order = "order"
    Vote = "vote"
    Cast = "cast"
    Summon = "summon"
    Admin = "admin"


class Channel:
    "A Delegate channel"

    def __init__(self, instance, name, state: dict, channels, users):
        self.instance = instance
        self.usersinst: users.Users = instance.users

        self.name = name
        self.channels = channels
        self.usersinst = users

        # Information about the channel not under
        # the channel settings, as specified by the
        # protocol.
        self.auxiliary = state["auxiliary"]

        # Information about the users in the channel.
        # This stays private to the outside. Not accessible via settings.
        self.users = self.auxiliary["users"]


        # All of the useful channel settings that are
        # publicly accessible through the public setting
        # abstraction.
        self.order: list = self.settings["$order"]
        self.roles: list = self.settings["$roles"]
        self.userlist: list = self.settings["$userlist"]
        self.userno: int = self.settings["$userno"]
        self.banned = self.settings["$banned"]
        self.muted = self.settings["$muted"]
        
        self.subchannels = self.settings["$subchannels"]

        self.settings = state["settings"]

        self.cdb: ChannelDb = ChannelDb(instance, name)
        

    def form_event(self, event, channel, body) -> dict:
        result = {
            "event": event,
            "channel": channel
        }.update(body)

        return result


    async def broadcast_event(self, event: str, body: dict, subchannel: str = None, user: str = None):
        "Send an event to people/a person."
        
        # Automatically add the channel as a field in the body of the event.
        body.update({"channel": self.name})

        # Sending it to members of a subchannel only.
        if (subchannel != None):
            body.update({"subchannel": subchannel})
            return

        # Sending it to ONE user.
        if (user != None):
            pass
            return

        # Send it to every user in every channel.
        for usr in self.userlist:
            await self.usersinst.send_event(usr, event, body)


    async def delete_channel(self):
        "Delete the channel. Permanently."

        self.cdb.delete()
        await self.broadcast_event("cdeleted")
        self.channels.unload_channel(self.name)







    async def add_subchannel(self, name):
        "Add a subchannel to the channel."

        self.subchannels[name] = generate_subchannel_state()
        await self.broadcast_event("subchannel", {
            "subchannel": name,
            "status": "created"
        })

    async def remove_user(self, username: str, message: str = None, circumstance: str = "normal"):
        "Remove a user from the channel."

        del self.users[username]
        await self.broadcast_event("leave", {
            "username": username,
            "message": message,
            "circumstance": circumstance
        })
    
    async def dup_subchannel(self, old, new):
        "Duplicate an existing subchannel to a new one."

        self.subchannels[new] = self.subchannels[old].copy()
        await self.broadcast_event("subchannel", {
            "subchannel": new,
            "status": "created"
        })

    async def add_user(self, username: str, message: str = None, role = "default"):
        "Add a user to the channel, giving them data."

        self.users[username] = generate_user_field(username, role = role)
        await self.broadcast_event("join", {
            "username": username,
            "message": message
        })




    def order_roles(self, username: str, role_order: list):
        """Change the ordering hierarchy of the roles, depending on a user's perspective.
        Raises KeyError when not all roles are provided in the new role order.
        Raises PermissionError when the role order is done insubordinately.
        """

        # While the order of the new and old role orders may be different
        # they must contain the same elements. Sets can achieve this.
        # Two sets are equal if they contain the same elements.
        # Python sets are so true to mathematical sets, it's quite fascinating...
        
        if (set(role_order) != set(self.order)):
            raise KeyError("One role is missing from the role_order")

        role: str = self.get_role(username)
        index: int = self.order.index(role)

        # Find the value and indices of roles that are at or below (more powerful)
        # the current role of the user.
        immutable_roles = filter(
            lambda x: x[0] <= index, 
            enumerate(self.order)
        )

        # Go through each index and role.
        for immrole in immutable_roles:
            # If the index has changed in the new role order for the untouchable roles
            # yield a permission's error.
            if (immrole[0] != role_order.index(immrole[1])):
                raise PermissionError("The ordering of your role and higher roles has been changed.")


        # It was a success: the role order has been changed.
        self.order = role_order


    def get_role(self, username) -> str:
        "Return the string role name that a username has."

        return self.users[username]["role"]

    def has_permission(self, username: str, perm: str, subchannel: str = None) -> bool:
        "Return whether a user has permission to do something or not."

        # Owner always has every permission
        if (self.get_role(username) == "owner"):
            return True

        # Get user channel-wide permissions.
        perms = self.perms(username)

        # You can laugh, but I am not changing the name of this variable.
        sperms = [] 
        
        # Get subchannel permissions if a subchannel is given to us.
        if (subchannel != None):
            sperms = self.subchannels[subchannel]["roles"][self.get_role(username)]

        # "admin" permissions always has every permission, except for channel deletion.
        if (ChannelPermissions.Admin in perms or ChannelPermissions.Admin in sperms):
            return True


        return (perm in perms) or (perm in sperms)


    def can_moderate(self, username1, username2) -> bool:
        "Can username1 moderate username2?"

        order1 = self.order.index(self.get_role(username1))
        order2 = self.order.index(self.get_role(username2))

        return order1 < order2

    def perms(self, username) -> list:
        "Return all permissions that a given user has."

        return self.roles[self.get_role(username)]


        

class Channels:
    def __init__(self, instance):
        self.channels = {}
        self.instance = instance

        self.database = self.instance.database
        self.cursor = self.instance.cursor

    
    def unload_channel(self, channel: str):
        "Unload a channel object from memory by its string name."

        del self.channels[channel]



    def add_channel(self, channel: str):
        "Add a channel from the database into memory."

        cdb = ChannelDb(self.instance, channel)
        self.channels[channel] = Channel(channel, cdb.getstate())

    def get_channel(self, channel: str) -> Channel:
        "Get a channel--if it isn't loaded into memory, do so."

        if (channel not in self.channels):
            self.add_channel(channel)

        return self.channels[channel]

    def channel_exists(self, channel: str) -> bool:
        "Efficient way to determine whether the given channel exists or not"

        if (channel in self.channels):
            return True

        cdb = ChannelDb(self.instance, channel)
        return cdb.exists()





class ChannelDb:
    def __init__(self, instance, name):
        self.name = name
        self.instance = instance
        self.database: psycopg2.cursor = instance.cursor

    def exists(self) -> bool:
        "Returns whether the channel is registered or not [MUST BE, ACCORDING TO PROTOCOL]"

        self.database.execute("SELECT channel FROM Channels WHERE channel = %s;", (self.name,))
        return self.database.fetchone() != None

    def getstate(self) -> dict:
        "Get the state of the channel and return it as a dictionary object."

        self.database.execute("SELECT state FROM Channels WHERE channel = %s;", (self.name,))
        return json.loads(self.database.fetchone()[0])


    def delete(self):
        "Delete the channel from the database"

        self.database.execute("DELETE FROM Channels WHERE channel = %s;", (self.name,))
        self.instance.database.commit()

    def register(self, username: str, group: bool):
        "Register a channel"

        created = round(time.time())

        self.database.execute("INSERT INTO Channels (channel, created, state) VALUES (%s, %s, %s);", (
            self.name,
            created,
            generate_default_channel_state(generate_channel_settings(created, username, group))
        ))

        self.instance.database.commit()

    def setstate(self, settings):
        "Set the state of the channel"

        self.database.execute("UPDATE Channels SET state = %s WHERE channel = %s;", (
            json.dumps(settings),
            self.name
        ))

        self.instance.database.commit()

    def gettime(self) -> int:
        "Get the creation time of the channel."

        self.database.execute("SELECT created FROM Channels WHERE channel = %s;", (self.name,))
        return int(self.database.fetchone()[0])


    


