from pyrogram import enums
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, user_data, LOGGER, DATABASE_URL, OWNER_ID, dispatcher, config_dict
from bot.helper.telegram_helper.message_utils import *
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.bot_utils import update_user_ldata

def caption_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name
    buttons = ButtonMaker()

    if config_dict['PAID_SERVICE'] is True:
        if not user_data[user_id].get('is_paid') and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Caption Feature.", context.bot, update.message)
            return
    buttons.sbutton("🛠 Change Font Style", f"capfont {user_id_} font")
    button = buttons.build_menu(2)
    if (BotCommands.CaptionCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        hlp_me = "<b>Send text with format along with command line:</b>\n"
        hlp_me += "<code>/cmd</code> {text} |previousname:newname:times (optional)\n\n"
        hlp_me += f"<b>Example:</b> /{BotCommands.CaptionCommand} " + "{filename}\n"
        hlp_me += '&lt;b&gt;Fork WZML Here : &lt;a href="link"&gt;Click Here&lt;/a&gt;&lt;/b&gt;|Fork:Star|Here:Now:1|WZML\n\n'
        hlp_me += "Output : Hi there.txt\nStar Now : Click Here\n\n"
        hlp_me += "<b>Explanation :</b> Here, Fork changed to Star, Here changed to Now, only 1 time and WZML is removed.\n\n"
        hlp_me += "<b>Custom Fillings:</b>\n"
        hlp_me += "{filename} - Filename of the File <i>(Note: This name already would be Changed if you set prefix or remname or suffix)</i>\n"
        hlp_me += "{size} - Size of the File\n\n"
        hlp_me += '''<b>Filter Notes:</b>
1. All HTML tags are Supported for Caption, you can set Hyperlink by using &lt;a&gt; anchor tag.

2. All Spaces are sensitive, if you give space unnecessarily, it will not work.

3. Use | for different changes, you can use as many times you need. If you keep single word or letter, it will be Removed and you can Change Specific Work or letter by : separator respectively. (optional)

4. For Changing, A work or Letter in a Limited no. of Times, use again : separator to specify no. of times to remove. (optional)

5. For New Line, Just Press Simple Enter on your Keyboard.'''
        sendMarkup(hlp_me, context.bot, update.message, button)
    else:
        lm = sendMessage(f"<b>Please Wait....Processing🤖</b>", context.bot, update.message)
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        caption_ = txt
        update_user_ldata(user_id_, 'caption', caption_)
        if DATABASE_URL:
            DbManger().update_userval(user_id_, 'caption', caption_)
            LOGGER.info(f"User : {user_id_} Caption is Saved in DB")
        editMessage(f"<b><u><a href='tg://user?id={user_id_}'>{u_men}</a>'s Caption is Set Successfully :</u></b>\n\n<b>• Caption Text: </b>{txt}", lm, button)

def userlog_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if config_dict['PAID_SERVICE'] is True:
        if not user_data[user_id].get('is_paid') and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Dump Feature.", context.bot, update.message)
            return
    if (BotCommands.UserLogCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        help_msg = "<b>Send channel id after command:</b>"
        help_msg += f"\n<code>/{BotCommands.UserLogCommand}" + " -100xxxxxxx" + "</code>\n"
        help_msg += "\n<b>By Replying to Message (Including Channel ID):</b>"
        help_msg += f"\n<code>/{BotCommands.UserLogCommand}" + " {message}" + "</code>"
        sendMessage(help_msg, context.bot, update.message)
        return
    lm = sendMessage("Checking your Channel ID... 🛃", context.bot, update.message)          
    pre_send = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    if len(pre_send) > 1:
        dumpid_ = pre_send[1]
    elif reply_to is not None:
        dumpid_ = reply_to.text
    else:
        dumpid_ = ""
    if not dumpid_.startswith('-100'):
        editMessage("<i><b>Your Channel ID Should Start with</b> -100xxxxxxxx, <u>Retry Again</u> !!</i>", lm)
        return
    dumpid_ = int(dumpid_.strip())
    try:
        editMessage("<i>Checking Your Channel Interaction ...</i> ♻️", lm)
        bot.sendMessage(chat_id=dumpid_, text=f'''╭─《 WZML DUMP CHANNEL 》
│
├🆔 <b>UserLog ID :</b> <code>{dumpid_}</code>
│
╰📂 <i>From Now On, The Bot will Send you Files in this Channel !!</i>''',  parse_mode='HTML')
    except Exception as err:
        editMessage(f"<i>Make Sure You have Added the Bot as Admin with Post Permission, Retry Again.</i>\n\nError : {err}", lm)
        return
    update_user_ldata(user_id_, 'userlog', str(dumpid_))
    if DATABASE_URL:
        DbManger().update_userval(user_id_, 'userlog', str(dumpid_))
        LOGGER.info(f"User : {user_id_} LeechLog ID Saved in DB")
    editMessage(f"<b><a href='tg://user?id={user_id_}'>{u_men}</a>'s Dump Channel ID Saved Successfully...🛸</b>", lm)


def remname_set(update, context):
    user_id_ = update.message.from_user.id 
    u_men = update.message.from_user.first_name

    if config_dict['PAID_SERVICE'] is True:
        if not user_data[user_id].get('is_paid') and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Remname Feature.", context.bot, update.message)
            return
    if (BotCommands.RemnameCommand in update.message.text) and (len(update.message.text.split(' ')) == 1):
        hlp_me = "<b>Send text with format along with command line:</b>\n"
        hlp_me += "<code>/cmd</code> previousname:newname:times|previousname:newname:times\n\n"
        hlp_me += f"<b>Example:</b> /{BotCommands.RemnameCommand} " + "Fork:Star|Here:Now:1|WZML\n\n"
        hlp_me += "Output : Star Now : Click Here.txt\n\n"
        hlp_me += "<b>Explanation :</b> Here, Fork changed to Star, Here changed to Now, only 1 time and WZML is removed.\n\n"
        hlp_me += '''<b>Filter Notes:</b>
1. All Spaces are sensitive, if you give space unnecessarily, it will not work.

2. Use | for different changes, you can use as many times you need. If you keep single word or letter, it will be Removed and you can Change Specific Work or letter by : separator respectively. (optional)

3. For Changing, A work or Letter in a Limited no. of Times, use again : separator to specify no. of times to remove. (optional)

4. Filename is Changed according to your Remname, so No need to change in Caption, again for filename.''' 
        sendMessage(hlp_me, context.bot, update.message)
    else:
        lm = sendMessage(f"<b>Please Wait....Processing🤖</b>", context.bot, update.message)
        pre_send = update.message.text.split(" ", maxsplit=1)
        reply_to = update.message.reply_to_message
        if len(pre_send) > 1:
            txt = pre_send[1]
        elif reply_to is not None:
            txt = reply_to.text
        else:
            txt = ""
        remname_ = txt
        update_user_ldata(user_id_, 'remname', remname_)
        if DATABASE_URL:
            DbManger().update_userval(user_id_, 'remname', remname_)
            LOGGER.info(f"User : {user_id_} Remname is Saved in DB")
        editMessage(f"<b><a href='tg://user?id={user_id_}'>{u_men}</a>'s Remname is Set Successfully :</b>\n\n<b>• Remname Text: </b>{txt}", lm)
