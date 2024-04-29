#!/usr/bin/env python3
from bot import CMD_SUFFIX, config_dict

class BotCommands:
    def __init__(self):
        command_list = [
            ('StartCommand', 'start'),
            ('MirrorCommand', f'mirror{CMD_SUFFIX}', f'm{CMD_SUFFIX}'),
            ('QbMirrorCommand', f'qbmirror{CMD_SUFFIX}', f'qm{CMD_SUFFIX}'),
            ('YtdlCommand', f'ytdl{CMD_SUFFIX}', f'y{CMD_SUFFIX}'),
            ('LeechCommand', f'leech{CMD_SUFFIX}', f'l{CMD_SUFFIX}'),
            ('QbLeechCommand', f'qbleech{CMD_SUFFIX}', f'ql{CMD_SUFFIX}'),
            ('YtdlLeechCommand', f'ytdlleech{CMD_SUFFIX}', f'yl{CMD_SUFFIX}'),
            ('CloneCommand', f'clone{CMD_SUFFIX}', f'c{CMD_SUFFIX}'),
            ('CountCommand', f'count{CMD_SUFFIX}'),
            ('DeleteCommand', f'del{CMD_SUFFIX}'),
            ('CancelMirror', f'cancel{CMD_SUFFIX}'),
            ('CancelAllCommand', f'cancelall{CMD_SUFFIX}', 'cancellallbot'),
            ('ListCommand', f'list{CMD_SUFFIX}'),
            ('SearchCommand', f'search{CMD_SUFFIX}'),
            ('StatusCommand', f'status{CMD_SUFFIX}', f's{CMD_SUFFIX}', 'statusall'),
            ('UsersCommand', f'users{CMD_SUFFIX}'),
            ('AuthorizeCommand', f'authorize{CMD_SUFFIX}', f'a{CMD_SUFFIX}'),
            ('UnAuthorizeCommand', f'unauthorize{CMD_SUFFIX}', f'ua{CMD_SUFFIX}'),
            ('AddBlackListCommand', f'blacklist{CMD_SUFFIX}', f'bl{CMD_SUFFIX}'),
            ('RmBlackListCommand', f'rmblacklist{CMD_SUFFIX}', f'rbl{CMD_SUFFIX}'),
            ('AddSudoCommand', f'addsudo{CMD_SUFFIX}'),
            ('RmSudoCommand', f'rmsudo{CMD_SUFFIX}'),
            ('PingCommand', f'ping{CMD_SUFFIX}', f'p{CMD_SUFFIX}'),
            ('RestartCommand', f'restart{CMD_SUFFIX}', f'r{CMD_SUFFIX}', 'restartall'),
            ('StatsCommand', f'stats{CMD_SUFFIX}', f'st{CMD_SUFFIX}'),
            ('HelpCommand', f'help{CMD_SUFFIX}'),
            ('LogCommand', f'log{CMD_SUFFIX}'),
            ('ShellCommand', f'shell{CMD_SUFFIX}'),
            ('EvalCommand', f'eval{CMD_SUFFIX}'),
            ('ExecCommand', f'exec{CMD_SUFFIX}'),
            ('ClearLocalsCommand', f'clearlocals{CMD_SUFFIX}'),
            ('BotSetCommand', f'bsetting{CMD_SUFFIX}', f'bs{CMD_SUFFIX}'),
            ('UserSetCommand', f'usetting{CMD_SUFFIX}', f'us{CMD_SUFFIX}'),
            ('BtSelectCommand', f'btsel{CMD_SUFFIX}'),
            ('CategorySelect', f'ctsel{CMD_SUFFIX}'),
            ('SpeedCommand', f'speedtest{CMD_SUFFIX}', f'sp{CMD_SUFFIX}'),
            ('RssCommand', f'rss{CMD_SUFFIX}'),
            ('LoginCommand', 'login'),
            ('AddImageCommand', f'addimg{CMD_SUFFIX}'),
            ('ImagesCommand', f'images{CMD_SUFFIX}'),
            ('IMDBCommand', f'imdb{CMD_SUFFIX}'),
            ('AniListCommand', f'anime{CMD_SUFFIX}'),
            ('AnimeHelpCommand', f'animehelp{CMD_SUFFIX}'),
            ('MediaInfoCommand', f'mediainfo{CMD_SUFFIX}', f'mi{CMD_SUFFIX}'),
            ('MyDramaListCommand', f'mdl{CMD_SUFFIX}'),
            ('GDCleanCommand', f'gdclean{CMD_SUFFIX}', f'gc{CMD_SUFFIX}'),
            ('BroadcastCommand', f'broadcast{CMD_SUFFIX}', f'bc{CMD_SUFFIX}')
        ]

        if config_dict['SHOW_EXTRA_CMDS']:
            extra_cmds = [
                ('MirrorCommand', f'unzipmirror{CMD_SUFFIX}', f'uzm{CMD_SUFFIX}', f'zipmirror{CMD_SUFFIX}', f'zm{CMD_SUFFIX}'),
                ('QbMirrorCommand', f'qbunzipmirror{CMD_SUFFIX}', f'quzm{CMD_SUFFIX}', f'qbzipmirror{CMD_SUFFIX}', f'qzm{CMD_SUFFIX}'),
                ('YtdlCommand', f'ytdlzip{CMD_SUFFIX}', f'yz{CMD_SUFFIX}'),
                ('LeechCommand', f'unzipleech{CMD_SUFFIX}', f'uzl{CMD_SUFFIX}', f'zipleech{CMD_SUFFIX}', f'zl{CMD_SUFFIX}'),
                ('QbLeechCommand', f'qbunzipleech{CMD_SUFFIX}', f'quzl{CMD_SUFFIX}', f'qbzipleech{CMD_SUFFIX}', f'qzl{CMD_SUFFIX}'),
                ('YtdlLeechCommand', f'ytdlzipleech{CMD_SUFFIX}', f'yzl{CMD_SUFFIX}')
            ]
            command_list += extra_cmds

        self.commands = {name: commands for name, *commands in command_list}

bot_commands = BotCommands()


print(bot_commands.commands['StartCommand'])  # Output: ('StartCommand', 'start')
