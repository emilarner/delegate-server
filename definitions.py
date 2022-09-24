from types import NoneType


class ServerCodes:
    class Success:
        Connection = 0
        Ping = 1
        Get = 2
        Authentication = 3

    class Error:
        NotOpen = -1
        ServerException = -2 
        Banned = -3
        Kicked = -4
        JSONError = -5
        TooLong = -6
        Password = -8
        PasswordRequired = -9
        NotApplicable = -10
        NoParameter = -11
        DontCare = -12
        NotImplemented = -13

class UserCodes:
    class Success:
        Signin = 100
        Register = 101
        Logout = 102
        MessageInfo = 103
        TwoFactor = 104
        Settings = 105

    class Errors:
        PasswordIncorrect = -100
        UsernameExists = -101
        WeakPassword = -102
        UsernameLength = -103
        UsernameRegex = -104
        UsernameExists = -105
        UsernameNoent = -106
        UserBlocked = -107
        UserMaxConnections = -108
        UserNoMoreAccounts = -109
        AlreadySignedIn = -110
        FriendRequestNoent = -111
        NotABot = -112
        BotCannotDoThat = -113
        TwoFactorVerify = -114
        CantBecomeFriends = -115
        CantSendMessage = -116
        FriendNoent = -117
        SubscriptionError = -118

class ChannelCodes:
    class Success:
        Join = 200
        Register = 201
        SubchannelCreated = 202
        SubchannelDestroyed = 203
        ChannelDeleted = 204
        Audit = 205

    class Errors:
        Noent = -200
        AlreadyExists = -201
        Banned = -202
        LackPermissions = -203
        NameLength = -205
        Regex = -206
        SubchannelNoent = -207
        SubchannelExists = -208
        SubchannelLength = -209
        SubchannelRegex = -210
        HigherRole = -211
        InviteOnly = -212
        Password = -213
        NoTor = -214
        NoJoins = -215
        WeakJoin = -216
        NotInChannel = -217
        InChannelAlready = -218
        JoinIncorrect = -219
        MainError = -220

class CommandCodes:
    ArgsMissing = -300
    NotFound = -301
    InvalidTypes = -302
    ServerPermissionDenied = -303
    NotSignedIn = -304
    MutuallyExclusive = -305

class SettingCodes:
    class Success:
        Obtained = 400
        Set = 401

    class Errors:
        Private = -400
        Scalar = -401
        Array = -402
        Object = -403
        Immutable = -404
        Type = -405
        MutuallyExclusive = -406
        NotWithinEnum = -407
        TooLong = -408
        Range = -409
        WrongData = -410
        
