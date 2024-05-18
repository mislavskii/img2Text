# https://github.com/python-telegram-bot/python-telegram-bot/discussions/2876#discussion-3831621
import logging
from io import BytesIO
import requests as rq
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

from screen2text import DictLookup as dlp

results_dict = {}  # store bot recognition results

# https://www.youtube.com/watch?v=9L77QExPmI0
logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                    filename='bot.log', encoding='utf-8',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

START_MESSAGE = 'Hello! To start using the service, please send a tightly cropped image of a word in Thai script. ' \
                '\n\nCurrent experimental implementation is built around Thai language drawing on Thai-based [Longdo ' \
                'Dictionary](https://dict.longdo.com/index.php) in [Python](https://www.python.org/) programming ' \
                'language using [python-telegram-bot](https://github.com/python-telegram-bot) library as well as [' \
                'Tesseract-OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html) in ' \
                '[pytesseract](https://pypi.org/project/pytesseract/) wrapper, [NECTEC Lexitron](' \
                'https://www.nectec.or.th/innovation/innovation-software/lexitron.html) and [PyThaiNLP](' \
                'https://pythainlp.github.io/) for spelling verification, [Pillow](' \
                'https://github.com/python-pillow/Pillow/) for image processing, [requests](' \
                'https://requests.readthedocs.io) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) ' \
                'for web content processing, and others. Many thanks to creators and maintainers of all these ' \
                'resources!\nFeel free to [contact the developer](https://t.me/jornjat) with any inquiries.'
HINT_MESSAGE = 'Please submit a tightly cropped image of a word in Thai script, enter suggestion number if known, ' \
               'or enter a word preceded by \"lookup\" and a whitespace to look it up in the dictionary.'
LOOKUP_TAIL = '...\nclick the link below for more'
FAILURE = 'something went wrong.'

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


def send_compressed_confirmation(message, context):
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             'Loading compressed image from server...'
                             )
    logger.info('compressed confirmation sent successfully' if sent else FAILURE)
    return sent


def send_uncompressed_confirmation(message, context):
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             'Loading uncompressed image file from server...'
                             )
    logger.info('uncompressed confirmation sent successfully' if sent else FAILURE)
    return sent


def send_processing_note(message, context):
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             'File loaded. Attempting recognition...'
                             )
    logger.info('processing note sent successfully' if sent else FAILURE)
    return sent


def send_rejection_note(message, context):
    logger.info('unsupported file extension, sending rejection note...')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             'File could not be accepted: unexpected type based on extension.'
                             )
    logger.info(f'rejection note sent successfully to {message.from_user.full_name}' if sent else FAILURE)
    return sent


def send_failure_note(message, context):
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             'Something went wrong... Please consider trying one more time.'
                             )
    logger.info(f'failure note sent successfully to {message.from_user.full_name}' if sent else FAILURE)
    return sent


def do_recognize(r: rq.Response, message, context):
    x = dlp()
    try:
        x.load_image(BytesIO(r.content))
    except Exception as e:
        logger.info("Couldn't open the file")
        logger.error(e)
        send_failure_note(message, context)
        return []
    logger.info('initiating recognition...')
    send_processing_note(message, context)
    x.threads_recognize(lang='tha', kind='line')
    x.generate_suggestions()
    logger.info(f'image recognition produced  {len(x.suggestions)} suggestion(s)')
    return x.suggestions


def obtain_word(message):
    word = ''
    text = message.text
    if text.isdigit():
        if message.from_user.id in results_dict.keys():
            their_results = results_dict[message.from_user.id]
            result_index = int(message.text)
            if result_index < len(their_results):
                word = their_results[result_index][0]
    if message.text.lower().startswith('lookup') and len(message.text.split()) == 2:
        word = message.text.split()[-1]
    return word


def do_lookup(message, context, word):
    logger.info(f'got a word to look up, initiating lookup for {word}')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             f'looking up {word} ...'
                             )
    logger.info(f'notification sent successfully to {message.from_user.full_name}' if sent else FAILURE)
    x = dlp()
    x.lookup(word)
    output = x.output_markdown()
    logger.info(f'lookup output generated ({output[:64] if len(output) > 64 else output} ...)')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             output if len(output) < 4096 else output[:4096 - len(LOOKUP_TAIL)] + LOOKUP_TAIL,
                             parse_mode=ParseMode.MARKDOWN,
                             timeout=15
                             )
    logger.info(f'and sent successfully to {message.from_user.full_name}' if sent else FAILURE)
    return


def generate_choices(suggestions):
    logger.info('generating choices')
    choices = 'Choose suggestion number to look up:\n' if suggestions \
        else 'No meaningful recognition results could be produced.'
    for i in range(0, len(suggestions)):
        option = suggestions[i]
        choices += f'{i} : {option[0]} ({option[1]})\n'
    return choices


def send_choices(message, context, choices):
    logger.info(f'sending choices to {message.from_user.full_name}')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             choices
                             )
    logger.info('choices sent successfully' if sent else FAILURE)
    return sent


def send_hint(message, context):
    logger.info('no meaningful action could be taken based on the message text, sending hint...')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             HINT_MESSAGE
                             )
    logger.info(f'hint message sent to {message.from_user.full_name}' if sent else FAILURE)
    return sent


def send_baffled(message, context):
    logger.info(f'unknown matter encountered in the message, sending baffled note...')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1, logger,
                             message.from_user.id,
                             'What is it?'
                             )
    logger.info('sent successfully' if sent else FAILURE)
    return sent
