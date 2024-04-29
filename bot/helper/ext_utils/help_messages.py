# This code contains help messages and default settings for various commands supported by the bot.

# Dictionary to store help messages for various commands
help_messages = {
    "yt_download": {
        "description": "Download videos or audio from YouTube.",
        "usage": "yt_download <URL> [<start_time>] [<end_time>] [--audio] [--video-format <format>]",
        "examples": [
            "yt_download https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "yt_download https://www.youtube.com/watch?v=dQw4w9WgXcQ 10:20 12:30 --audio",
            "yt_download https://www.youtube.com/watch?v=dQw4w9WgXcQ --video-format 1080p"
        ]
    },
    # ... other commands ...
}

# Default settings for the bot
DEFAULT_SETTINGS = {
    "download_location": {
        "name": "Download location",
        "description": "The default location to save downloaded files.",
        "value": "~/Downloads"
    },
    "max_concurrent_downloads": {
        "name": "Max concurrent downloads",
        "description": "The maximum number of files that can be downloaded simultaneously.",
        "value": 3
    },
    "mirror_directory_structure": {
        "name": "Mirror directory structure",
        "description": "Whether to preserve the directory structure when mirroring files.",
        "value": True
    }
}

# Error message for password-protected links
PASSWORD_ERROR_MESSAGE = (
    "This link requires a password. "
    "Please provide the password in the following format: `{password}`"
)

def get_command_help(command):
    """Return the help message for a given command."""
    return help_messages.get(command, {}).get("help", {})

def get_default_setting(setting):
    """Return the default value for a given setting."""
    return DEFAULT_SETTINGS.get(setting, {}).get("value")

