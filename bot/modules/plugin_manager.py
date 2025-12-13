from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import Message

from .. import LOGGER
from ..core.plugin_manager import get_plugin_manager
from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import edit_message, send_message, delete_message


async def get_plugins_menu(user_id: int, stype: str = "main"):
    plugin_manager = get_plugin_manager()
    buttons = ButtonMaker()
    
    if stype == "main":
        loaded_plugins = plugin_manager.list_plugins()
        available_plugins = plugin_manager.discover_plugins()
        
        buttons.data_button("Loaded Plugins", f"plugins {user_id} loaded", position="header")
        buttons.data_button("Available Plugins", f"plugins {user_id} available")
        buttons.data_button("Install from GitHub", f"plugins {user_id} github")
        buttons.data_button("Plugin Info", f"plugins {user_id} info")
        buttons.data_button("Check Updates", f"plugins {user_id} updates")
        buttons.data_button("Close", f"plugins {user_id} close", position="footer")
        
        text = f"""⌬ <b>Plugin Management System</b>
│
┟ <b>Loaded Plugins:</b> {len(loaded_plugins)}
┠ <b>Available Plugins:</b> {len(available_plugins)}
┠ <b>GitHub Plugins:</b> {len([p for p in plugin_manager.get_plugin_registry().values() if p.get('source_type') == 'github'])}
┖ <b>Total Plugins:</b> {len(available_plugins)}"""
        
        btns = buttons.build_menu(2)
        
    elif stype == "loaded":
        loaded_plugins = plugin_manager.list_plugins()
        
        for plugin in loaded_plugins:
            status = "✅" if plugin.enabled else "❌"
            source_icon = "🐙" if plugin.source_type == "github" else "📁"
            buttons.data_button(
                f"{status} {source_icon} {plugin.name}",
                f"plugins {user_id} plugin {plugin.name}"
            )
        
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button("Close", f"plugins {user_id} close", position="footer")
        
        text = f"""⌬ <b>Loaded Plugins</b>
│
┟ <b>Total Loaded:</b> {len(loaded_plugins)}
┖ <b>Legend:</b> ✅ Enabled | ❌ Disabled | 🐙 GitHub | 📁 Local"""
        
        btns = buttons.build_menu(1)
        
    elif stype == "available":
        available_plugins = plugin_manager.discover_plugins()
        loaded_plugins = [p.name for p in plugin_manager.list_plugins()]
        
        for plugin in available_plugins:
            if plugin not in loaded_plugins:
                registry = plugin_manager.get_plugin_registry()
                source_icon = "🐙" if registry.get(plugin, {}).get('source_type') == 'github' else "📦"
                buttons.data_button(
                    f"{source_icon} {plugin}",
                    f"plugins {user_id} load {plugin}"
                )
        
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button("Close", f"plugins {user_id} close", position="footer")
        
        unloaded_count = len([p for p in available_plugins if p not in loaded_plugins])
        text = f"""⌬ <b>Available Plugins</b>
│
┟ <b>Unloaded Plugins:</b> {unloaded_count}
┖ <b>Legend:</b> 🐙 GitHub | 📦 Local"""
        
        btns = buttons.build_menu(1)
        
    elif stype == "github":
        text = """⌬ <b>Install from GitHub</b>
│
┟ Send the GitHub repository URL
┠ Format: username/repository
┠ Example: octocat/Hello-World
┖ Or full URL: https://github.com/username/repo

<b>Note:</b> Repository must contain wzml_plugin.yml"""
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button("Close", f"plugins {user_id} close", position="footer")
        btns = buttons.build_menu(1)
        
    elif stype == "updates":
        text = """⌬ <b>Plugin Updates</b>
│
┟ Checking for updates...
┖ This feature will check GitHub repositories for newer versions
        
<b>Coming Soon:</b> Auto-update functionality"""
        
        buttons.data_button("Check Now", f"plugins {user_id} check_updates")
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button("Close", f"plugins {user_id} close", position="footer")
        btns = buttons.build_menu(1)
        
    elif stype == "info":
        loaded_plugins = plugin_manager.list_plugins()
        
        text = "⌬ <b>Plugin Information</b>\n│\n"
        for plugin in loaded_plugins:
            status = "✅ Enabled" if plugin.enabled else "❌ Disabled"
            source_info = f" ({plugin.source_type.title()})"
            text += f"┟ <b>{plugin.name}</b> v{plugin.version}{source_info}\n"
            text += f"┠ Author: {plugin.author}\n"
            text += f"┠ Status: {status}\n"
            text += f"┠ Commands: {', '.join(plugin.commands) if plugin.commands else 'None'}\n"
            if plugin.manifest:
                text += f"┠ Dependencies: {', '.join(plugin.manifest.python_dependencies) if plugin.manifest.python_dependencies else 'None'}\n"
            text += f"┖ Description: {plugin.description}\n\n"
        
        buttons.data_button("Back", f"plugins {user_id} main", position="footer")
        buttons.data_button("Close", f"plugins {user_id} close", position="footer")
        btns = buttons.build_menu(1)
        
    elif stype.startswith("plugin_"):
        plugin_name = stype.split("_", 1)[1]
        plugin_info = plugin_manager.get_plugin_info(plugin_name)
        
        if plugin_info:
            status = "✅ Enabled" if plugin_info.enabled else "❌ Disabled"
            source_info = f"Source: {plugin_info.source_type.title()}"
            
            buttons.data_button(
                "Disable" if plugin_info.enabled else "Enable",
                f"plugins {user_id} toggle {plugin_name}"
            )
            buttons.data_button("Unload", f"plugins {user_id} unload {plugin_name}")
            buttons.data_button("Reload", f"plugins {user_id} reload {plugin_name}")
            
            if plugin_info.source_type == "github":
                buttons.data_button("Update", f"plugins {user_id} update {plugin_name}")
                buttons.data_button("Uninstall", f"plugins {user_id} uninstall {plugin_name}")
            
            buttons.data_button("Back", f"plugins {user_id} loaded", position="footer")
            buttons.data_button("Close", f"plugins {user_id} close", position="footer")
            
            text = f"""⌬ <b>Plugin: {plugin_name}</b>
│
┟ <b>Version:</b> {plugin_info.version}
┠ <b>Author:</b> {plugin_info.author}
┠ <b>Status:</b> {status}
┠ <b>{source_info}</b>
┠ <b>Commands:</b> {', '.join(plugin_info.commands) if plugin_info.commands else 'None'}"""
            
            if plugin_info.manifest:
                text += f"\n┠ <b>Dependencies:</b> {', '.join(plugin_info.manifest.python_dependencies) if plugin_info.manifest.python_dependencies else 'None'}"
                if plugin_info.source_url:
                    text += f"\n┠ <b>Repository:</b> {plugin_info.source_url}"
            
            text += f"\n┖ <b>Description:</b> {plugin_info.description}"
            
            btns = buttons.build_menu(2)
        else:
            text = f"❌ Plugin {plugin_name} not found"
            buttons.data_button("Back", f"plugins {user_id} loaded", position="footer")
            btns = buttons.build_menu(1)
    
    return text, btns


@new_task
async def plugins_command(client: Client, message: Message):
    try:
        plugin_manager = get_plugin_manager()
        plugin_manager.bot = client
        
        text, buttons = await get_plugins_menu(message.from_user.id)
        await send_message(message, text, buttons)
        
    except Exception as e:
        LOGGER.error(f"Error in plugins_command: {e}", exc_info=True)
        await message.reply_text("Error loading plugin menu")


@new_task
async def edit_plugins_menu(client: Client, query):
    try:
        user_id = query.from_user.id
        data = query.data.split()
        
        if user_id != int(data[1]):
            return await query.answer("Not yours!", show_alert=True)
        
        if data[2] == "main":
            await query.answer()
            text, buttons = await get_plugins_menu(user_id, "main")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "loaded":
            await query.answer()
            text, buttons = await get_plugins_menu(user_id, "loaded")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "available":
            await query.answer()
            text, buttons = await get_plugins_menu(user_id, "available")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "github":
            await query.answer()
            text, buttons = await get_plugins_menu(user_id, "github")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "updates":
            await query.answer()
            text, buttons = await get_plugins_menu(user_id, "updates")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "info":
            await query.answer()
            text, buttons = await get_plugins_menu(user_id, "info")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "plugin":
            await query.answer()
            plugin_name = data[3]
            text, buttons = await get_plugins_menu(user_id, f"plugin_{plugin_name}")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "load":
            await query.answer("Loading plugin...", show_alert=True)
            plugin_name = data[3]
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            success = await plugin_manager.load_plugin(plugin_name)
            if success:
                await query.answer(f"Plugin {plugin_name} loaded successfully!", show_alert=True)
            else:
                await query.answer(f"Failed to load plugin {plugin_name}", show_alert=True)
            
            text, buttons = await get_plugins_menu(user_id, "available")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "unload":
            await query.answer("Unloading plugin...", show_alert=True)
            plugin_name = data[3]
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            success = await plugin_manager.unload_plugin(plugin_name)
            if success:
                await query.answer(f"Plugin {plugin_name} unloaded successfully!", show_alert=True)
            else:
                await query.answer(f"Failed to unload plugin {plugin_name}", show_alert=True)
            
            text, buttons = await get_plugins_menu(user_id, "loaded")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "reload":
            await query.answer("Reloading plugin...", show_alert=True)
            plugin_name = data[3]
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            success = await plugin_manager.reload_plugin(plugin_name)
            if success:
                await query.answer(f"Plugin {plugin_name} reloaded successfully!", show_alert=True)
            else:
                await query.answer(f"Failed to reload plugin {plugin_name}", show_alert=True)
            
            text, buttons = await get_plugins_menu(user_id, f"plugin_{plugin_name}")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "update":
            await query.answer("Updating plugin...", show_alert=True)
            plugin_name = data[3]
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            success = await plugin_manager.update_plugin(plugin_name)
            if success:
                await query.answer(f"Plugin {plugin_name} updated successfully!", show_alert=True)
            else:
                await query.answer(f"Failed to update plugin {plugin_name}", show_alert=True)
            
            text, buttons = await get_plugins_menu(user_id, f"plugin_{plugin_name}")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "uninstall":
            await query.answer("Uninstalling plugin...", show_alert=True)
            plugin_name = data[3]
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            success = await plugin_manager.uninstall_plugin(plugin_name)
            if success:
                await query.answer(f"Plugin {plugin_name} uninstalled successfully!", show_alert=True)
                text, buttons = await get_plugins_menu(user_id, "available")
                await edit_message(query.message, text, buttons)
            else:
                await query.answer(f"Failed to uninstall plugin {plugin_name}", show_alert=True)
            
        elif data[2] == "toggle":
            await query.answer("Toggling plugin...", show_alert=True)
            plugin_name = data[3]
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            plugin_info = plugin_manager.get_plugin_info(plugin_name)
            if plugin_info:
                if plugin_info.enabled:
                    success = await plugin_manager.disable_plugin(plugin_name)
                    action = "disabled"
                else:
                    success = await plugin_manager.enable_plugin(plugin_name)
                    action = "enabled"
                
                if success:
                    await query.answer(f"Plugin {plugin_name} {action} successfully!", show_alert=True)
                else:
                    await query.answer(f"Failed to {action} plugin {plugin_name}", show_alert=True)
            
            text, buttons = await get_plugins_menu(user_id, f"plugin_{plugin_name}")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "check_updates":
            await query.answer("Checking for updates...", show_alert=True)
            plugin_manager = get_plugin_manager()
            plugin_manager.bot = client
            
            updates = await plugin_manager.check_for_updates()
            if updates:
                await query.answer(f"Found {len(updates)} updates available!", show_alert=True)
            else:
                await query.answer("All plugins are up to date!", show_alert=True)
            
            text, buttons = await get_plugins_menu(user_id, "updates")
            await edit_message(query.message, text, buttons)
            
        elif data[2] == "close":
            await delete_message(query.message)
            
    except Exception as e:
        LOGGER.error(f"Error in edit_plugins_menu: {e}", exc_info=True)
        await query.answer("Error occurred", show_alert=True)


@new_task
async def handle_github_install(client: Client, message: Message):
    try:
        if not message.reply_to_message or not message.reply_to_message.text:
            return
        
        # Check if this is a response to GitHub install prompt
        if "Install from GitHub" not in message.reply_to_message.text:
            return
        
        repo_url = message.text.strip()
        plugin_manager = get_plugin_manager()
        plugin_manager.bot = client
        
        status_msg = await send_message(message, "🔄 Installing plugin from GitHub...")
        
        success = await plugin_manager.install_from_github(repo_url)
        
        if success:
            await edit_message(status_msg, "✅ Plugin installed successfully from GitHub!")
        else:
            await edit_message(status_msg, "❌ Failed to install plugin from GitHub. Check logs for details.")
            
    except Exception as e:
        LOGGER.error(f"Error handling GitHub install: {e}", exc_info=True)
        await message.reply_text("Error installing plugin from GitHub")


def register_plugin_commands():
    from ..core.handlers import TgClient
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
            edit_plugins_menu,
            filters=regex("^plugins")
        )
    )
    # Add handler for GitHub URL messages
    TgClient.bot.add_handler(
        MessageHandler(
            handle_github_install,
            filters=~command("") & CustomFilters.sudo
        )
    )