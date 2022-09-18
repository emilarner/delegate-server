import json
import time
import psycopg2


from definitions import *
from util import *


class Channel:
    "A Delegate channel"

    def __init__(self, name):
        self.name = name
        
        self.data = {

        }

        self.subchannels = {}

        self.roles = {
            "owner": [
                None
            ],

            "default": [
                None
            ]
        }


        self.banned = []
        self.settings = {}
        
        self.users = {
            "example": {
                "role": "default",
                "settings": {
                    "creation": 22323232
                },
            }
        }


    def perms(self, username):
        return self.roles[self.users[username]["role"]]


        

class ChannelDb:
    def __init__(self, instance, name):
        self.name = name
        self.instance = instance
        self.database: psycopg2.cursor = instance.cursor

    def exists(self) -> bool:
        "Returns whether the channel is registered or not [MUST BE, ACCORDING TO PROTOCOL]"

        self.database.execute("SELECT channel FROM Channels WHERE channel = %s;", (self.name,))
        return self.database.fetchone() != None

    def getsettings(self) -> dict:
        "Get the settings of the channel and return them as a dictionary object."

        self.database.execute("SELECT settings FROM Channels WHERE channel = %s;", (self.name,))
        return json.loads(self.database.fetchone()[0])

    def gettime(self) -> int:
        "Get the creation time of the channel."

        self.database.execute("SELECT created FROM Channels WHERE channel = %s;", (self.name,))
        return int(self.database.fetchone()[0])


    


