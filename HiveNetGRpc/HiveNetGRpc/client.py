#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
grpc客户端模块

@module client
@file client.py
"""
import os
import sys
import traceback
import grpc
import grpc.aio
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from HiveNetCore.generic import CResult
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetWebUtils.client import ClientBaseFw
from HiveNetCore.connection_pool import PoolConnectionFW
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.enum import EnumCallMode, EnumGRpcStatus
from HiveNetGRpc.tool import GRPC_STATUS_TO_ENUM
import HiveNetGRpc.proto.msg_json_pb2 as msg_json_pb2
import HiveNetGRpc.proto.msg_json_pb2_grpc as msg_json_pb2_grpc


class AIOGRpcClient(ClientBaseFw):
    """
    异步模式的GRpc客户端连接
    """

    #############################
    # 重载构造函数
    #############################
    def __init__(self, conn_config: dict, **kwargs):
        """
        异步模式的GRpc客户端连接

        @param {dict} conn_config - 连接参数, 定义如下:
            host {str} - 要连接的服务器IP, 默认为''
                注意: TSLSSL模式, 客户端是通过"服务名称:port"来获取服务的凭据，而不是"ip:port",
                如果使用TSL/SSL的情况客户端连接失败, 可从这个角度排查解决问题
            port {int} - 要连接的服务器端口, 默认为50051
            conn_str {str} - 连接字符串, 如果传入该字符串则不再使用ip和端口方式连接
                连接字符串的格式如下: 'ip协议(ipv4|ipv6):///ip1:port1,ip2:port2,...'
            timeout {float} - 超时时间，单位为秒, 不传代表不设置超时时间
            use_ssl {bool} - 是否使用SSL/TLS, 默认为False
            root_certificates {str|bytes} - 用于验证服务器证书的根证书，即服务器端的公钥证书
                1、字符形式传文件路径, 例如'/path/to/ca.crt'
                2、字节数组形式,例如:
                    with open('ca.crt', 'rb') as f:
                        root_certificates = f.read()
            ssl {dict} - 当反向认证时(服务器验证客户端证书)，客户端的证书, 支持两种送入的方式
                1、使用证书文件二进制数据 {'cert': crt证书bytes, 'key': 私钥bytes}
                    例如:
                    with open('clent.pem', 'rb') as f:
                        private_key = f.read()  # 客户端的私钥文件
                    with open('client.crt', 'rb') as f:
                        certificate_chain = f.read()  # 客户端的公钥证书
                    ssl = {'cert': certificate_chain, 'key': private_key}
                2、使用证书文件路径 {'cert': '/path/to/clent.pem', 'key': '/path/to/clent.crt'}
            ping_on_connect {bool} - 连接时进行有效性测试, 默认为False
            ping_with_health_check {bool} - 使用标准的health_check进行测试, 默认为False
            options {list} -  grpc选项数组, 可参考grpc的原生函数说明
            compression {Any} - grpc的压缩选项, 例如: grpc.compression.Gzip
            service_name {str} service_name='JsonService' - 服务名, 也就是proto文件中定义的服务名, 默认为'JsonService'
            pb2_module {module} - pb2模块对象, proto文件所生成的xx_pb2.py模块对象, 默认为msg_json_pb2
            pb2_grpc_module {module} - pb2_grpc模块对象, proto文件所生成的xx_pb2_grpc.py模块对象, 默认为msg_json_pb2_grpc
            use_sync_client {bool} - 是否使用grpc的同步客户端模式, 默认为False
                注: 默认使用asyncio模式, 但目前该模式存在一个bug, 会打印BlockingIOError异常信息, 如果不希望存在该bug, 可以使用同步模式的客户端
                该bug的issues: https://github.com/grpc/grpc/issues/25364
        @param {kwargs} - 扩展参数, 由实现类自定义
        """
        super().__init__(conn_config, **kwargs)

    #############################
    # 重载公共函数
    #############################
    async def ping(self, *args, **kwargs):
        """
        检测连接是否有效

        @returns {CResult} - 响应对象, 如果返回结果为失败代表检查失败
            ret.status 为 EnumGRpcStatus的枚举值
        """
        _check_result = CResult(code='00000')
        _check_result.status = EnumGRpcStatus.Unknow
        with ExceptionTool.ignored_cresult(_check_result):
            if self._channel is None:
                # 没有连接
                _check_result.change_code('23002', i18n_msg_paras=('connect'))
                _check_result.status = EnumGRpcStatus.Unknow
            elif self._conn_config['ping_with_health_check']:
                # 使用标准健康检查
                self._health_stub = self._generate_health_check_stub(self._channel)
                _check_result = await self._health_check_by_stub(
                    self._health_stub, self._conn_config['servicer_name'],
                    timeout=self._conn_config['timeout']
                )
            else:
                # 使用自定义的健康检查
                _check_result = self._self_health_check_by_stub(
                    self._stub, timeout=self._conn_config['timeout']
                )

        # 返回结果
        return _check_result

    async def close(self):
        """
        关闭连接
        """
        if self._channel is not None:
            await AsyncTools.async_run_coroutine(
                self._channel.close()
            )
            self._channel = None
            self._stub = None
            self._health_stub = None

    async def reconnect(self, *args, **kwargs):
        """
        重新连接

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
            ret.status 为 EnumGRpcStatus的枚举值
        """
        # 先关闭连接
        await AsyncTools.async_run_coroutine(self.close())

        # 进行连接
        self._channel = self._generate_channel()
        self._stub = self._generate_call_stub(self._channel)

        # 检查连接有效性
        if self._conn_config['ping_on_connect']:
            _ping_result = await AsyncTools.async_run_coroutine(
                self.ping()
            )
            return _ping_result
        else:
            # 不检查的情况，直接返回成功，连接状态为SERVING
            _check_result = CResult('00000')
            _check_result.status = EnumGRpcStatus.Serving
            return _check_result

    async def call(self, service_uri: str, request, call_mode=EnumCallMode.Simple,
             timeout: float = None, metadata=None, credentials=None,
             wait_for_ready=None, compression=None, **kwargs):
        """
        执行gRPC远程调用

        @param {str} service_uri - 要请求的服务唯一标识
        @param {xxx_pb2.RpcRequest|request_iterator} request - 请求对象或产生请求对象的迭代器(iterator), 应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式
        @param {float} timeout=None - 超时时间，单位为秒
        @param {object} metadata=None - Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
        @param {object} credentials=None - An optional CallCredentials for the RPC. Only valid for
            secure Channel.
        @param {object} wait_for_ready=None - This is an EXPERIMENTAL argument. An optional
            flag to enable wait for ready mechanism
        @param {object} compression=None - An element of grpc.compression, e.g.
            grpc.compression.Gzip. This is an EXPERIMENTAL option.
        @param {**kwargs} kwargs - 动态参数，用于支持调用链信息

        @returns {CResult} - 执行结果CResult
            cresult.resp {xxx_pb2.RpcResponse|iterator} - 响应对象, 如果服务器端返回流则是迭代器对象
            注: 如果客户端是同步模式, 流模式返回的是同步迭代对象, 客户端异步模式返回的是异步迭代对象
        """
        # 处理超时时间
        _timeout = timeout
        if timeout is None or timeout <= 0:
            _timeout = self._conn_config['timeout']

        # 处理metadata, 添加访问的uri信息
        _metadata = [] if metadata is None else metadata
        _metadata = list(_metadata)
        _metadata.append(('uri', service_uri))

        return await self._grpc_call_by_stub(
            self._stub, rpc_request=request, call_mode=call_mode,
            timeout=_timeout, metadata=_metadata, credentials=credentials,
            wait_for_ready=wait_for_ready, compression=compression
        )

    #############################
    # 需重载的内部函数
    #############################
    def _std_init_config(self):
        """
        标准化客户端初始配置
        """
        # 设置入参的默认值
        _conn_config = {
            'host': '',
            'port': 50051,
            'conn_str': None,
            'timeout': None,
            'use_ssl': False,
            'root_certificates': None,
            'ssl': None,
            'ping_on_connect': False,
            'ping_with_health_check': False,
            'options': None,
            'compression': None,
            'servicer_name': 'JsonService',
            'pb2_module': msg_json_pb2,
            'pb2_grpc_module': msg_json_pb2_grpc,
            'use_sync_client': False
        }
        _conn_config.update(self._conn_config)
        self._conn_config = _conn_config

        # 连接字符串
        if self._conn_config['conn_str'] is None:
            self._conn_config['conn_str'] = '%s:%s' % (
                self._conn_config['host'], str(self._conn_config['port'])
            )

        # ssl
        self._ssl_channel_credentials = None
        if self._conn_config['use_ssl']:
            # 验证服务器证书的根证书
            _root_certificates = self._conn_config['root_certificates']
            if _root_certificates is not None and type(_root_certificates) == str:
                with open(_root_certificates, 'rb') as f:
                    _root_certificates = f.read()

            # 反向验证的证书
            _private_key = None
            _certificate_chain = None
            _ssl = self._conn_config['ssl']
            if _ssl is not None:
                _private_key = _ssl.get('key', None)
                _certificate_chain = _ssl.get('cert', None)
                if _private_key is not None and type(_private_key) == str:
                    with open(_private_key, 'rb') as f:
                        _private_key = f.read()

                if _certificate_chain is not None and type(_certificate_chain) == str:
                    with open(_certificate_chain, 'rb') as f:
                        _certificate_chain = f.read()

            # 证书对象
            self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                root_certificates=_root_certificates,
                private_key=_private_key,
                certificate_chain=_certificate_chain
            )

        # 进行连接
        self._channel = self._generate_channel()
        self._stub = self._generate_call_stub(self._channel)

        # 检查连接有效性
        if self._conn_config['ping_on_connect']:
            _ping_result = AsyncTools.sync_run_coroutine(self.ping())
            if not _ping_result.is_success():
                # 连接失败
                raise ConnectionError('%s, grpc status: %s\ntrace_str: %s' % (
                    _ping_result.msg, _ping_result.status, _ping_result.trace_str)
                )

    #############################
    # 内部函数
    #############################
    def _generate_channel(self):
        """
        生成gRPC通道, 注意该通道需要后端主动关闭

        @return {grpc.Channel} - gRPC连接通道
        """
        _channel = None

        if self._ssl_channel_credentials is not None:
            # 使用SSL验证
            if self._conn_config['use_sync_client']:
                _create_channel_func = grpc.secure_channel
            else:
                _create_channel_func = grpc.aio.secure_channel

            _channel = _create_channel_func(
                self._conn_config['conn_str'], self._ssl_channel_credentials,
                options=self._conn_config['options'],
                compression=self._conn_config['compression']
            )
        else:
            # 不使用SSL验证
            if self._conn_config['use_sync_client']:
                _create_channel_func = grpc.insecure_channel
            else:
                _create_channel_func = grpc.aio.insecure_channel

            _channel = _create_channel_func(
                self._conn_config['conn_str'],
                options=self._conn_config['options'],
                compression=self._conn_config['compression']
            )
        return _channel

    def _generate_call_stub(self, channel):
        """
        生成gRPC桩代码对象(stub code, 可以理解为映射服务端的占坑代码)

        @param {grpc.Channel} channel - gRPC连接通道

        @return {xxx_pb2_grpc.SimpleGRpcServiceStub} - SimpleGRpc的桩代码对象
        """
        return eval(
            "self._conn_config['pb2_grpc_module'].%sStub(channel)" % self._conn_config['servicer_name']
        )

    def _generate_health_check_stub(self, channel):
        """
        生成gRPC标准的服务健康检查桩代码对象(stub code, 可以理解为映射服务端的占坑代码)

        @param {grpc.Channel} channel - gRPC连接通道

        @return {health_pb2_grpc.HealthStub} - 标准健康检查的桩代码对象
        """
        return health_pb2_grpc.HealthStub(channel)

    async def _health_check_by_stub(self, stub, servicer_name: str, timeout: float = None):
        """
        基于stub对象gRPC标准的服务健康检查

        @param {health_pb2_grpc.HealthStub} stub - 已连接的stub对象
        @param {string} servicer_name - 要检查的服务名
        @param {float} timeout=None - 超时时间，单位为秒

        @returns {CResult} - 响应对象, 如果返回结果为为成功代表检查失败
            ret.status 为 EnumGRpcStatus的枚举值
        """
        _result = CResult(code='00000')
        _result.status = EnumGRpcStatus.Unknow
        try:
            _result = CResult(code='00000')
            _resp_obj = await AsyncTools.async_run_coroutine(stub.Check(
                health_pb2.HealthCheckRequest(service=servicer_name),
                timeout=timeout
            ))
            _result.status = GRPC_STATUS_TO_ENUM[_resp_obj.status]
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
            _result.status = EnumGRpcStatus.Unknow
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
            _result.status = EnumGRpcStatus.Unknow
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                msg='call grpc error',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
            _result.status = EnumGRpcStatus.Unknow

        # 返回处理结果
        return _result

    async def _self_health_check_by_stub(self, stub, timeout: float = None):
        """
        自定义的健康检查, 访问健康检查服务

        @param {xxx_pb2_grpc.SimpleGRpcServiceStub} stub - 已连接的stub对象
        @param {float} timeout=None - 超时时间，单位为秒

        @returns {CResult} - 响应对象, 如果返回结果为为成功代表检查失败
            ret.status 为 EnumGRpcStatus的枚举值
        """
        _result = CResult(code='00000')
        _result.status = EnumGRpcStatus.Unknow
        try:
            _result = CResult(code='00000')
            _resp_obj = await AsyncTools.async_run_coroutine(stub.GRpcCallHealthCheck(
                self._pb2_module.HealthRequest(service=''),
                timeout=timeout
            ))
            _result.status = GRPC_STATUS_TO_ENUM[_resp_obj.status]
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
            _result.status = EnumGRpcStatus.Unknow
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
            _result.status = EnumGRpcStatus.Unknow
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
            _result.status = EnumGRpcStatus.Unknow

        # 返回处理结果
        return _result

    async def _grpc_call_by_stub(self, stub, rpc_request, call_mode=EnumCallMode.Simple,
                          timeout=None, metadata=None, credentials=None,
                          wait_for_ready=None, compression=None):
        """
        基于stub对象执行远程调用

        @param {xxx_pb2_grpc.XXXStub} stub - 已连接的stub对象
        @param {xxx_pb2.RpcRequest|request_iterator} rpc_request - 请求对象或产生请求对象的迭代器(iterator), 应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式
        @param {number} timeout=None - 超时时间，单位为秒
        @param {object} metadata=None - Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
        @param {object} credentials=None - An optional CallCredentials for the RPC. Only valid for
            secure Channel.
        @param {object} wait_for_ready=None - This is an EXPERIMENTAL argument. An optional
            flag to enable wait for ready mechanism
        @param {object} compression=None - An element of grpc.compression, e.g.
            grpc.compression.Gzip. This is an EXPERIMENTAL option.

        @returns {CResult} - 执行结果CResult
            cresult.resp {xxx_pb2.RpcResponse|iterator} - 响应对象, 如果服务器端返回流则是迭代器对象
            注: 如果客户端是同步模式, 流模式返回的是同步迭代对象, 客户端异步模式返回的是异步迭代对象
        """
        _result = CResult(code='00000')
        try:
            if call_mode == EnumCallMode.ServerSideStream:
                _resp_obj = await AsyncTools.async_run_coroutine(stub.GRpcCallServerSideStream(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                ))
                # 兼容同步和异步流处理返回值不同的情况
                if getattr(_resp_obj, '_fetch_stream_responses', None) is not None:
                    _resp_obj = _resp_obj._fetch_stream_responses()
            elif call_mode == EnumCallMode.ClientSideStream:
                _resp_obj = await AsyncTools.async_run_coroutine(stub.GRpcCallClientSideStream(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                ))
            elif call_mode == EnumCallMode.BidirectionalStream:
                _resp_obj = await AsyncTools.async_run_coroutine(stub.GRpcCallBidirectionalStream(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                ))
                # 兼容同步和异步流处理返回值不同的情况
                if getattr(_resp_obj, '_fetch_stream_responses', None) is not None:
                    _resp_obj = _resp_obj._fetch_stream_responses()
            else:
                # 简单模式
                _resp_obj = await AsyncTools.async_run_coroutine(stub.GRpcCallSimple(
                    rpc_request, timeout=timeout, metadata=metadata, credentials=credentials,
                    wait_for_ready=wait_for_ready, compression=compression
                ))

            # 设置返回对象
            _result.resp = _resp_obj
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
        except:
            _error = str(sys.exc_info()[0])
            _result = CResult(
                code='21007',
                error=_error,
                trace_str=traceback.format_exc(),
                i18n_msg_paras=(_error)
            )
            _result.resp = None

        # 返回结果
        return _result


class GRpcClient(AIOGRpcClient):
    """
    GRpc客户端连接
    """

    #############################
    # 重载公共函数
    #############################
    def ping(self, *args, **kwargs):
        """
        检测连接是否有效

        @returns {CResult} - 响应对象, 如果返回结果为失败代表检查失败
            ret.status 为 EnumGRpcStatus的枚举值
        """
        return AsyncTools.sync_run_coroutine(
            super().ping(*args, **kwargs)
        )

    def close(self):
        """
        关闭连接
        """
        return AsyncTools.sync_run_coroutine(super().close())

    def reconnect(self, *args, **kwargs):
        """
        重新连接

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
            ret.status 为 EnumGRpcStatus的枚举值
        """
        return AsyncTools.sync_run_coroutine(
            super().reconnect(*args, **kwargs)
        )

    def call(self, service_uri: str, request, call_mode=EnumCallMode.Simple,
             timeout: float = None, metadata=None, credentials=None,
             wait_for_ready=None, compression=None, **kwargs):
        """
        执行gRPC远程调用

        @param {str} service_uri - 要请求的服务唯一标识
        @param {xxx_pb2.RpcRequest|request_iterator} request - 请求对象或产生请求对象的迭代器(iterator), 应与call_mode匹配
        @param {EnumCallMode} call_mode=EnumCallMode.Simple - 调用服务端的模式
        @param {float} timeout=None - 超时时间，单位为秒
        @param {object} metadata=None - Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
        @param {object} credentials=None - An optional CallCredentials for the RPC. Only valid for
            secure Channel.
        @param {object} wait_for_ready=None - This is an EXPERIMENTAL argument. An optional
            flag to enable wait for ready mechanism
        @param {object} compression=None - An element of grpc.compression, e.g.
            grpc.compression.Gzip. This is an EXPERIMENTAL option.
        @param {**kwargs} kwargs - 动态参数，用于支持调用链信息

        @returns {CResult} - 执行结果CResult
            cresult.resp {xxx_pb2.RpcResponse|iterator} - 响应对象, 如果服务器端返回流则是迭代器对象
            注: 如果客户端是同步模式, 流模式返回的是同步迭代对象, 客户端异步模式返回的是异步迭代对象
        """
        _ret = AsyncTools.sync_run_coroutine(
            super().call(
                service_uri, request, call_mode=call_mode, timeout=timeout, metadata=metadata,
                credentials=credentials, wait_for_ready=wait_for_ready, compression=compression,
                **kwargs
            )
        )

        return _ret


class GRpcPoolConnection(PoolConnectionFW):
    """
    支持通过AIOConnectionPool连接池管理的连接适配器
    注: 传入AIOConnectionPool的参数要求如下:
        creator - 客户端连接对象类: AIOGRpcClient或GRpcClient
        pool_connection_class - 连接池连接对象的实现类: GRpcPoolConnection
        args - 客户端连接对象初始化参数: [conn_config]
        connect_method_name - 不设置, 直接使用creator初始化: None
    """

    #############################
    # 需要继承类实现的函数
    #############################
    async def _real_ping(self, *args, **kwargs) -> bool:
        """
        实现类的真实检查连接对象是否有效的的函数

        @returns {bool} - 返回检查结果
        """
        _result = AsyncTools.sync_run_coroutine(
            self._conn.ping(*args, **kwargs)
        )
        return _result.is_success()

    async def _fade_close(self):
        """
        实现类提供的虚假关闭函数
        注1: 不关闭连接, 只是清空上一个连接使用的上下文信息(例如数据库连接进行commit或rollback处理)
        注2: 如果必须关闭真实连接, 则可以关闭后创建一个新连接返回

        @returns {Any} - 返回原连接或新创建的连接
        """
        # 直接返回原连接
        return self._conn

    async def _real_close(self):
        """
        实现类提供的真实关闭函数
        """
        AsyncTools.sync_run_coroutine(
            self._conn.close()
        )
