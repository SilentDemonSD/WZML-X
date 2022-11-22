from os import path as ospath, makedirs
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from bot import DB_URI, user_data, rss_dict, botname, LOGGER


class DbManger:
    def __init__(self):
        self.__err = False
        self.__db = None
        self.__conn = None
        self.__connect()

    def __connect(self):
        try:
            self.__conn = MongoClient(DB_URI)
            self.__db = self.__conn.mltb
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.__err = True

    def db_load(self):
        if self.__err:
            return
        # User Data
        if self.__db.users.find_one():
            rows = self.__db.users.find({})  # return a dict ==> {_id, is_sudo, is_auth, as_media, as_doc, thumb}
            for row in rows:
                uid = row['_id']
                del row['_id']
                path = f"Thumbnails/{uid}.jpg"
                if row.get('thumb'):
                    if not ospath.exists('Thumbnails'):
                        makedirs('Thumbnails')
                    with open(path, 'wb+') as f:
                        f.write(row['thumb'])
                    row['thumb'] = True
                user_data[uid] = row
            LOGGER.info("Users data has been imported from Database")
        # Rss Data
        if self.__db.rss.find_one():
            rows = self.__db.rss.find({})  # return a dict ==> {_id, link, last_feed, last_name, filters}
            for row in rows:
                title = row['_id']
                del row['_id']
                rss_dict[title] = row
            LOGGER.info("Rss data has been imported from Database.")
        self.__conn.close()

    def update_user_data(self, user_id):
        if self.__err:
            return
        data = user_data[user_id]
        if data.get('thumb'):
            del data['thumb']
        self.__db.users.update_one({'_id': user_id}, {'$set': data}, upsert=True)
        self.__conn.close()

    def update_thumb(self, user_id, path=None):
        if self.__err:
            return
        if path is not None:
            image = open(path, 'rb+')
            image_bin = image.read()
        else:
            image_bin = False
        self.__db.users.update_one({'_id': user_id}, {'$set': {'thumb': image_bin}}, upsert=True)
        self.__conn.close()

    def update_userval(self, user_id, data, value=None):
        if self.__err:
            return
        if value is not None:
            dbval = value
        else:
            dbval = False
        self.__db.users.update_one({'_id': user_id}, {'$set': {data: dbval}}, upsert=True)
        self.__conn.close()

    def rss_update(self, title):
        if self.__err:
            return   
        self.__db.rss.update_one({'_id': title}, {'$set': rss_dict[title]}, upsert=True)
        self.__conn.close()

    def rss_delete(self, title):
        if self.__err:
            return
        self.__db.rss.delete_one({'_id': title})
        self.__conn.close()

    def add_incomplete_task(self, cid, link, tag):
        if self.__err:
            return
        self.__db.tasks[botname].insert_one({'_id': link, 'cid': cid, 'tag': tag})
        self.__conn.close()

    def rm_complete_task(self, link):
        if self.__err:
            return
        self.__db.tasks[botname].delete_one({'_id': link})
        self.__conn.close()

    def get_incomplete_tasks(self):
        notifier_dict = {}
        if self.__err:
            return notifier_dict
        if self.__db.tasks[botname].find_one():
            rows = self.__db.tasks[botname].find({})  # return a dict ==> {_id, cid, tag}
            for row in rows:
                if row['cid'] in list(notifier_dict.keys()):
                    if row['tag'] in list(notifier_dict[row['cid']]):
                        notifier_dict[row['cid']][row['tag']].append(row['_id'])
                    else:
                        notifier_dict[row['cid']][row['tag']] = [row['_id']]
                else:
                    usr_dict = {row['tag']: [row['_id']]}
                    notifier_dict[row['cid']] = usr_dict
        self.__db.tasks[botname].drop()
        self.__conn.close()
        return notifier_dict # return a dict ==> {cid: {tag: [_id, _id, ...]}}

    def trunc_table(self, name):
        if self.__err:
            return
        self.__db[name].drop()
        self.__conn.close()

if DB_URI is not None:
    DbManger().db_load()






    

#     def user_auth(self, chat_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif not self.user_check(chat_id):
#             sql = 'INSERT INTO users (uid, auth) VALUES ({}, TRUE)'.format(chat_id)
#         else:
#             sql = 'UPDATE users SET auth = TRUE WHERE uid = {}'.format(chat_id)
#         self.cur.execute(sql)
#         self.conn.commit()
#         self.disconnect()
#         return 'Authorized successfully'

#     def user_unauth(self, chat_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif self.user_check(chat_id):
#             sql = 'UPDATE users SET auth = FALSE WHERE uid = {}'.format(chat_id)
#             self.cur.execute(sql)
#             self.conn.commit()
#             self.disconnect()
#             return 'Unauthorized successfully'

#     def user_addsudo(self, user_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif not self.user_check(user_id):
#             sql = 'INSERT INTO users (uid, sudo) VALUES ({}, TRUE)'.format(user_id)
#         else:
#             sql = 'UPDATE users SET sudo = TRUE WHERE uid = {}'.format(user_id)
#         self.cur.execute(sql)
#         self.conn.commit()
#         self.disconnect()
#         return 'Successfully Promoted as Sudo'

#     def user_rmsudo(self, user_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif self.user_check(user_id):
#             sql = 'UPDATE users SET sudo = FALSE WHERE uid = {}'.format(user_id)
#             self.cur.execute(sql)
#             self.conn.commit()
#             self.disconnect()
#             return 'Successfully removed from Sudo'

#     def user_addpaid(self, user_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif not self.user_check(user_id):
#             sql = 'INSERT INTO users (uid, paid) VALUES ({}, TRUE)'.format(user_id)
#         else:
#             sql = 'UPDATE users SET paid = TRUE WHERE uid = {}'.format(user_id)
#         self.cur.execute(sql)
#         self.conn.commit()
#         self.disconnect()
#         return 'Successfully Promoted as Paid Member'

#     def user_rmpaid(self, user_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif self.user_check(user_id):
#             sql = 'UPDATE users SET paid = FALSE WHERE uid = {}'.format(user_id)
#             self.cur.execute(sql)
#             self.conn.commit()
#             self.disconnect()
#             return 'Successfully removed from Paid Membership'

#     def addleech_log(self, chat_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif not self.user_check(chat_id):
#             sql = 'INSERT INTO users (uid, leechlog) VALUES ({}, TRUE)'.format(chat_id)
#         else:
#             sql = 'UPDATE users SET leechlog = TRUE WHERE uid = {}'.format(chat_id)
#         self.cur.execute(sql)
#         self.conn.commit()
#         self.disconnect()
#         return 'Successfully added to leech logs'

#     def rmleech_log(self, chat_id: int):
#         if self.err:
#             return "Error in DB connection, check log for details"
#         elif self.user_check(chat_id):
#             sql = 'UPDATE users SET leechlog = FALSE WHERE uid = {}'.format(chat_id)
#             self.cur.execute(sql)
#             self.conn.commit()
#             self.disconnect()
#             return 'Removed from leech logs successfully'

#     def user_check(self, uid: int):
#         self.cur.execute("SELECT * FROM users WHERE uid = {}".format(uid))
#         res = self.cur.fetchone()
#         return res
