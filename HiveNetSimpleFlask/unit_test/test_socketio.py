#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试SocketIOServer
@module test_socketio
@file test_socketio.py
"""
import sys
import os
import unittest
from HiveNetCore.logging_hivenet import Logger
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetSimpleFlask.server import SocketIOServer
from HiveNetSimpleFlask.client import SocketIOClient


# 日志配置
_logger_config = {
    'conf_file_name': '',
    'logger_name': 'Console',
    'logfile_path': '',
    'config_type': 'JSON_STR',
    'json_str': """{
                "version": 1,
                "disable_existing_loggers": false,
                "formatters": {
                    "simpleFormatter": {
                        "format": "[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
                        "datefmt": "%Y_%m_%d %H:%M:%S"
                    }
                },

                "handlers": {
                    "ConsoleHandler": {
                        "class": "logging.StreamHandler",
                        "level": "DEBUG",
                        "formatter": "simpleFormatter",
                        "stream": "ext://sys.stdout"
                    }
                },

                "loggers": {
                    "Console": {
                        "level": "DEBUG",
                        "handlers": ["ConsoleHandler"]
                    }
                },

                "root": {
                    "level": "DEBUG",
                    "handlers": []
                }
            }
    """,
    'auto_create_conf': False,
    'is_create_logfile_by_day': False,
    'call_fun_level': 0
}


# 日志对象
LOGGER = Logger.create_logger_by_dict(_logger_config)


#############################
# 生命周期执行函数
#############################
async def before_server_start(server):
    print('run before_server_start')


async def after_server_start(server):
    print('run after_server_start')


async def before_server_stop(server):
    print('run before_server_stop haha')


async def after_server_stop(server):
    print('run after_server_stop haha')


#############################
# 服务函数
#############################
def main_resp_service(request: dict) -> dict:
    """
    直接返回收到的信息
    """
    print('dict_service get: %s' % str(request))
    return request['data']


def main_iter_service(request: dict):
    """
    返回迭代数据
    """
    print('main_iter_service get: %s' % str(request))
    for _item in request['data']:
        yield _item


def main_none_service(request: dict):
    """
    返回None
    """
    print('dict_service get: %s' % str(request))
    return


def main_error_service(request: dict):
    print('dict_service get: %s' % str(request))
    raise RuntimeError('test error')


#############################
# 类函数
#############################
class TestInstance(object):
    """
    类对象
    """

    def class_resp_service(self, request: dict) -> dict:
        """
        直接返回收到的信息
        """
        print('dict_service get: %s' % str(request))
        return request['data']


class TestSocketIOServer(unittest.TestCase):
    """
    测试SocketIOServer服务
    """

    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        cls.server = SocketIOServer(
            'test_sio_server', server_config={
                'debug': True,
                'flask_run': {
                    'host': '127.0.0.1', 'port': 5001
                },
                'service_namespace': ['/test', '/prd']
            },
            before_server_start=before_server_start,
            after_server_start=after_server_start,
            before_server_stop=before_server_stop,
            after_server_stop=after_server_stop,
            logger=LOGGER
        )

        # 添加服务
        cls.server.add_service(
            'main_resp_service', main_resp_service, namespace='/test'
        )
        cls.server.add_service(
            'main_iter_service', main_iter_service, namespace='/test'
        )
        cls.server.add_service(
            'main_none_service', main_none_service, namespace='/test'
        )
        cls.server.add_service(
            'main_error_service', main_error_service, namespace='/test'
        )
        _class_obj = TestInstance()
        cls.server.add_service_by_class(
            [_class_obj, ], namespace='/test'
        )

        # 启动服务
        _result = cls.server.start(is_asyn=True)
        if not _result.is_success():
            raise RuntimeError('start server error: %s' % str(_result))

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 停止服务
        _result = cls.server.stop()
        if not _result.is_success():
            print('stop server error: %s' % str(_result))

    def test_normal(self):
        # 连接客户端并进行测试
        with SocketIOClient({
            'url': 'http://127.0.0.1:5001',
            # 'namespaces': ['/test', '/prd'],
            'is_native_mode': False,
            'service_namespace': ['/test', '/prd']
        }) as _client:
            _tips = '测试发送字典并获取返回值'
            _except = {'a': 'val_a', 'b': 'val_b'}
            _result = _client.call(
                'main_resp_service', _except, namespace='/test'
            )
            self.assertTrue(
                _result.is_success() and TestTool.cmp_dict(_except, _result.resp),
                '%s失败: %s' % (_tips, str(_result))
            )

            _tips = '测试发送字符串并获取返回值'
            _except = 'test str'
            _result = _client.call(
                'main_resp_service', _except, namespace='/test'
            )
            self.assertTrue(
                _result.is_success() and _except == _result.resp,
                '%s失败: %s' % (_tips, str(_result))
            )

            _tips = '测试返回迭代对象'
            _except = ['a', 'b', 'c', 'd']
            _result = _client.call(
                'main_iter_service', _except, namespace='/test'
            )
            self.assertTrue(
                _result.is_success(), '%s失败: %s' % (_tips, str(_result))
            )
            _resp = []
            for _item in _result.resp:
                _resp.append(_item)
            self.assertTrue(
                TestTool.cmp_list(_except, _resp), '%s失败: %s' % (_tips, str(_result))
            )

            _tips = '测试处理函数为类函数'
            _except = {'a': 'val_a', 'b': 'val_b'}
            _result = _client.call(
                'TestInstance.class_resp_service', _except, namespace='/test'
            )
            self.assertTrue(
                _result.is_success() and TestTool.cmp_dict(_except, _result.resp),
                '%s失败: %s' % (_tips, str(_result))
            )

            _tips = '测试返回值为None'
            _except = {'a': 'val_a', 'b': 'val_b'}
            _result = _client.call(
                'main_none_service', _except, namespace='/test'
            )
            self.assertTrue(
                _result.is_success() and _result.resp is None,
                '%s失败: %s' % (_tips, str(_result))
            )

    def test_error(self):
        # 连接客户端并进行测试
        with SocketIOClient({
            'url': 'http://127.0.0.1:5001',
            # 'namespaces': ['/test', '/prd'],
            'is_native_mode': False,
            'service_namespace': ['/test', '/prd']
        }) as _client:
            _tips = '测试服务函数返回异常'
            _except = {'a': 'val_a', 'b': 'val_b'}
            _result = _client.call(
                'main_error_service', _except, namespace='/test'
            )
            self.assertTrue(
                not _result.is_success() and _result.error == 'test error',
                '%s失败: %s' % (_tips, str(_result))
            )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
