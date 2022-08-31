#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试ca证书

@module test_ca
@file test_ca.py
"""
#############################
# 测试TSL认证模式
# 需先生成相应证书文件（域名为localhost）
# --执行前先进入HiveNetGRpc/test_data/路径
# --创建CA根证书（自签名证书）
# --生成rsa私钥文件，使用des3加密文件（密码111111）
# openssl genrsa -passout pass:111111 -des3 -out ca.key 4096
# --通过私钥生成签名证书
# openssl req -passin pass:111111 -new -x509 -days 365 -key ca.key -out ca.crt -subj "/CN=localhost"
#
# --创建服务器证书
# --生成rsa私钥文件
# openssl genrsa -passout pass:111111 -des3 -out server.key 4096
# --通过私钥生成签名证书签名请求文件
# openssl req -passin pass:111111 -new -key server.key -out server.csr -subj "/CN=localhost"
# --由CA根证书签发根据请求文件签发证书
# openssl x509 -req -passin pass:111111 -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt
# --私钥文件由加密转为非加密
# openssl rsa -passin pass:111111 -in server.key -out server.key
#
# --创建客户端证书
# openssl genrsa -passout pass:111111 -des3 -out client.key 4096
# openssl req -passin pass:111111 -new -key client.key -out client.csr -subj "/CN=localhost"
# openssl x509 -passin pass:111111 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out client.crt
# openssl rsa -passin pass:111111 -in client.key -out client.key
#
# --对私钥进行pkcs8编码
# openssl pkcs8 -topk8 -nocrypt -in client.key -out client.pem
# openssl pkcs8 -topk8 -nocrypt -in server.key -out server.pem
#
# --第2套证书
# openssl genrsa -passout pass:123456 -des3 -out ca2.key 4096
# openssl req -passin pass:123456 -new -x509 -days 365 -key ca2.key -out ca2.crt -subj "/CN=localhost"
#
# --客户端证书
# openssl genrsa -passout pass:123456 -des3 -out client2.key 4096
# openssl req -passin pass:123456 -new -key client2.key -out client2.csr -subj "/CN=localhost"
# openssl x509 -passin pass:123456 -req -days 365 -in client2.csr -CA ca2.crt -CAkey ca2.key -set_serial 01 -out client2.crt
# openssl rsa -passin pass:123456 -in client2.key -out client2.key
# openssl pkcs8 -topk8 -nocrypt -in client2.key -out client2.pem
#############################
import os
import sys
import unittest
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.server import GRpcServer, AIOGRpcServer
from HiveNetGRpc.client import AIOGRpcClient, GRpcClient
from HiveNetGRpc.msg_formater import RemoteCallFormater


#############################
# 控制是否执行测试案例的字典
#############################
TEST_CONTROL = {
    'test_server_ssl_async': True,
    'test_server_ssl_sync': True,
    'test_double_ssl_async': True,
    'test_double_ssl_sync': True
}


#############################
# 服务端处理函数(Simple)
#############################
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
    def test_server_ssl_failed(case_obj, client, is_async):
        """
        测试服务端单向访问失败情况
        """
        _tips = '测试服务端ssl验证失败情况'
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
            _result.code == '20408',
            '%s error: %s' % (_tips, str(_result))
        )

    @staticmethod
    def test_server_ssl_success(case_obj, client, is_async):
        """
        测试服务端单向访问成功情况
        """
        _tips = '测试服务端ssl验证成功情况'
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


class TestGRpcJsonService(unittest.TestCase):
    """
    测试JsonService的grpc服务
    """
    _port = 50050
    _server_name_after = ''
    TEST_SERVER_ASYNC = False

    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        _ca_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'test_data/ca'
        ))
        cls.ca_path = _ca_path

        if cls.TEST_SERVER_ASYNC:
            _grpc_server_class = AIOGRpcServer
        else:
            _grpc_server_class = GRpcServer

        # 测试服务端单向ssl验证的服务
        cls.server_server_ssl = _grpc_server_class(
            'server_single_ssl' + cls._server_name_after, server_config={
                'run_config': {
                    'host': '127.0.0.1', 'port': cls._port + 2, 'workers': 2,
                    'enable_health_check': True,
                    'use_ssl': True,
                    'ssl': [{
                        'cert': os.path.join(_ca_path, 'server.crt'),
                        'key': os.path.join(_ca_path, 'server.pem')
                    }]
                }
            }
        )

        # 加载服务Simple
        _service_uri = 'service_simple_call_para'
        _result = AsyncTools.sync_run_coroutine(cls.server_server_ssl.add_service(
            _service_uri, service_simple_call_para,
        ))

        # 启动服务
        _result = AsyncTools.sync_run_coroutine(cls.server_server_ssl.start(is_asyn=True))
        if not _result.is_success():
            raise RuntimeError('start server server ssl error: %s' % str(_result))

        # 测试服务端双向ssl验证的服务
        cls.server_double_ssl = _grpc_server_class(
            'server_double_ssl' + cls._server_name_after, server_config={
                'run_config': {
                    'host': '127.0.0.1', 'port': cls._port + 3, 'workers': 2,
                    'enable_health_check': True,
                    'use_ssl': True,
                    'ssl': [{
                        'cert': os.path.join(_ca_path, 'server.crt'),
                        'key': os.path.join(_ca_path, 'server.pem')
                    }],
                    'root_certificates': os.path.join(_ca_path, 'client.crt')
                }
            }
        )

        # 加载服务Simple
        _service_uri = 'service_simple_call_para'
        _result = AsyncTools.sync_run_coroutine(cls.server_double_ssl.add_service(
            _service_uri, service_simple_call_para,
        ))

        # 启动服务
        _result = AsyncTools.sync_run_coroutine(cls.server_double_ssl.start(is_asyn=True))
        if not _result.is_success():
            raise RuntimeError('start server double ssl error: %s' % str(_result))

    @classmethod
    def tearDownClass(cls):
        """
        结束测试类执行的销毁，只执行一次
        """
        # 停止服务
        _result = AsyncTools.sync_run_coroutine(
            cls.server_server_ssl.stop()
        )
        if not _result.is_success():
            print('stop server server ssl error: %s' % str(_result))

        # 停止服务
        _result = AsyncTools.sync_run_coroutine(
            cls.server_double_ssl.stop()
        )
        if not _result.is_success():
            print('stop server double ssl error: %s' % str(_result))

    def test_server_ssl_async(self):
        if not TEST_CONTROL['test_server_ssl_async']:
            return

        print('测试服务端单向ssl验证(协程模式)')

        print('测试服务端单向ssl验证失败')
        try:
            _tips = '测试服务端单向ssl连接客户端不使用ssl(连接时ping)'
            AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 2, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
            })
            self.assertTrue(False, '%s error: 应抛出ConnectionError异常' % (_tips))
        except ConnectionError:
            pass

        _tips = '测试服务端单向ssl连接客户端不使用ssl(连接时不ping)'
        with AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 2, 'ping_on_connect': False, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
        }) as _client:
            TestFunction.test_server_ssl_failed(self, _client, True)

        print('测试服务端单向ssl验证通过')
        # 注意host必须为域名，不能为ip
        with AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 2, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3,
                'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt')
        }) as _client:
            TestFunction.test_server_ssl_success(self, _client, True)

    def test_server_ssl_sync(self):
        if not TEST_CONTROL['test_server_ssl_sync']:
            return

        print('测试服务端单向ssl验证(同步模式)')

        print('测试服务端单向ssl验证失败')
        try:
            _tips = '测试服务端单向ssl连接客户端不使用ssl(连接时ping)'
            GRpcClient({
                'host': 'localhost', 'port': self._port + 2, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': True, 'timeout': 3
            })
            self.assertTrue(False, '%s error: 应抛出ConnectionError异常' % (_tips))
        except ConnectionError:
            pass

        _tips = '测试服务端单向ssl连接客户端不使用ssl(连接时不ping)'
        with GRpcClient({
                'host': 'localhost', 'port': self._port + 2, 'ping_on_connect': False, 'ping_with_health_check': True,
                'use_sync_client': True, 'timeout': 3
        }) as _client:
            TestFunction.test_server_ssl_failed(self, _client, True)

        print('测试服务端单向ssl验证通过')
        # 注意host必须为域名，不能为ip
        with GRpcClient({
                'host': 'localhost', 'port': self._port + 2, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': True, 'timeout': 3,
                'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt')
        }) as _client:
            TestFunction.test_server_ssl_success(self, _client, True)

    def test_double_ssl_async(self):
        if not TEST_CONTROL['test_double_ssl_async']:
            return

        print('测试双向ssl验证(协程模式)')

        print('测试服务端ssl验证失败')
        try:
            _tips = '测试客户端不使用ssl(连接时ping)'
            AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
            })
            self.assertTrue(False, '%s error: 应抛出ConnectionError异常' % (_tips))
        except ConnectionError:
            pass

        _tips = '测试客户端不使用ssl(连接时不ping)'
        with AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': False, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
        }) as _client:
            TestFunction.test_server_ssl_failed(self, _client, True)

        _tips = '测试客户端反向验证失败'
        try:
            AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3,
                'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt'),
                'ssl': {
                    'cert': os.path.join(self.ca_path, 'client2.crt'),
                    'key': os.path.join(self.ca_path, 'client2.pem')
                }
            })
            self.assertTrue(False, '%s error: 应抛出ConnectionError异常' % (_tips))
        except ConnectionError:
            pass

        print('测试双向ssl验证通过')
        with AIOGRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3,
                'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt'),
                'ssl': {
                    'cert': os.path.join(self.ca_path, 'client.crt'),
                    'key': os.path.join(self.ca_path, 'client.pem')
                }
        }) as _client:
            TestFunction.test_server_ssl_success(self, _client, True)

    def test_double_ssl_sync(self):
        if not TEST_CONTROL['test_double_ssl_sync']:
            return

        print('测试双向ssl验证(同步模式)')

        print('测试服务端ssl验证失败')
        try:
            _tips = '测试客户端不使用ssl(连接时ping)'
            GRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
            })
            self.assertTrue(False, '%s error: 应抛出ConnectionError异常' % (_tips))
        except ConnectionError:
            pass

        _tips = '测试客户端不使用ssl(连接时不ping)'
        with GRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': False, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3
        }) as _client:
            TestFunction.test_server_ssl_failed(self, _client, True)

        _tips = '测试客户端反向验证失败'
        try:
            GRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3,
                'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt'),
                'ssl': {
                    'cert': os.path.join(self.ca_path, 'client2.crt'),
                    'key': os.path.join(self.ca_path, 'client2.pem')
                }
            })
            self.assertTrue(False, '%s error: 应抛出ConnectionError异常' % (_tips))
        except ConnectionError:
            pass

        print('测试双向ssl验证通过')
        with GRpcClient({
                'host': 'localhost', 'port': self._port + 3, 'ping_on_connect': True, 'ping_with_health_check': True,
                'use_sync_client': False, 'timeout': 3,
                'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt'),
                'ssl': {
                    'cert': os.path.join(self.ca_path, 'client.crt'),
                    'key': os.path.join(self.ca_path, 'client.pem')
                }
        }) as _client:
            TestFunction.test_server_ssl_success(self, _client, True)


class TestGRpcJsonServiceAsync(TestGRpcJsonService):
    """
    测试JsonService的grpc服务 - 异步服务
    """
    _port = 50060
    _server_name_after = '_async'
    TEST_SERVER_ASYNC = True


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
