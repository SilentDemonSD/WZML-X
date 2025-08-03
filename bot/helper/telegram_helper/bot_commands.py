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
        "NzbMirror": ["nzbmirror", "nm"],
        "Leech": ["leech", "l"],
        "QbLeech": ["qbleech", "ql"],
        "JdLeech": ["jdleech", "jl"],
        "YtdlLeech": ["ytdlleech", "yl"],
        "NzbLeech": ["nzbleech", "nl"],
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
        "MediaInfo": ["mediainfo", "mi"],
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
        "IMDB": "imdb",
        "Rss": "rss",
        "Authorize": ["authorize", "a"],
        "UnAuthorize": ["unauthorize", "ua"],
        "AddSudo": ["addsudo", "as"],
        "RmSudo": ["rmsudo", "rs"],
        "BotSet": ["bsetting", "bs"],
        "UserSet": ["usetting", "us"],
        "Select": ["select", "sel"],
        "NzbSearch": "nzbsearch",
        "Plugins": "plugins",
    }

    @classmethod
    def get_commands(cls):
        commands = cls._static_commands.copy()
        
        plugin_manager = get_plugin_manager()
        if plugin_manager:
            for plugin_info in plugin_manager.list_plugins():
                if plugin_info.enabled and plugin_info.commands:
                    for cmd in plugin_info.commands:
                        if cmd == "speedtest":
                            commands["SpeedTest"] = ["speedtest", "stest"]
                        elif cmd == "stest":
                            if "SpeedTest" not in commands:
                                commands["SpeedTest"] = ["speedtest", "stest"]
                            elif "stest" not in commands["SpeedTest"]:
                                commands["SpeedTest"].append("stest")
        
        return commands

    @classmethod
    def _build_command_vars(cls):
        commands = cls.get_commands()
        
        for key, cmds in commands.items():
            setattr(cls, f"{key}Command", (
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
            ))

    @classmethod
    def refresh_commands(cls):
        cls._build_command_vars()


BotCommands._build_command_vars()
