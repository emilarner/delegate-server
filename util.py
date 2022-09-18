import sys
import re

def eprint(string: str):
    "Print an error message to the standard error output"

    sys.stderr.write(string + "\n")

def regex_test(regex, string) -> bool:
    return re.compile(regex).match(string)

def within_range(number, min, max) -> bool:
    return min <= number <= max