#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
socket连接的工具类

@module socket
@file socket.py
"""
import sys
import os
import socket
import asyncio
import datetime
from HiveNetCore.generic import CResult, NullObj
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


class SocketTool(object):
    """
    socket连接的工具类
    """

    @classmethod
    def connect(cls, connect_config={}) -> CResult:
        """
        连接Socket服务器端并返回连接对象

        @param {dict} connect_config - 连接参数
            ip {str} - 主机名或IP地址, 默认为'127.0.0.1'
            port {int} - 监听端口, 默认为8080
            recv_timeout {float} - 数据接收的超时时间, 单位为秒, 默认为10.0
            send_timeout {float} - 数据发送的超时时间, 单位为秒, 默认为10.0

        @returns {CResult} - 连接结果:
            result.code: '00000'-成功, 其他值为失败
            result.net_info: 连接后的网络信息对象
                net_info.csocket - socket对象
                net_info.laddr 本地地址,地址对象("IP地址",打开端口)
                net_info.raddr 远端地址,地址对象("IP地址",打开端口)
                net_info.send_timeout 发送超时时间, 单位为秒
                net_info.recv_timeout 收取超时时间, 单位为秒
        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result, logger=None
        ):
            # 进行连接
            _tcp_cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 分配 TCP 客户端套接字
            _tcp_cli_sock.connect(
                (connect_config.get('ip', '127.09.0.1'), connect_config.get('port', 8080))
            )  # 主动连接
            _tcp_cli_sock.setblocking(False)   # 将socket设置为非阻塞. 在创建socket对象后就进行该操作.

            # 处理网络连接对象
            _result.net_info = NullObj()
            _result.net_info.csocket = _tcp_cli_sock
            _result.net_info.laddr = _tcp_cli_sock.getsockname()
            _result.net_info.raddr = _tcp_cli_sock.getpeername()
            _result.net_info.send_timeout = connect_config.get('send_timeout', 10.0)
            _result.net_info.recv_timeout = connect_config.get('recv_timeout', 10.0)

        return _result

    @classmethod
    def close(cls, net_info: NullObj):
        """
        关闭指定的网络连接

        @param {NullObj} net_info - 需要关闭的网络连接信息对象
            net_info.csocket - socket对象
            net_info.laddr 本地地址,地址对象("IP地址",打开端口)
            net_info.raddr 远端地址,地址对象("IP地址",打开端口)
            net_info.send_timeout 发送超时时间, 单位为秒
            net_info.recv_timeout 收取超时时间, 单位为秒

        @returns {CResult} - 关闭结果
            result.code: '00000'-成功, 其他值为失败
        """
        _result = CResult('00000')
        with ExceptionTool.ignored_cresult(
            _result, logger=None
        ):
            net_info.csocket.close()

        return _result

    @classmethod
    def recv_data(cls, net_info, recv_para={}):
        """
        从指定的网络连接中读取数据

        @param {NullObj} net_info - 网络连接信息对象
            net_info.csocket - socket对象
            net_info.laddr 本地地址,地址对象("IP地址",打开端口)
            net_info.raddr 远端地址,地址对象("IP地址",打开端口)
            net_info.send_timeout 发送超时时间, 单位为秒
            net_info.recv_timeout 收取超时时间, 单位为秒
        @param {dict} recv_para - 读取数据的参数, 包括:
            recv_len {int} - 要获取的数据长度, 必要参数
            overtime {float} - 获取超时时间, 单位为秒, 非必要参数

        @returns {CResult} - 数据获取结果:
            result.code: '00000'-成功, '20403'-获取数据超时, 其他为获取失败
            result.data: 获取到的数据对象(具体类型和定义, 由实现类自定义)
            result.recv_time : datetime 实际开始接受数据时间
            result.overtime : float 超时时间(秒), 当返回结果为超时, 可获取超时时间信息
        """
        if not isinstance(recv_para, dict):
            recv_para = {}

        _result = CResult('00000')
        _result.data = b''
        _result.recv_time = datetime.datetime.now()
        _overtime = recv_para.get('overtime', None)
        if _overtime is None:
            if hasattr(net_info, 'recv_timeout'):
                _overtime = net_info.recv_timeout
            else:
                _overtime = 10.0
        _result.overtime = _overtime

        with ExceptionTool.ignored_cresult(
            _result
        ):
            _rest_bytes = recv_para['recv_len']
            while _rest_bytes > 0:
                # 检查是否超时
                if (datetime.datetime.now() - _result.recv_time).total_seconds() > _overtime:
                    # 已超时
                    _result.change_code(code='20403')
                    break

                _buffer = b''
                with ExceptionTool.ignored(expect=(BlockingIOError)):
                    # 获取数据
                    _buffer = net_info.csocket.recv(_rest_bytes)
                    if _buffer is not None and len(_buffer) > 0:
                        _result.data = _result.data + _buffer
                        _rest_bytes = _rest_bytes - len(_buffer)
                    else:
                        # 休眠一下
                        AsyncTools.sync_run_coroutine(
                            asyncio.sleep(0.001)
                        )

        return _result

    @classmethod
    def send_data(cls, net_info, data: bytes, send_para={}):
        """
        向指定的网络连接发送数据

        @param {NullObj} net_info - 网络连接信息对象
            net_info.csocket - socket对象
            net_info.laddr 本地地址,地址对象("IP地址",打开端口)
            net_info.raddr 远端地址,地址对象("IP地址",打开端口)
            net_info.send_timeout 发送超时时间, 单位为秒
            net_info.recv_timeout 收取超时时间, 单位为秒
        @param {bytes} data - 要写入的数据对象
        @param {dict} send_para - 写入数据的参数:
            overtime {float} - 发送超时时间, 单位为秒, 非必须参数
        @returns {CResult} - 发送结果:
            result.code: '00000'-成功, '20404'-写入数据超时, 其他为写入失败
            result.send_time : datetime 实际发送完成时间
            result.overtime : float 超时时间(秒), 当返回结果为超时, 可获取超时时间信息
        """
        if not isinstance(send_para, dict):
            send_para = {}

        _result = CResult('00000')
        _result.send_time = None
        _overtime = send_para.get('overtime', None)
        if _overtime is None:
            if hasattr(net_info, 'send_timeout'):
                _overtime = net_info.send_timeout
            else:
                _overtime = 10.0

        _result.overtime = _overtime

        _begin_time = datetime.datetime.now()
        with ExceptionTool.ignored_cresult(
            _result
        ):
            _rest_bytes = len(data)
            _total_bytes = _rest_bytes
            while _rest_bytes > 0:
                # 检查是否超时
                if (datetime.datetime.now() - _begin_time).total_seconds() > _overtime:
                    # 已超时
                    _result.change_code(code='20404')
                    break
                with ExceptionTool.ignored(expect=(BlockingIOError)):
                    # 发送数据
                    _len = net_info.csocket.send(data[_total_bytes - _rest_bytes:])
                    if _len > 0:
                        _rest_bytes = _rest_bytes - _len

            _result.send_time = datetime.datetime.now()
        return _result
