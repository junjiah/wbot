# coding=utf-8
import logging
import os
import pickle
import re
import sys
import time
from contextlib import contextmanager

import peewee
from selenium import webdriver

db = peewee.SqliteDatabase('fan_uids.db')
db.connect()


class UID(peewee.Model):
    uid = peewee.CharField()

    class Meta:
        database = db


try:
    db.create_table(UID)
except peewee.OperationalError:
    # Table already exists.
    pass

logging.basicConfig(filename='uid_fetcher.log', level=logging.INFO)

# Load cookies and configure phantomjs.
cookies = pickle.load(open("cookies.pkl", "rb"))
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
def get_driver():
    driver = webdriver.PhantomJS(
        executable_path="./phantomjs")
    driver.set_window_size(1120, 1000000)
    yield driver
    driver.quit()


class RemoveZombieException(Exception):
    pass


def get_fan_uids_in_a_page(pager):
    remove_links = pager.find_elements_by_link_text(u'移除')
    if not remove_links:
        raise RemoveZombieException('No Remove links')

    uids = []
    for link in remove_links:
        href = link.get_attribute('href')
        uid = re.findall('uid=([0-9]*)', href)
        if not uid:
            msg = 'UID not found in link: ' + href
            logging.warning(msg)
            continue
        logging.info('Got UID: ' + uid[0])
        uids.append(uid[0])
    return uids


uids_to_persist = []
UIDS_PERSIST_THRESHOLD = 100


def persist_uids(uids):
    global uids_to_persist
    uids_to_persist.extend(uids)
    if len(uids_to_persist) >= UIDS_PERSIST_THRESHOLD:
        d = [{'uid': uid} for uid in uids_to_persist]
        with db.atomic():
            UID.insert_many(d).execute()
        logging.info('Persisted %d UIDs' % len(uids_to_persist))
        uids_to_persist = []


if __name__ == '__main__':
    my_uid = os.getenv('WEIBO_UID')
    if not my_uid:
        logging.error('No UID provided')
        sys.exit(1)

    follower_url = 'http://weibo.cn/{}/fans?rightmod=1&wvr=6'.format(my_uid)

    PAGE_NUM = 101
    FIND_NEXT_RETRY = 3

    uids = []

    url = follower_url
    for i in range(PAGE_NUM):
        with get_driver() as pager:
            pager.get(url)
            try:
                uids_in_page = get_fan_uids_in_a_page(pager)
                if uids_in_page:
                    persist_uids(uids_in_page)
            except RemoveZombieException as e:
                logging.exception(unicode(e))

            for _ in range(FIND_NEXT_RETRY):
                try:
                    links = pager.find_elements_by_link_text(u'下页')
                    if not links:
                        raise Exception('Could\'nt find next page link')
                    next_page = links[0]
                    # Set next page URL.
                    url = next_page.get_attribute('href')
                except Exception as e:
                    logging.exception(unicode(e))
                    logging.info('Retry after a second')
                    time.sleep(1)
                else:
                    logging.info('Go to next page: %d' % (i + 1))
                    break
            else:
                msg = 'Failed to find next page for %d times, exit' \
                      % FIND_NEXT_RETRY
                break

    # Persist remaining list of UIDs.
    with db.atomic():
        UID.insert_many([{'uid': uid} for uid in uids_to_persist]).execute()
