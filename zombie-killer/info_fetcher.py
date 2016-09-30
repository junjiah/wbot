# coding=utf-8
import logging
import pickle
import re

import grequests
import peewee
import sys

info_db = peewee.SqliteDatabase('fan_info.db')
info_db.connect()
uid_db = peewee.SqliteDatabase('fan_uids.db')
uid_db.connect()


class UID(peewee.Model):
    uid = peewee.CharField()

    class Meta:
        database = uid_db


class FanInfo(peewee.Model):
    uid = peewee.CharField()
    weibo_count = peewee.IntegerField()
    follower_count = peewee.IntegerField()

    class Meta:
        database = info_db


try:
    info_db.create_table(FanInfo)
except peewee.OperationalError:
    # Table already exists.
    pass

logging.basicConfig(filename='info_fetcher.log', level=logging.INFO)

# Load cookies.
cookies = pickle.load(open("cookies.pkl", "rb"))
cookies_str = ';'.join('%s=%s' % (name, val) for name, val in cookies.items())

HEADERS = {
    'Cookie': cookies_str
}

WEIBO_PATTERN = u'微博\[(\d+)\]'
FOLLOWER_PATTERN = u'粉丝\[(\d+)\]'


def get_uids(source):
    if source == 'db':
        return [uid.uid for uid in UID.select()]

    # Suppose it's a file.
    with open(source, 'r') as f:
        uids = map(str.strip, f.readlines())
    return uids


def info_url(uid):
    return 'http://weibo.cn/u/{}'.format(uid)


info_to_persist = []
INFO_PERSIST_THRESHOLD = 100


def persist_fan_info(info):
    global info_to_persist
    info_to_persist.append(info)
    if len(info_to_persist) >= INFO_PERSIST_THRESHOLD:
        with info_db.atomic():
            FanInfo.insert_many(info_to_persist).execute()
        logging.info('Persisted info for %d user(s)' % len(info_to_persist))
        info_to_persist = []


if __name__ == '__main__':
    uids = get_uids('db')
    if not uids:
        logging.error('No UIDs provided. Exit')
        sys.exit(1)

    CONCURRENT_CONNECTION_NUM = 20
    for i in range(0, len(uids), CONCURRENT_CONNECTION_NUM):
        sub_uid_list = uids[i:i+CONCURRENT_CONNECTION_NUM]
        concurrent_reqs = [
            grequests.get(info_url(uid), headers=HEADERS)
            for uid in sub_uid_list
        ]
        resp_list = grequests.map(concurrent_reqs)

        try:
            for uid, resp in zip(sub_uid_list, resp_list):
                matches = re.findall(
                    u'%s.*%s' % (WEIBO_PATTERN, FOLLOWER_PATTERN), resp.text)
                if matches:
                    weibo_cnt, follower_cnt = map(int, matches[0])
                    persist_fan_info({
                        'uid': uid,
                        'weibo_count': weibo_cnt,
                        'follower_count': follower_cnt
                    })
                    logging.info(
                        '%s Weibo Count: %d, Follower Count: %d' % (
                            uid, weibo_cnt, follower_cnt))
        except Exception:
            logging.exception('Exception for retrieving user info')
            continue

    # Persist remaining list of info.
    with info_db.atomic():
        FanInfo.insert_many(info_to_persist).execute()