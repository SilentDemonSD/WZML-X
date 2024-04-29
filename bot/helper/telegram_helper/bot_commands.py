#!/usr/bin/env python3
from bot import CMD_SUFFIX, config_dict
from typing import List, Tuple, Dict

class BotCommands:
    """A class to manage bot commands."""

    command_templates = (
        ('%sCommand', '%s%s', '%sc%s'),
        ('Qb%sCommand', 'qb%s%s', 'q%sc%s'),
        ('Ytdl%sCommand', 'ytdl%s%s', 'y%sc%s'),
        ('Zip%sCommand', '%szip%s%s', '%sz%s%s'),
        ('Unzip%sCommand', 'un%szip%s%s', 'un%sz%s%s'),
    )

    def __init__(self):
        self.commands = {
            name: tuple(commands % (alias, CMD_SUFFIX) for alias in commands)
            for name, *commands in self.command_templates
        }

        if config_dict['SHOW_EXTRA_CMDS']:
            self.commands.update({
                name: tuple(commands % (alias, CMD_SUFFIX) for alias in commands)
                for name, *commands in self.extra_command_templates
            })

    extra_command_templates = [
        ('MirrorCommand', 'unzipmirror', 'uzm', 'zipmirror', 'zm'),
        ('QbMirrorCommand', 'qbunzipmirror', 'quzm', 'qbzipmirror', 'qzm'),
        ('YtdlCommand', 'ytdlzip', 'yz'),
        ('LeechCommand', 'unzipleech', 'uzl', 'zipleech', 'zl'),
        ('QbLeechCommand', 'qbunzipleech', 'quzl', 'qbzipleech', 'qzl'),
        ('YtdlLeechCommand', 'ytdlzipleech', 'yzl'),
    ]


bot_commands = BotCommands()
print(bot_commands.commands['StartCommand'])  # Output: ('StartCommand', 'start')
