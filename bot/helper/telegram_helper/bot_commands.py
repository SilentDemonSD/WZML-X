from ...core.config_manager import Config
from ...core.plugin_manager import get_plugin_manager


class BotCommands:
    StartCommand = "start"
    LoginCommand = "login"

    _static_commands = {
        "Mirror": ["mirror", "m"],
        "QbMirror": ["qbmirror", "qm"],
        "JdMirror": ["jdmirror", "jm"],
        "Ytdl": ["ytdl", "y"],
        "UpHoster": ["uphoster", "up"],
        "NzbMirror": ["nzbmirror", "nm"],
        "Leech": ["leech", "l"],
        "QbLeech": ["qbleech", "ql"],
        "JdLeech": ["jdleech", "jl"],
        "YtdlLeech": ["ytdlleech", "yl"],
        "NzbLeech": ["nzbleech", "nl"],
        "SeedrLink": ["seedrlink", "slink", "srlink"],
        "Clone": ["clone", "cl"],
        "Count": "count",
        "Delete": "del",
        "List": "list",
        "Search": "search",
        "Users": "users",
        "CancelTask": ["cancel", "c"],
        "CancelAll": ["cancelall", "call"],
        "ForceStart": ["forcestart", "fs"],
        "Status": ["status", "s", "statusall"],
        "Stream": ["stream", "sl"],
        "Ping": "ping",
        "Restart": ["restart", "r", "restartall"],
        "RestartSessions": ["restartses", "rses"],
        "Broadcast": ["broadcast", "bc"],
        "Stats": ["stats", "st"],
        "Help": ["help", "h"],
        "Log": "log",
        "Shell": "shell",
        "AExec": "aexec",
        "Exec": "exec",
        "ClearLocals": "clearlocals",
        "Rss": "rss",
        "AddImage": ["addimage", "ai"],
        "Images": ["images", "img"],
        "Authorize": ["authorize", "a"],
        "UnAuthorize": ["unauthorize", "ua"],
        "AddSudo": ["addsudo", "as"],
        "RmSudo": ["rmsudo", "rs"],
        "BlackList": ["blacklist", "bl"],
        "RmBlackList": ["rmblacklist", "rbl"],
        "BotSet": ["bsetting", "bs"],
        "UserSet": ["usetting", "us"],
        "Select": ["select", "sel"],
        "CategorySelect": ["category", "ctsel"],
        "GDClean": ["gdclean", "gdc"],
        "Plugins": "plugins",
        "Memory": ["memory", "mem"],
    }

    @classmethod
    def get_commands(cls):
        commands = {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in cls._static_commands.items()
        }
        taken = set()
        for value in commands.values():
            taken.update(value if isinstance(value, list) else [value])

        plugin_manager = get_plugin_manager()
        if plugin_manager:
            for rec in plugin_manager.list_plugins():
                if not rec.enabled:
                    continue
                for primary, names in rec.command_map().items():
                    fresh = [name for name in names if name not in taken]
                    if not fresh:
                        continue
                    key = primary.capitalize()
                    if key in commands:
                        key = f"{rec.name.capitalize()}{key}"
                    commands[key] = fresh
                    taken.update(fresh)

        return commands

    @classmethod
    def _build_command_vars(cls):
        commands = cls.get_commands()

        for key, cmds in commands.items():
            setattr(
                cls,
                f"{key}Command",
                (
                    [
                        (
                            f"{cmd}{Config.CMD_SUFFIX}"
                            if cmd not in ["restartall", "statusall"]
                            else cmd
                        )
                        for cmd in cmds
                    ]
                    if isinstance(cmds, list)
                    else f"{cmds}{Config.CMD_SUFFIX}"
                ),
            )

    @classmethod
    def refresh_commands(cls):
        cls._build_command_vars()


BotCommands._build_command_vars()
