from asyncio import sleep
from functools import partial
from os import path as ospath
from time import time

from pyrogram.enums import ButtonStyle
from pyrogram.filters import command, create, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from .. import LOGGER
from ..core.config_manager import Config
from ..core.plugin_installer import (
    MAX_ARCHIVE,
    InstallError,
    get_installer,
    install_dependencies,
)
from ..core.plugin_manager import get_plugin_manager
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


def _is_owner(user_id):
    return user_id == Config.OWNER_ID


def _tag(rec):
    mark = "✅" if rec.enabled else "⛔"
    icon = f"{rec.manifest.icon} " if rec.manifest.icon else ""
    return f"{mark} {icon}{rec.name}"


def _plugin_text(rec):
    man = rec.manifest
    lines = [f"⌬ <b><u>{man.icon + ' ' if man.icon else ''}{man.name}</u></b>", "│"]
    lines.append(f"┟ <b>Version</b> → <code>{man.version}</code>")
    lines.append(f"┠ <b>State</b> → {'Enabled' if rec.enabled else 'Disabled'}")
    if man.author:
        lines.append(f"┠ <b>Author</b> → {man.author}")
    lines.append(f"┠ <b>Source</b> → {rec.source}")
    if rec.commands:
        lines.append("┠ <b>Commands</b> → " + ", ".join(f"/{c}" for c in rec.commands))
    if man.callbacks:
        lines.append(f"┠ <b>Callbacks</b> → {len(man.callbacks)}")
    if man.tags:
        lines.append("┠ <b>Tags</b> → " + ", ".join(man.tags))
    if man.python_dependencies:
        lines.append("┠ <b>Requires</b> → " + ", ".join(man.python_dependencies))
    lines.append(f"┖ <b>About</b> → <i>{man.description or 'No description'}</i>")
    return "\n".join(lines)


async def build_menu(user_id, view="main", arg=""):
    manager = get_plugin_manager()
    installer = get_installer()
    buttons = ButtonMaker()
    owner = _is_owner(user_id)

    if view == "main":
        records = manager.list_plugins()
        on = len([r for r in records if r.enabled])
        buttons.data_button(
            f"Installed ({len(records)})", f"plugins {user_id} list", position="header"
        )
        buttons.data_button("Marketplace", f"plugins {user_id} mkt 0")
        if owner:
            buttons.data_button("Install", f"plugins {user_id} install")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        text = (
            "⌬ <b><u>Plugin Manager</u></b>\n│\n"
            f"┟ <b>Installed</b> → {len(records)}\n"
            f"┠ <b>Enabled</b> → {on}\n"
            f"┖ <b>Folder</b> → <code>plugins/</code>"
        )
        if Config.DISABLE_PLUGINS:
            text += "\n\n<i>Plugins are switched off in Module Settings.</i>"
        return text, buttons.build_menu(2)

    if view == "list":
        records = sorted(manager.list_plugins(), key=lambda r: r.name)
        for rec in records:
            buttons.data_button(_tag(rec), f"plugins {user_id} view {rec.name}")
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        if records:
            text = "⌬ <b><u>Installed Plugins</u></b>\n\n<i>Pick one to manage it.</i>"
        else:
            broken = manager.discover()
            text = "⌬ <b><u>Installed Plugins</u></b>\n\n<i>Nothing loaded yet.</i>"
            if broken:
                text += (
                    "\n\n<b>On disk but not loaded:</b> "
                    + ", ".join(f"<code>{b}</code>" for b in broken)
                    + "\n<i>Check the logs for why.</i>"
                )
        return text, buttons.build_menu(2)

    if view == "view":
        rec = manager.get(arg)
        if rec is None:
            return "<i>That plugin is not loaded any more.</i>", buttons.build_menu(1)
        if owner:
            if rec.enabled:
                buttons.data_button("Disable", f"plugins {user_id} off {arg}")
            else:
                buttons.data_button(
                    "Enable", f"plugins {user_id} on {arg}", style=ButtonStyle.PRIMARY
                )
            buttons.data_button("Reload", f"plugins {user_id} reload {arg}")
            if rec.manifest.config_schema:
                buttons.data_button("Settings", f"plugins {user_id} cfg {arg}")
            if rec.source in ("github", "market", "url"):
                buttons.data_button("Update", f"plugins {user_id} update {arg}")
            buttons.data_button(
                "Uninstall", f"plugins {user_id} rmask {arg}", style=ButtonStyle.DANGER
            )
        buttons.data_button("Back", f"plugins {user_id} list", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        return _plugin_text(rec), buttons.build_menu(2)

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
            icon = f"{item.get('icon')} " if item.get("icon") else ""
            mark = "✅ " if manager.get(item["id"]) else ""
            buttons.data_button(
                f"{mark}{icon}{item.get('name') or item['id']}",
                f"plugins {user_id} show {item['id']}",
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
        if total:
            text = (
                "⌬ <b><u>Plugin Marketplace</u></b>\n\n"
                f"<i>{total} plugin(s) from {len(installer.index_urls())} index(es).</i>"
            )
        else:
            text = (
                "⌬ <b><u>Plugin Marketplace</u></b>\n\n"
                "<i>No plugins found. The index may be unreachable, or you can add "
                "your own with PLUGIN_INDEXES in bot settings.</i>"
            )
        return text, buttons.build_menu(1, fb_cols=8, lb_cols=1)

    if view == "show":
        item = installer.index_entry(arg)
        if item is None:
            return "<i>That entry is gone from the index.</i>", buttons.build_menu(1)
        installed = get_plugin_manager().get(arg)
        if owner:
            label = "Reinstall" if installed else "Install"
            buttons.data_button(
                label, f"plugins {user_id} get {arg}", style=ButtonStyle.PRIMARY
            )
        buttons.data_button("Back", f"plugins {user_id} mkt 0", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        icon = f"{item.get('icon')} " if item.get("icon") else ""
        lines = [f"⌬ <b><u>{icon}{item.get('name') or arg}</u></b>", "│"]
        lines.append(f"┟ <b>Version</b> → <code>{item.get('version', '?')}</code>")
        if item.get("author"):
            lines.append(f"┠ <b>Author</b> → {item['author']}")
        if item.get("tags"):
            lines.append("┠ <b>Tags</b> → " + ", ".join(item["tags"]))
        if installed:
            lines.append(f"┠ <b>Installed</b> → <code>{installed.version}</code>")
        lines.append(f"┖ <b>About</b> → <i>{item.get('description') or 'No description'}</i>")
        return "\n".join(lines), buttons.build_menu(2)

    if view == "install":
        buttons.data_button("Upload a .zip", f"plugins {user_id} upload")
        buttons.data_button("From GitHub", f"plugins {user_id} github")
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        text = (
            "⌬ <b><u>Install a Plugin</u></b>\n\n"
            "<i>A plugin is a folder holding a <code>wzml_plugin.yml</code> manifest "
            "and its Python files. Plugin code runs with full access to this bot — "
            "only install what you trust.</i>"
        )
        return text, buttons.build_menu(2)

    if view == "deps":
        state = pending.get(user_id)
        if not state:
            return "<i>That request expired.</i>", buttons.build_menu(1)
        buttons.data_button(
            "Install & continue", f"plugins {user_id} deps_ok", style=ButtonStyle.PRIMARY
        )
        buttons.data_button(
            "Cancel", f"plugins {user_id} deps_no", style=ButtonStyle.DANGER
        )
        man = state["manifest"]
        text = (
            f"⌬ <b><u>{man.name} v{man.version}</u></b>\n\n"
            "<b>Needs these packages, which are not installed:</b>\n"
            + "\n".join(f"• <code>{d}</code>" for d in state["missing"])
            + "\n\n<i>Install them into the bot's environment and continue?</i>"
        )
        return text, buttons.build_menu(2)

    if view == "cfg":
        rec = manager.get(arg)
        if rec is None:
            return "<i>That plugin is not loaded any more.</i>", buttons.build_menu(1)
        items = manager.schema_items(arg)
        current = manager.effective_config(arg)
        lines = [f"⌬ <b><u>{arg} settings</u></b>", "│"]
        for index, (key, spec) in enumerate(items):
            value = current.get(key)
            shown = "not set" if value is None else str(value)
            edge = "┖" if index == len(items) - 1 else ("┟" if index == 0 else "┠")
            lines.append(f"{edge} <b>{key}</b> → <code>{shown}</code>")
            if owner:
                kind = str((spec or {}).get("type") or "string").lower()
                label = (
                    f"{key}: {'on' if value else 'off'}"
                    if kind in ("bool", "boolean")
                    else key
                )
                buttons.data_button(label, f"plugins {user_id} cfge {arg} {index}")
        if not items:
            lines.append("┖ <i>This plugin has no settings.</i>")
        if owner and items:
            buttons.data_button(
                "Reset all", f"plugins {user_id} cfgr {arg}", position="l_body"
            )
        buttons.data_button("Back", f"plugins {user_id} view {arg}", position="footer")
        buttons.data_button(
            "Close", f"plugins {user_id} close", position="footer", style=ButtonStyle.DANGER
        )
        return "\n".join(lines), buttons.build_menu(2, lb_cols=1)

    if view == "rmask":
        buttons.data_button(
            "Yes, remove it", f"plugins {user_id} rm {arg}", style=ButtonStyle.DANGER
        )
        buttons.data_button("No", f"plugins {user_id} view {arg}")
        return (
            f"⌬ <b>Uninstall <code>{arg}</code>?</b>\n\n"
            "<i>Its folder and stored settings are deleted. This cannot be undone.</i>",
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


async def _stage_done(query, staged, manifest, missing, source, url):
    user_id = query.from_user.id
    if missing:
        pending[user_id] = {
            "staged": staged,
            "manifest": manifest,
            "missing": missing,
            "source": source,
            "url": url,
        }
        text, markup = await build_menu(user_id, "deps")
        await edit_message(query.message, text, markup)
        return
    await _finish(query, staged, manifest, source, url)


async def _finish(query, staged, manifest, source, url):
    user_id = query.from_user.id
    installer = get_installer()
    try:
        await installer.finalize(staged, manifest, source=source, url=url)
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message, f"<b>Install failed:</b> <i>{err}</i>\n\n{text}", markup
        )
        return
    text, markup = await build_menu(user_id, "view", manifest.name)
    await edit_message(
        query.message,
        f"<b>Installed {manifest.name} v{manifest.version}.</b>\n\n{text}",
        markup,
    )


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
            f"<b>Rejected:</b> <i>that file is {doc.file_size} bytes, the limit is "
            f"{MAX_ARCHIVE}.</i>\n\n{text}",
            markup,
        )
        return
    target = str(installer.staging_dir / f"upload_{user_id}.bin")
    from aiofiles.os import makedirs

    await makedirs(ospath.dirname(target), exist_ok=True)
    await edit_message(query.message, "<i>Downloading the archive…</i>")
    await message.download(file_name=target)
    try:
        staged, manifest, missing = await installer.stage_archive(target)
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message, f"<b>Rejected:</b> <i>{err}</i>\n\n{text}", markup
        )
        return
    finally:
        from aiofiles.os import remove

        try:
            await remove(target)
        except OSError:
            pass
    await _stage_done(query, staged, manifest, missing, "upload", doc.file_name or "")


@new_task
async def _on_github(client, message, query):
    user_id = query.from_user.id
    waiting[user_id] = False
    installer = get_installer()
    spec = (message.text or "").strip()
    await delete_message(message)
    await edit_message(query.message, f"<i>Fetching {spec}…</i>")
    try:
        staged, manifest, missing = await installer.stage_github(spec)
    except InstallError as err:
        text, markup = await build_menu(user_id, "install")
        await edit_message(
            query.message, f"<b>Rejected:</b> <i>{err}</i>\n\n{text}", markup
        )
        return
    await _stage_done(query, staged, manifest, missing, "github", spec)


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
            query.message, f"<b>{key}: {err}</b>\n\n{text}", markup
        )
    ok, err = await manager.set_config(plugin, key, value)
    text, markup = await build_menu(user_id, "cfg", plugin)
    if not ok:
        text = f"<b>Could not save:</b> <i>{err}</i>\n\n{text}"
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

    mutating = {
        "on", "off", "reload", "rm", "rmask", "get", "update",
        "install", "upload", "github", "deps_ok", "deps_no",
        "cfge", "cfgr",
    }
    if action in mutating and not _is_owner(user_id):
        return await query.answer("Owner only.", show_alert=True)
    if action in mutating and Config.DISABLE_PLUGINS:
        return await query.answer(
            "Plugins are switched off in Module Settings.", show_alert=True
        )

    if action == "close":
        await query.answer()
        await delete_message(query.message.reply_to_message)
        return await delete_message(query.message)

    if action == "stop":
        waiting[user_id] = False
        await query.answer("Cancelled")
        text, markup = await build_menu(user_id, "install")
        return await edit_message(query.message, text, markup)

    if action in ("main", "list", "install"):
        await query.answer()
        text, markup = await build_menu(user_id, action)
        return await edit_message(query.message, text, markup)

    if action in ("view", "show", "mkt", "rmask", "cfg"):
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

    if action in ("on", "off", "reload"):
        await query.answer(f"Working on {arg}…")
        if action == "on":
            ok, err = await manager.enable(arg)
        elif action == "off":
            ok, err = await manager.disable(arg)
        else:
            ok, err = await manager.reload(arg)
        text, markup = await build_menu(user_id, "view" if ok else "list", arg)
        if not ok:
            text = f"<b>{action} failed:</b> <i>{err}</i>\n\n{text}"
        return await edit_message(query.message, text, markup)

    if action == "rm":
        await query.answer("Removing…")
        ok, err = await installer.uninstall(arg)
        text, markup = await build_menu(user_id, "list")
        if not ok:
            text = f"<b>Uninstall failed:</b> <i>{err}</i>\n\n{text}"
        return await edit_message(query.message, text, markup)

    if action in ("get", "update"):
        await query.answer("Fetching…")
        if action == "get":
            item = installer.index_entry(arg)
            if item is None:
                return await query.answer("Not in the index any more.", show_alert=True)
            url, sha, source = item["url"], item.get("sha256"), "market"
        else:
            rec = manager.get(arg)
            if rec is None or not rec.url:
                return await query.answer("No source to update from.", show_alert=True)
            url, sha, source = rec.url, None, rec.source
        await edit_message(query.message, f"<i>Downloading {arg}…</i>")
        try:
            if source == "github":
                staged, manifest, missing = await installer.stage_github(url)
            else:
                staged, manifest, missing = await installer.stage_url(url, sha)
        except InstallError as err:
            text, markup = await build_menu(user_id, "mkt", "0")
            return await edit_message(
                query.message, f"<b>Rejected:</b> <i>{err}</i>\n\n{text}", markup
            )
        return await _stage_done(query, staged, manifest, missing, source, url)

    if action == "deps_ok":
        state = pending.pop(user_id, None)
        if not state:
            return await query.answer("That request expired.", show_alert=True)
        await query.answer("Installing packages…")
        await edit_message(
            query.message,
            "<i>Installing " + ", ".join(state["missing"]) + "…</i>",
        )
        ok, err = await install_dependencies(state["missing"])
        if not ok:
            installer.clear_staging()
            text, markup = await build_menu(user_id, "install")
            return await edit_message(
                query.message,
                f"<b>Could not install the packages:</b> <i>{err}</i>\n\n{text}",
                markup,
            )
        return await _finish(
            query, state["staged"], state["manifest"], state["source"], state["url"]
        )

    if action == "deps_no":
        pending.pop(user_id, None)
        installer.clear_staging()
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
        note = (spec or {}).get("description") or ""
        prompt = (
            f"⌬ <b>Set <code>{key}</code> for {arg}</b>\n\n"
            f"<i>Type: {kind}"
            + (f" ({', '.join(bounds)})" if bounds else "")
            + "</i>\n"
            + (f"<i>{note}</i>\n" if note else "")
            + "\n<i>Send the new value.</i>"
        )
        return await _ask(
            client, query, prompt, partial(_on_config, plugin=arg, key=key, spec=spec)
        )

    if action == "upload":
        await query.answer()
        return await _ask(
            client,
            query,
            "⌬ <b>Send the plugin .zip</b>\n\n"
            "<i>It must contain a wzml_plugin.yml manifest.</i>",
            _on_upload,
        )

    if action == "github":
        await query.answer()
        return await _ask(
            client,
            query,
            "⌬ <b>Send the repository</b>\n\n"
            "<i>Like <code>owner/repo</code> or <code>owner/repo@branch</code>.</i>",
            _on_github,
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
