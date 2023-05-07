from os import path as ospath
from pickle import load as pload
from telegram.ext import CommandHandler
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram.ext import CallbackQueryHandler
from google.oauth2.credentials import Credentials
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, config_dict, dispatcher
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands

def drive_clean(update, context):
    if ospath.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pload(token)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='token.pickle not found', reply_to_message_id=update.message.message_id)
        return

    try:
        service = build('drive', 'v3', credentials=creds)
    except HttpError as error:
        context.bot.send_message(chat_id=update.effective_chat.id, text='An error occurred: %s' % error, reply_to_message_id=update.message.message_id)
        return

    query = "'%s' in parents and trashed = false" % config_dict['GDRIVE_ID']
    page_token = None

    while True:
        try:
            response = service.files().list(q=query, spaces='drive', fields='nextPageToken, files(id, name)', pageToken=page_token, includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
            files = response.get('files', [])
            for file in files:
                service.files().delete(fileId=file['id'], supportsAllDrives=True).execute()

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

        except HttpError as error:
            context.bot.send_message(chat_id=update.effective_chat.id, text='An error occurred: %s' % error, reply_to_message_id=update.message.message_id)
            break

    context.bot.send_message(chat_id=update.effective_chat.id, text='Drive cleanup completed! 🚮')


def drive_clean_confirmation(update, context):
    keyboard = [[InlineKeyboardButton("I am 100% sure", callback_data='drive_clean')],
                [InlineKeyboardButton("No, Cancel", callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Are you sure to start drive cleanup? 🗑 This can not be undone.', reply_markup=reply_markup)


def button_response(update, context):
    query = update.callback_query
    if query.data == 'drive_clean':
        drive_clean(update, context)
        query.message.edit_reply_markup(reply_markup=None)
        query.message.delete()
    elif query.data == 'cancel':
        context.bot.send_message(chat_id=update.effective_chat.id, text='Drive cleanup cancelled!')
        query.message.delete()


driveclean_handler = CommandHandler(BotCommands.DriveCleanCommand, drive_clean_confirmation, filters=CustomFilters.owner_filter)

dispatcher.add_handler(driveclean_handler)
dispatcher.add_handler(CallbackQueryHandler(button_response))
