# coding=utf-8
import logging
import pickle
import re

from contextlib import contextmanager

from joblib import Parallel, delayed
from selenium import webdriver

# Logging.
logging.basicConfig(filename='killer.log',level=logging.INFO)

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

def construct_remove_url(uid, st):
    return 'http://weibo.cn/attention/remove?act=removec&uid={}&st={}' \
        .format(uid, st)

def remove_zombie(remove_url, uid):
    with get_driver() as remover:
        try:
            remover.get(remove_url)
        except Exception as e:
            return 'Failed to remove %s, because of: %s' % (uid, str(e))
        else:
            return 'Deleted %s' % uid

class RemoveZombieException(Exception):
    pass

def remove_zombies_in_one_page(pager):
    remove_links = pager.find_elements_by_link_text(u'移除')
    if not remove_links:
        raise RemoveZombieException('No Remove links')

    # Get mysterious 'st'.
    link = remove_links[0]
    href = link.get_attribute('href')
    st = re.findall('st=(.*$)', href)
    if not st:
        raise RemoveZombieException('Mysterious "st" not found in link')
    st = st[0]

    remove_urls, uids = [], []
    for link in remove_links:
        href = link.get_attribute('href')
        uid = re.findall('uid=([0-9]*)', href)
        if not uid:
            msg = 'UID not found in link: ' + href
            logging.warning(msg)
            continue
        uid = uid[0]
        uids.append(uid)
        remove_urls.append(construct_remove_url(uid, st))

    res = Parallel(n_jobs=len(uids))(
        delayed(remove_zombie)(url, uid) for url, uid in zip(remove_urls, uids))
    for msg in res:
        logging.info(msg)


if __name__ == '__main__':
    follower_url = "http://weibo.cn/3205389480/fans?rightmod=1&wvr=6"

    PAGE_NUM = 10
    FIND_NEXT_RETRY = 3

    with get_driver() as pager:
        pager.get(follower_url)

        for i in range(PAGE_NUM):
            try:
                remove_zombies_in_one_page(pager)
            except RemoveZombieException as e:
                logging.exception(str(e))

            for _ in range(FIND_NEXT_RETRY):
                try:
                    next_page = pager.find_element_by_link_text(u'下页')
                    pager.get(next_page.get_attribute('href'))
                except Exception as e:
                    logging.exception(str(e))
                    logger.info('Retry after a second')
                    time.sleep(1)
                else:
                    logging.info('Go to next page: %d' % (i + 1))
                    break
            else:
                msg = 'Failed to find next page for %d times, exit' \
                    % FIND_NEXT_RETRY
                raise Exception(msg)
