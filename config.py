from definitions import *

class ServerInfo:
    Name = "A Delegate Server"
    Description = "idk"
    Version = "1.0.0"
    Admin = "Me"

    HTTPEndpoints = [

    ]

    Safelinks = [

    ]

    Image = ""
    Banner = ""


class Networking:
    Host = "0.0.0.0"
    Port = 9998
    WSPort = 9999
    HTTP = 9997
    HTTPS = 9996

class ServerRegulations:
    MaxMessageLength = 4096
    Timeout = 60*15

class SettingRegulations:
    # Max size of free settings.
    FreeLength = 512

    # Max number of free settings.
    FreeNo = 128


class Database:
    Port = 80
    Username = "postgres"
    Password = "3313"
    Name = "delegatetest"
    Host = "/tmp"

class ServerPassword:
    On = False
    Password = "aserverpassword"

class UserSettings:
    UserAwayTime = 10*MINUTE

class UserRegulations:
    Length = [3, 24]
    Regex = "[a-zA-Z0-9-.]"
    PasswordLength = [8, 64]

class UserSettingRegulations:
    NameLength = [1, 24]
    StatusLength = [1, 32]
    DescriptionLength = [1, 360]
    AvatarLength = [256, 256]
    PagerLength = [256, 256]

class MessageRegulations:
    Length = [0, 1024]


class ChannelDefaults:
    JoinMessage = "Welcome to the channel!"
    LeaveMessage = "Sorry to see you leave!"

class ChannelRegulations:
    Length = [4, 64]
    Regex = "[a-zA-Z0-9+\/=-]"
    SubLength = [2, 192]
    SubRegex = "[a-zA-Z0-9+\/=-]"
