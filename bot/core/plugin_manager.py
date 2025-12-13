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
from ..helper.ext_utils.db_handler import database


@dataclass
class PluginManifest:
    name: str
    version: str
    author: str
    description: str
    min_wzml_version: str = "3.0.0"
    max_wzml_version: str = "99.0.0"
    repository: str = ""
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    enabled: bool = True
    auto_load: bool = True
    priority: int = 1
    python_dependencies: List[str] = field(default_factory=list)
    wzml_dependencies: List[str] = field(default_factory=list)
    main_file: str = "main.py"
    commands: List[Dict[str, Any]] = field(default_factory=list)
    callbacks: List[Dict[str, Any]] = field(default_factory=list)
    settings_schema: Optional[Dict[str, Any]] = None
    permissions: List[str] = field(default_factory=list)
    icon: str = ""
    screenshots: List[str] = field(default_factory=list)
    enabled: bool = True
    auto_load: bool = True
    priority: int = 0
    python_dependencies: List[str] = field(default_factory=list)
    wzml_dependencies: List[str] = field(default_factory=list)
    system_dependencies: List[str] = field(default_factory=list)
    main_file: str = "plugin.py"
    config_file: str = ""
    data_files: List[str] = field(default_factory=list)
    commands: List[Dict[str, Any]] = field(default_factory=list)
    handlers: List[Dict[str, Any]] = field(default_factory=list)
    callbacks: List[Dict[str, Any]] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    restricted_users: List[str] = field(default_factory=list)
    allowed_chats: List[str] = field(default_factory=list)


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
    manifest: Optional[PluginManifest] = None
    source_type: str = "local"
    source_url: str = ""
    install_path: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


class PluginBase:
    PLUGIN_INFO: PluginInfo
    PLUGIN_MANIFEST: Optional[PluginManifest] = None

    async def on_load(self) -> bool:
        return True

    async def on_unload(self) -> bool:
        return True

    async def on_enable(self) -> bool:
        return True

    async def on_disable(self) -> bool:
        return True

    async def on_install(self) -> bool:
        return True

    async def on_update(self, old_version: str, new_version: str) -> bool:
        return True

    async def on_configure(self, config: Dict[str, Any]) -> bool:
        return True

    def register_command(self, cmd: str, handler_func, filters=None):
        if filters is None:
            filters = CustomFilters.authorized
        return MessageHandler(handler_func, filters=cmd & filters)

    def register_callback(self, pattern: str, callback_func, filters=None):
        if filters is None:
            filters = CustomFilters.authorized
        return CallbackQueryHandler(callback_func, filters=pattern & filters)

    def get_config(self, key: str, default=None):
        if hasattr(self, 'PLUGIN_INFO') and self.PLUGIN_INFO.config:
            return self.PLUGIN_INFO.config.get(key, default)
        return default

    def set_config(self, key: str, value: Any):
        if hasattr(self, 'PLUGIN_INFO'):
            if not self.PLUGIN_INFO.config:
                self.PLUGIN_INFO.config = {}
            self.PLUGIN_INFO.config[key] = value

    async def validate_dependencies(self) -> bool:
        return True

    async def check_permissions(self, user_id: int, chat_id: int) -> bool:
        return True


class GitHubPluginLoader:
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.github_cache_dir = plugins_dir / ".github_cache"
        self.github_cache_dir.mkdir(exist_ok=True)

    async def download_plugin(self, repo_url: str, branch: str = "main") -> Optional[Path]:
        try:
            import aiohttp
            import zipfile
            import tempfile
            import shutil
            
            if not repo_url.startswith("https://github.com/"):
                repo_url = f"https://github.com/{repo_url}"
            
            parts = repo_url.replace("https://github.com/", "").split("/")
            if len(parts) < 2:
                LOGGER.error(f"Invalid GitHub repository URL: {repo_url}")
                return None
            
            owner, repo = parts[0], parts[1]
            download_url = f"https://github.com/{owner}/{repo}/archive/{branch}.zip"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status != 200:
                        LOGGER.error(f"Failed to download repository: {response.status}")
                        return None
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
                        temp_file.write(await response.read())
                        temp_path = Path(temp_file.name)
            
            extract_dir = self.github_cache_dir / f"{owner}-{repo}-{branch}"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(self.github_cache_dir)
            
            extracted_name = f"{repo}-{branch}"
            extracted_path = self.github_cache_dir / extracted_name
            
            if not extracted_path.exists():
                LOGGER.error(f"Extracted directory not found: {extracted_path}")
                return None
            
            temp_path.unlink()
            return extracted_path
            
        except Exception as e:
            LOGGER.error(f"Error downloading plugin from GitHub: {e}", exc_info=True)
            return None

    async def parse_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        try:
            import yaml
            
            manifest_file = plugin_dir / "wzml_plugin.yml"
            if not manifest_file.exists():
                for alt_name in ["wzml_plugin.yaml", "plugin.yml", "plugin.yaml"]:
                    alt_file = plugin_dir / alt_name
                    if alt_file.exists():
                        manifest_file = alt_file
                        break
                else:
                    LOGGER.warning(f"No manifest file found in {plugin_dir}")
                    return None
            
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return PluginManifest(**data)
            
        except Exception as e:
            LOGGER.error(f"Error parsing manifest file: {e}", exc_info=True)
            return None

    async def install_plugin(self, plugin_dir: Path, manifest: PluginManifest) -> bool:
        try:
            import shutil
            
            install_dir = self.plugins_dir / manifest.name
            if install_dir.exists():
                shutil.rmtree(install_dir)
            
            install_dir.mkdir(exist_ok=True)
            
            main_file = plugin_dir / manifest.main_file
            if not main_file.exists():
                LOGGER.error(f"Main plugin file not found: {manifest.main_file}")
                return False
            
            shutil.copy2(main_file, install_dir / f"{manifest.name}.py")
            
            manifest_file = plugin_dir / "wzml_plugin.yml"
            if manifest_file.exists():
                shutil.copy2(manifest_file, install_dir / "wzml_plugin.yml")
            
            for data_file in manifest.data_files:
                src_file = plugin_dir / data_file
                if src_file.exists():
                    if src_file.is_file():
                        shutil.copy2(src_file, install_dir / data_file)
                    else:
                        shutil.copytree(src_file, install_dir / data_file, dirs_exist_ok=True)
            
            if manifest.config_file:
                config_file = plugin_dir / manifest.config_file
                if config_file.exists():
                    shutil.copy2(config_file, install_dir / manifest.config_file)
            
            LOGGER.info(f"Plugin {manifest.name} installed successfully")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error installing plugin: {e}", exc_info=True)
            return False


class PluginManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.plugins: Dict[str, PluginInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.plugins_dir = Path("plugins")
        self.plugins_dir.mkdir(exist_ok=True)
        self.github_loader = GitHubPluginLoader(self.plugins_dir)
        self.registry: Dict[str, Dict[str, Any]] = {}

    async def _load_registry(self):
        self.registry = await database.load_plugin_registry()

    async def _save_registry(self):
        await database.save_plugin_registry(self.registry)

    def discover_plugins(self) -> List[str]:
        plugin_files = []
        for file in self.plugins_dir.glob("*.py"):
            if not file.name.startswith("__"):
                plugin_files.append(file.stem)
        
        for subdir in self.plugins_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                if (subdir / "wzml_plugin.yml").exists() or (subdir / f"{subdir.name}.py").exists():
                    plugin_files.append(subdir.name)
        
        return list(set(plugin_files))

    async def install_from_github(self, repo_url: str, branch: str = "main") -> bool:
        try:
            plugin_dir = await self.github_loader.download_plugin(repo_url, branch)
            if not plugin_dir:
                return False
            
            manifest = await self.github_loader.parse_manifest(plugin_dir)
            if not manifest:
                LOGGER.error("Plugin manifest not found or invalid")
                return False
            
            if not await self._validate_dependencies(manifest):
                LOGGER.error("Plugin dependencies validation failed")
                return False
            
            if not await self.github_loader.install_plugin(plugin_dir, manifest):
                return False
            
            self.registry[manifest.name] = {
                "source_type": "github",
                "source_url": repo_url,
                "branch": branch,
                "version": manifest.version,
                "installed_at": str(Path.cwd()),
                "manifest": manifest.__dict__
            }
            self._save_registry()
            LOGGER.info(f"Successfully installed plugin {manifest.name} from GitHub")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error installing plugin from GitHub: {e}", exc_info=True)
            return False

    async def update_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name not in self.registry:
                LOGGER.error(f"Plugin {plugin_name} not found in registry")
                return False
            
            registry_entry = self.registry[plugin_name]
            if registry_entry["source_type"] != "github":
                LOGGER.error(f"Plugin {plugin_name} is not from GitHub, cannot update")
                return False
            
            old_version = registry_entry["version"]
            was_loaded = plugin_name in self.loaded_modules
            if was_loaded:
                await self.unload_plugin(plugin_name)
            
            plugin_dir = await self.github_loader.download_plugin(
                registry_entry["source_url"], registry_entry["branch"])
            if not plugin_dir:
                return False
            
            manifest = await self.github_loader.parse_manifest(plugin_dir)
            if not manifest or not await self.github_loader.install_plugin(plugin_dir, manifest):
                return False
            
            self.registry[plugin_name]["version"] = manifest.version
            self.registry[plugin_name]["manifest"] = manifest.__dict__
            self._save_registry()
            
            if was_loaded:
                await self.load_plugin(plugin_name)
                if plugin_name in self.loaded_modules:
                    await self.loaded_modules[plugin_name].on_update(old_version, manifest.version)
            
            LOGGER.info(f"Successfully updated plugin {plugin_name} from {old_version} to {manifest.version}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error updating plugin {plugin_name}: {e}", exc_info=True)
            return False

    async def _validate_dependencies(self, manifest: PluginManifest) -> bool:
        try:
            for dep in manifest.python_dependencies:
                try:
                    __import__(dep.split("==")[0].split(">=")[0].split("<=")[0])
                except ImportError:
                    LOGGER.warning(f"Python dependency not found: {dep}")
                    return False
            return True
        except Exception as e:
            LOGGER.error(f"Error validating dependencies: {e}", exc_info=True)
            return False

    def _refresh_commands(self):
        try:
            from ..helper.telegram_helper.bot_commands import BotCommands
            from ..helper.ext_utils.help_messages import get_bot_commands, get_help_string
            import importlib
            
            BotCommands.refresh_commands()
            importlib.reload(sys.modules['bot.helper.ext_utils.help_messages'])
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

            plugin_path = None
            manifest = None
            plugin_dir = self.plugins_dir / plugin_name
            
            if plugin_dir.is_dir():
                manifest_file = plugin_dir / "wzml_plugin.yml"
                if manifest_file.exists():
                    manifest = await self.github_loader.parse_manifest(plugin_dir)
                    plugin_path = plugin_dir / f"{plugin_name}.py"
                    if not plugin_path.exists() and manifest:
                        plugin_path = plugin_dir / manifest.main_file
                else:
                    plugin_path = plugin_dir / f"{plugin_name}.py"
            else:
                plugin_path = self.plugins_dir / f"{plugin_name}.py"
            
            if not plugin_path or not plugin_path.exists():
                LOGGER.error(f"Plugin file {plugin_name} not found")
                return False

            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)

            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, PluginBase) and attr != PluginBase):
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
            plugin_info.manifest = manifest
            plugin_info.source_type = self.registry.get(plugin_name, {}).get("source_type", "local")
            plugin_info.source_url = self.registry.get(plugin_name, {}).get("source_url", "")
            plugin_info.install_path = str(plugin_path.parent)

            if manifest and not await self._validate_dependencies(manifest):
                LOGGER.error(f"Plugin {plugin_name} dependencies validation failed")
                return False

            if not await plugin_instance.on_load():
                LOGGER.error(f"Plugin {plugin_name} failed to load")
                return False

            self.plugins[plugin_name] = plugin_info
            self.loaded_modules[plugin_name] = plugin_instance
            await self._register_handlers(plugin_instance, plugin_info)
            self._refresh_commands()
            LOGGER.info(f"Plugin {plugin_name} loaded successfully")
            return True

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
                await self._unregister_handlers(plugin_info)
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

    async def uninstall_plugin(self, plugin_name: str) -> bool:
        try:
            if plugin_name in self.loaded_modules:
                await self.unload_plugin(plugin_name)
            
            plugin_dir = self.plugins_dir / plugin_name
            plugin_file = self.plugins_dir / f"{plugin_name}.py"
            
            import shutil
            if plugin_dir.exists() and plugin_dir.is_dir():
                shutil.rmtree(plugin_dir)
            elif plugin_file.exists():
                plugin_file.unlink()
            else:
                LOGGER.warning(f"Plugin {plugin_name} files not found for removal")
            
            if plugin_name in self.registry:
                del self.registry[plugin_name]
                self._save_registry()
            
            LOGGER.info(f"Plugin {plugin_name} uninstalled successfully")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error uninstalling plugin {plugin_name}: {e}", exc_info=True)
            return False

    def list_plugins(self) -> List[PluginInfo]:
        return list(self.plugins.values())

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        return self.plugins.get(plugin_name)

    def list_available_plugins(self) -> List[str]:
        return self.discover_plugins()

    def get_plugin_registry(self) -> Dict[str, Dict[str, Any]]:
        return self.registry.copy()

    async def _register_handlers(self, plugin_instance: PluginBase, plugin_info: PluginInfo):
        try:
            from ..helper.telegram_helper.filters import CustomFilters
            from pyrogram.filters import command as pyrogram_command, regex
            from pyrogram.handlers import MessageHandler
            
            for handler in plugin_info.handlers:
                self.bot.add_handler(handler)
            
            if plugin_info.manifest:
                manifest = plugin_info.manifest
                
                for cmd_info in manifest.commands:
                    cmd_name = cmd_info.get("name")
                    if not cmd_name:
                        continue
                    
                    module = sys.modules.get(plugin_info.name)
                    if not module:
                        continue
                    
                    handler_name = cmd_info.get("handler", f"{cmd_name}_command")
                    if hasattr(module, handler_name):
                        handler_func = getattr(module, handler_name)
                        filters = pyrogram_command(cmd_name, case_sensitive=True)
                        
                        if cmd_info.get("sudo_only", False):
                            filters = filters & CustomFilters.sudo
                        elif cmd_info.get("authorized_only", True):
                            filters = filters & CustomFilters.authorized
                        
                        handler = MessageHandler(handler_func, filters=filters)
                        plugin_info.handlers.append(handler)
                        self.bot.add_handler(handler)
                        LOGGER.info(f"Registered command /{cmd_name} for plugin {plugin_info.name}")
                        
                        if cmd_name not in plugin_info.commands:
                            plugin_info.commands.append(cmd_name)
                
                for callback_info in manifest.callbacks:
                    pattern = callback_info.get("pattern")
                    if not pattern:
                        continue
                    
                    module = sys.modules.get(plugin_info.name)
                    if not module:
                        continue
                    
                    handler_name = callback_info.get("handler")
                    if handler_name and hasattr(module, handler_name):
                        handler_func = getattr(module, handler_name)
                        callback_handler = CallbackQueryHandler(handler_func, filters=regex(pattern))
                        plugin_info.handlers.append(callback_handler)
                        self.bot.add_handler(callback_handler)
                        LOGGER.info(f"Registered callback {pattern} for plugin {plugin_info.name}")
            
            module = sys.modules.get(plugin_info.name)
            if module:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and attr_name.endswith('_command'):
                        cmd_name = attr_name.replace('_command', '')
                        if cmd_name in plugin_info.commands:
                            handler = MessageHandler(
                                attr, filters=pyrogram_command(cmd_name, case_sensitive=True) & CustomFilters.authorized)
                            plugin_info.handlers.append(handler)
                            self.bot.add_handler(handler)
                            LOGGER.info(f"Registered legacy command /{cmd_name} for plugin {plugin_info.name}")
                            
        except Exception as e:
            LOGGER.error(f"Error registering handlers for plugin {plugin_info.name}: {e}", exc_info=True)

    async def _unregister_handlers(self, plugin_info: PluginInfo):
        for handler in plugin_info.handlers:
            try:
                self.bot.remove_handler(handler)
            except Exception as e:
                LOGGER.warning(f"Error removing handler: {e}")
        plugin_info.handlers.clear()

    async def auto_load_plugins(self):
        try:
            available_plugins = self.discover_plugins()
            for plugin_name in available_plugins:
                if plugin_name in self.registry:
                    registry_entry = self.registry[plugin_name]
                    manifest_data = registry_entry.get("manifest", {})
                    if not manifest_data.get("auto_load", True):
                        continue
                await self.load_plugin(plugin_name)
        except Exception as e:
            LOGGER.error(f"Error during auto-load: {e}", exc_info=True)

    async def check_for_updates(self) -> Dict[str, str]:
        updates_available = {}
        try:
            for plugin_name, registry_entry in self.registry.items():
                if registry_entry.get("source_type") == "github":
                    updates_available[plugin_name] = "Update available"
        except Exception as e:
            LOGGER.error(f"Error checking for updates: {e}")
        return updates_available


# Global plugin manager instance
plugin_manager = PluginManager(None)

def get_plugin_manager() -> PluginManager:
    return plugin_manager
    