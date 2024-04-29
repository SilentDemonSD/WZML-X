import os
import logging
import subprocess
import pkg_resources
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO,
)

# Load environment variables from .env file
load_dotenv('config.env', override=True)

# Check for a specific environment variable and exit if it exists
if os.getenv('_____REMOVE_THIS_LINE_____', False):
    logging.error('The README.md file should be read! Exiting now!')
    exit()

# Get the bot token from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logging.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(':', 1)[0]

# Get the database URL from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')

# Connect to the database if the URL is provided
if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.wzmlx
    old_config = db.settings.deployConfig.find_one({'_id': bot_id})
    config_dict = db.settings.config.find_one({'_id': bot_id})

    # Check if the old configuration exists and matches the current environment variables
    if old_config:
        del old_config['_id']
    if (old_config == dict(dict(os.environ)) if old_config else True) and config_dict:
        # Set environment variables from the configuration dictionary
        for k, v in config_dict.items():
            os.environ[k] = v
    conn.close()

# Upgrade installed packages
if os.getenv('UPGRADE_PACKAGES', 'False').lower() == 'true':
    packages = [dist.project_name for dist in pkg_resources.working_set]
    subprocess.call(["pip", "install"] + packages, shell=True)

# Get the UPSTREAM_REPO and UPSTREAM_BRANCH environment variables
UPSTREAM_REPO = os.getenv('UPSTREAM_REPO')
UPSTREAM_BRANCH = os.getenv('UPSTREAM_BRANCH', 'master')

# If UPSTREAM_REPO is provided, perform Git-related tasks
if UPSTREAM_REPO:
    if os.path.exists('.git'):
        subprocess.run(["rm", "-rf", ".git"], check=True)

    # Clone the repository, set up the local Git repository, and pull the latest changes
    subprocess.run(
        [
            "git", "init", "-q",
            "&&", "git", "config", "--global", "user.email", "doc.adhikari@gmail.com",
            "&&", "git", "config", "--global", "user.name", "weebzone",
            "&&", "git", "add", ".",
            "&&", "git", "commit", "-sm", "update", "-q",
            "&&", "git", "remote", "add", "origin", UPSTREAM_REPO,
            "&&", "git", "fetch", "origin", "-q",
            "&&", "git", "reset", "--hard", f"origin/{UPSTREAM_BRANCH}", "-q"
        ],
        shell=True,
        check=True,
    )

    repo = UPSTREAM_REPO.split('/')
    UPSTREAM_REPO = f"https://github.com/{repo[-2]}/{repo[-1]}"
