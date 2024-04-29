#!/usr/bin/env python3
class WZMLStyle:
    """Class containing various message styles for the WZML bot."""

    # ----------------------
    # Message styles for bot startup
    # ----------------------

    #: The name of the first bot button
    ST_BN1_NAME: str = 'Repo'
    #: The URL of the first bot button
    ST_BN1_URL: str = 'https://www.github.com/weebzone/WZML-X'
    #: The name of the second bot button
    ST_BN2_NAME: str = 'Updates'
    #: The URL of the second bot button
    ST_BN2_URL: str = 'https://t.me/WZML_X'
    #: The startup message for the bot
    ST_MSG: str = '''<i>This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram or to ddl servers.</i>
<b>Type {help_command} to get a list of available commands</b>'''
    #: The message to be sent when the bot is added to a new chat
    ST_BOTPM: str = '''<i>Now, This bot will send all your files and links here. Start Using ...</i>'''
    #: The message to be sent when the user is not authorized
    ST_UNAUTH: str = '''<i>You Are not authorized user! Deploy your own WZML-X Mirror-Leech bot</i>'''
    # ----------------------

    # ----------------------
    # Message styles for bot statistics
    # ----------------------

    #: The bot statistics message
    BOT_STATS: str = '''⌬ <b><i>BOT STATISTICS :</i></b>
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
    #: The system statistics message
    SYS_STATS: str = '''⌬ <b><i>OS SYSTEM :</i></b>
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
    #: The repository statistics message
    REPO_STATS: str = '''⌬ <b><i>REPO STATISTICS :</i></b>
┠ <b>Bot Updated :</b> {last_commit}
┠ <b>Current Version :</b> {bot_version}
┠ <b>Latest Version :</b> {lat_version}
┖ <b>Last ChangeLog :</b> {commit_details}

⌬ <b>REMARKS :</b> <code>{remarks}</code>
    '''
    #: The bot limitations message
    BOT_LIMITS: str = '''⌬ <b><i>BOT LIMITATIONS :</i></b>
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
    # ----------------------

    # ----------------------
    # Message styles for bot restart
    # ----------------------

    #: The restarting message
    RESTARTING: str = '<i>Restarting...</i>'
    #: The restart success message
    RESTART_SUCCESS: str = '''⌬ <b><i>Restarted Successfully!</i></b>
┠ <b>Date:</b> {date}
┠ <b>Time:</b> {time}
┠ <b>TimeZone:</b> {timz}
┖ <b>Version:</b> {version}'''
    #: The restarted message
    RESTARTED: str = '''⌬ <b><i>Bot Restarted!</i></b>'''
    # ----------------------

    # ----------------------
    # Message styles for bot ping
    # ----------------------

    #: The ping message
    PING: str = '<i>Starting Ping..</i>'
    #: The ping value message
    PING_VALUE: str = '<b>Pong</b>\n<code>{value} ms..</code>'
    # ----------------------

    # ----------------------
    # Message styles for tasks listener
    # ----------------------

    #: The links start message
    LINKS_START: str = """<b><i>Task Started</i></b>
┠ <b>Mode:</b> {Mode}
┖ <b>By:</b> {Tag}\n\n"""
    #: The links source message
    LINKS_SOURCE: str = """➲ <b>Source:</b>
┖ <b>Added On:</b> {On}
------------------------------------------
{Source}
------------------------------------------\n\n"""
    #: The PM start message
    PM_START: str =            "➲ <b><u>Task Started :</u></b>\n┃\n┖ <b>Link:</b> <a href='{msg_link}'>Click Here</a>"
    #: The leech log start message
    L_LOG_START: str =           "➲ <b><u>Leech Started :</u></b>\n┃\n┠ <b>User :</b> {mention} ( #ID{uid} )\n┖ <b>Source :</b> <a href='{msg_link}'>Click Here</a>"

    #: The name message
    NAME: str =                  '<b><i>{Name}</i></b>\n┃\n'
    #: The size message
    SIZE: str =                  '┠ <b>Size: </b>{Size}\n'
    #: The elapsed message
    ELAPSE: str =                '┠ <b>Elapsed: </b>{Time}\n'
    #: The mode message
    MODE: str =                  '┠ <b>Mode: </b>{Mode}\n'

    #: The total files message (leech)
    L_TOTAL_FILES: str =         '┠ <b>Total Files: </b>{Files}\n'
    #: The corrupted files message (leech)
    L_CORRUPTED_FILES: str =     '┠ <b>Corrupted Files: </b>{Corrupt}\n'
    #: The leech complete message
    L_CC: str =                  '┖ <b>By: </b>{Tag}\n\n'
    #: The PM bot message
    PM_BOT_MSG: str =            '➲ <b><i>File(s) have been Sent above</i></b>'
    #: The leech bot message
    L_BOT_MSG: str =             '➲ <b><i>File(s) have been Sent to Bot PM (Private)</i></b>'
    #: The leech link message
    L_LL_MSG: str =              '➲ <b><i>File(s) have been Sent. Access via Links...</i></b>'

    #: The type message (mirror)
    M_TYPE: str =                '┠ <b>Type: </b>{Mimetype}\n'
    #: The subfolders message (mirror)
    M_SUBFOLD: str =             '┠ <b>SubFolders: </b>{Folder}\n'
    #: The total files message (mirror)
    TOTAL_FILES: str =           '┠ <b>Files: </b>{Files}\n'
    #: The rcpath message (mirror)
    RCPATH: str =                '┠ <b>Path: </b><code>{RCpath}</code>\n'
    #: The mirror complete message
    M_CC: str =                  '┖ <b>By: </b>{Tag}\n\n'
    #: The mirror bot message
    M_BOT_MSG: str =             '➲ <b><i>Link(s) have been Sent to Bot PM (Private)</i></b>'

    #: The cloud link button
    CLOUD_LINK: str =      '☁️ Cloud Link'
    #: The save message button
    SAVE_MSG: str =        '📨 Save Message'
    #: The rclone link button
    RCLONE_LINK: str =     '♻️ RClone Link'
    #: The ddl link button
    DDL_LINK: str =        '📎 {Serv} Link'
    #: The source url button
    SOURCE_URL: str =      '🔐 Source Link'
    #: The index link folder button
    INDEX_LINK_F: str =    '🗂 Index Link'
    #: The index link download button
    INDEX_LINK_D: str =    '⚡ Index Link'
    #: The view link button
    VIEW_LINK: str =       '🌐 View Link'
    #: The check pm button
    CHECK_PM: str =        '📥 View in Bot PM'
    #: The check ll button
    CHECK_LL: str =        '🖇 View in Links Log'
    #: The mediainfo link button
    MEDIAINFO_LINK: str =  '📃 MediaInfo'
    # ----------------------

    # ----------------------
    # Message styles for bot utils
    # ----------------------

    #: The status name message
    STATUS_NAME: str =       '<b><i>{Name}</i></b>'

    #####---------PROGRESSIVE STATUS-------
    #: The bar message
    BAR: str =               '\n┃ {Bar}'
    #: The processed message
    PROCESSED: str =         '\n┠ <b>Processed:</b> {Processed}'
    #: The status message
    STATUS: str =            '\n┠ <b>Status:</b> <a href="{Url}">{Status}</a>'
    #: The eta message
    ETA: str =               ' | <b>ETA:</b> {Eta}'
    #: The speed message
    SPEED: str =             '\n┠ <b>Speed:</b> {Speed}'
    #: The elapsed message
    ELAPSED: str =           ' | <b>Elapsed:</b> {Elapsed}'
    #: The engine message
    ENGINE: str =            '\n┠ <b>Engine:</b> {Engine}'
    #: The mode message
    STA_MODE: str =          '\n┠ <b>Mode:</b> {Mode}'
    #: The seeders message
    SEEDERS: str =           '\n┠ <b>Seeders:</b> {Seeders} | '
    #: The leechers message
    LEECHERS: str =         '<b>Leechers:</b> {Leechers}'

    #####---------SEEDING-------
    #: The seed size message
    SEED_SIZE: str =      '\n┠ <b>Size: </b>{Size}'
    #: The seed speed message
    SEED_SPEED: str =     '\n┠ <b>Speed: </b> {Speed} | '
    #: The uploaded message
    UPLOADED: str =                 '<b>Uploaded: </b> {Upload}'
    #: The ratio message
    RATIO: str =          '\n┠ <b>Ratio: </b> {Ratio} | '
    #: The time message
    TIME: str =           '\n┠ <b>Time: </b> {Time}'
    #: The seed engine message
    SEED_ENGINE: str =    '\n┠ <b>Engine:</b> {Engine}'

    #####---------NON-PROGRESSIVE + NON SEEDING-------
    #: The status size message
    STATUS_SIZE: str =    '\n┠ <b>Size: </b>{Size}'
    #: The non engine message
    NON_ENGINE: str =     '\n┠ <b>Engine:</b> {Engine}'

    #####---------OVERALL MSG FOOTER----------
    #: The user message
    USER: str =              '\n┠ <b>User:</b> <code>{User}</code> | '
    #: The id message
    ID: str =                                                        '<b>ID:</b> <code>{Id}</code>'
    #: The btsel message
    BTSEL: str =          '\n┠ <b>Select:</b> {Btsel}'
    #: The cancel message
    CANCEL: str =         '\n┖ {Cancel}\n\n'

    #: The footer message
    FOOTER: str = '⌬ <b><i>Bot Stats</i></b>\n'
    #: The tasks message
    TASKS: str =  '┠ <b>Tasks:</b> {Tasks}\n'
    #: The bot tasks message
    BOT_TASKS: str = '┠ <b>Tasks:</b> {Tasks}/{Ttask} | <b>AVL:</b> {Free}\n'
    #: The cpu message
    Cpu: str = '┠ <b>CPU:</b> {cpu}% | '
    #: The free message
    FREE: str =      '<b>F:</b> {free} [{free_p}%]'
    #: The ram message
    Ram: str = '\n┠ <b>RAM:</b> {ram}% | '
    #: The uptime message
    uptime: str =     '<b>UPTIME:</b> {uptime}'
    #: The dl message
    DL: str = '\n┖ <b>DL:</b> {DL}/s | '
    #: The ul message
    UL: str =                        '<b>UL:</b> {UL}/s'

    #####---------BUTTONS-------
    #: The previous button
    PREVIOUS: str = '⫷'
    #: The refresh button
    REFRESH: str = 'ᴘᴀɢᴇs\n{Page}'
    #: The next button
    NEXT: str = '⫸'
    # ----------------------

    # ----------------------
    # Message styles for clone
    # ----------------------

    #: The stop duplicate message
    STOP_DUPLICATE: str = 'File/Folder is already available in Drive.\nHere are {content} list results:'
    # ----------------------

    # ----------------------
    # Message styles for gd_count
    # ----------------------

    #: The count msg message
    COUNT_MSG: str = '<b>Counting:</b> <code>{LINK}</code>'
    #: The count name message
    COUNT_NAME: str = '<b><i>{COUNT_NAME}</i></b>\n┃\n'
    #: The count size message
    COUNT_SIZE: str = '┠ <b>Size: </b>{COUNT_SIZE}\n'
    #: The count type message
    COUNT_TYPE: str = '┠ <b>Type: </b>{COUNT_TYPE}\n'
    #: The count sub message
    COUNT_SUB: str =  '┠ <b>SubFolders: </b>{COUNT_SUB}\n'
    #:
