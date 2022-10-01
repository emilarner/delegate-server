from typing import Any

import config
from definitions import *
from util import *

class SettingTypes:
    Scalar = 0
    Array = 1
    Object = 2

class SettingQualifiers:
    Private = "&"
    Immutable = "$"
    ImmutablePrivate = "!"


class SettingInfo:
    def __init__(self, kind: type, range: list, special: bool, conflicts: list = None):
        "Packages setting information"
        
        self.kind: type = kind
        self.range: list = range
        self.special: bool = special
        self.qualifier: str = None
        self.conflicts: list = conflicts


    async def _range_error(self, connection, name):
        await connection.code(SettingCodes.Errors.Range, {
            "setting": name,
            "range": self.range
        })

    async def test(self, other_settings: dict, connection, name: str, setting: Any) -> bool:
        # If the type is not the one that is required, send the client an error detailing
        # that.
        if (not isinstance(setting, self.kind)):
            await connection.code(SettingCodes.Errors.Type, {
                "setting": name,
                "given": type(setting).__name__,
                "required": self.kind.__name__
            })

            return False


        # There are potential boolean conflicts with mutual exclusivity
        if (self.conflicts != None):
            for conflict in self.conflicts:

                # If both are True, that is illegal, so error.
                if (other_settings[conflict] and setting):
                    await connection.code(SettingCodes.Errors.MutuallyExclusive, {
                        "settings": [name, conflict]
                    })

                    return False


        # Check if the setting is within a specific numerical range
        if (self.range != None):

            # If it is a string, then the length will be ranged.
            if (isinstance(setting, str)):
                if (not within_range(len(setting), *self.range)):
                    await self._range_error(connection, name)
                    return False

            # If it is an integer, then the numerical value will be ranged.
            if (isinstance(setting, int)):
                if (not within_range(setting, *self.range)):
                    await self._range_error(connection, name)
                    return False


        return True


class UserSetting:
    def __init__(self, user, conn, setting, value, kind = SettingTypes.Scalar):
        self.user = user
        self.conn = conn
        self.setting = setting
        self.value = value
        self.kind = kind

