<p align="center">
   <img src="docs/w-icon.svg" alt="Borderless logo" width="160">
</p>

<h1 align="center">Borderless</h1>

<p align="center">
   Telegram mirroring and leeching platform with a container-based runtime, a lightweight web UI, and a configurable transfer pipeline.
</p>


## Index

<details open>
   <summary>Table of Contents <kbd>Click Here</kbd></summary>

   - [At a Glance](#at-a-glance)
   - [Why Use It](#why-use-it)
   - [What It Covers](#what-it-covers)
   - [How It Runs](#how-it-runs)
   - [Deployment](#deployment)
   - [Configuration](#configuration)
   - [Project Layout](#project-layout)
   - [Documentation](#documentation)
   - [Credits](#credits)
   - [License](#license)
</details>

## At a Glance

| Area | Details |
|---|---|
| Runtime | Python Telegram bot + web UI |
| Deployment | Docker & Docker Compose (buildx) |
| Required config | `BOT_TOKEN`, `TELEGRAM_API`, `TELEGRAM_HASH`, `OWNER_ID`, `DATABASE_URL` |
| License | [LICENSE](LICENSE) |

## Why Use It

Borderless is a Telegram transfer platform for mirroring, leeching, file management, and web-based file selection. It connects multiple download sources and storage destinations through one configurable bot stack.

## What It Covers

| Capability | Outcome |
|---|---|
| Mirroring | Send files to Telegram with a controllable pipeline |
| Leeching | Deliver files in the format you prefer, including document and media workflows |
| File selection UI | Review and select torrent / NZB / upload contents before finalizing |
| Multi-source downloads | Use qBittorrent, Aria2, JDownloader, Mega, NZB, and yt-dlp integrations |
| Storage and upload paths | Push content to Google Drive, Rclone, Mega, and other supported routes |
| Automation | Limit tasks, tune queues, and manage startup updates from one config layer |

## How It Runs

Deploy with Docker and provide the required configuration values. The container takes care of the runtime path, so users only need to build or start the image and set their settings.

<details>
   <summary>What you need <kbd>Click Here</kbd></summary>

   - Docker installed
   - Your Telegram bot token and Telegram API credentials
   - A MongoDB connection string
   - The optional service credentials you want to enable, such as Drive, Rclone, Mega, JDownloader, or SABnzbd
</details>

## Deployment

<details open>
   <summary>VPS / Dedicated Server (Recommended)</summary>

   ```bash
   git clone YOUR_BORDERLESS_REPOSITORY_URL Borderless
   cd Borderless
   cp config_sample.py config.py
   # Edit config.py with your values
   docker buildx compose up -d
   ```

   The bot runs behind a Cloudflare quick tunnel by default. Check the tunnel URL:

   ```bash
   docker compose logs tunnel
   ```

   You'll see a `https://*.trycloudflare.com` URL — that's your bot's web UI.

   To stop:

   ```bash
   docker buildx compose down
   ```
</details>

<details>
   <summary>VPS with VPN (Gluetun)</summary>

   1. Uncomment the `gluetun` service in `docker-compose.yml`
   2. Fill in your VPN provider credentials
   3. Set `network_mode: "service:gluetun"` on the `app` service
   4. Start:

   ```bash
   docker buildx compose up -d
   ```

   All traffic (including the cloudflared tunnel) routes through the VPN.
</details>

<details>
   <summary>Multi-Instance (Multiple Bots)</summary>

   Each bot needs its own `config.py` and data volumes. Example for a second bot:

   1. Create `config2.py` with different `BOT_TOKEN`, `OWNER_ID`, etc.
   2. Uncomment `app2` and `tunnel2` in `docker-compose.yml`
   3. Edit volume mounts to use `config2.py` and separate data dirs
   4. Start:

   ```bash
   docker buildx compose up -d
   ```

   Each bot gets its own cloudflared tunnel URL. Admin ports (qBittorrent, SABnzbd) are mapped to different host ports (`127.0.0.1:8091`, etc.).
</details>

<details>
   <summary>Single Container (Manual)</summary>

   ```bash
   git clone YOUR_BORDERLESS_REPOSITORY_URL Borderless
   cd Borderless
   docker build -t borderless .
   docker run -p 8080:8080 borderless
   ```
</details>

<details>
   <summary>Deployment Notes</summary>

   1. If you use qBittorrent, tune `AsyncIOThreadsCount` to your machine size.
   2. Stop the container before removing it, and remove the container before pruning images.
   3. Useful cleanup commands:

   ```bash
   docker container prune
   docker image prune -a
   ```
</details>


## Configuration

Start with the required values:

- `BOT_TOKEN`
- `TELEGRAM_API`
- `TELEGRAM_HASH`
- `OWNER_ID`
- `DATABASE_URL`

Then tune the optional behavior from `config_sample.py`.

<details>
   <summary>Important user-facing settings</summary>

   | Setting | User impact |
   |---|---|
   | `DEFAULT_LANG` | Bot language |
   | `STATUS_LIMIT` | How much status data is shown |
   | `DEFAULT_UPLOAD` | Default upload target |
   | `LEECH_SPLIT_SIZE` | How large leech outputs are split |
   | `QUEUE_ALL`, `QUEUE_DOWNLOAD`, `QUEUE_UPLOAD` | Queue pressure and concurrency |
   | `SHOW_CLOUD_LINK` | Whether cloud links are shown to users |
   | `WEB_PINCODE` | Protects web access to file selection |
</details>

<details>
   <summary>Integrations available in config</summary>

   The sample config also covers:

   - qBittorrent and Aria2-related controls
   - JDownloader login details
   - Mega credentials
   - SABnzbd server definitions
   - Google Drive settings
   - RSS, search, media metadata, and logging controls
</details>

<details>
   <summary>AllDebrid (<code>-ad</code>)</summary>

   Set `ALLDEBRID_API_KEY` (default: empty, feature off) in `config_sample.py`,
   in the environment, or from **Bot Settings → Config Variables → ALLDEBRID_API_KEY**.

   Add `-ad` to a mirror/leech command to route the input through AllDebrid:

   - `/mirror <filehost link> -ad` unlocks premium hosts (1fichier, rapidgator,
     mega, ...) and hands the direct link to the normal downloader.
   - `/leech <magnet> -ad` (or reply to a `.torrent` with `-ad`) uploads the
     torrent to AllDebrid, waits for it to finish there, then downloads every
     file from AllDebrid's CDN — aria2/qBittorrent are bypassed entirely.

   `ALLDEBRID_NO_SEED_TIMEOUT` (default: `180`) caps how many seconds a magnet may
   stall with no seeders and no download progress before the task is aborted.
   Set it to `0` to disable the check and rely on AllDebrid's own dead-torrent
   reporting instead.

   The flag is documented in the mirror help menu under the **AllDebrid** button.
   Without a key the task fails with `ALLDEBRID_API_KEY is not configured`;
   without `-ad` nothing changes. Magnets stop after 3 min with no seeders and
   2 h overall, and are removed from your AllDebrid history if the task fails.
</details>

## Project Layout

| Path | Purpose |
|---|---|
| `bot/` | Bot core, handlers, listeners, and modules |
| `web/` | FastAPI app, templates, and the file selector UI |
| `gen_scripts/` | Setup helpers for sessions, tokens, and drive configuration |
| `plugins/` | Optional bot plugins |
| `qBittorrent/` | Default qBittorrent configuration |
| `sabnzbd/` | Default SABnzbd configuration |

## Documentation

> [!NOTE]
> This documentation is still being expanded.

- Full guides: `docs/`
- Configuration reference: `config_sample.py`

## Credits

Borderless is built on the [mirror-leech-telegram-bot](https://github.com/anasty17/mirror-leech-telegram-bot) project.


## License

This project is distributed under the terms of the repository license. See [LICENSE](LICENSE) for the full text.

