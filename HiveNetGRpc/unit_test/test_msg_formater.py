#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试msg_formater(附带测试客户端和服务端)

@module test_msg_formater
@file test_msg_formater.py
"""
import os
import sys
import unittest
import asyncio
from xml.dom import NotFoundErr
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.test_tool import TestTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.enum import EnumCallMode
from HiveNetGRpc.server import AIOGRpcServer, GRpcServer
from HiveNetGRpc.client import AIOGRpcClient, GRpcClient
from HiveNetGRpc.msg_formater import RemoteCallFormater

#############################
# 控制是否执行测试案例的字典
#############################
TEST_CONTROL = {
    'test_simple_call_async': True,
    'test_simple_call_sync': True,
    'test_client_stream_call_async': True,
    'test_client_stream_call_sync': True,
    'test_server_stream_call_async': True,
    'test_server_stream_call_sync': True,
    'test_bidirectional_stream_call_async': True,
    'test_bidirectional_stream_call_sync': True,
    'test_class_menthod_call_async': True,
    'test_class_menthod_call_sync': True
}

#############################
# 指定测试异步IO服务还是同步服务
#############################
TEST_SERVER_ASYNC = True


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
# 服务端处理函数(Simple)
#############################
@RemoteCallFormater.format_service(with_request=False)
async def service_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(数组形式)
    """
    return [a, b, args, c, d, kwargs]


@RemoteCallFormater.format_service(with_request=False)
def service_simple_call_para_kv(c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(字典形式)
    """
    return {'c': c, 'd': d, 'kwargs': kwargs}


@RemoteCallFormater.format_service(with_request=False)
async def service_simple_no_para():
    """
    测试简单调用, 无参数无返回
    """
    return None


@RemoteCallFormater.format_service(with_request=False)
async def service_simple_no_para_overtime():
    """
    测试简单调用, 无参数超时
    """
    await asyncio.sleep(4)
    return None


@RemoteCallFormater.format_service(with_request=False)
async def service_simple_base_bool():
    """
    测试简单调用, 无参数返回基础类型(bool)
    """
    return False


@RemoteCallFormater.format_service(with_request=False)
async def service_simple_base_str():
    """
    测试简单调用, 无参数返回基础类型(str)
    """
    return '{"a": "abc"}'


@RemoteCallFormater.format_service(with_request=False)
async def service_simple_exception():
    """
    测试简单调用, 无参数抛出异常
    """
    return 1 / 0


#############################
# 服务端处理函数(ClientSideStream)
#############################
@RemoteCallFormater.format_service(with_request=True)
async def service_client_stream(request, a, b, c=10):
    """
    测试客户端流(数字加总)
    """
    d = 0
    for _item in request['request']:
        d += _item
    return [a, b, c, d]


@RemoteCallFormater.format_service(with_request=True)
async def service_client_stream_midle_return(request, a, b, c=10):
    """
    测试客户端流(收到一半返回)
    """
    d = 0
    index = 0
    for _item in request['request']:
        index += 1
        d += _item
        if index >= 2:
            break

    return [a, b, c, d]


@RemoteCallFormater.format_service(with_request=True)
async def service_client_stream_midle_exception(request, a, b, c=10):
    """
    测试客户端流(收到一半抛出异常)
    """
    d = 0
    index = 0
    for _item in request['request']:
        index += 1
        d += _item
        if index >= 2:
            raise RuntimeError('test exception')

    return [a, b, c, d]


#############################
# 服务端处理函数(ServerSideStream)
#############################
@RemoteCallFormater.format_service(with_request=True)
async def service_server_stream_async(request, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试服务端流(异步函数)
    """
    print([a, b, args, c, d, kwargs])
    for i in [1, 2, 3, 4]:
        yield i


@RemoteCallFormater.format_service(with_request=True)
def service_server_stream_sync(request, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试服务端流(同步函数)
    """
    print([a, b, args, c, d, kwargs])
    for i in [1, 2, 3, 4]:
        yield i


@RemoteCallFormater.format_service(with_request=True)
async def service_server_stream_exception(request, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试服务端流(抛出异常)
    """
    print([a, b, args, c, d, kwargs])
    index = 0
    for i in [1, 2, 3, 4]:
        index += 1
        yield i
        if index >= 2:
            raise RuntimeError('test exception')


#############################
# 服务端处理函数(BidirectionalStream)
#############################
@RemoteCallFormater.format_service(with_request=True)
async def service_bidirectional_stream_async(request, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试双向流(异步函数, 先收再发)
    """
    # 处理客户端的迭代
    d = 0
    for _item in request['request']:
        d += _item

    print([a, b, args, c, d, kwargs])

    # 处理返回迭代
    for i in [1, 2, 3, 4]:
        yield (d, i)


@RemoteCallFormater.format_service(with_request=True)
def service_bidirectional_stream_sync(request, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试双向流(同步函数, 边收边发)
    """
    # 处理客户端的迭代
    d = 0
    for _item in request['request']:
        yield (d, _item)


#############################
# 测试类函数和实例函数的情况
#############################
class ServiceClass(object):

    @staticmethod
    @RemoteCallFormater.format_service(with_request=False)
    async def service_simple_call_para_static(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
        """
        测试简单调用，直接返回传入的参数(数组形式)
        """
        return [a, b, args, c, d, kwargs]

    @classmethod
    @RemoteCallFormater.format_service(with_request=False)
    async def service_simple_call_para_class(cls, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
        """
        测试简单调用，直接返回传入的参数(数组形式)
        """
        return [a, b, args, c, d, kwargs]

    @RemoteCallFormater.format_service(with_request=False)
    async def service_simple_call_para_member(self, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
        """
        测试简单调用，直接返回传入的参数(数组形式)
        """
        return [a, b, args, c, d, kwargs]


class TestFunction(object):
    """
    真正的测试方法
    """

    @staticmethod
    def test_simple_call(case_obj, client, is_async):
        """
        测试简单模式调用
        """
        _tips = '测试ping'
        _result = AsyncTools.sync_run_coroutine(client.ping())
        case_obj.assertTrue(_result.is_success(), '%s error: %s' % (_tips, str(_result)))

        _tips = '测试服务不存在'
        _request = RemoteCallFormater.paras_to_grpc_request()
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_not_exists', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.code == '20408', '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试服务异常'
        _request = RemoteCallFormater.paras_to_grpc_request()
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_exception', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.code == '31008', '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试服务超时'
        _request = RemoteCallFormater.paras_to_grpc_request()
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_no_para_overtime', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.code == '30403', '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试简单调用，直接返回传入的参数(数组形式)'
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

        _tips = '测试简单调用，直接返回传入的参数(字典形式)'
        _expect = {'c': 14, 'd': {'d1': 'd1value'}, 'kwargs': {'e': 'e_val'}}
        _request = RemoteCallFormater.paras_to_grpc_request(
            None,
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_call_para_kv', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_dict(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试简单调用, 无参数无返回'
        _request = RemoteCallFormater.paras_to_grpc_request()
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_no_para', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and _result.resp is None,
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试简单调用, 无参数返回基础类型(bool)'
        _request = RemoteCallFormater.paras_to_grpc_request()
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_base_bool', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and _result.resp is False,
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试简单调用, 无参数返回基础类型(str)'
        _request = RemoteCallFormater.paras_to_grpc_request()
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_base_str', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and _result.resp == '{"a": "abc"}',
            '%s error: %s' % (_tips, str(_result))
        )

    @staticmethod
    def test_client_stream_call(case_obj, client, is_async):
        """
        测试客户端流模式调用
        """
        _tips = '测试客户端流(数字加总)'
        _expect = ['a_val', 'b_val', 14, 10]
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            [1, 2, 3, 4],
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )

        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_client_stream', _request, call_mode=EnumCallMode.ClientSideStream
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_list(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试客户端流(异步迭代)'

        async def generator_async():
            for _i in [1, 2, 3, 4]:
                yield _i

        _expect = ['a_val', 'b_val', 14, 10]
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            generator_async(),
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_client_stream', _request, call_mode=EnumCallMode.ClientSideStream
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_list(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试客户端流(迭代中间异常)'

        def generator_sync():
            for _i in [1, 2]:
                yield _i
            raise NotFoundErr('test')

        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            generator_sync(),
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )

        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_client_stream', _request, call_mode=EnumCallMode.ClientSideStream
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.code == '21007' if is_async else '20408',
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试客户端流(服务端中间返回)'
        _expect = ['a_val', 'b_val', 14, 3]
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            [1, 2, 3, 4],
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )

        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_client_stream_midle_return', _request, call_mode=EnumCallMode.ClientSideStream
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_list(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试客户端流(服务端中间异常)'
        _expect = ['a_val', 'b_val', 14, 3]
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            [1, 2, 3, 4],
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )

        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_client_stream_midle_exception', _request, call_mode=EnumCallMode.ClientSideStream
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.code == '31008', '%s error: %s' % (_tips, str(_result))
        )

    @staticmethod
    def test_server_stream_call(case_obj, client, is_async):
        """
        测试服务端流模式调用
        """
        _tips = '测试服务端流(异步迭代函数)'
        _expect = []
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_server_stream_async', _request, call_mode=EnumCallMode.ServerSideStream
        ))

        _result_iter = RemoteCallFormater.format_call_result(_result)

        for _result in _result_iter:
            case_obj.assertTrue(
                _result.is_success(), msg='%s get resp obj error: %s' % (_tips, str(_result))
            )
            _expect.append(_result.resp)

        case_obj.assertTrue(
            TestTool.cmp_list(_expect, [1, 2, 3, 4]),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试服务端流(同步迭代函数)'
        _expect = []
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_server_stream_sync', _request, call_mode=EnumCallMode.ServerSideStream
        ))

        _result_iter = RemoteCallFormater.format_call_result(_result)

        for _result in _result_iter:
            case_obj.assertTrue(
                _result.is_success(), msg='%s get resp obj error: %s' % (_tips, str(_result))
            )
            _expect.append(_result.resp)

        case_obj.assertTrue(
            TestTool.cmp_list(_expect, [1, 2, 3, 4]),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = "测试服务端流(抛出异常)"
        _expect = []
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_server_stream_exception', _request, call_mode=EnumCallMode.ServerSideStream
        ))

        _result_iter = RemoteCallFormater.format_call_result(_result)
        _index = 0
        for _result in _result_iter:
            _index += 1
            if _index <= 2:
                case_obj.assertTrue(
                    _result.is_success(), msg='%s get resp obj error: %s' % (_tips, str(_result))
                )
                _expect.append(_result.resp)
            else:
                case_obj.assertTrue(
                    _result.code == '20408', msg='%s get resp obj except exception error: %s' % (_tips, str(_result))
                )

        case_obj.assertTrue(
            TestTool.cmp_list(_expect, [1, 2]),
            '%s error: %s' % (_tips, str(_result))
        )

    @staticmethod
    def test_bidirectional_stream_call(case_obj, client, is_async):
        """
        测试双向流模式调用
        """
        _tips = '测试双向流(异步函数, 先收再发)'
        _expect = []
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            [1, 2, 3, 4],
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )

        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_bidirectional_stream_async', _request, call_mode=EnumCallMode.BidirectionalStream
        ))

        _result_iter = RemoteCallFormater.format_call_result(_result)

        for _result in _result_iter:
            case_obj.assertTrue(
                _result.is_success() and _result.resp[0] == 10,
                msg='%s get resp obj error: %s' % (_tips, str(_result))
            )
            _expect.append(_result.resp[1])

        case_obj.assertTrue(
            TestTool.cmp_list(_expect, [1, 2, 3, 4]),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '同步函数, 边收边发'
        _expect = []
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            [1, 2, 3, 4],
            ['a_val', 'b_val'],
            {
                'c': 14
            }
        )

        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_bidirectional_stream_sync', _request, call_mode=EnumCallMode.BidirectionalStream
        ))

        _result_iter = RemoteCallFormater.format_call_result(_result)

        for _result in _result_iter:
            case_obj.assertTrue(
                _result.is_success() and _result.resp[0] == 0,
                msg='%s get resp obj error: %s' % (_tips, str(_result))
            )
            _expect.append(_result.resp[1])

        case_obj.assertTrue(
            TestTool.cmp_list(_expect, [1, 2, 3, 4]),
            '%s error: %s' % (_tips, str(_result))
        )

    @staticmethod
    def test_class_menthod_call(case_obj, client, is_async):
        """
        测试类和实例函数的调用
        """
        _tips = '测试类静态函数调用'
        _expect = ['a_val', 'b_val', ['fixed_add1', 'fixed_add2'], 14, {'d1': 'd1value'}, {'e': 'e_val'}]
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_call_para_static', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_list(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试类函数调用'
        _expect = ['a_val', 'b_val', ['fixed_add1', 'fixed_add2'], 14, {'d1': 'd1value'}, {'e': 'e_val'}]
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_call_para_class', _request
        ))
        _result = RemoteCallFormater.format_call_result(_result)
        case_obj.assertTrue(
            _result.is_success() and TestTool.cmp_list(_expect, _result.resp),
            '%s error: %s' % (_tips, str(_result))
        )

        _tips = '测试实例函数调用'
        _expect = ['a_val', 'b_val', ['fixed_add1', 'fixed_add2'], 14, {'d1': 'd1value'}, {'e': 'e_val'}]
        _request = RemoteCallFormater.paras_to_grpc_request(
            ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
            {
                'c': 14, 'e': 'e_val'
            }
        )
        _result = AsyncTools.sync_run_coroutine(client.call(
            'service_simple_call_para_member', _request
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

    @classmethod
    def setUpClass(cls):
        """
        启动测试类执行的初始化，只执行一次
        """
        # 测试没有ssl的服务
        if TEST_SERVER_ASYNC:
            _grpc_server_class = AIOGRpcServer
        else:
            _grpc_server_class = GRpcServer

        cls.server_no_ssl = _grpc_server_class(
            'server_no_ssl', server_config={
                'run_config': {
                    'host': '127.0.0.1', 'port': 50051, 'workers': 2,
                    'enable_health_check': True
                }
            },
            before_server_start=before_server_start,
            after_server_start=after_server_start,
            before_server_stop=before_server_stop,
            after_server_stop=after_server_stop
        )

        # 加载服务Simple
        _service_uri = 'service_simple_call_para'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_call_para,
        ))

        _service_uri = 'service_simple_call_para_kv'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_call_para_kv,
        ))

        _service_uri = 'service_simple_no_para'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_no_para,
        ))

        _service_uri = 'service_simple_no_para_overtime'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_no_para_overtime,
        ))

        _service_uri = 'service_simple_base_bool'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_base_bool,
        ))

        _service_uri = 'service_simple_base_str'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_base_str,
        ))

        _service_uri = 'service_simple_exception'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_simple_exception,
        ))

        # 加载服务ClientSideStream
        _service_uri = 'service_client_stream'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_client_stream, EnumCallMode.ClientSideStream
        ))

        _service_uri = 'service_client_stream_midle_return'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_client_stream_midle_return, EnumCallMode.ClientSideStream
        ))

        _service_uri = 'service_client_stream_midle_exception'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_client_stream_midle_exception, EnumCallMode.ClientSideStream
        ))

        # 加载ServerSideStream
        _service_uri = 'service_server_stream_async'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_server_stream_async, EnumCallMode.ServerSideStream
        ))

        _service_uri = 'service_server_stream_sync'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_server_stream_sync, EnumCallMode.ServerSideStream
        ))

        _service_uri = 'service_server_stream_exception'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_server_stream_exception, EnumCallMode.ServerSideStream
        ))

        # 加载BidirectionalStream
        _service_uri = 'service_bidirectional_stream_async'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_bidirectional_stream_async, EnumCallMode.BidirectionalStream
        ))

        _service_uri = 'service_bidirectional_stream_sync'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, service_bidirectional_stream_sync, EnumCallMode.BidirectionalStream
        ))

        # 测试类函数和实例函数的情况
        _service_uri = 'service_simple_call_para_static'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, ServiceClass.service_simple_call_para_static,
        ))

        _service_uri = 'service_simple_call_para_class'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, ServiceClass.service_simple_call_para_class,
        ))

        _service_class = ServiceClass()
        _service_uri = 'service_simple_call_para_member'
        _result = AsyncTools.sync_run_coroutine(cls.server_no_ssl.add_service(
            _service_uri, _service_class.service_simple_call_para_member,
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

    def test_simple_call_async(self):
        if not TEST_CONTROL['test_simple_call_async']:
            return

        print('测试简单模式调用(协程模式)')
        # 建立连接
        with AIOGRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': False, 'timeout': 3
        }) as _client:
            TestFunction.test_simple_call(self, _client, True)

    def test_simple_call_sync(self):
        if not TEST_CONTROL['test_simple_call_sync']:
            return

        print('测试简单模式调用(同步模式)')
        # 建立连接
        with GRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': True, 'timeout': 3
        }) as _client:
            TestFunction.test_simple_call(self, _client, False)

    def test_client_stream_call_async(self):
        if not TEST_CONTROL['test_client_stream_call_async']:
            return

        print('测试客户端流模式调用(协程模式)')
        # 建立连接
        with AIOGRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': False, 'timeout': 5
        }) as _client:
            TestFunction.test_client_stream_call(self, _client, True)

    def test_client_stream_call_sync(self):
        if not TEST_CONTROL['test_client_stream_call_sync']:
            return

        print('测试客户端流模式调用(同步模式)')
        # 建立连接
        with GRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': True, 'timeout': 5
        }) as _client:
            TestFunction.test_client_stream_call(self, _client, False)

    def test_server_stream_call_async(self):
        if not TEST_CONTROL['test_server_stream_call_async']:
            return

        print('测试服务端流模式调用(协程模式)')
        # 建立连接
        with AIOGRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': False, 'timeout': 5
        }) as _client:
            TestFunction.test_server_stream_call(self, _client, True)

    def test_server_stream_call_sync(self):
        if not TEST_CONTROL['test_server_stream_call_sync']:
            return

        print('测试服务端流模式调用(同步模式)')
        # 建立连接
        with GRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': True, 'timeout': 5
        }) as _client:
            TestFunction.test_server_stream_call(self, _client, False)

    def test_bidirectional_stream_call_async(self):
        if not TEST_CONTROL['test_bidirectional_stream_call_async']:
            return

        print('测试双向流模式调用(协程模式)')
        # 建立连接
        with AIOGRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': False, 'timeout': 5
        }) as _client:
            TestFunction.test_bidirectional_stream_call(self, _client, True)

    def test_bidirectional_stream_call_sync(self):
        if not TEST_CONTROL['test_bidirectional_stream_call_sync']:
            return

        print('测试服务端流模式调用(协程模式)')
        # 建立连接
        with GRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': True, 'timeout': 5
        }) as _client:
            TestFunction.test_bidirectional_stream_call(self, _client, False)

    def test_class_menthod_call_async(self):
        if not TEST_CONTROL['test_class_menthod_call_async']:
            return

        print('测试类函数及实例函数调用(协程模式)')
        # 建立连接
        with AIOGRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': False, 'timeout': 5
        }) as _client:
            TestFunction.test_class_menthod_call(self, _client, True)

    def test_class_menthod_call_sync(self):
        if not TEST_CONTROL['test_class_menthod_call_sync']:
            return

        print('测试类函数及实例函数调用(同步模式)')
        # 建立连接
        with GRpcClient({
            'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
            'use_sync_client': True, 'timeout': 5
        }) as _client:
            TestFunction.test_class_menthod_call(self, _client, False)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
