# -*- coding: utf-8 -*-
import random
import os
import time
import threading
import datetime

import apptime
# from YSUNetAuthTools import YSUNetAuth
import YSUNetAuthTools
import parse_user

from dingtalk import DingTalk

import program_logs

import parseDingTalkJson
import config

import time_p
import ntp
import ntp_hosts

restartFilename = "restart.ysuauth"
if config.isFileExist(restartFilename):
    program_logs.print1('\t\t\t\t\t程序重启。')
    os.remove(restartFilename)

program_logs.print1('程序开始运行')

docker_status = config.isFileExist("docker_status")

dt = DingTalk()

if dt.getFromENV():
    program_logs.print1("从ENV中获取钉钉配置成功！")
else:
    extraPath = ""
    if docker_status:
        extraPath = "/ysuauth/settings/"
    dt.getFromFiles(extraPath)

delayTime = 10

my_ntp_hosts_class = ntp_hosts.ntp_hosts()
my_ntp_hosts_class.initFile()
my_ntp_hosts = my_ntp_hosts_class.getHosts()


# print("hosts")
# print(hosts)


class dingTalkThread(threading.Thread):
    def __init__(self, time, type=False, ntp_hosts=None, threadPool=None):
        threading.Thread.__init__(self)
        self.time = time
        self.type = type
        self.ntp_hosts = ntp_hosts
        self.threadPool = threadPool

    def run(self):
        nowtime = datetime.datetime.now()
        program_logs.print1("\t\t\t启动钉钉发信线程({})："
                            .format(datetime.datetime.strftime(nowtime, '%Y年%m月%d日 %H:%M:%S'))
                            + self.name)
        typeStr = "连接成功"

        if not self.type:
            msg_dict = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "联网成功",
                    "text": "#### 连网时间 @全体成员 \n > 联网时间为{}\n"
                            " > ![icon](https://lxy.ysu.edu.cn/images/lxy/bottom_logo.gif)\n > ###### {} 发送\n"
                            "[燕山大学网络](http://auth.ysu.edu.cn) \n".format(self.time, nowtime)
                },
                "at": {
                    "isAtAll": True
                }
            }
        else:
            typeStr = "断网时间"
            msg_dict = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "断网时间",
                    "text": "#### 断网时间 @全体成员 \n > 断网时间为{}\n"
                            " > ![icon](https://lxy.ysu.edu.cn/images/lxy/bottom_logo.gif)\n > ###### {} 发送\n"
                            "[燕山大学网络](http://auth.ysu.edu.cn) \n".format(self.time, nowtime)
                },
                "at": {
                    "isAtAll": True
                }
            }
        program_logs.print1(
            "\t\t\t延时{}秒后发送{}{}的消息！"
                .format(str(delayTime), self.time, typeStr)
        )
        time.sleep(delayTime)
        program_logs.print1(
            "\t\t\t延时完毕开始发送{}{}的消息！"
                .format(self.time, typeStr)
        )
        ok = False
        while not ok:
            try:
                if self.ntp_hosts is not None and len(self.ntp_hosts) != 0:
                    t = ntp.ntp_getTimeStamp(self.ntp_hosts)
                    program_logs.print1("NTP TIMESTAMP:{}".format(str(t)))
                else:
                    t = 0
                dt.getUrl(timestamp=t)
                f = dt.sendMsg(msg_dict)
                program_logs.print1("DingTalk Response:" + f.text)
            except Exception as e:
                # print(msg_dict)
                program_logs.print1(repr(e))
                program_logs.print1("发送出错，等待20s后再次发送。", True)
                time.sleep(20)
                raise e
            else:
                if f != None and len(f.text) != 0:
                    jsonStr = str(f.text)
                    ok = parseDingTalkJson.isDingTalkOk(jsonStr)
                    if not ok:
                        if parseDingTalkJson.testDingTalkError(jsonStr, "too fast"):
                            time.sleep(60 + random.randint(10, 30))
                        elif parseDingTalkJson.testDingTalkError(jsonStr, "invalid timestamp"):
                            dt.getUrl()

                else:
                    program_logs.print1("取不到返回吗？！", True)
                    ok = True

        nowtime = datetime.datetime.now()
        program_logs.print1("\t\t\t退出钉钉发信线程({})："
                            .format(datetime.datetime.strftime(nowtime, '%Y年%m月%d日 %H:%M:%S'))
                            + self.name)
        if self.threadPool is not None:
            self.threadPool.remove(self)


# YSUNetAuthTools.YSUNetAuth
ysuAuth = YSUNetAuthTools.YSUNetAuth()

users = []
users1 = parse_user.getUsersFromEnv()
if users1 is None:
    program_logs.print1("No any users in Env!")
else:
    users += users1
    program_logs.print1("从ENV中获取user列表成功！获取到{}个"
                        .format(len(users1)))
iniPath = "users.ini"
if docker_status:
    iniPath = "/ysuauth/settings/" + iniPath
users1 = parse_user.getUsersFromFile(iniPath)
if users1 is None:
    program_logs.print1("No any users!", True)
else:
    users += users1
    program_logs.print1("从File中获取user列表成功！获取到{}个"
                        .format(len(users1)))
program_logs.print1(users)
program_logs.print1("获取完毕！共计获取到{}个"
                    .format(len(users)))
if len(users) == 0:
    program_logs.print1("致命错误--未获取到任何用户！", True)
    exit(1)


def loginUser(users):
    for user in users:
        supports = user["support"].split(",")
        supports = [x for x in supports if int(x) in range(4)]

        for support in supports:
            re = ysuAuth.login(user["num"], user["password"], support)
            if re[0]:
                program_logs.print1("连接" + str(re))
                break
            else:
                program_logs.print1(parse_user.netTypeToString(support) + "失败(" + re[1] + ")"
                                    , True)


last = -1
disConnectedTime = ""
threadPool = []
if __name__ == "__main__":
    while True:

        now = datetime.datetime.now()
        hour = now.hour
        dayOfWeek = now.isoweekday()
        inYsuWeekend_Normal = dayOfWeek == 5 or dayOfWeek == 6
        inYsuWeekend_Holiday = (dayOfWeek == 5 and apptime.isInTime((6, 1), (23, 59))) \
                               or dayOfWeek == 6 \
                               or (dayOfWeek == 7 and apptime.isInTime((0, 0), (23, 25)))
        inYsuWeekend = inYsuWeekend_Holiday
        inWorkTime_weekday = (not inYsuWeekend) and apptime.isInTime((6, 1), (23, 28))
        inWorkTime_weekend = inYsuWeekend and apptime.isInTime((6, 1), (23, 59))
        inWorkTime = inWorkTime_weekday or inWorkTime_weekend
        if not inWorkTime:
            if last == 1:
                # 还是检测一下吧，免得一晚log全是这个！
                program_logs.print1("不在工作时间！")
                last = 4
            # 防止时间出错，晚上间隔长一点，但是不会不让连接
            if last != 2:
                time.sleep(60)

        if not ysuAuth.tst_net():
            program_logs.print1("Not Connect!!!!!")
            if last == 2:
                disConnectedTime = \
                    datetime.datetime.strftime(now, '%Y年%m月%d日 %H:%M:%S')
            if last != 4 and last != 1:
                last = 1
            loginUser(users)
        else:
            if last != 2:
                program_logs.print1("Turn to connected!")
                program_logs \
                    .asynchronismPrintThread("Turn to connected!",
                                             my_ntp_hosts
                                             )

                ntp_timestamp = ntp.ntp_getTimeStamp(my_ntp_hosts)
                if ntp_timestamp == 0:
                    ntp_time_str = "???有毒吧？？？\n凭什么获取不到？？？"
                    program_logs.print1("NTP时间获取出错！！！")
                    program_logs.print1(ntp_time_str)
                    program_logs.print1("my_ntp_hosts")
                    program_logs.print1(my_ntp_hosts)
                    last = 1
                else:
                    ntp_time_str = \
                        datetime.datetime.fromtimestamp(ntp_timestamp) \
                            .strftime("%Y年%m月%d日 %H:%M:%S")

                thread = \
                    dingTalkThread(
                        datetime.datetime.strftime(now, '%Y年%m月%d日 %H:%M:%S')
                        + "\n NTP时间为：" + ntp_time_str
                        ,
                        False,
                        my_ntp_hosts,
                        threadPool
                        # None
                    )
                thread.start()
                threadPool.append(thread)
            last = 2
            if len(disConnectedTime) != 0:
                thread = \
                    dingTalkThread(disConnectedTime, True, my_ntp_hosts, threadPool)
                thread.start()
                threadPool.append(thread)
                disConnectedTime = ""

        if config.isFileExist("restart.ysuauth"):
            program_logs.print1("检测到重启程序指令。")
            program_logs.print1("跳出检测循环。")
            program_logs.print1("-----------------------------------------------------")
            break

        time.sleep(10)
