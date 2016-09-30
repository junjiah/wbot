# -*- coding: utf-8 -*-
# From https://github.com/xchaoinfo/fuck-login/blob/master/003%20weibo.cn/m.weibo.cn.py
import base64
import json
import math
import os
import pickle
import random
import time
from urllib import quote_plus

import requests
from PIL import Image

agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36'
global headers
headers = {
    "Host": "passport.weibo.cn",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    'User-Agent': agent
}

session = requests.session()

index_url = "https://passport.weibo.cn/signin/login"
session.get(index_url, headers=headers)


def get_su(username):
    """
    对 email 地址和手机号码 先 javascript 中 encodeURIComponent
    对应 Python 3 中的是 urllib.parse.quote_plus
    然后在 base64 加密后decode
    """
    username_quote = quote_plus(username)
    username_base64 = base64.b64encode(username_quote.encode("utf-8"))
    return username_base64.decode("utf-8")


def login_pre(username):
    params = {
        "checkpin": "1",
        "entry": "mweibo",
        "su": get_su(username),
        "callback": "jsonpcallback" + str(int(time.time() * 1000) + math.floor(random.random() * 100000))
    }
    pre_url = "https://login.sina.com.cn/sso/prelogin.php"
    headers["Host"] = "login.sina.com.cn"
    headers["Referer"] = index_url
    pre = session.get(pre_url, params=params, headers=headers)
    if True:
        js = json.loads(pre.text)
        if js["showpin"] == 1:
            headers["Host"] = "passport.weibo.cn"
            capt = session.get("https://passport.weibo.cn/captcha/image", headers=headers)
            capt_json = capt.json()
            capt_base64 = capt_json['data']['image'].split("base64,")[1]
            with open('capt.jpg', 'wb') as f:
                f.write(base64.b64decode(capt_base64))
                f.close()
            im = Image.open("capt.jpg")
            im.show()
            cha_code = input("请输入验证码\n>")
            return cha_code, capt_json['data']['pcid']
        else:
            return ""


def login(username, password, pincode):
    postdata = {
        "username": username,
        "password": password,
        "savestate": "1",
        "ec": "0",
        "pagerefer": "",
        "entry": "mweibo",
        "wentry": "",
        "loginfrom": "",
        "client_id": "",
        "code": "",
        "qq": "",
        "hff": "",
        "hfp": "",
    }
    if pincode == "":
        pass
    else:
        postdata["pincode"] = pincode[0]
        postdata["pcid"] = pincode[1]
    headers["Host"] = "passport.weibo.cn"
    headers["Reference"] = index_url
    headers["Origin"] = "https://passport.weibo.cn"
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    post_url = "https://passport.weibo.cn/sso/login"
    login = session.post(post_url, data=postdata, headers=headers)
    js = login.json()
    crossdomain = js["data"]["crossdomainlist"]
    cn = "https:" + crossdomain["sina.com.cn"]
    headers["Host"] = "login.sina.com.cn"
    session.get(cn, headers=headers)
    headers["Host"] = "weibo.cn"
    with open('cookies.pkl', 'w') as f:
        pickle.dump(requests.utils.dict_from_cookiejar(session.cookies), f)


if __name__ == "__main__":
    username = os.getenv('WEIBO_USERNAME')
    password = os.getenv('WEIBO_PASSWORD')
    code = login_pre(username)
    login(username, password, code)
