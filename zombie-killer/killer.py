# coding=utf-8
import pickle
import re

from selenium import webdriver

# Followers page.
url = "http://weibo.cn/3205389480/fans?rightmod=1&wvr=6"

cap = webdriver.DesiredCapabilities.PHANTOMJS
cap["phantomjs.page.settings.resourceTimeout"] = 1000
cap["phantomjs.page.settings.loadImages"] = False
cap["phantomjs.page.settings.disk-cache"] = True
# Load cookies.
cookies = pickle.load(open("cookies.pkl", "rb"))
cookies_str = ';'.join('%s=%s' % (name, val) for name, val in cookies.items())
cap["phantomjs.page.customHeaders.Cookie"] = cookies_str

driver = webdriver.PhantomJS(
    executable_path="./phantomjs", desired_capabilities=cap)
driver.set_window_size(1120, 1000000)

driver.get(url)

links = driver.find_elements_by_link_text(u'移除')
for link in links:
    href = link.get_attribute('href')
    uid = re.findall('uid=([0-9]*)', href)
    if uid:
        uid = uid[0]
    print uid
    if uid == 'dfkaldjf':
        link.click()  # Remove. TODO: Needs confirmation.

# if diver.find_element_by_link_text("下一页"):
#    pass
# else:
#     time.sleep(1)
