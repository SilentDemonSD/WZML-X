<p align="center">
  <img width="220" src="https://i.postimg.cc/XvdvXTkS/photo-2024-12-27-11-46-15.jpg" alt="Downloader Zone Logo">
</p>

<p align="center">
  <b>Modern Telegram Mirror/Leech Bot</b><br>
  <i>Wzml-X is a powerful, modern Telegram bot for mirroring, leeching, and managing downloads to Google Drive, Telegram, or any RClone-supported cloud. Built for speed, reliability, and a beautiful user experience.</i>
</p>

<p align="center">
  <a href="https://github.com/DownloaderZone/WZML-X"><img src="https://img.shields.io/github/stars/DownloaderZone/WZML-X?style=flat-square&color=yellow&logo=github"/></a>
  <a href="https://github.com/DownloaderZone/WZML-X"><img src="https://img.shields.io/github/forks/DownloaderZone/WZML-X?style=flat-square&color=blue&logo=github"/></a>
  <a href="https://t.me/DOWNLOADERZONEUPDATES"><img src="https://img.shields.io/badge/Telegram-Channel-blue?style=flat-square&logo=telegram"/></a>
  <a href="https://t.me/DZONEDISCUSSION"><img src="https://img.shields.io/badge/Support-Group-blueviolet?style=flat-square&logo=telegram"/></a>
  <a href="https://github.com/DownloaderZone/WZML-X/blob/main/LICENSE"><img src="https://img.shields.io/github/license/DownloaderZone/WZML-X?style=flat-square&color=success"/></a>
</p>

---

## 🚀 Features

<details>
  <summary><b>View all features</b></summary>

- Multi-source Download: Supports torrents (qBittorrent, Aria2c), direct links, Mega.nz, YouTube (yt-dlp), devuploads, and more
- Flexible Uploads: Upload to Google Drive, Telegram, RClone remotes, or supported DDL sites
- Advanced File Management: Archive/extract (zip, rar, 7z), split/join files, rename, and more
- User & Sudo Controls: Per-user settings, limits, and admin controls
- Status & Queue System: Real-time status, unlimited tasks, and queue management
- RSS Automation: Auto-download and filter RSS feeds
- Database Support: MongoDB for persistent settings, tasks, and user data
- Docker Ready: Easy deployment with Docker & docker-compose
- Extensive Configurability: All features and limits are configurable via environment or config file
- Multi-cloud: RClone integration for any supported cloud (GDrive, OneDrive, Dropbox, etc)
- Multi-bot & Multi-user: Designed for groups, channels, and private use
- Token/Multi-Shortener Support: Support for token based usage and multi-shortener services
- **Actively Maintained**: By Downloader Zone & Team.
</details>

---

## 🖥️ Live Demo & Public Mirror/Leech Group

- Channel: [DOWNLOADER ZONE UPDATES](https://t.me/DOWNLOADERZONEUPDATES)
- Group: [DOWNLOADER ZONE FREE MIRROR LEECH GROUP](https://t.me/downloaderzonefreemirrorleech)

---

## 📦 Deploy Methods

- [Google Collab Deploy](https://colab.research.google.com/drive/1A9h93Qtyrk1Rf2902CXHOM0mTMah1AQ9?authuser=2)

---

## ⚙️ Configuration

All configuration is done via `config.env` (or environment variables). See `config_sample.py` for all options and detailed comments.

<details>
  <summary><b>Click to view all config variables</b></summary>

### Required
- `BOT_TOKEN`: Telegram Bot Token from @BotFather
- `OWNER_ID`: Telegram User ID of the bot owner
- `TELEGRAM_API`: Telegram API ID from https://my.telegram.org
- `TELEGRAM_HASH`: Telegram API Hash from https://my.telegram.org

### Optional (most common)
- `DATABASE_URL`: MongoDB connection string
- `DOWNLOAD_DIR`: Local download directory
- `AUTHORIZED_CHATS`: Space-separated list of allowed user/group IDs
- `SUDO_USERS`: Space-separated list of sudo user IDs
- `DEFAULT_UPLOAD`: `gd` (Google Drive), `rc` (RClone), or `ddl` (DDL sites)
- `GDRIVE_ID`: Google Drive folder/TeamDrive ID or `root`
- `RCLONE_PATH`: Default rclone path (e.g. `remote:path`)
- `RCLONE_FLAGS`: RClone flags (see [RClone Flags](https://rclone.org/flags/))
- `RCLONE_SERVE_URL`: URL for rclone serve (e.g. `http://myip:port`)
- `RCLONE_SERVE_PORT`: Port for rclone serve (default: 8080)
- `RCLONE_SERVE_USER`/`RCLONE_SERVE_PASS`: Auth for rclone serve
- `LEECH_LOG_ID`/`MIRROR_LOG_ID`: Chat IDs for logs
- `QUEUE_ALL`/`QUEUE_DOWNLOAD`/`QUEUE_UPLOAD`: Task queue limits
- `DAILY_TASK_LIMIT`, `DAILY_MIRROR_LIMIT`, `DAILY_LEECH_LIMIT`: User limits
- `YT_DLP_OPTIONS`: Default yt-dlp options (see [yt-dlp options](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184))
- `EXTENSION_FILTER`: Space-separated list of file extensions to block
- `SAFE_MODE`: Hide links/files in group, send to PM
- `TIMEZONE`: Timezone (default: Asia/Kolkata)

...and many more! See `config_sample.py`.

</details>

---

## 📝 Usage

- Start the bot on Telegram and use `/help` for all commands.
- All commands can be set automatically with the `SET_COMMANDS` variable.
- For advanced usage, see the Bot Commands below.

---
## 🤖 Bot Commands

<details>
  <summary>Click to view all bot commands</summary>

```
mirror - or /m Mirror
leech - or /l Leech
qbmirror - or /qm Mirror torrent using qBittorrent
qbleech - or /ql Leech torrent using qBittorrent
jdmirror - or /jm Mirror files using JDownloader
jdleech - or /jl Leech files using JDownloader
ytdl - or /y Mirror yt-dlp supported link
ytdlleech - or /yl Leech through yt-dlp supported link
clone - Copy file/folder to Drive
count - Count file/folder from Drive
select - Select files from torrent
list - Search files in Drive
search - Search for torrents with API
mediainfo - Get Mediainfo of the Target Media
rss - Rss menu
usetting - User settings
status - Get Mirror Status message
forcestart - Force start from queued task
cancel - Cancel a task
cancelall - Cancel all tasks
login - Login to Bot
ping - Ping the Bot
stats - Bot Usage Stats
speedtest - Check Internet Speed
help - All cmds with description
bsetting - Bot settings
del - Delete file/folder from Drive
restart - Restart the Bot
restartses - Restart User Sessions
```

</details>

---

## 🏷️ Credits & Authors
- **Downloader Zone** ([Telegram](https://t.me/DOWNLOADERZONEUPDATES), [GitHub](https://github.com/DOWNLOADER-ZONE))
- **BeastBots Team** ([Telegram](https://t.me/MirrorBeast), [GitHub](https://github.com/BeastBots))
- Base Repo is [WZML-X](https://github.com/SilentDemonSD/WZML-X)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <b>Made with ❤️ by Downloader Zone</b>
</p>

