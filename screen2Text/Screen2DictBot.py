from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from bot_config import token
from bot_utils import *


def start(update: Update, context: CallbackContext) -> None:
    message = update.message
    logger.info(f'/start called by {message.from_user.full_name}')
    sent = dlp.retry_or_none(context.bot.send_message, 2, 1,
                             message.from_user.id,
                             START_MESSAGE,
                             parse_mode=ParseMode.MARKDOWN
                             )
    if sent:
        logger.info(f'start message sent to {message.from_user.full_name}')
    else:
        logger.warning(f'failed sending start message to {message.from_user.full_name}')
        send_failure_note(message, context)


def service(update: Update, context: CallbackContext) -> None:
    """
    This function is added to the dispatcher as a general handler for messages coming from the Bot API
    """
    message = update.message
    if message.text:
        logger.info(f'incoming text message from {message.from_user.full_name}')
        word = obtain_word(message)
        if word:
            do_lookup(message, context, word)
        else:
            send_hint(message, context)
    elif message.photo or message.document:
        file = None
        if message.photo:
            logger.info(f'incoming photo from {message.from_user.full_name} detected by service handler.')
            file = context.bot.get_file(message.photo[0].file_id)
            send_compressed_confirmation(message, context)
        elif message.document:
            logger.info(f'incoming file from {message.from_user.full_name} detected by service handler.')
            file = context.bot.get_file(message.document.file_id)
            if file.file_path.endswith('.png') or file.file_path.endswith('.jpg'):
                send_uncompressed_confirmation(message, context)
            else:
                send_rejection_note(message, context)
                return
        logger.info(f'loading {file.file_path}')
        r = dlp.retry_or_none(rq.get, 3, 1, file.file_path, timeout=30)
        if not r:
            send_failure_note(message, context)
            return
        results_dict[message.from_user.id] = do_recognize(r, message, context)
        suggestions = results_dict[message.from_user.id]
        choices = generate_choices(suggestions)
        send_choices(message, context, choices)
        return
    else:
        send_baffled(message, context)
        return


def menu(update: Update, context: CallbackContext) -> None:  # Not yet implemented
    """
    This handler sends a menu with the pre-assigned inline buttons
    """
    context.bot.send_message(
        update.message.from_user.id,
        FIRST_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=FIRST_MENU_MARKUP
    )


def button_tap(update: Update, context: CallbackContext) -> None:  # Not yet implemented
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


def simulated_error(update: Update, context: CallbackContext):
    raise Exception('Intentional error for testing purposes')


def error_handler(update: Update, context: CallbackContext):
    """Handle errors raised by handlers."""
    logger.info(f'error handler invoked in relation to {update.message.text if update else None}')
    logger.error(f"Update {update.update_id if update else None} caused error: {context.error}")
    tb_logger.error(context.error, exc_info=True)


def main() -> None:
    updater = Updater(token, request_kwargs={'read_timeout': 10})

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", menu))
    dispatcher.add_handler(CommandHandler("error", simulated_error))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(button_tap))

    # Process any text message that is not a command, handle photos and files
    dispatcher.add_handler(MessageHandler(~Filters.command, service))

    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling(poll_interval=2, timeout=10, bootstrap_retries=2)

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
