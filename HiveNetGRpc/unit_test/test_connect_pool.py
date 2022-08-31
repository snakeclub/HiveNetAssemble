#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试连接池

@module test_connect_pool
@file test_connect_pool.py
"""

import os
import sys
import unittest
import time
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.test_tool import TestTool
from HiveNetCore.connection_pool import AIOConnectionPool, TooManyConnections
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.enum import EnumCallMode
from HiveNetGRpc.server import GRpcServer, AIOGRpcServer
from HiveNetGRpc.client import AIOGRpcClient, GRpcClient, GRpcPoolConnection
from HiveNetGRpc.msg_formater import RemoteCallFormater


@RemoteCallFormater.format_service(with_request=False)
async def service_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(数组形式)
    """
    return [a, b, args, c, d, kwargs]


class TestFunction(object):
    """
    真正的测试方法
    """

    @staticmethod
    def test_connection_pool(case_obj, is_async, port):
        """
        测试测试连接池
        """
        if is_async:
            # 客户端异步模式
            _creator = AIOGRpcClient
            _connect_config = {
                'host': '127.0.0.1', 'port': port, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
            }
        else:
            # 客户端同步模式
            _creator = GRpcClient
            _connect_config = {
                'host': '127.0.0.1', 'port': port, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': True, 'timeout': 3
            }

        # 建立连接池
        _pool = AIOConnectionPool(
            _creator, GRpcPoolConnection, args=[_connect_config],
            connect_method_name=None, max_size=3, min_size=0, connect_on_init=True,
            get_timeout=1,
            free_idle_time=5, ping_on_get=True, ping_on_back=True, ping_on_idle=True,
            ping_interval=5
        )

        print("测试连接池-获取连接并执行")
        # 尝试获取连接
        client = AsyncTools.sync_run_coroutine(_pool.connection())

        # 执行调用
        _tips = '测试连接池-获取连接并执行'
        _expect = ['a_val', 'b_val', ['fixed_add1', 'fixed_add2'], 14, {'d1': 'd1value'}, {'e': 'e_val'}]
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_call_para', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_list(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        print('测试连接池-获取连接超时')
        _c1 = AsyncTools.sync_run_coroutine(_pool.connection())
        _c2 = AsyncTools.sync_run_coroutine(_pool.connection())

        try:
            _c3 = AsyncTools.sync_run_coroutine(_pool.connection())
            case_obj.assertTrue(False, msg='测试连接池-获取连接超时失败，应抛出超时')
        except TooManyConnections:
            pass
        except Exception as e:
            case_obj.assertTrue(False, msg='测试连接池-获取连接超时失败，未期望的异常:%s' % str(e))

        case_obj.assertTrue(3 == _pool.current_size, msg='测试连接池-获取连接超时-当前连接池大小错误：%d' %
                        _pool.current_size)

        print('测试连接池-释放连接')
        AsyncTools.sync_run_coroutine(client.close())
        _c3 = AsyncTools.sync_run_coroutine(_pool.connection())  # 这样c3可用获取连接并使用
        case_obj.assertTrue(3 == _pool.current_size, msg='测试连接池-释放连接-当前连接池大小错误：%d' %
                        _pool.current_size)

        print('测试连接池-自动释放连接')
        AsyncTools.sync_run_coroutine(_c1.close())
        AsyncTools.sync_run_coroutine(_c2.close())
        AsyncTools.sync_run_coroutine(_c3.close())
        time.sleep(10)
        case_obj.assertTrue(0 == _pool.current_size, msg='测试连接池-自动释放连接-当前连接池大小错误：%d' %
                        _pool.current_size)


class TestGRpcJsonService(unittest.TestCase):
    """
    测试JsonService的grpc服务(连接池) - 同步grpc
    """

    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        # 测试没有ssl的服务
        if True:
            # 指定测试异步IO服务
            _grpc_server_class = AIOGRpcServer
        else:
            # 指定测试同步IO服务
            _grpc_server_class = GRpcServer

        cls._port = 50051
        cls._server_name = 'server_no_ssl'
        cls.server_no_ssl = _grpc_server_class(
            cls._server_name, server_config={
                'run_config': {
                    'host': '127.0.0.1', 'port': cls._port, 'workers': 2,
                    'enable_health_check': True
                }
            }
        )

        # 加载服务Simple
        _service_uri = 'service_simple_call_para'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_call_para,
        ))

        # 启动服务
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.start(is_asyn=True))
        if not _result.is_success():
            raise RuntimeError('start server no ssl error: %s' % str(_result))

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 停止服务
        _result = AsyncTools.sync_run_coroutine(
            cls.server_no_ssl.stop()
        )
        if not _result.is_success():
            print('stop server no ssl error: %s' % str(_result))

    def test_test_connection_pool_async(self):
        print('测试连接池处理(协程模式)')
        TestFunction.test_connection_pool(self, True, self._port)

    def test_test_connection_pool_sync(self):
        print('测试连接池处理(同步模式)')
        TestFunction.test_connection_pool(self, False, self._port)


class TestGRpcJsonServiceAsync(unittest.TestCase):
    """
    测试JsonService的grpc服务(连接池) - 异步grpc
    """

    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        # 测试没有ssl的服务
        if True:
            # 指定测试异步IO服务
            _grpc_server_class = AIOGRpcServer
        else:
            # 指定测试同步IO服务
            _grpc_server_class = GRpcServer

        cls._port = 50052
        cls._server_name = 'server_no_ssl_async'
        cls.server_no_ssl = _grpc_server_class(
            cls._server_name, server_config={
                'run_config': {
                    'host': '127.0.0.1', 'port': cls._port, 'workers': 2,
                    'enable_health_check': True
                }
            }
        )

        # 加载服务Simple
        _service_uri = 'service_simple_call_para'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_call_para,
        ))

        # 启动服务
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.start(is_asyn=True))
        if not _result.is_success():
            raise RuntimeError('start server no ssl error: %s' % str(_result))

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 停止服务
        _result = AsyncTools.sync_run_coroutine(
            cls.server_no_ssl.stop()
        )
        if not _result.is_success():
            print('stop server no ssl error: %s' % str(_result))

    def test_test_connection_pool_async(self):
        print('测试连接池处理(协程模式)')
        TestFunction.test_connection_pool(self, True, self._port)

    def test_test_connection_pool_sync(self):
        print('测试连接池处理(同步模式)')
        TestFunction.test_connection_pool(self, False, self._port)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
