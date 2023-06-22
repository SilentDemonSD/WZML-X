#!/usr/bin/env python3

YT_HELP_MESSAGE = """
<b>Send link along with command line</b>:
<code>/cmd</code> link -s -n new name -opt x:y|x1:y1

<b>By replying to link</b>:
<code>/cmd</code> -n  new name -z password -opt x:y|x1:y1

<b>New Name</b>: -n
<code>/cmd</code> link -n new name
Note: Don't add file extension

<b>Quality Buttons</b>: -s
Incase default quality added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
<code>/cmd</code> link -s

<b>Zip</b>: -z password
<code>/cmd</code> link -z (zip)
<code>/cmd</code> link -z password (zip password protected)

<b>Options</b>: -opt
<code>/cmd</code> link -opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)
Note: Add `^` before integer or float, some values must be numeric and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.

<b>Multi links only by replying to first link</b>: -i
<code>/cmd</code> -i 10(number of links)

<b>Multi links within same upload directory only by replying to first link</b>: -m
<code>/cmd</code> -i 10(number of links) -m folder name

<b>Upload</b>: -up
<code>/cmd</code> link -up <code>rcl</code> (To select rclone config, remote and path)
You can directly add the upload path: -up remote:dir/subdir
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/cmd</code> link -up <code>mrcc:</code>main:dump

<b>Rclone Flags</b>: -rcf
<code>/cmd</code> link -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.

<b>Bulk Download</b>: -b
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -opt ytdlpoptions
Note: You can't add -m arg for some links only, do it for all links or use multi without bulk!
link pswd: pass(zip/unzip) opt: ytdlpoptions up: remote2:path2
Reply to this example by this cmd <code>/cmd</code> b(bulk)
You can set start and end of the links from the bulk with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.


Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
"""

MIRROR_HELP_MESSAGE = """
<code>/cmd</code> link -n new name

<b>By replying to link/file</b>:
<code>/cmd</code> -n new name -z -e -up upload destination

<b>New Name</b>: -n
<code>/cmd</code> link -n new name
Note: Doesn't work with torrents.

<b>Direct link authorization</b>: -au -ap
<code>/cmd</code> link -au username -ap password

<b>Extract/Zip</b>: -e -z
<code>/cmd</code> link -e password (extract password protected)
<code>/cmd</code> link -z password (zip password protected)
<code>/cmd</code> link -z password -e (extract and zip password protected)
<code>/cmd</code> link -e password -z password (extract password protected and zip password protected)
Note: When both extract and zip added with cmd it will extract first and then zip, so always extract first

<b>Bittorrent selection</b>: -s
<code>/cmd</code> link -s or by replying to file/link

<b>Bittorrent seed</b>: -d
<code>/cmd</code> link -d ratio:seed_time or by replying to file/link
To specify ratio and seed time add -d ratio:time. Ex: -d 0.7:10 (ratio and time) or -d 0.7 (only ratio) or -d :10 (only time) where time in minutes.

<b>Multi links only by replying to first link/file</b>: -i
<code>/cmd</code> -i 10(number of links/files)

<b>Multi links within same upload directory only by replying to first link/file</b>: -m
<code>/cmd</code> -i 10(number of links/files) -m folder name (multi message)
<code>/cmd</code> -b -m folder name (bulk-message/file)

<b>Upload</b>: -up
<code>/cmd</code> link -up <code>rcl</code> (To select rclone config, remote and path)
You can directly add the upload path: -up remote:dir/subdir
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/cmd</code> link -up <code>mrcc:</code>main:dump

<b>Rclone Flags</b>: -rcf
<code>/cmd</code> link|path|rcl -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.

<b>Bulk Download</b>: -b
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -up remote2:path2
Note: You can't add -m arg for some links only, do it for all links or use multi without bulk!
Reply to this example by this cmd <code>/cmd</code> -b(bulk)
You can set start and end of the links from the bulk like seed, with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.

<b>Join Splitted Files</b>: -j
This option will only work before extract and zip, so mostly it will be used with -m argument (samedir)
By Reply:
<code>/cmd</code> -i 3 -j -m folder name
<code>/cmd</code> -b -j -m folder name
if u have link have splitted files:
<code>/cmd</code> link -j

<b>Rclone Download</b>:
Treat rclone paths exactly like links
<code>/cmd</code> main:dump/ubuntu.iso or <code>rcl</code>(To select config, remote and path)
Users can add their own rclone from user settings
If you want to add path manually from your config add <code>mrcc:</code> before the path without space
<code>/cmd</code> <code>mrcc:</code>main:dump/ubuntu.iso

<b>TG Links</b>:
Treat links like any direct link
Some links need user access so sure you must add USER_SESSION_STRING for it.
Three types of links:
Public: <code>https://t.me/channel_name/message_id</code>
Private: <code>tg://openmessage?user_id=xxxxxx&message_id=xxxxx</code>
Super: <code>https://t.me/c/channel_id/message_id</code>

<b>NOTES:</b>
1. Commands that start with <b>qb</b> are ONLY for torrents.
"""

RSS_HELP_MESSAGE = """
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command + any arg
-inf For included words filter.
-exf For excluded words filter.

Example: Title https://www.rss-url.com inf: 1080 or 720 or 144p|mkv or mp4|hevc exf: flv or web|xxx opt: up: mrcc:remote:path/subdir rcf: --buffer-size:8M|key|key:value
This filter will parse links that it's titles contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't conyain (flv or web) and xxx` words. You can add whatever you want.

Another example: inf:  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
3. You can add `or` and `|` as much as you want."
4. Take look on title if it has static special character after or before the qualities or extensions or whatever and use them in filter to avoid wrong match.
Timeout: 60 sec.
"""

CLONE_HELP_MESSAGE = """
Send Gdrive|Gdot|Filepress|Filebee|Appdrive|Gdflix link or rclone path along with command or by replying to the link/rc_path by command.

<b>Multi links only by replying to first gdlink or rclone_path:</b>
<code>/cmd</code> -i 10(number of links/pathies)

<b>Gdrive:</b>
<code>/cmd</code> gdrivelink

<b>Rclone:</b>
<code>/cmd</code> (rcl or rclone_path) -up (rcl or rclone_path) -rcf flagkey:flagvalue|flagkey|flagkey:flagvalue

Note: If -up not specified then rclone destination will be the RCLONE_PATH from config.env
"""


default_desp = {'AS_DOCUMENT': 'Default type of Telegram file upload. Default is False mean as media.',
                'ANIME_TEMPLATE': 'Set template for AniList Template. HTML Tags supported',
                'AUTHORIZED_CHATS': 'Fill user_id and chat_id of groups/users you want to authorize. Separate them by space.',
                'AUTO_DELETE_MESSAGE_DURATION': "Interval of time (in seconds), after which the bot deletes it's message and command message which is expected to be viewed instantly.\n\n <b>NOTE:</b> Set to -1 to disable auto message deletion.",
                'BASE_URL': 'Valid BASE URL where the bot is deployed to use torrent web files selection. Format of URL should be http://myip, where myip is the IP/Domain(public) of your bot or if you have chosen port other than 80 so write it in this format http://myip:port (http and not https). Str',
                'BASE_URL_PORT': 'Which is the BASE_URL Port. Default is 80. Int',
                'STORAGE_THRESHOLD': 'To leave specific storage free and any download will lead to leave free storage less than this value will be cancelled the default unit is GB. Int',
                'LEECH_LIMIT':  'To limit the Torrent/Direct/ytdlp leech size. the default unit is GB. Int',
                'CLONE_LIMIT': 'To limit the size of Google Drive folder/file which you can clone. the default unit is GB. Int',
                'MEGA_LIMIT': 'To limit the size of Mega download. the default unit is GB. Int',
                'TORRENT_LIMIT': 'To limit the size of torrent download. the default unit is GB. Int',
                'DIRECT_LIMIT': 'To limit the size of direct link download. the default unit is GB. Int',
                'YTDLP_LIMIT': 'To limit the size of ytdlp download. the default unit is GB. Int',
                'PLAYLIST_LIMIT': 'To limit Maximum Playlist Number. Int',
                'IMAGES': 'Add multiple telgraph(graph.org) image links that are seperated by spaces.',
                'IMG_SEARCH': 'Put Keyword to Download Images. Sperarte each name by , like anime, iron man, god of war',
                'IMG_PAGE': 'Set the page value for downloading a image. Each page have approx 70 images. Deafult is 1. Int',
                'IMDB_TEMPLATE': 'Set Bot Default IMDB Template. HTML Tags, Emojis supported. str',
                'AUTHOR_NAME': 'Author name for Telegraph pages',
                'AUTHOR_URL': 'Author URL for Telegraph page',
                'TITLE_NAME': 'Title name for Telegraph pages (while using /list command)',
                'GD_INFO': 'Description of file uploaded to gdrive using bot',
                'BOT_THEME': 'Change the theme of bot. For now theme availabe is minimal. You can make your own theme checkout this link https://t.ly/9rVXq',
                'USER_MAX_TASKS': 'Limit the Maximum task for users of group at a time. use the Int',
                'DAILY_TASK_LIMIT': 'Maximum task a user can do in one day. use the Int',
                'DISABLE_DRIVE_LINK': 'Disable drive link button. Default is False. Bool',
                'DAILY_MIRROR_LIMIT': 'Total size upto which user can Mirror in one day. the default unit is GB. Int',
                'GDRIVE_LIMIT': 'To limit the size of Google Drive folder/file link for leech, Zip, Unzip. the default unit is GB. Int',
                'DAILY_LEECH_LIMIT': 'Total size upto which user can Leech in one day. the default unit is GB. Int',
                'USER_TASKS_LIMIT': 'The maximum limit on every users for all tasks. Int',
                'FSUB_IDS': 'Fill chat_id(-100xxxxxx) of groups/channel you want to force subscribe. Separate them by space. Int\n\nNote: Bot should be added in the filled chat_id as admin',
                'BOT_PM': 'File/links send to the BOT PM also. Default is False',
                'BOT_TOKEN': 'The Telegram Bot Token that you got from @BotFather',
                'CMD_SUFFIX': 'commands index number. This number will added at the end all commands.',
                'DATABASE_URL': "Your Mongo Database URL (Connection string). Follow this Generate Database to generate database. Data will be saved in Database: auth and sudo users, users settings including thumbnails for each user, rss data and incomplete tasks.\n\n <b>NOTE:</b> You can always edit all settings that saved in database from the official site -> (Browse collections)",
                'DEFAULT_UPLOAD': 'Whether rc to upload to RCLONE_PATH or gd to upload to GDRIVE_ID or ddl to upload to DDLserver. Default is gd.',
                'DOWNLOAD_DIR': 'The path to the local folder where the downloads should be downloaded to. ',
                'MDL_TEMPLATE': 'Set Bot Custom Default MyDramaList Template. HTML Tags, Emojis Supported',
                'LEECH_LOG_ID': "Chat ID to where leeched files would be uploaded. Int. NOTE: Only available for superGroup/channel. Add -100 before channel/superGroup id. In short don't add bot id or your id!",
                'MIRROR_LOG_ID': "Chat ID to where Mirror files would be Send. Int. NOTE: Only available for superGroup/channel. Add -100 before channel/superGroup id. In short don't add bot id or your id!. For Multiple id Separate them by space.",
                'EQUAL_SPLITS': 'Split files larger than LEECH_SPLIT_SIZE into equal parts size (Not working with zip cmd). Default is False.',
                'EXTENSION_FILTER': "File extensions that won't upload/clone. Separate them by space.",
                'GDRIVE_ID': 'This is the Folder/TeamDrive ID of the Google Drive OR root to which you want to upload all the mirrors using google-api-python-client.',
                'INCOMPLETE_TASK_NOTIFIER': 'Get incomplete task messages after restart. Require database and superGroup. Default is False',
                'INDEX_URL': 'Refer to https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index.',
                'IS_TEAM_DRIVE': 'Set True if uploading to TeamDrive using google-api-python-client. Default is False',
                'SHOW_MEDIAINFO': 'Add Button to Show MediaInfo in Leeched file. Bool',
                'CAP_FONT': 'Add Custom Caption Font to Leeched Files, Available Values : b, i, u, s, code, spoiler. Reset Var to use Regular ( No Format )',
                'LEECH_FILENAME_PREFIX': 'Add custom word prefix to leeched file name. Str',
                'LEECH_FILENAME_SUFFIX': 'Add custom word suffix to leeched file name. Str',
                'LEECH_FILENAME_CAPTION': 'Add custom word caption to leeched file/vedios. Str',
                'LEECH_FILENAME_REMNAME': 'Remove custom word from the leeched file name. Str',
                'LOGIN_PASS': 'Permanent pass for user to skip the token system',
                'TOKEN_TIMEOUT': 'Token timeout for each group member in sec. Int',
                'LEECH_SPLIT_SIZE': 'Size of split in bytes. Default is 2GB. Default is 4GB if your account is premium.',
                'MEDIA_GROUP': 'View Uploaded splitted file parts in media group. Default is False.',
                'MEGA_EMAIL': 'E-Mail used to sign-in on mega.nz for using premium account. Str',
                'MEGA_PASSWORD': 'Password for mega.nz account. Str',
                'OWNER_ID': 'The Telegram User ID (not username) of the Owner of the bot.',
                'QUEUE_ALL': 'Number of parallel tasks of downloads and uploads. For example if 20 task added and QUEUE_ALL is 8, then the summation of uploading and downloading tasks are 8 and the rest in queue. Int. NOTE: if you want to fill QUEUE_DOWNLOAD or QUEUE_UPLOAD, then QUEUE_ALL value must be greater than or equal to the greatest one and less than or equal to summation of QUEUE_UPLOAD and QUEUE_DOWNLOAD',
                'QUEUE_DOWNLOAD': 'Number of all parallel downloading tasks. Int',
                'QUEUE_UPLOAD': 'Number of all parallel uploading tasks. Int',
                'RCLONE_FLAGS': 'key:value|key|key|key:value . Check here all RcloneFlags.',
                'RCLONE_PATH': "Default rclone path to which you want to upload all the mirrors using rclone.",
                'RCLONE_SERVE_URL': 'Valid URL where the bot is deployed to use rclone serve. Format of URL should be http://myip, where myip is the IP/Domain(public) of your bot or if you have chosen port other than 80 so write it in this format http://myip:port (http and not https)',
                'RCLONE_SERVE_USER': 'Username for rclone serve authentication.',
                'RCLONE_SERVE_PASS': 'Password for rclone serve authentication.',
                'RCLONE_SERVE_PORT': 'Which is the RCLONE_SERVE_URL Port. Default is 8080.',
                'RSS_CHAT_ID': 'Chat ID where rss links will be sent. If you want message to be sent to the channel then add channel id. Add -100 before channel id. Int',
                'RSS_DELAY': 'Time in seconds for rss refresh interval. Recommended 900 second at least. Default is 900 in sec. Int',
                'SEARCH_API_LINK': 'Search api app link. Get your api from deploying this repository. Supported Sites: 1337x, Piratebay, Nyaasi, Torlock, Torrent Galaxy, Zooqle, Kickass, Bitsearch, MagnetDL, Libgen, YTS, Limetorrent, TorrentFunk, Glodls, TorrentProject and YourBittorrent',
                'SEARCH_LIMIT': 'Search limit for search api, limit for each site and not overall result limit. Default is zero (Default api limit for each site).',
                'SEARCH_PLUGINS': 'List of qBittorrent search plugins (github raw links). I have added some plugins, you can remove/add plugins as you want.',
                'STATUS_LIMIT': 'Limit the no. of tasks shown in status message with buttons. Default is 10. NOTE: Recommended limit is 4 tasks.',
                'STATUS_UPDATE_INTERVAL': 'Time in seconds after which the progress/status message will be updated. Recommended 10 seconds at least.',
                'STOP_DUPLICATE': "Bot will check file/folder name in Drive incase uploading to GDRIVE_ID. If it's present in Drive then downloading or cloning will be stopped. (NOTE: Item will be checked using name and not hash, so this feature is not perfect yet). Default is False",
                'SUDO_USERS': 'Fill user_id of users whom you want to give sudo permission. Separate them by space. Int',
                'TELEGRAM_API': 'This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.',
                'TELEGRAM_HASH': 'This is to authenticate your Telegram account for downloading Telegram files. You can get this from https://my.telegram.org.',
                'TIMEZONE': 'Set your Preferred Time Zone for Restart Message. Get yours at <a href="http://www.timezoneconverter.com/cgi-bin/findzone.tzc">Here</a> Str',
                'TORRENT_TIMEOUT': 'Timeout of dead torrents downloading with qBittorrent and Aria2c in seconds. Int',
                'UPSTREAM_REPO': "Your github repository link, if your repo is private add https://username:{githubtoken}@github.com/{username}/{reponame} format. Get token from Github settings. So you can update your bot from filled repository on each restart.",
                'UPSTREAM_BRANCH': 'Upstream branch for update. Default is master.',
                'SAVE_MSG': 'Add button of save message. Bool',
                'SET_COMMANDS': 'Set bot command automatically. Bool',
                'UPTOBOX_TOKEN': 'Uptobox token to mirror uptobox links. Get it from <a href="https://uptobox.com/my_account">Uptobox Premium Account</a>.',
                'USER_SESSION_STRING': "To download/upload from your telegram account and to send rss. To generate session string use this command <code>python3 generate_string_session.py</code> after mounting repo folder for sure.\n\n<b>NOTE:</b> You can't use bot with private message. Use it with superGroup.",
                'USE_SERVICE_ACCOUNTS': 'Whether to use Service Accounts or not, with google-api-python-client. For this to work see Using Service Accounts section below. Default is False',
                'WEB_PINCODE': ' Whether to ask for pincode before selecting files from torrent in web or not. Default is False. Bool.',
                'YT_DLP_OPTIONS': 'Default yt-dlp options. Check all possible options HERE or use this script to convert cli arguments to api options. Format: key:value|key:value|key:value. Add ^ before integer or float, some numbers must be numeric and some string. \nExample: "format:bv*+mergeall[vcodec=none]|nocheckcertificate:True"'
                }
