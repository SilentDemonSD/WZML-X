# WZMLStyle class for defining various bot messages and buttons
class WZMLStyle:

    # Constants for the 'start' command
    ST_BN1_NAME = 'Repo'  # Name of the first button
    ST_BN1_URL = 'https://www.github.com/weebzone/WZML-X'  # URL of the first button
    ST_BN2_NAME = 'Updates'  # Name of the second button
    ST_BN2_URL = 'https://t.me/WZML_X'  # URL of the second button
    ST_MSG = '''<i>This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram or to ddl servers.</i>
<b>Type {help_command} to get a list of available commands</b>'''  # Main message for the 'start' command
    ST_BOTPM = '''<i>Now, This bot will send all your files and links here. Start Using ...</i>'''  # Message for sending files and links to the bot's private messages
    ST_UNAUTH = '''<i>You Are not authorized user! Deploy your own WZML-X Mirror-Leech bot</i>'''  # Message for unauthorized users

    # Constants for the 'token' command
    OWN_TOKEN_GENERATE = '''<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>'''  # Message for temporary token not belonging to the user
    USED_TOKEN = '''<b>Temporary Token already used!</b>\n\n<i>Kindly generate a new one.</i>'''  # Message for already used temporary token
    LOGGED_PASSWORD = '''<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>'''  # Message for bot already logged in via password
    ACTIVATE_BUTTON = 'Activate Temporary Token'  # Button text for activating temporary token
    TOKEN_MSG = '''<b><u>Generated Temporary Login Token!</u></b>
<b>Temp Token:</b> <code>{token}</code>
<b>Validity:</b> {validity}'''  # Message for generated temporary login token

    # Constants for the 'token_callback' function
    ACTIVATED = '✅️ Activated ✅'  # Message for activated temporary token

    # Constants for the 'login' command
    LOGGED_IN = '<b>Already Bot Login In!</b>'  # Message for bot already logged in
    INVALID_PASS = '<b>Invalid Password!</b>\n\nKindly put the correct Password .'  # Message for invalid password
    PASS_LOGGED = '<b>Bot Permanent Login Successfully!</b>'  # Message for successful permanent login
    LOGIN_USED = '<b>Bot Login Usage :</b>\n\n<code>/cmd [password]</code>'  # Message for bot login usage

    # Constants for the 'log' command
    LOG_DISPLAY_BT = '📑 Log Display'  # Button text for displaying logs
    WEB_PASTE_BT = '📨 Web Paste (SB)'  # Button text for web paste

    # Constants for the 'bot_help' command
    BASIC_BT = 'Basic'  # Button text for basic commands
    USER_BT = 'Users'  # Button text for user-related commands
    MICS_BT = 'Mics'  # Button text for micro-related commands
    O_S_BT = 'Owner & Sudos'  # Button text for owner and sudo-related commands
    CLOSE_BT = 'Close'  # Button text for closing the help menu
    HELP_HEADER = "㊂ <b><i>Help Guide Menu!</i></b>\n\n<b>NOTE: <i>Click on any CMD to see more minor detalis.</i></b>"  # Header for the help menu

    # Constants for the 'stats' function
    BOT_STATS = '''⌬ <b><i>BOT STATISTICS :</i></b>
┖ <b>Bot Uptime :</b> {bot_uptime}

┎ <b><i>RAM ( MEMORY ) :</i></b>
┃ {ram_bar} {ram}%
┖ <b>U :</b> {ram_u} | <b>F :</b> {ram_f} | <b>T :</b> {ram_t}

┎ <b><i>SWAP MEMORY :</i></b>
┃ {swap_bar} {swap}%
┖ <b>U :</b> {swap_u} | <b>F :</b> {swap_f} | <b>T :</b> {swap_t}

┎ <b><i>DISK :</i></b>
┃ {disk_bar} {disk}%
┃ <b>Total Disk Read :</b> {disk_read}
┃ <b>Total Disk Write :</b> {disk_write}
┖ <b>U :</b> {disk_u} | <b>F :</b> {disk_f} | <b>T :</b> {disk_t}
    
    '''  # Stats for the bot
    SYS_STATS = '''⌬ <b><i>OS SYSTEM :</i></b>
┠ <b>OS Uptime :</b> {os_uptime}
┠ <b>OS Version :</b> {os_version}
┖ <b>OS Arch :</b> {os_arch}

⌬ <b><i>NETWORK STATS :</i></b>
┠ <b>Upload Data:</b> {up_data}
┠ <b>Download Data:</b> {dl_data}
┠ <b>Pkts Sent:</b> {pkt_sent}k
┠ <b>Pkts Received:</b> {pkt_recv}k
┖ <b>Total I/O Data:</b> {tl_data}

┎ <b>CPU :</b>
┃ {cpu_bar} {cpu}%
┠ <b>CPU Frequency :</b> {cpu_freq}
┠ <b>System Avg Load :</b> {sys_load}
┠ <b>P-Core(s) :</b> {p_core} | <b>V-Core(s) :</b> {v_core}
┠ <b>Total Core(s) :</b> {total_core}
┖ <b>Usable CPU(s) :</b> {cpu_use}
    '''  # Stats for the operating system
    REPO_STATS = '''⌬ <b><i>REPO STATISTICS :</i></b>
┠ <b>Bot Updated :</b> {last_commit}
┠ <b>Current Version :</b> {bot_version}
┠ <b>Latest Version :</b> {lat_version}
┖ <b>Last ChangeLog :</b> {commit_details}

⌬ <b>REMARKS :</b> <code>{remarks}</code>
    '''  # Stats for the repository
    BOT_LIMITS = '''⌬ <b><i>BOT LIMITATIONS :</i></b>
┠ <b>Direct Limit :</b> {DL} GB
┠ <b>Torrent Limit :</b> {TL} GB
┠ <b>GDrive Limit :</b> {GL} GB
┠ <b>YT-DLP Limit :</b> {YL} GB
┠ <b>Playlist Limit :</b> {PL}
┠ <b>Mega Limit :</b> {ML} GB
┠ <b>Clone Limit :</b> {CL} GB
┖ <b>Leech Limit :</b> {LL} GB

┎ <b>Token Validity :</b> {TV}
┠ <b>User Time Limit :</b> {UTI} / task
┠ <b>User Parallel Tasks :</b> {UT}
┖ <b>Bot Parallel Tasks :</b> {BT}
    '''  # Limitations for the bot

    # Constants for the 'restart' command
    RESTARTING = '<i>Restarting...</i>'  # Message for restarting

    # Constants for the 'restart_notification' function
    RESTART_SUCCESS = '''⌬ <b><i>Restarted Successfully!</i></b>
┠ <b>Date:</b> {date}
┠ <b>Time:</b> {time}
┠ <b>TimeZone:</b> {timz}
┖ <b>Version:</b> {version}'''  # Message for successful restart
    RESTARTED = '''⌬ <b><i>Bot Restarted!</i></b>'''  # Message for bot restarted

    # Constants for the 'ping' command
    PING = '<i>Starting Ping..</i>'  # Message for starting ping
    PING_VALUE = '<b>Pong</b>\n<code>{value} ms..</code>'  # Message for ping value

    # Constants for the 'onDownloadStart' function
    LINKS_START = """<b><i>Task Started</i></b>
┠ <b>Mode:</b> {Mode}
┖ <b>By:</b> {Tag}\n\n"""  # Message for task started
    LINKS_SOURCE = """➲ <b>Source:</b>
┖ <b>Added On:</b> {On}
------------------------------------------
{Source}
------------------------------------------\n\n"""  # Message for task source

    # Constants for the '__msg_to_reply' function
    PM_START =            "➲ <b><u>Task Started :</u></b>\n┃\n┖ <b>Link:</b> <a href='{msg_link}'>Click Here</a>"  # Message for task started in private messages
    L_LOG_START =           "➲ <b><u>Leech Started :</u></b>\n┃\n┠ <b>User :</b> {mention} ( #ID{uid} )\n┖ <b>Source :</b> <a href='{msg_link}'>Click Here</a>"  # Message for leech started

    # Constants for the 'onUploadComplete' function
    NAME =                  '<b><i>{Name}</i></b>\n┃\n'  # Message for file name
    SIZE =                  '┠ <b>Size: </b>{Size}\n'  # Message for file size
    ELAPSE =                '┠ <b>Elapsed: </b>{Time}\n'  # Message for elapsed time
    MODE =                  '┠ <b>Mode: </b>{Mode}\n'  # Message for mode

    # Constants for leech
    L_TOTAL_FILES =         '┠ <b>Total Files: </b>{Files}\n'  # Message for total files
    L_CORRUPTED_FILES =     '┠ <b>Corrupted Files: </b>{Corrupt}\n'  # Message for corrupted files
    L_CC =                  '┖ <b>By: </b>{Tag}\n\n'  # Message for completed by
    PM_BOT_MSG =            '➲ <b><i>File(s) have been Sent above</i></b>'  # Message for files sent in private messages
    L_BOT_MSG =             '➲ <b><i>File(s) have been Sent to Bot PM (Private)</i></b>'  # Message for files sent to bot's private messages
    L_LL_MSG =              '➲ <b><i>File(s) have been Sent. Access via Links...</i></b>\n'  # Message for files sent with links

    # Constants for mirror
    M_TYPE =                '┠ <b>Type: </b>{Mimetype}\n'  # Message for file type
    M_SUBFOLD =             '┠ <b>SubFolders: </b>{Folder}\n'  # Message for subfolders
    TOTAL_FILES =           '┠ <b>Files: </b>{Files}\n'  # Message for total files
    RCPATH =                '┠ <b>Path: </b><code>{RCpath}</code>\n'  # Message for file path
    M_CC =                  '┖ <b>By: </b>{Tag}\n\n'  # Message for completed by
    M_BOT_MSG =             '➲ <b><i>Link(s) have been Sent to Bot PM (Private)</i></b>'  # Message for links sent to bot's private messages

    # Constants for buttons
    CLOUD_LINK =      '☁️ Cloud Link'  # Button text for cloud link
    SAVE_MSG =        '📨 Save Message'  # Button text for save message
    RCLONE_LINK =     '♻️ RClone Link'  # Button text for rclone link
    DDL_LINK =        '📎 {Serv} Link'  # Button text for ddl link
    SOURCE_URL =      '🔐 Source Link'  # Button text for source link
    INDEX_LINK_F =    '🗂 Index Link'  # Button text for index link (folder)
    INDEX_LINK_D =    '⚡ Index Link'  # Button text for index link (direct)
    VIEW_LINK =       '🌐 View Link'  # Button text for view link
    CHECK_PM =        '📥 View in Bot PM'  # Button text for view in bot private messages
    CHECK_LL =        '🖇 View in Links Log'  # Button text for view in links log
    MEDIAINFO_LINK =  '📃 MediaInfo'  # Button text for media info link
    SCREENSHOTS =     '🖼 ScreenShots'  # Button text for screenshots
