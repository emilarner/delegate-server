import pyfiglet
import os
import sys
import random


def get_available_fonts() -> list:
    text = os.popen("pyfiglet -l", "r").read()
    return text.splitlines()


#get_available_fonts()

fonts = [
    "3-d",
    "3x5",
    "5x7",
    "5lineoblique",
    "6x10",
    "6x9",
    "acrobatic",
    "alligator",
    "alligator2",
    "arrows",
    "asc_____",
    "ascii___",
    "avatar",
    "banner",
    "banner3",
    "banner3-D",
    "banner4",
    "barbwire",
    "basic",
    "bell",
    "big",
    "block",
    "brite",
    "broadway",
    "bubble__",
    "bulbhead",
    "c_ascii_",
    "calgphy2",
    "catwalk",
    "charact1",
    "charact3",
    "chunky",
    "clb6x10",
    "coinstak",
    "colossal",
    "computer",
    "contessa",
    "contrast",
    "cosmic",
    "cricket",
    "crawford",
    "defleppard",
    "diamond",
    "doh",
    "double",
    "dotmatrix",
    "ebbs_2__",
    "eftirobot",
    "epic",
    "fender",
    "fraktur",
    "gothic",
    "graceful",
    "graffiti",
    "hollywood",
    "inc_raw_",
    "isometric1",
    "isometric2",
    "isometric3",
    "isometric4",
    "larry3d",
    "marquee",
    "mini",
    "nipples",
    "npn_____",
    "nvscript",
    "o8",
    "ogre",
    "peaks",
    "pawp",
    "radical_",
    "rectangles",
    "roman",
    "roman___",
    "rounded",
    "rowancap",
    "rozzo",
    "sans",
    "sblood",
    "sbook",
    "sbookb",
    "slant",
    "slide",
    "smkeyboard",
    "space_op",
    "starwars",
    "t__of_ap",
    "thin",
    "thick",
    "tiles",
    "trashman",
    "trek",
    "tty",
    "tubular",
    "univers",
    "whimsy"
]

available_fonts: list = fonts


letters = list("qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM")

def distort(letter: str, intensity = 1):
    result = ""

    for line in letter.splitlines():
        for i in range(random.randint(0, intensity)):
            result += " "

        result += line + "\n"

    return result


def generate_ascii_captcha(text: str):
    result = ""

    for char in text:
        result += distort(pyfiglet.figlet_format(char, font = random.choice(available_fonts)))

    return result


def main():
    #for font in available_fonts:
    #    print(f"{font}:")
    #    print(pyfiglet.figlet_format("hello", font = font))

    print(generate_ascii_captcha(sys.argv[1]))

if (__name__ == "__main__"):
    main()