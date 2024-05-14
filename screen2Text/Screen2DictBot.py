import requests as rq
import logging
from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from PIL import Image
from io import BytesIO

from screen2text import DictLookup as dlp

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
        'Hello! This is an experimental bot. It is learning to handle text messages, photos and files'
    )


def echo(update: Update, context: CallbackContext) -> None:
    """
    This function is added to the dispatcher as a general handler for messages coming from the Bot API
    """
    global results_dict
    message = update.message
    if message.text:
        print(f'{message.from_user.first_name} wrote: {message.text}')
        if message.text.isdigit():
            their_result = results_dict[message.from_user.id]
            word = their_result[int(message.text)][0]
            x = dlp()
            x.lookup(word)
            context.bot.send_message(
                message.from_user.id,
                # f"Sea monkeys didn't manage to concoct any meaningful output for {word} yet, but they are trying real "
                # f"hard..."
                x.output_markdown(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        # This is equivalent to forwarding, without the sender's name
        update.message.copy(update.message.chat_id)
    elif message.photo:
        print(f'incoming photo from {message.from_user.full_name} detected by echo handler.')
        file = context.bot.get_file(message.photo[0].file_id)
        print(file.file_path)
        # im = Image.open(file.download())  # this also works but the image is needlessly saved, too
        r = rq.get(file.file_path)
        im = Image.open(BytesIO(r.content))
        context.bot.send_message(
            message.from_user.id,
            f'Compressed {im.mode} image sized {im.width}x{im.height} accepted.'
        )
    elif message.document:
        print(f'incoming file from {message.from_user.full_name} detected by echo handler.')
        file = context.bot.get_file(message.document.file_id)
        print(file.file_path)
        if file.file_path.endswith('.png'):
            r = rq.get(file.file_path)
            im = Image.open(BytesIO(r.content))
            context.bot.send_message(
                message.from_user.id,
                f'{im.mode} file sized {im.width}x{im.height} accepted.'
            )
            x = dlp()
            x.load_image(im)
            x.threads_recognize(lang='tha', kind='word')
            x.generate_suggestions()
            # print(x.suggestions)
            results_dict[message.from_user.id] = x.suggestions
            options = 'Choose suggestion number to look up:\n'
            for i in range(0, len(x.suggestions)):
                option = x.suggestions[i]
                options += f'{i} : {option[0]} ({option[1]})\n'
            context.bot.send_message(
                message.from_user.id,
                options
            )
            print(results_dict[message.from_user.id])
        else:
            context.bot.send_message(
                update.message.from_user.id,
                'File could not be accepted: unexpected type based on extension.'
            )
    else:
        context.bot.send_message(
            update.message.from_user.id,
            'What is it?'
        )


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

    # Echo any text message that is not a command, handle photos and files
    dispatcher.add_handler(MessageHandler(~Filters.command, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
