import os
import re
import time
import asyncio
import platform
from datetime import datetime
from base64 import b64encode
from os import path as ospath, remove as aioremove, mkdir
from pkg_resources import get_distribution, DistributionNotFound
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, mkdir
from re import match as re_match
from time import time
from html import escape
from uuid import uuid4
from subprocess import run as srun
from psutil import disk_usage, disk_io_counters, Process, cpu_percent, swap_memory, cpu_count, cpu_freq, getloadavg, virtual_memory, net_io_counters, boot_time
from asyncio import create_subprocess_exec, create_subprocess_shell, run_coroutine_threadsafe, sleep
from asyncio.subprocess import PIPE
from functools import partial, wraps
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import requests
import mega
import pyrogram
from pyrogram.enums import ChatType
from pyrogram.types import BotCommand
from pyrogram.errors import PeerIdInvalid

# Rest of the code remains the same
