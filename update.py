import os
import logging
import subprocess
import pkg_resources
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO,
)

load_dotenv('config.env', override=True)

MISSING_ENV_VAR = '_____REMOVE_THIS_LINE_____'
if MISSING_ENV_VAR in os.environ:
    logging.error('The README.md file should be read! Exiting now!')
    exit()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logging.error("BOT_TOKEN variable is missing! Exiting now")
    exit(1)

bot_id = BOT_TOKEN.split(':', 1)[0]
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    client = MongoClient(DATABASE_URL)
    db = client.wzmlx
    old_config = db.settings.deployConfig.find_one({'_id': bot_id})
    config_dict = db.settings.config.find_one({'_id': bot_id})

    if old_config and old_config != dict(os.environ):
        for k, v in old_config.items():
            if k in os.environ:
                os.environ[k] = v

    if config_dict:
        for k, v in config_dict.items():
            if k not in os.environ:
                os.environ[k] = v

    client.close()

UPGRADE_PACKAGES = os.getenv('UPGRADE_PACKAGES', 'False').lower() == 'true'
if UPGRADE_PACKAGES:
    packages = [dist.project_name for dist in pkg_resources.working_set]
    subprocess.call(["pip", "install"] + packages, shell=True)

UPSTREAM_REPO = os.getenv('UPSTREAM_REPO')
UPSTREAM_BRANCH = os.getenv('UPSTREAM_BRANCH', 'master')

if UPSTREAM_REPO:
    if not os.path.exists('.git'):
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-sm", "update", "-q"], check=True)

    subprocess.run(
        [
            "git", "remote", "add", "origin", UPSTREAM_REPO,
            "&&", "git", "fetch", "origin", "-q",
            "&&", "git", "reset", "--hard", f"origin/{UPSTREAM_BRANCH}", "-q"
        ],
        shell=True,
        check=True,
    )

    repo = UPSTREAM_REPO.split('/')
    UPSTREAM_REPO = f"https://github.com/{repo[-2]}/{repo[-1]}"
