import time
from YSUNetAuthTools import YSUNetAuth
from logs import log
import parse

import datetime

ysuAuth = YSUNetAuth()
users = parse.getUsersFromFile("users.ini")


def loginUser(users):
    for user in users:
        supports = user["support"].split(",")
        supports = [x for x in supports if int(x) in range(4)]

        for support in supports:
            re = ysuAuth.login(user["num"], user["password"], support)
            if re[0]:
                print("[", datetime.datetime.now(), "]", "连接", re)
                break
            else:
                print("[", datetime.datetime.now(), "]", parse.netTypeToString(support) + "失败")


while True:

    if not ysuAuth.tst_net():
        print("[", datetime.datetime.now(), "]", "Not Connect!!!!!")
        loginUser(users)
    else:
        print("[", datetime.datetime.now(), "]", "connected!")
    print("-----------------------------------------------------")
    time.sleep(10)
