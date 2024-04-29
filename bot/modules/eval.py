#!/usr/bin/env python3
import asyncio
import os
import sys
import textwrap
from io import StringIO
from re import match

async def run\_command(cmd):
"""
Asynchronously run a shell command.

:param cmd: The command to run.
:type cmd: str
:return: The output of the command.
:rtype: str
"""
process = await asyncio.create\_subprocess\_shell(
cmd,
stdout=asyncio.subprocess.PIPE,
stderr=asyncio.subprocess.PIPE,
)

stdout, stderr = await process.communicate()

if stderr:
return f"{cmd}\n{stderr.decode()}"

return f"{cmd}\n{stdout.decode()}"

async def run\_commands(commands):
"""
Asynchronously run a list of shell commands.

:param commands: The list of commands to run.
:type commands: list
:return: A list of the output of each command.
:rtype: list
"""
output = []

for cmd in commands:
output.append(await run\_command(cmd))

return output

def main():
if len(sys.argv) < 2:
print("Usage: {} command [command ...]".format(os.path.basename(sys.argv[0])))
sys.exit(1)

commands = sys.argv[1:]

output = asyncio.run(run\_commands(commands))

for line in output:
print(line, end="")

if __name__ == "__main__":
main()
