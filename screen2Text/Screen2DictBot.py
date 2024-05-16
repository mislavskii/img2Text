import logging

import telegram.error
from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from bot_utils import *

from bot_config import token


results_dict = {}  # store bot recognition results

logger = logging.getLogger(__name__)

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


def start(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        update.message.from_user.id,
        'Hello! To start using the service, please send a tightly cropped image of a word. '
        'The current implementation is built around Thai language drawing on Thai-based '
        '[Longdo Dictionary](https://dict.longdo.com/index.php).',
        parse_mode=ParseMode.MARKDOWN
    )


def service(update: Update, context: CallbackContext) -> None:
    """
    This function is added to the dispatcher as a general handler for messages coming from the Bot API
    """
    global results_dict
    message = update.message
    if message.text:
        print(f'{message.from_user.first_name} wrote: {message.text}')
        word = ''
        if message.text.isdigit():
            if message.from_user.id in results_dict.keys():
                their_results = results_dict[message.from_user.id]
                result_index = int(message.text)
                if result_index < len(their_results):
                    word = their_results[result_index][0]
        if message.text.lower().startswith('lookup') and len(message.text.split()) == 2:
            word = message.text.split()[-1]
        if word:
            context.bot.send_message(
                message.from_user.id,
                f'looking up {word} ...'
            )
            x = dlp()
            x.lookup(word)
            output = x.output_markdown()
            tail = ' ...\nclick the link below for more'
            context.bot.send_message(
                message.from_user.id,
                output if len(output) < 4096 else output[:4096 - len(tail)] + tail,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        # This is equivalent to forwarding, without the sender's name
        context.bot.send_message(
            message.from_user.id,
            'Please submit a tightly cropped image of a word, enter suggestion number if known, '
            'or enter a word preceded by \"lookup\" and a whitespace to look it up in the dictionary.'
        )
        return
    elif message.photo or message.document:
        file = None
        if message.photo:
            print(f'incoming photo from {message.from_user.full_name} detected by service handler.')
            file = context.bot.get_file(message.photo[0].file_id)
            context.bot.send_message(
                message.from_user.id,
                f'Compressed image accepted. Processing...'
            )
        elif message.document:
            print(f'incoming file from {message.from_user.full_name} detected by service handler.')
            file = context.bot.get_file(message.document.file_id)
            if file.file_path.endswith('.png'):
                context.bot.send_message(
                    message.from_user.id,
                    'Uncompressed image file accepted. Processing...'
                )
            else:
                context.bot.send_message(
                    update.message.from_user.id,
                    'File could not be accepted: unexpected type based on extension.'
                )
        suggestions = do_recognize(file) if file else []
        results_dict[message.from_user.id] = suggestions
        choices = 'Choose suggestion number to look up:\n' if suggestions else 'No meaningful recognition results ' \
                                                                               'could be produced.'
        for i in range(0, len(suggestions)):
            option = suggestions[i]
            choices += f'{i} : {option[0]} ({option[1]})\n'
        context.bot.send_message(
            message.from_user.id,
            choices
        )
        print(results_dict[message.from_user.id])
        return
    else:
        context.bot.send_message(
            update.message.from_user.id,
            'What is it?'
        )
        return


def menu(update: Update, context: CallbackContext) -> None:
    """
    This handler sends a menu with the inline buttons we pre-assigned above
    """
    context.bot.send_message(
        update.message.from_user.id,
        FIRST_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=FIRST_MENU_MARKUP
    )


def button_tap(update: Update, context: CallbackContext) -> None:
    """
    This handler processes the inline buttons on the menu
    """
    data = update.callback_query.data
    text = ''
    markup = None

    if data == NEXT_BUTTON:
        text = SECOND_MENU
        markup = SECOND_MENU_MARKUP
    elif data == BACK_BUTTON:
        text = FIRST_MENU
        markup = FIRST_MENU_MARKUP

    # Close the query to end the client-side loading animation
    update.callback_query.answer()

    # Update message content with corresponding menu section
    update.callback_query.message.edit_text(
        text,
        ParseMode.HTML,
        reply_markup=markup
    )


def main() -> None:
    updater = Updater(token)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", menu))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(button_tap))

    # Process any text message that is not a command, handle photos and files
    dispatcher.add_handler(MessageHandler(~Filters.command, service))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
