# WZML-X Plugins

A plugin is a folder in here holding a `wzml_plugin.yml` manifest and one or more
Python files. Manage them from Telegram with `/plugins` — browse the marketplace,
upload a `.zip`, install from GitHub, and enable or disable anything live without
restarting the bot.

> Plugin code runs inside the bot process with full access to its tokens,
> database and host. There is no sandbox. Only install plugins you trust.
> Enabling, disabling and removing is **owner-only**. Sudo users can browse and
> install, but not change what is already there.

---

## Contents

1. [Quick start](#quick-start)
2. [Layout](#layout)
3. [Manifest reference](#manifest-reference)
4. [Writing handlers](#writing-handlers)
5. [Multi-file plugins](#multi-file-plugins)
6. [Lifecycle hooks](#lifecycle-hooks)
7. [Settings](#settings)
8. [The helpers you get](#the-helpers-you-get)
9. [States and actions](#states-and-actions)
10. [Dependencies](#dependencies)
11. [Installing and publishing](#installing-and-publishing)
12. [What gets your plugin refused](#what-gets-your-plugin-refused)
13. [Debugging](#debugging)
14. [Bundled plugins](#bundled-plugins)

---

## Quick start

A working plugin is two files. Create `plugins/hello/`:

**`plugins/hello/wzml_plugin.yml`**

```yaml
name: hello
version: "1.0.0"
author: You
description: Say hello
entry: hello.py
commands:
  - name: hello
    handler: hello_command
    description: Say hello
    access: authorized
```

**`plugins/hello/hello.py`**

```python
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.message_utils import send_message


@new_task
async def hello_command(_, message):
    await send_message(message, "<b>Hello!</b>")
```

Open `/plugins → Installed`, or restart. `/hello` now works, and it shows up in
`/help` on its own.

---

## Layout

```
plugins/
  hello/
    wzml_plugin.yml      required — the manifest
    hello.py             the manifest's `entry`
    helpers.py           optional siblings, imported with `from .helpers import ...`
    assets/              any files you like; they travel with the plugin
```

The folder name **must** match `name:` in the manifest. It is also the plugin's
identity everywhere: the database record, the module namespace, and the callback
data in `/plugins`.

---

## Manifest reference

`wzml_plugin.yml` is the single source of truth. Nothing about a plugin's
commands lives in Python.

### Top level

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string | **required** | `[a-z][a-z0-9_]{1,31}`. Must equal the folder name. |
| `version` | string | **required** | Free-form, e.g. `"1.2.0"`. Quote it, or YAML reads `1.0` as a float. |
| `entry` | string | `<name>.py` | The Python file loaded as the plugin. |
| `author` | string | `""` | Shown in `/plugins`. |
| `description` | string | `""` | Shown in `/plugins` and `/help`. |
| `icon` | string | `""` | Accepted for compatibility; the menu does not show it. |
| `license` | string | `""` | Informational. |
| `repository` | string | `""` | Informational. |
| `tags` | list | `[]` | Shown in `/plugins` and used by marketplace listings. |
| `min_bot_version` | string | `""` | Refuses to load on anything older. |
| `max_bot_version` | string | `""` | Refuses to load on anything newer. |
| `python_dependencies` | list | `[]` | pip requirement strings. |
| `commands` | list | `[]` | See below. |
| `callbacks` | list | `[]` | See below. |
| `config_schema` | map | `{}` | See [Settings](#settings). |

Unknown top-level keys are **ignored with a warning**, never fatal — a manifest
written for a newer bot still loads on an older one. These older spellings are
accepted as aliases: `main_file` → `entry`, `min_wzml_version` →
`min_bot_version`, `max_wzml_version` → `max_bot_version`, `settings_schema` →
`config_schema`, `deps` → `python_dependencies`.

### `commands[]`

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | **required** | The command, without the slash. |
| `handler` | `<name>_command` | A module-level `async def` in the entry file. |
| `description` | `""` | Shown in `/help`. |
| `usage` | `""` | Shown on the plugin's page. |
| `aliases` | `[]` | Extra names for the same handler. |
| `access` | `authorized` | `authorized`, `sudo`, `owner`, or `authorized_uset`. |

A bare string is accepted as shorthand — `commands: [ping]` means
`{name: ping, handler: ping_command, access: authorized}`.

`Config.CMD_SUFFIX` is appended automatically to every name and alias, so a bot
running with a suffix answers `/hello1` without the plugin doing anything.

### `callbacks[]`

| Key | Default | Meaning |
| --- | --- | --- |
| `pattern` | **required** | Regex matched against `query.data`. |
| `handler` | — | A module-level `async def` in the entry file. |
| `access` | `authorized` | Same values as commands. |
| `description` | `""` | Informational. |

Prefix your callback data with the plugin name so patterns cannot collide:
`^hello` matching `hello <user_id> <action>`.

---

## Writing handlers

Handlers are plain module-level coroutines. The bot builds the pyrogram handler
for you from the manifest — you never call `add_handler` yourself.

```python
from bot import LOGGER
from bot.helper.ext_utils.bot_utils import new_task, sync_to_async
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import edit_message, send_message


@new_task
async def hello_command(client, message):
    buttons = ButtonMaker()
    buttons.data_button("Wave back", f"hello {message.from_user.id} wave")
    await send_message(message, "<b>Hello!</b>", buttons.build_menu(1))


@new_task
async def hello_callback(client, query):
    data = query.data.split()
    if query.from_user.id != int(data[1]):
        return await query.answer("Not yours!", show_alert=True)
    await query.answer("👋")
    await edit_message(query.message, "<b>Waved.</b>")
```

Notes that matter:

- **`@new_task` is optional but usually right.** It runs your handler as a
  detached task so a slow command does not block the dispatcher. Use it for
  anything doing network or disk work.
- **Parse mode is HTML.** `<b>`, `<i>`, `<code>`, `<a href="">`. Escape user
  input with `html.escape` before interpolating it.
- **Never block the event loop.** Wrap synchronous libraries:
  `result = await sync_to_async(requests.get, url)`.
- **Callback ownership.** Anyone can press a button. Put the owning user id in
  the callback data and check it, as above.
- **Callback data is capped at 64 bytes** by Telegram. Keep it short.

---

## Multi-file plugins

Split freely. The entry file is imported as a package, so relative imports work:

```python
# plugins/hello/hello.py
from .render import card
from .api import fetch
```

```python
# plugins/hello/render.py
from bot.helper.ext_utils.status_utils import get_readable_file_size


def card(data):
    return f"<b>{data['name']}</b> — {get_readable_file_size(data['size'])}"
```

Two rules:

- **Bot imports are absolute** — `from bot.helper...`, never `from ...helper`.
  Your plugin lives outside the `bot` package.
- **Your own modules are relative** — `from .render import card`.

Each plugin is imported under `wzplugins.<name>`, so its module name can never
collide with a real library. A plugin called `imdb` doing `import imdb` still
gets the actual imdb library, not itself.

---

## Lifecycle hooks

Optional. Subclass `PluginBase` anywhere in the entry file and the bot will find
and instantiate it:

```python
from bot import LOGGER
from bot.core.plugin_manager import PluginBase


class HelloPlugin(PluginBase):
    async def on_load(self):
        # Return False to refuse the load.
        LOGGER.info("hello ready")
        return True

    async def on_unload(self):
        # Close sessions, cancel tasks, delete temp files. Always called.
        return True

    async def on_enable(self):
        return True

    async def on_disable(self):
        return True

    async def on_configure(self, config):
        # Called after any setting changes.
        return True
```

Inside the class, `self.manifest` is the parsed manifest, `self.bot` is the
pyrogram client, `self.config` is the current settings dict, and
`self.get_config("key", default)` reads one value.

**If you start anything long-lived — a background task, an aiohttp session, a
scheduler job — stop it in `on_unload`.** Nothing else will.

---

## Settings

Declare `config_schema` and `/plugins → your plugin → Settings` renders an editor
for it. Values persist in the database per bot.

```yaml
config_schema:
  timeout:
    type: integer
    default: 60
    min: 30
    max: 300
    description: Seconds before giving up
  label:
    type: string
    default: Results
  loud:
    type: boolean
    default: false
  mode:
    type: string
    default: fast
    choices: [fast, slow]
  hosts:
    type: list
    default: []
```

Types: `integer`, `float`, `string`, `boolean`, `list` (entered comma-separated).
`min`/`max` apply to numbers, `choices` to anything. Booleans toggle with a
single tap; everything else prompts for a value and is validated before it is
stored.

Read them in your code:

```python
class HelloPlugin(PluginBase):
    async def on_configure(self, config):
        LOGGER.info(f"timeout is now {config['timeout']}")
        return True


# or from anywhere:
from bot.core.plugin_manager import get_plugin_manager

cfg = get_plugin_manager().effective_config("hello")
timeout = cfg["timeout"]
```

`effective_config` merges your declared defaults with whatever the owner set, so
every key in the schema is always present.

---

## The helpers you get

The bot's own utilities, with their real signatures:

```python
from bot import LOGGER, bot_loop, task_dict, task_dict_lock, user_data
from bot.core.config_manager import Config
from bot.core.tg_client import TgClient

from bot.helper.ext_utils.bot_utils import (
    new_task,                 # decorator: run the handler as a detached task
    sync_to_async,            # await sync_to_async(fn, *args, **kwargs)
    cmd_exec,                 # stdout, stderr, code = await cmd_exec([...])
    get_content_type,         # await get_content_type(url) -> str | None
    download_image_url,       # await download_image_url(url) -> path | None
)
from bot.helper.ext_utils.status_utils import (
    get_readable_file_size,   # 1536 -> "1.5 KiB"
    get_readable_time,        # 3661 -> "1h 1m 1s"
)
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.telegraph_helper import telegraph

from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import (
    send_message,             # (message, text, buttons=None, photo=None)
    edit_message,             # (message, text, buttons=None, photo=None)
    send_file,                # (message, file, caption="", buttons=None)
    delete_message,           # (*messages) — ignores None safely
    auto_delete_message,      # (*messages, stime=90)
)
```

Buttons:

```python
buttons = ButtonMaker()
buttons.data_button("Label", "callback data")
buttons.url_button("Open", "https://example.com")
buttons.data_button("Close", "hello close", position="footer")
markup = buttons.build_menu(2)          # 2 columns
```

Positions are `default`, `header`, `f_body`, `l_body`, `footer`.

`send_message(..., photo="IMAGES")` picks a random configured banner image.

---

## States and actions

A plugin is in one of three states, and `/plugins → Installed` shows each one
with a coloured button plus a line naming the state:

| Button | State | Meaning |
| --- | --- | --- |
| SUCCESS | Enabled | In memory, commands live. |
| DANGER | Disabled | In memory, commands off. |
| plain | Not Loaded | Not in memory. Files still on disk. |

Every action and exactly what it touches:

| Action | Handlers | Module in memory | Files on disk | DB record |
| --- | --- | --- | --- | --- |
| **enable** | attached | reused | kept | `enabled: true` |
| **disable** | detached | **kept** | kept | `enabled: false` |
| **rescan** | attached for anything new | imported | kept | seeded if new |
| **update** | rebuilt | re-imported | replaced | version bumped |
| **uninstall** | detached | purged | **deleted** | **deleted** |

**Disable is cheap and reversible** — the code stays in memory, only the handlers
come off, so `/yourcommand` stops answering instantly and re-enabling is
immediate. Both the enabled and disabled choices persist across restarts.

Every installed plugin has an **Update** button. If it came from GitHub, the
marketplace or a URL it re-fetches that source; a bundled or hand-copied one
re-fetches from your upstream repo and branch, picking the folder by name.

Plugins are loaded at boot. **Rescan** picks up a folder you dropped in while the
bot was running, and reports how many it found and how many were newly loaded.
A folder that fails to load stays listed with the reason on its page rather than
disappearing.

Everything above is serialized behind a lock, so two people mashing buttons in
`/plugins` cannot interleave a disable with a reload and leave a handler
stranded.

At boot the bot reads the database, loads every plugin folder it finds, and
attaches handlers only for the ones that are enabled. A folder with no database
record is treated as newly bundled and starts enabled. Command tables and `/help`
are rebuilt **once** for the whole batch, not once per plugin.

`DISABLE_PLUGINS` in Module Settings unloads everything live and blocks the
system entirely until it is switched back on.

---

## Dependencies

List pip requirement strings:

```yaml
python_dependencies:
  - speedtest-cli>=2.1.3
  - imdbio
  - pillow~=10.0
```

Presence is checked against installed **distributions**, not import names, so
`speedtest-cli` resolves correctly even though you `import speedtest`.

When something is missing, installing the plugin shows the list and asks the
owner to confirm; on approval the bot installs into its own environment and
continues. Nothing is ever installed silently. A plugin whose dependencies are
missing will not load and says so in the log.

If you are bundling a plugin into the repo itself, add its dependencies to the
top-level `requirements.txt` too — bundled plugins ship enabled, so they need to
resolve before anyone can open `/plugins`.

---

## Installing and publishing

Three routes, all owner-only, all from `/plugins → Install`:

**Upload** — send a `.zip` of the folder. Both shapes work:

```
hello.zip                       hello.zip
  wzml_plugin.yml                 hello/
  hello.py                          wzml_plugin.yml
                                    hello.py
```

**GitHub** — send `owner/repo`, `owner/repo@branch`, or a full GitHub URL. The
bot finds **every** plugin folder in the archive, not just the first, and shows
them as a list: green means it is not installed yet, blue means you already have
it and pressing it just says "Already Added". Pick one and it installs; the
download is kept so you can install several from the same repo without fetching
it again.

**Marketplace** — entries come from an index file. The official index is read
from your configured upstream:

```
https://raw.githubusercontent.com/<UPSTREAM_REPO>/<UPSTREAM_BRANCH>/plugins/index.json
```

so a fork with `UPSTREAM_REPO` and `UPSTREAM_BRANCH` set gets its own list
automatically — you do not need to configure anything. `PLUGIN_INDEXES` is only
for **extra** indexes; set it to a list of URLs. The exact URL in use is shown on
the Marketplace page.

> `index.schema.json` is the JSON-Schema that *describes* the format.
> It is **not an index** — do not put it in `PLUGIN_INDEXES`. The bot detects
> that mistake and says so on the Marketplace page.

An entry names its download one of two ways:

```json
{
  "plugins": [
    {
      "id": "hello",
      "name": "Hello",
      "version": "1.0.0",
      "description": "Say hello",
      "tags": ["utility"],
      "url": "https://example.com/hello-1.0.0.zip",
      "sha256": "9f3c…"
    },
    {
      "id": "goodbye",
      "version": "1.0.0",
      "repo": "someone/their-bot@main"
    }
  ]
}
```

Use `url` for a standalone archive of the plugin folder. Use `repo` when the
plugin lives inside a bigger repository — the bot downloads the repo archive and
picks out the folder whose manifest `name` matches the entry's `id`. That is how
the bundled plugins are listed.

`sha256` is optional. When present the download is refused on any mismatch.

Upgrades are atomic: the previous version is kept aside, and if the new one fails
to import it is restored and re-registered automatically.

---

## What gets your plugin refused

The loader is strict on purpose. Any of these stops the plugin with a message in
the log and in `/plugins`:

- The manifest is missing, unreadable, or has no `name`/`version`.
- `name` is not `[a-z][a-z0-9_]{1,31}`, or does not match the folder name.
- `entry` points outside the plugin folder.
- A declared command already belongs to a built-in or another plugin — you get
  told which. Nothing is registered, rather than silently losing to whichever was
  registered first.
- `min_bot_version` / `max_bot_version` exclude the running bot.
- A `python_dependencies` entry is not installed.
- The entry file raises on import.
- `on_load` returns `False` or raises.

For archives, additionally: path traversal, absolute paths, symlinks, more than
512 entries, more than 16 MB compressed or 48 MB unpacked.

A manifest naming a handler that does not exist is **not** fatal — the plugin
loads, that one command is skipped, and the log names the missing function.

---

## Debugging

- `/plugins → Installed` lists what loaded. Anything on disk that failed is
  listed separately with a pointer to the log.
- `/log` or `log.txt` carries the reason. Every refusal is logged with the plugin
  name.
- After editing a file, use **Reload** — the module is re-imported from disk.
- `LOGGER.info` / `LOGGER.error` from your plugin land in the same log.
- Import errors usually mean a relative bot import. Use `from bot.helper...`.

---

## Bundled plugins

These ship with the bot and are ordinary plugins — read them as worked examples.

| Plugin | Commands | Needs | Shows off |
| --- | --- | --- | --- |
| `speedtest` | `/speedtest`, `/spt` | speedtest-cli | multi-file, `sync_to_async` |
| `imdb` | `/imdb` | imdbio, pycountry | a callback handler |
| `mediainfo` | `/mediainfo`, `/mi` | — | telegraph output, `cmd_exec` |
| `nzb_search` | `/nzbsearch`, `/ns` | — | aiohttp, reading `Config` |
| `gen_pyro_sess` | `/exportsession` | — | its own runtime handlers and client |

Disable or uninstall any of them from `/plugins`; the choice is stored per bot
and survives a restart.
