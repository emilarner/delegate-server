import sys
import os
import json
import websocket
import time
import pyotp.totp
import datetime
import blessed

t = blessed.Terminal()

from dataclasses import dataclass

from websocket import create_connection
from definitions import *
from usertests import *

def spinning_cursor(t):
    for i in range(t * 2):
        # 0.5 each
        for cursor in '\\|/-':
            time.sleep(0.125)
            # Use '\r' to move cursor back to line beginning
            # Or use '\b' to erase the last character
            sys.stdout.write('\r{}'.format(cursor))
            # Force Python to write data into terminal.
            sys.stdout.flush()

    print("\n")

@dataclass
class Event:
    event: str
    body: dict

    @staticmethod
    def from_json(text: str):
        block = json.loads(text)
        assert ("event" in block)
        return Event(block["event"], block)


def check_code(name, jsontext: str, code: int, fields = {}) -> dict:
    print(f"Testing {name}...")
    obj = json.loads(jsontext)
    
    try:
        assert("code" in obj)
        assert(obj["code"] == code)
    except:
        raise AssertionError("Assertion failed, here's the body: \n" + jsontext)

    for field, value in fields.items():
        try:
            assert(field in obj)
            assert(obj[field] == value)
        except:
            raise AssertionError(f"Assertion failed. \nField: {field}; Value: {value}")

    print(f"'{name}'... " + t.bold_green("PASSED \u2713 \n"))
    return obj


def main():
    # Phase 1 of testing
    ws = create_connection(sys.argv[1])

    ws.send("NOT A JSON STRING")
    check_code("JSON sanity checking", ws.recv(), ServerCodes.Error.JSONError)

    # Test user registration
    ws.send(user_register)
    check_code("user registration", ws.recv(), UserCodes.Success.Register)

    # No duplicate registration test
    ws.send(user_register)
    check_code("no duplicate usernames", ws.recv(), UserCodes.Errors.UsernameExists)

    # Successful sign in
    ws.send(user_signin)
    check_code("user signin", ws.recv(), UserCodes.Success.Signin)

    # No duplicate sign ins like that
    ws.send(user_signin)
    check_code("no duplicate signins", ws.recv(), UserCodes.Errors.AlreadySignedIn)

    # Log out
    ws.send(user_logout)
    check_code("user logout", ws.recv(), UserCodes.Success.Logout)

    ws.close()

    # Phase 2 of testing 
    ws = create_connection(sys.argv[1])

    # Test incorrect password
    ws.send(user_fail_login)
    check_code("password protection", ws.recv(), UserCodes.Errors.PasswordIncorrect)

    # Successful sign in
    ws.send(user_signin)
    check_code("another user sign in", ws.recv(), UserCodes.Success.Signin)

    # 2FA command working...
    ws.send(tfa_command)
    tfa_body = ws.recv()
    check_code("2fa command", tfa_body, UserCodes.Success.TwoFactor)

    tfa_body = json.loads(tfa_body)
    assert ("secret" in tfa_body)
    tfa_secret = tfa_body["secret"]

    ws.send(set_tfa_true)
    
    ws.send(uget_2fa)
    check_code("&2fa variable", ws.recv(), UserCodes.Success.Settings, {
        "settings": {
            "&2fa": True
        }
    })


    ws.close()
    # Phase 3
    print("Waiting for database to be written....")
    spinning_cursor(1)

    ws = create_connection(sys.argv[1])

    totp = pyotp.totp.TOTP(tfa_secret)
    totp_code = None

    while True:
        totp_code = totp.now()
        time_remaining = round(totp.interval - datetime.datetime.now().timestamp() % totp.interval)

        # Make sure the TOPT won't randomly expire
        if (time_remaining < 5):
            print("Hold on... we need to give TOPT more time")
            spinning_cursor(time_remaining + 1)
            continue

        break

    ws.send(sign_in_2fa.format(tfa = totp_code))
    check_code("testing 2fa", ws.recv(), UserCodes.Success.Signin)


    ws.send(immutable_test_1)
    check_code("testing for $creation immutability", ws.recv(), SettingCodes.Errors.Immutable)
    ws.send(immutable_test_2)
    check_code("testing for !channels immutability", ws.recv(), SettingCodes.Errors.Immutable)

    ws2 = create_connection(sys.argv[1])

    ws2.send(dummy_account_create)
    ws2.recv()
    ws2.send(dummy_account_login)
    ws2.recv()
    ws2.send(dummy_account_message)
    print(ws2.recv())

    # Message event
    event: dict = Event.from_json(ws.recv()).body

    try:
        assert ("timestamp" in event and isinstance(event["timestamp"], int))
        assert ("type" in event and event["type"] == None)
        assert ("uuid" in event and isinstance(event["uuid"], str))
        assert ("origin" in event and event["origin"] == 1) 
        assert ("username" in event and event["username"] == "dummy")
        assert ("format" in event and event["format"] == None)
        assert ("content" in event and event["content"] == "Hello world")
    
    except AssertionError:
        raise AssertionError(f"Assertion failed... body: \n + {event}")



    print("Finished without a hitch... your server implementation complies with the protocol!")





if (__name__ == "__main__"):
    main()