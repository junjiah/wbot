# coding=utf-8
import grequests
import logging
import pickle
import re
import requests
import time

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

construct_remove_url = \
    'http://weibo.cn/attention/remove?act=removec&uid={uid}&st={st}'.format


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
        remove_urls.append(construct_remove_url(uid=uid, st=st))

    gets = [
        grequests.get(url, headers={
            'Cookie': cookies_str
        }) for url in remove_urls
    ]
    resp_list = grequests.map(gets, size=5)  # Throttling.
    for resp in resp_list:
        if resp.status_code == requests.codes.ok:
            logging.info('Succeeded')
        else:
            logging.error(
                'Failed for %s' % (resp.status_code + ':' + resp.text))


if __name__ == '__main__':
    follower_url = "http://weibo.cn/3205389480/fans?rightmod=1&wvr=6"

    PAGE_NUM = 10
    FIND_NEXT_RETRY = 3

    url = follower_url
    for i in range(PAGE_NUM):
        with get_driver() as pager:
            pager.get(url)

            try:
                remove_zombies_in_one_page(pager)
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
                raise Exception(msg)
