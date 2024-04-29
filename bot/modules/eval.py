#!/usr/bin/env python3
import asyncio
import os
import sys
import textwrap
from io import StringIO
from re import match

async def run_command(cmd):
    """
    Asynchronously run a shell command.

    :param cmd: The command to run.
    :type cmd: str
    :return: The output of the command.

