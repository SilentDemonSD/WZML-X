from asyncio import sleep
from functools import partial
from os import path as ospath
from time import time

from pyrogram.enums import ButtonStyle
from pyrogram.filters import command, create, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from .. import LOGGER, sudo_users, user_data
from ..core.config_manager import Config
from ..core.plugin_installer import (
    MAX_ARCHIVE,
    InstallError,
    get_installer,
    install_dependencies,
    official_index_url,
    official_repo_spec,
)
from ..core.plugin_manager import _version_tuple, get_plugin_manager
from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)

PAGE = 6
INPUT_TIMEOUT = 120
waiting = {}
pending = {}

OWNER_ONLY = {
    "on",
    "off",
    "rm",
    "rmask",
    "get",
    "update",
    "rescan",
    "deps_ok",
    "deps_no",
    "cfge",
    "cfgr",
}
SUDO_ALLOWED = {"install", "upload", "github", "pick", "dup"}
MUTATING = OWNER_ONLY | SUDO_ALLOWED


def _is_owner(user_id):
    try:
        return int(user_id) == int(Config.OWNER_ID or 0)
    except (TypeError, ValueError):
        return str(user_id) == str(Config.OWNER_ID)


def _is_sudo(user_id):
    if _is_owner(user_id):
        return True
    return user_id in sudo_users or bool(user_data.get(user_id, {}).get("SUDO"))


def _may(user_id, action):
    if action in OWNER_ONLY:
        return _is_owner(user_id)
    if action in SUDO_ALLOWED:
        return _is_sudo(user_id)
    return True


def _wz(title, rows, note=""):
    lines = [f"⌬ <b><u>{title}</u></b>", "│"]
    for index, (key, value) in enumerate(rows):
        edge = "┟" if index == 0 else ("┖" if index == len(rows) - 1 else "┠")
        lines.append(f"{edge} <b>{key}</b> → {value}")
    if not rows:
        lines = [f"⌬ <b><u>{title}</u></b>"]
    if note:
        lines.append("")
        lines.append(f"<i>{note}</i>")
    return "\n".join(lines)


def _newer(rec):
    entry = get_installer().index_entry(rec.name)
    if not entry:
        return ""
    remote = str(entry.get("version") or "").strip()
    if not remote:
        return ""
    if _version_tuple(remote) > _version_tuple(rec.version):
        return remote
    return ""


def _var(name):
    return str(name).upper()


def _state_of(rec):
    return "Enabled" if rec.enabled else "Disabled"


def _style_of(rec):
    return ButtonStyle.SUCCESS if rec.enabled else ButtonStyle.DANGER


async def build_menu(user_id, view="main", arg=""):
    manager = get_plugin_manager()
    installer = get_installer()
    buttons = ButtonMaker()
    owner = _is_owner(user_id)
    sudo = _is_sudo(user_id)

    if view == "main":
        records = manager.list_plugins()
        idle = manager.available()
        on = len([r for r in records if r.enabled])
        total = len(records) + len(idle)
        buttons.data_button(
            f"Installed ({total})", f"plugins {user_id} list", position="header"
        )
        buttons.data_button("Marketplace", f"plugins {user_id} mkt 0")
        if sudo:
            buttons.data_button(
                "Install", f"plugins {user_id} install", style=ButtonStyle.PRIMARY
            )
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        rows = [("Installed", str(total)), ("Enabled", str(on))]
        if len(records) - on:
            rows.append(("Disabled", str(len(records) - on)))
        if idle:
            rows.append(("Not Loaded", str(len(idle))))
        rows.append(("Folder", f"<code>{manager.plugins_dir}</code>"))
        note = ""
        if Config.DISABLE_PLUGINS:
            note = "Plugins are switched off in Module Settings."
        return _wz("Plugin Manager", rows, note), buttons.build_menu(2)

    if view == "list":
        records = sorted(manager.list_plugins(), key=lambda r: r.name)
        idle = sorted(manager.available())
        for rec in records:
            buttons.data_button(
                rec.name, f"plugins {user_id} view {rec.name}", style=_style_of(rec)
            )
        for name in idle:
            buttons.data_button(name, f"plugins {user_id} dview {name}")
        if owner:
            buttons.data_button(
                "Rescan", f"plugins {user_id} rescan", position="l_body"
            )
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )

        if not records and not idle:
            rows = [
                ("Looked In", f"<code>{manager.plugins_dir}</code>"),
                ("Folder Exists", str(manager.plugins_dir.is_dir())),
                ("Needs", "a subfolder holding <code>wzml_plugin.yml</code>"),
            ]
            return (
                _wz(
                    "Installed Plugins",
                    rows,
                    "No plugin folders found. If you expected the bundled plugins "
                    "here, the deploy did not include the plugins/ folder.",
                ),
                buttons.build_menu(2, lb_cols=1),
            )

        rows = [(rec.name, _state_of(rec)) for rec in records]
        rows += [
            (name, manager.errors.get(name, "Not Loaded")[:48]) for name in idle
        ]
        return (
            _wz("Installed Plugins", rows, "Pick one to manage it."),
            buttons.build_menu(2, lb_cols=1),
        )

    if view == "view":
        rec = manager.get(arg)
        if rec is None:
            return "<i>That plugin is not loaded any more.</i>", buttons.build_menu(1)
        newer = _newer(rec)
        if owner:
            if rec.enabled:
                buttons.data_button(
                    "Disable", f"plugins {user_id} off {arg}", style=ButtonStyle.DANGER
                )
            else:
                buttons.data_button(
                    "Enable", f"plugins {user_id} on {arg}", style=ButtonStyle.SUCCESS
                )
            if newer:
                buttons.data_button(
                    f"Update to {newer}",
                    f"plugins {user_id} update {arg}",
                    position="header",
                    style=ButtonStyle.PRIMARY,
                )
            if rec.manifest.config_schema:
                buttons.data_button("Settings", f"plugins {user_id} cfg {arg}")
            buttons.data_button(
                "Uninstall", f"plugins {user_id} rmask {arg}", style=ButtonStyle.DANGER
            )
        buttons.data_button("Back", f"plugins {user_id} list", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        man = rec.manifest
        version = f"<code>{man.version}</code>"
        if newer:
            version += f" → <code>{newer}</code> available"
        rows = [("Version", version), ("State", _state_of(rec))]
        if man.author:
            rows.append(("Author", man.author))
        rows.append(("Source", rec.source))
        if rec.commands:
            rows.append(
                ("Commands", ", ".join(f"/{c}" for c in rec.commands))
            )
        if man.callbacks:
            rows.append(("Callbacks", str(len(man.callbacks))))
        if man.tags:
            rows.append(("Tags", ", ".join(man.tags)))
        if man.python_dependencies:
            rows.append(("Requires", ", ".join(man.python_dependencies)))
        rows.append(("About", f"<i>{man.description or 'No description'}</i>"))
        note = ""
        if not owner:
            note = (
                "Only the owner can change plugins. You are "
                f"<code>{user_id}</code>, OWNER_ID is <code>{Config.OWNER_ID}</code>."
            )
        return _wz(man.name, rows, note), buttons.build_menu(2)

    if view == "dview":
        man = manager.disk_manifest(arg)
        if owner:
            buttons.data_button(
                "Uninstall", f"plugins {user_id} rmask {arg}", style=ButtonStyle.DANGER
            )
            buttons.data_button("Rescan", f"plugins {user_id} rescan")
        buttons.data_button("Back", f"plugins {user_id} list", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        if man is None:
            rows = [
                ("State", "Not Loaded"),
                ("Problem", "its manifest cannot be read, check the log"),
            ]
            return _wz(arg, rows), buttons.build_menu(2)
        rows = [("Version", f"<code>{man.version}</code>"), ("State", "Not Loaded")]
        if man.author:
            rows.append(("Author", man.author))
        if man.command_names():
            rows.append(
                ("Commands", ", ".join(f"/{c}" for c in man.command_names()))
            )
        if man.python_dependencies:
            rows.append(("Requires", ", ".join(man.python_dependencies)))
        if arg in manager.errors:
            rows.append(("Error", f"<i>{manager.errors[arg]}</i>"))
        rows.append(("About", f"<i>{man.description or 'No description'}</i>"))
        return (
            _wz(
                man.name,
                rows,
                "Its code is not in memory and its commands are inactive.",
            ),
            buttons.build_menu(2),
        )

    if view == "mkt":
        page = int(arg or 0)
        try:
            entries = await installer.fetch_index()
        except Exception as err:
            entries = []
            LOGGER.error(f"marketplace unreachable: {err}")
        total = len(entries)
        chunk = entries[page * PAGE : page * PAGE + PAGE]
        for item in chunk:
            installed = manager.get(item["id"])
            buttons.data_button(
                item.get("name") or item["id"],
                f"plugins {user_id} show {item['id']}",
                style=ButtonStyle.SUCCESS if installed else ButtonStyle.DEFAULT,
            )
        pages = max(1, -(-total // PAGE))
        if pages > 1:
            for index in range(pages):
                buttons.data_button(
                    f"[{index + 1}]" if index == page else str(index + 1),
                    f"plugins {user_id} mkt {index}",
                    position="f_body",
                )
        buttons.data_button("Refresh", f"plugins {user_id} refresh", position="l_body")
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )

        installed = len([e for e in entries if manager.get(e["id"])])
        extra = len(installer.index_urls()) - 1
        rows = [("Available", str(total))]
        if installed:
            rows.append(("Already Installed", f"{installed} of {total}"))
        if extra:
            rows.append(("Sources", f"official + {extra} custom"))
        rows.append(("Official", f"<code>{official_index_url()}</code>"))
        for url, why in getattr(installer, "problems", [])[:3]:
            rows.append((url.rsplit("/", 3)[-1] or "index", f"<i>{why}</i>"))
        note = ""
        if not total:
            note = (
                "Nothing to install from here yet. Use Install to add one from a "
                "zip or a GitHub repo, or point PLUGIN_INDEXES at your own index."
            )
        return _wz("Plugin Marketplace", rows, note), buttons.build_menu(
            2, fb_cols=8, lb_cols=1
        )

    if view == "show":
        item = installer.index_entry(arg)
        if item is None:
            return "<i>That entry is gone from the index.</i>", buttons.build_menu(1)
        installed = manager.get(arg)
        if sudo:
            buttons.data_button(
                "Reinstall" if installed else "Install",
                f"plugins {user_id} get {arg}",
                style=ButtonStyle.PRIMARY,
            )
        buttons.data_button("Back", f"plugins {user_id} mkt 0", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        rows = [("Version", f"<code>{item.get('version', '?')}</code>")]
        if item.get("author"):
            rows.append(("Author", item["author"]))
        if item.get("tags"):
            rows.append(("Tags", ", ".join(item["tags"])))
        if installed:
            rows.append(("Installed", f"<code>{installed.version}</code>"))
        rows.append(("About", f"<i>{item.get('description') or 'No description'}</i>"))
        return _wz(item.get("name") or arg, rows), buttons.build_menu(2)

    if view == "install":
        buttons.data_button("Upload a .zip", f"plugins {user_id} upload")
        buttons.data_button("From GitHub", f"plugins {user_id} github")
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        rows = [
            ("Needs", "a folder with <code>wzml_plugin.yml</code>"),
            ("Accepts", "a .zip upload, or <code>owner/repo</code>"),
            ("Limit", f"{MAX_ARCHIVE // (1024 * 1024)} MB"),
        ]
        return (
            _wz(
                "Install a Plugin",
                rows,
                "Plugin code runs with full access to this bot. Only install what "
                "you trust.",
            ),
            buttons.build_menu(2),
        )

    if view == "pick":
        state = pending.get(user_id)
        if not state or not state.get("items"):
            return "<i>That request expired.</i>", buttons.build_menu(1)
        rows = []
        for index, (_, man) in enumerate(state["items"]):
            here = manager.get(man.name)
            if here:
                buttons.data_button(
                    man.name,
                    f"plugins {user_id} dup {man.name}",
                    style=ButtonStyle.PRIMARY,
                )
                rows.append((man.name, f"installed <code>{here.version}</code>"))
            else:
                buttons.data_button(
                    man.name,
                    f"plugins {user_id} pick {index}",
                    style=ButtonStyle.SUCCESS,
                )
                rows.append((man.name, f"<code>{man.version}</code>"))
        buttons.data_button("Back", f"plugins {user_id} install", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        head = [("Source", f"<code>{state.get('label') or state.get('url')}</code>")]
        return (
            _wz("Plugins Found", head + rows, "Pick one to install."),
            buttons.build_menu(2),
        )

    if view == "deps":
        state = pending.get(user_id)
        if not state:
            return "<i>That request expired.</i>", buttons.build_menu(1)
        buttons.data_button(
            "Install & Continue",
            f"plugins {user_id} deps_ok",
            style=ButtonStyle.SUCCESS,
        )
        buttons.data_button(
            "Cancel", f"plugins {user_id} deps_no", style=ButtonStyle.DANGER
        )
        man = state["manifest"]
        rows = [
            ("Plugin", f"{man.name} <code>{man.version}</code>"),
            ("Missing", ", ".join(f"<code>{d}</code>" for d in state["missing"])),
        ]
        return (
            _wz(
                "Dependencies Needed",
                rows,
                "Install them into the bot's environment and continue?",
            ),
            buttons.build_menu(2),
        )

    if view == "cfg":
        rec = manager.get(arg)
        if rec is None:
            return "<i>That plugin is not loaded any more.</i>", buttons.build_menu(1)
        items = manager.schema_items(arg)
        current = manager.effective_config(arg)
        stored = rec.config or {}
        rows = []
        for index, (key, spec) in enumerate(items):
            value = current.get(key)
            shown = "not set" if value in (None, "") else value
            label = _var(key)
            mark = "" if key in stored else " (default)"
            rows.append((label, f"<code>{shown}</code>{mark}"))
            if owner:
                kind = str((spec or {}).get("type") or "string").lower()
                if kind in ("bool", "boolean"):
                    buttons.data_button(
                        label,
                        f"plugins {user_id} cfge {arg} {index}",
                        style=ButtonStyle.SUCCESS if value else ButtonStyle.DANGER,
                    )
                else:
                    buttons.data_button(label, f"plugins {user_id} cfge {arg} {index}")
        if owner and items:
            buttons.data_button(
                "Reset All", f"plugins {user_id} cfgr {arg}", position="l_body"
            )
        buttons.data_button("Back", f"plugins {user_id} view {arg}", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        note = "" if items else "This plugin has no settings."
        return _wz(f"{_var(arg)} Settings", rows, note), buttons.build_menu(2, lb_cols=1)

    if view == "rmask":
        buttons.data_button(
            "Yes, Remove", f"plugins {user_id} rm {arg}", style=ButtonStyle.DANGER
        )
        buttons.data_button("No", f"plugins {user_id} list")
        rows = [("Plugin", f"<code>{arg}</code>"), ("Removes", "its folder and settings")]
        return (
            _wz("Confirm Uninstall", rows, "This cannot be undone."),
            buttons.build_menu(2),
        )

    return "<i>Unknown menu.</i>", buttons.build_menu(1)


async def _ask(client, query, prompt, handler):
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    waiting[user_id] = True
    buttons = ButtonMaker()
    buttons.data_button("Cancel", f"plugins {user_id} stop", style=ButtonStyle.DANGER)
    await edit_message(query.message, prompt, buttons.build_menu(1))

    async def _filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user
            and user.id == user_id
            and event.chat.id == chat_id
            and (event.text or event.document)
        )

    registered = client.add_handler(
        MessageHandler(partial(handler, query=query), filters=create(_filter)), group=-1
    )
    started = time()
    try:
        while waiting.get(user_id):
            await sleep(0.5)
            if time() - started > INPUT_TIMEOUT:
                waiting[user_id] = False
                text, markup = await build_menu(user_id, "install")
                await edit_message(query.message, text, markup)
    finally:
        client.remove_handler(*registered)
        waiting.pop(user_id, None)


def _forget(user_id):
    state = pending.pop(user_id, None)
    if state and state.get("stage"):
        get_installer().drop_stage(state["stage"])
    return state


async def _offer(query, stage, found, source, url, label=""):
    user_id = query.from_user.id
    _forget(user_id)
    pending[user_id] = {
        "stage": stage,
        "items": found,
        "source": source,
        "url": url,
        "label": label or url,
    }
    if len(found) == 1:
        return await _stage_done(query, found[0][0], found[0][1], source, url)
    text, markup = await build_menu(user_id, "pick")
    await edit_message(query.message, text, markup)


async def _stage_done(query, staged, manifest, source, url):
    user_id = query.from_user.id
    installer = get_installer()
    try:
        missing = installer.check(manifest)
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        return await edit_message(
            query.message, f"<b>Rejected</b> → <i>{err}</i>\n\n{text}", markup
        )
    if missing:
        state = dict(pending.get(user_id) or {})
        state.update(
            {
                "staged": staged,
                "manifest": manifest,
                "missing": missing,
                "source": source,
                "url": url,
            }
        )
        pending[user_id] = state
        text, markup = await build_menu(user_id, "deps")
        await edit_message(query.message, text, markup)
        return
    await _finish(query, staged, manifest, source, url)


async def _finish(query, staged, manifest, source, url):
    user_id = query.from_user.id
    installer = get_installer()
    state = pending.get(user_id) or {}
    more = len(state.get("items") or []) > 1
    try:
        await installer.finalize(
            staged, manifest, source=source, url=url, cleanup=not more
        )
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message, f"<b>Install failed</b> → <i>{err}</i>\n\n{text}", markup
        )
        return
    head = f"<b>Installed</b> → {manifest.name} <code>{manifest.version}</code>"
    if more:
        text, markup = await build_menu(user_id, "pick")
    else:
        _forget(user_id)
        text, markup = await build_menu(user_id, "view", manifest.name)
    await edit_message(query.message, f"{head}\n\n{text}", markup)


@new_task
async def _on_upload(client, message, query):
    user_id = query.from_user.id
    waiting[user_id] = False
    installer = get_installer()
    doc = message.document
    await delete_message(message)
    if doc is None:
        await edit_message(query.message, "<i>That was not a file. Try again.</i>")
        return
    if doc.file_size and doc.file_size > MAX_ARCHIVE:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message,
            f"<b>Rejected</b> → <i>that file is {doc.file_size} bytes, the limit is "
            f"{MAX_ARCHIVE}.</i>\n\n{text}",
            markup,
        )
        return
    target = str(installer.staging_dir / f"upload_{user_id}.bin")
    from aiofiles.os import makedirs, remove

    await makedirs(ospath.dirname(target), exist_ok=True)
    await edit_message(query.message, "<i>Downloading the archive…</i>")
    await message.download(file_name=target)
    try:
        stage, found = await installer.stage_archive(target)
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message, f"<b>Rejected</b> → <i>{err}</i>\n\n{text}", markup
        )
        return
    finally:
        try:
            await remove(target)
        except OSError:
            pass
    await _offer(query, stage, found, "upload", "", doc.file_name or "upload")


@new_task
async def _on_github(client, message, query):
    user_id = query.from_user.id
    waiting[user_id] = False
    installer = get_installer()
    spec = (message.text or "").strip()
    await delete_message(message)
    await edit_message(query.message, f"<i>Fetching {spec}…</i>")
    try:
        stage, found = await installer.stage_github(spec)
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message, f"<b>Rejected</b> → <i>{err}</i>\n\n{text}", markup
        )
        return
    await _offer(query, stage, found, "github", spec, spec)


@new_task
async def _on_config(client, message, query, plugin=None, key=None, spec=None):
    user_id = query.from_user.id
    waiting[user_id] = False
    raw = (message.text or "").strip()
    await delete_message(message)
    manager = get_plugin_manager()
    try:
        value = manager.coerce_config(spec, raw)
    except ValueError as err:
        text, markup = await build_menu(user_id, "cfg", plugin)
        return await edit_message(
            query.message, f"<b>{key}</b> → <i>{err}</i>\n\n{text}", markup
        )
    ok, err = await manager.set_config(plugin, key, value)
    text, markup = await build_menu(user_id, "cfg", plugin)
    if not ok:
        text = f"<b>Could not save</b> → <i>{err}</i>\n\n{text}"
    await edit_message(query.message, text, markup)


@new_task
async def plugins_command(client, message):
    manager = get_plugin_manager()
    manager.bot = client
    text, markup = await build_menu(message.from_user.id, "main")
    await send_message(message, text, markup)


@new_task
async def edit_plugins_menu(client, query):
    user_id = query.from_user.id
    data = query.data.split()
    if len(data) < 3 or user_id != int(data[1]):
        return await query.answer("Not yours!", show_alert=True)

    action = data[2]
    arg = data[3] if len(data) > 3 else ""
    manager = get_plugin_manager()
    manager.bot = client
    installer = get_installer()

    if action in MUTATING and not _may(user_id, action):
        return await query.answer(
            "Only the owner can change plugins."
            if action in OWNER_ONLY
            else "Sudo users only.",
            show_alert=True,
        )
    if action in MUTATING and Config.DISABLE_PLUGINS:
        return await query.answer(
            "Plugins are switched off in Module Settings.", show_alert=True
        )

    if action == "close":
        _forget(user_id)
        await query.answer()
        await delete_message(query.message.reply_to_message)
        return await delete_message(query.message)

    if action == "stop":
        waiting[user_id] = False
        _forget(user_id)
        await query.answer("Cancelled")
        text, markup = await build_menu(user_id, "install")
        return await edit_message(query.message, text, markup)

    if action in ("main", "list", "install"):
        await query.answer()
        text, markup = await build_menu(user_id, action)
        return await edit_message(query.message, text, markup)

    if action in ("view", "show", "mkt", "rmask", "cfg", "dview"):
        await query.answer()
        text, markup = await build_menu(user_id, action, arg)
        return await edit_message(query.message, text, markup)

    if action == "refresh":
        await query.answer("Refreshing the index…")
        try:
            await installer.fetch_index(force=True)
        except Exception as err:
            LOGGER.error(f"index refresh failed: {err}")
        text, markup = await build_menu(user_id, "mkt", "0")
        return await edit_message(query.message, text, markup)

    if action == "rescan":
        found, fresh = await manager.rescan()
        if fresh:
            said = f"Loaded {', '.join(fresh)}."
        elif found:
            said = f"{len(found)} plugin folder(s), all already loaded."
        else:
            said = f"No plugin folders in {manager.plugins_dir}."
        await query.answer(said, show_alert=True)
        text, markup = await build_menu(user_id, "list")
        return await edit_message(query.message, text, markup)

    if action in ("on", "off"):
        if action == "on":
            ok, err = await manager.enable(arg)
            said = f"{arg} enabled."
        else:
            ok, err = await manager.disable(arg)
            said = f"{arg} disabled."
        await query.answer(said if ok else (err or "Failed."), show_alert=not ok)
        text, markup = await build_menu(user_id, "view" if ok else "list", arg)
        return await edit_message(query.message, text, markup)

    if action == "rm":
        ok, err = await installer.uninstall(arg)
        await query.answer(
            f"Removed {arg}." if ok else (err or "Failed."), show_alert=True
        )
        text, markup = await build_menu(user_id, "list")
        return await edit_message(query.message, text, markup)

    if action == "dup":
        return await query.answer("Already Added", show_alert=True)

    if action == "pick":
        state = pending.get(user_id)
        index = int(arg) if arg.isdigit() else -1
        if not state or not 0 <= index < len(state.get("items") or []):
            return await query.answer("That request expired.", show_alert=True)
        root, manifest = state["items"][index]
        if manager.get(manifest.name):
            return await query.answer("Already Added", show_alert=True)
        await query.answer(f"Installing {manifest.name}…")
        return await _stage_done(query, root, manifest, state["source"], state["url"])

    if action in ("get", "update"):
        await query.answer("Fetching…")
        if action == "get":
            item = installer.index_entry(arg)
            if item is None:
                return await query.answer("Not in the index any more.", show_alert=True)
            source = "github" if item.get("repo") else "market"
            url = item.get("repo") or item["url"]
            fetch = partial(installer.stage_entry, item)
        else:
            rec = manager.get(arg)
            if rec is not None and rec.url and rec.source in ("github", "market", "url"):
                source, url = rec.source, rec.url
                fetch = partial(
                    installer.stage_github if source == "github" else installer.stage_url,
                    url,
                    pick=arg,
                )
            else:
                source, url = "github", official_repo_spec()
                fetch = partial(installer.stage_github, url, pick=arg)
        await edit_message(query.message, f"<i>Downloading {arg}…</i>")
        try:
            stage, found = await fetch()
        except InstallError as err:
            back = "view" if action == "update" and manager.get(arg) else "mkt"
            text, markup = await build_menu(
                user_id, back, arg if back == "view" else "0"
            )
            return await edit_message(
                query.message, f"<b>Rejected</b> → <i>{err}</i>\n\n{text}", markup
            )
        if action == "update":
            pending[user_id] = {
                "stage": stage,
                "items": found[:1],
                "source": source,
                "url": url,
                "label": url,
            }
            return await _stage_done(query, found[0][0], found[0][1], source, url)
        return await _offer(query, stage, found, source, url, url)

    if action == "deps_ok":
        state = pending.get(user_id)
        if not state or not state.get("manifest"):
            return await query.answer("That request expired.", show_alert=True)
        await query.answer("Installing packages…")
        await edit_message(
            query.message,
            "<i>Installing " + ", ".join(state["missing"]) + "…</i>",
        )
        ok, err = await install_dependencies(state["missing"])
        if not ok:
            _forget(user_id)
            text, markup = await build_menu(user_id, "install")
            return await edit_message(
                query.message,
                f"<b>Could not install</b> → <i>{err}</i>\n\n{text}",
                markup,
            )
        return await _finish(
            query, state["staged"], state["manifest"], state["source"], state["url"]
        )

    if action == "deps_no":
        _forget(user_id)
        await query.answer("Cancelled")
        text, markup = await build_menu(user_id, "install")
        return await edit_message(query.message, text, markup)

    if action == "cfgr":
        await query.answer("Cleared")
        await manager.reset_config(arg)
        text, markup = await build_menu(user_id, "cfg", arg)
        return await edit_message(query.message, text, markup)

    if action == "cfge":
        index = int(data[4]) if len(data) > 4 else -1
        items = manager.schema_items(arg)
        if not 0 <= index < len(items):
            return await query.answer("That setting is gone.", show_alert=True)
        key, spec = items[index]
        kind = str((spec or {}).get("type") or "string").lower()
        if kind in ("bool", "boolean"):
            await query.answer()
            current = manager.effective_config(arg).get(key)
            await manager.set_config(arg, key, not bool(current))
            text, markup = await build_menu(user_id, "cfg", arg)
            return await edit_message(query.message, text, markup)

        await query.answer()
        bounds = []
        if (spec or {}).get("min") is not None:
            bounds.append(f"min {spec['min']}")
        if (spec or {}).get("max") is not None:
            bounds.append(f"max {spec['max']}")
        if (spec or {}).get("choices"):
            bounds.append("one of " + ", ".join(str(c) for c in spec["choices"]))
        current = manager.effective_config(arg).get(key)
        rows = [
            ("Variable", f"<code>{_var(key)}</code>"),
            ("Type", kind),
            ("Current", f"<code>{'not set' if current in (None, '') else current}</code>"),
        ]
        if bounds:
            rows.append(("Limits", ", ".join(bounds)))
        if (spec or {}).get("description"):
            rows.append(("About", f"<i>{spec['description']}</i>"))
        prompt = (
            _wz(f"{_var(arg)} Settings", rows)
            + f"\n\n<i>Send a valid value for <code>{_var(key)}</code>.</i>"
            + f"\n┖ <b>Time Left :</b> <code>{INPUT_TIMEOUT} sec</code>"
        )
        return await _ask(
            client, query, prompt, partial(_on_config, plugin=arg, key=key, spec=spec)
        )

    if action == "upload":
        await query.answer()
        rows = [("Send", "a .zip of the plugin folder"), ("Needs", "wzml_plugin.yml")]
        return await _ask(
            client, query, _wz("Upload a Plugin", rows), _on_upload
        )

    if action == "github":
        await query.answer()
        rows = [
            ("Send", "<code>owner/repo</code>"),
            ("Or", "<code>owner/repo@branch</code>"),
        ]
        return await _ask(
            client, query, _wz("Install from GitHub", rows), _on_github
        )

    await query.answer()


def register_plugin_commands():
    from ..core.tg_client import TgClient
    from ..helper.telegram_helper.bot_commands import BotCommands

    TgClient.bot.add_handler(
        MessageHandler(
            plugins_command,
            filters=command(BotCommands.PluginsCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(
            edit_plugins_menu, filters=regex("^plugins") & CustomFilters.sudo
        )
    )
