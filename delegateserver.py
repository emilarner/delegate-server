import asyncio
import websockets
import json
import psycopg2
import traceback

import config
import commands

import users
import channels
import messages

from commands import DelegateCommand
from definitions import *
from util import *


# Any amateur fool can make a chat application/protocol
# But only a professional can make it scalable and efficient.


class Connection:
    def __init__(self, websocket):
        "An abstraction for a websocket client."

        self.websocket = websocket

    async def code(self, code: int, body: dict = {}):
        code_body = {
            "code": code
        }

        code_body.update(body)
        await self.websocket.send(json.dumps(code_body))





class DelegateServer:
    def __init__(self, name, port: int, tls: bool):
        self.name = name
        self.port: int = port
        self.tls: bool = tls

        self.users = users.Users(self)


        try:
            self.database = psycopg2.connect(
                host = "/tmp",
                dbname = config.Database.Name, 
                user = config.Database.Username, 
                password = config.Database.Password
            )

        except Exception as error:
            eprint(f"Error connecting to database: {error}")


        self.cursor = self.database.cursor()
        
        # Create the databases if they do not already exist
        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS Users"
            "(username TEXT, created INTEGER, settings TEXT, passhash TEXT, tfa TEXT DEFAULT NULL);"
        ))

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS Channels"
            "(channel TEXT, created INTEGER, settings TEXT);"
        ))

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS ChannelQueryables"
            "(channel TEXT, queryable TEXT, value TEXT); "
        ))

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS ChannelMessages"
            "(id UUID, kind TEXT, channel TEXT, subchannel TEXT, whom TEXT, containing TEXT," 
            "creation INTEGER, format TEXT);"
        ))

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS UserMessages"
            "(id UUID, kind TEXT, parties TEXT, whom TEXT, containing TEXT," 
            "creation INTEGER, format TEXT);"
        ))
        
        self.database.commit()
        self.messages: messages.MessagesDatabase = messages.MessagesDatabase(self)

        # Server constants that expose information about the server to ALL clients.
        self.constants = {
            # Server
            "name": config.ServerInfo.Name,
            "description": config.ServerInfo.Description,
            "version": config.ServerInfo.Version,
            "admin": config.ServerInfo.Admin,
            "password": config.ServerPassword.On,
            "msglen": config.ServerRegulations.MaxMessageLength,
            "timeout": config.ServerRegulations.Timeout,
            
            # Settings

            "freesettinglen"

            # User
            "username_len": config.UserRegulations.Length,
            "username_regex": config.UserRegulations.Regex,
            "password_len": config.UserRegulations.PasswordLength
        }



    async def handle(self, ws):
        # Make the Connection abstraction
        conn: Connection = Connection(ws)

        # Store the username and User object of the request
        username = None
        user = None


        
        # Websockets has an abstraction for messages, so let's go through each of them
        async for message in ws:
            try:
                command: DelegateCommand = DelegateCommand.from_json(
                    conn, 
                    self, 
                    message,
                    user
                )


                if (command.command in commands.primitive_commands):
                    # Initial sign in
                    if (command.command == "user"):
                        if (user != None):
                            await conn.code(UserCodes.Errors.AlreadySignedIn)
                            continue
                        
                        # User sign in failed.
                        if (not await commands.initial_user_signin(command)):
                            continue

                        # Add it to the collection of currently connected users
                        # Then, give this connection a connected user. 
                        user = self.users.add_user(command.body["username"], conn)
                        username = command.body["username"]

                        await conn.code(UserCodes.Success.Signin)

                        

                    
                    # User registration
                    if (command.command == "uregister"):
                        # User registration has failed.
                        if (not await commands.user_register(command)):
                            continue

                        await conn.code(UserCodes.Success.Register)
                    
                    continue



                # Command was not found
                if (command.command not in commands.commands_list):
                    await conn.code(CommandCodes.NotFound)
                    continue

                # The user must be signed in to use this command.
                if (user == None):
                    await conn.code(CommandCodes.NotSignedIn)
                    continue

                # Call the command handler and pass in the DelegateCommand object instance.
                await commands.commands_list[command.command](command)
                    

            # When JSON was likely not sent or was malformed (for some reason?)
            except json.JSONDecodeError as je:
                await conn.code(ServerCodes.Error.JSONError)

            # When an unknown or general server exception was thrown
            except Exception as e:
                await conn.code(ServerCodes.Error.ServerException, {
                    "exception": type(e).__name__,
                    "message": str(e)
                })

                eprint("A server exception occured while handling a command: ")
                eprint(traceback.format_exc())


    async def main_server(self):
        async with websockets.serve(self.handle, "0.0.0.0", self.port):
            await asyncio.Future()

    def start(self):
        asyncio.run(self.main_server())
