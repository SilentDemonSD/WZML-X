from bot import CMD_SUFFIX
from os import environ

def getCommand(name: str, command: str):
    try:
        if len(environ[name]) == 0:
            raise KeyError
        return environ[name]
    except KeyError:
        return command

class _BotCommands:
    def __init__(self):
        self.StartCommand = getCommand(f'START_COMMAND', f'start{CMD_SUFFIX}')
        self.MirrorCommand = getCommand(f'MIRROR_COMMAND', f'mirror{CMD_SUFFIX}'), f'm{CMD_SUFFIX}'
        self.UnzipMirrorCommand = getCommand(f'UNZIP_COMMAND', f'unzipmirror{CMD_SUFFIX}'), f'uzm{CMD_SUFFIX}'
        self.ZipMirrorCommand = getCommand(f'ZIP_COMMAND', f'zipmirror{CMD_SUFFIX}'), f'zm{CMD_SUFFIX}'
        self.LeechCommand = getCommand(f'LEECH_COMMAND', f'leech{CMD_SUFFIX}'), f'l{CMD_SUFFIX}'
        self.UnzipLeechCommand = getCommand(f'UNZIPLEECH_COMMAND', f'unzipleech{CMD_SUFFIX}'), f'uzl{CMD_SUFFIX}'
        self.ZipLeechCommand = getCommand(f'ZIPLEECH_COMMAND', f'zipleech{CMD_SUFFIX}'), f'zl{CMD_SUFFIX}'
        self.CloneCommand = getCommand(f'CLONE_COMMAND', f'clone{CMD_SUFFIX}'), f'c{CMD_SUFFIX}'
        self.QbMirrorCommand = getCommand(f'QBMIRROR_COMMAND', f'qbmirror{CMD_SUFFIX}'), f'qm{CMD_SUFFIX}'
        self.QbUnzipMirrorCommand = getCommand(f'QBUNZIP_COMMAND', f'qbunzipmirror{CMD_SUFFIX}'), f'quzm{CMD_SUFFIX}'
        self.QbZipMirrorCommand = getCommand(f'QBZIP_COMMAND', f'qbzipmirror{CMD_SUFFIX}'), f'qzm{CMD_SUFFIX}'
        self.QbLeechCommand = getCommand(f'QBLEECH_COMMAND', f'qbleech{CMD_SUFFIX}'), f'ql{CMD_SUFFIX}'
        self.QbUnzipLeechCommand = getCommand(f'QBZIPLEECH_COMMAND', f'qbunzipleech{CMD_SUFFIX}'), f'quzl{CMD_SUFFIX}'
        self.QbZipLeechCommand = getCommand(f'QBUNZIPLEECH_COMMAND', f'qbzipleech{CMD_SUFFIX}'), f'qzl{CMD_SUFFIX}'
        self.ScrapeCommand = getCommand(f'SCRAPE_COMMAND', f'scrape{CMD_SUFFIX}'), f'sm{CMD_SUFFIX}'
        self.YtdlCommand =  getCommand(f'YTDL_COMMAND', f'ytdl{CMD_SUFFIX}'), f'y{CMD_SUFFIX}'
        self.YtdlZipCommand = getCommand(f'YTDLZIP_COMMAND', f'ytdlzip{CMD_SUFFIX}'), f'yz{CMD_SUFFIX}'
        self.YtdlLeechCommand = getCommand(f'YTDLLEECH_COMMAND',  f'ytdlleech{CMD_SUFFIX}'), f'yl{CMD_SUFFIX}'
        self.YtdlZipLeechCommand = getCommand(f'YTDLZIPLEECH_COMMAND', f'ytdlzipleech{CMD_SUFFIX}'), f'yzl{CMD_SUFFIX}'
        self.MediaInfoCommand = getCommand(f'MEDIAINFO_COMMAND', f'mediainfo{CMD_SUFFIX}'), f'mi{CMD_SUFFIX}'
        self.UserSetCommand  = getCommand(f'USERSET_COMMAND', f'usetting{CMD_SUFFIX}'), f'us{CMD_SUFFIX}'
        self.BotSetCommand = getCommand(f'BOT_SETTING', f'bsetting{CMD_SUFFIX}'), f'bs{CMD_SUFFIX}'
        self.CancelMirror = getCommand(f'CANCEL_COMMAND', f'cancel{CMD_SUFFIX}')
        self.CancelAllCommand = getCommand(f'CANCEL_ALL_COMMAND', f'cancelall{CMD_SUFFIX}')
        self.ListCommand = getCommand(f'LIST_COMMAND', f'list{CMD_SUFFIX}')
        self.SearchCommand = getCommand(f'SEARCH_COMMAND', f'search{CMD_SUFFIX}')
        self.StatusCommand = getCommand(f'STATUS_COMMAND', f'status{CMD_SUFFIX}')
        self.UsersCommand = getCommand(f'USERS_COMMAND', f'users{CMD_SUFFIX}')
        self.PaidUsersCommand = getCommand(f'PAID_COMMAND', f'paid{CMD_SUFFIX}')
        self.AddPaidCommand = getCommand(f'ADDPAID_COMMAND', f'addpaid{CMD_SUFFIX}')
        self.RmPaidCommand = getCommand(f'RMPAID_COMMAND', f'rmpaid{CMD_SUFFIX}')
        self.AuthorizeCommand = getCommand(f'AUTH_COMMAND', f'authorize{CMD_SUFFIX}')
        self.UnAuthorizeCommand = getCommand(f'UNAUTH_COMMAND', f'unauthorize{CMD_SUFFIX}')
        self.AddSudoCommand = getCommand(f'ADDSUDO_COMMAND', f'addsudo{CMD_SUFFIX}')
        self.RmSudoCommand = getCommand(f'RMSUDO_COMMAND', f'rmsudo{CMD_SUFFIX}')
        self.PingCommand = getCommand(f'PING_COMMAND', f'ping{CMD_SUFFIX}')
        self.RestartCommand =  getCommand(f'RESTART_COMMAND', f'restart{CMD_SUFFIX}')
        self.StatsCommand = getCommand(f'STATS_COMMAND', f'stats{CMD_SUFFIX}')
        self.HelpCommand = getCommand(f'HELP_COMMAND', f'help{CMD_SUFFIX}')
        self.LogCommand = getCommand(f'LOG_COMMAND', f'log{CMD_SUFFIX}')
        self.BtSelectCommand = getCommand(f'BTSEL_COMMAND', f'btsel{CMD_SUFFIX}')
        self.SpeedCommand = getCommand(f'SPEEDTEST_COMMAND', f'speedtest{CMD_SUFFIX}'), f'st{CMD_SUFFIX}'
        self.CountCommand = getCommand(f'COUNT_COMMAND', f'count{CMD_SUFFIX}')
        self.DeleteCommand = getCommand(f'DELETE_COMMAND', f'del{CMD_SUFFIX}')
        self.ShellCommand = getCommand(f'SHELL_COMMAND', f'shell{CMD_SUFFIX}')
        self.ExecHelpCommand = getCommand(f'EXEHELP_COMMAND', f'exechelp{CMD_SUFFIX}')
        self.HashCommand = getCommand(f'HASH_COMMAND', f'hash{CMD_SUFFIX}')
        self.RssListCommand = getCommand(f'RSSLIST_COMMAND', f'rsslist{CMD_SUFFIX}')
        self.RssGetCommand = getCommand(f'RSSGET_COMMAND', f'rssget{CMD_SUFFIX}')
        self.RssSubCommand = getCommand(f'RSSSUB_COMMAND', f'rsssub{CMD_SUFFIX}')
        self.RssUnSubCommand = getCommand(f'RSSUNSUB_COMMAND', f'rssunsub{CMD_SUFFIX}')
        self.RssSettingsCommand = getCommand(f'RSSSET_COMMAND', f'rssset{CMD_SUFFIX}')
        self.WayBackCommand = getCommand(f'WAYBACK_COMMAND', f'wayback{CMD_SUFFIX}')
        self.AddleechlogCommand = getCommand(f'ADDLEECHLOG_CMD', f'addleechlog{CMD_SUFFIX}')
        self.RmleechlogCommand = getCommand(f'RMLEECHLOG_CMD', f'rmleechlog{CMD_SUFFIX}')
        self.SelectCategory = getCommand(f'CATSEL_CMD', f'catsel{CMD_SUFFIX}')
        self.EvalCommand = f'eval{CMD_SUFFIX}'
        self.ExecCommand = f'exec{CMD_SUFFIX}'
        self.ClearLocalsCommand = f'clearlocals{CMD_SUFFIX}'
        self.LimitCommand = getCommand(f'LIMIT_COMMAND', f'limit{CMD_SUFFIX}')
        self.DriveCleanCommand = getCommand(f'DRIVECLEAN_COMMAND', f'driveclean{CMD_SUFFIX}')

BotCommands = _BotCommands()
