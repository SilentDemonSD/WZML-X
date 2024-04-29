import os
import logging
import subprocess
import pkg_resources
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO,
)

def load_env_variables() -> None:
    """Load environment variables from a .env file."""
    load_dotenv('config.env', override=True)

def initialize_mongodb_connection(database_url: str) -> MongoClient:
    """Initialize a MongoDB connection."""
    client = MongoClient(database_url)
    return client

def update_environment_variables(client: MongoClient, bot_id: str) -> None:
    """Update the environment variables from the database."""
    db = client.wzmlx
    old_config = db.settings.deployConfig.find_one({'_id': bot_id})
    config_dict = db.settings.config.find_one({'_id': bot_id})

    # Update the environment variables with the ones from the database
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
        subprocess.check_call(["pip", "install"] + packages)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to upgrade packages: {e}")

def update_codebase(upstream_url: str, upstream_branch: str) -> None:
    """Update the codebase from the upstream repository."""
    try:
        subprocess.check_call(
            [
                "git", "remote", "add", "origin", upstream_url,
                "&&", "git", "fetch", "origin", "-q",
                "&&", "git", "reset", "--hard", f"origin/{upstream_branch}", "-q"
            ],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update codebase: {e}")

if __name__ == "__main__":
    # Load environment variables from .env file
    load_env_variables()

    # Check for missing environment variables
    if 'MISSING_ENV_VAR' in os.environ:
        logging.error('The README.md file should be read! Exiting now!')
        exit()

    # Check for BOT_TOKEN
    if not os.getenv('BOT_TOKEN'):
        logging.error("BOT_TOKEN variable is missing! Exiting now")
        exit(1)

    # Initialize MongoDB connection and update environment variables
    bot_id = os.getenv('BOT_TOKEN').split(':', 1)[0]
    DATABASE_URL = os.getenv('DATABASE_URL')

    if DATABASE_URL:
        client = initialize_mongodb_connection(DATABASE_URL)
        update_environment_variables(client, bot_id)

    # Upgrade Python packages if specified
    if os.getenv('UPGRADE_PACKAGES', 'False').lower() == 'true':
        upgrade_packages()

    # Update codebase from the upstream repository if specified
    UPSTREAM_REPO = os.getenv('UPSTREAM_REPO')
    UPSTREAM_BRANCH = os.getenv('UPSTREAM_BRANCH', 'master')

    if UPSTREAM_REPO:
        update_codebase(UPSTREAM_REPO, UPSTREAM_BRANCH)
