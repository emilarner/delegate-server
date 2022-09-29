import uuid
import json
import psycopg2

class EventOrigins:
    Server = 0
    User = 1
    Channel = 2

class Event:
    def __init__(self, origin: int, timestamp: int, name: str, body: dict,
        parties: str = None,
        channel: str = None,
        subchannel: str = None,
        uuid: str = None
    ):
        self.parties = parties

        self.channel = channel
        self.subchannel = subchannel

        self.origin: int = origin
        self.name: str = name
        self.body: dict = body

        if (uuid != None):
            self.uuid: str = uuid
        else:
            self.uuid: str = str(uuid.uuid4())

    
class EventDatabase:

    def __init__(self, instance):
        self.instance = instance
        self.database = self.instance.database
        self.cursor: psycopg2.cursor = self.instance.cursor

    def user_event(self, e: Event):
        self.cursor.execute((
            "INSERT INTO UserEvents (id, event, parties,"
            "creation, contents) VALUES (%s, %s, %s, %s, %s);"
        ), (
            e.uuid,
            e.name,
            e.parties,
            e.timestamp,
            json.dumps(e.body)
        ))

        self.database.commit()

