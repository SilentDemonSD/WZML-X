import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyrogram import Client
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from .. import LOGGER
from ..helper.telegram_helper.filters import CustomFilters


@dataclass
class PluginInfo:
    name: str
    version: str
    author: str
    description: str
    enabled: bool = True
    handlers: List[Any] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class PluginBase:
    PLUGIN_INFO: PluginInfo

    async def on_load(self) -> bool:
        return True

    async def on_unload(self) -> bool:
        return True

    async def on_enable(self) -> bool:
        return True

    async def on_disable(self) -> bool:
        return True

    def register_command(self, command: str, handler_func, filters=None):
        if filters is None:
            filters = CustomFilters.authorized
        return MessageHandler(handler_func, filters=command & filters)

    def register_callback(self, pattern: str, callback_func, filters=None):
        if filters is None:
            filters = CustomFilters.authorized
        return CallbackQueryHandler(callback_func, filters=pattern & filters)


class PluginManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.plugins: Dict[str, PluginInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.plugins_dir = Path("plugins")
        self.plugins_dir.mkdir(exist_ok=True)

    def discover_plugins(self) -> List[str]:
        plugin_files = []
        for file in self.plugins_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue
            plugin_files.append(file.stem)
        return plugin_files

    def _refresh_commands(self):
        try:
            from ..helper.telegram_helper.bot_commands import BotCommands
            from ..helper.ext_utils.help_messages import get_bot_commands, get_help_string
            import importlib
            
            BotCommands.refresh_commands()
            
            importlib.reload(sys.modules['bot.helper.ext_utils.help_messages'])
            from ..helper.ext_utils.help_messages import BOT_COMMANDS, help_string
            globals()['BOT_COMMANDS'] = get_bot_commands()
            globals()['help_string'] = get_help_string()
            
            LOGGER.info("Bot commands and help refreshed")
        except Exception as e:
            LOGGER.error(f"Error refreshing commands: {e}", exc_info=True)

    async def load_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name in self.loaded_modules:
                LOGGER.warning(f"Plugin {plugin_name} already loaded")
                return False

            plugin_path = self.plugins_dir / f"{plugin_name}.py"
            if not plugin_path.exists():
                LOGGER.error(f"Plugin file {plugin_name}.py not found")
                return False

            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)

            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase):
                    plugin_class = attr
                    break

            if not plugin_class:
                LOGGER.error(f"No valid plugin class found in {plugin_name}")
                return False

            plugin_instance = plugin_class()
            if not hasattr(plugin_instance, 'PLUGIN_INFO'):
                LOGGER.error(f"Plugin {plugin_name} missing PLUGIN_INFO")
                return False

            plugin_info = plugin_instance.PLUGIN_INFO
            if await plugin_instance.on_load():
                self.plugins[plugin_name] = plugin_info
                self.loaded_modules[plugin_name] = plugin_instance
                self._register_handlers(plugin_instance, plugin_info)
                self._refresh_commands()
                LOGGER.info(f"Plugin {plugin_name} loaded successfully")
                return True
            else:
                LOGGER.error(f"Plugin {plugin_name} failed to load")
                return False

        except Exception as e:
            LOGGER.error(f"Error loading plugin {plugin_name}: {e}", exc_info=True)
            return False

    async def unload_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name not in self.loaded_modules:
                LOGGER.error(f"Plugin {plugin_name} not loaded")
                return False

            plugin_instance = self.loaded_modules[plugin_name]
            plugin_info = self.plugins[plugin_name]

            if await plugin_instance.on_unload():
                self._unregister_handlers(plugin_info)
                del self.loaded_modules[plugin_name]
                del self.plugins[plugin_name]
                if plugin_name in sys.modules:
                    del sys.modules[plugin_name]
                self._refresh_commands()
                LOGGER.info(f"Plugin {plugin_name} unloaded successfully")
                return True
            else:
                LOGGER.error(f"Plugin {plugin_name} failed to unload")
                return False

        except Exception as e:
            LOGGER.error(f"Error unloading plugin {plugin_name}: {e}", exc_info=True)
            return False

    async def reload_plugin(self, plugin_name: str) -> bool:
        try:
            await self.unload_plugin(plugin_name)
            return await self.load_plugin(plugin_name)
        except Exception as e:
            LOGGER.error(f"Error reloading plugin {plugin_name}: {e}", exc_info=True)
            return False

    async def enable_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name not in self.plugins:
                LOGGER.error(f"Plugin {plugin_name} not found")
                return False

            plugin_instance = self.loaded_modules[plugin_name]
            if await plugin_instance.on_enable():
                self.plugins[plugin_name].enabled = True
                self._refresh_commands()
                LOGGER.info(f"Plugin {plugin_name} enabled")
                return True
            else:
                LOGGER.error(f"Plugin {plugin_name} failed to enable")
                return False

        except Exception as e:
            LOGGER.error(f"Error enabling plugin {plugin_name}: {e}", exc_info=True)
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name not in self.plugins:
                LOGGER.error(f"Plugin {plugin_name} not found")
                return False

            plugin_instance = self.loaded_modules[plugin_name]
            if await plugin_instance.on_disable():
                self.plugins[plugin_name].enabled = False
                self._refresh_commands()
                LOGGER.info(f"Plugin {plugin_name} disabled")
                return True
            else:
                LOGGER.error(f"Plugin {plugin_name} failed to disable")
                return False

        except Exception as e:
            LOGGER.error(f"Error disabling plugin {plugin_name}: {e}", exc_info=True)
            return False

    def list_plugins(self) -> List[PluginInfo]:
        return list(self.plugins.values())

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        return self.plugins.get(plugin_name)

    def _register_handlers(self, plugin_instance: PluginBase, plugin_info: PluginInfo):
        from ..helper.telegram_helper.filters import CustomFilters
        from pyrogram.filters import command
        from pyrogram.handlers import MessageHandler
        
        for handler in plugin_info.handlers:
            self.bot.add_handler(handler)
        
        module = sys.modules.get(plugin_info.name)
        if module:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and attr_name.endswith('_command'):
                    cmd_name = attr_name.replace('_command', '')
                    if cmd_name in plugin_info.commands:
                        handler = MessageHandler(
                            attr,
                            filters=command(cmd_name, case_sensitive=True) & CustomFilters.authorized
                        )
                        plugin_info.handlers.append(handler)
                        self.bot.add_handler(handler)
                        LOGGER.info(f"Registered command /{cmd_name} for plugin {plugin_info.name}")

    def _unregister_handlers(self, plugin_info: PluginInfo):
        for handler in plugin_info.handlers:
            try:
                self.bot.remove_handler(handler)
            except Exception as e:
                LOGGER.warning(f"Error removing handler: {e}")


plugin_manager = PluginManager(None)

def get_plugin_manager() -> PluginManager:
    return plugin_manager