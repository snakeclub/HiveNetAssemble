#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
使用gunicorn服务的模式
@module gunicorn_server
@file gunicorn_server.py

通过以下命令启动：
gunicorn -w 4 -b 0.0.0.0:5000 -k gevent gunicorn_server:app
"""

import sys
import os
import random
from HiveNetCore.utils.run_tool import RunTool
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetSimpleFlask.server import FlaskServer


RANDOM_STR = str(random.randint(0, 1000))


def index():
    """
    主页执行函数
    """
    global RANDOM_STR
    RunTool.sleep(1)  # 阻塞1秒
    print('resp: ' + RANDOM_STR)
    return RANDOM_STR


server = FlaskServer(
    'flask_no_paraller', server_config={
        'flask_run': {
            'port': 5000,
            'threaded': True,
            'processes': 1
        },
        'use_wsgi': False
    }
)
server.add_service('/', index)
app = server.native_app


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 测试结果：183738	0	1108	1000	2146	3	878.4	0.0
    # 需要注意的是多个worker，进程间的变量环境是不一样的，等于开了多个应用
    server.start()
