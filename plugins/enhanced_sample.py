from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
from bot.core.plugin_manager import PluginBase, PluginInfo, PluginManifest
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.message_utils import send_message, edit_message
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER


class EnhancedSamplePlugin(PluginBase):
    
    PLUGIN_INFO = PluginInfo(
        name="enhanced_sample",
        version="2.0.0",
        author="WZML-X Team",
        description="Enhanced sample plugin showcasing new plugin system features",
        enabled=True,
        handlers=[],
        commands=["esample", "econfig", "estatus"],
        dependencies=["aiohttp"]
    )
    
    PLUGIN_MANIFEST = PluginManifest(
        name="enhanced_sample",
        version="2.0.0",
        author="WZML-X Team",
        description="Enhanced sample plugin showcasing new plugin system features",
        min_wzml_version="3.0.0",
        repository="https://github.com/wzml-x/enhanced-sample-plugin",
        license="MIT",
        tags=["sample", "demo", "enhanced"],
        icon="⚡",
        enabled=True,
        auto_load=True,
        priority=1,
        python_dependencies=["aiohttp>=3.8.0"],
        main_file="enhanced_sample.py",
        commands=[
            {
                "name": "esample",
                "handler": "sample_command",
                "description": "Enhanced sample command",
                "usage": "/esample [text]",
                "sudo_only": False,
                "authorized_only": True
            },
            {
                "name": "econfig",
                "handler": "config_command",
                "description": "Plugin configuration",
                "usage": "/econfig",
                "sudo_only": True,
                "authorized_only": True
            },
            {
                "name": "estatus",
                "handler": "status_command",
                "description": "Plugin status",
                "usage": "/estatus",
                "sudo_only": False,
                "authorized_only": True
            }
        ],
        callbacks=[
            {
                "pattern": "^esample_",
                "handler": "sample_callback"
            }
        ]
    )

    def __init__(self):
        super().__init__()
        self.call_count = 0
        self.last_used = None

    async def on_load(self) -> bool:
        """Called when plugin is loaded"""
        LOGGER.info("Enhanced Sample Plugin: Loading...")
        
        # Initialize plugin configuration
        default_config = {
            "max_usage": 100,
            "enable_stats": True,
            "welcome_message": "Welcome to Enhanced Sample Plugin!"
        }
        
        for key, value in default_config.items():
            if self.get_config(key) is None:
                self.set_config(key, value)
        
        LOGGER.info("Enhanced Sample Plugin: Loaded successfully")
        return True

    async def on_unload(self) -> bool:
        """Called when plugin is unloaded"""
        LOGGER.info("Enhanced Sample Plugin: Unloading...")
        return True

    async def on_enable(self) -> bool:
        """Called when plugin is enabled"""
        LOGGER.info("Enhanced Sample Plugin: Enabled")
        return True

    async def on_disable(self) -> bool:
        """Called when plugin is disabled"""
        LOGGER.info("Enhanced Sample Plugin: Disabled")
        return True

    async def on_install(self) -> bool:
        """Called when plugin is first installed"""
        LOGGER.info("Enhanced Sample Plugin: First installation")
        return True

    async def on_update(self, old_version: str, new_version: str) -> bool:
        """Called when plugin is updated"""
        LOGGER.info(f"Enhanced Sample Plugin: Updated from {old_version} to {new_version}")
        return True

    async def on_configure(self, config: dict) -> bool:
        """Called when plugin configuration is updated"""
        LOGGER.info("Enhanced Sample Plugin: Configuration updated")
        return True

    async def validate_dependencies(self) -> bool:
        """Validate plugin dependencies"""
        try:
            import aiohttp
            return True
        except ImportError:
            LOGGER.error("Enhanced Sample Plugin: aiohttp dependency not found")
            return False

    async def check_permissions(self, user_id: int, chat_id: int) -> bool:
        """Check if user/chat has permission to use plugin"""
        # Add custom permission logic here
        return True


# Command handlers
@new_task
async def sample_command(client: Client, message: Message):
    """Enhanced sample command handler"""
    try:
        plugin_manager = None
        plugin_instance = None
        
        # Get plugin instance
        from bot.core.plugin_manager import get_plugin_manager
        plugin_manager = get_plugin_manager()
        if "enhanced_sample" in plugin_manager.loaded_modules:
            plugin_instance = plugin_manager.loaded_modules["enhanced_sample"]
            plugin_instance.call_count += 1
            plugin_instance.last_used = message.date
        
        # Get command arguments
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        text = " ".join(args) if args else "Hello from Enhanced Sample Plugin!"
        
        # Create interactive buttons
        buttons = ButtonMaker()
        buttons.data_button("📊 Stats", f"esample_stats_{message.from_user.id}")
        buttons.data_button("⚙️ Config", f"esample_config_{message.from_user.id}")
        buttons.data_button("🔄 Reload", f"esample_reload_{message.from_user.id}")
        buttons.data_button("❌ Close", f"esample_close_{message.from_user.id}")
        
        response = f"""⚡ <b>Enhanced Sample Plugin</b>

📝 <b>Your text:</b> {text}
🎯 <b>User:</b> {message.from_user.first_name}
🆔 <b>User ID:</b> {message.from_user.id}
💬 <b>Chat:</b> {message.chat.title or 'Private'}
🕐 <b>Time:</b> {message.date.strftime('%Y-%m-%d %H:%M:%S')}"""

        if plugin_instance:
            response += f"\n📈 <b>Usage Count:</b> {plugin_instance.call_count}"
            max_usage = plugin_instance.get_config("max_usage", 100)
            response += f"\n🎯 <b>Max Usage:</b> {max_usage}"
        
        await send_message(message, response, buttons.build_menu(2))
        
    except Exception as e:
        LOGGER.error(f"Error in sample_command: {e}", exc_info=True)
        await message.reply_text("❌ Error occurred in sample command")


@new_task
async def config_command(client: Client, message: Message):
    """Plugin configuration command"""
    try:
        from bot.core.plugin_manager import get_plugin_manager
        plugin_manager = get_plugin_manager()
        
        if "enhanced_sample" not in plugin_manager.loaded_modules:
            await message.reply_text("❌ Plugin not loaded")
            return
        
        plugin_instance = plugin_manager.loaded_modules["enhanced_sample"]
        
        config = {
            "max_usage": plugin_instance.get_config("max_usage", 100),
            "enable_stats": plugin_instance.get_config("enable_stats", True),
            "welcome_message": plugin_instance.get_config("welcome_message", "Welcome!")
        }
        
        config_text = "⚙️ <b>Enhanced Sample Plugin Configuration</b>\n\n"
        for key, value in config.items():
            config_text += f"🔹 <b>{key}:</b> {value}\n"
        
        await send_message(message, config_text)
        
    except Exception as e:
        LOGGER.error(f"Error in config_command: {e}", exc_info=True)
        await message.reply_text("❌ Error occurred in config command")


@new_task
async def status_command(client: Client, message: Message):
    """Plugin status command"""
    try:
        from bot.core.plugin_manager import get_plugin_manager
        plugin_manager = get_plugin_manager()
        
        if "enhanced_sample" not in plugin_manager.loaded_modules:
            await message.reply_text("❌ Plugin not loaded")
            return
        
        plugin_instance = plugin_manager.loaded_modules["enhanced_sample"]
        plugin_info = plugin_manager.get_plugin_info("enhanced_sample")
        
        status_text = f"""📊 <b>Enhanced Sample Plugin Status</b>

🔹 <b>Name:</b> {plugin_info.name}
🔹 <b>Version:</b> {plugin_info.version}
🔹 <b>Author:</b> {plugin_info.author}
🔹 <b>Status:</b> {'✅ Enabled' if plugin_info.enabled else '❌ Disabled'}
🔹 <b>Source:</b> {plugin_info.source_type.title()}
🔹 <b>Commands:</b> {', '.join(plugin_info.commands)}
🔹 <b>Usage Count:</b> {plugin_instance.call_count}
🔹 <b>Last Used:</b> {plugin_instance.last_used.strftime('%Y-%m-%d %H:%M:%S') if plugin_instance.last_used else 'Never'}

📋 <b>Description:</b> {plugin_info.description}"""
        
        await send_message(message, status_text)
        
    except Exception as e:
        LOGGER.error(f"Error in status_command: {e}", exc_info=True)
        await message.reply_text("❌ Error occurred in status command")


@new_task
async def sample_callback(client: Client, query: CallbackQuery):
    """Handle sample plugin callbacks"""
    try:
        data = query.data.split("_")
        action = data[1]
        user_id = int(data[2]) if len(data) > 2 else 0
        
        if query.from_user.id != user_id and user_id != 0:
            await query.answer("❌ Not your button!", show_alert=True)
            return
        
        from bot.core.plugin_manager import get_plugin_manager
        plugin_manager = get_plugin_manager()
        
        if action == "stats":
            if "enhanced_sample" in plugin_manager.loaded_modules:
                plugin_instance = plugin_manager.loaded_modules["enhanced_sample"]
                stats_text = f"""📊 <b>Plugin Statistics</b>

🎯 <b>Total Usage:</b> {plugin_instance.call_count}
🕐 <b>Last Used:</b> {plugin_instance.last_used.strftime('%Y-%m-%d %H:%M:%S') if plugin_instance.last_used else 'Never'}
⚙️ <b>Max Usage:</b> {plugin_instance.get_config('max_usage', 100)}
📈 <b>Stats Enabled:</b> {plugin_instance.get_config('enable_stats', True)}"""
                
                await query.answer()
                await edit_message(query.message, stats_text)
            else:
                await query.answer("❌ Plugin not loaded", show_alert=True)
                
        elif action == "config":
            await query.answer("⚙️ Configuration menu coming soon!", show_alert=True)
            
        elif action == "reload":
            await query.answer("🔄 Reloading plugin...", show_alert=True)
            success = await plugin_manager.reload_plugin("enhanced_sample")
            if success:
                await query.answer("✅ Plugin reloaded successfully!", show_alert=True)
            else:
                await query.answer("❌ Failed to reload plugin", show_alert=True)
                
        elif action == "close":
            await query.message.delete()
            
    except Exception as e:
        LOGGER.error(f"Error in sample_callback: {e}", exc_info=True)
        await query.answer("❌ Error occurred", show_alert=True)


# Plugin instance (required for the plugin system)
plugin_instance = EnhancedSamplePlugin()
