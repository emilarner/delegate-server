from dataclasses import dataclass
from definitions import *

#Due to the nature of this program, it is not feasible to use a testing framework and/or abstraction to test the features of this server backend implementation.
#Register: OK
user_register = """
{
    "command": "uregister",
    "username": "testing",
    "password": "testingpassword"
}
"""

# Check if the database has been written to for the Users table, with an Argon2 password hash
#Sign in (without 2FA): OK

user_signin = """
{
    "command": "user",
    "username": "testing",
    "password": "testingpassword"
}
"""



user_logout = """
{
    "command": "logout"
}
"""

user_fail_login = """
{
    "command": "user",
    "username": "testing",
    "password": "nottestingpassword"
}
"""

#User Settings

#2FA

tfa_command = """
{
    "command": "2fa"
}
"""


set_tfa_true = """
{
    "command": "uset",
    "settings": {
        "&2fa": true
    }
}
"""
# Should return nothing

uget_2fa = """
{
    "command": "uget",
    "username": null,
    "settings": ["&2fa"]
}
"""

# S_USER_SET, 2fa should be true

sign_in_2fa = """
{{
    "command": "user",
    "username": "testing",
    "password": "testingpassword",
    "2fa": "{tfa}"
}}
"""

# Should complain both about immutability.
immutable_test_1 = """
{
    "command": "uset",
    "settings": {
        "$creation": 0
    }
}
"""

immutable_test_2 = """
{
    "command": "uset",
    "settings": {
        "!channels": ["main"] 
    }
}
"""


dummy_account_create = """
{
    "command": "uregister",
    "username": "dummy",
    "password": "dummydummy"
}
"""

dummy_account_login = """
{
    "command": "user",
    "username": "dummy",
    "password": "dummydummy"
}
"""

dummy_account_message = """
{
    "command": "usend",
    "username": "testing",
    "type": null,
    "format": null,
    "message": "Hello world"
}
"""

