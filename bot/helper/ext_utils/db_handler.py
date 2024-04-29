#!/usr/bin/env python3
import asyncio
import os

import aiofiles
from aiofiles.os import path as aiopath, makedirs
from aiofiles import open as aiopen
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from dotenv import dotenv_values

from bot import (
    DATABASE_URL,
    user_data,
    rss_dict,
    LOGGER,
    bot_id,
    config_dict,
    aria2_options,
    qbit_options,
    bot_loop,
)


class DbManager:
    def __init__(self):
        self.__err = False
        self.__db = None
        self.__connect()

    async def __connect(self):
        try:
            self.__conn = await AsyncIOMotorClient(DATABASE_URL).connect()
            self.__db = self.__conn["wzmlx"]
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.__err = True

    async def db_load(self):
        if self.__err:
            return

        await self.__load_settings()
        await self.__load_users()
        await self.__load_rss()

    async def __load_settings(self):
        settings_collection = self.__db.settings

        await settings_collection.config.update_one(
            {"_id": bot_id}, {"$set": config_dict}, upsert=True
        )

        aria2c_options = {"_id": bot_id, **aria2_options}
        await settings_collection.aria2c.update_one(
            {"_id": bot_id}, {"$set": aria2c_options}, upsert=True
        )

        qbittorrent_options = {"_id": bot_id, **qbit_options}
        await settings_collection.qbittorrent.update_one(
            {"_id": bot_id}, {"$set": qbittorrent_options}, upsert=True
        )

    async def __load_users(self):
        users_collection = self.__db.users

        async for row in users_collection[bot_id].find():
            user_id = row["_id"]
            del row["_id"]

            thumb_path = f'Thumbnails/{user_id}.jpg'
            rclone_path = f'rclone/{user_id}.conf'

            if row.get("thumb"):
                if not await aiopath.exists("Thumbnails"):
                    await makedirs("Thumbnails")

                async with aiopen(thumb_path, "wb+") as f:
                    await f.write(row["thumb"])

                row["thumb"] = thumb_path

            if row.get("rclone"):
                if not await aiopath.exists("rclone"):
                    await makedirs("rclone")

                async with aiopen(rclone_path, "wb+") as f:
                    await f.write(row["rclone"])

                row["rclone"] = rclone_path

            user_data[user_id] = row

        LOGGER.info("Users data has been imported from Database")

    async def __load_rss(self):
        rss_collection = self.__db.rss

        async for row in rss_collection[bot_id].find():
            user_id = row["_id"]
            del row["_id"]
            rss_dict[user_id] = row

        LOGGER.info("Rss data has been imported from Database.")

    async def update_deploy_config(self):
        if self.__err:
            return

        current_config = dict(dotenv_values("config.env"))
        await self.__db.settings.deployConfig.replace_one(
            {"_id": bot_id}, current_config, upsert=True
        )

    async def update_config(self, dict_):
        if self.__err:
            return

        await self.__db.settings.config.update_one({"_id": bot_id}, {"$set": dict_}, upsert=True)

    async def update_aria2(self, key, value):
        if self.__err:
            return

        await self.__db.settings.aria2c.update_one(
            {"_id": bot_id}, {"$set": {key: value}}, upsert=True
        )

    async def update_qbittorrent(self, key, value):
        if self.__err:
            return

        await self.__db.settings.qbittorrent.update_one(
            {"_id": bot_id}, {"$set": {key: value}}, upsert=True
        )

    async def update_private_file(self, path):
        if self.__err:
            return

        if await aiopath.exists(path):
            async with aiopen(path, "rb+") as pf:
                pf_bin = await pf.read()
        else:
            pf_bin = b""

        path = path.replace(".", "__")
        await self.__db.settings.files.update_one(
            {"_id": bot_id}, {"$set": {path: pf_bin}}, upsert=True
        )

        if path == "config.env":
            await self.update_deploy_config()

    async def update_user_data(self, user_id):
        if self.__err:
            return

        data = user_data[user_id]
        if data.get("thumb"):
            del data["thumb"]
        if data.get("rclone"):
            del data["rclone"]

        await self.__db.users[bot_id].replace_one({"_id": user_id}, data, upsert=True)

    async def update_user_doc(self, user_id, key, path=""):
        if self.__err:
            return

        if path:
            async with aiopen(path, "rb+") as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = b""

        await self.__db.users[bot_id].update_one(
            {"_id": user_id}, {"$set": {key: doc_bin}}, upsert=True
        )

    async def get_pm_uids(self):
        if self.__err:
            return []

        return [doc["_id"] async for doc in self.__db.pm_users[bot_id].find({})]

    async def update_pm_users(self, user_id):
        if self.__err:
            return

        if not bool(await self.__db.pm_users[bot_id].find_one({"_id": user_id})):
            await self.__db.pm_users[bot_id].insert_one({"_id": user_id})
            LOGGER.info(f"New PM User Added : {user_id}")

    async def rm_pm_user(self, user_id):
        if self.__err:
            return

        await self.__db.pm_users[bot_id].delete_one({"_id": user_id})

    async def rss_update_all(self):
        if self.__err:
            return

        for user_id in list(rss_dict.keys()):
            await self.__db.rss[bot_id].replace_one({"_id": user_id}, rss_dict[user_id], upsert=True)

    async def rss_update(self, user_id):
        if self.__err:
            return

        await self.__db.rss[bot_id].replace_one({"_id": user_id}, rss_dict[user_id], upsert=True)

    async def rss_delete(self, user_id):
        if self.__err:
            return

        await self.__db.rss[bot_id].delete_one({"_id": user_id})

    async def add_incomplete_task(self, cid, link, tag, msg_link, msg):
        if self.__err:
            return

        await self.__db.tasks[bot_id].insert_one(
            {"_id": link, "cid": cid, "tag": tag, "source": msg_link, "org_msg": msg}
        )

    async def rm_complete_task(self, link):
        if self.__err:
            return

        await self.__db.tasks[bot_id].delete_one({"_id": link})

    async def get_incomplete_tasks(self):
        notifier_dict = {}

        if self.__err:
            return notifier_dict

        if await self.__db.tasks[bot_id].find_one():
            rows = self.__db.tasks[bot_id].find({})
            async for row in rows:
                if row["cid"] in list(notifier_dict.keys()):
                    if row["tag"] in list(notifier_dict[row["cid"]]):
                        notifier_dict[row["cid"]][row["tag"]].append(
                            {row["_id"]: row["source"]}
                        )
                    else:
                        notifier_dict[row["cid"]][row["tag"]] = [
                            {row["_id"]: row["source"]}
                        ]
                else:
                    notifier_dict[row["cid"]] = {row["tag"]: [{row["_id"]: row["source"]}]}

        await self.__db.tasks[bot_id].drop()

        return notifier_dict

    async def trunc_table(self, name):
        if self.__err:
            return

        await self.__db[name][bot_id].drop()


if DATABASE_URL:
    bot_loop.run_until_complete(DbManager().db_load())
