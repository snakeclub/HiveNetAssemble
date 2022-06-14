#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Web服务基础框架类

@module server
@file server.py
"""
import sys
import os
import logging
import copy
import threading
import datetime
import asyncio
import json
import socket
from functools import wraps
from collections import OrderedDict
from enum import Enum
from typing import Callable
from HiveNetCore.generic import CResult, NullObj
from HiveNetCore.i18n import _, get_global_i18n, init_global_i18n
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetCore.utils.net_tool import NetTool
from HiveNetCore.utils.run_tool import AsyncTools, RunTool
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetWebUtils.utils.socket import SocketTool


__MOUDLE__ = 'server'  # 模块名
__DESCRIPT__ = u'Web服务基础框架类'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.05.04'  # 发布日期


class EnumServerRunStatus(Enum):
    """
    服务器运行状态

    @enum {string}
    """
    Stop = 'Stop'  # 停止
    Running = 'Running'  # 正在运行
    WaitStop = 'WaitStop'  # 等待停止
    WaitStart = 'WaitStart'  # 等待启动
    ForceStop = 'ForceStop'  # 强制停止


class ServerBaseFW(object):
    """
    服务基础类, 定义了服务的标准调用函数
    """
    #############################
    # 静态函数
    #############################
    @classmethod
    def get_init_server_dict(cls) -> OrderedDict:
        """
        获取已经初始化的服务访问字典

        @returns {OrderedDict} - 返回字典
        """
        INIT_SERVER = RunTool.get_global_var('INIT_HIVENET_WEB_UTILS_SERVER')
        if INIT_SERVER is None:
            INIT_SERVER = OrderedDict()
            RunTool.set_global_var('INIT_HIVENET_WEB_UTILS_SERVER', INIT_SERVER)

        return INIT_SERVER

    @classmethod
    def get_init_server(cls, app_name: str = None):
        """
        获取已经初始化的服务对象

        @param {str} app_name=None - 要获取的服务的app_name, 如果不传默认取第一个

        @returns {ServerBaseFW} - 获取到的对象
        """
        INIT_SERVER = cls.get_init_server_dict()
        if app_name is None:
            return list(INIT_SERVER.values())[0]
        else:
            return INIT_SERVER[app_name]

    @classmethod
    def get_auth_fun(cls, auth_name: str = '', app_name: str = None):
        """
        获取Server支持的Auth实例对象
        注: 该函数主要用于 auth_required_static 修饰符入参

        @param {str} auth_name='' - 验证对象类型名(比如类名, 具体取决于Server的初始化参数)
        @param {str} app_name=None - 要获取的Server的app_name, 如果不传默认取第一个
        """
        _server = cls.get_init_server(app_name=app_name)
        return _server._support_auths[auth_name]

    @classmethod
    def auth_required_static(cls, f=None, auth_name: str = '', app_name: str = None):
        """
        静态的服务鉴权修饰函数
        (用于支持鉴权对象实例化前对函数进行修饰处理)

        @param {function} f - 要调用的函数
        @param {str} auth_name='' - 验证对象类型名(比如类名, 具体取决于Server的初始化参数)
        @param {str} app_name=None - 要获取的Server的app_name, 如果不传默认取第一个

        @example  指定API需要IP黑白名单验证
            class RestfulApiClass(object):
                @classmethod
                @ServerBaseFW.auth_required_static(auth_name='IPAuth', app_name='demo_servr')
                def login(user_name, methods=['POST'], **kwargs):
                    ...
        """
        def auth_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 获取验证对象
                _auth = cls.get_auth_fun(auth_name=auth_name, app_name=app_name)

                # 执行验证修饰函数
                return  AsyncTools.sync_run_coroutine(
                    _auth.auth_required_call(f, *args, **kwargs)
                )
            return decorated

        if f:
            return auth_internal(f)
        return auth_internal

    #############################
    # 构造函数和析构函数
    #############################
    def __init__(self, app_name: str, server_config: dict = {}, support_auths: dict = {},
            before_server_start=None, after_server_start=None,
            before_server_stop=None, after_server_stop=None, logger=None, log_level: int = logging.INFO,
            load_i18n_para=None, **kwargs):
        """
        构造函数

        @param {str} app_name - 服务器名称
        @param {dict} server_config={} - 服务配置字典, 由实现类自定义传值, 例如绑定主机, 端口等
        @param {dict} support_auths={} - 服务器支持的验证对象字典, key为验证对象类型名(可以为类名), value为验证对象实例对象
            注意: 支持的auth对象必须有auth_required_call这个函数
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
        # 控制程序逻辑的一些特殊参数, 用来支持多种处理模式, 实现类可以自行修改参数改变框架的处理模式
        # 启动服务模式, 支持的模式说明如下:
        # thread - 默认, 在子线程的运行启动过程, 执行的线程函数为 _start_server_thread_fun
        # func - 执行实现类的自有函数进行启动, 不启动线程, 直接执行_start_server_thread_fun
        self._start_server_mode = 'thread'

        # 判断初始化是否成功的变量
        self._init_success = False

        # 判断服务器名是否重复
        INIT_SERVER = self.get_init_server_dict()
        if app_name in INIT_SERVER.keys():
            raise RuntimeError(_('server [$1] already exists', app_name))

        # 参数处理
        self._app_name = app_name
        self._server_config = copy.deepcopy(server_config)
        self._support_auths = support_auths
        self._before_server_start = before_server_start
        self._after_server_start = after_server_start
        self._before_server_stop = before_server_stop
        self._after_server_stop = after_server_stop
        self._logger = logger
        self._log_level = log_level
        if logger is None:
            logging.basicConfig()
            self._logger = logging.getLogger(__name__)
            self._logger.level = logging.INFO
        self._kwargs = kwargs

        # 加载多国语言
        self._load_i18n_dict(
            os.path.join(os.path.dirname(__file__), 'i18n'), 'socket_server', 'utf-8'
        )  # 框架默认的语言文件
        _load_i18n_para = load_i18n_para
        if _load_i18n_para is not None:
            _path = _load_i18n_para.get('path', '')
            _prefix = _load_i18n_para.get('prefix', '')
            _encoding = _load_i18n_para.get('encoding', 'utf-8')
            if _prefix != '':
                self._load_i18n_dict(_path, _prefix, _encoding)

        # 内部参数
        self._status = EnumServerRunStatus.Stop  # 服务状态
        self._status_lock = threading.RLock()  # 服务状态变更的锁
        self._start_begin_time = datetime.datetime.now()  # 服务启动开始时间
        self._last_start_result = None  # 启动如果失败, 存放服务线程中返回的失败原因结果对象
        self._stop_begin_time = datetime.datetime.now()  # 服务关闭开始时间
        self._dynamic_var = {}  # 存放动态内部变量的字典, 方便实现类进行变量定义

        # 服务路由管理, key为service_uri, value为{'handler': 执行函数对象, 'kwargs': 添加服务时的kwargs传参}
        self._service_router = {}

        # 标准化服务初始配置
        self._std_init_config()

        # 将自己加入已初始化的服务器对象全局变量
        INIT_SERVER[self._app_name] = self

        # 标注初始化成功
        self._init_success = True

    def __del__(self):
        """
        析构函数
        """
        # 将自己从已初始化的服务器对象全局变量中移除
        if self._init_success:
            INIT_SERVER = self.get_init_server_dict()
            INIT_SERVER.pop(self._app_name, None)

            # 判断是否服务还在运行, 强制关闭服务
            if self._status == EnumServerRunStatus.Running:
                AsyncTools.sync_run_coroutine(
                    self.stop(is_force=True)
                )

    #############################
    # 其他公共属性及函数
    #############################
    @property
    def status(self) -> EnumServerRunStatus:
        """
        获得服务器运行状态

        @property {EnumServerRunStatus} - 返回运行状态
        """
        return self._status

    @property
    def app_name(self) -> str:
        """
        获取应用名
        @property {str}
        """
        return self._app_name

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
            # 先获取锁，拿到最准确的服务状态
            self._status_lock.acquire()
            try:
                if self.status != EnumServerRunStatus.Stop:
                    # 不属于停止状态，不能启动
                    _temp_result = CResult(code='21401')  # 服务启动失败-服务已启动
                    self._logger.log(
                        self._log_level,
                        '[SER-STARTING][NAME:%s]%s' % (self._app_name, _temp_result.msg))
                    return _temp_result

                # 执行启动服务的动作，通过线程方式启动
                self._start_begin_time = datetime.datetime.now()
                self._server_status_change(EnumServerRunStatus.WaitStart)
                if self._start_server_mode == 'func':
                    # func模式, 直接运行线程函数
                    _result = self._start_server_thread_fun(1)
                else:
                    # thread模式
                    _server_thread = threading.Thread(
                        target=self._start_server_thread_fun, args=(1,), name='Thread-Server-Main'
                    )
                    _server_thread.setDaemon(True)
                    _server_thread.start()
            finally:
                # 释放锁
                self._status_lock.release()

        if not _result.is_success():
            # 执行出现错误, 直接返回
            return _result

        # 等待服务启动完成
        while self.status == EnumServerRunStatus.WaitStart:
            await asyncio.sleep(sleep_time)

        if self._status != EnumServerRunStatus.Running:
            # 服务线程中出现启动异常
            return self._last_start_result

        if is_asyn:
            # 异步模式, 直接返回
            return _result

        # 同步模式, 循环等待结束
        while self._status == EnumServerRunStatus.Running:
            await asyncio.sleep(sleep_time)

        return _result

    async def stop(self, overtime: float = 0, sleep_time: int = 0.5, **kwargs) -> CResult:
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
                    # 运行状态，处理设置等待关闭状态
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
                    # 不属于运行状态，不能处理
                    _temp_result = CResult(code='21402')  # 服务停止失败-服务已关闭
                    self._logger.log(
                        self._log_level,
                        '[SER-STOPING][NAME:%s]%s' % (self._app_name, _temp_result.msg))
                    return _temp_result
            finally:
                self._status_lock.release()

            # 对于func模式, 需要通过线程执行主动处理关闭的逻辑
            if self._start_server_mode == 'func':
                _stop_thread = threading.Thread(
                    target=self._func_mode_stop_thread_fun, args=(0,), name='Thread-Server-Stop-Func'
                )
                _stop_thread.setDaemon(True)
                _stop_thread.start()

        # 等待服务关闭
        _begin_time = datetime.datetime.now()  # 记录等待开始时间
        while True:
            if self._status == EnumServerRunStatus.Stop:
                break

            if overtime > 0 and (datetime.datetime.now() - _begin_time).total_seconds() > overtime:
                _result = CResult(code='31005')  # 执行超时
                break

            # 等待下一次检查
            await asyncio.sleep(sleep_time)

        # 返回结果
        return _result

    async def add_service(self, service_uri: str, handler: Callable, **kwargs) -> CResult:
        """
        添加请求处理服务
        (可以为同步或异步函数)

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {Callable} handler - 请求处理函数, 应可同时支持同步或异步函数
            注: 由实现类自定义请求函数的要求
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
                self._service_router[service_uri] = {
                    'handler': handler, 'kwargs': kwargs
                }

        return _result

    async def remove_service(self, service_uri: str, **kwargs) -> CResult:
        """
        移除请求处理服务
        (可以为同步或异步函数)

        @param {str} service_uri - 服务唯一标识, 例如服务名或url路由
        @param {kwargs}  - 实现类的自定义扩展参数

        @returns {CResult} - 删除服务结果, result.code: '00000'-成功, '21403'-服务不存在, 其他-异常
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

        return _result

    #############################
    # 内部函数
    #############################

    def _load_i18n_dict(self, path: str, prefix: str, encoding: str):
        """
        装载多国语言字典

        @param {str} path - 要加载的i18n字典文件路径, 如果填空代表程序运行的当前路径
        @param {str} prefix - 要加载的i18n字典文件前缀
        @param {str} encoding - 要加载的i18n字典文件的字符编码, 默认为'utf-8'
        """
        _i18n_obj = get_global_i18n()
        if _i18n_obj is None:
            # 创建对象并加入到全局中
            init_global_i18n()
            _i18n_obj = get_global_i18n()

        # 进行语言装载
        _i18n_obj.load_trans_from_dir(
            trans_file_path=path, trans_file_prefix=prefix, encoding=encoding, append=True
        )

    def _server_status_change(self, status: EnumServerRunStatus):
        """
        通用的服务器状态修改函数

        @param {EnumServerRunStatus} status - 要修改的服务器状态
        """
        self._status_lock.acquire()
        try:
            self._status = status
        finally:
            self._status_lock.release()

    def _start_server_thread_fun(self, tid):
        """
        启动服务处理主线程, 本线程结束就代表服务停止

        @param {int} tid - 线程id

        """
        _result = CResult(code='00000')  # 成功
        _server_info = None
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

            # 执行真正服务初始化处理，执行通过则代表启动成功
            self._last_start_result = AsyncTools.sync_run_coroutine(self._real_server_initialize(tid))
            if not self._last_start_result.is_success():
                # 启动失败，登记了日志，修改状态为未启动，退出
                self._logger.log(
                    logging.ERROR,
                    ('[SER-STARTING][NAME:%s][USE:%ss]%s: %s - %s' % (
                        self._app_name,
                        str((datetime.datetime.now() - self._start_begin_time).total_seconds()),
                        _('start server error'), self._last_start_result.code, self._last_start_result.msg))
                )
                self._server_status_change(EnumServerRunStatus.Stop)
                return self._last_start_result

            # 启动成功
            self._logger.log(
                self._log_level,
                '[SER-STARTED][NAME:%s][USE:%ss]%s' % (
                    self._app_name,
                    str((datetime.datetime.now() - self._start_begin_time).total_seconds()),
                    _('start server sucess')
                ))
            self._server_status_change(EnumServerRunStatus.Running)

            # 服务启动成功, 执行after_server_start
            if self._after_server_start is not None:
                AsyncTools.sync_run_coroutine(self._after_server_start(self))

            # 如果是func模式, 不处理循环, 直接返回启动结果即可
            if self._start_server_mode == 'func':
                return self._last_start_result

            # 开始进入循环处理
            _server_info = self._last_start_result.server_info  # 真正服务启动返回的服务器信息
            while True:
                if self._status == EnumServerRunStatus.WaitStop:
                    # 收到指令等待停止, 执行关闭前的预处理操作
                    self._prepare_stop_process_fun(tid)
                    break
                elif self._status == EnumServerRunStatus.ForceStop:
                    # 收到指令马上停止
                    # 服务关闭前处理函数
                    if self._before_server_stop is not None:
                        AsyncTools.sync_run_coroutine(
                            self._before_server_stop(self)
                        )

                    break
                else:
                    # 正常执行一次服务处理函数
                    _run_result = AsyncTools.sync_run_coroutine(
                        self._real_server_accept_and_run(tid, _server_info)
                    )

                    # 判断是否结束服务
                    if _run_result.is_success() and not _run_result.is_finished:
                        continue
                    else:
                        # 根据运行处理函数的返回结果, 结束服务
                        # 服务关闭前处理函数
                        if self._before_server_stop is not None:
                            AsyncTools.sync_run_coroutine(
                                self._before_server_stop(self)
                            )
                        break

        # 正常情况func模式不应该走到这个这步骤, 说明出了异常
        if self._start_server_mode == 'func':
            self._logger.log(
                logging.ERROR,
                ('[SER-STARTING][NAME:%s][USE:%ss]%s: %s - %s' % (
                    self._app_name,
                    str((datetime.datetime.now() - self._start_begin_time).total_seconds()),
                    _('start server error'), self._result.code, self._result.msg))
            )
            self._server_status_change(EnumServerRunStatus.Stop)
            return _result

        # 线程结束就代表服务已关闭，执行结束处理函数
        AsyncTools.sync_run_coroutine(self._real_server_stop(tid, _server_info))
        self._server_status_change(EnumServerRunStatus.Stop)
        self._logger.log(
            self._log_level,
            '[SER-STOPED][NAME:%s][USE:%ss]%s' % (
                self._app_name, str((datetime.datetime.now() - self._stop_begin_time).total_seconds()),
                _('server stoped')
            ))

        # 服务关闭后执行函数
        if self._after_server_stop is not None:
            AsyncTools.sync_run_coroutine(self._after_server_stop(self))

    def _prepare_stop_process_fun(self, tid):
        """
        关闭前的预处理函数

        @param {int} tid - 线程id
        """
        # 服务关闭前处理函数
        if self._before_server_stop is not None:
            AsyncTools.sync_run_coroutine(
                self._before_server_stop(self)
            )

        while True:
            if self._status == EnumServerRunStatus.ForceStop:
                # 过程中又被要求强制退出
                break

            # 执行服务关闭前的处理函数
            _prepare_stop_result = AsyncTools.sync_run_coroutine(
                self._real_server_prepare_stop(tid)
            )
            if not _prepare_stop_result.is_success() and not _prepare_stop_result.is_finished:
                # 预处理未完成，需要循环处理
                AsyncTools.sync_run_coroutine(
                    asyncio.sleep(0.1)
                )
                continue
            else:
                # 预处理已完成，退出
                break

    def _func_mode_stop_thread_fun(self, tid):
        """
        func模式的关闭处理线程函数

        @param {int} tid - 线程id
        """
        # 服务关闭前, 执行关闭前的预处理操作
        self._prepare_stop_process_fun(tid)

        # 执行真正服务关闭
        AsyncTools.sync_run_coroutine(self._real_server_stop(tid, None))

        self._server_status_change(EnumServerRunStatus.Stop)
        self._logger.log(
            self._log_level,
            '[SER-STOPED][NAME:%s][USE:%ss]%s' % (
                self._app_name, str((datetime.datetime.now() - self._stop_begin_time).total_seconds()),
                _('server stoped')
            ))

        # 服务关闭后执行函数
        if self._after_server_stop is not None:
            AsyncTools.sync_run_coroutine(self._after_server_stop(self))

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
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(_result):
            # 注: 重载该函数, 可在该部分实现自定义的服务初始化或启动逻辑
            pass

        # 返回处理结果
        return _result

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
        _result = CResult(code='00000')  # 成功
        _result.is_finished = False
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (
                self._app_name, _('server run error')),
            force_log_level=logging.ERROR
        ):
            # 注: 重载该函数, 可在该部分实现自定义的获取请求及处理逻辑
            pass

        # 返回处理结果
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
            # 注: 重载该函数, 可在该部分实现自定义的服务关闭前处理
            pass

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
            # 注: 重载该函数, 可在该部分实现自定义的服务关闭处理
            pass

    def _std_init_config(self):
        """
        标准化服务初始配置
        """
        # 实现类可以通过该函数设置或修改内部参数
        pass


class TcpIpServer(ServerBaseFW):
    """
    TcpIp协议的服务实现
    通讯协议为: 前4个字节为后续报文信息的字节长度(int), 后面报文信息为json字符串的字节数组, 字节编码为utf-8
    注:
    1、通过add_service可以添加service_uri为''的处理函数, 如果请求匹配不到service_uri时将使用该函数进行处理;
    2、add_service的处理函数的定义如下:
        func(net_info, service_uri: str, request: dict) -> dict
            service_uri - 匹配上的服务标识
            request - 获取到的请求信息json字典
            返回值为要返回到socket的字典, 如果无需返回则使用None返回
    """

    def __init__(self, app_name: str, server_config: dict = None, support_auths: dict = {},
            before_server_start=None, after_server_start=None,
            before_server_stop=None, after_server_stop=None, logger=None, log_level: int = logging.INFO,
            load_i18n_para=None, **kwargs):
        """
        构造函数

        @param {str} app_name - 服务器名称
        @param {dict} server_config={} - 服务配置字典
            ip {str} - 主机名或IP地址, 默认为''
            port {int} - 监听端口, 默认为8080
            max_connect {int} - 允许最大连接数, 默认为20
            recv_timeout {float} - 数据接收的超时时间, 单位为秒, 默认为10
            send_timeout {float} - 数据发送的超时时间, 单位为秒, 默认为10
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
        @param {kwargs} - 自定义扩展参数
            match_service_uri_func {function} - 获取请求匹配的service_uri的函数, 格式如下:
                func(request: dict) -> str
                其中request为获取到的请求信息字典, 返回所匹配的service_uri字符串
        """
        super().__init__(
            app_name, server_config=server_config, support_auths=support_auths,
            before_server_start=before_server_start,
            after_server_start=after_server_start, before_server_stop=before_server_stop,
            after_server_stop=after_server_stop, logger=logger, log_level=log_level,
            load_i18n_para=load_i18n_para, **kwargs
        )
        self._match_service_uri_func = kwargs.get('match_service_uri_func', None)

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
        _result = CResult(code='00000')  # 成功
        _result.server_info = NullObj()
        with ExceptionTool.ignored_cresult(_result):
            # 注: 重载该函数, 可在该部分实现自定义的服务初始化或启动逻辑
            # 启动服务，但不接受连接
            self._logger.log(
                self._log_level,
                '[SER-STARTING][NAME:%s]%s:\n%s' % (
                    self._app_name, _('net start parameter'), self._formated_server_config()
                )
            )
            _result = self._start_server_without_accept()
            _result.server_info = _result.server_info

        # 返回处理结果
        return _result

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
        _result = CResult(code='00000')  # 成功
        _result.is_finished = False
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER][NAME:%s]%s: ' % (
                self._app_name, _('server run error')),
            force_log_level=logging.ERROR
        ):
            # 注: 重载该函数, 可在该部分实现自定义的获取请求及处理逻辑
            # 监听下一个连接请求
            _accept_result = await AsyncTools.async_run_coroutine(self._accept_one(server_info))

            if _accept_result.is_success():
                # 获取到一个连接，获取请求信息及处理
                await AsyncTools.async_run_coroutine(
                    self._get_request_and_deal(_accept_result.net_info)
                )
            elif _accept_result.code != '20407':
                # 不是超时的其他获取错误，打印信息
                self._logger.log(
                    logging.ERROR,
                    "[SER][NAME:%s][EX:%s]%s: %s\n%s" % (
                        self._app_name, str(type(_accept_result.error)),
                        _('accept net connection error'), _accept_result.msg,
                        _accept_result.trace_str
                    )
                )
            else:
                # 监听超时, 睡眠一小段时间, 释放cpu
                await asyncio.sleep(0.01)

        # 返回处理结果
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
            # 注: 重载该函数, 可在该部分实现自定义的服务关闭前处理
            # 等待所有连接处理完成
            if len(self._dynamic_var['connect_thread']['list']) > 0:
                _result.is_finished = False

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
            # 注: 重载该函数, 可在该部分实现自定义的服务关闭处理
            await AsyncTools.async_run_coroutine(self._stop_server(server_info))

    def _std_init_config(self):
        """
        标准化服务初始配置
        """
        # 实现类可以通过该函数设置或修改内部参数
        if self._server_config.get('ip', None) is None:
            self._server_config['ip'] = ''
        if self._server_config.get('port', None) is None:
            self._server_config['port'] = 8080

        _max_connect = self._server_config.get('max_connect', None)
        if _max_connect is None or _max_connect <= 0:
            _max_connect = 20

    #############################
    # 内部函数
    #############################

    def _formated_server_config(self) -> str:
        """
        获取字符串格式化后的服务配置参数

        @returns {str} - 要输出的格式化后字符串
        """
        return json.dumps(self._server_config, ensure_ascii=False, indent=2)

    def _start_server_without_accept(self) -> CResult:
        """
        启动服务但不接受请求服务
        注: 该方法只做到启动端口层面, 轮询监听不在该方法中实现, 注意该该函数必须捕获并处理异常

        @returns {CResult} - 启动结果:
            result.code: '00000'-成功, 其他值为失败
            result.server_info: 启动后的服务端网络连接信息对象, 该对象将传给后续的监听线程(self._accept_one)
                server_info = NullObj()
                server_info.csocket - socket对象
                server_info.laddr 本地地址, 地址对象, ("IP地址",打开端口)
                server_info.raddr 远端地址, 地址对象, ("IP地址",打开端口)
                server_info.send_timeout 发送超时时间, 单位为毫秒
                server_info.recv_timeout 收取超时时间, 单位为毫秒
        """
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger,
            self_log_msg='[SER-LIS-STARTING][NAME:%s]%s - %s error: ' % (
                self._app_name, _('net server starting'), _('listen without accept')),
            force_log_level=logging.ERROR
        ):
            # 生成请求执行线程任务变量参数
            self._dynamic_var['connect_thread'] = {
                'id': 1,  # 服务端的链接线程ID序列
                'list': {},  # 服务端正在运行的连接线程列表
                'list_lock': threading.RLock()  # 连接线程列表变更的同步锁
            }

            # 绑定监听端口, 同时返回服务信息
            _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _server_socket.setblocking(False)   # 将socket设置为非阻塞. 在创建socket对象后就进行该操作.
            _server_socket.bind((self._server_config['ip'], self._server_config['port']))
            _server_socket.listen(self._server_config.get('max_connect', 20))

            _result.server_info = NullObj()
            _result.server_info.laddr = _server_socket.getsockname()
            _result.server_info.raddr = ('', 0)
            _result.server_info.csocket = _server_socket
            _result.server_info.send_timeout = self._server_config.get('send_timeout', 10.0)
            _result.server_info.recv_timeout = self._server_config.get('recv_timeout', 10.9)

        return _result

    async def _accept_one(self, server_info: NullObj) -> CResult:
        """
        监听接受一个请求并返回
        注: 提供监听并获取到请求连接返回的方法, 注意该该函数必须捕获并处理异常

        @param {NullObj} server_info - 服务端连接信息对象, self._start_server_without_accept 中获取到的结果

        @returns {CResult} - 获取网络连接结果:
            result.code: '00000'-成功, '20407'-获取客户端连接请求超时
            result.net_info: 客户端连接信息对象, 该对象将传给后续单个连接处理的线程
        """
        # 子类必须定义该功能
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result, logger=self._logger, expect=(BlockingIOError), expect_no_log=True,  # 超时不记录日志
            error_map={BlockingIOError: ('20407', None)},
            self_log_msg='[SER-LIS][NAME:%s]%s error: ' % (
                self._app_name, _('accept client connect')),
            force_log_level=None
        ):
            _csocket, _addr = server_info.csocket.accept()  # 接收客户端连接，返回客户端和地址
            _csocket.setblocking(False)   # 将socket设置为非阻塞. 在创建socket对象后就进行该操作.
            _result.net_info = NullObj()
            _result.net_info.csocket = _csocket
            _result.net_info.raddr = _addr
            _result.net_info.laddr = _csocket.getsockname()
            _result.net_info.send_timeout = self._server_config.get('send_timeout', 10.0)
            _result.net_info.recv_timeout = self._server_config.get('recv_timeout', 10.0)

            self._logger.log(
                self._log_level,
                '[SER-LIS][NAME:%s]%s: %s - %s' % (
                    self._app_name, _('accept one client connection'), str(_addr), str(_csocket)
                )
            )

        return _result

    async def _get_request_and_deal(self, net_info):
        """
        获取请求信息并进行处理
        注: 支持同步和异步函数, 可以启动一个新线程进行处理, 注意函数需捕获并处理异常

        @param {NullObj} net_info - 连接信息对象, self._accept_one 中获取到的结果
        """
        # 子类必须定义该功能
        with ExceptionTool.ignored_all(
            logger=self._logger,
            self_log_msg='[SER-DEAL][NAME:%s]%s error: ' % (
                self._app_name, _('net server connect deal threading error')
            )
        ):
            # 放入实际的获取请求数据和处理的逻辑代码
            # 创建线程
            self._dynamic_var['connect_thread']['list_lock'].acquire()
            try:
                self._dynamic_var['connect_thread']['id'] += 1
                _thread_id = self._dynamic_var['connect_thread']['id']
                _new_thread = threading.Thread(
                    target=self._connect_deal_thread_func,
                    args=(_thread_id, net_info),
                    name='Thread-ConnectDeal' + str(_thread_id)
                )
                # 将线程添加到队列
                self._dynamic_var['connect_thread']['list'][_thread_id] = _new_thread
            finally:
                self._dynamic_var['connect_thread']['list_lock'].release()

            _new_thread.setDaemon(True)
            _new_thread.start()

    async def _stop_server(self, server_info: NullObj):
        """
        关闭服务吹
        注: 支持同步和异步函数, 提供关闭服务的方法

        @param {NullObj} server_info - 服务端连接信息对象, self._start_server_without_accept 中获取到的结果
        """
        # 放入实际的关闭服务逻辑
        # 清除连接线程
        self._dynamic_var['connect_thread']['list_lock'].acquire()
        try:
            self._dynamic_var['connect_thread']['list'].clear()
        finally:
            self._dynamic_var['connect_thread']['list_lock'].release()

        # 关闭网络连接
        server_info.csocket.close()

    #############################
    # 处理线程相关函数
    #############################

    def _connect_deal_thread_func(self, thread_id: int, net_info):
        """
        连接处理线程

        @param {int} thread_id - 线程id
        @param {NullObj} net_info - 连接信息对象, self._accept_one 中获取到的结果
        """
        try:
            with ExceptionTool.ignored_all(
                logger=self._logger,
                self_log_msg='[SER-DEAL][NAME:%s]%s: ' % (self._app_name, _(
                    'net server connect deal threading error')),
                force_log_level=logging.ERROR
            ):
                # 注: 重载该函数, 可在该部分实现自定义请求处理逻辑
                # 获取请求标准信息
                _request_dict = AsyncTools.sync_run_coroutine(
                    self._get_std_request(net_info)
                )
                if _request_dict is None:
                    return

                # 获取匹配的处理函数
                _match_service_uri = ''
                if self._match_service_uri_func is not None:
                    _match_service_uri = AsyncTools.sync_run_coroutine(
                        self._match_service_uri_func(_request_dict)
                    )

                _deal_fun_para = self._service_router.get(_match_service_uri, None)
                if _deal_fun_para is None:
                    _deal_fun_para = self._service_router.get('', None)

                if _deal_fun_para is None:
                    raise ModuleNotFoundError(_('service "[$1]" not found', _match_service_uri))

                # 执行处理
                _resp_dict = AsyncTools.sync_run_coroutine(
                    _deal_fun_para['handler'](net_info, _match_service_uri, _request_dict)
                )

                # 处理返回
                if _resp_dict is not None:
                    _data = json.dumps(_resp_dict, ensure_ascii=False).encode(encoding='utf-8')
                    _data = NetTool.int_to_bytes(len(_data), signed=False) + _data
                    _send_result = AsyncTools.sync_run_coroutine(
                        SocketTool.send_data(net_info, _data)
                    )
                    if not _send_result.is_success():
                        # 记录失败日志
                        self._logger.error('%s: %s' % (_('send data to remote error'), str(_send_result)))
        finally:
            # 关闭网络连接
            AsyncTools.sync_run_coroutine(
                SocketTool.close(net_info)
            )

            # 结束处理, 删除线程清单
            self._dynamic_var['connect_thread']['list_lock'].acquire()
            try:
                self._dynamic_var['connect_thread']['list'].pop(thread_id, None)
            finally:
                self._dynamic_var['connect_thread']['list_lock'].release()

    async def _get_std_request(self, net_info) -> dict:
        """
        获取标准请求对象

        @param {NullObj} net_info - 需要关闭的网络连接信息对象
            net_info.csocket - socket对象
            net_info.laddr 本地地址,地址对象("IP地址",打开端口)
            net_info.raddr 远端地址,地址对象("IP地址",打开端口)
            net_info.send_timeout 发送超时时间, 单位为秒
            net_info.recv_timeout 收取超时时间, 单位为秒

        @returns {dict} - 返回请求处理后的字典
        """
        _request_dict = None
        # 获取报文信息长度
        _result = await AsyncTools.async_run_coroutine(
            SocketTool.recv_data(net_info, {'recv_len': 4})
        )
        if _result.is_success():
            _msg_len = NetTool.bytes_to_int(_result.data, signed=False)

            # 获取报文信息
            _result = await AsyncTools.async_run_coroutine(
                SocketTool.recv_data(net_info, {'recv_len': _msg_len})
            )
            if _result.is_success():
                _request_dict = json.loads(_result.data)

        if _request_dict is not None:
            # 正常获取到信息
            return _request_dict
        else:
            # 获取失败, 打印错误日志
            self._logger.error('%s: %s' % (_('recv data from remote error'), str(_result)))
            return None


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
