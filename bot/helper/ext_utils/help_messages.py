#!/usr/bin/env python3
from bot.helper.telegram_helper.bot_commands import BotCommands

YT_HELP_MESSAGE = ["""<i>Send links/files along with cmd or reply to cmd to mirror or leech ytdl supported stes on Telegram or GDrive or DDLs with different Engines like RClone or yt-dlp</i>

➲ <b><u>Available Args</u></b>:

1.  <b>-n or -name :</b> Rename file.
2.  <b>-z or -zip :</b> Zip files or Links
3.  <b>-up or -upload :</b> Upload to your Drive or RClone or DDL
4.  <b>-b or -bulk :</b> Download bulk links.
5.  <b>-i :</b> Download multi links by reply
6.  <b>-m or -sd or -samedir :</b> Download multi links within same upload directory.
7.  <b>-opt or -options :</b> Attach Custom yt-dlp options to link
8.  <b>-s or -select :</b> Select files from yt-dlp links even if qual is specified
9.  <b>-rcf :</b> RClone additional Flags
10. <b>-id :</b> GDrive Folder id or link
11. <b>-index:</b> Index url for gdrive_arg
12. <b>-c or -category :</b> Gdrive category to Upload, Specific Name (case insensitive)
13. <b>-ud or -dump :</b> Dump category to Upload, Specific Name (case insensitive) or chat_id or chat_username
14. <b>-ss or -screenshots :</b> Generate Screenshots for Leeched Files
15. <b>-t or -thumb :</b> Custom Thumb for Specific Leech
""", """
➲ <b><i>Send link along with command line</i></b>:
<code>/cmd</code> link -s -n new name -opt x:y|x1:y1

➲ <b><i>By replying to link</i></b>:
<code>/cmd</code> -n  new name -z password -opt x:y|x1:y1

➲ <b><i>New Name</i></b>: -n or -name
<code>/cmd</code> link -n new name
<b>Note:</b> Don't add file extension

➲ <b><i>Screenshot Generation</b>: -ss or -screenshots
<code>/cmd</code> link -ss number ,Screenshots for each Video File

➲ <b><i>Custom Thumbnail</b>: -t or -thumb
<code>/cmd</code> link -t tglink|dl_link
<b>Direct Link:</b> dl_link specifies download link, where it is Image url
<b>Tg Link:</b> Give Public/Private/Super Link to download Image from Tg

➲ <b><i>Quality Buttons</i></b>: -s or -select
Incase default quality added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
<code>/cmd</code> link -s

➲ <b<i>Zip files (with/without pass)</i></b>: -z or -zip password
<code>/cmd</code> link -z (zip)
<code>/cmd</code> link -z password (zip password protected)

➲ <b><i>Options</i></b>: -opt or -options
<code>/cmd</code> link -opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)
<b>Note:</b> Add `^` before integer or float, some values must be numeric and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.

➲ <b><i>Multi links only by replying to first link</i></b>: -i
<code>/cmd</code> -i 10(number of links)

➲ <b><i>Multi links within same upload directory only by replying to first link</i></b>: -m or -sd or -samedir
<code>/cmd</code> -i 10(number of links) -m folder name

➲ <b><i>Upload Custom Drive:</i></b> -id & -index(Optional)
<code>/{cmd}</code> -id <code>drive_folder_link</code> or <code>drive_id</code> -index <code>https://example.com/0:</code>
Here, drive_id must be folder id or folder link and index must be url else it will not accept.

➲ <b><i>Custom Category Select:</i></b> -c or -category
<code>/{cmd}</code> -c <code>category_name</code>
This works for both Bot Categories as well as UserTDs (if enabled)
You can also select Drive Upload from Buttons if having more than 1 and this arg not specified

➲ <b><i>Custom Dump Select:</i></b> -ud or -dump
<code>/{cmd}</code> -ud <code>dump_name</code> or <code>@username</code> or <code>-100xxxxxx chat_id</code> or all
You can also select Dump Chat from Buttons if having more than 1 and this arg not specified
You -ud all for Uploading in all Dump Chats of yours
Make Sure Bot is already Admin else it will not accept.

➲ <b><i>Upload</i></b>: -up or -upload
<code>/cmd</code> link -up <code>rcl</code> (To select rclone config, remote and path)
<code>/cmd</code> link -up <code>ddl</code>
You can directly add the upload path: -up remote:dir/subdir

If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If DEFAULT_UPLOAD is `ddl` then you can pass up: `rc` or `gd` to upload to RCLONE_PATH or GDRIVE_ID
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/cmd</code> link -up <code>mrcc:</code>main:dump

➲ <b><i>RClone Flags</i></b>: -rcf
<code>/cmd</code> link -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.

➲ <b><i>Bulk Download</i></b>: -b or -bulk
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
<b>Example:</b>
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -z -n new name -opt ytdlpoptions

<b>Note:</b> You can't add -m arg for some links only, do it for all links or use multi without bulk!
link pswd: pass(zip) opt: ytdlpoptions up: remote2:path2
Reply to this example by this cmd <code>/cmd</code> b(bulk)
You can set start and end of the links from the bulk with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.

➲ <b>NOTES:</b>
Check all yt-dlp API options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a>
"""]

MIRROR_HELP_MESSAGE = ["""<i>Send links/files along with cmd or reply to cmd to mirror or leech on Telegram or GDrive or DDLs with different Engines like RClone, Aria2 or qBit</i>

➲ <b><u>Available Args</u></b>:

1.  <b>-n or -name :</b> Rename file.
2.  <b>-z or -zip :</b> Zip files or Links
3.  <b>-e or -extract or -uz or -unzip :</b> Extract/Unzip files from Archive
4.  <b>-up or -upload :</b> Upload to your Drive or RClone or DDL
6.  <b>-b or -bulk :</b> Download bulk links.
7.  <b>-i :</b> Download multi links by reply
9.  <b>-m or -sd or -samedir :</b> Download multi links within same upload directory.
10. <b>-d or -seed :</b> Bittorrent seed torrent.
11. <b>-s or -select :</b> Select files from torrent via Bittorrent
12. <b>-u or -user :</b> Enter username for Auth
13. <b>-p or -pass :</b> Enter password for Auth
14. <b>-j or -join :</b> Join Multiple Files.
15. <b>-rcf :</b> RClone additional Flags
16. <b>-id :</b> GDrive Folder id or link
17. <b>-index:</b> Index url for gdrive_arg
18. <b>-c or -category :</b> Gdrive category to Upload, Specific Name (case insensitive)
19. <b>-ud or -dump :</b> Dump category to Upload, Specific Name (case insensitive) or chat_id or chat_username
20. <b>-ss or -screenshots :</b> Generate Screenshots for Leeched Files
21. <b>-t or -thumb :</b> Custom Thumb for Specific Leech
""", """
➲ <b><i>By along the cmd</i></b>:
<code>/cmd</code> link -n new name

➲ <b><i>By replying to link/file</i></b>:
<code>/cmd</code> -n new name -z -e -up upload_destination

➲ <b><i>Custom New Name</i></b>: -n or -name
<code>/cmd</code> link -n new name
<b>NOTES</b>: Doesn't work with torrents.

➲ <b><i>Direct Link Authorization</i></b>: -u -p or -user -pass
<code>/cmd</code> link -u username -p password

➲ <b><i>Direct link custom headers</i></b>: -h or -headers
<code>/cmd</code> link -h key: value key1: value1

➲ <b><i>Screenshot Generation</b>: -ss or -screenshots
<code>/cmd</code> link -ss number ,Screenshots for each Video File

➲ <b><i>Custom Thumbnail</b>: -t or -thumb
<code>/cmd</code> link -t tglink|dl_link
<b>Direct Link:</b> dl_link specifies download link, where it is Image url
<b>Tg Link:</b> Give Public/Private/Super Link to download Image from Tg

➲ <b><i>Extract / Zip</i></b>: -uz -z or -zip -unzip or -e -extract
<code>/cmd</code> link -e password (extract password protected)
<code>/cmd</code> link -z password (zip password protected)
<code>/cmd</code> link -z password -e (extract and zip password protected)
<code>/cmd</code> link -e password -z password (extract password protected and zip password protected)
<b>NOTES:</b> When both extract and zip added with cmd it will extract first and then zip, so always extract first

➲ <b><i>qBittorrent selection</i></b>: -s or -select
<code>/cmd</code> link -s or by replying to file/link

➲ <b><i>qBittorrent / Aria2 Seed</i></b>: -d or -seed
<code>/cmd</code> link -d ratio:seed_time or by replying to file/link
To specify ratio and seed time add -d ratio:time. Ex: -d 0.7:10 (ratio and time) or -d 0.7 (only ratio) or -d :10 (only time) where time in minutes.

➲ <b><i>Multi links only by replying to first link/file</i></b>: -i
<code>/cmd</code> -i 10(number of links/files)

➲ <b><i>Multi links within same upload directory only by replying to first link/file</i></b>: -m or -sd or -samedir
<code>/cmd</code> -i 10(number of links/files) -m folder name (multi message)
<code>/cmd</code> -b -m folder name (bulk-message/file)

➲ <b><i>Upload Custom Drive:</i></b> -id & -index(Optional)
<code>/{cmd}</code> -id <code>drive_folder_link</code> or <code>drive_id</code> -index <code>https://example.com/0:</code>
Here, drive_id must be folder id or folder link and index must be url else it will not accept.

➲ <b><i>Custom Category Select:</i></b> -c or -category
<code>/{cmd}</code> -c <code>category_name</code>
This works for both Bot Categories as well as UserTDs (if enabled)
You can also select Drive Upload from Buttons if having more than 1 and this arg not specified

➲ <b><i>Custom Dump Select:</i></b> -ud or -dump
<code>/{cmd}</code> -ud <code>dump_name</code> or <code>@username</code> or <code>-100xxxxxx chat_id</code> or all
You can also select Dump Chat from Buttons if having more than 1 and this arg not specified
You -ud all for Uploading in all Dump Chats of yours
Make Sure Bot is already Admin else it will not accept.

➲ <b><i>Custom Upload</i></b>: -up or -upload
<code>/cmd</code> link -up <code>rcl</code> (To select rclone config, remote and path)
<code>/cmd</code> link -up <code>ddl</code>
You can directly add the upload path: -up remote:dir/subdir

If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If DEFAULT_UPLOAD is `ddl` then you can pass up: `rc` or `gd` to upload to RCLONE_PATH or GDRIVE_ID
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/cmd</code> link -up <code>mrcc:</code>main:dump

➲ <b><i>RClone Flags</i></b>: -rcf
<code>/cmd</code> link|path|rcl -up path|rcl -rcf --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.

➲ <b><i>Bulk Download</i></b>: -b or -bulk
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
<b>Some Examples:</b>
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -uz -n new name -up remote2:path2
<b>NOTES:</b> You can't add -m arg for some links only, do it for all links or use multi without bulk!
Reply to this example by this cmd <code>/cmd</code> -b(bulk)
You can set start and end of the links from the bulk like seed, with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.

➲ <b><i>Join Splitted Files</i></b>: -j or -join
This option will only work before extract and zip, so mostly it will be used with -m argument (samedir)
This option is not Merging of Two links/files.
<b>By Reply:</b>
<code>/cmd</code> -i 3 -j -m folder name
<code>/cmd</code> -b -j -m folder name
If you have link which has splitted files:
<code>/cmd</code> link -j

➲ <b><i>RClone Download</i></b>:
Treat rclone paths exactly like links
<code>/cmd</code> main:dump/ubuntu.iso or <code>rcl</code>(To select config, remote and path)
Users can add their own rclone from user settings

If you want to add path manually from your config add <code>mrcc:</code> before the path without space
<code>/cmd</code> <code>mrcc:</code>main:dump/ubuntu.iso

➲ <b><i>TG Links</i></b>:
Treat tg links like any direct link
Some links need user access so sure you must add USER_SESSION_STRING for it.
<b><u>Types of links:</u></b>
• <b>Public:</b> <code>https://t.me/channel_name/message_id</code>
• <b>Private:</b> <code>tg://openmessage?user_id=xxxxxx&message_id=xxxxx</code>
• <b>Super:</b> <code>https://t.me/c/channel_id/message_id</code>

➲ <b>NOTES:</b>
1. Commands that start with <b>qb</b> are ONLY for torrents.
"""]

RSS_HELP_MESSAGE = """
➲ <b>Format to adding feed url(s):</b>
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

➲ <b><i>Argument Details:</i></b>
-c command + any arg
-inf For included words filter.
-exf For excluded words filter.

<b>Example:</b> Title https://www.rss-url.com inf: 1080 or 720 or 144p|mkv or mp4|hevc exf: flv or web|xxx opt: up: mrcc:remote:path/subdir rcf: --buffer-size:8M|key|key:value
This filter will parse links that it's titles contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't conyain (flv or web) and xxx` words. You can add whatever you want.

Another example: inf:  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

➲ <b><i>Filter Notes:</i></b>
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
3. You can add `or` and `|` as much as you want."
4. Take look on title if it has static special character after or before the qualities or extensions or whatever and use them in filter to avoid wrong match.

<b>Timeout:</b> 60 sec.
"""

CLONE_HELP_MESSAGE = ["""<i>Send Gdrive | Gdtot | Filepress | Filebee | Appdrive | Gdflix link or RClone path along with or by replying to the link/rc_path by command with args.</i>

➲ <b><u>Available Args</u></b>:

1. <b>-up or -upload :</b> Upload to your Drive or RClone or DDL
2. <b>-i :</b> Download multi links by reply
3. <b>-rcf :</b> RClone additional Flags
4. <b>-id :</b> GDrive Folder id or link
5. <b>-index:</b> Index url for gdrive_arg
6. <b>-c or -category :</b> Gdrive category to Upload, Specific Name (case insensitive)""",
"""➲ <b><i>Links:</i></b>
Gdrive | Gdtot | Filepress | Filebee | Appdrive | Gdflix link or rclone path

➲ <b><i>Multi Links (only by replying to first gdlink or rclone_path):</i></b>
<code>/cmd</code> -i 10(number of links/paths)

➲ <b><i>Gdrive Link:</i></b>
<code>/cmd</code> gdrive_link

➲ <b><i>RClone Path with RC Flags:</i></b> -rcf
<code>/cmd</code> (rcl or rclone_path) -up (rcl or rclone_path) -rcf flagkey:flagvalue|flagkey|flagkey:flagvalue

➲ <b><i>Upload Custom Drive:</i></b> -id & -index(Optional)
<code>/{cmd}</code> -id <code>drive_folder_link</code> or <code>drive_id</code> -index <code>https://example.com/0:</code>

➲ <b><i>Custom Category Select:</i></b> -c or -category
<code>/{cmd}</code> -c <code>category_name</code>

<b>NOTES:</b>
1. If -up or -upload not specified then rclone destination will be the RCLONE_PATH from <code>config.env</code>.
2. If UserTD enabled, then only it will upload to UserTD either by direct arg or category buttons.
3. For Multi Custom Upload always use Arg in respective msgs and then reply with /cmd -i 10(number)
"""]

CATEGORY_HELP_MESSAGE = """Reply to an active /{cmd} which was used to start the download or add gid along with {cmd}
This command mainly for change category incase you decided to change category from already added download.
But you can always use -c or -category with to select category before download start.

➲ <b><i>Upload Custom Drive</i></b>
<code>/{cmd}</code> -id <code>drive_folder_link</code> or <code>drive_id</code> -index <code>https://example.com/0:</code> gid or by replying to active download

<b>NOTE:</b> drive_id must be folder id or folder link and index must be url else it will not accept.
"""

help_string = [f'''⌬ <b><i>Basic Commands!</i></b>

<b>Use Mirror commands to download your link/file/rcl</b>
┠ /{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Download via file/url/media to Upload to Cloud Drive.
┖ /{BotCommands.CategorySelect}: Select Custom category to Upload to Cloud Drive from UserTds or Bot Categories.

<b>Use qBit commands for torrents only:</b>
┠ /{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Download using qBittorrent and Upload to Cloud Drive.
┖ /{BotCommands.BtSelectCommand}: Select files from torrents by btsel_gid or reply.

<b>Use yt-dlp commands for YouTube or any supported sites:</b>
┖ /{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.

<b>Use Leech commands for upload to Telegram:</b>
┠ /{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Upload to Telegram.
┠ /{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Download using qBittorrent and upload to Telegram(For torrents only).
┖ /{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Download using Yt-Dlp(supported link) and upload to telegram.

<b>G-Drive commands:</b>
┠ /{BotCommands.CloneCommand[0]}: Copy file/folder to Cloud Drive.
┠ /{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
┖ /{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).

<b>Cancel Tasks:</b>
┖ /{BotCommands.CancelMirror}: Cancel task by cancel_gid or reply.''',

f'''⌬ <b><i>Users Commands!</i></b>

<b>Bot Settings:</b>
┖ /{BotCommands.UserSetCommand[0]} or /{BotCommands.UserSetCommand[1]} [query]: Open User Settings (PM also)

<b>Authentication:</b>
┖ /login: Login to Bot to Access Bot without Temp Pass System (Private)

<b>Bot Stats:</b>
┠ /{BotCommands.StatusCommand[0]} or /{BotCommands.StatusCommand[1]}: Shows a status page of all active tasks.
┠ /{BotCommands.StatsCommand[0]} or /{BotCommands.StatsCommand[1]}: Show Server detailed stats.
┖ /{BotCommands.PingCommand[0]} or /{BotCommands.PingCommand[1]}: Check how long it takes to Ping the Bot.

<b>RSS Feed:</b>
┖ /{BotCommands.RssCommand}: Open RSS Menu (Sub/Unsub/Start/Pause)''',

f'''⌬ <b><i>Owner or Sudos Commands!</i></b>

<b>Bot Settings:</b>
┠ /{BotCommands.BotSetCommand[0]} or /{BotCommands.BotSetCommand[1]} [query]: Open Bot Settings (Only Owner & Sudo).
┖ /{BotCommands.UsersCommand}: Show User Stats Info (Only Owner & Sudo).

<b>Authentication:</b>
┠ /{BotCommands.AuthorizeCommand[0]} or /{BotCommands.AuthorizeCommand[1]}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
┠ /{BotCommands.UnAuthorizeCommand[0]} or /{BotCommands.UnAuthorizeCommand[1]}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
┠ /{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
┠ /{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).
┠ /{BotCommands.AddBlackListCommand[0]} or /{BotCommands.AddBlackListCommand[1]}: Add User in BlackListed, so that user can't use the Bot anymore.
┖ /{BotCommands.RmBlackListCommand[0]} or /{BotCommands.RmBlackListCommand[1]}: Remove a BlackListed User, so that user can again use the Bot.

<b>Bot Stats:</b>
┖ /{BotCommands.BroadcastCommand[0]} or /{BotCommands.BroadcastCommand[1]} [reply_msg]: Broadcast to PM users who have started the bot anytime.

<b>G-Drive commands:</b>
┖ /{BotCommands.GDCleanCommand[0]} or /{BotCommands.GDCleanCommand[1]} [drive_id]: Delete all files from specific folder in Google Drive.

<b>Cancel Tasks:</b>
┖ /{BotCommands.CancelAllCommand[0]}: Cancel all Tasks & /{BotCommands.CancelAllCommand[1]} for Multiple Bots.

<b>Maintainance:</b>
┠ /{BotCommands.RestartCommand[0]} or /{BotCommands.RestartCommand[1]}: Restart and Update the Bot (Only Owner & Sudo).
┠ /{BotCommands.RestartCommand[2]}: Restart and Update all Bots (Only Owner & Sudo).
┖ /{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).

<b>Executors:</b>
┠ /{BotCommands.ShellCommand}: Run shell commands (Only Owner).
┠ /{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
┠ /{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
┠ /{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
┖ /exportsession: Generate User StringSession of Same Pyro Version (Only Owner).

<b>RSS Feed:</b>
┖ /{BotCommands.RssCommand}: Open RSS Menu (Sub/Unsub/Start/Pause)

<b>Extras:</b>
┠ /{BotCommands.AddImageCommand} [url/photo]: Add Images in Bot
┖ /{BotCommands.ImagesCommand}: Generate grid of Stored Images.''',

f'''⌬ <b><i>Miscellaneous Commands!</i></b>

<b>Extras:</b>
┠ /{BotCommands.SpeedCommand[0]} or /{BotCommands.SpeedCommand[1]}: Check Speed in VPS/Server.
┖ /{BotCommands.MediaInfoCommand[0]} or /{BotCommands.MediaInfoCommand[1]} [url/media]: Generate MediaInfo of Media or DL Urls

<b>Torrent/Drive Search:</b>
┠ /{BotCommands.ListCommand} [query]: Search in Google Drive(s).
┖ /{BotCommands.SearchCommand} [query]: Search for torrents with API.

<b>Movie/TV Shows/Drama Search:</b>
┠ /{BotCommands.IMDBCommand}: Search in IMDB.
┠ /{BotCommands.AniListCommand}: Search for anime in AniList.
┠ /{BotCommands.AnimeHelpCommand}: Anime help guide.
┖ /{BotCommands.MyDramaListCommand}: Search in MyDramaList.
''']


PASSWORD_ERROR_MESSAGE = """
<b>This link requires a password!</b>
- Insert sign <b>::</b> after the link and write the password after the sign.
<b>Example:</b> {}::love you
Note: No spaces between the signs <b>::</b>
For the password, you can use a space!
"""

default_desp = {'AS_DOCUMENT': 'Default type of Telegram file upload. Default is False mean as media.',
                'ANIME_TEMPLATE': 'Set template for AniList Template. HTML Tags supported',
                'AUTHORIZED_CHATS': 'Fill user_id and chat_id of groups/users you want to authorize. Separate them by space.',
                'AUTO_DELETE_MESSAGE_DURATION': "Interval of time (in seconds), after which the bot deletes it's message and command message which is expected to be viewed instantly.\n\n <b>NOTE:</b> Set to -1 to disable auto message deletion.",
                'BASE_URL': 'Valid BASE URL where the bot is deployed to use torrent web files selection. Format of URL should be http://myip, where myip is the IP/Domain(public) of your bot or if you have chosen port other than 80 so write it in this format http://myip:port (http and not https). Str',
                'BASE_URL_PORT': 'Which is the BASE_URL Port. Default is 80. Int',
                'BLACKLIST_USERS': 'Restrict User from Using the Bot. It will Display a BlackListed Msg. USER_ID separated by space. Str',
                'BOT_MAX_TASKS': 'Maximum number of Task Bot will Run parallel. (Queue Tasks Included). Int',
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
                'AUTHOR_NAME': 'Author name for Telegraph pages, Shown in Telegraph Page as by AUTHOR_NAME',
                'AUTHOR_URL': 'Author URL for Telegraph page, Put Channel URL to Show Join Channel. Str',
                'COVER_IMAGE': 'Cover Image for Telegraph Page. Put Telegraph Photo Link',
                'TITLE_NAME': 'Title name for Telegraph pages (while using /list command)',
                'GD_INFO': 'Description of file uploaded to gdrive using bot',
                'DELETE_LINKS': 'Delete TgLink/Magnet/File on Start of Task to Auto Clean Group. Default is False',
                'EXCEP_CHATS': 'Exception Chats which will not use Logging, chat_id separated by space. Str',
                'SAFE_MODE': 'Hide Task Name, Source Link and Indexing of Leech Link for Safety Precautions. Default is False',
                'SOURCE_LINK': 'Add a Extra Button of Source Link whether it is Magnet Link or File Link or DL Link. Default is False',
                'SHOW_EXTRA_CMDS': 'Add Extra Commands beside Arg Format for -z or -e. \n\n<b>COMMANDS: </b> /unzipxxx or /zipxxx or /uzx or /zx',
                'BOT_THEME': 'Theme of the Bot to Switch. For now Deafault Theme Availabe is minimal. You can make your own Theme and Add in BSet. \n\n<b>Sample Format</b>: https://t.ly/9rVXq',
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
                'CMD_SUFFIX': 'Telegram Bot Command Index number or Custom Text. This will added at the end all commands except Global Commands. Str',
                'DATABASE_URL': "Your Mongo Database URL (Connection string). Follow this Generate Database to generate database. Data will be saved in Database: auth and sudo users, users settings including thumbnails for each user, rss data and incomplete tasks.\n\n <b>NOTE:</b> You can always edit all settings that saved in database from the official site -> (Browse collections)",
                'DEFAULT_UPLOAD': 'Whether rc to upload to RCLONE_PATH or gd to upload to GDRIVE_ID or ddl to upload to DDLserver. Default is gd.',
                'DOWNLOAD_DIR': 'The path to the local folder where the downloads should be downloaded to. ',
                'MDL_TEMPLATE': 'Set Bot Custom Default MyDramaList Template. HTML Tags, Emojis Supported',
                'CLEAN_LOG_MSG': 'Clean Leech Log & Bot PM Task Start Message. Default is False',
                'LEECH_LOG_ID': "Chat ID to where leeched files would be uploaded. Int. NOTE: Only available for superGroup/channel. Add -100 before channel/superGroup id. In short don't add bot id or your id!",
                'MIRROR_LOG_ID': "Chat ID to where Mirror files would be Send. Int. NOTE: Only available for superGroup/channel. Add -100 before channel/superGroup id. In short don't add bot id or your id!. For Multiple id Separate them by space.",
                'EQUAL_SPLITS': 'Split files larger than LEECH_SPLIT_SIZE into equal parts size (Not working with zip cmd). Default is False.',
                'EXTENSION_FILTER': "File extensions that won't upload/clone. Separate them by space.",
                'GDRIVE_ID': 'This is the Folder/TeamDrive ID of the Google Drive OR root to which you want to upload all the mirrors using google-api-python-client.',
                'INCOMPLETE_TASK_NOTIFIER': 'Get incomplete task messages after restart. Require database and superGroup. Default is False',
                'INDEX_URL': 'Refer to https://gitlab.com/ParveenBhadooOfficial/Google-Drive-Index.',
                'IS_TEAM_DRIVE': 'Set True if uploading to TeamDrive using google-api-python-client. Default is False',
                'SHOW_MEDIAINFO': 'Add Button to Show MediaInfo in Leeched file. Bool',
                'SCREENSHOTS_MODE': 'Enable or Diable generating Screenshots via -ss arg. Default is False. Bool',
                'CAP_FONT': 'Add Custom Caption Font to Leeched Files, Available Values : b, i, u, s, code, spoiler. Reset Var to use Regular ( No Format )',
                'LEECH_FILENAME_PREFIX': 'Add custom word prefix to leeched file name. Str',
                'LEECH_FILENAME_SUFFIX': 'Add custom word suffix to leeched file name. Str',
                'LEECH_FILENAME_CAPTION': 'Add custom word caption to leeched file/vedios. Str',
                'LEECH_FILENAME_REMNAME': 'Remove custom word from the leeched file name. Str',
                'LOGIN_PASS': 'Permanent pass for user to skip the token system',
                'TOKEN_TIMEOUT': 'Token timeout for each group member in sec. Int',
                'DEBRID_LINK_API': 'Set debrid-link.com API for 172 Supported Hosters Leeching Support. Str',
                'REAL_DEBRID_API': 'Set real-debrid.com API for Torrent Cache & Few Supported Hosters (VPN Maybe). Str',
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
                'UPGRADE_PACKAGES': 'Install New Requirements File without thinking of Crash. Bool',
                'SAVE_MSG': 'Add button of save message. Bool',
                'SET_COMMANDS': 'Set bot command automatically. Bool',
                'JIODRIVE_TOKEN': 'Set token for the jiodrive.xyz to download the files. str',
                'USER_TD_MODE': 'Enable User GDrive TD to Use. Default is False',
                'USER_TD_SA': 'Add Global SA mail for User to give Permissions to Bot for UserTD Upload. Like wzmlx@googlegroups.com. Str',
                'USER_SESSION_STRING': "To download/upload from your telegram account and to send rss. To generate session string use this command <code>python3 generate_string_session.py</code> after mounting repo folder for sure.\n\n<b>NOTE:</b> You can't use bot with private message. Use it with superGroup.",
                'USE_SERVICE_ACCOUNTS': 'Whether to use Service Accounts or not, with google-api-python-client. For this to work see Using Service Accounts section below. Default is False',
                'WEB_PINCODE': ' Whether to ask for pincode before selecting files from torrent in web or not. Default is False. Bool.',
                'YT_DLP_OPTIONS': 'Default yt-dlp options. Check all possible options HERE or use this script to convert cli arguments to api options. Format: key:value|key:value|key:value. Add ^ before integer or float, some numbers must be numeric and some string. \nExample: "format:bv*+mergeall[vcodec=none]|nocheckcertificate:True"'
                }
