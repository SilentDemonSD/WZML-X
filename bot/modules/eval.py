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
    """
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise asyncio.SubprocessError(
            cmd,
            process.returncode,
            stderr.decode().strip()
        )

    output = stdout.decode().strip()
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script.py [command]")
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        output = asyncio.run(run_command(cmd))
        print(textwrap.dedent(f"""\
            Command Output:
            {output}
        """))

    except asyncio.SubprocessError as e:
        print(textwrap.dedent(f"""\
            Error running command "{e.cmd}":
            {e.stderr}
        """))
        sys.exit(e.returncode)
