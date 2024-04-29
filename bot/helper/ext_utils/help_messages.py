# This code contains help messages for various commands supported by the bot.
# The help messages are used to provide users with information on how to use the commands.

# Dictionary to store help messages for various commands
help_messages = {
    "yt_download": {
        # Help message for YouTube download command
        "description": "Download videos or audio from YouTube",
        "usage": "yt_download <URL> [<start_time>] [<end_time>] [--audio] [--video-format <format>]",
        "examples": [
            "yt_download https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "yt_download https://www.youtube.com/watch?v=dQw4w9WgXcQ 10:20 12:30 --audio",
            "yt_download https://www.youtube.com/watch?v=dQw4w9WgXcQ --video-format 1080p"
        ]
    },
    "mirror": {
        # Help message for mirror command
        "description": "Create a mirror link for a file or folder",
        "usage": "mirror <file/folder path> <destination path>",
        "examples": [
            "mirror /path/to/file /path/to/destination",
            "mirror /path/to/folder /path/to/destination"
        ]
    },
    "rss_feed": {
        # Help message for RSS feed command
        "description": "Generate an RSS feed for a website or search query",
        "usage": "rss_feed <URL or search query>",
        "examples": [
            "rss_feed https://www.example.com",
            "rss_feed 'iphone 13 pro max'"
        ]
    },
    "clone": {
        # Help message for clone command
        "description": "Clone a repository or project",
        "usage": "clone <repository URL> <destination path>",
        "examples": [
            "clone https://github.com/username/repo.git /path/to/destination",
            "clone git@github.com:username/repo.git /path/to/destination"
        ]
    },
    "category": {
        # Help message for category command
        "description": "Manage categories for tasks and reminders",
        "usage": "category [list | create <name> | delete <name> | rename <old_name> <new_name>]",
        "examples": [
            "category list",
            "category create Personal",
            "category delete Work",
            "category rename Personal Home"
        ]
    }
}

# Default settings for the bot
default_settings = {
    "download_location": {
        "name": "Download location",
        "description": "The default location to save downloaded files"
    },
    "max_concurrent_downloads": {
        "name": "Max concurrent downloads",
        "description": "The maximum number of files that can be downloaded simultaneously"
    },
    "mirror_directory_structure": {
        "name": "Mirror directory structure",
        "description": "Whether to preserve the directory structure when mirroring files"
    }
}

# Error message for password-protected links
password_error_message = (
    "This link requires a password. "
    "Please provide the password in the following format: `{password}`"
)
