# coding=utf-8
import logging
import pickle
import sched
from itertools import izip

import grequests
import time

from model import Follower

if not Follower.table_exists():
    Follower.create_table()

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(
    filename='log/killer.log', level=logging.INFO, format=FORMAT)
# Suppress other logging.
for k in logging.Logger.manager.loggerDict:
    logging.getLogger(k).setLevel(logging.WARNING)

# Load cookies.
cookies = pickle.load(open('data/cookies.pkl', 'rb'))
cookies_str = ';'.join('%s=%s' % (name, val) for name, val in cookies.items())
remove_url = 'http://weibo.cn/attention/remove?act=removec&uid={}&st={}'.format

HEADERS = {
    'Cookie': cookies_str
}
SCHEDULE_INTERVAL = 60  # 1 min.
ZOMBIE_KILL_LIMIT = 5000
CONCURRENT_CONN = 15


def get_st():
    try:
        with open('data/st.pkl', 'r') as f:
            st = pickle.load(f)
        return st
    except Exception:
        return None


def kill_zombies(scheduler):
    st = get_st()
    uids = Follower.get_zombie_uids(limit=ZOMBIE_KILL_LIMIT)
    if uids and st:
        logging.info('Try to delete %d zombie followers' % len(uids))
        for i in range(0, len(uids), CONCURRENT_CONN):
            sub_uid_list = uids[i:i + CONCURRENT_CONN]
            concurrent_reqs = [
                grequests.get(
                    remove_url(uid, st), headers=HEADERS,
                    allow_redirects=False)
                for uid in sub_uid_list
            ]
            resp_list = grequests.map(concurrent_reqs)

            deleted_uids = [
                uid for uid, resp in izip(sub_uid_list, resp_list)
                if resp.status_code == 200
            ]
            # Record back to DB about deleted UIDs.
            if deleted_uids:
                Follower.confirm_uid_deleted(deleted_uids)
                logging.info('Confirmed deletion of %d uids' % len(deleted_uids))
    else:
        logging.error(
            'Failed to necessary data, st: %s, uid length: %d' %
            (st, len(uids)))

    # Schedule next task.
    logging.info('Schedule next fetching')
    scheduler.enter(
        SCHEDULE_INTERVAL, 1, kill_zombies, (scheduler,))


if __name__ == '__main__':
    # Schedule the job.
    s = sched.scheduler(time.time, time.sleep)
    logging.info('Start first fetching')
    s.enter(0, 1, kill_zombies, (s,))
    s.run()
