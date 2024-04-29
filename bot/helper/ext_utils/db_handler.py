import os
import typing as t
from pymongo import MongoClient, PyMongoError

from bot import DATABASE_URL, user_data, rss_dict, LOGGER, bot_id, config_dict, aria2_options, qbit_options

class DbManager:
    def __init__(self):
        self.__err = False
        self.__db = None
        self.__conn = None
        self.__connect()

    def __connect(self):
        try:
            self.__conn = MongoClient(DATABASE_URL)
            self.__db = self.__conn.mltb
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.__err = True

    def disconnect(self):
        if self.__conn:
            self.__conn.close()
            self.__conn = None
            self.__db = None

    def db_load(self):
        if self.__err:
            return
        try:
            # Save bot settings
            self.__db.settings.config.update_one({'_id': bot_id}, {'$set': config_dict}, upsert=True)
            # Save Aria2c options
            aria2_doc = self.__db.settings.aria2c.find_one({'_id': bot_id})
            if aria2_doc is None:
                self.__db.settings.aria2c.update_one({'_id': bot_id}, {'$set': aria2_options}, upsert=True)
            # Save qbittorrent options
            qbit_doc = self.__db.settings.qbittorrent.find_one({'_id': bot_id})
            if qbit_doc is None:
                self.__db.settings.qbittorrent.update_one({'_id': bot_id}, {'$set': qbit_options}, upsert=True)
            # User Data
            if self.__db.users.find_one():
                rows = self.__db.users.find({})  # return a dict ==> {_id, is_sudo, is_auth, as_doc, thumb}
                for row in rows:
                    uid = row['_id']
                    del row['_id']
                    path = f"Thumbnails/{uid}.jpg"
                    if row.get('thumb'):
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, 'wb+') as f:
                            f.write(row['thumb'])
                        row['thumb'] = path
                    user_data[uid] = row
                LOGGER.info("Users data has been imported from Database")
            # Rss Data
            if self.__db.rss[bot_id].find_one():
                rows = self.__db.rss[bot_id].find({})  # return a dict ==> {_id, link, last_feed, last_name, filters}
                for row in rows:
                    title = row['_id']
                    del row['_id']
                    rss_dict[title] = row
                LOGGER.info("Rss data has been imported from Database.")
        except Exception as e:
            LOGGER.error(f"Error in db_load: {e}")
            self.__err = True

    def update_config(self, dict_: dict) -> None:
        if self.__err:
            return
        self.__db.settings.config.update_one({'_id': bot_id}, {'$set': dict_}, upsert=True)
        self.__conn.close()

    def update_aria2(self, key: str, value: t.Any) -> None:
        if self.__err:
            return
        self.__db.settings.aria2c.update_one({'_id': bot_id}, {'$set': {key: value}}, upsert=True)
        self.__conn.close()

    def update_qbittorrent(self, key: str, value: t.Any) -> None:
        if self.__err:
            return
        self.__db.settings.qbittorrent.update_one({'_id': bot_id}, {'$set': {key: value}}, upsert=True)
        self.__conn.close()


    def update_private_file(self, path: str) -> None:
        if self.__err:
            return
        if os.path.exists(path):
            with open(path, 'rb+') as pf:
                pf_bin = pf.read()
        else:
            pf_bin = b''
        path = path.replace('.', '__')
        self.__db.settings.files.update_one({'_id': bot_id}, {'$set': {path: pf_bin}}, upsert=True)
        self.__conn.close()

    def update_user_data(self, user_id: str) -> None:
        if self.__err:
            return
        data = user_data.get(user_id)
        if data and data.get('thumb'):
            del data['thumb']
        self.__db.users.update_one({'_id': user_id}, {'$set': data}, upsert=True)
        self.__conn.close()

    def update_thumb(self, user_id: str, path: str = None) -> None:
        if self.__err:
            return
        if path is not None:
            with open(path, 'rb+') as image:
                image_bin = image.read()
        else:
            image_bin = b''
        self.__db.users.update_one({'_id': user_id}, {'$set': {'thumb': image_bin}}, upsert=True)
        self.__conn.close()

    def update_userval(self, user_id: str, data: str, value: t.Any = None) -> None:
        if self.__err:
            return
        if value is not None:
            dbval = value
        else:
            dbval = False
        self.__db.users.update_one({'_id': user_id}, {'$set': {data: dbval}}, upsert=True)
        self.__conn.close()

    def rss_update(self, title: str) -> None:
        if self.__err:
            return   
        self.__db.rss[bot_id].update_one({'_id': title}, {'$set': rss_dict[title]}, upsert=True)
        self.__conn.close()

    def rss_delete(self, title: str) -> None:
        if self.__err:
            return
        self.__db.rss[bot_id].delete_one({'_id': title})
        self.__conn.close()

    def add_incomplete_task(self, cid: str, link: str, tag: str) -> None:
        if self.__err:
            return
        self.__db.tasks[bot_id].insert_one({'_id': link, 'cid': cid, 'tag': tag})
        self.__conn.close()

    def rm_complete_task(self, link: str) -> None:
        if self.__err:
            return
        self.__db.tasks[bot_id].delete_one({'_id': link})
        self.__conn.close()

    def get_incomplete_tasks(self) -> dict:
        notifier_dict = {}
        if self.__err:
            return notifier_dict
        if self.__db.tasks[bot_id].find_one():
            rows = self.__db.tasks[bot_id].find({})  # return a dict ==> {_id, cid, tag}
            for row in rows:
                if row['cid'] in list(notifier_dict.keys()):
                    if row['tag'] in list(notifier_dict[row['cid']]):
                        notifier_dict[row['cid']][row['tag']].append(row['_id'])
                    else:
                        notifier_dict[row['cid']][row['tag']] = [row['_id']]
                else:
                    usr_dict = {row['tag']: [row['_id']]}
                    notifier_dict[row['cid']] = usr_dict
        self.__db.tasks[bot_id].drop()
        self.__conn.close()
        return notifier_dict # return a dict ==> {cid: {tag: [_id, _id, ...]}}

    def trunc_table(self, name: str) -> None:
        if self.__err:
            return
        self.__db[name][bot_id].drop()
        self.__conn.close()

if DATABASE_URL:
    db_manager = DbManager()
    db_manager.db_load()
    # use db_manager to interact with the database
    db_manager.disconnect()
