#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
grpc服务模块

@module server
@file server.py
"""
from inspect import isasyncgen, isgenerator
import os
import sys
import logging
import threading
import traceback
from concurrent import futures
from typing import Any, Callable
import grpc
import grpc._channel
import grpc.aio
from grpc_health.v1.health import HealthServicer
from grpc_health.v1 import health_pb2_grpc
from HiveNetCore.generic import CResult, NullObj
from HiveNetCore.i18n import _
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetWebUtils.server import ServerBaseFW
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.enum import EnumCallMode, EnumGRpcStatus
from HiveNetGRpc.tool import GRpcTool, ENUM_TO_GRPC_STATUS, GRPC_STATUS_TO_ENUM
import HiveNetGRpc.proto.msg_json_pb2 as msg_json_pb2
import HiveNetGRpc.proto.msg_json_pb2_grpc as msg_json_pb2_grpc


class ServiceUriNotFoundError(Exception):
    """
    服务uri不存在抛出的异常
    """
    pass


class AIOGRpcServicer(object):
    """
    grpc通用服务管理(异步IO模式, 注意不支持同步模式的GRpcServer)
    注: 管理proto相关的通讯服务类
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, service_name: str, pb2_module, pb2_grpc_module,
            error_response_func=None, logger: logging.Logger = None):
        """
        grpc通用服务管理

        @param {str} service_name - 服务名, 也就是proto文件中定义的服务名, 例如JsonService
        @param {module} pb2_module - pb2模块对象, proto文件所生成的xx_pb2.py模块对象, 例如msg_json_pb2
        @param {module} pb2_grpc_module - pb2_grpc模块对象, proto文件所生成的xx_pb2_grpc.py模块对象, 例如msg_json_pb2_grpc
        @param {function} error_response_func=None - 当遇到失败时生成响应报文的函数
            函数格式 func(request, cresult) -> xxx_pb2.RpcResponse
            注: 如果不设置, 出现异常不返回
        @param {logging.Logger} logger=None - 日志对象
        """
        # 参数处理
        self.service_name = service_name
        self._error_response_func = error_response_func
        self.logger = logger
        if logger is None:
            logging.basicConfig()
            self.logger = logging.getLogger(__name__)

        # 协议模块处理
        self._pb2_module = pb2_module
        self._pb2_grpc_module = pb2_grpc_module
        # 添加服务对象到服务器的函数
        self.add_servicer_to_server = eval('self._pb2_grpc_module.add_%sServicer_to_server' % self.service_name)

        # 可执行服务列表, 分别对应GRpcCall、...
        # 统一格式, key为服务名, value为执行信息字典{'handler': 执行函数func, 'kwargs': add_service传入的kwargs}
        #   func的格式统一为 func(request/request_iterator, context)
        self._service_list_mapping = {
            EnumCallMode.Simple: {},  # 简单调用的可执行的服务列表
            EnumCallMode.ClientSideStream: {},  # 客户端流式的可执行的服务列表
            EnumCallMode.ServerSideStream: {},  # 服务端流式的可执行的服务列表
            EnumCallMode.BidirectionalStream: {}  # 双向数据流模式的可执行的服务列表
        }

        self._dealing_num = 0  # 当前正在处理的报文数
        self._dealing_num_lock = threading.RLock()  # 为保证缓存信息的一致性, 需要控制的锁

        # 服务名参数
        self._app_name = ''

    #############################
    # 公共函数
    #############################
    def set_app_name(self, app_name: str):
        """
        设置服务的app_name
        注: 主要用于输出日志显示

        @param {str} app_name - 应用名
        """
        self._app_name = app_name

    def add_service(self, service_uri: str, handler: Callable, call_mode: EnumCallMode = EnumCallMode.Simple,
            **kwargs) -> CResult:
        """
        添加请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {Callable} handler - 请求处理函数, 可同时支持同步或异步函数
            函数格式统一为 func(request) -> xxx_pb2.RpcResponse
                其中, request为请求字典:
                {
                    'request': request/request_iterator,  # 请求报文对象, 如果是流模式则为请求报文对象的迭代器
                    'context': context,  # 请求服务端上下文, grpc.ServicerContext
                    'call_mode': call_mode  # 调用模式
                }
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 服务调用模式
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21405'-服务名已存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            if service_uri == '':
                # 服务标识不可为空
                return CResult(code='11006', i18n_msg_paras=('service_uri'))

            for _dict in self._service_list_mapping.values():
                if service_uri in _dict.keys():
                    # 服务名已存在, 返回错误
                    return CResult(code='21405', i18n_msg_paras=(service_uri, ))

            # 添加服务
            self._service_list_mapping[call_mode][service_uri] = {
                'handler': handler, 'kwargs': kwargs
            }

        return _result

    def remove_service(self, service_uri: str, **kwargs) -> CResult:
        """
        移除请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21403'-服务不存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('remove service error'))
        ):
            _paras = self._service_router.pop(service_uri, None)
            if _paras is None:
                # 服务名不存在, 返回错误
                _result = CResult(code='21403', i18n_msg_paras=(service_uri, ))

        return _result

    def clear_service(self, **kwargs) -> CResult:
        """
        清空请求处理服务

        @returns {CResult} - 清空结果, result.code: '00000'-成功, '21403'-服务不存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self.logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('clear service error'))
        ):
            for _dict in self._service_list_mapping.values():
                _dict.clear()

        return _result

    #############################
    # gRPC的标准接入服务接口
    #############################
    async def GRpcCallSimple(self, request, context):
        """
        简单模式(Simple)gRPC的标准接入服务接口

        @param {xxx_pb2.RpcRequest} request - 请求对象, 与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {xxx_pb2.RpcResponse} - 返回调用结果信息
        """
        return await self._common_call(request, context, EnumCallMode.Simple)

    async def GRpcCallClientSideStream(self, request_iterator, context):
        """
        客户端流模式(ClientSideStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器(msg_pb2.RpcRequest), 单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {xxx_pb2.RpcResponse} - 返回调用结果信息
        """
        return await self._common_call(request_iterator, context, EnumCallMode.ClientSideStream)

    async def GRpcCallServerSideStream(self, request, context):
        """
        服务器流模式(ServerSideStream)gRPC的标准接入服务接口

        @param {xxx_pb2.RpcRequest} request - 请求对象, 与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息(xxx_pb2.RpcResponse)的迭代器(iterator)
        """
        async for _resp in self._common_call_back_iter(request, context, EnumCallMode.ServerSideStream):
            yield _resp

    async def GRpcCallBidirectionalStream(self, request_iterator, context):
        """
        双向流模式(BidirectionalStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器(msg_pb2.RpcRequest), 单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息(msg_pb2.RpcResponse)的迭代器(iterator)
        """
        async for _resp in self._common_call_back_iter(request_iterator, context, EnumCallMode.BidirectionalStream):
            yield _resp

    def GRpcCallHealthCheck(self, request, context):
        """
        自定义的健康检查服务

        @param {xxx_pb2.HealthRequest} request - 请求对象, 与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {xxx_pb2.HealthResponse} - 返回调用结果信息
        """
        return self._pb2_module.HealthResponse(status=self._pb2_module.HealthResponse.SERVING)

    #############################
    # 内部函数
    #############################
    def _dealing_num_addon(self, add_num):
        """
        修改正在处理报文数量(通过所控制一致性)

        @param {int} add_num - 增加或减少的值, 减少传入复数即可
        """
        self._dealing_num_lock.acquire()
        try:
            self._dealing_num = self._dealing_num + add_num
        finally:
            self._dealing_num_lock.release()

    async def _common_call(self, request, context, call_mode) -> Any:
        """
        通用的请求函数调用
        注: 四种类型的调用处理都一致,

        @param {xxx_pb2.RpcRequest|iterator} request - 请求对象或获取请求对象的迭代器
        @param {grpc.ServicerContext} context - 服务端上下文对象
        @param {EnumCallMode} call_mode - 请求类型

        @returns {msg_pb2.RpcResponse|iterator} - 返回结果, 或者是迭代对象
        """
        # 正在处理报文计数+1
        self._dealing_num_addon(1)
        _request = {
            'request': request,  # 请求报文对象, 如果是流模式则为请求报文对象的迭代器
            'context': context,  # 请求服务端上下文, grpc.ServicerContext
            'call_mode': call_mode  # 调用模式
        }
        try:
            # 获取uri, uri正常是从metadata中送入
            _metadata = GRpcTool.metadata_to_dict(context)
            _uri = _metadata.get('uri', '')

            # 获取执行函数
            _deal_func_paras = self._service_list_mapping[call_mode].get(_uri, None)
            if _deal_func_paras is None:
                # uri不存在
                raise ServiceUriNotFoundError()
            else:
                _deal_func = _deal_func_paras['handler']

            # 执行处理函数
            return await AsyncTools.async_run_coroutine(
                _deal_func(_request)
            )
        except ServiceUriNotFoundError:
            # 服务不存在
            self.logger.warning('[SER][NAME:%s]%s: %s' % (self._app_name, _('call uri no exists'), _uri))
            if self._error_response_func is not None:
                _result = CResult(code='11403', i18n_msg_paras=(_uri, ))
                return self._error_response_func(_request, _result)
            else:
                raise
        except:
            # 出现异常, 执行打印处理
            _error = str(sys.exc_info()[0])
            trace_str = traceback.format_exc()
            self.logger.error(
                '[EX:%s]%s' % (_error, trace_str)
            )
            if self._error_response_func is not None:
                _result = CResult(
                    code='31008', error=_error, trace_str=trace_str, i18n_msg_paras=(_error, )
                )
                return self._error_response_func(_request, _result)
            else:
                raise
        finally:
            # 正在处理报文计数-1
            self._dealing_num_addon(-1)

    async def _common_call_back_iter(self, request, context, call_mode):
        """
        通用的请求函数调用(迭代器形式返回)

        @param {xxx_pb2.RpcRequest|iterator} request - 请求对象或获取请求对象的迭代器
        @param {grpc.ServicerContext} context - 服务端上下文对象
        @param {EnumCallMode} call_mode - 请求类型

        @returns {iterator} - 返回迭代对象
        """
        # 正在处理报文计数+1
        self._dealing_num_addon(1)
        _request = {
            'request': request,  # 请求报文对象, 如果是流模式则为请求报文对象的迭代器
            'context': context,  # 请求服务端上下文, grpc.ServicerContext
            'call_mode': call_mode  # 调用模式
        }
        try:
            # 获取uri, uri正常是从metadata中送入
            _metadata = GRpcTool.metadata_to_dict(context)
            _uri = _metadata.get('uri', '')

            # 获取执行函数
            _deal_func_paras = self._service_list_mapping[call_mode].get(_uri, None)
            if _deal_func_paras is None:
                # uri不存在
                raise ServiceUriNotFoundError()
            else:
                _deal_func = _deal_func_paras['handler']

            # 执行处理函数
            _result = await AsyncTools.async_run_coroutine(
                _deal_func(_request)
            )

            # 根据不同迭代类型返回处理
            if isgenerator(_result) == 'generator':
                for _ret in _result:
                    yield _ret
            elif isasyncgen(_result):
                async for _ret in _result:
                    yield _ret
            else:
                yield _result
        except ServiceUriNotFoundError:
            # 服务不存在
            self.logger.warning('[SER][NAME:%s]%s: %s' % (self._app_name, _('call uri no exists'), _uri))
            if self._error_response_func is not None:
                _result = CResult(code='11403', i18n_msg_paras=(_uri, ))
                yield self._error_response_func(_request, _result)
            else:
                raise
        except:
            # 出现异常, 执行打印处理
            _error = str(sys.exc_info()[0])
            trace_str = traceback.format_exc()
            self.logger.error(
                '[EX:%s]%s' % (_error, trace_str)
            )
            if self._error_response_func is not None:
                _result = CResult(
                    code='31008', error=_error, trace_str=trace_str, i18n_msg_paras=(_error, )
                )
                yield self._error_response_func(_request, _result)
            else:
                raise
        finally:
            # 正在处理报文计数-1
            self._dealing_num_addon(-1)


class GRpcServicer(AIOGRpcServicer):
    """
    grpc通用服务管理(同步模式)
    """

    #############################
    # 异步转同步
    #############################
    def GRpcCallSimple(self, request, context):
        """
        简单模式(Simple)gRPC的标准接入服务接口

        @param {xxx_pb2.RpcRequest} request - 请求对象, 与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {xxx_pb2.RpcResponse} - 返回调用结果信息
        """
        return AsyncTools.sync_run_coroutine(super().GRpcCallSimple(request, context))

    def GRpcCallClientSideStream(self, request_iterator, context):
        """
        客户端流模式(ClientSideStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器(msg_pb2.RpcRequest), 单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {xxx_pb2.RpcResponse} - 返回调用结果信息
        """
        return AsyncTools.sync_run_coroutine(super().GRpcCallClientSideStream(
            request_iterator, context
        ))

    def GRpcCallServerSideStream(self, request, context):
        """
        服务器流模式(ServerSideStream)gRPC的标准接入服务接口

        @param {xxx_pb2.RpcRequest} request - 请求对象, 与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息(xxx_pb2.RpcResponse)的迭代器(iterator)
        """
        return AsyncTools.sync_for_async_iter(super().GRpcCallServerSideStream(
            request, context
        ))

    def GRpcCallBidirectionalStream(self, request_iterator, context):
        """
        双向流模式(BidirectionalStream)gRPC的标准接入服务接口

        @param {iterator} request_iterator - 请求对象迭代器(msg_pb2.RpcRequest), 单个对象与msg.proto定义一致,
          例如可通过request.para_json获取要执行的函数的入参信息
        @param {grpc.ServicerContext} context - 服务端的上下文,
          具体定义@see https://grpc.github.io/grpc/python/grpc.html#service-side-context

        @retrun {iterator} - 返回调用结果信息(msg_pb2.RpcResponse)的迭代器(iterator)
        """
        return AsyncTools.sync_for_async_iter(super().GRpcCallBidirectionalStream(
            request_iterator, context
        ))


class AIOGRpcServer(ServerBaseFW):
    """
    grpc服务(异步IO模式)
    """

    #############################
    # 通用服务框架函数重载
    #############################

    def __init__(self, app_name: str, server_config: dict = {}, support_auths: dict = {},
            before_server_start=None, after_server_start=None,
            before_server_stop=None, after_server_stop=None, logger=None, log_level: int = logging.INFO,
            load_i18n_para=None, **kwargs):
        """
        构造函数

        @param {str} app_name - 服务器名称
        @param {dict} server_config={} - 服务配置字典
            run_config {dict} - 运行参数字典, 参数包括:
                host {str} - 绑定的主机地址, 默认为''
                port {int} - 服务监听的端口, 默认为50051
                workers {int} - 最大工作线程数, 默认为1
                max_connect {int} - 允许最大连接数, 默认为20
                enable_health_check {bool} - 是否启用健康检查服务, 默认为False
                auto_enable_service {bool} - 是否自动启用加载的服务, 默认为True
                use_ssl {bool} - 是否使用SSL/TLS - 默认为False
                ssl {list[dict]} - 使用ssl时的证书配置, 允许送入多套, dict信息支持两种送入的方式
                    1、使用证书文件二进制数据 {'cert': crt证书bytes, 'key': 私钥bytes}
                        例如:
                        with open('server.pem', 'rb') as f:
                            private_key = f.read()  # 服务器端的私钥文件
                        with open('server.crt', 'rb') as f:
                            certificate_chain = f.read()  # 服务器端的公钥证书文件
                        ssl = {'cert': certificate_chain, 'key': private_key}
                    2、使用证书文件路径 {'cert': '/path/to/server.crt', 'key': '/path/to/server.pem'}
                root_certificates {str|bytes} - 客户端反向认证时(验证客户端证书)的客户端根证书, 即客户端的公钥证书文件
                    多客户端反向认证时, 客户端证书应基于同一个根证书签发, 这里使用根证书的公钥证书文件
                    1、字符形式传文件路径, 例如'/path/to/ca.crt'
                    2、字节数组形式,例如:
                        with open('ca.crt', 'rb') as f:
                            root_certificates = f.read()
            grpc_config {dict} - grpc其他的原生参数
                options {list} - grpc选项数组, 可参考grpc的原生函数说明, 例如:
                    [('grpc.max_send_message_length', 最大发送消息长度), ('grpc.max_receive_message_length', 最大接收消息长度)]
                compression {} - grpc的压缩选项, 例如: grpc.compression.Gzip
                handlers {} - An optional list of GenericRpcHandlers used for executing RPCs. More handlers may be added by calling add_generic_rpc_handlers any time before the server is started
                interceptors {} - An optional list of ServerInterceptor objects that observe and optionally manipulate the incoming RPCs before handing them over to handlers. The interceptors are given control in the order they are specified
        @param {dict} support_auths={} - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
            注意: 支持的auth对象必须有auth_required这个修饰符函数
        @param {function} before_server_start=None - 服务器启动前执行的函数对象, 传入服务自身(self)
        @param {function} after_server_start=None - 服务器启动后执行的函数对象, 传入服务自身(self)
        @param {function} before_server_stop=None - 服务器关闭前执行的函数对象, 传入服务自身(self)
        @param {function} after_server_stop=None - 服务器关闭后执行的函数对象, 传入服务自身(self)
        @param {Logger} logger=None - 自定义应用逻辑使用的日志对象
        @param {int} log_level=logging.INFO - 一般信息的记录使用的日志级别
        @param {dict} load_i18n_para=None - 要装载的i18n语言文件配置
            path {str} - 要加载的i18n字典文件路径, 如果填空代表程序运行的当前路径
            prefix {str} - 要加载的i18n字典文件前缀
            encoding {str} - 要加载的i18n字典文件的字符编码, 默认为'utf-8'
        @param {kwargs} - 实现类自定义扩展参数
            servicer_mapping {dict} - 服务对象映射字典, key为服务对象标识, value为服务对象实例
                注意: 如果不设置, 将自动构建一个JsonService服务对象
        """
        # 指定当前服务为异步模式
        self._grpc_server_async = True

        # 引用框架的构造函数
        super().__init__(
            app_name, server_config=server_config, support_auths=support_auths,
            before_server_start=before_server_start,
            after_server_start=after_server_start, before_server_stop=before_server_stop,
            after_server_stop=after_server_stop, logger=logger, log_level=log_level,
            load_i18n_para=load_i18n_para, **kwargs
        )

    #############################
    # 自己的通用函数
    #############################
    def set_service_status(self, servicer_name, status_code: EnumGRpcStatus):
        """
        设置服务可用状态

        @param {string} servicer_name - 要设置的服务名, 如果为''则代表设置所有服务
        @param {EnumGRpcStatus} status_code - 要设置的服务状态
        """
        if self._server_config.get('run_config', {}).get('enable_health_check', False):
            if servicer_name == '':
                # 设置所有服务
                for _servicer_name in self._servicer_mapping.keys():
                    self._grpc_health_servicer.set(
                        _servicer_name, ENUM_TO_GRPC_STATUS[status_code]
                    )
            else:
                # 设置单个服务
                self._grpc_health_servicer.set(
                    servicer_name, ENUM_TO_GRPC_STATUS[status_code]
                )

    def get_service_status(self, servicer_name='') -> EnumGRpcStatus:
        """
        获取服务可用状态

        @param {string} servicer_name - 要获取的服务名, 如果为''则代表获取所有服务状态汇总

        @return {EnumGRpcStatus} - 获取到的状态值
            注意: 如果传入的服务名为空, 则会检查所有服务的状态, 只要有一个不可用, 都会返回不可用的状态, 返回的优先级别为
            EnumGRpcStatus.Unknow、EnumGRpcStatus.ServiceUnknown、
            EnumGRpcStatus.NotServing、EnumGRpcStatus.NotFound
            注意: 如果服务名不存在, 返回EnumGRpcStatus.NotFound
        """
        if servicer_name == '':
            # 通过递归方式获取所有服务的状态
            _all_status = EnumGRpcStatus.NotFound
            for _servicer_name in self._servicer_mapping.keys():
                _status = self.get_service_status(_servicer_name)
                if _status == EnumGRpcStatus.Unknow:
                    # 已经是最差的状态了
                    _all_status = _status
                    break
                elif _all_status in (EnumGRpcStatus.NotFound, EnumGRpcStatus.Serving):
                    # 比最好状态差, 直接赋值
                    _all_status = _status
                elif _all_status == EnumGRpcStatus.NotServing and _status in (
                    EnumGRpcStatus.ServiceUnknown
                ):
                    _all_status = _status
                else:
                    # 其他情况不处理
                    pass

            # 循环检查完成
            return _all_status
        else:
            # 获取指定服务状态
            with self._grpc_health_servicer._lock:
                _status = self._grpc_health_servicer._server_status.get(servicer_name)
                if _status is None:
                    return EnumGRpcStatus.NotFound
                else:
                    return GRPC_STATUS_TO_ENUM[_status]

    #############################
    # 需要重载的通用函数
    #############################

    async def add_service(self, service_uri: str, handler: Callable,
            call_mode: EnumCallMode = EnumCallMode.Simple, servicer_name: str = 'JsonService',
            **kwargs) -> CResult:
        """
        添加请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {Callable} handler - 请求处理函数, 应可同时支持同步或异步函数
            函数格式统一为 func(request) -> xxx_pb2.RpcResponse
            其中, request为请求字典:
            {
                'request': request/request_iterator,  # 请求报文对象, 如果是流模式则为请求报文对象的迭代器
                'context': context,  # 请求服务端上下文, grpc.ServicerContext
                'call_mode': call_mode  # 调用模式
            }
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用模式
        @param {str} servicer_name='JsonService' - 服务对象名
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21405'-服务名已存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            if service_uri in self._service_router.keys():
                # 服务名已存在, 返回错误
                _result = CResult(code='21405', i18n_msg_paras=(service_uri, ))
            else:
                # 添加到服务对象
                _servicer = self._servicer_mapping[servicer_name]
                _result = _servicer.add_service(
                    service_uri, handler, call_mode=call_mode
                )

                if _result.is_success():
                    # 本地也记录一下, 在删除时使用
                    self._service_router[service_uri] = {
                        'handler': handler, 'kwargs': kwargs
                    }

        return _result

    async def remove_service(self, service_uri: str, **kwargs) -> CResult:
        """
        移除请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21403'-服务不存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('remove service error'))
        ):
            _paras = self._service_router.pop(service_uri, None)
            if _paras is None:
                # 服务名不存在, 返回错误
                _result = CResult(code='21403', i18n_msg_paras=(service_uri, ))

            # 从servicer删除
            _kwargs = _paras['kwargs']
            _servicer = self._servicer_mapping[_kwargs.get('servicer_name', 'JsonService')]
            _result = _servicer.remove_service(service_uri)

        return _result

    #############################
    # 实现类需重载的内部函数
    #############################
    def _std_init_config(self):
        """
        标准化服务初始配置
        """
        # 服务对象映射字典
        self._servicer_mapping = self._kwargs.get('servicer_mapping', None)
        if self._servicer_mapping is None:
            # 没有设置则自动创建一个
            if self._grpc_server_async:
                # 异步io模式
                _servicer_class = AIOGRpcServicer
            else:
                _servicer_class = GRpcServicer

            _JsonService = _servicer_class(
                'JsonService', msg_json_pb2, msg_json_pb2_grpc, logger=self._logger
            )
            self._servicer_mapping = {
                'JsonService': _JsonService
            }

        # 初始化GRPC服务参数
        _run_config = self._server_config.get('run_config', {})
        _grpc_config = self._server_config.get('grpc_config', {})

        self._grpc_server = None
        self._grpc_init_args = [
            futures.ThreadPoolExecutor(max_workers=_run_config.get('workers', 1)), # 最大连接数
        ]
        self._grpc_init_kwargs = {
            'maximum_concurrent_rpcs': _run_config.get('max_connect', 20), # 最大连接数
            'options': _grpc_config.get('options', None),
            'compression': _grpc_config.get('compression', None),
            'handlers': _grpc_config.get('handlers', None),
            'interceptors': _grpc_config.get('interceptors', None)
        }

        # 监听服务参数
        self._grpc_host_str = ('%s:%s' % (
            _run_config.get('host', ''), _run_config.get('port', 50051))
        )
        self._ssl_server_credentials = None
        if _run_config.get('use_ssl', False):
            # 处理证书服务端证书
            _private_key_certificate_chain_pairs = []
            for _ssl in _run_config.get('ssl', []):
                if type(_ssl['cert']) == str:
                    with open(_ssl['cert'], 'rb') as f:
                        _certificate_chain = f.read()  # 服务器端的公钥证书文件
                else:
                    _certificate_chain = _ssl['cert']

                if type(_ssl['key']) == str:
                    with open(_ssl['key'], 'rb') as f:
                        _private_key = f.read()  # 服务器端的私钥文件
                else:
                    _private_key = _ssl['key']

                _private_key_certificate_chain_pairs.append(
                    (_private_key, _certificate_chain)
                )

            # 处理客户端反向认证根证书
            _root_certificates = _run_config.get('root_certificates', None)
            if _root_certificates is not None and type(_root_certificates) == str:
                with open(_root_certificates, 'rb') as f:
                    _root_certificates = f.read()

            # 使用SSL加密传输
            self._ssl_server_credentials = grpc.ssl_server_credentials(
                _private_key_certificate_chain_pairs,
                root_certificates=_root_certificates,
                require_client_auth=(_root_certificates is not None)
            )

        # 注册健康检查服务
        self._grpc_health_servicer = None
        if _run_config.get('enable_health_check', False):
            self._grpc_health_servicer = HealthServicer()

    async def _real_server_initialize(self, tid) -> CResult:
        """
        初始化真正的服务端处理对象

        @param {int} tid - 服务线程id

        @returns {CResult} - 启动结果:
            result.code: '00000'-成功, 其他值为失败
            result.server_info: 启动成功后的服务信息, 用于传递到后续的服务处理函数
        """
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(_result):
            # 初始化GRPC服务
            if self._grpc_server_async:
                # 异步io模式
                self._grpc_server = grpc.aio.server(
                    *self._grpc_init_args, **self._grpc_init_kwargs
                )
            else:
                # 非异步io模式
                self._grpc_server = grpc.server(
                    *self._grpc_init_args, **self._grpc_init_kwargs
                )

            # 注册健康检查服务
            if self._grpc_health_servicer is not None:
                health_pb2_grpc.add_HealthServicer_to_server(
                    self._grpc_health_servicer, self._grpc_server
                )

            # 向服务注册处理对象
            for _servicer_name, _servicer in self._servicer_mapping.items():
                _servicer.set_app_name(self.app_name)  # 设置打印显示名
                _servicer.add_servicer_to_server(
                    _servicer, self._grpc_server
                )
                self.set_service_status(_servicer_name, EnumGRpcStatus.Unknow)

            # 设置监听服务
            if self._ssl_server_credentials is not None:
                # 使用SSL加密传输
                self._grpc_server.add_secure_port(self._grpc_host_str, self._ssl_server_credentials)
            else:
                # 非加密方式访问
                self._grpc_server.add_insecure_port(self._grpc_host_str)

            # 启动服务
            await AsyncTools.async_run_coroutine(
                self._grpc_server.start()
            )

            # 启动后是否自动对外提供服务
            if self._server_config.get('run_config', {}).get('auto_enable_service', True):
                self.set_service_status('', EnumGRpcStatus.Serving)

        # 返回处理结果
        _result.server_info = None
        return _result

    async def _real_server_prepare_stop(self, tid) -> CResult:
        """
        服务关闭前的处理函数
        注: 支持同步或异步函数, 可以在该函数中等待已接入的请求或线程完成处理

        @param {int} tid - 线程id

        @returns {CResult} - 处理结果:
            result.code: '00000'-成功, 其他值为失败
            result.is_finished: 指示停止前的预处理是否已完成, True - 已处理完成可停止服务, False - 未完成, 需循环继续调用本函数
        """
        _result = CResult(code='00000')  # 成功
        _result.is_finished = True
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER-PRE-STOP][NAME:%s]%s: ' % (
                self._app_name, _('stop net server error')),
            force_log_level=logging.ERROR
        ):
            # 停止前先将服务状态值为不可用, 让其他服务不再访问
            self.set_service_status('', EnumGRpcStatus.NotServing)
            # 检查是否有正在处理的报文
            for _servicer_name, _servicer in self._servicer_mapping.items():
                if hasattr(_servicer, 'dealing_num') and _servicer.dealing_num > 0:
                    # 还有报文没有处理完
                    _result.is_finished = False
                    break

        return _result

    async def _real_server_stop(self, tid, server_info):
        """
        真正服务的关闭处理
        注: 支持同步或异步函数, 可以在该函数中清理处理线程并关闭监听

        @param {int} tid - 线程id
        @param {Any} server_info - 启动成功后的服务信息
        """
        # 子类必须定义该功能
        with ExceptionTool.ignored_all(
            logger=self._logger,
            self_log_msg='[SER-STOP][NAME:%s]%s error: ' % (
                self._app_name, _('stop net server error')
            )
        ):
            # 停止服务
            await AsyncTools.async_run_coroutine(self._grpc_server.stop(0))

            # 停止完成更新状态为未知
            self.set_service_status('', EnumGRpcStatus.Unknow)


class GRpcServer(AIOGRpcServer):
    """
    grpc服务(同步模式)
    """

    #############################
    # 异步转同步函数
    #############################
    def add_service(self, service_uri: str, handler: Callable,
            call_mode: EnumCallMode = EnumCallMode.Simple, servicer_name: str = 'JsonService',
            **kwargs) -> CResult:
        """
        添加请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {Callable} handler - 请求处理函数, 应可同时支持同步或异步函数
            函数格式统一为 func(request) -> xxx_pb2.RpcResponse
            其中, request为请求字典:
            {
                'request': request/request_iterator,  # 请求报文对象, 如果是流模式则为请求报文对象的迭代器
                'context': context,  # 请求服务端上下文, grpc.ServicerContext
                'call_mode': call_mode  # 调用模式
            }
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用模式
        @param {str} servicer_name='JsonService' - 服务对象名
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21405'-服务名已存在, 其他-异常
        """
        return AsyncTools.sync_run_coroutine(super().add_service(
            service_uri, handler, call_mode=call_mode, servicer_name=servicer_name,
            **kwargs
        ))

    def remove_service(self, service_uri: str, **kwargs) -> CResult:
        """
        移除请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21403'-服务不存在, 其他-异常
        """
        return AsyncTools.sync_run_coroutine(super().remove_service(
            service_uri, **kwargs
        ))

    #############################
    # 重载_std_init_config
    #############################

    def _std_init_config(self):
        """
        标准化服务初始配置
        """
        # 指定当前服务为同步模式
        self._grpc_server_async = False
        super()._std_init_config()


