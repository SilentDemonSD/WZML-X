from ...core.config_manager import Config


class BotCommands:
    StartCommand = "start"
    LoginCommand = "login"

    commands = {
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
        "SpeedTest": ["speedtest", "stest"],
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
    }

    for key, cmds in commands.items():
        vars()[f"{key}Command"] = (
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
        )