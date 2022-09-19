import json

import users
import config
import messages

from settings import *
from util import *
from definitions import *

class DelegateCommand:
    def __init__(self, connection, instance, command, body, user):
        self.connection = connection

        self.instance = instance
        self.messages: messages.MessagesDatabase = self.instance.messages

        self.command: str = command
        self.body: dict = body
        self.user = user

    @staticmethod
    def from_json(connection, instance, ccode, user):
        "Loads a command from raw JSON data."
        
        code = json.loads(ccode)
        return DelegateCommand(connection, instance, code["command"], code, user)


async def initial_user_signin(command: DelegateCommand) -> bool:
    try:
        username = command.body["username"]
        password = command.body["password"]

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return False


    # 2FA is not implemented yet.
    if ("2fa" in command.body):
        await command.connection.code(ServerCodes.Error.NotImplemented)
        return False

    udb = users.UserDb(command.instance, username)

    # If the user is not registered.
    if (not udb.exists()):
        await command.connection.code(UserCodes.Errors.UsernameNoent)
        return False

    # Incorrect password
    if (not udb.verify(password)):
        await command.connection.code(UserCodes.Errors.PasswordIncorrect)
        return False

    return True


async def quit_command(command: DelegateCommand):
    pass

async def ping_command(command: DelegateCommand):
    pass

async def get_command(command: DelegateCommand):
    pass

async def authenticate_command(command: DelegateCommand):
    pass

async def notifications_command(command: DelegateCommand):
    pass

async def reportmsg_command(command: DelegateCommand):
    pass



async def user_register(command: DelegateCommand) -> bool:
    try:
        username = command.body["username"]
        password = command.body["password"]

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return False


    # Username is not within the server's length constraints.
    if (not within_range(len(username), *config.UserRegulations.Length)):
        await command.connection.code(UserCodes.Errors.UsernameLength)
        return False

    # Username is not within the server's REGEX requirements.
    if (not regex_test(config.UserRegulations.Regex, username)):
        await command.connection.code(UserCodes.Errors.UsernameRegex)
        return False

    # Password not within the length requirements.
    if (not within_range(len(password), *config.UserRegulations.PasswordLength)):
        await command.connection.code(UserCodes.Errors.WeakPassword)
        return False

    udb = users.UserDb(command.instance, username)
    
    # User already exists; cannot register them.
    if (udb.exists()):
        await command.connection.code(UserCodes.Errors.UsernameExists)
        return False


    udb.register(password)
    
    return True




async def usend_command(command: DelegateCommand):
    try:
        to = command.body["username"]
        contents = command.body["message"]
        kind = command.body["type"] if "type" in command.body else None
        format = command.body["format"] if "format" in command.body else None

        checking = [to, contents, kind, format]
        for check in checking:
            # Every single argument above must be type 'str'
            if (not isinstance(check, str)):
                await command.connection.code(CommandCodes.InvalidTypes)
                return

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return


    udb = users.UserDb(command.instance, to)

    # User does not exist!!11111
    if (not udb.exists()):
        await command.connection.code(UserCodes.Errors.UsernameNoent)
        return

    # Make a message object
    msg = messages.Message(
        messages.MessageOrigins.User,
        command.user.username,
        contents,
        format,
        kind = kind,
        to = to
    )

    # Send a live event to the other user, if they are online.
    if ((to_user := command.instance.users.get_user(to)) != None):
        await command.user.send_message(to_user, msg)

    # Store the message in the database.
    command.messages.user_message(msg)


async def get_command(command: DelegateCommand):
    try:
        settings: list = command.body["settings"]

        # Settings must be an array.
        if (not isinstance(settings, list)):
            await command.connection.code(CommandCodes.InvalidTypes)
            return

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return

    
    result = {

    }

    for setting in settings:
        # Settings which do not exist are made to be None.
        if (setting not in command.instance.constants):
            result[setting] = None

        result[setting] = command.instance.constants[setting]

    await command.connection.code(ServerCodes.Success.Get, {
        "settings": result
    })

async def uset_command(command: DelegateCommand):
    try:
        settings: dict = command.body["settings"]

        # Must be a dictionary.
        if (not isinstance(settings, dict)):
            await command.connection.code(CommandCodes.InvalidTypes)
            return

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return

    special_settings = {

    }

    for key, value in settings.items():
        key: str = key

        # Trying to modify an immutable setting.
        if (key[0] in [SettingQualifiers.Immutable, SettingQualifiers.ImmutablePrivate]):
            await command.connection.code(SettingCodes.Errors.Immutable)
            return

        # A regulated user setting
        if (key in users.setting_infos):
            info: SettingInfo = users.setting_infos[key]

            # Detect error in type.
            if (not isinstance(value, info.kind)):
                await command.connection.code(SettingCodes.Errors.Type, {
                    "setting": key,
                    "given": type(value).__name__,
                    "required": info.kind.__name__
                })

                return

            # Regulate a value's range. (Must be str or int)
            if (info.range != None):
                # This can be simplified. But am I going to do it?
                # Calculate range based upon string length
                if (isinstance(value, str)):
                    if (not within_range(len(value), *info.range)):
                        await command.connection.code(SettingCodes.Errors.Range, {
                            "setting": key,
                            "range": info.range
                        })

                # Calculate range based upon integer value
                if (isinstance(value, int)):
                    if (not within_range(value, *info.range)):
                        await command.connection.code(SettingCodes.Errors.Range, {
                            "setting": key,
                            "range": info.range
                        })

            # Add this to the list of special settings we need to send events for.
            if (info.special):
                special_settings[key] = value


            command.user.set_setting(key, value)


        
    
async def uget_command(command: DelegateCommand):
    try:
        settings: list = command.body["settings"]
        username: str = command.body["username"]


        # Must be specific type.
        if (not isinstance(settings, list)):
            await command.conn.code(CommandCodes.InvalidTypes)
            return

        if (not isinstance(username, str)):
            await command.conn.code(CommandCodes.InvalidTypes)
            return

    except KeyError:
        await command.conn.code(CommandCodes.ArgsMissing)
        return

    
    result = {

    }

    # Obtain the settings of the user whether or not they are online.
    # Do it in a way such that it is cached, hence the long function below.
    users_settings = command.instance.users.get_user_settings(
        command.user.username if username == None else username
    )

    for setting in settings:
        if (username != None):

            # If not operating on themselves and trying to access private settings
            # disallow them from doing so, by yielding an error.
            # Stating which settings were private is NOT needed, since it is readily apparent.
            if (setting[0] in [SettingQualifiers.Private, SettingQualifiers.ImmutablePrivate]):
                await command.connection.code(SettingCodes.Errors.Private)
                return

        # Settings that do not exist are going to be None/null
        if (setting not in users_settings):
            result[setting] = None
            continue
        
        # Store our setting value in our results
        result[setting] = users_settings[setting]


    # Send back the settings that were received.
    await command.connection.code(UserCodes.Success.Settings, {
        "username": username,
        "settings": result
    })


# Deprecated
async def upriv_command(command: DelegateCommand):
    pass




async def frequest_command(command: DelegateCommand):
    pass

async def friend_command(command: DelegateCommand):
    pass

async def usubscribe_command(command: DelegateCommand):
    pass

async def umsgquery_command(command: DelegateCommand):
    pass

async def ueventquery_command(command: DelegateCommand):
    pass


commands_list = {
    "usend": usend_command,
    "get": uget_command,
    "uset": uset_command,
    "uget": uget_command
}

primitive_commands = [
    "user",
    "uregister",
    "quit",
    "ping",
    "get",
    "authenticate"
]   
    