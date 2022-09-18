import enum
import config

class SettingTypes:
    Scalar = 0
    Array = 1
    Object = 2

class SettingQualifiers:
    Private = "&"
    Immutable = "$"
    ImmutablePrivate = "!"


class SettingInfo:
    def __init__(self, kind: type, range: list, special: bool):
        "Packages setting information"
        
        self.kind: type = kind
        self.range: list = range
        self.special: bool = special
        self.qualifier: str = None



class UserSetting:
    def __init__(self, user, conn, setting, value, kind = SettingTypes.Scalar):
        self.user = user
        self.conn = conn
        self.setting = setting
        self.value = value
        self.kind = kind


user_regulated_settings = {

}

user_special_settings = {
    
}