#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
消息格式化模块

@module msg_formater
@file msg_formater.py
"""
import json
import os
from re import I
import sys
import logging
import traceback
from logging import Logger
from functools import wraps
from inspect import isasyncgen, isawaitable, isgenerator
import grpc._channel
import grpc.aio._call
from HiveNetCore.generic import CResult
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.string_tool import StringTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.enum import EnumCallMode
from HiveNetGRpc.proto import msg_json_pb2


class RemoteCallFormater(object):
    """
    远程调用函数的消息格式化类
    (基于默认的JsonService报文格式进行处理)
    """
    #############################
    # 修饰函数
    #############################
    @classmethod
    def format_service(cls, with_request: bool = True, native_request: bool = False, logger: Logger = None):
        """
        服务端处理函数的请求格式转换修饰函数
        注: 支持修饰同步及异步函数, 但修饰后需按异步函数执行

        @param {bool} with_request=True - 是否将请求对象送入处理函数的参数中执行
            注1: 如果为True则代表会将原始请求对象送入处理函数(作为第一个参数送入)
            注2: 如果是流模式, 该参数固定为True, 并且会将原请求request字典中的'request'对象替换为第二个迭代值开始的json字典的迭代对象
        @param {bool} native_request=False - 送入的请求对象是否原生请求对象(RpcRequest)
            注: 如果请求数据包含extend_bytes的信息, 则应设置为True以获取到对应的值, 否则只能获取到return_json的值
        @param {Logger} logger=None - 日志对象
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                _logger = cls._get_logger(logger)
                _resp_obj = None  # 响应对象
                try:
                    # 正常情况只传入一个request参数字典
                    if len(args) > 1:
                        # 是类函数
                        _request = args[1]
                    else:
                        _request = args[0]

                    # 处理函数入参
                    if _request['call_mode'] in (EnumCallMode.Simple, EnumCallMode.ServerSideStream):
                        # 传入的是单个请求对象
                        _args, _kwargs = cls.service_request_to_paras(
                            _request, with_request=with_request, native_request=native_request
                        )
                    else:
                        # 传入的是迭代器
                        _args, _kwargs = cls.service_request_to_paras_iter(
                            _request, native_request=native_request
                        )

                    # 处理类函数的第一个参数
                    if len(args) > 1:
                        _args.insert(0, args[0])
                except:
                    # 处理传入参数的异常
                    _error = str(sys.exc_info()[0])
                    _err_msg = 'argument consistency error'
                    _traceback_str = traceback.format_exc()
                    _logger.warning(
                        'deal with para_json error, [%s]%s: %s' % (
                            _error, _err_msg, _traceback_str
                        )
                    )
                    _resp_obj = cls.service_exception_to_grpc_resp(
                        '21003', _error, _err_msg
                    )

                # 执行函数对象
                if _resp_obj is None:
                    try:
                        _resp_obj = f(*_args, **_kwargs)
                        if isawaitable(_resp_obj):
                            _resp_obj = await _resp_obj
                    except:
                        # 执行函数出现异常
                        _error = str(sys.exc_info()[0])
                        _err_msg = 'remote function execute raise exception'
                        _traceback_str = traceback.format_exc()
                        _logger.error(
                            'call service function error, [%s]%s: %s' % (
                                _error, _err_msg, _traceback_str
                            )
                        )
                        _resp_obj = cls.service_exception_to_grpc_resp(
                            '31008', _error, _err_msg
                        )

                # 返回结果处理
                try:
                    return cls.service_resp_to_grpc_resp(_resp_obj, _request['call_mode'])
                except:
                    # 处理返回结果出现异常
                    _error = str(sys.exc_info()[0])
                    _err_msg = 'deal with response error'
                    _traceback_str = traceback.format_exc()
                    _logger.warning(
                        'deal with service function response error, [%s]%s: %s' % (
                            _error, _err_msg, _traceback_str
                        )
                    )
                    _resp_obj = cls.service_exception_to_grpc_resp(
                        '31001', _error, _err_msg
                    )
                    return cls.service_resp_to_grpc_resp(_resp_obj, _request['call_mode'])

            return decorated_function

        return decorator

    #############################
    # 服务端工具函数
    #############################
    @classmethod
    def service_request_to_paras(cls, request: dict, with_request: bool = True,
            native_request: bool = False) -> tuple:
        """
        服务端请求对象转换为函数入参

        @param {dict} request - 服务的请求入参字典
            {
                'request': request,  # 请求报文对象(如果是流模式也需获取对应的请求报文对象)
                'context': context,  # 请求服务端上下文, grpc.ServicerContext
                'call_mode': call_mode  # 调用模式
            }
        @param {bool} with_request=True - 是否将请求对象送入处理函数的参数中执行
        @param {bool} native_request=False - 送入的请求对象是否原生请求对象(RpcRequest)
            注: 如果请求数据包含extend_bytes的信息, 则应设置为True以获取到对应的值, 否则只能获取到return_json的值

        @returns {tuple} - 返回函数入参的二元组(args, kwargs)
        """
        _args = []
        _kwargs = {}

        # 按标准处理参数
        _para_json = StringTool.json_loads_hive_net(
            request['request'].para_json
        )

        if with_request:
            # 请求对象送入处理函数的参数
            if native_request:
                _args.append(request)
            else:
                _args.append({
                    'request': _para_json,
                    'context': request['context'],
                    'call_mode': request['call_mode']
                })

        _args.extend(_para_json.get('args', []))
        _kwargs.update(_para_json.get('kwargs', {}))

        # 返回结果
        return _args, _kwargs

    @classmethod
    def service_request_to_paras_iter(cls, request: dict, native_request: bool = False) -> tuple:
        """
        服务端迭代类型的请求对象转换为函数入参及迭代对象
        注: 第一个迭代值固定为函数入参, 后面的迭代值则转换为json值的迭代

        @param {dict} request - 服务的请求入参字典
            {
                'request': request_iterator,  # 流模式的请求对象迭代器
                'context': context,  # 请求服务端上下文, grpc.ServicerContext
                'call_mode': call_mode  # 调用模式
            }
        @param {bool} native_request=False - 送入的请求对象是否原生请求对象(RpcRequest)
            注: 如果请求数据包含extend_bytes的信息, 则应设置为True以获取到对应的值, 否则只能获取到return_json的值

        @returns {tuple} - 返回函数入参的二元组(args, kwargs)
        """
        # 先分离第一个对象和第二个开始的值迭代器
        _request, _value_iter = cls._get_service_request_json_iter(
            request['request'], native_request=native_request
        )

        _temp_request = {
            'request': _request,
            'context': request['context'],
            'call_mode': request['call_mode']
        }

        # 获取函数入参
        _args, _kwargs = cls.service_request_to_paras(
            _temp_request, with_request=True, native_request=native_request
        )

        # 替换请求对象并送入处理函数
        _temp_request['request'] = _value_iter
        _args[0] = _temp_request

        return _args, _kwargs

    @classmethod
    def service_exception_to_grpc_resp(cls, code: str, error: str, err_msg: str,
            msg_para: tuple = ()) -> msg_json_pb2.RpcResponse:
        """
        服务端异常信息转换为grpc的响应对象

        @param {str} code - 错误码
        @param {str} error - 抛出异常时，异常对象的类型
        @param {str} err_msg - 错误信息
        @param {tuple} msg_para - 错误信息对应的参数, JSON格式, 数组()

        @returns {msg_json_pb2.RpcResponse} - 返回的grpc响应对象
        """
        return msg_json_pb2.RpcResponse(
            return_json='', call_code=code, call_msg=err_msg, call_error=error,
            call_msg_para=json.dumps(msg_para, ensure_ascii=False)
        )

    @classmethod
    def service_resp_to_grpc_resp(cls, obj, call_mode: EnumCallMode, extend_bytes: bytes = None):
        """
        将服务端函数返回对象转换为服务返回的grpc对象或迭代器

        @param {Any} obj - 要处理的对象
        @param {EnumCallMode} call_mode - 请求模式
        @param {bytes} extend_bytes = None - 要返回的扩展字节数组
            注: 如果传入的对象已经是msg_json_pb2.RpcResponse或迭代器则不会处理

        @returns {msg_json_pb2.RpcResponse|iterator} - 返回grpc对象或迭代器
        """
        if call_mode in (EnumCallMode.Simple, EnumCallMode.ClientSideStream):
            # 返回的是对象
            return cls._service_resp_obj_to_grpc_resp(obj, extend_bytes=extend_bytes)
        else:
            # 需要返回迭代器
            return cls._service_resp_obj_to_grpc_async_iter(obj)

    #############################
    # 客户端工具函数
    #############################
    @classmethod
    def paras_to_grpc_request(cls, args: list = None, kwargs: dict = None) -> msg_json_pb2.RpcRequest:
        """
        将函数入参转换为grpc请求对象

        @param {list} args=None - 函数固定参数
        @param {dict} kwargs=None - 函数kv参数

        @returns {msg_json_pb2.RpcRequest} - 请求对象
        """
        _args = [] if args is None else args
        _kwargs = {} if kwargs is None else kwargs

        return msg_json_pb2.RpcRequest(
            para_json=StringTool.json_dumps_hive_net(
                {
                    'args': _args, 'kwargs': _kwargs
                }, ensure_ascii=False
            )
        )

    @classmethod
    def paras_to_grpc_request_iter(cls, iter_obj, args: list = None, kwargs: dict = None):
        """
        将迭代对象和函数入参转换为grpc请求对象迭代对象(流模式)

        @param {generator|async_generator} iter_obj - 要发送的请求数据迭代对象(支持同步或异步)
        @param {list} args=None - 函数固定参数
        @param {dict} kwargs=None - 函数kv参数

        @returns {generator} - 请求迭代对象
        """
        # 第一个迭代对象是函数调用参数
        yield cls.paras_to_grpc_request(args, kwargs)

        # 从后面开始放送数据
        for _data in AsyncTools.sync_for_async_iter(iter_obj):
            if isinstance(_data, msg_json_pb2.RpcRequest):
                # 已经是标准请求对象, 无需转换
                yield _data
            else:
                yield msg_json_pb2.RpcRequest(
                    para_json=StringTool.json_dumps_hive_net(_data, ensure_ascii=False)
                )

    @classmethod
    def format_call_result(cls, call_result: CResult) -> CResult:
        """
        将GRpcClient调用返回的结果转换为标准CResult对象

        @param {CResult} call_result - grpc客户端的call函数返回结果

        @returns {CResult} - 标准CResult对象
            cresult.resp - 远程调用的返回值
            cresult.extend_bytes - 扩展返回的字节数组
        """
        if not call_result.is_success():
            # 本身调用失败
            call_result.resp = None
            return call_result
        else:
            if isgenerator(call_result.resp) or isasyncgen(call_result.resp) or getattr(call_result.resp, '__next__', None) is not None:
                # 是迭代对象, 需要将call_result.resp转换为标准的CResult的迭代对象
                return cls._client_grpc_iter_to_cresult_iter(call_result.resp)
            else:
                # 正常对象处理
                return cls._client_grpc_resp_to_cresult(call_result.resp)

    #############################
    # 内部函数
    #############################
    @classmethod
    def _get_logger(cls, logger: Logger) -> Logger:
        """
        获取日志对象

        @param {Logger} logger - 送入的日志对象
            注: 如果送None代表自动创建一个日志对象

        @returns {Logger} - 返回的日志对象
        """
        if logger is None:
            logging.basicConfig()
            _logger = logging.getLogger(__name__)
            _logger.level = logging.INFO
            return _logger
        else:
            return logger

    @classmethod
    def _get_service_request_json_iter(cls, request_iter, native_request: bool = False) -> tuple:
        """
        获取服务端请求的json迭代对象

        @param {Any} request_iter - 流模式的请求对象迭代器
        @param {list} out_first_obj=[] - 要返回的第一个request对象(放入数组)
        @param {bool} native_request=False - 送入的请求对象是否原生请求对象(RpcRequest)
            注: 如果请求数据包含extend_bytes的信息, 则应设置为True以获取到对应的值, 否则只能获取到return_json的值

        @returns {tuple} - 返回第一个迭代值和剩余迭代器的数组(first, iter)
        """
        # 获取第一个迭代对象
        if hasattr(request_iter, '__anext__'):
            _first = AsyncTools.sync_run_coroutine(
                request_iter.__anext__()
            )
        else:
            # 非异步模式, 需要用for才能获取到第一个对象
            for _item in request_iter:
                _first = _item
                break

        return _first, cls._service_request_iter_to_json_iter(
            request_iter, native_request=native_request
        )

    @classmethod
    def _service_request_iter_to_json_iter(cls, request_iter, native_request: bool = False):
        """
        将服务端请求数据迭代对象转换为json迭代对象

        @param {iter} request_iter - 请求迭代对象(第二个开始)
        @param {bool} native_request=False - 送入的请求对象是否原生请求对象(RpcRequest)
            注: 如果请求数据包含extend_bytes的信息, 则应设置为True以获取到对应的值, 否则只能获取到return_json的值

        @returns {iter} - 如果native_request为False返回转换的json字典迭代对象, 否则返回原生的RpcRequest迭代对象
        """
        if hasattr(request_iter, '__anext__'):
            # 异步模式
            while True:
                try:
                    _item = AsyncTools.sync_run_coroutine(
                        request_iter.__anext__()
                    )
                    if native_request:
                        yield _item
                    else:
                        yield StringTool.json_loads_hive_net(_item.para_json)
                except StopAsyncIteration:
                    break
        else:
            # 同步模式
            for _item in request_iter:
                if native_request:
                    yield _item
                else:
                    yield StringTool.json_loads_hive_net(_item.para_json)

    @classmethod
    def _service_resp_obj_to_grpc_resp(cls, obj, extend_bytes: bytes = None) -> msg_json_pb2.RpcResponse:
        """
        将服务端函数返回的单个对象转换为msg_json_pb2.RpcResponse对象(服务端使用)

        @param {Any} obj - 要转换的对象
        @param {bytes} extend_bytes = None - 要返回的扩展字节数组
            注: 如果传入的对象已经是msg_json_pb2.RpcResponse则不会处理

        @returns {msg_json_pb2.RpcResponse} - grpc的响应对象
        """
        if isinstance(obj, msg_json_pb2.RpcResponse):
            # 无需转换
            return obj

        return msg_json_pb2.RpcResponse(
            return_json=StringTool.json_dumps_hive_net(obj, ensure_ascii=False),
            extend_bytes=extend_bytes,
            call_code='00000',
            call_msg='success',
            call_error='',
            call_msg_para='[]'
        )

    @classmethod
    async def _service_resp_obj_to_grpc_async_iter(cls, obj):
        """
        将服务端返回对象转换为异步迭代grpc响应对象(服务端使用)

        @param {Any} obj - 要处理的对象
        """
        if isgenerator(obj):
            # 普通迭代器
            for _iter_item in obj:
                yield cls._service_resp_obj_to_grpc_resp(_iter_item)
        elif isasyncgen(obj):
            # 异步迭代器
            async for _iter_item in obj:
                yield cls._service_resp_obj_to_grpc_resp(_iter_item)
        else:
            # obj是单个对象
            yield cls._service_resp_obj_to_grpc_resp(obj)

    @classmethod
    def _client_grpc_resp_to_cresult(cls, grpc_resp: msg_json_pb2.RpcResponse) -> CResult:
        """
        客户端将单个grpc响应对象转换为CResult对象

        @param {msg_json_pb2.RpcResponse} grpc_resp - grpc的响应对象

        @returns {CResult} - 标准CResult对象
            cresult.resp - 远程调用的返回值
            cresult.extend_bytes - 扩展返回的字节数组
        """
        _result = CResult(
            code=grpc_resp.call_code, msg=grpc_resp.call_msg, error=grpc_resp.call_error,
            i18n_msg_paras=[] if grpc_resp.call_msg_para == '' else StringTool.json_loads_hive_net(
                grpc_resp.call_msg_para
            )
        )
        _result.resp = None if grpc_resp.return_json == '' else StringTool.json_loads_hive_net(
            grpc_resp.return_json
        )
        _result.extend_bytes = grpc_resp.extend_bytes

        return _result

    @classmethod
    def _client_grpc_iter_to_cresult_iter(cls, obj):
        """
        将grpc流模式返回的迭代响应对象转换为CResult迭代对象

        @param {iter} obj - 迭代对象
        """
        try:
            for _resp in AsyncTools.sync_for_async_iter(obj):
                yield cls._client_grpc_resp_to_cresult(_resp)
        except (grpc._channel._Rendezvous, grpc._channel._InactiveRpcError):
            # 执行远程调用出现异常
            _code = '20408'
            _grpc_err = sys.exc_info()[1]
            if _grpc_err._state.code.value[0] == 4:
                # 调用超时
                _code = '30403'
            _result = CResult(
                code=_code,
                error=str(type(_grpc_err)),
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_grpc_err._state.code.name, _grpc_err._state.details)
            )
            _result.resp = None
            yield _result
        except (grpc.aio._call.AioRpcError):
            # 执行远程调用出现异常(异步的情况)
            _code = '20408'
            _aio_grpc_error = sys.exc_info()[1]
            _state_code = _aio_grpc_error.code()
            if _state_code.value[0] == 4:
                # 调用超时
                _code = '30403'
            _result = CResult(
                code=_code,
                error=str(type(_aio_grpc_error)),
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_state_code.name, _aio_grpc_error.details())
            )
            _result.resp = None
            yield _result
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
            _result.resp = None
            yield _result

