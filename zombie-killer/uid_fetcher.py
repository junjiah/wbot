# coding=utf-8
import logging
import os
import pickle
import re
import sched
import time
from contextlib import contextmanager

from selenium import webdriver

from model import Follower

if not Follower.table_exists():
    Follower.create_table()

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(
    filename='log/uid_fetcher.log', level=logging.INFO, format=FORMAT)
# Suppress other logging.
for k in logging.Logger.manager.loggerDict:
    logging.getLogger(k).setLevel(logging.WARNING)


# Fail immediately if not provided.
my_uid = os.environ['WEIBO_UID']

# Load cookies and configure phantomjs.
cookies = pickle.load(open('data/cookies.pkl', 'rb'))
cookies_str = ';'.join('%s=%s' % (name, val) for name, val in cookies.items())
cap = {
    'phantomjs.page.settings.resourceTimeout': 1000,
    'phantomjs.page.settings.loadImages': False,
    'phantomjs.page.settings.disk-cache': True,
    'phantomjs.page.customHeaders.Cookie': cookies_str,
}
for k, v in cap.iteritems():
    webdriver.DesiredCapabilities.PHANTOMJS[k] = v


@contextmanager
def get_pager():
    pager = webdriver.PhantomJS(
        executable_path='./phantomjs')
    pager.set_window_size(1120, 1000000)
    yield pager
    pager.quit()


class RemoveZombieException(Exception):
    pass


# A token used by Sina for follower removal operation.
# Loaded from follower page, then pickle it to be used by other scripts.
st = None

UID_PATTERN = re.compile('uid=([0-9]*)')
ST_PATTERN = re.compile('st=(.*$)')
SCHEDULE_INTERVAL = 60 * 10 * 2  # 20 min.


def get_follower_uids_in_a_page(pager):
    global st
    remove_links = pager.find_elements_by_link_text(u'移除')
    if not remove_links:
        raise RemoveZombieException('No Remove links')

    uids = []
    for link in remove_links:
        href = link.get_attribute('href')
        curr_st = ST_PATTERN.search(href)
        # Update st if found and different from before.
        if curr_st:
            curr_st = curr_st.groups()[0]
            if curr_st != st:
                logging.info('Update st from %s to %s' % (st, curr_st))
                st = curr_st
                with open('data/st.pkl', 'w') as f:
                    pickle.dump(st, f)

        uid = UID_PATTERN.search(href)
        if not uid:
            logging.warning('UID not found in link: ' + href)
            continue
        else:
            uid = uid.groups()[0]
        logging.info('Got UID: ' + uid)
        uids.append(uid)
    return uids


def fetch_uids_from_weibo_cn(scheduler):
    # Params.
    global my_uid
    follower_url = 'http://weibo.cn/{}/fans?rightmod=1&wvr=6'.format(my_uid)
    page_num = 101
    find_next_retry = 3

    uids, persist_thresh = [], 100
    url = follower_url
    for i in xrange(page_num):
        with get_pager() as pager:
            pager.get(url)
            try:
                # Remember the following function also update 'st' token which
                # would be used to to remove followers.
                uids_in_page = get_follower_uids_in_a_page(pager)
                if uids_in_page:
                    uids.extend(uids_in_page)

                if len(uids) >= persist_thresh:
                    Follower.save_uids(uids)
                    logging.info('Persisted %d uids' % len(uids))
                    uids = []
            except RemoveZombieException as e:
                logging.warn(unicode(e))

            for _ in range(find_next_retry):
                try:
                    links = pager.find_elements_by_link_text(u'下页')
                    if not links:
                        raise Exception('Could\'nt find next page link')
                    next_page = links[0]
                    # Set next page URL.
                    url = next_page.get_attribute('href')
                except Exception as e:
                    logging.warn(unicode(e))
                    logging.info('Retry after a second')
                    time.sleep(1)
                else:
                    logging.info('Go to next page: %d' % (i + 1))
                    break
            else:
                msg = 'Failed to find next page for %d times, exit' \
                      % find_next_retry
                logging.warn(msg)
                break

    # Persist remaining list of UIDs.
    if uids:
        logging.info('Persisted %d uids' % len(uids))
        Follower.save_uids(uids)

    # Schedule next task.
    logging.info('Schedule next fetching')
    scheduler.enter(
        SCHEDULE_INTERVAL, 1, fetch_uids_from_weibo_cn, (scheduler,))


if __name__ == '__main__':
    # Schedule the job.
    s = sched.scheduler(time.time, time.sleep)
    logging.info('Start first fetching')
    s.enter(0, 1, fetch_uids_from_weibo_cn, (s,))
    s.run()
