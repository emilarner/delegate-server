import asyncio
import websockets
import websockets.exceptions as wes
import json
import psycopg2
import traceback

import config
import commands

import users
import channels
import messages
import events

from commands import DelegateCommand
from definitions import *
from util import *


# Any amateur fool can make a chat application/protocol
# But only a professional can make it scalable and efficient.
# We are incapable of making scalable and efficient software.


class Connection:
    def __init__(self, websocket):
        "An abstraction for a websocket client."

        self.websocket = websocket

    #def _identity(self) -> str:
    #    return self.websocket.remote_address

    #def __eq__(self, another):
    #    return self._identity == another._identity

    async def code(self, code: int, body: dict = {}):
        "Issue a response code to the socket in question."

        code_body = {
            "code": code
        }

        code_body.update(body)
        await self.websocket.send(json.dumps(code_body))


    async def close(self):
        "Close the socket"

        await self.websocket.close()




class DelegateServer:
    def __init__(self, hostip, port: int, tls: bool):
        self.hostip = hostip
        self.port: int = port
        self.tls: bool = tls


        try:
            self.database = psycopg2.connect(
                host = config.Database.Host,
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
            "(channel TEXT, created INTEGER, state TEXT);"
        ))

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS ChannelQueryables"
            "(channel TEXT, queryable TEXT, value_str TEXT, value_int INTEGER, value_bool BOOLEAN); "
        ))


        # for later i guess
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

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS UserEvents (id UUID, event TEXT, parties TEXT,"
            "contents TEXT);"
        ))

        self.cursor.execute((
            "CREATE TABLE IF NOT EXISTS UserNotifications (id UUID, event TEXT, body TEXT,"
            "origin TEXT, creation INTEGER, read BOOLEAN);"
        ))

        
        # Save the database table creations
        self.database.commit()

        
        self.messages: messages.MessagesDatabase = messages.MessagesDatabase(self)
        self.events: events.EventDatabase = events.EventDatabase(self)

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

            "freesettinglen": 20,

            # User
            "username_len": config.UserRegulations.Length,
            "username_regex": config.UserRegulations.Regex,
            "password_len": config.UserRegulations.PasswordLength
        }

        self.users = users.Users(self)
        self.channels = channels.Channels(self)



    async def handle(self, ws):
        # Make the Connection abstraction
        conn: Connection = Connection(ws)

        # Store the username and User object of the request
        username = None
        user = None
        authenticated = False
        event_listener = False


        
        # Websockets has an abstraction for messages, so let's go through each of them
        try:
            async for message in ws:
                try:
                    command: DelegateCommand = DelegateCommand.from_json(
                        conn, 
                        self, 
                        message,
                        user
                    )

                    # Quit the connection and logoff if signed in.
                    if (command.command == "quit"):
                        if (username != None):
                            await self.users.user_logoff(conn, username)

                        await conn.close()
                        break

                    # If a password is required, make sure they can't run any commands
                    # besides 'authenticate' and 'quit'
                    if (config.ServerPassword.On and not authenticated):
                        if (command.command != "authenticate"):
                            await conn.code(ServerCodes.Error.PasswordRequired)
                            continue

                    
                    # Server authentication command
                    if (command.command == "authenticate"):
                        # The password was incorrect, so alert them of that and continue.
                        if (not commands.authenticate_command(command)):
                            await conn.code(ServerCodes.Error.Password)
                            continue
                        
                        # Authentication was a success
                        authenticated = True
                        continue



                    # If the command does not require a preexisting user sign in.
                    if (command.command in commands.primitive_commands):
                        # Initial sign in
                        if (command.command == "user"):
                            try:
                                event: bool = command.body["event"]

                            except KeyError:
                                await conn.code(CommandCodes.ArgsMissing)
                                continue

                            if (user != None):
                                await conn.code(UserCodes.Errors.AlreadySignedIn)
                                continue
                            
                            # User sign in failed.
                            if (not await commands.initial_user_signin(command)):
                                continue

                            # Add it to the collection of currently connected users
                            # Then, give this connection a connected user. 
                            user = await self.users.add_user(
                                command.body["username"], 
                                conn,
                                event = event
                            )

                            username = command.body["username"]

                            await conn.code(UserCodes.Success.Signin)

                            

                        
                        # User registration
                        if (command.command == "uregister"):
                            # User registration has failed.
                            if (not await commands.user_register(command)):
                                continue

                            await conn.code(UserCodes.Success.Register)
                        
                        continue

                    # Logout
                    if (command.command == "logout"):
                        if (user == None):
                            await conn.code(CommandCodes.NotSignedIn)
                            continue

                        await self.users.user_logoff(conn, username, consensual = True)
                        user = None
                        username = None
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
        
        except (wes.WebSocketException, wes.ConnectionClosedError, asyncio.exceptions.IncompleteReadError):
            if (user != None):
                await self.users.user_logoff(conn, user.username, event = event_listener)

            return


    async def main_server(self):
        async with websockets.serve(self.handle, self.hostip, self.port):
            await asyncio.Future()

    def start(self):
        asyncio.run(self.main_server())
