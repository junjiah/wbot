# coding=utf-8
import logging
import pickle
import re
import sched
from collections import namedtuple

import grequests
import time

from model import Follower

if not Follower.table_exists():
    Follower.create_table()

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(
    filename='log/info_fetcher.log', level=logging.INFO, format=FORMAT)
# Suppress other logging.
for k in logging.Logger.manager.loggerDict:
    logging.getLogger(k).setLevel(logging.WARNING)

# Load cookies.
cookies = pickle.load(open('data/cookies.pkl', 'rb'))
cookies_str = ';'.join('%s=%s' % (name, val) for name, val in cookies.items())
info_url = 'http://weibo.cn/u/{}'.format

HEADERS = {
    'Cookie': cookies_str
}
WEIBO_PATTERN = u'微博\[(\d+)\]'
FOLLOWER_PATTERN = u'粉丝\[(\d+)\]'
SCHEDULE_INTERVAL = 60 * 5  # 5 min.
CONCURRENT_CONN = 15


def fetch_follower_info(scheduler):
    uids = Follower.get_unfilled_uids()
    info = namedtuple('Info', ['uid', 'weibo_count', 'follower_count'])
    if uids:
        follower_info_list, persist_thresh = [], 100
        for i in range(0, len(uids), CONCURRENT_CONN):
            sub_uid_list = uids[i:i + CONCURRENT_CONN]
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

                        follower_info_list.append(info(
                            uid, weibo_cnt, follower_cnt))
                        logging.info(
                            '%s Weibo Count: %d, Follower Count: %d' % (
                                uid, weibo_cnt, follower_cnt))

                        if len(follower_info_list) > persist_thresh:
                            Follower.save_follower_info(follower_info_list)
                            logging.info('Persisted %d follower info entries' %
                                         len(follower_info_list))
                            follower_info_list = []
                    else:
                        logging.warn('Failed to get info of user %s' % uid)
            except Exception:
                logging.exception('Exception for retrieving user info')
                continue

        # Persist remaining list of info.
        if follower_info_list:
            Follower.save_follower_info(follower_info_list)
            logging.info('Persisted %d follower info entries' %
                         len(follower_info_list))
    else:
        logging.error('No UIDs provided. Wait for next time')

    # Schedule next task.
    logging.info('Schedule next fetching')
    scheduler.enter(
        SCHEDULE_INTERVAL, 1, fetch_follower_info, (scheduler,))


if __name__ == '__main__':
    # Schedule the job.
    s = sched.scheduler(time.time, time.sleep)
    logging.info('Start first fetching')
    s.enter(0, 1, fetch_follower_info, (s,))
    s.run()
