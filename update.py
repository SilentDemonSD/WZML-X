# Import necessary modules
from logging import FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info
from os import path as ospath, environ, remove
from subprocess import run as srun, call as scall
from pkg_resources import working_set
from requests import get as rget
from dotenv import load_dotenv, dotenv_values
from pymongo import MongoClient

# Check for existing log files and clear/remove them
if ospath.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

if ospath.exists('rlog.txt'):
    remove('rlog.txt')

# Configure logging
basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s",
            datefmt="%d-%b-%y %I:%M:%S %p",
            handlers=[FileHandler('log.txt'), StreamHandler()],
            level=INFO)

# Load environment variables from .env file
load_dotenv('config.env', override=True)

# Check for a specific environment variable and exit if it exists
try:
    if bool(environ.get('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

# Get the bot token from environment variables
BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    log_error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

# Get the bot ID from the bot token
bot_id = BOT_TOKEN.split(':', 1)[0]

# Get the database URL from environment variables
DATABASE_URL = environ.get('DATABASE_URL', '')
if len(DATABASE_URL) == 0:
    DATABASE_URL = None

# Connect to the database if the URL is provided
if DATABASE_URL is not None:
    conn = MongoClient(DATABASE_URL)
    db = conn.wzmlx
    old_config = db.settings.deployConfig.find_one({'_id': bot_id})
    config_dict = db.settings.config.find_one({'_id': bot_id})

    # Check if the old configuration exists and matches the current environment variables
    if old_config is not None:
        del old_config['_id']
    if (old_config is not None and old_config == dict(dotenv_values('config.env')) or old_config is None) \
            and config_dict is not None:
        # Set environment variables from the configuration dictionary
        environ['UPSTREAM_REPO'] = config_dict['UPSTREAM_REPO']
        environ['UPSTREAM_BRANCH'] = config_dict['UPSTREAM_BRANCH']
        environ['UPGRADE_PACKAGES'] = config_dict.get('UPDATE_PACKAGES', 'False')
    conn.close()

# Get the UPGRADE_PACKAGES environment variable
UPGRADE_PACKAGES = environ.get('UPGRADE_PACKAGES', 'False') 
if UPGRADE_PACKAGES.lower() == 'true':
    # Upgrade installed packages
    packages = [dist.project_name for dist in working_set]
    scall("pip install " + ' '.join(packages), shell=True)

# Get the UPSTREAM_REPO and UPSTREAM_BRANCH environment variables
UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')
if len(UPSTREAM_BRANCH) == 0:
    UPSTREAM_BRANCH = 'master'

# If UPSTREAM_REPO is provided, perform Git-related tasks
if UPSTREAM_REPO is not None:
    if ospath.exists('.git'):
        srun(["rm", "-rf", ".git"])

    # Clone the repository, set up the local Git repository, and pull the latest changes
    update = srun([f"git init -q \
                     && git config --global user.email doc.adhikari@gmail.com \
                     && git config --global user.name weebzone \
                     && git add . \
                     && git commit -sm update -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q"], shell=True)

    repo = UPSTREAM_REPO.split('/')
    UPSTREAM_REPO = f"https://github.com/{repo[-2
