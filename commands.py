import json

import users
import config
import messages

from settings import *
from util import *
from definitions import *


def type_test(variables: list, types: list):
    "Given a list of variables, then a list of their supposed types, check if its true."

    for i in range(len(variables)):
        if (not isinstance(variables[i], types[i])):
            return False

    return True

# Okay, so I tried abstracting away a lot of the command sanity checking boilerplate with this.
# But if I am to be honest, this method just looks so fucking ugly it's unbelievable.
# If I ever get tired of writing the boilerplate, I'll use this. But until then,
# this is fucking ugly as shit, admit it. I tend to write C-like Python code, because
# I'm *that* kind of person. Make fun of me for using parentheses around my if-statements,
# because I'll just keep using them...

async def test_command_parameters(body: dict, parameters: list, connection) -> list:
    results = []

    # Go through each parameter in the form of (name: str, type: type, required: bool)
    for parameter in parameters:
        name, kind, required = parameter
        value = None

        # If it is not required, leave it as None or the actual value provided.
        if (not required):
            if (name in body):
                value = body[name]

        else:

            # If it is required, send an error code and return None if it does not exist.
            if (name not in body):
                await connection.code(CommandCodes.ArgsMissing)
                return None

            value = body[name]

        # If the value of the parameter is mismatching and is required
        # (cannot have a value of None/null), send an error code and return None
        if (not isinstance(value, kind) and required):
            await connection.code(CommandCodes.InvalidTypes)
            return None

        results.append(value)

    return results




class DelegateCommand:
    def __init__(self, connection, instance, command, body, user):
        self.connection = connection

        self.instance = instance
        self.messages: messages.MessagesDatabase = self.instance.messages

        self.command: str = command
        self.body: dict = body
        self.user: users.User = user
        self.users: users.Users = user.users

    @staticmethod
    def from_json(connection, instance, ccode, user):
        "Loads a command from raw JSON data."
        
        code = json.loads(ccode)
        return DelegateCommand(connection, instance, code["command"], code, user)




async def initial_user_signin(command: DelegateCommand) -> bool:
    try:
        username: str = command.body["username"]
        password: str = command.body["password"]
        tfa: str = None if "2fa" not in command.body else command.body["2fa"]

        # Validate the types that are sent in by the client.
        if (not type_test([username, password], [str, str]) or 
            (tfa != None and not isinstance(tfa, str))):

            await command.connection.code(CommandCodes.InvalidTypes)
            return

        

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
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


    # If two-factor authentication is required and it is denied, error.
    if (command.users.has_2fa(username)):
        if (not command.users.verify_2fa(username, tfa)):
            await command.connection.code(UserCodes.Errors.TwoFactorVerify)
            return


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


#async def logout_command(command: DelegateCommand)


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


    # The user has blocked you, so you may not send messages to them.
    if (command.user.has_me_blocked(to)):
        await command.connection.code(UserCodes.Errors.UserBlocked)
        return 

    other_settings: dict = command.users.get_user_settings(to)

    # Cannot message them, no matter what
    if (other_settings["&asocial"]):
        await command.connection.code(UserCodes.Errors.CantSendMessage)
        return

    # Cannot send a message to them, because we are not friends.
    if (other_settings["&friends_only"] and not command.user.friends_with(to)):
        await command.connection.code(UserCodes.Errors.CantSendMessage)
        return


    # Cannot send a message to them because we don't share a channel.
    if (not other_settings["&friendly"] 
            and not command.users.two_users_in_channel(command.user.username, to)):

        await command.connection.code(UserCodes.Errors.CantSendMessage)
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
    
    # Under construction; this will be implemented later
    # Phase III:
    # command.messages.user_message(msg)


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

    new_settings = {

    }

    existing_settings: dict = command.user.settings

    for key, value in settings.items():
        key: str = key

        # Trying to modify an immutable setting.
        if (key[0] in [SettingQualifiers.Immutable, SettingQualifiers.ImmutablePrivate]):
            await command.connection.code(SettingCodes.Errors.Immutable)
            return

        # A regulated user setting
        if (key in users.setting_infos):
            info: SettingInfo = users.setting_infos[key]

            # Test if it passed the regulations.
            if (not info.test(existing_settings, command.connection, key, value)):
                return

            # Add this to the list of special settings we need to send events for
            # only if it is a special setting.
            if (info.special):
                special_settings[key] = value


            new_settings[key] = value
        
    # Modify the settings and put the user on the queue.
    command.user.set_settings(new_settings)

    # Emit special setting notice to all friends and subscribers
    if (special_settings != {}):
        await command.user.special_settings_emit(special_settings)


        
    
async def uget_command(command: DelegateCommand):
    try:
        settings: list = command.body["settings"]
        username: str = command.body["username"]


        # Must be specific type.
        if (not isinstance(settings, list)):
            await command.connection.code(CommandCodes.InvalidTypes)
            return

        # Username may be *null* to signify that we are obtaining from ourselves.
        if (username != None and not isinstance(username, str)):
            await command.connection.code(CommandCodes.InvalidTypes)
            return

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return


    # If the username does not exist.
    if (username != None and not command.users.user_exists(username)):
        await command.connection.code(UserCodes.Errors.UsernameNoent)
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


# Deprecated--it no longer exists within the protocol.
async def upriv_command(command: DelegateCommand):
    pass




async def frequest_command(command: DelegateCommand):
    try:
        username = command.body["username"]
        message = None if message not in command.body else command.body["message"]
    
        # Detect invalid types.
        if (not isinstance(username, str) or (message != None and not isinstance(message, str))):
            await command.connection.code(CommandCodes.InvalidTypes)
            return

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return

    # Check if the user exists.
    if (not command.users.user_exists(username)):
        await command.connection.code(UserCodes.Errors.UsernameNoent)
        return

    their_settings: dict = command.users.get_user_settings(username)
    

    # Nobody can become friends with them.
    if (their_settings["&lone"]):
        await command.connection.code(UserCodes.Errors.CantBecomeFriends)
        return


    # Cannot become friends due to the other user's skepticism.
    if (their_settings["&skeptic"] 
            and not command.users.two_users_in_channel(username, command.user.username)):

        await command.connection.code(UserCodes.Errors.CantBecomeFriends)
        return

    await command.user.send_friendreq(username, message)


async def friend_command(command: DelegateCommand):
    try:
        username: str = command.body["username"]
        accept: bool = command.body["accept"]
        notify: bool = command.body["notify"]

        # Enforce types.
        # We could abstract/simplify this, but honestly it's better like this...
        if (not isinstance(username, str) 
            or not isinstance(accept, bool)
            or not isinstance(notify, bool)):

            await command.connection.code(CommandCodes.InvalidTypes)
            return

        

    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return

    # If the user does not exist.
    if (username not in command.user.friend_requests):
        await command.connection.code(UserCodes.Errors.FriendRequestNoent)
        return

    # Accept or deny the friend request.
    await command.user.handle_friendreq(username, accept, notify)


async def usubscribe_command(command: DelegateCommand):
    try:
        username: str = command.body["username"]
        subscribe: bool = command.body["subscribe"]

        # Check types, as always.
        if (not isinstance(username, str) or not isinstance(subscribe, bool)):
            await command.connection.code(CommandCodes.InvalidTypes)
            return
    
    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return

    # Add a user subscription
    if (subscribe):
        # Cannot subscribe if already subscribed to.
        if (command.user.is_subscribedto(username)):
            await command.connection.code(UserCodes.Errors.SubscriptionError)
            return

        command.user.subscribe_to(username)

    # Remove a user subscription
    else:
        # Cannot unsubscribe if not already subscribed to.
        if (not command.user.is_subscribedto(username)):
            await command.connection.code(UserCodes.Errors.SubscriptionError)
            return

        command.user.unsubscribe_to(username)
        


# in construction, moved to Phase III
async def umsgquery_command(command: DelegateCommand):
    try:
        username: str = command.body["username"]
        query: dict = command.body["query"]
        page_len: int = command.body["page_len"]
        timestamp: int = command.body["timestamp"] if "timestamp" in command.body else None

        # New anti-boilerplate feature.
        if (not type_test([username, query, page_len], [str, dict, int]) 
            or (not isinstance(timestamp, int) and timestamp != None)):

            await command.connection.code(CommandCodes.InvalidTypes)
            return


    except KeyError:
        await command.connection.code(CommandCodes.ArgsMissing)
        return


    
    


async def ueventquery_command(command: DelegateCommand):
    pass


# A list of non-primitive commands corresponding to their function handler.
commands_list = {
    "usend": usend_command,
    "get": uget_command,
    "uset": uset_command,
    "uget": uget_command,
    "frequest": frequest_command,
    "friend": friend_command
}


# A list of commands which do not require signing into a user.
primitive_commands = [
    "user",
    "uregister",
    "quit",
    "ping",
    "get",
    "authenticate"
]   
    