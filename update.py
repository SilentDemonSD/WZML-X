import os
import pathlib
import subprocess
from typing import Any, Optional

import pymongo
from pydantic import BaseModel
from requests import get

from dotenv import load_dotenv, dotenv_values

# Load environment variables from .env file
load_dotenv()

# Logging configuration
log_fmt = "[%(asctime)s] [%(levelname)s] - %(message)s"
date_fmt = "%d-%b-%y %I:%M:%S %p"
handlers = [logging.FileHandler("log.txt"), logging.StreamHandler()]
basicConfig(format=log_fmt, datefmt=date_fmt, handlers=handlers, level=logging.INFO)

class Config(BaseModel):
    UPSTREAM_REPO: Optional[str] = None
    UPSTREAM_BRANCH: Optional[str] = "master"

class Database(BaseModel):
    DATABASE_URL: Optional[str] = None

def get_env_var(var_name: str, default: Any = None) -> Any:
    """Get the value of an environment variable, or return a default value if it's not set."""
    return os.getenv(var_name, default)

def is_true(val: str) -> bool:
    """Check if a string is truthy."""
    return val.lower() in ["true", "yes", "t"]

def update_repository() -> None:
    """Update the repository with the latest commits from the upstream repository."""
    upstream_repo = get_env_var("UPSTREAM_REPO")
    upstream_branch = get_env_var("UPSTREAM_BRANCH")

    if not upstream_repo:
        log_error("UPSTREAM_REPO variable is missing! Exiting now")
        exit(1)

    if not upstream_branch:
        upstream_branch = "master"

    if os.path.exists(".git"):
        subprocess.run(["rm", "-rf", ".git"], check=True)

    subprocess.run(
        [
            "git init -q && git config --global user.email doc.adhikari@gmail.com && git config --global user.name weebzone && git add . && git commit -sm update -q && git remote add origin {} && git fetch origin -q && git reset --hard origin/{} -q".format(
                upstream_repo, upstream_branch
            )
        ],
        shell=True,
        check=True,
    )

    repo = upstream_repo.split("/")
    upstream_repo = "https://github.com/{}".format("/".join(repo[-2:]))

    log_info("Successfully updated with latest commits !!")
    log_error(f"UPSTREAM_REPO: {upstream_repo} | UPSTREAM_BRANCH: {upstream_branch}")

if __name__ == "__main__":
    bot_token = get_env_var("BOT_TOKEN")
    if not bot_token:
        log_error("BOT_TOKEN variable is missing! Exiting now")
        exit(1)

    bot_id = bot_token.split(":")[0]

    database_url = get_env_var("DATABASE_URL")
    if not database_url:
        database_url = None

    if database_url is not None:
        conn = pymongo.MongoClient(database_url)
        db = conn.wzmlx
        old_config = db.settings.deployConfig.find_one({"_id": bot_id})
        config_dict = db.settings.config.find_one({"_id": bot_id})

        if old_config is not None:
            del old_config["_id"]

        if (
            old_config is not None
            and old_config == dotenv_values("config.env")
            or old_config is None
        ) and config_dict is not None:
            os.environ["UPSTREAM_REPO"] = config_dict["UPSTREAM_REPO"]
            os.environ["UPSTREAM_BRANCH"] = config_dict["UPSTREAM_BRANCH"]

        conn.close()

    config = Config(UPSTREAM_REPO=os.getenv("UPSTREAM_REPO"), UPSTREAM_BRANCH=os.getenv("UPSTREAM_BRANCH"))
    update_repository()
