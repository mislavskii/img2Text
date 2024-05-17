from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from bot_config import token
from bot_utils import *

results_dict = {}  # store bot recognition results


def start(update: Update, context: CallbackContext) -> None:
    logger.info(f'/start called by {update.message.from_user.full_name}')
    sent = context.bot.send_message(
            update.message.from_user.id,
            START_MESSAGE,
            parse_mode=ParseMode.MARKDOWN
        )
    logger.info(f'start message sent to {update.message.from_user.full_name}'
                ) if sent else logger.warning(f'failed sending start message to {update.message.from_user.full_name}')


def service(update: Update, context: CallbackContext) -> None:
    """
    This function is added to the dispatcher as a general handler for messages coming from the Bot API
    """
    global results_dict
    message = update.message
    if message.text:
        logger.info(f'{message.from_user.first_name} wrote: {message.text}')
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
        send_hint(message, context)
        return
    elif message.photo or message.document:
        file = None
        if message.photo:
            logger.info(f'incoming photo from {message.from_user.full_name} detected by service handler.')
            file = context.bot.get_file(message.photo[0].file_id)
            send_compressed_confirmation(message, context)
        elif message.document:
            logger.info(f'incoming file from {message.from_user.full_name} detected by service handler.')
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
                return
        results_dict[message.from_user.id] = do_recognize(file) if file else []
        suggestions = results_dict[message.from_user.id]
        choices = generate_choices(suggestions)
        logger.info(f'sending choices to {message.from_user.full_name}')
        sent = context.bot.send_message(
            message.from_user.id,
            choices
        )
        logger.info('sent successfully') if sent else logger.warning('something went wrong... :(')
        return
    else:
        context.bot.send_message(
            update.message.from_user.id,
            'What is it?'
        )
        return


def menu(update: Update, context: CallbackContext) -> None:
    """
    This handler sends a menu with the pre-assigned inline buttons
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
    updater.start_polling(poll_interval=2, bootstrap_retries=2)

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
