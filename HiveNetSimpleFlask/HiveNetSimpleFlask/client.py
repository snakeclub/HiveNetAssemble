#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
客户端模块

@module client
@file client.py
"""
import os
import sys
import time
import threading
import queue
import uuid
import gevent
from pyparsing import traceback
import socketio
from HiveNetCore.generic import CResult
from HiveNetCore.queue_hivenet import MemoryQueue
from HiveNetCore.utils.run_tool import RunTool, AsyncTools
from HiveNetWebUtils.client import ClientBaseFw, AIOHttpClient, HttpClient
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))


class SocketIOClient(ClientBaseFw):
    """
    SocketIO客户端
    """

    #############################
    # 重载构造函数
    #############################
    def __init__(self, conn_config: dict, **kwargs):
        """
        SocketIO客户端

        @param {dict} conn_config - 连接参数, 定义如下:
            原生socketio.Client.connect支持设置的参数:
            url {str} - 要连接到的url地址, 例如'http://localhost:5000/', 该url也可以包含请求参数字符串
            headers {dict} - 连接报文头字典, 默认为{}
            auth {dict|function} - 连接验证数据
            transports {list} - 允许的传输模式列表, 支持的传输模式包括'polling'和'websocket'
                注: 如果不送入, 则先通过'polling'模式连接, 然后切换至'websocket'模式
            namespaces {str|list} - 指定要连接的命名空间, 如果不传则只会连接已经注册了事件的命名空间
            socketio_path {str} - 服务端设置的路径, 默认为'socket.io'
            wait_timeout {float} - 连接等待超时时间, 单位为秒, 默认为1

            原生socketio.Client支持的初始化参数:
            reconnection {bool} - 是否自动重连, 默认为True
            reconnection_attempts {int} - 断开连接后尝试重连的次数, 如果设置为0代表一直尝试重连, 默认为0
            reconnection_delay {float} - 第一次尝试重连等待的秒数, 后续每次尝试重连是上一次等待时间的一倍, 默认为1秒
            reconnection_delay_max {float} - 两次尝试重连的最大等待秒数, 默认为5秒
            logger {bool|Logger} - 如果需要打印日志, 则设置为True或送入Logger对象, 默认为False
            json {object} - 用来进行python对象和json字符串相互转换的对象, 必须支持标准json的dumps和loads函数
            request_timeout {float} - 请求超时时间, 单位为秒, 默认为5秒
            http_session {requests.Session} - Session对象, 如果需要用到proxy或ssl则需要使用该对象
            ssl_verify {bool} - 是否需要ssl验证, 可以设置为False跳过验证, 默认为True

            客户端模式设置参数:
            is_native_mode {bool} - 是否使用原生模式, 默认为False
                原生模式: 需调用者自行通过connect、disconnect、bind_on_event等公共函数处理socketio相关逻辑
                非原生模式: 匹配ClientBaseFw的使用模式, 通过call请求远端并同步返回远端的处理结果
            service_event {str} - 指定服务模式的事件标识(需与服务器配置相对应), 默认为'socketio_service'
            service_namespace {str|list} - 指定服务模式对应的命名空间, 默认为None(全局命名空间)
                注: 如果传入的类型是list, 则会在清单中的命名空间都进行服务事件的注册
        """
        super().__init__(conn_config, **kwargs)

    #############################
    # 需要重载的公共函数
    #############################
    def ping(self, *args, **kwargs) -> CResult:
        """
        检测连接是否有效
        (可为同步或异步函数)

        @param {args} - 检测函数的固定入参
        @param {kwargs} - 检测函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表检查失败
            注: 应将ret.status 设置为明细的检查结果值(例如状态码), 具体值由实现类定义
        """
        if self.socketio.connected:
            _ret = CResult(code='00000')
            _ret.status = None
        else:
            # 未连接
            _ret = CResult(code='20599')
            _ret.status = None

        # 返回结果
        return _ret

    def close(self):
        """
        关闭连接
        """
        try:
            # 断开连接
            self.disconnect()
        except:
            pass

    def reconnect(self, *args, **kwargs) -> CResult:
        """
        重新连接

        @param {args} - 重新连接函数的固定入参
        @param {kwargs} - 重新连接函数的kv入参

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
        """
        if self.socketio.connected:
            # 原本已经连接上, 无需处理
            return CResult(code='00000')
        else:
            return self._connect_and_check()

    def call(self, service_uri: str, request, namespace: str = None,
            overtime: float = 5.0, **kwargs) -> CResult:
        """
        执行远程调用

        @param {str} service_uri - 请求的服务uri或唯一标识
        @param {dict} request - 请求数据字典
        @param {str} namespace=None - 命名空间, 例如'/test'
        @param {float} overtime=None - 请求超时时间, 如果不设置则使用初始化时的request_timeout参数
        @param {kwargs} - 远程调用的kv入参

        @returns {CResult} - 执行结果CResult
            注: 建议将请求的返回对象放到 cresult.resp 属性中
        """
        if not self.socketio.connected:
            # 未连接
            return CResult(code='20406')

        try:
            # 处理参数
            _overtime = overtime if overtime is not None else self._client_para['request_timeout']
            _id = str(uuid.uuid1())
            _request = {
                'id': _id,
                'service_uri': service_uri,
                'data': request
            }

            # 先放置请求响应的字典信息
            self._wait_resp_dict[_id] = {
                'lock': threading.Lock(),
                'resp': []
            }

            # 通过后台发送请求
            self.emit_bg(self.service_event, data=_request, namespace=namespace)

            # 等待发送和响应
            _start_time = time.time()
            while len(self._wait_resp_dict[_id]['resp']) <= 0:
                if (time.time() - _start_time) < _overtime:
                    gevent.sleep(0.01)
                else:
                    # 超时退出循环
                    break

            # 处理返回结果
            with self._wait_resp_dict[_id]['lock']:
                if len(self._wait_resp_dict[_id]['resp']) == 0:
                    # 超时
                    self._wait_resp_dict.pop(_id, None)
                    return CResult(code='30403')
                else:
                    # 获取到结果
                    _resp = self._wait_resp_dict[_id]['resp'][0]
                    if _resp['err_code'][0] == '0':
                        # 返回结果成功
                        _result = CResult(code=_resp['err_code'])
                        if _resp.get('is_end', True):
                            # 已经完结
                            self._wait_resp_dict.pop(_id, None)
                            _result.resp = _resp.get('data', None)
                        else:
                            # 迭代方式, 不删除对象
                            _result.resp = self._get_service_resp_iter(_id, _overtime)

                        # 返回结果
                        return _result
                    else:
                        self._wait_resp_dict.pop(_id, None)
                        return CResult(code=_resp['err_code'], error=_resp['error'])
        except:
            # 其他失败, 尝试删除等待数据
            self._wait_resp_dict.pop(_id, None)
            return CResult(
                code='30406', error=str(sys.exc_info()[1]), trace_str=traceback.format_exc()
            )

    #############################
    # 需重载的内部函数
    #############################
    def _std_init_config(self):
        """
        标准化客户端初始配置
        """
        # 实现类可以通过该函数设置或修改内部参数
        self._client_para = {
            'reconnection': self._conn_config.get('reconnection', True),
            'reconnection_attempts': self._conn_config.get('reconnection_attempts', 0),
            'reconnection_delay': self._conn_config.get('reconnection_delay', 1),
            'reconnection_delay_max': self._conn_config.get('reconnection_delay_max', 5),
            'logger': self._conn_config.get('logger', False),
            'json': self._conn_config.get('json', None),
            'request_timeout': self._conn_config.get('request_timeout', 5),
            'http_session': self._conn_config.get('http_session', None),
            'ssl_verify': self._conn_config.get('ssl_verify', True)
        }
        self._url = self._conn_config['url']
        self._connect_para = {
            'headers': self._conn_config.get('headers', {}),
            'auth': self._conn_config.get('auth', None),
            'transports': self._conn_config.get('transports', None),
            'namespaces': self._conn_config.get('namespaces', None),
            'socketio_path': self._conn_config.get('socketio_path', 'socket.io'),
            'wait': True,
            'wait_timeout': self._conn_config.get('wait_timeout', 1)
        }
        self.socketio = socketio.Client(**self._client_para)
        self._thread = None  # 客户端连接等待线程

        # 后台发送数据的公共队列
        self._bg_emit_queues = dict()

        # 登记绑定的后台任务信息
        self._bg_tasks = dict()

        # 非原生模式参数
        self.is_native_mode = self._conn_config.get('is_native_mode', False)
        self.service_event = self._conn_config.get('service_event', 'socketio_service')
        self.service_namespace = self._conn_config.get('service_namespace', None)
        if self.service_namespace is not None and isinstance(self.service_namespace, str):
            # 转换为列表模式
            self.service_namespace = [self._conn_config['service_namespace']]

        # 等待响应结果的字典, key为uuid, value为字典{'lock': 操作锁, 'resp': [按顺序放入的响应信息列表]}
        self._wait_resp_dict = {}

        if not self.is_native_mode:
            # 绑定服务反馈处理事件
            if self.service_namespace is None:
                # 全局命名空间模式
                self.bind_on_event('%s_resp' % self.service_event, self._service_resp_event_deal_func)
                self.bind_emit_bg_task_on_connect(namespace=None)  # 绑定后台提交任务
            else:
                # 指定命名空间模式
                for _namespace in self.service_namespace:
                    self.bind_on_event(
                        '%s_resp' % self.service_event, self._service_resp_event_deal_func,
                        namespace=_namespace
                    )
                    self.bind_emit_bg_task_on_connect(namespace=_namespace)  # 绑定后台提交任务

            # 尝试进行连接
            _result = self._connect_and_check()
            if not _result.is_success():
                raise RuntimeError('Connect error: %s' % str(_result))

    #############################
    # 自己的公共参数
    #############################
    def connect(self, is_asyn: bool = False):
        """
        连接服务器

        @param {bool} is_asyn=False - 是否异步处理, 如果是则直接返回
        """
        if self.socketio.connected:
            raise RuntimeError('Client is already connected!')

        # 执行连接
        self.socketio.connect(self._url, **self._connect_para)

        if is_asyn:
            # 异步模式
            self._thread = threading.Thread(
                target=self.socketio.wait,
                name='Socketio-client-wait-thread'
            )
            self._thread.setDaemon(True)
            self._thread.start()
        else:
            # 同步模式， 等待连接中断
            self.socketio.wait()

    def disconnect(self):
        """
        关闭连接
        """
        # 关闭所有后台线程
        for _event in self._bg_tasks.keys():
            for _task_para in self._bg_tasks[_event].values():
                try:
                    RunTool.async_raise(
                        _task_para['thread'].ident, SystemExit
                    )
                except:
                    pass

        # 清空所有待发送数据
        for _namespace, _queue in self._bg_emit_queues.items():
            _queue.clear()

        # 关闭等待数据的线程
        try:
            if self._thread is not None:
                RunTool.async_raise(self._thread.ident, SystemExit)
        except:
            pass

        # 断开连接
        try:
            self.socketio.disconnect()
        except:
            pass

    def bind_on_event(self, event: str, func, namespace: str = None):
        """
        绑定指定函数为特定事件的处理函数

        @param {str} event - 事件名, 其中一些事件是标准事件, 例如:
            'connect' - 连接事件
            'disconnect' - 断开连接事件
        @param {function} func - 处理函数对象
        @param {str} namespace=None - 命名空间，例如'/test'
        """
        self.socketio.on(event, handler=func, namespace=namespace)

    def bind_bg_task_on_event(self, event: str, task_func, func_args: list = [],
            func_kwargs: dict = {}, namespace: str = None):
        """
        绑定为特定事件处理的后台执行函数

        @param {str} event - 事件名, 其中一些事件是标准事件, 例如:
            'connect' - 连接事件
            'disconnect' - 断开连接事件
        @param {function} task_func - 后台处理函数
            注: task_func 内部如果要sleep, 必须使用 socketio.sleep 而不是time.sleep, 否则将会导致线程阻塞
        @param {list} func_args=[] - 后台执行函数的固定入参列表
        @param {dict} func_kwargs={} - 后台执行函数的kv入参列表
        @param {str} namespace=None - 命名空间, 例如'/test'
        """
        # 添加后台配置参数
        if self._bg_tasks.get(event, None) is None:
            self._bg_tasks[event] = {}

        self._bg_tasks[event][namespace] = {
            'task_func': task_func,
            'args': func_args,
            'kwargs': func_kwargs
        }

        # 按每次绑定定义一个可以传入event和namespace的函数
        def _temp_bg_tasks_func():
            self._bg_tasks_func(event, namespace)

        # 绑定任务函数
        self.socketio.on(event, _temp_bg_tasks_func, namespace=namespace)

    def bind_emit_bg_task_on_connect(self, namespace: str = None):
        """
        绑定connect事件的后台提交处理任务

        @param {str} namespace=None - 指定要绑定的命名空间
        """
        # 添加队列
        self._bg_emit_queues[namespace] = MemoryQueue()

        # 进行连接时的绑定
        self.bind_bg_task_on_event(
            'connect', self.emit_bg_task, func_kwargs={'namespace': namespace}, namespace=namespace
        )

    def emit(self, event, data=None, namespace=None, callback=None):
        """
        向服务器发送信息
        注意：该函数必须在绑定事件的函数内部使用

        @param {str} event - 事件名
        @param {dict} data - 要通知的数据字典
        @param {str} namespace='/' - 命名空间
        @param {function} callback=None - 回调函数
            注: 服务端的return值将作为回调函数的入参
        """
        self.socketio.emit(
            event, data=data, namespace=namespace, callback=callback
        )

    def emit_bg(self, event: str, data=None, namespace=None):
        """
        后台向服务器发送信息
        注: 必须设置了emit_bg_task作为后台服务才可以支持

        @param {str} event - 事件名
        @param {dict} data - 要通知的数据字典
        @param {str} namespace='/' - 命名空间
        """
        _queue: MemoryQueue = self._bg_emit_queues.get(namespace, None)
        if _queue is None:
            raise RuntimeError('Emit bg task namespace[%s] is not found' % (
                namespace
            ))

        _queue.put([event, namespace, data])

    def emit_bg_task(self, namespace: str = None):
        """
        后台向服务器发送信息的线程函数
        注: 该函数不可单独调用, 用于bind_bg_task_on_connected函数的后台函数,
            监控队列并将送入队列的数据发往服务器
        """
        _queue: MemoryQueue = self._bg_emit_queues.get(namespace, None)
        if _queue is None:
            # 未绑定
            raise RuntimeError('Emit bg task namespace[%s] is not found' % (
                namespace
            ))

        # 等待连接成功
        _start_time = time.time()
        _wait_timeout = self._connect_para['wait_timeout']
        if _wait_timeout <= 0:
            _wait_timeout = 5

        while not self.socketio.connected:
            if (time.time() - _start_time) >= _wait_timeout:
                raise RuntimeError('Emit bg task namespace[%s] wait connected timeout' % (
                    namespace
                ))

        while self.socketio.connected:
            # 连接状态才进行处理
            try:
                # 从队列获取数据
                _data = _queue.get()

                # 向服务器提交数据
                self.emit(
                    _data[0], data=_data[2], namespace=_data[1]
                )
            except queue.Empty:
                # 队列为空
                pass

            # 等待下一次处理
            gevent.sleep(0.1)

    #############################
    # 自己的内部函数
    #############################
    def _connect_and_check(self) -> CResult:
        """
        连接并检查连接结果

        @returns {CResult} - 响应对象, 如果返回结果为失败代表重连失败
        """
        # 先尝试关闭连接
        try:
            self.disconnect()
        except:
            pass

        # 进行连接
        self.connect(is_asyn=True)

        # 检查连接状态
        _start_time = time.time()
        while True:
            if self.socketio.connected:
                # 已连接成功
                return CResult(code='00000')

            # 判断是否超时
            if (time.time() - _start_time) < self._connect_para['wait_timeout']:
                gevent.sleep(0.01)
            else:
                break

        # 等待超时
        return CResult(code='20402')

    def _get_service_resp_iter(self, id: str, overtime: float):
        """
        将服务返回信息转换为迭代对象

        @param {str} id - 要获取的对象id
        @param {float} overtime - 超时时间, 单位为秒
        """
        _start_time = time.time()
        while True:
            if len(self._wait_resp_dict[id]['resp']) > 0:
                # 有收取到数据
                with self._wait_resp_dict[id]['lock']:
                    _resp = self._wait_resp_dict[id]['resp'].pop(0)

                if _resp['err_code'][0] != '0':
                    # 出现异常
                    raise RuntimeError(
                        'Get service response stream error, id[%s], code[%s]: %s' % (
                            id, _resp['err_code'], _resp['error']
                        )
                    )

                if _resp.get('is_end', True):
                    # 数据获取已结束, 最后一个返回值只是结束标志
                    return
                else:
                    # 返回结果
                    yield _resp.get('data', None)

                    # 更新获取开始时间
                    _start_time = time.time()
            else:
                # 获取不到数据
                if (time.time() - _start_time) < overtime:
                    gevent.sleep(0.01)
                else:
                    # 超时，抛出异常
                    raise RuntimeError(
                        'Get service response stream overtime, id[%s], code[30403]' % id
                    )

    def _service_resp_event_deal_func(self, resp: dict):
        """
        通用的服务反馈事件处理函数

        @param {dict} resp - 服务端返回的标准响应字典, 格式如下:
            {
                'id': '', # 事件请求id
                'err_code': '00000', # 错误码, 0开头代表成功
                'is_end': True,  # 是否还有下一个响应对象
                'data': ..., # 响应数据
                'error': '',  # 失败时的错误信息
            }
        """
        # 检查id是否存在
        _wait_resp_obj = self._wait_resp_dict.get(resp['id'], None)
        if _wait_resp_obj is None:
            # 找不到请求对象(可能超时或系统出了异常), 直接丢弃
            raise RuntimeError('Deal with response error: request id[%s] not found' % resp['id'])

        # 将数据放入列表
        with _wait_resp_obj['lock']:
            _wait_resp_obj['resp'].append(resp)

    def _bg_tasks_func(self, event: str, namespace: str):
        """
        绑定的后台执行函数的任务
        """
        _task_para = self._bg_tasks.get(event, {}).get(namespace, None)
        if _task_para is None:
            self._logger.error('Bg task event[%s] namespace[%s] para not found' % (
                event, namespace
            ))
            return

        # 发起后台执行
        _task_para['thread'] = self.socketio.start_background_task(
            _task_para['task_func'], *_task_para['args'], **_task_para['kwargs']
        )
