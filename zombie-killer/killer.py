# coding=utf-8
import pickle
import re

from contextlib import contextmanager

from selenium import webdriver

# Load cookies.
cookies = pickle.load(open("cookies.pkl", "rb"))
cookies_str = ';'.join('%s=%s' % (name, val) for name, val in cookies.items())

# Followers page at first.
url = "http://weibo.cn/3205389480/fans?rightmod=1&wvr=6"

@contextmanager
def get_new_page(url):

    def get_driver():
        cap = webdriver.DesiredCapabilities.PHANTOMJS
        cap["phantomjs.page.settings.resourceTimeout"] = 1000
        cap["phantomjs.page.settings.loadImages"] = False
        cap["phantomjs.page.settings.disk-cache"] = True
        cap["phantomjs.page.customHeaders.Cookie"] = cookies_str

        driver = webdriver.PhantomJS(
            executable_path="./phantomjs", desired_capabilities=cap)
        driver.set_window_size(1120, 1000000)
        return driver

    driver = get_driver()
    driver.get(url)
    yield driver
    driver.quit()

for _ in range(30):  # TODO: first 30 pages.
    with get_new_page(url) as follower_page:
        links = follower_page.find_elements_by_link_text(u'移除')
        for link in links:
            href = link.get_attribute('href')
            uid = re.findall('uid=([0-9]*)', href)
            if uid:
                uid = uid[0]
            if uid:
                with get_new_page(href) as confirm_remove_page:
                    l = confirm_remove_page.find_element_by_link_text(u'确定')
                    with get_new_page(l.get_attribute('href')) as remove_page:
                        print 'Deleted ' + uid

        next_page = follower_page.find_element_by_link_text(u'下页')
        url = next_page.get_attribute('href')
