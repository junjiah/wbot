# coding=utf-8
import logging
import pickle
import re

from contextlib import contextmanager

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

class RemoveZombieException(Exception):
    pass

def remove_zombies_in_one_page(pager, remover):
    remove_links = pager.find_elements_by_link_text(u'移除')
    if not remove_links:
        raise RemoveZombieException('No Remove links')

    # Get mysterious 'st'.
    link = remove_links[0]
    href = link.get_attribute('href')
    st = re.findall('st=(.*$)', href)
    if not st:
        raise RemoveZombieException('Mysterious "st"" not found in link')
    st = st[0]

    for link in remove_links:
        href = link.get_attribute('href')
        uid = re.findall('uid=([0-9]*)', href)
        if not uid:
            msg = 'UID not found in link: ' + href
            logging.warning(msg)
            continue
        uid = uid[0]
        remove_url = construct_remove_url(uid, st)
        remover.get(remove_url)
        logging.info('Deleted ' + uid)


if __name__ == '__main__':
    follower_url = "http://weibo.cn/3205389480/fans?rightmod=1&wvr=6"

    PAGE_NUM = 10
    FIND_NEXT_RETRY = 3

    with get_driver() as pager, get_driver() as remover:
        pager.get(follower_url)

        for i in range(PAGE_NUM):
            try:
                remove_zombies_in_one_page(pager, remover)
            except RemoveZombieException as e:
                logging.exception(str(e))

            for _ in range(FIND_NEXT_RETRY):
                try:
                    next_page = pager.find_element_by_link_text(u'下页')
                    pager.get(next_page.get_attribute('href'))
                    logging.info('Go to next page: %d' % (i + 1))
                    break
                except Exception as e:
                    logging.exception(str(e))
                    logger.info('Retry after a second')
                    time.sleep(1)
            else:
                msg = 'Failed to find next page for %d times, exit' \
                    % FIND_NEXT_RETRY
                raise Exception(msg)
