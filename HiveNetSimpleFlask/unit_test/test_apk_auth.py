#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import json
import requests
import unittest
from flask import request, jsonify
from HiveNetCore.utils.test_tool import TestTool
from HiveNetCore.logging_hivenet import Logger
from HiveNetWebUtils.server import EnumServerRunStatus
from HiveNetWebUtils.client import HttpClient
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetSimpleFlask.server import FlaskTool, FlaskServer
from HiveNetSimpleFlask.auth import IPAuthFlask, AppKeyAuthFlask


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


class TestApi(object):
    """
    测试非实例化调用的API接口
    """

    @classmethod
    def no_auth(cls, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权处理的接口
        """
        return 'no_auth: {"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    def no_auth_403(cls, a: int, b: str, methods=['GET']):
        """
        没有安全鉴权, 由处理程序返回指定http状态码的接口
        """
        return 'no_auth_403: {"a":%d, "b":"%s"}' % (a, b), 403

    @classmethod
    @FlaskTool.support_object_resp
    def no_auth_dict(cls, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权并直接返回字典对象
        """
        return {"a": a, "b": b}

    @classmethod
    @FlaskServer.auth_required_static(auth_name='IPAuth', app_name='test_server')
    def auth_ip(cls, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(不通过)
        """
        return '{"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    @FlaskServer.auth_required_static(auth_name='IPAuthGo', app_name='test_server')
    def auth_ip_go(cls, a: int, b: str, methods=['GET'], **kwargs):
        """
        进行IP鉴权的接口(通过)
        """
        return '{"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    @FlaskServer.auth_required_static(auth_name='AppKeyAuth', app_name='test_server')
    def auth_appkey(cls, a: int, b: str, methods=['POST'], **kwargs):
        """
        通过app_key模式鉴权的接口(返回值不加签名验证)
        """
        return '{"a":%d, "b":"%s"}' % (a, b)

    @classmethod
    @FlaskServer.auth_required_static(auth_name='AppKeyAuthResp', app_name='test_server')
    def auth_appkey_sign_resp(cls, a: int, b: str, methods=['POST'], **kwargs):
        """
        通过app_key模式鉴权的接口(返回值加签名验证)
        """
        _interface_id = request.json.get('interface_id', '')
        return '{"a":%d, "b":"%s", "interface_id": "%s"}' % (a, b, _interface_id)


class TestApiInstance(object):
    """
    以实例对象方式的接口对象
    """

    def __init__(self, id: str):
        self.id = id

    def no_auth(self, a: int, b: str, methods=['POST'], **kwargs):
        """
        没有安全鉴权的接口
        """
        return '{"a":%d, "b":"%s", "id":"%s"}' % (a, b, self.id)


class Test(unittest.TestCase):
    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        # 验证模块
        _ip_auth = IPAuthFlask(
            init_blacklist=['127.0.*.*']
        )
        _ip_auth_go = IPAuthFlask(
        )

        # 响应报文不加签
        _apk_auth = AppKeyAuthFlask(
            algorithm='HMAC-SHA256'
        )

        # 响应报文也加签的情况
        _apk_auth_resp = AppKeyAuthFlask(
            algorithm='HMAC-SHA256', sign_resp=True
        )

        # 生成app_key, app_secret
        _apk_auth.apk_generate_key_pair('123456')
        _apk_auth_resp.apk_generate_key_pair('654321')

        # 实例化的接口对象
        _api_instance = TestApiInstance('instance_id')

        # 服务器配置
        _sever = FlaskServer(
            'test_server', server_config={
                'debug': True,
                'flask_run': {
                    'host': '127.0.0.1', 'port': 5000
                },
            },
            support_auths={
                'IPAuth': _ip_auth, 'AppKeyAuth': _apk_auth, 'IPAuthGo': _ip_auth_go,
                'AppKeyAuthResp': _apk_auth_resp
            },
            logger=LOGGER
        )

        # 装载api接口
        _sever.add_service_by_class([TestApi, _api_instance])
        print(_sever.native_app.url_map)

        # 启动服务
        _sever.start(is_asyn=True)

    @classmethod
    def tearDownClass(cls):
        # 停止服务
        FlaskServer.get_init_server(app_name='test_server').stop()

    def test_no_auth(self):
        # 等待服务器启动
        _sever: FlaskServer = FlaskServer.get_init_server(app_name='test_server')
        while _sever.status not in (EnumServerRunStatus.Running, EnumServerRunStatus.Stop):
            time.sleep(1)

        # 客户端
        _http_client = HttpClient({
            'conn_str': 'http://127.0.0.1:5000/'
        })

        _tips = "test no_auth"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = 'api/TestApi/no_auth/%d/%s' % (_a, _b)
        _result = _http_client.call(_url)
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 200 and str(
                _result.resp['data'], encoding='utf-8'
            ) == 'no_auth: {"a":%d, "b":"%s"}' % (_a, _b),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test no_auth_403"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = 'api/TestApi/no_auth_403/%d/%s' % (_a, _b)
        _result = _http_client.call(_url)
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 403 and str(
                _result.resp['data'], encoding='utf-8'
            ) == 'no_auth_403: {"a":%d, "b":"%s"}' % (_a, _b),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test no_auth_dict"
        print(_tips)
        _a = 12
        _b = 't12'
        _url = 'api/TestApi/no_auth_dict/%d/%s' % (_a, _b)
        _result = _http_client.call(_url, method='POST')
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 200 and TestTool.cmp_dict(
                json.loads(_result.resp['data']), {"a": _a, "b": _b}
            ),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test instance no_auth"
        print(_tips)
        _a = 12
        _b = 't12'
        _url = 'api/TestApiInstance/no_auth/%d/%s' % (_a, _b)
        _result = _http_client.call(_url, method='POST')
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 200 and TestTool.cmp_dict(
                json.loads(_result.resp['data']), {"a": _a, "b": _b, 'id': 'instance_id'}
            ),
            '%s back error: %s' % (_tips, str(_result))
        )

    def test_auth(self):
        # 等待服务器启动
        _sever: FlaskServer = FlaskServer.get_init_server(app_name='test_server')
        while _sever.status not in (EnumServerRunStatus.Running, EnumServerRunStatus.Stop):
            time.sleep(1)

        # 客户端
        _http_client = HttpClient({
            'conn_str': 'http://127.0.0.1:5000/'
        })

        # 准备初始参数
        _headers = {'Content-Type': 'application/json'}

        _auth_appkey: AppKeyAuthFlask = _sever.get_auth_fun(
            auth_name='AppKeyAuth', app_name='test_server')

        _auth_appkey_resp: AppKeyAuthFlask = _sever.get_auth_fun(
            auth_name='AppKeyAuthResp', app_name='test_server')

        _auth_error = AppKeyAuthFlask(
            algorithm='HMAC-SHA256'
        )
        _app_id = '123456'
        _app_id_resp = '654321'
        _auth_error.apk_generate_key_pair(_app_id)

        _tips = "test auth_ip"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = 'api/TestApi/auth_ip/%d/%s' % (_a, _b)
        _result = _http_client.call(_url)
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 403 and TestTool.cmp_dict(
                json.loads(_result.resp['data']), {'status': '10409', 'msg': 'IP地址验证失败'}
            ),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test auth_ip_go"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = 'api/TestApi/auth_ip_go/%d/%s' % (_a, _b)
        _result = _http_client.call(_url)
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 200 and TestTool.cmp_dict(
                json.loads(_result.resp['data']), {"a": _a, "b": _b}
            ),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test auth_appkey 403"
        print(_tips)
        _a = 10
        _b = 't10'
        _url = 'api/TestApi/auth_appkey/%d/%s' % (_a, _b)
        _data = {
            'interface_id': '1',
            'app_id': _app_id
        }
        _json = json.dumps(
            _auth_error.sign(_data), ensure_ascii=False
        )
        _result = _http_client.call(_url, request=_json, headers=_headers, method='POST')
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 403 and TestTool.cmp_dict(
                json.loads(_result.resp['data']), {'status': '13007', 'msg': '签名检查失败'}
            ),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test auth_appkey"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = 'api/TestApi/auth_appkey/%d/%s' % (_a, _b)
        _data = {
            'interface_id': '2',
            'app_id': _app_id
        }
        _json = json.dumps(
            _auth_appkey.sign(_data), ensure_ascii=False
        )
        _result = _http_client.call(_url, request=_json, headers=_headers, method='POST')
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 200 and TestTool.cmp_dict(
                json.loads(_result.resp['data']), {'a': _a, 'b': _b}
            ),
            '%s back error: %s' % (_tips, str(_result))
        )

        _tips = "test auth_appkey_sign_resp"
        print(_tips)
        _a = 11
        _b = 't11'
        _url = 'api/TestApi/auth_appkey_sign_resp/%d/%s' % (_a, _b)
        _data = {
            'interface_id': '3',
            'app_id': _app_id_resp
        }
        _json = json.dumps(
            _auth_appkey_resp.sign(_data), ensure_ascii=False
        )
        _result = _http_client.call(_url, request=_json, headers=_headers, method='POST')
        self.assertTrue(
            _result.is_success() and _result.resp['status'] == 200 and _auth_appkey_resp.verify_sign(
                json.loads(_result.resp['data'])
            ),
            '%s back error: %s' % (_tips, str(_result))
        )


if __name__ == '__main__':
    unittest.main()
