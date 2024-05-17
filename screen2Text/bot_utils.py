# https://github.com/python-telegram-bot/python-telegram-bot/discussions/2876#discussion-3831621

from io import BytesIO

from PIL import Image
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from screen2text import DictLookup as dlp
import requests as rq

START_MESSAGE = '''Hello! To start using the service, please send a tightly cropped image of a word in Thai script. 
                The current implementation is built around Thai language drawing on Thai-based 
                [Longdo Dictionary](https://dict.longdo.com/index.php).'''

# Pre-assign menu text
FIRST_MENU = "<b>Menu 1</b>\n\nA beautiful menu with a shiny inline button."
SECOND_MENU = "<b>Menu 2</b>\n\nA better menu with even more shiny inline buttons."

# Pre-assign button text
NEXT_BUTTON = "Next"
BACK_BUTTON = "Back"
TUTORIAL_BUTTON = "Tutorial"

# Build keyboards
FIRST_MENU_MARKUP = InlineKeyboardMarkup([[
    InlineKeyboardButton(NEXT_BUTTON, callback_data=NEXT_BUTTON)
]])
SECOND_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(BACK_BUTTON, callback_data=BACK_BUTTON)],
    [InlineKeyboardButton(TUTORIAL_BUTTON, url="https://core.telegram.org/bots/tutorial")]
])


def do_recognize(file):
    r = rq.get(file.file_path)
    im = Image.open(BytesIO(r.content))
    x = dlp()
    x.load_image(im)
    x.threads_recognize(lang='tha', kind='line')
    x.generate_suggestions()
    return x.suggestions
