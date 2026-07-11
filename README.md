<p align="center">
   <img src="docs/WZML-X.png" alt="WZML-X logo" width="420">
</p>

<h1 align="center">WZML-X</h1>

<p align="center">
   Telegram mirroring and leeching platform with a container-based runtime, a lightweight web UI, and a configurable transfer pipeline.
</p>

<p align="center">
   <a href="https://github.com/SilentDemonSD/WZML-X">
      <img src="https://img.shields.io/github/stars/SilentDemonSD/WZML-X?style=for-the-badge&logo=github&label=Stars" alt="Stars">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/search?l=python">
      <img src="https://img.shields.io/github/languages/top/SilentDemonSD/WZML-X?style=for-the-badge&logo=python&label=Python" alt="Python">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/blob/main/docker-compose.yml">
      <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose">
   </a>

   <a href="https://t.me/WZML_X">
      <img src="https://img.shields.io/badge/Telegram-Community-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/SilentDemonSD/WZML-X?style=for-the-badge&label=License" alt="License">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/commits/main">
      <img src="https://img.shields.io/github/last-commit/SilentDemonSD/WZML-X?style=for-the-badge&label=Last%20Commit" alt="Last Commit">
   </a>
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
   - [Support](#support)
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

WZML-X is built for users who want a single bot stack that can mirror, leech, manage files, and expose a simple web-based selection flow without stitching together multiple tools. The README focuses on what you need to deploy it quickly, understand the moving parts, and tune the behavior safely.

## What It Covers

| Capability | Outcome |
|---|---|
| Mirroring | Send files to Telegram with a controllable pipeline |
| Leeching | Deliver files in the format you prefer, including document and media workflows |
| File selection UI | Review and select torrent / NZB / upload contents before finalizing |
| Multi-source downloads | Use qBittorrent, Aria2, JDownloader, Mega, Rapidgator, NZB, and yt-dlp integrations |
| Storage and upload paths | Push content to Google Drive, Rclone, Mega, and other supported routes |
| Automation | Limit tasks, tune queues, and manage startup updates from one config layer |

## How It Runs

Deploy with Docker and provide the required configuration values. The container takes care of the runtime path, so users only need to build or start the image and set their settings.

<details>
   <summary>What you need <kbd>Click Here</kbd></summary>

   - Docker installed
   - Your Telegram bot token and Telegram API credentials
   - A MongoDB connection string
   - The optional service credentials you want to enable, such as Drive, Rclone, Mega, Rapidgator, JDownloader, or SABnzbd
</details>

## Deployment

<details open>
   <summary>VPS / Dedicated Server (Recommended)</summary>

   ```bash
   git clone https://github.com/SilentDemonSD/WZML-X.git
   cd WZML-X
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
   git clone https://github.com/SilentDemonSD/WZML-X.git
   cd WZML-X
   docker build -t wzmlx .
   docker run -p 8080:8080 wzmlx
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

<details>
   <summary>Legacy Workflow Guide</summary>

   Some users still rely on the external workflow path referenced by the previous README:

   - [WZ Deploy workflow guide](https://github.com/SilentDemonSD/WZ-Deploy/tree/main?tab=readme-ov-file#2%EF%B8%8F%E2%83%A3-method-2-github-workflow-guide)

   Keep this only if that workflow still matches your deployment style.
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
   - Mega and Rapidgator credentials
   - SABnzbd server definitions
   - Google Drive settings
   - RSS, search, media metadata, and logging controls
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
- Deployment notes: the docs site linked from the repository at WZ Docs
- Configuration reference: `config_sample.py`

## Support

<details>
   <summary>Join Community</summary>

   - Telegram channel: https://t.me/WZML_X
   - Support group: https://t.me/WZML_Support
</details>

## Credits

WZML-X is a fork of [mirror-leech-telegram-bot](https://github.com/anasty17/mirror-leech-telegram-bot). The base project belongs to [anasty17](https://github.com/anasty17) and upstream contributors.

<details>
   <summary>Bot Authors</summary>

   <table>
      <thead>
         <tr>
            <th>Avatar</th>
            <th>Name</th>
            <th>Role</th>
            <th>Profile</th>
         </tr>
      </thead>
      <tbody>
         <tr>
            <td><img src="https://avatars.githubusercontent.com/u/105407900?v=4" width="72" alt="SilentDemonSD"></td>
            <td>SilentDemonSD</td>
            <td>Author, UI design, and custom features</td>
            <td><a href="https://github.com/SilentDemonSD">GitHub</a></td>
         </tr>
         <tr>
            <td><img src="https://avatars.githubusercontent.com/u/93116400?v=4" width="72" alt="RjRiajul"></td>
            <td>RjRiajul</td>
            <td>Co-author and maintainer</td>
            <td><a href="https://github.com/rjriajul">GitHub</a></td>
         </tr>
         <tr>
            <td><img src="https://avatars.githubusercontent.com/u/113664541?v=4" width="72" alt="CodeWithWeeb"></td>
            <td>CodeWithWeeb</td>
            <td>Feature expansion and wrap-up improvements</td>
            <td><a href="https://github.com/weebzone">GitHub</a></td>
         </tr>
         <tr>
            <td><img src="https://avatars.githubusercontent.com/u/84721324?v=4" width="72" alt="Maverick"></td>
            <td>Maverick</td>
            <td>Co-author and bug testing</td>
            <td><a href="https://github.com/MajnuRangeela">GitHub</a></td>
         </tr>
      </tbody>
   </table>
</details>

## Fork Customizations & Syncing

If you are hosting your own fork of this project (for example, to use custom features like Rapidgator downloads) and want to keep it updated with the upstream repository:

### Setup Your Fork Remotes
Rename the default remote to `upstream` and add your fork as `origin`:
```bash
git remote rename origin upstream
git remote add origin https://github.com/your-username/WZML-X.git
```

### Sync Updates From Upstream
To pull new updates from the original repository into your fork without losing your custom code (like your Rapidgator implementation), run:
```bash
# Fetch the latest changes from upstream
git fetch upstream

# Rebase the upstream branch (wzv3) onto your current branch (e.g. main)
git rebase upstream/wzv3

# Push the rebased code to your fork
git push origin main --force
```

### Rapidgator Downloader Integration
This fork includes native premium Rapidgator downloading support.

1. **Global Configuration**: Add the following parameters to your `config.env` or `config.py` file:
   - `RAPIDGATOR_EMAIL`: Your premium Rapidgator account email.
   - `RAPIDGATOR_PASSWORD`: Your premium Rapidgator account password.
   - `DISABLE_RAPIDGATOR` (Optional): Set to `True` if you want to turn off Rapidgator support. Default: `False`.
   - `RAPIDGATOR_LIMIT` (Optional): Size limit (in GB) for downloading from Rapidgator. Default: `0` (unlimited).

2. **Per-User Configuration**: Users can also configure their own premium Rapidgator credentials inside Telegram via `/usersettings` -> **Mirror Settings** -> **Rapidgator Tools**.

## License

This project is distributed under the terms of the repository license. See [LICENSE](LICENSE) for the full text.

