class WZMLStyle:
    """Class for defining various bot messages and buttons."""

    # Constants for the 'start' command
    st_bn1_name: str = 'Repo'  # Name of the first button
    st_bn1_url: str = 'https://www.github.com/weebzone/WZML-X'  # URL of the first button
    st_bn2_name: str = 'Updates'  # Name of the second button
    st_bn2_url: str = 'https://t.me/WZML_X'  # URL of the second button
    st_msg: str = (
        '<i>This bot can mirror all your links|files|torrents to Google Drive or any rclone cloud or to telegram or to ddl servers.</i>'
        '<b>Type {help_command} to get a list of available commands</b>'
    )  # Main message for the 'start' command
    st_botpm: str = (
        '<i>Now, This bot will send all your files and links here. Start Using ...</i>'
    )  # Message for sending files and links to the bot's private messages
    st_unauth: str = (
        '<i>You Are not authorized user! Deploy your own WZML-X Mirror-Leech bot</i>'
    )  # Message for unauthorized users

    def __init_subclass__(cls):
        """Initialize the class variables for subclasses."""
        for name, value in cls.__dict__.items():
            if name.startswith("st_"):
                globals()[name] = value

    # Constants for the 'token' command
    own_token_generate: str = (
        '<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>'
    )  # Message for temporary token not belonging to the user
    used_token: str = (
        '<b>Temporary Token already used!</b>\n\n<i>Kindly generate a new one.</i>'
    )  # Message for already used temporary token
    logged_password: str = (
        '<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>'
    )  # Message for bot already logged in via password
    activate_button: str = 'Activate Temporary Token'  # Button text for activating temporary token
    token_msg: str = f'<b><u>Generated Temporary Login Token!</u></b>\n\n' f'<b>Temp Token:</b> <code>{token}</code>\n' f'<b>Validity:</b> {validity}'  # Message for generated temporary login token

    # Constants for the 'token_callback' function
    activated: str = '✅️ Activated ✅'  # Message for activated temporary token

    # Constants for the 'login' command
    logged_in: str = '<b>Already Bot Login In!</b>'  # Message for bot already logged in
    invalid_pass: str = '<b>Invalid Password!</b>\n\nKindly put the correct Password .'  # Message for invalid password
    pass_logged: str = '<b>Bot Permanent Login Successfully!</b>'  # Message for successful permanent login
    login_used: str = '<b>Bot Login Usage :</b>\n\n<code>/cmd [password]</code>'  # Message for bot login usage

    # Constants for the 'log' command
    log_display_bt: str = '📑 Log Display'  # Button text for displaying logs
    web_paste_bt: str = '📨 Web Paste (SB)'  # Button text for web paste

    # Constants for the 'bot_help' command
    basic_bt: str = 'Basic'  # Button text for basic commands
    user_bt: str = 'Users'  # Button text for user-related commands
    mics_bt: str = 'Mics'  # Button text for micro-related commands
    o_s_bt: str = 'Owner & Sudos'  # Button text for owner and sudo-related commands
    close_bt: str = 'Close'  # Button text for closing the help menu
    help_header: str = (
        "㊂ <b><i>Help Guide Menu!</i></b>\n\n<b>NOTE: <i>Click on any CMD to see more minor detalis.</i></b>"
    )  # Header for the help menu

    # Constants for the 'stats' function
    bot_stats: str = f'⌬ <b><i>BOT STATISTICS :</i></b>\n\n' f'┖ <b>Bot Uptime :</b> {bot_uptime}\n\n' f'┎ <b><i>RAM ( MEMORY ) :</i></b>\n' f'┃ {ram_bar} {ram}%\n' f'┖ <b>U :</b> {ram_u} | <b>F :</b> {ram_f} | <b>T :</b> {ram_t}\n\n' f'┎ <b><i>SWAP MEMORY :</i></b>\n' f'┃ {swap_bar} {swap}%\n' f'┖ <b>U :</b> {swap_u} | <b>F :</b> {swap_f} | <b>T :</b> {swap_t}\n\n' f'┎ <b><i>DISK :</i></b>\n' f'┃ {disk_bar} {disk}%\n' f'┃ <b>Total Disk Read :</b> {disk_read}\n' f'┃ <b>Total Disk Write :</b> {disk_write}\n' f'┖ <b>U :</b> {disk_u} | <b>F :</b> {disk_f} | <b>T :</b> {disk_t}'

    sys_stats: str = f'⌬ <b><i>OS SYSTEM :</i></b>\n\n' f'┠ <b>OS Uptime :</b> {os_uptime}\n' f'┠ <b>OS Version :</b> {os_version}\n' f'┖ <b>OS Arch :</b> {os_arch}\n\n' f'⌬ <b><i>NETWORK STATS :</i></b>\n' f'┠ <b>Upload Data:</b> {up_data}\n' f'┠ <b>Download Data:</b> {dl_data}\n' f'┠ <b>Pkts Sent:</b> {pkt_sent}k\n' f'┠ <b>Pkts Received:</b> {pkt_recv}k\n' f'┖ <b>Total I/O Data:</b> {tl_data}\n\n' f'┎ <b>CPU :</b>\n' f'┃ {cpu_bar} {cpu}%\n' f'┠ <b>CPU Frequency :</b> {cpu_freq}\n' f'┠ <b>System Avg Load :</b> {sys_load}\n' f'┠ <b>P-Core(s) :</b> {p_core} | <b>V-Core(s) :</b> {v_core}\n' f'┠ <b>Total Core(s) :</b> {total_core}\n' f'┖ <b>Usable CPU(s) :</b> {cpu_use}'

    repo_stats: str = f'⌬ <b><i>REPO STATISTICS :</i></b>\n\n' f'┠ <b>Bot Updated :</b> {last_commit}\n' f'┠ <b>Current Version :</b> {bot_version}\n' f'┠ <b>Latest Version :</b> {lat_version}\n' f'┖ <b>Last ChangeLog :</b> {commit_details}\n\n' f'⌬ <b>REMARKS :</b> <code>{remarks}</code>'

    bot_limits: str = f'⌬ <b><i>BOT LIMITATIONS :</i></b>\n\n' f'┠ <b>Direct Limit :</b> {DL} GB\n' f'┠ <b>Torrent Limit :</b> {TL} GB\n' f'┠ <b>GDrive Limit :</b> {GL} GB\n' f'┠ <b>YT-DLP Limit :</b> {YL} GB\n' f'┠ <b>Playlist Limit :</b> {PL}\n' f'┠ <b>Mega Limit :</b> {ML} GB\n' f'┠ <b>Clone Limit :</b> {CL} GB\n' f'┖ <b>Leech Limit :</b> {LL} GB\n\n' f'┎ <b>Token Validity :</b> {TV}\n' f'┠ <b>User Time Limit :</b> {UTI} / task\n' f'┠ <b>User Parallel Tasks :</b> {UT}\n' f'┖ <b>Bot Parallel Tasks :</b> {BT}'

    # Constants for the 'restart' command
    restarting: str = '<i>Restarting...</i>'  # Message for restarting

    # Constants for the 'restart_notification' function
    restart_success: str = f'⌬ <b><i>Restarted Successfully!</i></b>\n\n' f'┠ <b>Date:</b> {date}\n' f'┠ <b>Time:</b> {time}\n' f'┠ <b>TimeZone:</b> {timz}\n' f'┖ <b>Version:</b> {version}'  # Message for successful restart
    restarted: str = '⌬ <b><i>Bot Restarted!</i></b>'  # Message for bot restarted

    # Constants for the 'ping' command
    ping: str = '<i>Starting Ping..</i>'  # Message for starting ping
    ping_value: str = f'<b>Pong</b>\n<code>{value} ms..</code>'  # Message for ping value

    # Constants for the 'onDownloadStart' function
    links_start: str = f'<b><i>Task Started</i></b>\n┠ <b>Mode:</b> {Mode}\n┖ <b>By:</b> {Tag}\n\n'  # Message for task started
    links_source: str = f'➲ <b>Source:</b>\n┖ <b>Added On:</b> {On}\n------------------------------------------\n{Source}\n------------------------------------------\n\n'  # Message for task source

    # Constants for the '__msg_to_reply' function
    pm_start: str = f'➲ <b><i>Task Started :</i></b>\n┃\n┖ <b>Link:</b> <a href=\'{msg_link}\'>Click Here</a>'  # Message for task started in private messages
    l_log_start: str = f'➲ <b><i>Leech Started :</i></b>\n┃\n┠ <b>User :</b> {mention} ( #ID{uid} )\n┖ <b>Source :</b> <a href=\'{msg_link}\'>Click Here</a>'  # Message for leech started

    # Constants for the 'onUploadComplete' function
    name: str = f'<b><i>{Name}</i></b>\n┃\n'  # Message for file name
    size: str = '┠ <b>Size: </b>{Size}\n'  # Message for file size
    elapse: str = '┠ <b>Elapsed: </b>{Time}\n'  # Message for elapsed time
    mode: str = '┠ <b>Mode: </b>{Mode}\n'  # Message for mode

    # Constants for leech
    l_total_files: str = '┠ <b>Total Files: </b>{Files}\n'  # Message for total files
    l_corrupted_files: str = '┠ <b>Corrupted Files: </b>{Corrupt}\n'  # Message for corrupted files
    l_cc: str = '┖ <b>By: </b>{Tag}\n\n'  # Message for completed by
    pm_bot_msg: str = '➲ <b><i>File(s) have been Sent above</i></b>'  # Message for files sent in private messages
    l_bot_msg: str = '➲ <b><i>File(s) have been Sent to Bot PM (Private)</i></b>'  # Message for files sent to bot's private messages
    l_ll_msg: str = '➲ <b><i>File(s) have been Sent. Access via Links...</i></b>\n'  # Message for files sent with links

    # Constants for mirror
    m_type: str = '┠ <b>Type: </b>{Mimetype}\n'  # Message for file type
    m_subfold: str = '┠ <b>SubFolders: </b>{Folder}\n'  # Message for subfolders
    total_files: str = '┠ <b>Files: </b>{Files}\n'  # Message for total files
    rcpath: str = '┠ <b>Path: </b><code>{RCpath}</code>\n'  # Message for file path
    m_cc: str = '┖ <b>By: </b>{Tag}\n\n'  # Message for completed by
    m_bot_msg: str = '➲ <b><i>Link(s) have been Sent to Bot PM (Private)</i></b>'  # Message for links sent to bot's private messages

    # Constants for buttons
    cloud_link: str = '☁️ Cloud Link'  # Button text for cloud link
    save_msg: str = '📨 Save Message'  # Button text for save message
    rclone_link: str = '♻️ RClone Link'  # Button text for rclone link
    ddl_link: str = f'📎 {Serv} Link'  # Button text for ddl link
    source_url: str = '🔐 Source Link'  # Button text for source link
    index_link_f: str = '🗂 Index Link'  # Button text for index link (folder)

