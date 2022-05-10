#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Simple Sanic的服务模块

@module server
@file server.py
"""

import os
import sys
import logging
import threading
import asyncio
import inspect
from functools import wraps
import traceback
from typing import Callable
from inspect import isawaitable
from collections import OrderedDict
from sanic import Sanic
from sanic.response import HTTPResponse, text, json
from sanic_ext import Extend
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetCore.utils.run_tool import RunTool, AsyncTools
from HiveNetWebUtils.server import ServerBaseFW, EnumServerRunStatus
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


class SanicTool(object):
    """
    Sanic工具类, 提供路由, 内容解析等通用处理功能
    注: 由于Sanic的机制, 不支持线程运行情况的stop操作, 因此取消了stop函数
    """
    @classmethod
    def add_route(cls, app: Sanic, url: str, func, name: str = None,
                  with_para: bool = False, methods: list = None, version=None):
        """
        添加指定路由

        @param {Sanic} app - 要添加路由的服务器实例
        @param {str} url - 路由url, 例如'/test'
        @param {function} func - 要添加路由的函数
        @param {str} name=None - 路由标识, 如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法, 如果不传代表支持所有方法
        @param {int|float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        """
        _route = url if url == '/' else url.rstrip('/')  # 去掉最后的'/'
        _methods = methods
        _name = name if name is not None else RunTool.get_function_name(
            func, is_with_class=True, is_with_module=True
        )

        if with_para:
            # 根据函数入参处理路由
            _para_list = RunTool.get_function_parameter_defines(func)
            for _para in _para_list:
                if _para['name'] == 'methods':
                    # 指定了处理方法
                    _methods = _para['default']
                elif _para['name'] in ('self', 'cls', 'request'):
                    # 不处理 self 和 cls 入参, 以及第一个请求的入参
                    continue
                elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                    # 不处理 *args及**kwargs参数
                    _type = ''
                    if _para['annotation'] == str:
                        _type = ':str'
                    if _para['annotation'] == int:
                        _type = ':int'
                    elif _para['annotation'] == float:
                        _type = ':float'

                    _route = '%s/<%s:%s>' % (_route, _para['name'], _type)

        # 处理方法的设置
        _methods = ['GET'] if _methods is None else _methods

        # 添加路由
        app.add_route(
            func, _route, methods=_methods, name=_name, version=version
        )

    @classmethod
    def add_route_by_class(cls, app: Sanic, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
                           url_base: str = 'api', version=None):
        """
        通过类对象动态增加路由

        @param {Sanic} app - 要增加服务的Sanic应用实例
        @param {list} class_objs - Api类对象清单(可以支持传入类对象, 也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {int|float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
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
                    _router_name = '%s.%s' % (_class_name, _name)
                    if url_base == '':
                        # 忽略前置
                        _route = '/%s/%s' % (_class_name, _name)
                    else:
                        _route = '/%s/%s/%s' % (url_base, _class_name, _name)
                    _methods = None
                    _para_list = RunTool.get_function_parameter_defines(_value)
                    for _para in _para_list:
                        if _para['name'] == 'methods':
                            # 指定了处理方法
                            _methods = _para['default']
                        elif _para['name'] == 'self' and _instance is not None:
                            # 不处理实例对象的self入参
                            continue
                        elif _para['name'] in ('request', 'cls'):
                            continue
                        elif _para['type'] not in ('VAR_POSITIONAL', 'VAR_KEYWORD'):
                            # 不处理 *args及**kwargs参数
                            _type = ''
                            if _para['annotation'] == str:
                                _type = ':str'
                            if _para['annotation'] == int:
                                _type = ':int'
                            elif _para['annotation'] == float:
                                _type = ':float'

                            _route = '%s/<%s%s>' % (_route, _para['name'], _type)

                    # 处理方法的设置
                    _methods = ['GET'] if _methods is None else _methods

                    # 对于实例对象, 获取真实的函数对象
                    if _instance is not None:
                        _value = getattr(_instance, _name)

                    # 加入路由
                    app.add_route(
                        _value, _route, methods=_methods, name=_router_name, version=version
                    )

    @classmethod
    def support_object_resp(cls, func):
        """
        支持函数直接返回Python对象的修饰符
        注: 正常函数应该返回标准的sanic.response.HTTPResponse对象, 本修饰符允许按以下方式返回
            1、返回sanic.response.HTTPResponse对象
            2、返回二元数组, 其中第1个为要返回的内容对象, 第2个为状态码
            3、直接返回要处理的对象, 状态码默认为200(注意不可直接将数组对象返回)

        @param {function} func - 修饰符处理的函数

        @example Restful函数返回非字符串格式内容
            @SanicTool.support_object_resp
            def func(a, b):
                ...
                return {'a':'value'}
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            _ret = func(*args, **kwargs)
            if isinstance(_ret, HTTPResponse):
                # 已按正常规范返回
                return _ret
            else:
                _status = 200
                if isinstance(_ret, (tuple, list)):
                    # 是列表, 第1个是要返回的值, 第2个是http状态码
                    _body = _ret[0]
                    if len(_ret) > 1:
                        _status = _ret[1]
                else:
                    _body = _ret

                if isinstance(_body, str):
                    # 字符串
                    return text(_body, status=_status)
                else:
                    # 对象
                    return json(_body, status=_status)
        return wrapper


class SanicServer(ServerBaseFW):
    """
    Sanic服务
    """

    #############################
    # 静态函数
    #############################
    @classmethod
    async def default_index_handler(cls, request):
        """
        默认根路径处理函数, 返回资源部不存在的错误

        @param {sanic.request.Request} request - 请求对象
        """
        return text("Resource not found", status=404)

    #############################
    # 添加的属性
    #############################
    @property
    def native_app(self) -> Sanic:
        """
        获取原生app对象
        @property {Sanic}
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
            app_config {dict} - Sanic初始化参数字典(请参考Sanic官方文档), 常用参数包括:
                ctx {object} - 自定义上下文对象, 通过上下文对象可以在程序中共享数据
                    注: 默认会创建一个SimpleNamespace作为上下文, 你也可以送入一个指定的对象初始化上下文, 例如送入"ctx: {}"
                config {sanic.config.Config} - 自定义应用配置, 传入的对象应继承sanic.config.Config类
                    注: 可以通过 app.config.XXX 访问所设置的自定义配置; 此外也可以在创建服务后, 直接修改 app.config 的配置值(字典操作)
                log_config {dict} - 自定义的日志配置信息, 默认为sanic.log.LOGGING_CONFIG_DEFAULTS
                    注: 要求定义的日志名必须包括sanic.root、sanic.error、sanic.access
                configure_logging {bool} - 是否使用自定义日志配置, 配合log_config自行设置特定的日志
            run_config {dict} - SanicServer运行参数字典(请参考Sanic官方文档), 常用参数包括:
                host {str} - 绑定的主机地址, 默认为'127.0.0.1'
                port {int} - 服务监听的端口, 默认为8000
                workers {int} - 工作线程数, 默认为1
                ssl {ssl.SSLContext|dict} - ssl加密连接的配置, 可以有两种配置方式
                    1、使用ssl.create_default_context方法创建ssl.SSLContext并传入, 具体代码可参考官方文档示例
                    2、通过字典传递密钥和证书文件: ssl = {"cert": "/path/to/cert", "key": "/path/to/keyfile"}
                debug {bool} - 是否开启debug模式(生产部署请关闭), 默认为False
                    注: 非asgi模式不支持设置debug为True
                access_log {bool} - 启用请求访问日志(生产部署请关闭), 默认为True
            cors_config {dict} - 跨域访问的支持参数, 具体参数见 https://sanicframework.org/zh/plugins/sanic-ext/http/cors.html#%E9%85%8D%E7%BD%AE-configuration
                常用的参数如下:
                CORS_ORIGINS - 允许访问资源的来源, 默认为'*', 传参支持:
                    字符串格式, 例如'http://foobar.com,http://bar.com'
                    数组格式, 例如['http://foobar.com', 'http://bar.com']
                    正则表达式对象(re.Pattern), 例如 re.compile(r'http://.*\.bar\.com')
                CORS_METHODS - 允许来源可以使用的http方法, 例如['GET', 'POST']
                CORS_EXPOSE_HEADERS - 允许来源获取到返回值的header中的值列表, 如果不设置客户端只能获取6个基本字段: Cache-Control、Content-Language、Content-Type、Expires、Last-Modified、Pragma
                    例如['header-name-1', 'header-name-2']
                CORS_ALLOW_HEADERS - 服务器支持的header的字段列表, 默认为*
                CORS_SUPPORTS_CREDENTIALS {bool} - 是否允许发送Cookie, 默认为False
            use_asgi {bool} - 是否使用asgi服务模式启动(例如daphne、uvicorn、hypercorn、Gunicorn-不支持异步)
                注: asgi服务模式, 将由第三方服务应用通过app实例启动服务, 不会调用start/stop方法进行处理
            run_in_thread {bool} - 是否线程启动模式, 默认为True
                注: 线程启动模式不支持多工作线程, 而非线程启动不支持异步起动
            auto_trace {bool} - 是否开启http的trace功能(允许客户端TRACE请求时原样返回收到的报文内容), 默认为False
            oas {bool} - 是否开启OpenAPI文档生成, 默认为False
            oas_config {dict} - OpenAPI自动文档生成参数, 具体参数见 https://sanicframework.org/zh/plugins/sanic-ext/openapi/ui.html#%E9%85%8D%E7%BD%AE%E9%80%89%E9%A1%B9-config-options
                常用参数包括:
                OAS_UI_DEFAULT - 控制文档显示的UI, 可以为 redoc(默认) 或 swagger; 如果设置为 None, 则不会设置文档路由
                OAS_URL_PREFIX - 用于 OpenAPI 文档蓝图的 URL 前缀, 默认为 '/docs'
            add_default_route {bool} - 添加默认根节点的GET路由, 默认为True
                注意: 如果不添加根节点路由, 且启动前未添加含GET方法的路由, Sanic服务启动会报错
        @param {dict} support_auths={} - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
            注意: 支持的auth对象必须有auth_required这个修饰符函数
        @param {function} before_server_start=None - 服务器启动前执行的函数对象, 传入服务自身(self)
        @param {function} after_server_start=None - 服务器启动后执行的函数对象, 传入服务自身(self)
        @param {function} before_server_stop=None - 服务器关闭前执行的函数对象, 传入服务自身(self)
        @param {function} after_server_stop=None - 服务器关闭后执行的函数对象, 传入服务自身(self)
            注: CPU为M1版本的 Mac Book, 通过 ctrl+c 结束进程时无法正常关闭Sanic, 因此 before_server_stop 和 after_server_stop 无法正常使用
                其他操作系统暂未测试验证
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

    async def start(self, is_asyn: bool = False, sleep_time: float = 0.5, **kwargs) -> CResult:
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
            _run_in_thread = self._server_config.get('run_in_thread', True)
            # 只有线程启动模式支持异步启动处理
            if not _run_in_thread and is_asyn:
                raise RuntimeError('only run_in_thread mode support async start')

            # 获取锁，拿到最准确的服务状态
            self._status_lock.acquire()
            try:
                if self.status != EnumServerRunStatus.Stop:
                    # 不属于停止状态，不能启动
                    _temp_result = CResult(code='21401')  # 服务启动失败-服务已启动
                    self._logger.log(
                        self._log_level,
                        '[SER-STARTING][NAME:%s]%s' % (self._app_name, _temp_result.msg))
                    return _temp_result

                # 将运行状态置为正在启动
                self._status = EnumServerRunStatus.WaitStart
                self._is_before_server_stop_runned = False
                self._is_after_server_stop_runned = False
            finally:
                # 释放锁
                self._status_lock.release()

            if not _run_in_thread:
                # 直接执行启动动作
                self._server_run_fun()
            else:
                # 线程启动模式
                self._thread = threading.Thread(
                    target=self._server_run_fun,
                    name='Thread-SanicServer-Running-%s' % self._app_name
                )
                self._thread.setDaemon(True)
                self._thread.start()

                # 等待服务启动完成
                while self.status == EnumServerRunStatus.WaitStart:
                    await asyncio.sleep(sleep_time)

        if not _result.is_success():
            # 执行出现错误, 直接返回
            return _result

        if is_asyn:
            # 异步模式, 直接返回
            return _result

        # 同步模式, 循环等待结束
        try:
            while self._status == EnumServerRunStatus.Running:
                await asyncio.sleep(sleep_time)
        except:
            # 遇到键盘退出情况, 结束运行
            await self.stop()

        return _result

    async def stop(self, overtime: float = 0, sleep_time: int = 0.5, **kwargs) -> CResult:
        """
        停止服务运行
        (可以为同步或异步函数)

        @param {float} overtime=0 - 等待超时时间, 单位为秒, 0代表一直不超时
        @param {float} sleep_time=0.5 - 每次等待睡眠时间, 单位为秒
        @param {kwargs} - 实现类自定义的扩展参数

        @returns {CResult} - 停止结果, result.code: '00000'-成功, '21402'-服务停止失败-服务已关闭,
            '31005'-执行超时, 29999'-其他系统失败
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER-STOPING][NAME:%s]%s: ' % (
                self._app_name, _('stop service error')),
            force_log_level=logging.ERROR
        ):
            _run_in_thread = self._server_config.get('run_in_thread', True)
            if not _run_in_thread:
                raise RuntimeError('only run_in_thread mode support stop')

            self._status_lock.acquire()
            try:
                if self._status != EnumServerRunStatus.Running:
                    _temp_result = CResult(code='21402')  # 服务停止失败-服务已关闭
                    self._logger.log(
                        self._log_level,
                        '[SER-STOPING][NAME:%s]%s' % (self._app_name, _temp_result.msg))
                    return _temp_result

                self._logger.log(
                    self._log_level,
                    '[SER-STOPING][NAME:%s]%s' % (self._app_name, _('server stoping')))

                # 执行关闭前操作
                self._status = EnumServerRunStatus.WaitStop
                if not self._is_before_server_stop_runned and self._before_server_stop is not None:
                    await AsyncTools.async_run_coroutine(
                        self._before_server_stop(self)
                    )

                # 直接结束线程
                try:
                    if self._thread.is_alive():
                        RunTool.stop_thread(self._thread)
                except:
                    self._logger.log(
                        self._log_level,
                        '[SER-STOPING][NAME:%s]%s: %s' % (
                            self._app_name, _('close server thread error'), traceback.format_exc()
                        )
                    )
                self._status = EnumServerRunStatus.Stop

                # 执行关闭后操作
                if not self._is_after_server_stop_runned and self._after_server_stop is not None:
                    await AsyncTools.async_run_coroutine(self._after_server_stop(self))
            finally:
                self._status_lock.release()

        # 返回结果
        return _result

    async def add_service(self, service_uri: str, handler: Callable, name: str = None,
                  with_para: bool = False, methods: list = None, version=None, **kwargs) -> CResult:
        """
        添加请求处理服务
        (可以为同步或异步函数)

        @param {str} service_uri - 服务唯一标识, 例如'/demo'
        @param {Callable} handler - 请求处理函数, 应可同时支持同步或异步函数
            注: 由实现类自定义请求函数的要求
        @param {str} name=None - 路由标识, 如果不传默认使用函数名(会存在函数名相同导致异常的情况)
        @param {bool} with_para=False - 路由是否根据函数添加入参
        @param {list} methods=None - 指定路由支持的方法, 如果不传代表支持所有方法
        @param {int|float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        @param {kwargs}  - 自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '21405'-服务名已存在, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            SanicTool.add_route(
                self._app, url=service_uri, func=handler, name=name, with_para=with_para, methods=methods
            )

        return _result

    async def remove_service(self, service_uri: str, **kwargs) -> CResult:
        """
        移除请求处理服务
        (可以为同步或异步函数)

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 添加服务结果, result.code: '00000'-成功, '1404'-不支持的命令, 其他-异常
        """
        return CResult(code='21404', i18n_msg_paras=('remove_service', ))

    async def add_service_by_class(self, class_objs: list, blacklist: list = None, class_name_mapping: dict = None,
            url_base: str = 'api', version=None) -> CResult:
        """
        通过类对象动态增加服务

        @param {list} class_objs - Api类对象清单(可以支持传入类对象, 也可以支持传入类实例)
        @param {list} blacklist=None - 禁止添加的服务黑名单, 格式为"类名/函数名"
        @param {dict} class_name_mapping=None - 类名映射, 可以根据这个改变访问url的路径, key为真实类名, value为映射后的类名
        @param {str} url_base='api' - 路由开始的基础url
        @param {int|float|str} version=None - 指定路由的版本, 则路由变为"/v{version}/url"
        """
        _result = CResult(code='00000')  # 成功
        with ExceptionTool.ignored_cresult(
            result_obj=_result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (self._app_name, _('add service error'))
        ):
            SanicTool.add_route_by_class(
                self._app, class_objs, blacklist=blacklist, class_name_mapping=class_name_mapping,
                url_base=url_base, version=version
            )

        return _result

    #############################
    # 内部函数
    #############################
    def _server_status_change(self, status: EnumServerRunStatus):
        """
        通用的服务器状态修改函数

        @param {EnumServerRunStatus} status - 要修改的服务器状态
        """
        # 无需使用的函数, 置为空函数
        pass

    def _start_server_thread_fun(self, tid):
        """
        启动服务处理主线程, 本线程结束就代表服务停止

        @param {int} tid - 线程id

        """
        # 无需使用的函数, 置为空函数
        pass

    #############################
    # 实现类需重载的内部函数
    #############################
    async def _real_server_initialize(self, tid) -> CResult:
        """
        初始化真正的服务端处理对象
        注: 可以在该函数中启动真正的服务, 例如绑定监听端口

        @param {int} tid - 服务线程id

        @returns {CResult} - 启动结果:
            result.code: '00000'-成功, 其他值为失败
            result.server_info: 启动成功后的服务信息, 用于传递到后续的服务处理函数
        """
        # 无需使用的函数, 置为空函数
        pass

    async def _real_server_accept_and_run(self, tid, server_info) -> CResult:
        """
        真正的服务获取请求并运行
        注: 支持同步或异步函数, 可以在该函数中获取请求, 并启动线程执行请求处理

        @param {int} tid - 线程id
        @param {Any} server_info - 启动成功后的服务信息

        @returns {CResult} - 处理结果:
            result.code: '00000'-成功, 其他值为失败, 如果为失败将停止服务
            result.is_finished: 指示服务是否已完成, True - 已处理完成可停止服务, False - 未完成, 需循环处理下一个请求
        """
        # 无需使用的函数, 置为空函数
        pass

    async def _real_server_prepare_stop(self, tid) -> CResult:
        """
        服务关闭前的处理函数
        注: 支持同步或异步函数, 可以在该函数中等待已接入的请求或线程完成处理

        @param {int} tid - 线程id

        @returns {CResult} - 处理结果:
            result.code: '00000'-成功, 其他值为失败
            result.is_finished: 指示停止前的预处理是否已完成, True - 已处理完成可停止服务, False - 未完成, 需循环继续调用本函数
        """
        # 无需使用的函数, 置为空函数
        pass

    async def _real_server_stop(self, tid, server_info):
        """
        真正服务的关闭处理
        注: 支持同步或异步函数, 可以在该函数中清理处理线程并关闭监听

        @param {int} tid - 线程id
        @param {Any} server_info - 启动成功后的服务信息
        """
        # 无需使用的函数, 置为空函数
        pass

    def _std_init_config(self):
        """
        标准化服务初始配置
        """
        # 实现类可以通过该函数设置或修改内部参数
        # 参数处理
        if self._server_config.get('run_config', None) is None:
            self._server_config['run_config'] = {}

        # 创建应用
        self._app = Sanic(self._app_name, **self._server_config.get('app_config', {}))

        # 跨域访问支持
        self._app.config.update(self._server_config.get('cors_config', {}))
        # 是否开启http trace方法支持
        if self._server_config.get('auto_trace', False):
            self._app.config.HTTP_AUTO_TRACE = True

        # 是否开启OpenAPI文档生成
        if self._server_config.get('oas', False):
            self._app.config.OAS = True
            self._app.config.update(**self._server_config.get('oas_config', {}))
        else:
            # 不开启文档生成
            self._app.config.OAS = False

        Extend(self._app)

        # 日志对象的处理
        self._app.ctx.logger = self._logger

        # 内部控制参数
        self._thread = None  # 正在运行的线程对象
        self._is_before_server_stop_runned = True  # 标记结束前函数是否已执行
        self._is_after_server_stop_runned = True  # 标记结束后函数是否已执行

        # 添加服务生命周期的监听服务
        if self._before_server_start is not None:
            self._app.register_listener(self._before_server_start_func, 'before_server_start')

        self._app.register_listener(self._after_server_start_func, 'after_server_start')

        if not self._server_config.get('run_in_thread', True):
            # 线程执行模式无法处理结束的函数, 需要自行处理
            self._app.register_listener(self._before_server_stop_func, 'before_server_stop')
            self._app.register_listener(self._after_server_stop_func, 'after_server_stop')

        # 区别对待不使用asgi启动的处理
        if not self._server_config.get('use_asgi', False):
            self._server_config['run_config']['debug'] = False  # 线程启动不支持debug模式
            self._server_config['run_config']['register_sys_signals'] = False  # 线程启动需要把信号注册去掉
            if self._server_config.get('run_in_thread', True):
                self._server_config['run_config']['workers'] = 1  # 线程启动模式工作线程只支持1个

        # 是否添加默认路由
        if self._server_config.get('add_default_route', True):
            AsyncTools.sync_run_coroutine(
                self.add_service(
                    '/', self.default_index_handler, name=self._app_name + '.default_index_handler'
                )
            )

    #############################
    # 内部函数
    #############################
    def _server_run_fun(self):
        """
        启动服务器的线程函数
        """
        try:
            # 判断是否已有路由, 如果没有则添加默认路由(否则无法正常启动)
            if len(self._app.router.routes) == 0:
                AsyncTools.sync_run_coroutine(
                    self.add_service(
                        '/', self.default_index_handler, name=self._app_name + '.default_index_handler'
                    )
                )

            # 启动服务
            _run_config = self._server_config.get('run_config', {})
            self._app.run(**_run_config)
        finally:
            # 再更新一次状态
            self._status = EnumServerRunStatus.Stop

    async def _before_server_start_func(self, *args, **kwargs):
        """
        服务启动前执行的函数
        """
        _resp = self._before_server_start(self)
        if isawaitable(_resp):
            _resp = await _resp

    async def _after_server_start_func(self, *args, **kwargs):
        """
        服务启动后函数
        """
        self._status_lock.acquire()
        try:
            self._status = EnumServerRunStatus.Running  # 更新状态为运行中
        finally:
            self._status_lock.release()

        if self._after_server_start is not None:
            _resp = self._after_server_start(self)  # 执行启动后运行函数
            if isawaitable(_resp):
                _resp = await _resp

    async def _before_server_stop_func(self, *args, **kwargs):
        """
        服务关闭前执行函数
        """
        self._is_before_server_stop_runned = True
        if self._before_server_stop is not None:
            _resp = self._before_server_stop(self)
            if isawaitable(_resp):
                _resp = await _resp

        self._status_lock.acquire()
        try:
            self._status = EnumServerRunStatus.WaitStop  # 更新状态为关闭中
        finally:
            self._status_lock.release()

    async def _after_server_stop_func(self, *args, **kwargs):
        """
        服务关闭后执行的函数
        """
        self._is_after_server_stop_runned = True

        self._status_lock.acquire()
        try:
            self._status = EnumServerRunStatus.Stop  # 更新状态为关闭中
        finally:
            self._status_lock.release()

        if self._after_server_stop is not None:
            _resp = self._after_server_stop(self)
            if isawaitable(_resp):
                _resp = await _resp
