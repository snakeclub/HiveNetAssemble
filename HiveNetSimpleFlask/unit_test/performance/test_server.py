#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试服务器
@module test_server
@file test_server.py
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


def server_flask_no_paraller():
    """
    原生启动，无并行参数
    """
    _server = FlaskServer(
        'flask_no_paraller', server_config={
            'flask_run': {
                'port': 5000,
                'threaded': False,
                'processes': 1
            },
            'use_wsgi': False
        }
    )
    _server.add_service('/', index)
    _server.start(is_asyn=False)


def server_flask_threaded():
    """
    原生启动，多线程
    """
    _server = FlaskServer(
        'flask_no_paraller', server_config={
            'flask_run': {
                'port': 5000,
                'threaded': True,
                'processes': 1
            },
            'use_wsgi': False
        }
    )
    _server.add_service('/', index)
    _server.start(is_asyn=False)


def server_flask_processes():
    """
    原生启动，多进程
    """
    _server = FlaskServer(
        'flask_no_paraller', server_config={
            'flask_run': {
                'port': 5000,
                'threaded': False,
                'processes': 4
            },
            'use_wsgi': False
        }
    )
    _server.add_service('/', index)
    _server.start(is_asyn=False)


def server_wsgi():
    """
    使用wsgi服务
    """
    _server = FlaskServer(
        'flask_no_paraller', server_config={
            'flask_run': {
                'port': 5000
            },
            'use_wsgi': True
        }
    )
    _server.add_service('/', index)
    _server.start(is_asyn=False)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 压测参数: locust -f req_locust_script.py --host http://127.0.0.1:5000 -u 10000 -r 10
    # 结果: 请求数 失败数 平均响应时长（毫秒） 最小响应时长（毫秒） 最大响应时长（毫秒） 平均收取大小（byte） TPS 失败率（笔/秒）
    # flask_no_paraller: 107	0	49337	1011	97729	3	1.0	0.0
    # flask_threaded: 5271	0	1022	1002	1071	3	88.3	0.0
    # flask_processes: 412	0	21302	1018	25505	3	3.9	0.0
    # wsgi: 111122	0	1019	1000	1202	3	671.8	0.0
    para = RunTool.get_kv_opts()
    if para.get('type', '') == 'flask_no_paraller':
        # python test_server.py type=flask_no_paraller
        server_flask_no_paraller()
    if para.get('type', '') == 'flask_threaded':
        # python test_server.py type=flask_threaded
        server_flask_threaded()
    if para.get('type', '') == 'flask_processes':
        # python test_server.py type=flask_processes
        server_flask_processes()
    if para.get('type', '') == 'wsgi':
        # python test_server.py type=wsgi
        server_wsgi()
    else:
        raise AttributeError('not support type!')
