#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试TcpIpServer
@module test_tcpip_server
@file test_tcpip_server.py
"""

import os
import sys
import time
import json
import unittest
from HiveNetCore.generic import CResult
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.net_tool import NetTool
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetWebUtils.server import TcpIpServer
from HiveNetWebUtils.utils.socket import SocketTool


#############################
# 生命周期函数
#############################
def before_server_start(server):
    print('execute before_server_start')


def after_server_start(server):
    print('execute after_server_start')


def before_server_stop(server):
    print('execute before_server_stop')


def after_server_stop(server):
    print('execute after_server_stop')


#############################
# 通过报文匹配服务标识的函数
#############################
def match_service_uri_func(request: dict) -> str:
    return request.get('head', {}).get('uri', '')


#############################
# 服务处理函数
#############################
def common_service(net_info, service_uri: str, request: dict) -> dict:
    """
    通用的服务
    """
    return {'name': 'common_service', 'service_uri': service_uri, 'request': request}


def no_return_service(net_info, service_uri: str, request: dict) -> dict:
    """
    不返回值的服务
    """
    print('run o_return_service: %s, %s' % (service_uri, str(request)))
    return None


class TestTcpIpServer(unittest.TestCase):
    # 测试用的工具函数
    @classmethod
    def send_msg(cls, msg: dict, is_recv: bool = True) -> CResult:
        """
        发送消息到服务器端, 同时接收返回值
        """
        # 连接服务器
        _result = AsyncTools.sync_run_coroutine(
            SocketTool.connect(connect_config={'ip': '127.0.0.1', 'port': 9512})
        )
        if not _result.is_success():
            return _result
        _net_info = _result.net_info

        # 发送消息
        _send_data = json.dumps(msg, ensure_ascii=False).encode(encoding='utf-8')
        _send_data = NetTool.int_to_bytes(len(_send_data), signed=False) + _send_data
        _result = AsyncTools.sync_run_coroutine(
            SocketTool.send_data(_net_info, _send_data)
        )
        if not _result.is_success():
            return _result

        # 接收响应信息
        if is_recv:
            _result = AsyncTools.sync_run_coroutine(
                SocketTool.recv_data(_net_info, recv_para={'recv_len': 4})
            )
            if not _result.is_success():
                return _result

            _msg_len = NetTool.bytes_to_int(_result.data, signed=False)

            _result = AsyncTools.sync_run_coroutine(
                SocketTool.recv_data(_net_info, recv_para={'recv_len': _msg_len})
            )
            if not _result.is_success():
                return _result

            _result.data = json.loads(_result.data)

        # 关闭连接
        _close_result = AsyncTools.sync_run_coroutine(SocketTool.close(_net_info))
        if not _close_result.is_success():
            return _close_result

        return _result

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化, 只执行一次
        """
        # 创建服务
        cls.server = TcpIpServer(
            'test_tcpip', {
                'ip': '127.0.0.1', 'port': 9512,

            },
            before_server_start=before_server_start, after_server_start=after_server_start,
            before_server_stop=before_server_stop, after_server_stop=after_server_stop,
            match_service_uri_func=match_service_uri_func
        )

        # 添加服务
        _result = AsyncTools.sync_run_coroutine(cls.server.add_service(
            '', common_service
        ))  # 通用服务

        _result = AsyncTools.sync_run_coroutine(cls.server.add_service(
            'no_return_uri', no_return_service
        ))  # 不返回值的uri

        # 启动服务
        _result = AsyncTools.sync_run_coroutine(
            cls.server.start(is_asyn=True)
        )
        if not _result.is_success():
            print('start server error: %s' % str(_result))
            raise RuntimeError()

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁, 只执行一次
        """
        # 关闭服务器连接
        _i = 0
        while _i < 2:
            time.sleep(1)
            _i = _i + 1

        AsyncTools.sync_run_coroutine(cls.server.stop())

    def test_services(self):
        _tips = '测试调用通用服务'
        _uri = 'no_exists_uri'
        _msg = {
            'head': {'uri': _uri},
            'msg': 'test common_service'
        }
        _expect_resp = {
            'name': 'common_service', 'service_uri': _uri, 'request': _msg
        }
        _result = self.send_msg(_msg)
        self.assertTrue(
            _result.is_success() and TestTool.cmp_dict(_result.data, _expect_resp),
            msg='%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试调用不返回值的服务'
        _uri = 'no_return_uri'
        _msg = {
            'head': {'uri': _uri},
            'msg': 'test no_return_service'
        }
        _result = self.send_msg(_msg, is_recv=False)
        self.assertTrue(
            _result.is_success(),
            msg='%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试获取返回值超时'
        _uri = 'no_return_uri'
        _msg = {
            'head': {'uri': _uri},
            'msg': 'test recv overtime'
        }
        _result = self.send_msg(_msg, is_recv=True)
        self.assertTrue(
            _result.code == '20403',
            msg='%s error: %s' % (_tips, str(_result))
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
