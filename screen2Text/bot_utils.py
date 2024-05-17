# https://github.com/python-telegram-bot/python-telegram-bot/discussions/2876#discussion-3831621
import logging
from io import BytesIO

from PIL import Image
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from screen2text import DictLookup as dlp
import requests as rq

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                    filename='bot.log',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

START_MESSAGE = 'Hello! To start using the service, please send a tightly cropped image of a word in Thai script. ' \
                'The current implementation is built around Thai language drawing on Thai-based [Longdo Dictionary](' \
                'https://dict.longdo.com/index.php).'
HINT_MESSAGE = 'Please submit a tightly cropped image of a word, enter suggestion number if known, or enter a word ' \
               'preceded by \"lookup\" and a whitespace to look it up in the dictionary.'

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
