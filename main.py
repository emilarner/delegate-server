import os
import sys
import threading

from util import *

import config
import delegateserver


def debug_thread(instance):
    while True:
        exec(input("python>"))

def main():
    hostip = config.Networking.Host
    port = config.Networking.Port
    tls = False

    try:
        for i in range(len(sys.argv)):
            if (sys.argv[i].startswith("-")):
                if (sys.argv[i] in ["-p", "--port"]):
                    port = sys.argv[i + 1]

                elif (sys.argv[i] in ["-t", "--tls"]):
                    tls = True 

                elif (sys.argv[i] in ["-h", "--host"]):
                    hostip = sys.argv[i + 1]
                
                else:
                    eprint(f"Flag '{sys.argv[i]}' not recognized... exiting...")
                    sys.exit(-1)

    except IndexError:
        eprint("A required argument was not given... exiting....")
        sys.exit(-2)


    status_string = "Delegate Backend Server started on {port} with TLS {tls} on {host}".format(
        port = port,
        tls = "enabled" if tls else "disabled",
        host = hostip
    )

    print(status_string)

    d = delegateserver.DelegateServer(hostip, port, tls)

    threading.Thread(target = debug_thread, args = (d,)).start()

    d.start()

if (__name__ == "__main__"):
    main()