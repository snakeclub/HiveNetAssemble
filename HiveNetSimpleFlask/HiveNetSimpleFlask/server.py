#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Simple Flask的服务模块
@module server
@file server.py
"""
import os
import sys
import inspect
import math
import logging
import datetime
import threading
import asyncio
import gevent
import traceback
from functools import wraps
from typing import Callable
from gevent import pywsgi
import requests
from flask import Flask, jsonify, request as flask_request
from flask_cors import CORS
from flask.helpers import locked_cached_property
from flask.logging import create_logger
from flask.wrappers import Response
from werkzeug.routing import Rule
from flask_socketio import SocketIO, emit
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _
from HiveNetCore.utils.run_tool import RunTool, AsyncTools
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetWebUtils.server import ServerBaseFW, EnumServerRunStatus
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


class FlaskServerExit(SystemExit):
    """
    自定义异常类, 用于中止FlaskServer
    """
    pass


class FlaskWithLogger(Flask):
    """
    自定义Flask的logger设置
    """
    _logger = None  # 自定义的logger

    @locked_cached_property
    def logger(self):
        """A standard Python :class:`~logging.Logger` for the app, with
        the same name as :attr:`name`.

        In debug mode, the logger's :attr:`~logging.Logger.level` will
        be set to :data:`~logging.DEBUG`.

        If there are no handlers configured, a default handler will be
        added. See :doc:`/logging` for more information.

        .. versionchanged:: 1.1.0
            The logger takes the same name as :attr:`name` rather than
            hard-coding ``"flask.app"``.

        .. versionchanged:: 1.0.0
            Behavior was simplified. The logger is always named
            ``"flask.app"``. The level is only set during configuration,
            it doesn't check ``app.debug`` each time. Only one format is
            used, not different ones depending on ``app.debug``. No
            handlers are removed, and a handler is only added if no
            handlers are already configured.

        .. versionadded:: 0.3
        """
        if self._logger is None:
            self._logger = create_logger(self)

        return self._logger


class FlaskTool(object):
    """
    Flash工具类
    """
    @classmethod
    def add_route(cls, app: Flask, url: str, func, name: str = None,
                  with_para: bool = False, methods: list = None):
        """
        添加指定路由

        @param {Flask} app - 要添加路由的服务器
        @param {str} url - 路由url, 例如'/test'
        @param {function} func - 要添加路由的函数
        @param {str} name=None - 路由标识, 如果不传默认使用函数名(会存在函数名相同导致异常的情况)
            注: 该参数是flask路由的endpoint参数
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法, 如果不传且with_para为True时, 将获取路由函数本身带的'methods'参数定义
        """
        _route = url if url == '/' else url.rstrip('/')  # 去掉最后的'/'
        _methods = methods
        _endpoint = name if name is not None else RunTool.get_function_name(
            func, is_with_class=True, is_with_module=True
        )

        # 判断endpoint是否重复
        if _endpoint in app.view_functions.keys():
            raise RuntimeError('endpoint [%s] exists!' % _endpoint)

        if with_para:
            # 根据函数入参处理路由
            _para_list = RunTool.get_function_parameter_defines(func)
            for _para in _para_list:
                if _para['name'] == 'methods':
                    # 指定了处理方法
                    if _methods is None:
                        _methods = _para['default']
                elif _para['name'] in ('self', 'cls'):
                    # 不处理 self 和 cls 入参
                    continue
                elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                    # 不处理 *args及**kwargs参数
                    _type = ''
                    if _para['annotation'] == int:
                        _type = 'int:'
                    elif _para['annotation'] == float:
                        _type = 'float:'

                    _route = '%s/<%s%s>' % (_route, _type, _para['name'])

        # 处理方法的设置
        _methods = ['GET'] if _methods is None else _methods

        # 创建路由
        app.url_map.add(
            Rule(_route, endpoint=_endpoint, methods=_methods)
        )
        # 加入路由
        app.view_functions[_endpoint] = func

    @classmethod
    def add_route_by_class(cls, app: Flask, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
                           url_base: str = 'api', ver_is_new: bool = True):
        """
        通过类对象动态增加路由

        @param {Flask} app - 要增加服务的Flask应用
        @param {list} class_objs - Api类对象清单(可以支持传入类对象, 也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {bool} ver_is_new=True - 导入版本为最新, 如果为True, 代表有版本号的情况下也会创建一个非版本访问的路由
        """
        _blacklist = list() if blacklist is None else blacklist
        _class_name_mapping = dict() if class_name_mapping is None else class_name_mapping
        for _class in class_objs:
            _instance = None
            if not inspect.isclass(_class):
                _instance = _class
                _class = type(_instance)

            _real_class_name = _class.__name__
            # 获取映射后的类名
            _class_name = _class_name_mapping.get(_real_class_name, _real_class_name)
            # 遍历所有函数
            for _name, _value in inspect.getmembers(_class):
                if not _name.startswith('_') and callable(_value):
                    # 判断是否在黑名单中
                    if '%s/%s' % (_real_class_name, _name) in _blacklist:
                        continue

                    # 正常处理
                    _endpoint = '%s.%s' % (_class_name, _name)
                    if url_base == '':
                        # 忽略前置
                        _route = '{$ver$}/%s/%s' % (_class_name, _name)
                    else:
                        _route = '/%s{$ver$}/%s/%s' % (url_base, _class_name, _name)
                    _methods = None
                    _ver = ''
                    _para_list = RunTool.get_function_parameter_defines(_value)
                    for _para in _para_list:
                        if _para['name'] == 'methods':
                            # 指定了处理方法
                            _methods = _para['default']
                        elif _para['name'] == 'ver':
                            # 有指定ver的入参, 在路由api后面进行变更
                            _ver = '/<ver>'
                        elif _para['name'] == 'self' and _instance is not None:
                            # 不处理实例对象的self入参
                            continue
                        elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                            # 不处理 *args及**kwargs参数
                            _type = ''
                            if _para['annotation'] == int:
                                _type = 'int:'
                            elif _para['annotation'] == float:
                                _type = 'float:'

                            _route = '%s/<%s%s>' % (_route, _type, _para['name'])

                    # 创建路由
                    app.url_map.add(
                        Rule(_route.replace('{$ver$}', _ver), endpoint=_endpoint, methods=_methods)
                    )
                    if _ver != '' and ver_is_new:
                        # 也支持不传入版本的情况
                        app.url_map.add(
                            Rule(_route.replace('{$ver$}', ''),
                                 endpoint=_endpoint, methods=_methods)
                        )

                    # 对于实例对象, 获取真实的函数对象
                    if _instance is not None:
                        _value = getattr(_instance, _name)

                    # 加入路由
                    app.view_functions[_endpoint] = _value

    @classmethod
    def support_object_resp(cls, func):
        """
        支持函数直接返回Python对象的修饰符
        注: 正常函数应该返回标准的flask.wrappers.Response对象, 本修饰符允许按以下方式返回
            1、返回flask.wrappers.Response对象
            2、返回三元数组, 其中第1个为要返回的内容对象, 第2个为状态码, 第3个是header字典
            3、直接返回要处理的对象, 状态码默认为200(注意不可直接将数组对象返回)

        @param {function} func - 修饰符处理的函数

        @example Restful函数返回非字符串格式内容
            @FlaskTool.support_object_resp
            def func(a, b):
                ...
                return {'a':'value'}
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            _ret = func(*args, **kwargs)
            if isinstance(_ret, Response):
                # 已按正常规范返回
                return _ret
            else:
                _status = 200
                _header = {}
                if isinstance(_ret, (tuple, list)):
                    # 是列表, 第1个是要返回的值, 第2个是http状态码, 第3个是header字典
                    _body = _ret[0]
                    if len(_ret) > 1:
                        _status = _ret[1]
                    if len(_ret) > 2:
                        _header = _ret[2]
                else:
                    _body = _ret

                _type = type(_body)
                if _type == str:
                    # 字符串
                    return _body, _status, _header
                elif _type == bytes or inspect.isgenerator(_body):
                    # 字节数组或二进制流迭代对象, 当作二进制流
                    return Response(
                        _body, status=_status, headers=_header,
                        content_type='application/octet-stream'
                    )
                elif inspect.isasyncgen(_body):
                    # 异步迭代对象, 转换为同步
                    _resp_body = AsyncTools.sync_for_async_iter(_body)
                    return Response(
                        _resp_body, status=_status, headers=_header,
                        content_type='application/octet-stream'
                    )
                else:
                    # 对象
                    return jsonify(_body), _status, _header
        return wrapper


class FlaskServer(ServerBaseFW):
    """
    Flask服务
    """

    #############################
    # 添加的属性
    #############################
    @property
    def native_app(self) -> Flask:
        """
        获取原生app对象
        @property {Flask}
        """
        return self._app

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
            app_config {dict} - Flask初始化参数字典(请参考官方Flask文档), 常用参数包括:
                root_path {str} - Flask应用的资源根目录, 默认会获取所执行应用的根目录, 可以手工指定
                static_folder {str} - 静态资源目录, 为 root_path 的相对路径, 默认为'static'
                    注: 如果指定绝对路径则会与 root_path 路径无关
                static_url_path {str} - 静态资源的访问url前缀, 行为表现如下:
                    未传值的情况:
                    1. 如果static_folder未被指定, 那么static_url_path取为static, 也就是通过'/static/index.html'访问静态资源
                    2. 如果static_folder被指定了, 那么static_url_path等于static_folder的最后一级文件夹名称, 也就是通过'/最后一级文件夹/index.html'访问静态资源
                    有传值的情况:
                    1. static_url_path='', 代表直接通过根路径'/'访问静态资源, 也就是通过'/index.html'访问静态资源
                    2. static_url_path='path/path2' 或 '/path/path2', 将通过'/path/path2/index.html'访问静态资源
                    3. static_url_path='/path/', 路径前面不带'/'的情况, 将通过'/path/index.html'访问静态资源
            cors_config {dict} - flask_cors的配置参数字典, 例如:
                supports_credentials {bool} - 是否支持跨域
            flask_run {dict} - FlaskServer运行参数字典(请参考官方Flask文档), 常用参数包括:
                host {str} - 绑定的主机地址, 可以为 '127.0.0.1' 或不传
                port {int} - 监听端口, 默认为 5000
                threaded {bool} - 是否启动多线程, 默认为 True
                processes {int} - 进程数, 默认为 1, 如果设置进程数大于1, 必须将threaded设置为False
                ssl_context {str|tuple} - 使用https, 有两种使用方式
                    1. ssl_context='adhoc': 使用 pyOpenSSL 自带证书, 注意需进行安装 'pip install pyOpenSSL'
                    2. ssl_context=('/certificates/server.crt', '/certificates/server.key'): 使用指定路径的证书文件
                        示例: ssl_context=('/certificates/server-cert.pem', '/certificates/server-key.pem')
            debug {bool} - 是否debug模式, 默认False
            send_file_max_age_default {int} - 单位为秒, 发送文件功能最大的缓存超时时间, 默认为12小时, 如果要调试静态文件, 可以设置为1
            templates_auto_reload {bool} - 是否自动重新加载模版, 默认为False, 如果要调试模版, 可以设置为True
            json_as_ascii {bool} - josn字符串是否采取ascii模式, 默认为True, 如果需要json显示中文需传入False
            max_upload_size {float} - 上传文件的最大大小, 单位为MB
            use_wsgi {bool} - 是否使用WSGIServer, 默认为False
                注意: 如果使用wsgi,  处理函数内部请勿使用time.sleep, 否则会造成堵塞, 请统一调整为使用gevent.sleep
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
        """
        # 引用框架的构造函数
        super().__init__(
            app_name, server_config=server_config, support_auths=support_auths,
            before_server_start=before_server_start,
            after_server_start=after_server_start, before_server_stop=before_server_stop,
            after_server_stop=after_server_stop, logger=logger, log_level=log_level,
            load_i18n_para=load_i18n_para, **kwargs
        )

    def start(self, is_asyn: bool = False, sleep_time: float = 0.5, **kwargs) -> CResult:
        """
        启动服务
        (可以为同步或异步函数)

        @param {bool} is_asyn=False - 是否异步处理, 如果是则直接返回, 同步则阻塞处理直到服务停止
        @param {float} sleep_time=0.5 - 同步处理的每次循环检测状态的睡眠时间, 单位为秒
        @param {kwargs} - 实现类自定义的扩展参数

        @returns {CResult} - 异步情况返回启动结果, result.code: '00000'-成功, '21401'-服务不属于停止状态, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER-STARTING][NAME:%s]%s: ' % (
                self._app_name, _('start server error')
            ),
            force_log_level=logging.ERROR
        ):
            # 先获取锁, 拿到最准确的服务状态
            self._status_lock.acquire()
            try:
                if self.status != EnumServerRunStatus.Stop:
                    # 不属于停止状态, 不能启动
                    _temp_result = CResult(code='21401')  # 服务启动失败-服务已启动
                    self._logger.log(
                        self._log_level,
                        '[SER-STARTING][NAME:%s]%s' % (self._app_name, _temp_result.msg))
                    return _temp_result

                # 执行启动服务的动作, 通过线程方式启动
                self._start_begin_time = datetime.datetime.now()
                self._server_status_change(EnumServerRunStatus.WaitStart)

                # 启动运行线程
                self._thread = threading.Thread(
                    target=self._start_server_thread_fun, args=(1,), name='Thread-Server-Main'
                )
                self._thread.setDaemon(True)
                self._thread.start()

                # 循环等待服务启动成功
                if not self.use_wsgi and self._server_config.get('flask_run', {}).get('processes', 1) > 1:
                    # 多进程模式由于flask的bug, 无法使用标准做法验证, 采取等待一段时间后认为进程启动的方式
                    gevent.sleep(2)
                    if self._status == EnumServerRunStatus.WaitStart:
                        self._status = EnumServerRunStatus.Running
                else:
                    _url = '%s://%s:%d/' % (
                        'https' if 'ssl_context' in self._server_config.get(
                            'flask_run', {}).keys() else 'http',
                        self._server_config.get('flask_run', {}).get('host', '127.0.0.1'),
                        self._server_config.get('flask_run', {}).get('port', 5000)
                    )
                    while self.status == EnumServerRunStatus.WaitStart:
                        # 向Flask发送根目录的请求, 触发状态更新
                        gevent.sleep(sleep_time)
                        requests.get(_url)
            finally:
                # 释放锁
                self._status_lock.release()

        if not _result.is_success():
            # 执行出现错误, 直接返回
            return _result

        if self._status != EnumServerRunStatus.Running:
            # 服务线程中出现启动异常
            self._logger.log(
                logging.ERROR,
                ('[SER-STARTING][NAME:%s][USE:%ss]%s: %s - %s' % (
                    self._app_name,
                    str((datetime.datetime.now() - self._start_begin_time).total_seconds()),
                    _('start server error'), self._last_start_result.code, self._last_start_result.msg))
            )
            return self._last_start_result

        # 执行启动后函数
        if self._after_server_start is not None:
            AsyncTools.sync_run_coroutine(
                self._after_server_start(self)
            )

        # 启动成功
        self._logger.log(
            self._log_level,
            '[SER-STARTED][NAME:%s][USE:%ss]%s' % (
                self._app_name,
                str((datetime.datetime.now() - self._start_begin_time).total_seconds()),
                _('start server sucess')
            ))

        if is_asyn:
            # 异步模式, 直接返回
            return _result

        # 同步模式, 循环等待结束
        while self._status == EnumServerRunStatus.Running:
            AsyncTools.sync_run_coroutine(
                asyncio.sleep(sleep_time)
            )

        return _result

    def stop(self, overtime: float = 0, sleep_time: int = 0.5, **kwargs) -> CResult:
        """
        停止服务运行
        (可以为同步或异步函数)

        @param {float} overtime=0 - 等待超时时间, 单位为秒, 0代表一直不超时
        @param {float} sleep_time=0.5 - 每次等待睡眠时间, 单位为秒
        @param {kwargs} - 实现类自定义的扩展参数
            is_force {bool} - 是否强制关闭服务(有未正常关闭的风险), 默认为False

        @returns {CResult} - 停止结果, result.code: '00000'-成功, '21402'-服务停止失败-服务已关闭,
            '31005'-执行超时, 29999'-其他系统失败
        """
        self._stop_begin_time = datetime.datetime.now()
        _is_force = kwargs.get('is_force', False)
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER-STOPING][NAME:%s]%s: ' % (
                self._app_name, _('stop service error')),
            force_log_level=logging.ERROR
        ):
            self._status_lock.acquire()
            try:
                _status = EnumServerRunStatus.WaitStop
                if _is_force:
                    _status = EnumServerRunStatus.ForceStop

                if self._status == EnumServerRunStatus.Running:
                    # 运行状态, 处理设置等待关闭状态
                    self._logger.log(
                        self._log_level,
                        '[SER-STOPING][NAME:%s]%s' % (self._app_name, _('server stoping')))
                    self._status = _status
                elif self._status == EnumServerRunStatus.WaitStop \
                        and _status == EnumServerRunStatus.ForceStop:
                    self._logger.log(
                        self._log_level,
                        '[SER-STOPING][NAME:%s]%s' % (self._app_name, _('server force stoping')))
                    self._status = _status
                else:
                    # 不属于运行状态, 不能处理
                    _temp_result = CResult(code='21402')  # 服务停止失败-服务已关闭
                    self._logger.log(
                        self._log_level,
                        '[SER-STOPING][NAME:%s]%s' % (self._app_name, _temp_result.msg))
                    return _temp_result
            finally:
                self._status_lock.release()

            # 处理关闭前的函数运行
            if self._before_server_stop is not None:
                AsyncTools.sync_run_coroutine(
                    self._before_server_stop(self)
                )

            # 关闭服务
            self._flask_server_stop()

        # 等待服务关闭
        _begin_time = datetime.datetime.now()  # 记录等待开始时间
        while True:
            if self._status == EnumServerRunStatus.Stop:
                break

            if overtime > 0 and (datetime.datetime.now() - _begin_time).total_seconds() > overtime:
                _result = CResult(code='31005')  # 执行超时
                break

            # 等待下一次检查
            AsyncTools.sync_run_coroutine(asyncio.sleep(sleep_time))

        # 返回结果
        return _result

    def add_service(self, service_uri: str, handler: Callable, name: str = None,
                  with_para: bool = False, methods: list = None, **kwargs) -> CResult:
        """
        添加请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如'/demo'
        @param {Callable} handler - 请求处理函数, 应可同时支持同步或异步函数
            func(*args) -> flask.wrappers.Response
            非uri路由的请求参数可通过flask.request对象获取
            *args定义适配flask路由uri配置的<xxx>形式的路由参数(例如/xx/<arg1>/<arg2>), 注意只支持固定位置参数, 不支持kwargs
            返回值可以支持两种形式:
            1、Response对象, 如果返回为str对象, 将自动通过Response('str')转换为该对象; 如果是其他对象, 可以通过flask.jsonify转换
            2、返回三元组(data: str|Response, status_code: int, headers: dict), 例如("", 200, {"ContentType":"application/json"})
        @param {str} name=None - 路由标识, 如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法, 如果不传且with_para为True时, 将获取路由函数本身带的'methods'参数定义
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21405'-服务名已存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            FlaskTool.add_route(
                self._app, url=service_uri, func=handler, name=name, with_para=with_para, methods=methods
            )

        return _result

    def remove_service(self, service_uri: str, **kwargs) -> CResult:
        """
        移除请求处理服务

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 删除服务结果, result.code: '00000'-成功, '1404'-不支持的命令, 其他-异常
        """
        return CResult(code='21404', i18n_msg_paras=('remove_service', ))

    def add_service_by_class(self, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
            url_base: str = 'api', ver_is_new: bool = True) -> CResult:
        """
        通过类对象动态增加服务

        @param {list} class_objs - Api类对象清单(可以支持传入类对象, 也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {bool} ver_is_new=True - 导入版本为最新, 如果为True, 代表有版本号的情况下也会创建一个非版本访问的路由
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            FlaskTool.add_route_by_class(
                self._app, class_objs=class_objs, blacklist=blacklist,
                class_name_mapping=class_name_mapping, url_base=url_base,
                ver_is_new=ver_is_new
            )

        return _result

    #############################
    # 内部函数重载
    #############################
    def _start_server_thread_fun(self, tid):
        """
        启动服务处理主线程, 本线程结束就代表服务停止

        @param {int} tid - 线程id

        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER-STARTING][NAME:%s]%s: ' % (self._app_name, _('start server error'))
        ):
            # 统一的异常处理
            self._logger.log(
                self._log_level,
                '[SER-STARTING][NAME:%s]%s' % (self._app_name, _('server starting'))
            )

            # 执行before_server_start
            if self._before_server_start is not None:
                AsyncTools.sync_run_coroutine(self._before_server_start(self))

            # 启动服务
            try:
                _flask_run = self._server_config.get('flask_run', {})
                # 因为不在main线程启动Flask, 所以不支持use_reloader参数
                _flask_run['use_reloader'] = False
                if self.use_wsgi:
                    # 使用WSGIServer
                    self._wsgi_server_start(_flask_run)
                else:
                    # 使用原生方式启动
                    self._flask_server_start(_flask_run)
            except FlaskServerExit:
                # 正常执行中止服务后的操作, 无需抛出异常
                pass
            finally:
                # 执行关闭后函数
                if self._after_server_stop is not None:
                    AsyncTools.sync_run_coroutine(
                        self._after_server_stop(self)
                    )
                self._status = EnumServerRunStatus.Stop
                self._logger.log(
                    self._log_level,
                    '[SER-STOPED][NAME:%s][USE:%ss]%s' % (
                        self._app_name, str((datetime.datetime.now() - self._stop_begin_time).total_seconds()),
                        _('server stoped')
                    )
                )

        # 走到这一步说明有异常或服务结束了
        self._status = EnumServerRunStatus.Stop
        if not _result.is_success():
            # 设置最后一次异常信息, 供启动函数获取
            self._last_start_result = _result

        return _result

    #############################
    # 实现类需重载的内部函数
    #############################
    def _std_init_config(self):
        """
        标准化服务初始配置
        """
        # 内部参数
        self._thread = None  # 启动服务的线程对象

        # 创建应用
        self._app = FlaskWithLogger(self._app_name, **self._server_config.get('app_config', {}))
        CORS(self._app, **self._server_config.get('cors_config', {}))

        # Flask应用配置
        if self._logger is not None:
            self._app._logger = self._logger
        else:
            # 不传logger时, 使用flask默认的logger
            self._logger = self._app.logger
        self._app.debug = self._server_config.get('debug', False)
        self._app.send_file_max_age_default = datetime.timedelta(
            seconds=self._server_config.get('send_file_max_age_default', 12 * 60 * 60)
        )
        _templates_auto_reload = self._server_config.get('templates_auto_reload', False)
        if _templates_auto_reload:
            self._app.jinja_env.auto_reload = True
            self._app.templates_auto_reload = True
        self._app.config['JSON_AS_ASCII'] = self._server_config.get('json_as_ascii', True)
        if 'max_upload_size' in self._server_config.keys():
            self._app.config['MAX_CONTENT_LENGTH'] = math.floor(
                self._server_config['max_upload_size'] * 1024 * 1024
            )
        self.use_wsgi = self._server_config.get('use_wsgi', False)

        # 在收到第一个请求前执行的函数(在多进程的情况下没有调用, 可能是Flask的bug)
        self._app.before_first_request_funcs.append(self._update_running_status)

    #############################
    # 内部函数
    #############################
    def _wsgi_server_start(self, run_para: dict):
        """
        启动wsgi服务器的函数
        注: 如果需改用其他wsgi服务器, 请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        _ssl_args = dict()
        # keyfile='server.key', certfile='server.crt'
        _ssl_context = run_para.get('ssl_context', None)
        if _ssl_context is not None and type(_ssl_context) in (tuple, list):
            _ssl_args['certfile'] = _ssl_context[0]
            _ssl_args['keyfile'] = _ssl_context[1]
        _wsgi_server = pywsgi.WSGIServer(
            (run_para.get('host', '127.0.0.1'), run_para.get('port', 5000)),
            application=self._app,
            **_ssl_args
        )
        _wsgi_server.serve_forever()

    def _flask_server_start(self, run_para: dict):
        """
        flask原生启动方式
        注：如果需改用其他启动方式, 请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        self._app.run(**run_para)

    def _update_running_status(self):
        """
        线程启动完成后更新状态为正在运行
        """
        self._status = EnumServerRunStatus.Running

    def _flask_server_stop(self):
        """
        关闭Flask服务器的方法
        注: 关闭方法要保证服务状态变更为stop, 否则关闭方法可能会循环等待无法退出
        """
        # 向线程发送中止异常
        RunTool.async_raise(self._thread.ident, FlaskServerExit)


class SocketIOServer(FlaskServer):
    """
    SocketIO服务器
    注：直接继承自 FlaskServer
    注意: web请使用socket.io.js的3.x版本进行对接: https://cdnjs.cloudflare.com/ajax/libs/socket.io/3.0.4/socket.io.js
    """

    #############################
    # 重载构造函数
    #############################
    def __init__(self, app_name: str, server_config: dict = {}, support_auths: dict = {},
            before_server_start=None, after_server_start=None,
            before_server_stop=None, after_server_stop=None, logger=None, log_level: int = logging.INFO,
            load_i18n_para=None, **kwargs):
        """
        初始化SocketIOServer

        @param {str} app_name - Flask服务器名称
        @param {dict} server_config=None - 服务器配置字典, 定义如下:
            app_config {dict} - Flask初始化参数字典(请参考官方Flask文档), 常用参数包括:
                root_path {str} - Flask应用的资源根目录, 默认会获取所执行应用的根目录, 可以手工指定
                static_folder {str} - 静态资源目录, 为 root_path 的相对路径, 默认为'static'
                    注: 如果指定绝对路径则会与 root_path 路径无关
                static_url_path {str} - 静态资源的访问url前缀, 行为表现如下:
                    未传值的情况:
                    1. 如果static_folder未被指定, 那么static_url_path取为static, 也就是通过'/static/index.html'访问静态资源
                    2. 如果static_folder被指定了, 那么static_url_path等于static_folder的最后一级文件夹名称, 也就是通过'/最后一级文件夹/index.html'访问静态资源
                    有传值的情况:
                    1. static_url_path='', 代表直接通过根路径'/'访问静态资源, 也就是通过'/index.html'访问静态资源
                    2. static_url_path='path/path2' 或 '/path/path2', 将通过'/path/path2/index.html'访问静态资源
                    3. static_url_path='/path/', 路径前面不带'/'的情况, 将通过'/path/index.html'访问静态资源
            cors_config {dict} - flask_cors的配置参数字典, 例如:
                supports_credentials {bool} - 是否支持跨域
            socketio_config {dict} - SocketIO初始化参数, 具体支持的参数参考SocketIO文档,例如：
                'cors_allowed_origins': '*'  # 解决跨域访问问题
                'path': 'socket.io'  # 指定socketio的对外资源路径, 可以修改为其他值
                'json': object # 指定自定义的json处理对象, 来支持默认json处理无法转换的特色对象, 该对象必须有兼容标准json模块的dumps和loads函数
            flask_run {dict} - SocketIoServer运行参数字典(请参考官方socketio.run文档), 常用参数包括:
                host {str} - 绑定的主机地址, 可以为 '127.0.0.1' 或不传
                port {int} - 监听端口, 默认为 5000
            debug {bool} - 是否debug模式, 默认False
            send_file_max_age_default {int} - 单位为秒, 发送文件功能最大的缓存超时时间, 默认为12小时
            json_as_ascii {bool} - josn字符串是否采取ascii模式, 默认为True, 如果需要json显示中文需传入False
            max_upload_size {float} - 上传文件的最大大小, 单位为MB
            use_wsgi {bool} - 是否使用WSGIServer, 默认为False
            is_native_mode {bool} - 是否使用原生模式, 默认为False
                注: 原生模式不支持add_service这类请求响应的方法, 需要自行通过bind_on_event绑定事件处理函数;
                    非原生模式通过指定特定的事件作为服务请求事件, 从而形成请求响应模式的处理
            service_event {str} - 指定服务模式的事件标识, 默认为'socketio_service'
            service_namespace {str|list} - 指定服务模式对应的命名空间, 默认为None(全局命名空间)
                注: 如果传入的类型是list, 则会在清单中的命名空间都进行服务事件的注册
        @param {dict} support_auths=None - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
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
        """
        # 执行父类构造函数
        super(SocketIOServer, self).__init__(
            app_name, server_config=server_config, support_auths=support_auths,
            before_server_start=before_server_start, after_server_start=after_server_start,
            before_server_stop=before_server_stop, after_server_stop=after_server_stop,
            logger=logger, log_level=log_level, load_i18n_para=load_i18n_para,
            **kwargs
        )

        # 自有参数
        self.is_native_mode = self._server_config.get('is_native_mode', False)
        self.service_event = self._server_config.get('service_event', 'socketio_service')
        self.service_namespace = self._server_config.get('service_namespace', None)
        if self.service_namespace is not None and isinstance(self.service_namespace, str):
            # 转换为列表模式
            self.service_namespace = [self._server_config['service_namespace']]

        # 设置SokcetIO
        _socketio_config = self._server_config.get('socketio_config', {})
        if self._server_config.get('use_wsgi', False) and _socketio_config.get('async_mode', None) is None:
            _socketio_config['async_mode'] = 'gevent_uwsgi'

        self.socketio: SocketIO = SocketIO(
            app=self._app, **_socketio_config
        )

        # 登记绑定的后台任务信息
        self._bg_tasks = dict()

        # 非原生模式需绑定事件处理
        if not self.is_native_mode:
            # 绑定服务处理事件
            if self.service_namespace is None:
                # 全局命名空间模式
                self.bind_on_event(self.service_event, self._service_event_deal_func)
            else:
                # 指定命名空间模式
                for _namespace in self.service_namespace:
                    self.bind_on_event(
                        self.service_event, self._service_event_deal_func, namespace=_namespace
                    )

    #############################
    # 重载公共函数
    #############################
    def add_service(self, service_uri: str, handler: Callable, namespace=None, **kwargs) -> CResult:
        """
        添加请求处理服务
        注: 命名空间和服务名重复将被覆盖

        @param {str} service_uri - 服务唯一标识(事件)
        @param {Callable} handler - 请求处理函数, 可同时支持同步或异步函数
            函数格式如下: func(request: dict) -> dict
            送入的request字典格式为:
                {
                    'id': '', # 事件请求id
                    'service_uri': '', # 请求服务uri
                    'data': ... # 请求数据对象
                }
            可以直接返回支持json转换的原生python对象反馈到客户端
            注1: 如果返回的对象是iter, 则客户端也可以以iter方式处理返回值
            注2: 处理函数内部可以通过emit或broadcast函数进行向客户端推送其他事件(非当前请求的响应事件)
        @param {str|list} namespace=None - 要添加到的服务命名空间
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            # 将入参统一调整为清单模式
            _namespace_list = []
            if namespace is None or isinstance(namespace, str):
                _namespace_list.append(namespace)
            else:
                _namespace_list.extend(namespace)

            # 逐个服务添加
            for _namespace in _namespace_list:
                if self._service_router.get(_namespace, None) is None:
                    self._service_router[_namespace] = {}

                self._service_router[_namespace][service_uri] = {
                    'handler': handler, 'kwargs': kwargs
                }

        return _result

    def remove_service(self, service_uri: str, namespace=None, **kwargs) -> CResult:
        """
        移除请求处理服务
        注: 服务不存在的情况也不返回错误

        @param {str} service_uri - 服务唯一标识(事件)
        @param {str|list} namespace=None - 要移除服务所属服务命名空间
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 删除服务结果, result.code: '00000'-成功, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('remove service error'))
        ):
            # 将入参统一调整为清单模式
            _namespace_list = []
            if namespace is None or isinstance(namespace, str):
                _namespace_list.append(namespace)
            else:
                _namespace_list.extend(namespace)

            for _namespace in _namespace_list:
                _dict = self._service_router.get(_namespace, None)
                if _dict is None:
                    continue
                _dict.pop(service_uri, None)

        return _result

    def add_service_by_class(self, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
            namespace=None, **kwargs) -> CResult:
        """
        通过类对象动态增加服务
        注: service_uri固定为'class_name.function_name'

        @param {list} class_objs - Api类对象清单(可以支持传入类对象, 也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问uri的路径, key为真实类名, value为映射后的类名
        @param {str|list} namespace=None - 要添加到的服务命名空间
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            _blacklist = list() if blacklist is None else blacklist
            _class_name_mapping = dict() if class_name_mapping is None else class_name_mapping
            for _class in class_objs:
                _instance = None
                if not inspect.isclass(_class):
                    _instance = _class
                    _class = type(_instance)

                _real_class_name = _class.__name__
                # 获取映射后的类名
                _class_name = _class_name_mapping.get(_real_class_name, _real_class_name)
                # 遍历所有函数
                for _name, _value in inspect.getmembers(_class):
                    if not _name.startswith('_') and callable(_value):
                        # 判断是否在黑名单中
                        if '%s/%s' % (_real_class_name, _name) in _blacklist:
                            continue

                        # 正常处理
                        _uri = '%s.%s' % (_class_name, _name)

                        # 对于实例对象, 获取真实的函数对象
                        if _instance is not None:
                            _value = getattr(_instance, _name)

                        # 添加服务
                        _result = self.add_service(
                            _uri, _value, namespace=namespace, **kwargs
                        )
                        if not _result.is_success():
                            return _result

        return _result

    #############################
    # 重载WSGI服务器启动方式, 暂时仍用原生开发模式启动
    #############################

    def _wsgi_server_start(self, run_para: dict):
        """
        启动wsgi服务器的函数
        注: 如果需改用其他wsgi服务器, 请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        self.socketio.run(self._app, **run_para)

    def _flask_server_start(self, run_para: dict):
        """
        flask原生启动方式
        注：如果需改用其他启动方式, 请继承并重载该函数

        @param {dict} run_para - 启动参数
        """
        self.socketio.run(self._app, **run_para)

    def _flask_server_stop(self):
        """
        关闭Flask服务器的方法
        注: 关闭方法要保证服务状态变更为stop, 否则关闭方法可能会循环等待无法退出
        """
        self.socketio.stop()

    #############################
    # SocketIO的自有方法
    #############################
    @classmethod
    def broadcast(cls, event: str, data: dict, namespace: str = None, with_context_app=None):
        """
        发送消息给所有连接的客户端
        注意：该函数必须在绑定事件的函数内部使用

        @param {str} event - 事件名
        @param {dict} data - 要通知的数据字典
        @param {str} namespace=None - 命名空间, 例如'/'
        @param {Flask} with_context_app=None - 指定上下文的Flask App对象
            注: 解决 Working outside of application context 的问题
        """
        if with_context_app is None:
            emit(event, data, namespace=namespace, broadcast=True)
        else:
            with with_context_app.app_context():
                emit(event, data, namespace=namespace, broadcast=True)

    @classmethod
    def emit(cls, event, *args, **kwargs):
        """
        向客户端发送消息, 是emit函数的直接映射
        注意：该函数必须在绑定事件的函数内部使用

        @param {str} event - 事件
        """
        _with_context_app = kwargs.get('with_context_app', None)
        if _with_context_app is None:
            emit(event, *args, **kwargs)
        else:
            with _with_context_app.app_context():
                emit(event, *args, **kwargs)

    def bind_on_event(self, event: str, func, namespace: str = None):
        """
        绑定指定函数为特定事件的处理函数

        @param {str} event - 事件名, 其中一些事件是标准事件, 例如:
            'connect' - 连接事件
            'disconnect' - 断开连接事件
        @param {function} func - 处理函数对象
        @param {str} namespace=None - 命名空间, 例如'/test'
        """
        self.socketio.on_event(event, func, namespace=namespace)

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

        # 绑定任务函数
        self.socketio.on_event(event, self._bg_tasks_func, namespace=namespace)

    #############################
    # 内部函数
    #############################
    def _service_event_deal_func(self, request: dict):
        """
        通用的服务事件处理函数

        @param {dict} request - 客户端送入的标准服务请求字典, 格式如下:
            {
                'id': '', # 事件请求id
                'service_uri': '', # 请求服务uri
                'data': ... # 请求数据对象
            }
        """
        _namespace = flask_request.namespace
        _handler = self._service_router.get(_namespace, {}).get(
            request.get('service_uri', ''), {}
        ).get('handler', None)

        try:
            if _handler is None:
                # 没有找到请求对象
                raise RuntimeError('Handler not found')

            # 执行相关函数
            _resp = AsyncTools.sync_run_coroutine(
                _handler(request)
            )

            if inspect.isasyncgen(_resp):
                _resp = AsyncTools.sync_for_async_iter(_resp)

            if inspect.isgenerator(_resp):
                # 迭代模式
                _id = request.get('id', '')
                for _item in _resp:
                    _std_resp = {
                        'id': _id,
                        'err_code': '00000',
                        'is_end': False,
                        'data': _item
                    }
                    self.emit('%s_resp' % self.service_event, _std_resp, namespace=_namespace)

                # 发送结束的标记
                _std_resp = {
                    'id': _id,
                    'err_code': '00000',
                    'is_end': True,
                    'data': None
                }
            else:
                # 返回执行结果
                _std_resp = {
                    'id': request.get('id', ''),
                    'err_code': '00000',
                    'is_end': True,
                    'data': _resp
                }
        except:
            # 执行出现异常
            self._logger.error('event execute error, namespace[%s], request[%s]: %s' % (
                _namespace, str(request), traceback.format_exc()
            ))
            _std_resp = {
                'id': request.get('id', ''),
                'err_code': '29999',
                'is_end': True,
                'error': str(sys.exc_info()[1])
            }

        self.emit('%s_resp' % self.service_event, _std_resp, namespace=_namespace)

    def _bg_tasks_func(self):
        """
        绑定的后台执行函数的任务
        """
        _event = flask_request.event['message']
        _namespace = flask_request.namespace
        _task_para = self._bg_tasks.get(_event, {}).get(_namespace, None)
        if _task_para is None:
            self._logger.error('Bg task event[%s] namespace[%s] para not found' % (
                _event, _namespace
            ))
            return

        # 发起后台执行
        self.socketio.start_background_task(
            _task_para['task_func'], *_task_para['args'], **_task_para['kwargs']
        )
