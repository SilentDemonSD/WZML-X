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
    if len(cmd) > 256:
        raise ValueError("Command length should not exceed 256 characters")

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=asyncio.get_event_loop().get_timeout(),
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise asyncio.SubprocessError(
            cmd, process.returncode, stderr.decode().strip()
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
        print(textwrap.dedent(
            """\
            Command Output:\n
            {}""".format(output)
        ))

    except asyncio.CancelledError as e:
        print(textwrap.dedent(
            """\
            Command execution timed out."""
        ))
        sys.exit(1)

    except ValueError as e:
        print(textwrap.dedent(
            """\
            Error: {}\n
            Usage: python3 script.py [command]""".format(e)
        ))
        sys.exit(1)

    except asyncio.SubprocessError as e:
        print(textwrap.dedent(
            """\
            Error running command "{}":\n
            {}""".format(e.cmd, e.stderr)
        ))
        sys.exit(e.returncode)
