from bot import CMD_INDEX
import os
def getCommand(name: str, command: str):
    try:
        if len(os.environ[name]) == 0:
            raise KeyError
        return os.environ[name]
    except KeyError:
        return command


class _BotCommands:
    def __init__(self):
        self.StartCommand = getCommand(f'START_COMMAND', f'start{CMD_INDEX}')
        self.MirrorCommand = getCommand('MIRROR_COMMAND', f'mirror{CMD_INDEX}')
        self.UnzipMirrorCommand = getCommand('UNZIP_COMMAND', f'unzipmirror{CMD_INDEX}')
        self.ZipMirrorCommand = getCommand('ZIP_COMMAND', f'zipmirror{CMD_INDEX}')
        self.CancelMirror = getCommand('CANCEL_COMMAND', f'cancel{CMD_INDEX}')
        self.CancelAllCommand = getCommand('CANCEL_ALL_COMMAND', f'cancelall{CMD_INDEX}')
        self.ListCommand = getCommand('LIST_COMMAND', f'list{CMD_INDEX}')
        self.SearchCommand = getCommand('SEARCH_COMMAND', f'search{CMD_INDEX}')
        self.StatusCommand = getCommand('STATUS_COMMAND', f'status{CMD_INDEX}')
        self.AuthorizedUsersCommand = getCommand('USERS_COMMAND', f'users{CMD_INDEX}')
        self.PaidUsersCommand = getCommand('PAID_COMMAND', f'paid{CMD_INDEX}')
        self.AddPaidCommand = getCommand('ADDPAID_COMMAND', f'addpaid{CMD_INDEX}')
        self.RmPaidCommand = getCommand('RMPAID_COMMAND', f'rmpaid{CMD_INDEX}')
        self.PreNameCommand = getCommand('PRENAME_COMMAND', f'prefix{CMD_INDEX}')
        self.SufNameCommand = getCommand('SUFFIX_COMMAND', f'suffix{CMD_INDEX}')
        self.CaptionCommand = getCommand('CAPTION_COMMAND', f'caption{CMD_INDEX}')
        self.UserLogCommand = getCommand('DUMPID_COMMAND', f'dumpid{CMD_INDEX}')
        self.RemnameCommand = getCommand('REMNAME_COMMAND', f'remname{CMD_INDEX}')
        self.AuthorizeCommand = getCommand('AUTH_COMMAND', f'authorize{CMD_INDEX}')
        self.UnAuthorizeCommand = getCommand('UNAUTH_COMMAND', f'unauthorize{CMD_INDEX}')
        self.AddSudoCommand = getCommand('ADDSUDO_COMMAND', f'addsudo{CMD_INDEX}')
        self.RmSudoCommand = getCommand('RMSUDO_COMMAND', f'rmsudo{CMD_INDEX}')
        self.PingCommand = getCommand('PING_COMMAND', f'ping{CMD_INDEX}')
        self.RestartCommand =  getCommand('RESTART_COMMAND', f'restart{CMD_INDEX}')
        self.StatsCommand = getCommand('STATS_COMMAND', f'stats{CMD_INDEX}')
        self.HelpCommand = getCommand('HELP_COMMAND', f'help{CMD_INDEX}')
        self.LogCommand = getCommand('LOG_COMMAND', f'log{CMD_INDEX}')
        self.BtSelectCommand = getCommand('BTSEL_COMMAND', f'btsel{CMD_INDEX}')
        self.SpeedCommand = getCommand('SPEEDTEST_COMMAND', f'speedtest{CMD_INDEX}')
        self.CloneCommand = getCommand('CLONE_COMMAND', f'clone{CMD_INDEX}')
        self.CountCommand = getCommand('COUNT_COMMAND', f'count{CMD_INDEX}')
        self.WatchCommand =  getCommand('WATCH_COMMAND', f'watch{CMD_INDEX}')
        self.ZipWatchCommand = getCommand('ZIPWATCH_COMMAND', f'zipwatch{CMD_INDEX}')
        self.ScrapeCommand = getCommand('SCRAPE_COMMAND', f'scrape{CMD_INDEX}')
        self.QbMirrorCommand = getCommand('QBMIRROR_COMMAND', f'qbmirror{CMD_INDEX}')
        self.QbUnzipMirrorCommand = getCommand('QBUNZIP_COMMAND', f'qbunzipmirror{CMD_INDEX}')
        self.QbZipMirrorCommand = getCommand('QBZIP_COMMAND', f'qbzipmirror{CMD_INDEX}')
        self.DeleteCommand = getCommand('DELETE_COMMAND', f'del{CMD_INDEX}')
        self.ShellCommand = getCommand('SHELL_COMMAND', f'shell{CMD_INDEX}')
        self.ExecHelpCommand = getCommand('EXEHELP_COMMAND', f'exechelp{CMD_INDEX}')
        self.LeechSetCommand = getCommand('LEECHSET_COMMAND', f'leechset{CMD_INDEX}')
        self.SetThumbCommand = getCommand('SETTHUMB_COMMAND', f'setthumb{CMD_INDEX}')
        self.LeechCommand = getCommand('LEECH_COMMAND', f'leech{CMD_INDEX}')
        self.UnzipLeechCommand = getCommand('UNZIPLEECH_COMMAND', f'unzipleech{CMD_INDEX}')
        self.ZipLeechCommand = getCommand('ZIPLEECH_COMMAND', f'zipleech{CMD_INDEX}')
        self.QbLeechCommand = getCommand('QBLEECH_COMMAND', f'qbleech{CMD_INDEX}')
        self.QbUnzipLeechCommand = getCommand('QBZIPLEECH_COMMAND', f'qbunzipleech{CMD_INDEX}')
        self.QbZipLeechCommand = getCommand('QBUNZIPLEECH_COMMAND', f'qbzipleech{CMD_INDEX}')
        self.LeechWatchCommand = getCommand('LEECHWATCH_COMMAND',  f'leechwatch{CMD_INDEX}')
        self.MediaInfoCommand = getCommand('MEDIAINFO_COMMAND', f'mediainfo{CMD_INDEX}')
        self.HashCommand = getCommand('HASH_COMMAND', f'hash{CMD_INDEX}')
        self.LeechZipWatchCommand = getCommand('LEECHZIPWATCH_COMMAND', f'leechzipwatch{CMD_INDEX}')
        self.RssListCommand = getCommand('RSSLIST_COMMAND', f'rsslist{CMD_INDEX}')
        self.RssGetCommand = getCommand('RSSGET_COMMAND', f'rssget{CMD_INDEX}')
        self.RssSubCommand = getCommand('RSSSUB_COMMAND', f'rsssub{CMD_INDEX}')
        self.RssUnSubCommand = getCommand('RSSUNSUB_COMMAND', f'rssunsub{CMD_INDEX}')
        self.RssSettingsCommand = getCommand('RSSSET_COMMAND', f'rssset{CMD_INDEX}')
        self.WayBackCommand = getCommand('WAYBACK_COMMAND', f'wayback{CMD_INDEX}')
        self.AddleechlogCommand = getCommand('ADDLEECHLOG_CMD', f'addleechlog{CMD_INDEX}')
        self.RmleechlogCommand = getCommand('RMLEECHLOG_CMD', f'rmleechlog{CMD_INDEX}')
        self.UsageCommand = getCommand('USAGE_COMMAND', f'usage{CMD_INDEX}')
        self.SleepCommand = getCommand('SLEEP_COMMAND', f'sleep{CMD_INDEX}')
        self.EvalCommand = f'eval{CMD_INDEX}'
        self.ExecCommand = f'exec{CMD_INDEX}'
        self.ClearLocalsCommand = f'clearlocals{CMD_INDEX}'

BotCommands = _BotCommands()
