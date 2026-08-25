import importlib
import importlib.metadata
import importlib.util
import sys
from asyncio import Lock
from dataclasses import dataclass, field
from pathlib import Path
from re import match as re_match
from types import ModuleType
from typing import Any, Dict, List, Optional

from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler

from .. import LOGGER
from ..helper.telegram_helper.filters import CustomFilters
from .config_manager import Config

PKG = "wzplugins"
MANIFEST_NAMES = ("wzml_plugin.yml", "wzml_plugin.yaml", "plugin.yml", "plugin.yaml")
NAME_RE = r"^[a-z][a-z0-9_]{1,31}$"
ACCESS = {
    "authorized": "authorized",
    "sudo": "sudo",
    "owner": "owner",
    "authorized_uset": "authorized_uset",
}
KEY_ALIASES = {
    "main_file": "entry",
    "min_wzml_version": "min_bot_version",
    "max_wzml_version": "max_bot_version",
    "settings_schema": "config_schema",
    "deps": "python_dependencies",
}


def _version_tuple(value):
    parts = []
    for chunk in str(value or "").strip().lstrip("vV").split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def dist_name(spec):
    text = str(spec or "").strip()
    for sep in ("[", ";", "=", ">", "<", "!", "~", " "):
        text = text.split(sep, 1)[0]
    return text.strip()


def missing_dependencies(specs):
    missing = []
    for spec in specs or []:
        name = dist_name(spec)
        if not name:
            continue
        try:
            importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(spec)
    return missing


@dataclass
class PluginCommand:
    name: str
    handler: str = ""
    description: str = ""
    usage: str = ""
    aliases: List[str] = field(default_factory=list)
    access: str = "authorized"

    @property
    def names(self):
        seen = []
        for item in [self.name, *self.aliases]:
            item = str(item).strip().lstrip("/")
            if item and item not in seen:
                seen.append(item)
        return seen


@dataclass
class PluginCallback:
    pattern: str
    handler: str = ""
    description: str = ""
    access: str = "authorized"


@dataclass
class PluginManifest:
    name: str
    version: str
    entry: str = ""
    author: str = ""
    description: str = ""
    icon: str = ""
    license: str = ""
    repository: str = ""
    tags: List[str] = field(default_factory=list)
    min_bot_version: str = ""
    max_bot_version: str = ""
    python_dependencies: List[str] = field(default_factory=list)
    commands: List[PluginCommand] = field(default_factory=list)
    callbacks: List[PluginCallback] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("manifest is not a mapping")

        src = {}
        for key, value in data.items():
            src[KEY_ALIASES.get(key, key)] = value

        name = str(src.pop("name", "") or "").strip()
        if not re_match(NAME_RE, name):
            raise ValueError(
                f"invalid plugin name {name!r}, expected lowercase letters, digits and underscores"
            )
        version = str(src.pop("version", "") or "").strip()
        if not version:
            raise ValueError(f"plugin {name} has no version")

        commands = []
        for item in src.pop("commands", None) or []:
            if isinstance(item, str):
                item = {"name": item}
            if not isinstance(item, dict) or not item.get("name"):
                LOGGER.warning(f"Plugin {name}: skipping malformed command entry {item!r}")
                continue
            commands.append(
                PluginCommand(
                    name=str(item["name"]).strip().lstrip("/"),
                    handler=str(item.get("handler") or f"{item['name']}_command"),
                    description=str(item.get("description") or ""),
                    usage=str(item.get("usage") or ""),
                    aliases=[str(a) for a in (item.get("aliases") or [])],
                    access=_access_of(item, name),
                )
            )

        callbacks = []
        for item in src.pop("callbacks", None) or []:
            if not isinstance(item, dict) or not item.get("pattern"):
                LOGGER.warning(f"Plugin {name}: skipping malformed callback entry {item!r}")
                continue
            callbacks.append(
                PluginCallback(
                    pattern=str(item["pattern"]),
                    handler=str(item.get("handler") or ""),
                    description=str(item.get("description") or ""),
                    access=_access_of(item, name),
                )
            )

        known = {
            "entry",
            "author",
            "description",
            "icon",
            "license",
            "repository",
            "tags",
            "min_bot_version",
            "max_bot_version",
            "python_dependencies",
            "config_schema",
        }
        fields = {k: src.pop(k) for k in list(src) if k in known}
        if src:
            LOGGER.warning(f"Plugin {name}: ignoring unknown manifest keys {sorted(src)}"
            )

        return cls(
            name=name,
            version=version,
            entry=str(fields.get("entry") or f"{name}.py"),
            author=str(fields.get("author") or ""),
            description=str(fields.get("description") or ""),
            icon=str(fields.get("icon") or ""),
            license=str(fields.get("license") or ""),
            repository=str(fields.get("repository") or ""),
            tags=[str(t) for t in (fields.get("tags") or [])],
            min_bot_version=str(fields.get("min_bot_version") or ""),
            max_bot_version=str(fields.get("max_bot_version") or ""),
            python_dependencies=[str(d) for d in (fields.get("python_dependencies") or [])],
            commands=commands,
            callbacks=callbacks,
            config_schema=fields.get("config_schema") or {},
            extra=src,
        )

    def command_names(self):
        names = []
        for cmd in self.commands:
            for item in cmd.names:
                if item not in names:
                    names.append(item)
        return names

    def version_error(self, current):
        now = _version_tuple(current)
        if self.min_bot_version and now < _version_tuple(self.min_bot_version):
            return f"needs bot v{self.min_bot_version} or newer, this is {current}"
        if self.max_bot_version and now > _version_tuple(self.max_bot_version):
            return f"supports bot up to v{self.max_bot_version}, this is {current}"
        return ""


def _access_of(item, plugin_name):
    value = str(item.get("access") or "").strip().lower()
    if not value:
        if item.get("sudo_only"):
            value = "sudo"
        elif item.get("owner_only"):
            value = "owner"
        else:
            value = "authorized"
    if value not in ACCESS:
        LOGGER.warning(f"Plugin {plugin_name}: unknown access {value!r}, falling back to authorized"
        )
        value = "authorized"
    return value


def read_manifest(plugin_dir):
    import yaml

    path = None
    for candidate in MANIFEST_NAMES:
        target = Path(plugin_dir) / candidate
        if target.is_file():
            path = target
            break
    if path is None:
        raise FileNotFoundError(f"no manifest in {plugin_dir}")
    with open(path, "r", encoding="utf-8") as handle:
        return PluginManifest.from_dict(yaml.safe_load(handle) or {})


class PluginBase:
    manifest: Optional[PluginManifest] = None
    bot = None
    config: Dict[str, Any] = {}

    async def on_load(self) -> bool:
        return True

    async def on_unload(self) -> bool:
        return True

    async def on_enable(self) -> bool:
        return True

    async def on_disable(self) -> bool:
        return True

    async def on_configure(self, config: Dict[str, Any]) -> bool:
        return True

    def get_config(self, key, default=None):
        return (self.config or {}).get(key, default)


@dataclass
class PluginRecord:
    manifest: PluginManifest
    path: Path
    instance: Optional[PluginBase] = None
    module: Any = None
    enabled: bool = True
    registered: bool = False
    source: str = "local"
    url: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    handlers: List[Any] = field(default_factory=list)
    error: str = ""

    @property
    def name(self):
        return self.manifest.name

    @property
    def version(self):
        return self.manifest.version

    @property
    def description(self):
        return self.manifest.description

    @property
    def commands(self):
        return self.manifest.command_names()

    def command_map(self):
        return {cmd.name: cmd.names for cmd in self.manifest.commands}


class PluginManager:
    def __init__(self, bot=None):
        self.bot = bot
        self.records: Dict[str, PluginRecord] = {}
        self.states: Dict[str, Dict[str, Any]] = {}
        self.errors: Dict[str, str] = {}
        self.installer = None
        self._lock = Lock()
        self._quiet = False
        self.plugins_dir = self._resolve_dir()
        try:
            self.plugins_dir.mkdir(exist_ok=True)
        except OSError as err:
            LOGGER.error(f"Plugins folder not usable: {err}")

    @staticmethod
    def _resolve_dir():
        beside = Path(__file__).resolve().parents[2] / "plugins"
        if beside.is_dir():
            return beside
        here = Path.cwd() / "plugins"
        if here.is_dir():
            LOGGER.warning(f"Using {here} for plugins, not {beside}")
            return here
        return beside

    def dir_of(self, name):
        target = (self.plugins_dir / name).resolve()
        if target.parent != self.plugins_dir.resolve():
            raise ValueError(f"plugin path escapes the plugins directory: {name}")
        return target

    def discover(self):
        found = []
        if not self.plugins_dir.is_dir():
            LOGGER.error(f"Plugins folder not found at {self.plugins_dir}")
            return found
        for entry in sorted(self.plugins_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith((".", "__")):
                continue
            if ".bak-" in entry.name:
                continue
            if any((entry / n).is_file() for n in MANIFEST_NAMES):
                found.append(entry.name)
            else:
                LOGGER.warning(
                    f"{entry.name} has no {MANIFEST_NAMES[0]}, skipping it"
                )
        return found

    def disk_manifest(self, name):
        try:
            return read_manifest(self.dir_of(name))
        except Exception as err:
            LOGGER.error(f"Plugin {name}: cannot read manifest: {err}")
            return None

    def available(self):
        return [name for name in self.discover() if name not in self.records]

    async def set_autoload(self, name, value):
        state = dict(self.states.get(name) or {})
        state["autoload"] = bool(value)
        self.states[name] = state
        try:
            from ..helper.ext_utils.db_handler import database

            await database.save_plugin(name, state)
        except Exception as err:
            LOGGER.error(f"Plugin {name}: could not persist autoload: {err}")

    def list_plugins(self):
        return list(self.records.values())

    def get(self, name):
        return self.records.get(name)

    def taken_commands(self, skip=None):
        from ..helper.telegram_helper.bot_commands import BotCommands

        taken = {}
        for key, value in BotCommands._static_commands.items():
            for item in value if isinstance(value, list) else [value]:
                taken[item] = key
        for rec in self.records.values():
            if rec.name == skip:
                continue
            for item in rec.commands:
                taken[item] = f"plugin {rec.name}"
        return taken

    def _ensure_namespace(self):
        if PKG not in sys.modules:
            namespace = ModuleType(PKG)
            namespace.__path__ = [str(self.plugins_dir)]
            sys.modules[PKG] = namespace

    def _purge_modules(self, name):
        prefix = f"{PKG}.{name}"
        for key in [
            k for k in list(sys.modules) if k == prefix or k.startswith(f"{prefix}.")
        ]:
            sys.modules.pop(key, None)

    def _import(self, name, manifest, plugin_dir):
        entry = (plugin_dir / manifest.entry).resolve()
        if plugin_dir.resolve() not in entry.parents:
            raise ValueError(f"entry {manifest.entry!r} escapes the plugin directory")
        if not entry.is_file():
            raise FileNotFoundError(f"entry file {manifest.entry} not found")

        self._ensure_namespace()
        self._purge_modules(name)
        pkg_name = f"{PKG}.{name}"
        spec = importlib.util.spec_from_file_location(
            pkg_name, entry, submodule_search_locations=[str(plugin_dir)]
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot build an import spec for {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[pkg_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            self._purge_modules(name)
            raise
        return module

    def _refresh_commands(self):
        if self._quiet:
            return
        try:
            from ..helper.telegram_helper.bot_commands import BotCommands

            BotCommands.refresh_commands()

            help_mod = sys.modules.get("bot.helper.ext_utils.help_messages")
            if help_mod is not None:
                importlib.reload(help_mod)

                handlers_mod = sys.modules.get("bot.core.handlers")
                if handlers_mod is not None and hasattr(handlers_mod, "BOT_COMMANDS"):
                    handlers_mod.BOT_COMMANDS = help_mod.BOT_COMMANDS

                help_page_mod = sys.modules.get("bot.modules.help")
                if help_page_mod is not None and hasattr(help_page_mod, "help_string"):
                    help_page_mod.help_string = help_mod.help_string
        except Exception as err:
            LOGGER.error(f"Plugin commands not refreshed: {err}", exc_info=True)

    def _filter_for(self, access):
        return getattr(CustomFilters, ACCESS.get(access, "authorized"))

    def _suffixed(self, names):
        suffix = Config.CMD_SUFFIX or ""
        return [f"{item}{suffix}" for item in names]

    def _build_handlers(self, rec):
        built = []
        module = rec.module
        for cmd in rec.manifest.commands:
            func = getattr(module, cmd.handler, None)
            if not callable(func):
                LOGGER.error(f"Plugin {rec.name}: handler {cmd.handler!r} for /{cmd.name} is missing"
                )
                continue
            built.append(
                (
                    MessageHandler(
                        func,
                        filters=command(
                            self._suffixed(cmd.names), case_sensitive=True
                        )
                        & self._filter_for(cmd.access),
                    ),
                    0,
                )
            )
        for cb in rec.manifest.callbacks:
            func = getattr(module, cb.handler, None) if cb.handler else None
            if not callable(func):
                LOGGER.error(f"Plugin {rec.name}: callback handler {cb.handler!r} is missing"
                )
                continue
            built.append(
                (
                    CallbackQueryHandler(
                        func,
                        filters=regex(cb.pattern) & self._filter_for(cb.access),
                    ),
                    0,
                )
            )
        return built

    def _attach(self, rec):
        if rec.registered:
            return True
        if self.bot is None:
            rec.error = "bot client is not ready"
            LOGGER.error(f"Plugin {rec.name}: {rec.error}")
            return False
        handlers = self._build_handlers(rec)
        for handler, group in handlers:
            self.bot.add_handler(handler, group)
        rec.handlers = handlers
        rec.registered = True
        return True

    def _detach(self, rec):
        if not rec.registered:
            return
        for handler, group in rec.handlers:
            try:
                self.bot.remove_handler(handler, group)
            except Exception as err:
                LOGGER.warning(f"Plugin {rec.name}: could not remove a handler: {err}")
        rec.handlers = []
        rec.registered = False

    async def _do_load(self, name, enabled=None, source=None, url=None, config=None):
        if name in self.records:
            LOGGER.warning(f"Plugin {name} is already loaded")
            return False, "already loaded"
        try:
            plugin_dir = self.dir_of(name)
        except ValueError as err:
            return False, str(err)
        if not plugin_dir.is_dir():
            return False, f"plugin folder {name} not found"

        try:
            manifest = read_manifest(plugin_dir)
        except Exception as err:
            LOGGER.error(f"Plugin {name}: bad manifest: {err}")
            return False, f"bad manifest: {err}"

        if manifest.name != name:
            return False, f"manifest name {manifest.name!r} does not match folder {name!r}"

        from ..version import get_version

        problem = manifest.version_error(get_version())
        if problem:
            return False, problem

        missing = missing_dependencies(manifest.python_dependencies)
        if missing:
            return False, "missing dependencies: " + ", ".join(missing)

        state = self.states.get(name, {})
        clash = self.taken_commands(skip=name)
        for item in manifest.command_names():
            if item in clash:
                return False, f"/{item} is already used by {clash[item]}"

        try:
            module = self._import(name, manifest, plugin_dir)
        except Exception as err:
            LOGGER.error(f"Plugin {name}: import failed: {err}", exc_info=True)
            return False, f"import failed: {err}"

        instance = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, PluginBase) and attr is not PluginBase:
                instance = attr()
                break

        rec = PluginRecord(
            manifest=manifest,
            path=plugin_dir,
            instance=instance,
            module=module,
            enabled=state.get("enabled", True) if enabled is None else bool(enabled),
            source=source or state.get("source", "local"),
            url=url or state.get("url", ""),
            config=config if config is not None else dict(state.get("config") or {}),
        )
        if instance is not None:
            instance.manifest = manifest
            instance.bot = self.bot
            instance.config = rec.config
            try:
                if not await instance.on_load():
                    self._purge_modules(name)
                    return False, "on_load returned False"
            except Exception as err:
                LOGGER.error(f"Plugin {name}: on_load failed: {err}", exc_info=True)
                self._purge_modules(name)
                return False, f"on_load failed: {err}"

        self.records[name] = rec
        if rec.enabled and not self._attach(rec):
            reason = rec.error or "could not register handlers"
            self.records.pop(name, None)
            if instance is not None:
                try:
                    await instance.on_unload()
                except Exception as err:
                    LOGGER.error(f"Plugin {name}: on_unload failed: {err}")
            self._purge_modules(name)
            return False, reason
        self._refresh_commands()
        return True, ""

    async def _do_unload(self, name):
        rec = self.records.get(name)
        if rec is None:
            return False, "not loaded"
        self._detach(rec)
        if rec.instance is not None:
            try:
                await rec.instance.on_unload()
            except Exception as err:
                LOGGER.error(f"Plugin {name}: on_unload failed: {err}", exc_info=True)
        self.records.pop(name, None)
        self._purge_modules(name)
        self._refresh_commands()
        return True, ""

    async def load(self, name, **kwargs):
        async with self._lock:
            ok, err = await self._do_load(name, **kwargs)
            if ok:
                self.errors.pop(name, None)
            else:
                self.errors[name] = err
            return ok, err

    async def unload(self, name):
        async with self._lock:
            return await self._do_unload(name)

    async def enable(self, name):
        async with self._lock:
            return await self._do_enable(name)

    async def disable(self, name):
        async with self._lock:
            return await self._do_disable(name)

    async def reload(self, name):
        async with self._lock:
            rec = self.records.get(name)
            enabled = rec.enabled if rec else None
            source = rec.source if rec else None
            url = rec.url if rec else None
            config = dict(rec.config) if rec else None
            if rec is not None:
                await self._do_unload(name)
            return await self._do_load(
                name, enabled=enabled, source=source, url=url, config=config
            )

    async def _do_enable(self, name):
        rec = self.records.get(name)
        if rec is None:
            ok, err = await self._do_load(name, enabled=True)
            if ok:
                await self._store(name, enabled=True)
            return ok, err
        if rec.enabled and rec.registered:
            return True, ""
        if rec.instance is not None:
            try:
                if not await rec.instance.on_enable():
                    return False, "on_enable returned False"
            except Exception as err:
                LOGGER.error(f"Plugin {name}: on_enable failed: {err}", exc_info=True)
                return False, f"on_enable failed: {err}"
        if not self._attach(rec):
            return False, rec.error or "could not register handlers"
        rec.enabled = True
        self._refresh_commands()
        await self._store(name, enabled=True)
        LOGGER.info(f"Plugin {name} enabled")
        return True, ""

    async def _do_disable(self, name):
        rec = self.records.get(name)
        if rec is None:
            return False, "not loaded"
        if rec.instance is not None:
            try:
                if not await rec.instance.on_disable():
                    return False, "on_disable returned False"
            except Exception as err:
                LOGGER.error(f"Plugin {name}: on_disable failed: {err}", exc_info=True)
                return False, f"on_disable failed: {err}"
        self._detach(rec)
        rec.enabled = False
        self._refresh_commands()
        await self._store(name, enabled=False)
        LOGGER.info(f"Plugin {name} disabled")
        return True, ""

    async def _store(self, name, **changes):
        rec = self.records.get(name)
        state = dict(self.states.get(name) or {})
        if rec is not None:
            state.update(
                {
                    "autoload": True,
                    "version": rec.version,
                    "source": rec.source,
                    "url": rec.url,
                    "enabled": rec.enabled,
                    "config": rec.config,
                }
            )
        state.update(changes)
        self.states[name] = state
        try:
            from ..helper.ext_utils.db_handler import database

            await database.save_plugin(name, state)
        except Exception as err:
            LOGGER.error(f"Plugin {name}: could not persist state: {err}")

    def schema_items(self, name):
        rec = self.records.get(name)
        if rec is None:
            return []
        schema = rec.manifest.config_schema or {}
        return [(key, schema[key] or {}) for key in sorted(schema)]

    def effective_config(self, name):
        rec = self.records.get(name)
        if rec is None:
            return {}
        merged = {}
        for key, spec in self.schema_items(name):
            merged[key] = spec.get("default")
        merged.update(rec.config or {})
        return merged

    @staticmethod
    def coerce_config(spec, raw):
        kind = str((spec or {}).get("type") or "string").lower()
        text = str(raw).strip()
        if kind in ("bool", "boolean"):
            if text.lower() in ("true", "1", "yes", "on"):
                return True
            if text.lower() in ("false", "0", "no", "off"):
                return False
            raise ValueError("expected true or false")
        if kind in ("int", "integer"):
            try:
                value = int(text)
            except ValueError:
                raise ValueError("expected a whole number") from None
        elif kind in ("float", "number"):
            try:
                value = float(text)
            except ValueError:
                raise ValueError("expected a number") from None
        elif kind == "list":
            return [part.strip() for part in text.split(",") if part.strip()]
        else:
            value = text
        low, high = (spec or {}).get("min"), (spec or {}).get("max")
        if isinstance(value, (int, float)):
            if low is not None and value < low:
                raise ValueError(f"must be at least {low}")
            if high is not None and value > high:
                raise ValueError(f"must be at most {high}")
        choices = (spec or {}).get("choices")
        if choices and value not in choices:
            raise ValueError("must be one of " + ", ".join(str(c) for c in choices))
        return value

    async def set_config(self, name, key, value):
        async with self._lock:
            rec = self.records.get(name)
            if rec is None:
                return False, "not loaded"
            rec.config[key] = value
            if rec.instance is not None:
                rec.instance.config = rec.config
                try:
                    await rec.instance.on_configure(dict(rec.config))
                except Exception as err:
                    LOGGER.error(f"Plugin {name}: on_configure failed: {err}")
            await self._store(name)
            try:
                from ..helper.ext_utils.db_handler import database

                await database.save_plugin_config(name, rec.config)
            except Exception as err:
                LOGGER.error(f"Plugin {name}: could not save settings: {err}")
            return True, ""

    async def reset_config(self, name):
        async with self._lock:
            rec = self.records.get(name)
            if rec is None:
                return False, "not loaded"
            rec.config = {}
            if rec.instance is not None:
                rec.instance.config = rec.config
            await self._store(name)
            try:
                from ..helper.ext_utils.db_handler import database

                await database.save_plugin_config(name, {})
            except Exception as err:
                LOGGER.error(f"Plugin {name}: could not clear settings: {err}")
            return True, ""

    async def load_states(self):
        try:
            from ..helper.ext_utils.db_handler import database

            self.states = await database.get_plugins() or {}
        except Exception as err:
            LOGGER.error(f"Plugin states not read: {err}")
            self.states = {}
        return self.states

    async def rescan(self):
        async with self._lock:
            before = set(self.records)
            if not self.plugins_dir.is_dir():
                self.plugins_dir = self._resolve_dir()
            found = self.discover()
            self._quiet = True
            try:
                for name in found:
                    if name in self.records:
                        continue
                    state = self.states.get(name) or {}
                    if not state.get("autoload", True):
                        continue
                    ok, err = await self._do_load(
                        name,
                        enabled=state.get("enabled", True),
                        source=state.get("source", "local"),
                        url=state.get("url", ""),
                        config=state.get("config") or {},
                    )
                    if ok:
                        self.errors.pop(name, None)
                    else:
                        self.errors[name] = err
            finally:
                self._quiet = False
            self._refresh_commands()
            return found, sorted(set(self.records) - before)

    async def unload_all(self):
        async with self._lock:
            self._quiet = True
            try:
                for name in list(self.records):
                    await self._do_unload(name)
            finally:
                self._quiet = False
            self._refresh_commands()

    async def boot(self):
        if Config.DISABLE_PLUGINS:
            LOGGER.info("Plugins are disabled. Skipping plugin load.")
            return
        async with self._lock:
            await self.load_states()
            found = self.discover()
            self.errors.clear()
            self._quiet = True
            loaded = 0
            try:
                for name in found:
                    state = self.states.get(name)
                    if state is None:
                        await self._store(name, enabled=True, source="bundled")
                        state = self.states[name]
                    if not state.get("autoload", True):
                        continue
                    ok, err = await self._do_load(
                        name,
                        enabled=state.get("enabled", True),
                        source=state.get("source", "local"),
                        url=state.get("url", ""),
                        config=state.get("config") or {},
                    )
                    if ok:
                        loaded += 1
                    else:
                        self.errors[name] = err
            finally:
                self._quiet = False
            self._refresh_commands()
            if found:
                names = ", ".join(sorted(self.records))
                line = f"Plugins Loaded [{loaded}/{len(found)}]"
                if names:
                    line += f": {names}"
                idle = self.available()
                if idle:
                    line += f" | Skipped: {', '.join(sorted(idle))}"
                LOGGER.info(line)


plugin_manager = PluginManager(None)


def get_plugin_manager() -> PluginManager:
    return plugin_manager
