#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import json
import requests
import unittest
from sanic.request import Request
from sanic.response import json as json_sanic, text
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetSimpleSanic.server import SanicServer, SanicTool, EnumServerRunStatus
from HiveNetSimpleSanic.auth import IPAuthSanic, AppKeyAuthSanic


class TestApi(object):
    """
    测试非实例化调用的API接口
    """

    @classmethod
    def no_auth(cls, request: Request, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权处理的接口
        """
        print(request)
        return text('no_auth: {"a":%d, "b":"%s"}' % (a, b))

    @classmethod
    def no_auth_403(cls, request: Request, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权, 由处理程序返回指定http状态码的接口
        """
        return text('no_auth_403: {"a":%d, "b":"%s"}' % (a, b), status=403)

    @classmethod
    @SanicTool.support_object_resp
    def no_auth_dict(cls, request: Request, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权并直接返回字典对象, 增加支持python对象直接返回的修饰符
        """
        return {"a": a, "b": b}

    @classmethod
    @SanicServer.auth_required_static(auth_name='IPAuth', app_name='test_server')
    def auth_ip(cls, request: Request, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(不通过)
        """
        return text('{"a":%d, "b":"%s"}' % (a, b))

    @classmethod
    @SanicServer.auth_required_static(auth_name='IPAuthGo', app_name='test_server')
    def auth_ip_go(cls, request: Request, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(通过)
        """
        return text('{"a":%d, "b":"%s"}' % (a, b))

    @classmethod
    @SanicServer.auth_required_static(auth_name='AppKeyAuth', app_name='test_server')
    def auth_appkey(cls, request: Request, a: int, b: str, methods=['POST'], **kwargs):
        """
        通过app_key模式鉴权的接口(返回值不加签名验证)
        """
        return text('{"a":%d, "b":"%s"}' % (a, b))

    @classmethod
    @SanicServer.auth_required_static(auth_name='AppKeyAuthResp', app_name='test_server')
    def auth_appkey_sign_resp(cls, request: Request, a: int, b: str, methods=['POST'], **kwargs):
        """
        通过app_key模式鉴权的接口(返回值加签名验证)
        """
        _interface_id = request.json.get('interface_id', '')
        return text('{"a":%d, "b":"%s", "interface_id": "%s"}' % (a, b, _interface_id))


class TestApiInstance(object):
    """
    以实例对象方式的接口对象
    """

    def __init__(self, id: str):
        self.id = id

    def no_auth(self, request: Request, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权的接口
        """
        return text('{"a":%d, "b":"%s", "id":"%s"}' % (a, b, self.id))


class Test(unittest.TestCase):

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        print("test class start =======>")

        # 验证模块
        _ip_auth = IPAuthSanic(
            init_blacklist=['127.0.*.*']
        )
        _ip_auth_go = IPAuthSanic(
        )

        # 响应报文不加签
        _apk_auth = AppKeyAuthSanic(
            algorithm='HMAC-SHA256'
        )

        # 响应报文也加签的情况
        _apk_auth_resp = AppKeyAuthSanic(
            algorithm='HMAC-SHA256', sign_resp=True
        )

        # 生成app_key, app_secret
        _apk_auth.apk_generate_key_pair('123456')
        _apk_auth_resp.apk_generate_key_pair('654321')

        # 实例化的接口对象
        _api_instance = TestApiInstance('instance_id')

        # 服务器配置
        _server = SanicServer(
            'test_server',
            server_config={
                'run_config': {
                    'debug': False,
                    'host': '0.0.0.0',
                    'port': 5012,
                    'workers': 1,
                    'access_log': False
                },
                'run_in_thread': True
            },
            support_auths={
                'IPAuth': _ip_auth, 'AppKeyAuth': _apk_auth, 'IPAuthGo': _ip_auth_go,
                'AppKeyAuthResp': _apk_auth_resp
            }
        )

        # 装载api接口
        AsyncTools.sync_run_coroutine(_server.add_service_by_class([TestApi, _api_instance]))
        print(_server._app.router)

        # 启动服务
        AsyncTools.sync_run_coroutine(
            _server.start(is_asyn=True)
        )

    @classmethod
    def tearDownClass(cls):
        print("test class end =======>")
        # 停止服务
        AsyncTools.sync_run_coroutine(
            SanicServer.get_init_server(app_name='test_server').stop()
        )

    def test_no_auth(self):
        # 等待服务器启动
        _server: SanicServer = SanicServer.get_init_server(app_name='test_server')
        while _server.status not in (EnumServerRunStatus.Running, EnumServerRunStatus.Stop):
            time.sleep(1)

        # 准备初始参数
        _base_url = 'http://127.0.0.1:5012/'

        _tips = "test no_auth"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/no_auth/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        self.assertTrue(
            _back_str == 'no_auth: {"a":%d, "b":"%s"}' % (_a, _b),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test no_auth_403"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = '%sapi/TestApi/no_auth_403/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 403, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        self.assertTrue(
            _back_str == 'no_auth_403: {"a":%d, "b":"%s"}' % (_a, _b),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test no_auth_dict"
        print(_tips)
        _a = 12
        _b = 't12'
        _url = '%sapi/TestApi/no_auth_dict/%d/%s' % (_base_url, _a, _b)
        _resp = requests.post(_url)
        # _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {"a": _a, "b": _b}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test instance no_auth"
        print(_tips)
        _a = 12
        _b = 't12'
        _url = '%sapi/TestApiInstance/no_auth/%d/%s' % (_base_url, _a, _b)
        _resp = requests.post(_url)
        # _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {"a": _a, "b": _b, 'id': 'instance_id'}),
            '%s back error: %s' % (_tips, _back_str)
        )

    def test_auth(self):
        # 等待服务器启动
        _server: SanicServer = SanicServer.get_init_server(app_name='test_server')
        while _server.status not in (EnumServerRunStatus.Running, EnumServerRunStatus.Stop):
            time.sleep(1)

        # 准备初始参数
        _base_url = 'http://127.0.0.1:5012/'
        _headers = {'Content-Type': 'application/json'}

        _auth_appkey: AppKeyAuthSanic = _server.get_auth_fun(
            auth_name='AppKeyAuth', app_name='test_server')

        _auth_appkey_resp: AppKeyAuthSanic = _server.get_auth_fun(
            auth_name='AppKeyAuthResp', app_name='test_server')

        _auth_error = AppKeyAuthSanic(
            algorithm='HMAC-SHA256'
        )
        _app_id = '123456'
        _app_id_resp = '654321'
        _auth_error.apk_generate_key_pair(_app_id)

        _tips = "test auth_ip"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/auth_ip/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 403, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {'status': '10409', 'msg': 'IP地址验证失败'}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_ip_go"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/auth_ip_go/%d/%s' % (_base_url, _a, _b)
        _resp = requests.get(_url)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {"a": _a, "b": _b}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_appkey 403"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = '%sapi/TestApi/auth_appkey/%d/%s' % (_base_url, _a, _b)
        _data = {
            'interface_id': '1',
            'app_id': _app_id
        }
        _json = json.dumps(
            _auth_error.sign(_data), ensure_ascii=False
        )
        _resp = requests.post(_url, data=_json, headers=_headers)
        self.assertTrue(_resp.status_code == 403, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {'status': '13007', 'msg': '签名检查失败'}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_appkey"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = '%sapi/TestApi/auth_appkey/%d/%s' % (_base_url, _a, _b)
        _data = {
            'interface_id': '2',
            'app_id': _app_id
        }
        _json = json.dumps(
            _auth_appkey.sign(_data), ensure_ascii=False
        )
        _resp = requests.post(_url, data=_json, headers=_headers)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            TestTool.cmp_dict(_back_dict, {'a': _a, 'b': _b}),
            '%s back error: %s' % (_tips, _back_str)
        )

        _tips = "test auth_appkey_sign_resp"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = '%sapi/TestApi/auth_appkey_sign_resp/%d/%s' % (_base_url, _a, _b)
        _data = {
            'interface_id': '3',
            'app_id': _app_id_resp
        }
        _json = json.dumps(
            _auth_appkey_resp.sign(_data), ensure_ascii=False
        )
        _resp = requests.post(_url, data=_json, headers=_headers)
        self.assertTrue(_resp.status_code == 200, '%s status code error' % _tips)
        _back_str = str(_resp.content, encoding='utf-8')
        _back_dict = json.loads(_back_str)
        self.assertTrue(
            _auth_appkey_resp.verify_sign(
                _back_dict) and _back_dict['a'] == _a and _back_dict['b'] == _b and _back_dict['interface_id'] == _data['interface_id'],
            '%s back error: %s' % (_tips, _back_str)
        )


if __name__ == '__main__':
    unittest.main()
