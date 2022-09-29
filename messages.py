import json
import uuid
import time
import psycopg2
import hashlib

class MessageOrigins:
    "An enumeration describing different message origins."

    Server = 0
    User = 1
    Channel = 2

class Message:
    "A container for a Delegate message"

    def __init__(self, origin, username, contents, 
                format, kind = None, created = None, uuid = None,
                channel = None, subchannel = None, to = None):
        
        self.username = username
        self.channel = channel
        self.subchannel = subchannel

        if (uuid == None):
            self.uuid: str = str(uuid.uuid4())
        else:
            self.uuid = uuid

        self.origin = origin
        
        if (created == None):
            self.created: int = round(time.time())
        else:
            self.created: int = created

        self.kind: str = kind
        self.to: str = to
        self.contents: str = contents
        self.format: dict = format

    def to_dict(self) -> dict:
        "Convert the Message object to a dictionary, in format of what the Delegate Protocol wants."

        result = {
            "uuid": self.uuid,
            "timestamp": self.created,
            "origin": self.origin,
            "type": self.kind,
            "username": self.username,
            "format": self.format,
            "content": self.contents
        }

        # If this is a channel message, add additional channel information.
        if (self.channel != None):
            result.update({
              "channel": self.channel,
              "subchannel": self.subchannel  
            })

        return result

    def __str__(self):
        return json.dumps(self.to_dict())



queryables = [
    
]

class MessagesDatabase:
    "A class which handles inputting messages into a database."

    def __init__(self, instance):
        self.instance = instance
        self.database = instance.database
        self.cursor: psycopg2.cursor = instance.cursor



    def user_message(self, msg: Message):
        "Store a user private message into the database."

        self.cursor.execute((
            "INSERT INTO UserMessages (id, kind, parties, whom, containing, creation, format)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s);"
        ), (
            msg.uuid,
            msg.kind,
            msg.username + "-" + msg.to,
            msg.username,
            msg.contents,
            msg.created,
            msg.format
        ))

        self.database.commit()

    

    def channel_message(self, event: dict):
        pass