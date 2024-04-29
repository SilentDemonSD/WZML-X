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

def load_env_variables(env_file: str) -> None:
    """Load environment variables from a .env file."""
    load_dotenv(env_file, override=True)

def initialize_mongodb_connection(database_url: str) -> MongoClient:
    """Initialize a MongoDB connection."""
    client = MongoClient(database_url)
    return client

def update_environment_variables(client: MongoClient, bot_id: str) -> None:
    """Update the environment variables from the database."""
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

def upgrade_packages() -> None:
    """Upgrade Python packages."""
    packages = [dist.project_name for dist in pkg_resources.working_set]
    try:
        os.system("pip install " + " ".join(pkg for pkg in packages))
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to upgrade packages: {e}")

def update_codebase(upstream_url: str, upstream_branch: str) -> None:
    """Update the codebase from the upstream repository."""
    try:
        subprocess.run(
            [
                "git", "remote", "add", "origin", upstream_url,
                "&&", "git", "fetch", "origin", "-q",
                "&&", "git", "reset", "--hard", f"origin/{upstream_branch}", "-q"
            ],
            shell=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update codebase: {e}")

if __name__ == "__main__":
    load_env_variables('config.env')

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
        client = initialize_mongodb_connection(DATABASE_URL)
        update_environment_variables(client, bot_id)

    UPGRADE_PACKAGES = os.getenv('UPGRADE_PACKAGES', 'False').lower() == 'true'
    if UPGRADE_PACKAGES:
        upgrade_packages()

    UPSTREAM_REPO = os.getenv('UPSTREAM_REPO')
    UPSTREAM_BRANCH = os.getenv('UPSTREAM_BRANCH', 'master')

    if UPSTREAM_REPO:
        update_codebase(UPSTREAM_REPO, UPSTREAM_BRANCH)
