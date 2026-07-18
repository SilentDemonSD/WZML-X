from asyncio import run
from hashlib import sha256
from importlib import import_module
from logging import ERROR, INFO, FileHandler, StreamHandler, basicConfig, getLogger
from os import environ, path, remove
from os.path import isdir
from shutil import rmtree
from subprocess import call as scall
from subprocess import run as srun
from sys import exit

getLogger("pymongo").setLevel(ERROR)

_LOGGER = getLogger("update")
_DB_PARTITION_SALT = b"wzmlx_v3_db_partition_salt"

_VAR_LIST = [
    "BOT_TOKEN",
    "TELEGRAM_API",
    "TELEGRAM_HASH",
    "OWNER_ID",
    "DATABASE_URL",
    "BASE_URL",
    "UPSTREAM_REPO",
    "UPSTREAM_BRANCH",
]


def _get_version():
    try:
        return import_module("bot.version").get_version()
    except Exception:
        return "unknown"


def _setup_logging():
    if path.exists("log.txt"):
        with open("log.txt", "w"):
            pass
    if path.exists("rlog.txt"):
        remove("rlog.txt")
    basicConfig(
        format="[%(asctime)s] [%(levelname)s] - %(message)s",
        datefmt="%d-%b-%y %I:%M:%S %p",
        handlers=[FileHandler("log.txt"), StreamHandler()],
        level=INFO,
    )


def _load_config():
    try:
        settings = import_module("config")
        config_file = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in vars(settings).items()
            if not key.startswith("__")
        }
    except ModuleNotFoundError:
        _LOGGER.info("Config.py file is not Added! Checking ENVs..")
        config_file = {}
    env_updates = {key: environ[key].strip() for key in _VAR_LIST if key in environ}
    if env_updates:
        _LOGGER.info("Config data is updated with ENVs!")
        config_file.update(env_updates)
    return config_file


def _db_partition_id(bot_id):
    raw = sha256(_DB_PARTITION_SALT + str(bot_id).encode()).hexdigest()
    return f"p_{raw[:24]}"


async def _fetch_db_config(database_url, db_part, collection="config"):
    try:
        from pymongo import AsyncMongoClient
        from pymongo.server_api import ServerApi
    except ImportError:
        scall("uv pip install pymongo", shell=True)
        from pymongo import AsyncMongoClient
        from pymongo.server_api import ServerApi
    conn = AsyncMongoClient(database_url, server_api=ServerApi("1"))
    try:
        return await conn.wzmlx.settings[collection].find_one(
            {"_id": db_part}, {"_id": 0}
        )
    except Exception as e:
        _LOGGER.error(f"Database ERROR: {e}")
        return None
    finally:
        await conn.close()


def _fetch_config_from_db(config_file, db_part):
    database_url = config_file.get("DATABASE_URL", "").strip()
    if not database_url:
        return

    db_config = run(_fetch_db_config(database_url, db_part))
    if db_config is None:
        _LOGGER.warning("No saved config found in MongoDB, using defaults")
        return

    old_config = run(_fetch_db_config(database_url, db_part, collection="deployConfig"))
    env_keys = {k: config_file[k] for k in _VAR_LIST if k in environ}

    if old_config is not None and old_config != config_file:
        merged = dict(config_file)
        for k, v in db_config.items():
            if k in old_config and config_file.get(k) is not None:
                if old_config.get(k) == config_file.get(k):
                    merged[k] = v
            elif k not in merged or merged[k] is None:
                merged[k] = v
        config_file.clear()
        config_file.update(merged)
        _LOGGER.info("Config: config.py changed, takes priority over MongoDB")
    else:
        merged = dict(config_file)
        if db_config:
            merged.update(db_config)
        config_file.clear()
        config_file.update(merged)
        _LOGGER.info(
            "Config imported from MongoDB"
            if old_config is not None
            else "Config: first deploy, config.py fills gaps from MongoDB"
        )
    config_file.update(env_keys)


def _run_update(upstream_repo, upstream_branch, version):
    if not upstream_repo:
        _LOGGER.info("No UPSTREAM_REPO set, skipping git update")
        return
    if path.exists(".git"):
        srun(["rm", "-rf", ".git"])
    git_cmds = [
        ["git", "init", "-q"],
        [
            "git",
            "config",
            "--global",
            "user.email",
            "105407900+SilentDemonSD@users.noreply.github.com",
        ],
        ["git", "config", "--global", "user.name", "SilentDemonSD"],
        ["git", "add", "."],
        ["git", "commit", "-sm", "update", "-q"],
        ["git", "remote", "add", "origin", upstream_repo],
        ["git", "fetch", "origin", "-q"],
        ["git", "reset", "--hard", f"origin/{upstream_branch}", "-q"],
    ]
    for cmd in git_cmds:
        result = srun(cmd)
        if result.returncode != 0:
            break
    display_repo = "/".join(upstream_repo.split("/")[-2:])
    if result and result.returncode == 0:
        _LOGGER.info("Successfully updated with Latest Updates!")
    else:
        _LOGGER.error("Something went Wrong! Recheck your details or Ask Support!")
    _LOGGER.info(
        f"UPSTREAM_REPO: {display_repo} | UPSTREAM_BRANCH: {upstream_branch} | VERSION: {version}"
    )


def _update_packages():
    scall("uv pip install -U -r requirements.txt", shell=True)
    _LOGGER.info("Successfully Updated all the Packages!")


def _cleanup():
    for d in ["gen_scripts", ".github"]:
        if isdir(d):
            rmtree(d, ignore_errors=True)
    for f in ["README.md", "LICENSE", "Dockerfile", "docker-compose.yml"]:
        if path.exists(f):
            remove(f)


def main():
    _setup_logging()
    config_file = _load_config()
    version = _get_version()
    bot_token = config_file.get("BOT_TOKEN", "")
    if not bot_token:
        _LOGGER.error("BOT_TOKEN variable is missing! Exiting now")
        exit(1)
    _fetch_config_from_db(config_file, _db_partition_id(bot_token.split(":", 1)[0]))
    upstream_repo = config_file.get("UPSTREAM_REPO", "").strip()
    upstream_branch = config_file.get("UPSTREAM_BRANCH", "").strip() or "wzv3"
    _run_update(upstream_repo, upstream_branch, version)
    _cleanup()
    _update_packages()


if __name__ == "__main__":
    main()
