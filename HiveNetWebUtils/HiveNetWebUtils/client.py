#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
客户端连接的通用框架

@module client
@file client.py
"""
import sys
import os
import copy
import ssl
from typing import Any
import aiohttp
from aiohttp.http import HttpVersion
from HiveNetCore.generic import CResult
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.string_tool import StringTool
from pyparsing import traceback
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


class ClientBaseFw(object):
    """
    客户端连接基础框架
    """

    #############################
    # 构造函数和析构函数
    #############################
    def __init__(self, conn_config: dict, **kwargs):
        """
        客户端连接构造函数

        @param {dict} conn_config - 连接参数, 由实现类自定义
        @param {kwargs} - 扩展参数, 由实现类自定义
        """
        self._conn_config = conn_config
        self._kwargs = kwargs
        # 调用实现类的初始化处理函数
        self._std_init_config()

    def __del__(self):
        """
        析构函数
        """
        AsyncTools.sync_run_coroutine(self.close())

    #############################
    # 支持with方式调用
    #############################
    def __enter__(self):
        """
        with进入调用的函数
        """
        # 需要返回对象自身
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        with退出的函数

        @param {?} exc_type - 异常类型
        @param {?} exc_val - 异常值
        @param {?} exc_tb - tracback信息
        """
        # 退出是关闭连接
        AsyncTools.sync_run_coroutine(self.close())

    #############################
    # 需要重载的公共函数
    #############################
    async def ping(self, *args, **kwargs) -> CResult:
        """
        检测连接是否有效
        (可为同步或异步函数)

        @param {args} - 检测函数的固定入参
        @param {kwargs} - 检测函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表检查失败
            注: 应将ret.status 设置为明细的检查结果值(例如状态码), 具体值由实现类定义
        """
        _ret = CResult(code='00000')
        _ret.status = None

        # 返回结果
        return _ret

    async def close(self):
        """
        关闭连接
        (可为同步或异步函数)
        """
        raise NotImplementedError()

    async def reconnect(self, *args, **kwargs) -> CResult:
        """
        重新连接
        (可为同步或异步函数)

        @param {args} - 重新连接函数的固定入参
        @param {kwargs} - 重新连接函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
        """
        raise NotImplementedError()

    async def call(self, service_uri: str, request, *args, **kwargs) -> CResult:
        """
        执行远程调用

        @param {str} service_uri - 请求的服务uri或唯一标识
        @param {Any} request - 请求对象, 由实现类定义对象类型
        @param {args} - 远程调用的固定入参
        @param {kwargs} - 远程调用的kv入参

        @returns {CResult} - 执行结果CResult
            注: 建议将请求的返回对象放到 cresult.resp 属性中
        """
        raise NotImplementedError()

    #############################
    # 需重载的内部函数
    #############################
    def _std_init_config(self):
        """
        标准化客户端初始配置
        """
        # 实现类可以通过该函数设置或修改内部参数
        pass


class AIOHttpClient(ClientBaseFw):
    """
    异步模式的Http客户端连接
    """

    #############################
    # 重载构造函数
    #############################
    def __init__(self, conn_config: dict, **kwargs):
        """
        Http客户端连接

        @param {dict} conn_config - 连接参数, 定义如下:
            protocol {str} - 通讯协议, 支持http, https, 默认为'http'
            host {str} - 要连接的服务器IP或域名, 默认为'127.0.0.1'
            port {int} - 要连接的服务器端口, 默认为80
            conn_str {str} - 连接字符串, 如果传入该字符串则不再使用ip和端口方式连接
                连接字符串的格式如下: 'http://ip:port'
            timeout {float} - 超时时间，单位为秒, 不传代表不设置超时时间
            headers {dict} - 全局的http头字典
            json_ensure_ascii {bool} - 转换json字符串是严格为ascii编码, 默认为False
            cafile {str} - 证书文件名称, 例如'ca.crt'
            capath {str} - 证书文件路径
            certfile {str} - cert证书文件路径, 例如'xxx/xxx.pem'
            keyfile {str} - 证书key文件路径, 例如'xxx/xxx.key'
            http_ver {tuple} - http协议版本, (主版本号, 次版本号), 默认为(1, 1)
            aiohttp_session_paras {dict} - aiohttp.ClientSession的全局调用参数
            aiohttp_request_paras {dict} - aiohttp.ClientSession.request的全局调用参数
        """
        super().__init__(conn_config, **kwargs)

    #############################
    # 需要重载的公共函数
    #############################
    async def ping(self, *args, **kwargs) -> CResult:
        """
        检测连接是否有效
        (可为同步或异步函数)

        @param {args} - 检测函数的固定入参
        @param {kwargs} - 检测函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表检查失败
            注: 应将ret.status 设置为明细的检查结果值(例如状态码), 具体值由实现类定义
        """
        _ret = CResult(code='00000')
        _ret.status = None

        # 返回结果
        return _ret

    async def close(self):
        """
        关闭连接
        (可为同步或异步函数)
        """
        pass

    async def reconnect(self, *args, **kwargs) -> CResult:
        """
        重新连接
        (可为同步或异步函数)

        @param {args} - 重新连接函数的固定入参
        @param {kwargs} - 重新连接函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
        """
        pass

    async def call(self, service_uri: str, request: Any = None, headers: dict = {}, method: str = 'GET',
            timeout: float = None, bytes_read_size: int = -1, **kwargs) -> CResult:
        """
        执行远程调用

        @param {str} service_uri - 请求的服务uri, 可以为完整的url字符串, 也可以仅为访问路径url
            注: 如果仅为访问路径url, 将拼接客户端对象的初始化host和端口
        @param {Any} request=None - 请求对象(要发送的内容), 可以支持Python的基础数据类型
        @param {dict} headers={} - 当前请求的http头字典
            注: 如果与全局http头重复的项将进行覆盖
        @param {str} method='GET' - 请求的方法
        @param {float} timeout=None - 指定本次请求的超时时间
        @param {int} bytes_read_size=-1 - 二进制数据读取缓存大小, 如果设置为-1代表一次性读取所有内容
        @param {kwargs} - aiohttp.ClientSession.request的其他可选参数

        @returns {CResult} - 执行结果CResult
            _result.resp 是标准响应内容字典, 格式为:
                url {str} - 访问的url
                status {int} - 返回状态码
                headers {dict} - 返回报文头
                data {bytes|asyncgen} - 返回内容, 如果bytes_read_size为-1则是全部的字节数组, 否则为异步迭代对象(每次返回指定大小的数组)
        """
        # 要访问的url
        _url = service_uri if service_uri.startswith('http://') or service_uri.startswith('https://') else '%s%s' % (
            self._base_url, service_uri.lstrip('/')
        )

        # 其他请求参数的处理
        _headers = copy.deepcopy(self._headers)
        _headers.update(headers)
        _timeout = self._timeout if timeout is None else timeout
        _aiohttp_request_paras = copy.copy(self._aiohttp_request_paras)
        _aiohttp_request_paras.update(kwargs)

        # 处理发送对象
        _send_data = None if request is None else self._obj_to_request(request, _headers)

        _std_resp = {} # 标准响应对象
        try:
            async with aiohttp.ClientSession(
                headers=_headers,
                timeout=aiohttp.ClientTimeout(total=_timeout),
                connector=aiohttp.TCPConnector(enable_cleanup_closed=True),
                version=self._http_ver, **self._aiohttp_session_paras
            ) as _session:
                # 真正进行调用
                try:
                    async with _session.request(
                        method, _url, data=_send_data, ssl=self._ssl, **_aiohttp_request_paras
                    ) as _response:
                        # 处理标准响应信息
                        _std_resp['url'] = _response.url
                        _std_resp['status'] = _response.status
                        _std_resp['headers'] = {}
                        for _item in _response.headers.items():
                            _std_resp['headers'][_item[0].lower()] = _item[1]

                        # 获取内容
                        if bytes_read_size > 0:
                            # 分次获取二进制流数据的方式
                            _std_resp['data'] = self._resp_bytes_to_async_iter(
                                _response, bytes_read_size
                            )
                        else:
                            _std_resp['data'] = await _response.read()
                            if _std_resp['status'] == 200 and _std_resp['data'] == '':
                                _std_resp['data'] = None

                        # 返回处理结果
                        _result = CResult(code='00000')
                        _result.resp = _std_resp
                        return _result
                except Exception as _err:
                    # 已经发起远程调用, 如果出现异常都视为未知类的异常
                    _result = CResult(
                        code='31007', error=str(_err), trace_str=traceback.format_exc()
                    )
                    _result.resp = _std_resp
                    return _result
        except Exception as _err:
            # 未发起远程调用, 异常视为失败
            _result = CResult(
                code='21007', error=str(_err), trace_str=traceback.format_exc()
            )
            _result.resp = _std_resp
            return _result

    #############################
    # 需重载的内部函数
    #############################
    def _std_init_config(self):
        """
        标准化客户端初始配置
        """
        # 初始化的基础连接url
        self._base_url = self._conn_config.get('conn_str', None)
        if self._base_url is None or self._base_url == '':
            self._base_url = '%s://%s:%d/' % (
                self._conn_config.get('protocol', 'http'),
                self._conn_config.get('host', '127.0.0.1'),
                self._conn_config.get('port', 80),
            )
        elif not self._base_url.endswith('/'):
            self._base_url = '%s/' % self._base_url

        # 证书处理
        if self._conn_config.get('cafile', None) is None:
            self._ssl = False
        else:
            self._ssl = ssl.create_default_context(
                cafile=self._conn_config['cafile'], capath=self._conn_config['capath']
            )
            if self._conn_config.get('certfile', None) is not None:
                self._ssl.load_cert_chain(
                    self._conn_config['certfile'], self._conn_config['keyfile']
                )

        # 其他常用参数
        self._timeout = self._conn_config.get('timeout', 60.0)
        self._headers = self._conn_config.get('headers', {})
        _http_ver = self._conn_config.get('http_ver', (1, 1))
        self._http_ver = HttpVersion(_http_ver[0], _http_ver[1])
        self._aiohttp_session_paras = self._conn_config.get('aiohttp_session_paras', {})
        self._aiohttp_request_paras = self._conn_config.get('aiohttp_request_paras', {})

    #############################
    # 内部函数
    #############################
    def _obj_to_request(self, obj: Any, headers: dict) -> bytes:
        """
        将对象转换为请求

        @param {Any} obj - 要转换的对象
        @apram {dict} headers - 报文头对象
            注: 根据对象不同会设置不同的Content-Type

        @returns {bytes} - 要发送的数据
        """
        _type = type(obj)
        if _type == str:
            # 字符串
            _content_type = 'text/plain;charset=utf-8;'
            _data = obj.encode(encoding='utf-8')
        elif _type == bytes:
            # 本身为字节
            _content_type = 'application/octet-stream'
            _data = obj
        else:
            # 其他类型，转换为json对象
            _content_type = 'application/json;charset=utf-8;'
            _data = StringTool.json_dumps_hive_net(
                obj, ensure_ascii=self._conn_config.get('json_ensure_ascii', False)
            ).encode(encoding='utf-8')

        # 判断是否需要更新Content-Type
        if headers.get('Content-Type', None) is None:
            headers['Content-Type'] = _content_type

        # 返回字节数组
        return _data

    async def _resp_bytes_to_async_iter(self, response, bytes_read_size: int) -> bytes:
        """
        将响应对象的content内容转换为异步迭代方式获取

        @param {ClientResponse} response - 响应对象
        @param {int} bytes_read_size - 二进制数据读取缓存大小
        """
        while True:
            _chunk = await response.content.read(bytes_read_size)
            if not _chunk:
                break
            yield _chunk


class HttpClient(AIOHttpClient):
    """
    同步模式的Http客户端连接
    """
    #############################
    # 需要重载的公共函数
    #############################
    def ping(self, *args, **kwargs) -> CResult:
        """
        检测连接是否有效

        @param {args} - 检测函数的固定入参
        @param {kwargs} - 检测函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表检查失败
            注: 应将ret.status 设置为明细的检查结果值(例如状态码), 具体值由实现类定义
        """
        return AsyncTools.sync_run_coroutine(
            super().ping(*args, **kwargs)
        )

    def close(self):
        """
        关闭连接
        """
        return AsyncTools.sync_run_coroutine(super().close())

    def reconnect(self, *args, **kwargs) -> CResult:
        """
        重新连接

        @param {args} - 重新连接函数的固定入参
        @param {kwargs} - 重新连接函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
        """
        return AsyncTools.sync_run_coroutine(
            super().reconnect(*args, **kwargs)
        )

    def call(self, service_uri: str, request: Any = None, headers: dict = {}, method: str = 'GET',
            timeout: float = None, bytes_read_size: int = -1, **kwargs) -> CResult:
        """
        执行远程调用

        @param {str} service_uri - 请求的服务uri, 可以为完整的url字符串, 也可以仅为访问路径url
            注: 如果仅为访问路径url, 将拼接客户端对象的初始化host和端口
        @param {Any} request=None - 请求对象(要发送的内容), 可以支持Python的基础数据类型
        @param {dict} headers={} - 当前请求的http头字典
            注: 如果与全局http头重复的项将进行覆盖
        @param {str} method='GET' - 请求的方法
        @param {float} timeout=None - 指定本次请求的超时时间
        @param {int} bytes_read_size=-1 - 二进制数据读取缓存大小, 如果设置为-1代表一次性读取所有内容
        @param {kwargs} - aiohttp.ClientSession.request的其他可选参数

        @returns {CResult} - 执行结果CResult
            _result.resp 是标准响应内容字典, 格式为:
                url {str} - 访问的url
                status {int} - 返回状态码
                headers {dict} - 返回报文头
                data {bytes|asyncgen} - 返回内容, 如果bytes_read_size为-1则是全部的字节数组, 否则为异步迭代对象(每次返回指定大小的数组)
        """
        return AsyncTools.sync_run_coroutine(
            super().call(
                service_uri, request, headers=headers, method=method, timeout=timeout,
                bytes_read_size=bytes_read_size, **kwargs
            )
        )
