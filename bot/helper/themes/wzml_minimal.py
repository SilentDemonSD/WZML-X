#!/usr/bin/env python3
class WZMLStyle:
    """Class containing various style messages and texts for the bot."""

    # ---------------------
    # Bot Messages
    # ---------------------

    #: Message to display when the bot is starting
    ST_BN1_NAME = 'Repo'
    ST_BN1_URL = 'https://www.github.com/weebzone/WZML-X'
    ST_BN2_NAME = 'Updates'
    ST_BN2_URL = 'https://t.me/WZML_X'
    ST_MSG = '''<i>This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram or to ddl servers.</i>
<b>Type {help_command} to get a list of available commands</b>'''
    ST_BOTPM = '''<i>Now, This bot will send all your files and links here. Start Using ...</i>'''
    ST_UNAUTH = '''<i>You Are not authorized user! Deploy your own WZML-X Mirror-Leech bot</i>'''
    OWN_TOKEN_GENERATE = '''<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>'''
    USED_TOKEN = '''<b>Temporary Token already used!</b>\n\n<i>Kindly generate a new one.</i>'''
    LOGGED_PASSWORD = '''<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>'''
    ACTIVATE_BUTTON = 'Activate Temporary Token'
    TOKEN_MSG = '''<b><u>Generated Temporary Login Token!</u></b>
<b>Temp Token:</b> <code>{token}</code>
<b>Validity:</b> {validity}'''

    # ---------------------
    # Callback Messages
    # ---------------------

    #: Message to display when the temporary token is activated
    ACTIVATED = '✅️ Activated ✅'

    # ---------------------
    # Login Messages
    # ---------------------

    #: Message to display when the bot is already logged in
    LOGGED_IN = '<b>Already Bot Login In!</b>'
    #: Message to display when the provided password is invalid
    INVALID_PASS = '<b>Invalid Password!</b>\n\nKindly put the correct Password .'
    #: Message to display when the bot is permanently logged in via password
    PASS_LOGGED = '<b>Bot Permanent Login Successfully!</b>'
    #: Message to display when the login usage
    LOGIN_USED = '<b>Bot Login Usage :</b>\n\n<code>/cmd [password]</code>'

    # ---------------------
    # Log Messages
    # ---------------------

    #: Message to display when showing the log
    LOG_DISPLAY_BT = '📑 Log Display'
    #: Message to display when pasting from the web
    WEB_PASTE_BT = '📨 Web Paste (SB)'

    # ---------------------
    # Help Messages
    # ---------------------

    #: Header for the help guide menu
    HELP_HEADER = "㊂ <b><i>Help Guide Menu!</i></b>\n\n<b>NOTE: <i>Click on any CMD to see more minor detalis.</i></b>"

    # ---------------------
    # Stats Messages
    # ---------------------

    #: Message to display bot statistics
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
    
    '''
    #: Message to display OS statistics
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
    '''
    #: Message to display repository statistics
    REPO_STATS = '''⌬ <b><i>REPO STATISTICS :</i></b>
┠ <b>Bot Updated :</b> {last_commit}
┠ <b>Current Version :</b> {bot_version}
┠ <b>Latest Version :</b> {lat_version}
┖ <b>Last ChangeLog :</b> {commit_details}

⌬ <b><i>REMARKS :</i></b> <code>{remarks}</code>
    '''
    #: Message to display bot limitations
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
    '''

    # ---------------------
    # Restart Messages
    # ---------------------

    #: Message to display when the bot is restarting
    RESTARTING = '<i>Restarting...</i>'
    #: Message to display when the bot has been restarted successfully
    RESTART_SUCCESS = '''⌬ <b><i>Restarted Successfully!</i></b>
┠ <b>Date:</b> {date}
┠ <b>Time:</b> {time}
┠ <b>TimeZone:</b> {timz}
┖ <b>Version:</b> {version}'''
    #: Message to display when the bot has been restarted
    RESTARTED = '''⌬ <b><i>Bot Restarted!</i></b>'''

    # ---------------------
    # Ping Messages
    # ---------------------

    #: Message to display when starting the ping
    PING = '<i>Starting Ping..</i>'
    #: Message to display the ping value
    PING_VALUE = '<b>Pong</b>\n<code>{value} ms..</code>'

    # ---------------------
    # Download Messages
    # ---------------------

    #: Message to display when a task is started
    LINKS_START = """<b><i>Task Started</i></b>
┠ <b>Mode:</b> {Mode}
┖ <b>By:</b> {Tag}\n\n"""
    #: Message to display the source of the download
    LINKS_SOURCE = """➲ <b>Source:</b>
┖ <b>Added On:</b> {On}
------------------------------------------
{Source}
------------------------------------------\n\n"""

    # ---------------------
    # Reply Messages
    # ---------------------

    #: Message to display when sending a private message
    PM_START =            "➲ <b><u>Task Started :</u></b>\n┃\n┖ <b>Link:</b> <a href='{msg_link}'>Click Here</a>"
    #: Message to display when starting a leech
    L_LOG_START =           "➲ <b><u>Leech Started :</u></b>\n┃\n┠ <b>User :</b> {mention} ( #ID{uid} )\n┖ <b>Source :</b> <a href='{msg_link}'>Click Here</a>"

    # ---------------------
    # Upload Messages
    # ---------------------

    #: Message to display the name of the upload
    NAME =                  '<b><i>{Name}</i></b>\n┃\n'
    #: Message to display the size of the upload
    SIZE =                  '┠ <b>Size: </b>{Size}\n'
    #: Message to display the elapsed time of the upload
    ELAPSE =                '┠ <b>Elapsed: </b>{Time}\n'
    #: Message to display the mode of the upload
    MODE =                  '┠ <b>Mode: </b>{Mode}\n'

    # ---------------------
    # Leech Messages
    # ---------------------

    #: Message to display the total files in a leech
    L_TOTAL_FILES =         '┠ <b>Total Files: </b>{Files}\n'
    #: Message to display the corrupted files in a leech
    L_CORRUPTED_FILES =     '┠ <b>Corrupted Files: </b>{Corrupt}\n'
    #: Message to display the user who initiated the leech
    L_CC =                  '┖ <b>By: </b>{Tag}\n\n'
    #: Message to display when the files have been sent to the user
    PM_BOT_MSG =            '➲ <b><i>File(s) have been Sent above</i></b>'
    #: Message to display when the files have been sent to the bot's private message
    L_BOT_MSG =             '➲ <b><i>File(s) have been Sent to Bot PM (Private)</i></b>'
    #: Message to display when the files have been sent and the user can access them via links
    L_LL_MSG =              '➲ <b><i>File(s) have been Sent. Access via Links...</i></b>\n'

    # ---------------------
    # Mirror Messages
    # ---------------------

    #: Message to display the mimetype of the mirror
    M_TYPE =                '┠ <b>Type: </b>{Mimetype}\n'
    #: Message to display the subfolders in the mirror
    M_SUBFOLD =             '┠ <b>SubFolders: </b>{Folder}\n'
    #: Message to display the total files in the mirror
    TOTAL_FILES =           '┠ <b>Files: </b>{Files}\n'
    #: Message to display the remote path of the mirror
    RCPATH =                '┠ <b>Path: </b><code>{RCpath}</code>\n'
    #: Message to display the user who initiated the mirror
    M_CC =                  '┖ <b>By: </b>{Tag}\n\n'
    #: Message to display when the links have been sent to the bot's private message
    M_BOT_MSG =             '➲ <b><i>Link(s) have been Sent to Bot PM (Private)</i></b>'

    # ---------------------
    # Buttons Messages
    # ---------------------

    #: Message to display the cloud link button
    CLOUD_LINK =      '☁️ Cloud Link'
    #: Message to display the save message button
    SAVE_MSG =        '📨 Save Message'
    #: Message to display the rclone link button
    RCLONE_LINK =     '♻️ RClone Link'
    #: Message to display the ddl link button
    DDL_LINK =        '📎 {Serv} Link'
    #: Message to display the source link button
    SOURCE_URL =      '🔐 Source Link'
    #: Message to display the index link button
    INDEX_LINK_F =    '🗂 Index Link'
    #: Message to display the index link button
    INDEX_LINK_D =    '⚡ Index Link'
    #: Message to display the view link button
    VIEW_LINK =       '🌐 View Link'
    #: Message to display the check pm button
    CHECK_PM =        '📥 View in Bot PM'
    #: Message to display the check ll button
    CHECK_LL =        '🖇 View in Links Log'
    #: Message to display the media info button
    MEDIAINFO_LINK =  '📃 MediaInfo'
    #: Message to display the screenshots button
    SCREENSHOTS =     '🖼 ScreenShots'

    # ---------------------
    # Overall Messages
    # ---------------------

    #: Message to display the status name
    STATUS_NAME =       '<b><i>{Name}</i></b>'

    #: Message to display the processed status
    PROCESSED =         '\n┠ <b>Processed:</b> {Processed}'
    #: Message to display the status
    STATUS =            '\n┠ <b>Status:</b> <a href="{Url}">{Status}</a>'
    #: Message to display the eta
    ETA =                                                ' | <b>ETA:</b> {Eta}'
    #: Message to display the speed
    SPEED =             '\n┠ <b>Speed:</b> {Speed}'
    #: Message to display the elapsed time
    ELAPSED =                                     ' | <b>Elapsed:</b> {Elapsed}'
    #: Message to display the engine
    ENGINE =            '\n┠ <b>Engine:</b> {Engine}'
    #: Message to display the mode
    STA_MODE =          '\n┠ <b>Mode:</b> {Mode}'
    #: Message to display the seeders
    SEEDERS =           '\n┠ <b>Seeders:</b> {Seeders} | '
    #: Message to display the leechers
    LEECHERS =                                           '<b>Leechers:</b> {Leechers}'

    #: Message to display the size of the seed
    SEED_SIZE =      '\n┠ <b>Size: </b>{Size}'
    #: Message to display the speed of the seed
    SEED_SPEED =     '\n┠ <b>Speed: </b> {Speed} | '
    #: Message to display the uploaded data
    UPLOADED =                                     '<b>Uploaded: </b> {Upload}'
    #: Message to display the ratio
    RATIO =          '\n┠ <b>Ratio: </b> {Ratio} | '
    #: Message to display the time
    TIME =                                         '<b>Time: </b> {Time}'
    #: Message to display the engine of the seed
    SEED_ENGINE =    '\n┠ <b>Engine:</b> {Engine}'

    #: Message to display the size of the non-progressive and non-seeding items
    STATUS_SIZE =    '\n┠ <b>Size: </b>{Size}'
    #: Message to display the engine of the non-progressive and non-seeding items
    NON_ENGINE =     '\n┠ <b>Engine:</b> {Engine}'

    #: Message to display the footer
    FOOTER = '⌬ <b><i>Bot Stats</i></b>\n'
    #: Message to display the tasks
    TASKS =  '┠ <b>Tasks:</b> {Tasks}\n'
    #: Message to display the bot tasks
    BOT_TASKS = '┠ <b>Tasks:</b> {Tasks}/{Ttask} | <b>AVL:</b> {Free}\n'
    #: Message to display the cpu
    Cpu = '┠ <b>CPU:</b> {cpu}% | '
    #: Message to display the free memory
    FREE =                      '<b>F:</b> {free} [{free_p}%]'
    #: Message to display the ram
    Ram = '\n┠ <b>RAM:</b> {ram}% | '
    #: Message to display the uptime
    uptime =                     '<b>UPTIME:</b> {uptime}'
    #: Message to display the download speed
    DL = '\n┖ <b>DL:</b> {DL}/s | '
    #: Message to display the upload speed
    UL =                        '<b>UL:</b> {UL}/s'

    #: Message to display the previous button
    PREVIOUS = '⫷'
    #: Message to display the refresh button
    REFRESH = 'ᴘᴀɢᴇs\n{Page}'
    #: Message to display the next button
    NEXT = '⫸'

    # ---------------------
    # Stop Duplicate Messages
    # ---------------------

    #: Message to display when a duplicate file or folder is found
    STOP_DUPLICATE = 'File/Folder is already available in Drive.\nHere are {content} list results:'

    # ---------------------
    # Count Messages
    # ---------------------

    #: Message to display when counting items
    COUNT_MSG = '<b>Counting:</b> <code>{LINK}</code>'
    #: Message to display the name of the count
    COUNT_NAME = '<b><i>{COUNT_NAME}</i></b>\n┃\n'
    #: Message to display the size of the count
    COUNT_SIZE = '┠ <b>Size: </b>{COUNT_SIZE}\n'
    #: Message to display the type of the count
    COUNT_TYPE = '┠ <b>Type: </b>{COUNT_TYPE}\n'
    #: Message to display the subfolders in the count
    COUNT_SUB =  '┠ <b>SubFolders: </b>{COUNT_SUB}\n'
    #: Message to display the files in the count
    COUNT_FILE = '┠ <b>Files: </b>{COUNT_FILE}\n'
    #: Message to display the user who initiated the count
    COUNT_CC =   '┖ <b>By: </b>{COUNT_CC}\n'

    # ---------------------
    # List Messages
    # ---------------------

    #: Message to display when searching for an item
    LIST_SEARCHING = '<b>Searching for <i>{NAME}</i></b>'
    #: Message to display the found items
    LIST_FOUND = '<b>Found {NO} result for <i>{NAME}</i></b>'
    #: Message to display when no items are found
    LIST_NOT_FOUND = 'No result found for <i>{NAME}</i>'

    # ---------------------
    # Mirror Status Messages
    # ---------------------

    #: Message to display when there are no active downloads
    NO_ACTIVE_DL = '''<i>No
