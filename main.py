import os
import sys
import threading

from util import *
import delegateserver


def debug_thread(instance):
    while True:
        exec(input("python>"))

def main():
    port = 8080
    tls = False

    try:
        for i in range(len(sys.argv)):
            if (sys.argv[i].startswith("-")):
                if (sys.argv[i] in ["-p", "--port"]):
                    port = sys.argv[i + 1]

                elif (sys.argv[i] in ["-t", "--tls"]):
                    tls = True 

                else:
                    eprint(f"Flag '{sys.argv[i]}' not recognized... exiting...")
                    sys.exit(-1)

    except IndexError:
        eprint("A required argument was not given... exiting....")
        sys.exit(-2)



    print("Delegate Backend Server started on port 8080")

    d = delegateserver.DelegateServer("test", 8080, False)

    threading.Thread(target = debug_thread, args = (d,)).start()

    d.start()

if (__name__ == "__main__"):
    main()