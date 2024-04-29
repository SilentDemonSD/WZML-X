class WZMLConstants:
    ST_START_BN1_NAME = "Repo"
    ST_START_BN1_URL = "https://www.github.com/weebzone/WZML-1"
    ST_START_BN2_NAME = "Updates"
    ST_START_BN2_URL = "https://t.me/WZML_X"
    ST_START_MSG = (
        "<i>This is a description of the bot's functionality.</i>"
        "<i>Type {help_command} to get a list of available commands</i>"
    )
    ST_START_BOTPM = "<i>Bot started. Use /start command to send files and links to the bot's private messages.</i>"
    ST_START_UNAUTH = "<i>You are not an authorized user. Deploy your own WZML-X Mirror-Leech bot.</i>"

    ST_OWN_BOT_TOKEN = "Your own bot token"
    ST_USED_TOKEN = "Temporary token already used. Kindly generate a new one if you haven't already."
    ST_LOGGED_PASSWORD = "Bot already logged in via password. No need to accept temp tokens."
    ST_ACTIVATE_BUTTON = "Activate Temporary Token"
    ST_TOKEN_MSG = f'<b><u>Generated Temporary Login Token!</u></b>\n\n' f'<b>Temp:</b> <code>{token}</code>\n' f'<b>Validity:</b> {validity}'

    ST_ACTIVATED_TEMP_TOKEN = "✅️ Activated ✅" 

    ST_LOGGED_IN = "<b>Already Bot Login In!</b>"
    ST_INVALID_PASS = "<b>Invalid Password!</b>\n\nKindly put the correct Password ."
    ST_PASS_LOGGED = "<b>Bot Permanent Login Successfully!</b>"
    ST_LOGIN_USED = "<b>Bot Login Usage :</b>\n\n<code>/cmd [password]</code>"

    ST_LOGGED_OUT = "<b>Bot Logged Out!</b>"

    ST_LOG_DISPLAY_BT = "📑 Log Display"
    ST_WEB_PASTE_BT = "📨 Web Paste (SB)"

    ST_BASIC_BT = "📚 Basic"
    ST_USER_BT = "👥 Users"
    ST_MICS_BT = "🎤 Mics"
    ST_O_S_BT = "👑 Owner & Sudos"
    ST_CLOSE_BT = "🔒 Close"
    ST_HELP_HEADER = (
        "㊂ <b><i>Help Guide Menu!</i></b>\n\n<b>NOTE: <i>Click on any CMD to see more minor detalis.</i></b>"
    )

    ST_BASIC_CMDS = "/start /help /restart /stats /log /token"
    ST_USER_CMDS = "/useradd /userdel /userdelall"
    ST_MICS_CMDS = "/mics /micsdel /micsdelall"
    ST_O_S_CMDS = "/logs /sh /eval /id /promote /depromote /ban /unban /mute /unmute /restart /stats"

    ST_BASIC_DESC = "Basic commands for bot usage."
    ST_USER_DESC = "Commands for managing users."
    ST_MICS_DESC = "Commands for managing micro-related features."
    ST_OWNER_DESC = "Commands for bot owner and sudo users."

    ST_BOT_STATS = f'➲ <b><i>BOT STATISTICS :</i></b>\n\n' f'➲ <b>Bot Uptime :</b> {bot_uptime}\n\n' f'➲ <b><i>RAM (M
