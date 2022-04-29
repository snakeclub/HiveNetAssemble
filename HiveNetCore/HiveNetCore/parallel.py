#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
并发处理模块, 多线程、多进程支持
注意: 本模块要使用内置的affinity, 在windows平台需要同步安装pywin32；
@module parallel
@file parallel.py

"""

import os
import sys
import threading
from multiprocessing import Process, Manager, Lock
import datetime
import traceback
import inspect
import ctypes
import uuid
import copy
import re
import logging
import psutil
import asyncio
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
if sys.platform == 'win32':
    import win32con
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
import HiveNetCore.utils.affinity as affinity
from HiveNetCore.generic import CResult
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.import_tool import ImportTool
from HiveNetCore.utils.exception_tool import ExceptionTool


__MOUDLE__ = 'parallel'  # 模块名
__DESCRIPT__ = u'并发处理模块, 多线程、多进程支持'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.10.02'  # 发布日期


class AlreadyRunning(Exception):
    """
    已运行异常

    """
    pass


class NotRunning(Exception):
    """
    未运行异常

    """
    pass


class CallOverTime(Exception):
    """
    当执行超时时, 抛出该异常

    """
    pass


class CoroutineSingleThread(object):
    """
    单线程并发协程处理类
    注: 在子线程中通过协程处理异步函数
    """

    def __init__(self, deal_fun=None, event_loop=None) -> None:
        """
        单线程并发协程处理类

        @param {function} deal_fun=None - 默认的异步处理函数
        @param {EventLoop} event_loop=None - 时间循环对象
            注: 可以通过asyncio.new_event_loop()获取, 如果不送入将自动获取
        """
        # 默认处理函数
        self.deal_fun = deal_fun

        # 获取事件循环对象
        self.event_loop = event_loop
        if self.event_loop is None:
            try:
                self.event_loop = asyncio.get_running_loop()
            except:
                try:
                    self.event_loop = asyncio.get_event_loop()
                except:
                    self.event_loop = asyncio.new_event_loop()

        # 生成线程对象并进行启动
        self.thread = threading.Thread(target=self._start_loop, args=(self.event_loop,))
        self.thread.setDaemon(True)
        self.thread.start()

    #############################
    # 公共函数
    #############################
    def run_coroutine(self, coroutine):
        """
        运行协程对象

        @param {Coroutine} coroutine - 要运行的协程对象
        """
        asyncio.run_coroutine_threadsafe(coroutine, self.event_loop)

    def run_deal_fun(self, *args, **kwargs):
        """
        运行默认异步处理函数
        """
        _coroutine = self.deal_fun(*args, **kwargs)
        self.run_coroutine(_coroutine)

    def run_async_fun(self, async_fun, *args, **kwargs):
        """
        执行特定异步处理函数

        @param {function} async_fun - 异步函数对象
        """
        _coroutine = async_fun(*args, **kwargs)
        self.run_coroutine(_coroutine)

    #############################
    # 内部函数
    #############################

    def _start_loop(event_loop):
        """
        专门创建事件运行的线程函数, 在线程里进行启动

        @param {EventLoop} event_loop - 时间循环对象
        """
        asyncio.set_event_loop(event_loop)
        event_loop.run_forever()


class ParallelLockFw(ABC):
    """
    并发锁框架类, 定义各类并发技术的通用函数架构

    @param {**kwargs} kwargs - 初始化参数, 具体参数定义参考具体实现类

    """

    #############################
    # 内部变量
    #############################
    _init_kwargs = None  # 锁初始化参数

    #############################
    # 公开函数
    #############################

    def __init__(self, **kwargs):
        """
        构造函数, 初始化锁对象

        @param {**kwargs} kwargs - 初始化参数, 具体参数定义参考具体实现类

        """
        self._init_kwargs = kwargs
        self._init(**kwargs)

    def acquire(self, **kwargs):
        """
        获取并发锁

        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        """
        self._acquire(**kwargs)

    def release(self, **kwargs):
        """
        释放并发锁

        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        """
        self._release(**kwargs)

    #############################
    # 内部函数, 抽象类
    #############################
    def _init(self, **kwargs):
        """
        初始化并发锁

        @param {**kwargs} kwargs - 初始化参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError

    def _acquire(self, **kwargs):
        """
        获取并发锁

        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError

    def _release(self, **kwargs):
        """
        释放并发锁

        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError


class ParallelShareDictFw(ABC):
    """
    并发任务共享字典框架, 用于支持并发任务之间的基础数据共享(查询和修改)
    整体思路是重载取值和赋值运算符, 取值前先获取最新数据, 赋值后提交更新

    @param {string} tag - 唯一标识

    """

    def __init__(self, tag):
        """
        初始化函数, 增加标识的登记

        @param {string} tag - 唯一标识

        """
        self._tag = tag
        self._dict = self._init(tag)

    def __getitem__(self, key):
        """
        重载要获取的数据加载方法

        @param {object} key - 索引

        @returns {object} - 返回更新后的值

        """
        return self._refresh(key)

    def __setitem__(self, key, value):
        """
        重载设置值的方法

        @param {object} key - 索引
        @param {object} value - 要设置的值

        """
        return self._update(key, value)

    #############################
    # 需实现类实现的接口定义
    #############################
    @abstractmethod
    def _init(self, tag):
        """
        初始化对象(比如从服务端下载后进行初始化)

        @param {string} tag - 唯一标识

        @returns {object} - 需要返回初始化后的本地对象, 存放在self._dict中

        """
        raise NotImplementedError

    @abstractmethod
    def _refresh(self, key):
        """
        刷新自身对象指定key的值(比如从服务端下载)

        @param {object} key - 要刷新的key

        @returns {object} - 返回具体的值

        """
        raise NotImplementedError

    @abstractmethod
    def _update(self, key, value):
        """
        更新自身对象指定key的值(比如上传到服务端)

        @param {object} key - 索引
        @param {object} value - 要设置的值

        """
        raise NotImplementedError


class ParallelFw(ABC):
    """
    并发处理框架类, 定义并发处理通用函数架构

    @param {fuction} deal_fun - 并发处理主函数, 按顺序入参, 可以有返回值
    @param {tuple} run_args=None - 并发处理主函数的入参列表
    @param {dict} run_kwargs=None - 并发处理主函数的动态入参列表
    @param {bool} auto_start=False - 是否创建时自动发起并发任务
    @param {string} pid='' - 并发对象的id
    @param {string} pname='' - 并发对象的标识名
    @param {ParallelLockFw} lock=None - 并发锁对象, 控制多个并发对象根据该锁控制单一处理
    @param {fuction} callback_fun=None - 回调函数, 在执行完函数后执行, 定义如下
        fun(id, name, call_result, deal_fun_ret)
            id - 并发对象的id
            name - 并发对象的标识名
            call_result - 线程执行的结果, CResult对象, 如果执行无异常返回'00000'；
                如果发生异常, 返回'21399', 并登记异常信息
            deal_fun_ret - deal_fun函数执行的返回值
    @param {bool} set_daemon=False - 是否设置守护, 如果设置守护, 则在主进程中使用join方法等待所有并发完成,
        否则主进程结束后并发执行的结果不可预知；如果不设置守护, 主进程结束后并发任务仍会执行
    @param {Logger} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
        1、标准logging的logger对象
        2、自定义的日志类对象, 但应实现info、warning、error等标准方法
    @param {bool} is_use_global_logger=True - 当logger=None时, 是否使用全局logger对象
        注: 通过RunTool.set_global_logger进行设置
    @param {int} log_level=logging.INFO - 打印日志的级别
    @param {bool} use_distributed_logger=False - 是否使用分布式logger, 如果是, 则每个分布任务自行创建独立logger记录日志
        注: 对于多进程及分布式并发任务, 应采取该日志模式
    @param {string} distributed_logger_module_name='' - 分布式日志类模块名
    @param {string} distributed_logger_class_name='' - 分布式日志类类名
    @param {tuple} distributed_logger_args=None - 分布式日志类创建参数
    @param {dict} distributed_logger_kwargs=None - 分布式日志类创建参数
    @param {dict} distributed_logger_replace_para=dict() - 分布式日志动态参数替换, 在每创建一个并发任务通过该参数修改日志参数
        key - 如果是int类型, 代表替换distributed_logger_args的第几个参数；如果是string, 代表替换distributed_logger_kwargs的指定参数
        value - 替换参数字典, key为要替换正则表达式字符, value为要替换的动态值
            要替换的动态值, 可选值有以下几种:
                'pid' - 并发任务id
                'pname' - 并发任务名
                'pocess_id' - 进程ID
                'thread_id' - 线程ID
    @param {bool} is_logger_to_deal_fun=False - 是否传递并发任务logger到deal_fun中
        注意: 传递通过kwargs, 参数名为logger

    @param {**kwargs} kwargs - 初始化参数, 具体参数定义参考具体实现类

    """
    #############################
    # 内部变量
    #############################
    _deal_fun = None
    _run_args = None
    _run_kwargs = None
    _pid = ''
    _pname = ''
    _lock = None
    _callback_fun = None
    _set_daemon = False
    _logger = None
    _log_level = logging.INFO
    _init_kwargs = None

    _is_running = False  # 任务运行状态
    _stat_lock = None

    #############################
    # 公开函数
    #############################
    @property
    def is_running(self):
        """
        检查任务是否正在执行

        @property {bool}

        """
        return self._is_running

    def __init__(
        self, deal_fun, run_args=None, run_kwargs=None, auto_start=False,
        pid='', pname='', lock=None, callback_fun=None, set_daemon=False,
        logger=None, is_use_global_logger=True, log_level=logging.INFO,
        use_distributed_logger=False, distributed_logger_module_name='',
        distributed_logger_class_name='',
        distributed_logger_args=None, distributed_logger_kwargs=None,
        distributed_logger_replace_para=None,
        is_logger_to_deal_fun=False,
        **kwargs
    ):
        """
        并发对象初始函数

        @param {fuction} deal_fun - 并发处理主函数, 按顺序入参, 可以有返回值
        @param {tuple} run_args=None - 并发处理主函数的入参列表
        @param {dict} run_kwargs=None - 并发处理主函数的动态入参列表
        @param {bool} auto_start=False - 是否创建时自动发起并发任务
        @param {string} pid='' - 并发对象的id
        @param {string} pname='' - 并发对象的标识名
        @param {ParallelLockFw} lock=None - 并发锁对象, 控制多个并发对象根据该锁控制单一处理
        @param {fuction} callback_fun=None - 回调函数, 在执行完函数后执行, 定义如下
            fun(id, name, call_result, deal_fun_ret)
                id - 并发对象的id
                name - 并发对象的标识名
                call_result - 线程执行的结果, CResult对象, 如果执行无异常返回'00000'；
                    如果发生异常, 返回'21399', 并登记异常信息
                deal_fun_ret - deal_fun函数执行的返回值
        @param {bool} set_daemon=False - 是否设置守护, 如果设置守护, 则在主进程中使用join方法等待所有并发完成,
            否则主进程结束后并发执行的结果不可预知；如果不设置守护, 主进程结束后并发任务仍会执行
        @param {Logger} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现info、warning、error等标准方法
        @param {bool} is_use_global_logger=True - 当logger=None时, 是否使用全局logger对象
            注: 通过RunTool.set_global_logger进行设置
        @param {int} log_level=logging.INFO - 打印日志的级别
        @param {bool} use_distributed_logger=False - 是否使用分布式logger, 如果是, 则每个分布任务自行创建独立logger记录日志
            注: 对于多进程及分布式并发任务, 应采取该日志模式
        @param {string} distributed_logger_module_name='' - 分布式日志类模块名
        @param {string} distributed_logger_class_name='' - 分布式日志类类名
        @param {tuple} distributed_logger_args=None - 分布式日志类创建参数
        @param {dict} distributed_logger_kwargs=None - 分布式日志类创建参数
        @param {dict} distributed_logger_replace_para=dict() - 分布式日志动态参数替换, 在每创建一个并发任务通过该参数修改日志参数
            key - 如果是int类型, 代表替换distributed_logger_args的第几个参数；如果是string, 代表替换distributed_logger_kwargs的指定参数
            value - 替换参数字典, key为要替换正则表达式字符, value为要替换的动态值
                要替换的动态值, 可选值有以下几种:
                    'pid' - 并发任务id
                    'pname' - 并发任务名
                    'pocess_id' - 进程ID
                    'thread_id' - 线程ID
        @param {bool} is_logger_to_deal_fun=False - 是否传递并发任务的logger到deal_fun中
            注意: 传递通过kwargs, 参数名为logger

        @param {**kwargs} kwargs - 初始化参数, 具体参数定义参考具体实现类

        """
        self._init_kwargs = {}
        self._deal_fun = deal_fun
        self._run_args = run_args
        if run_args is None:
            self._run_args = ()
        self._run_kwargs = run_kwargs
        if run_kwargs is None:
            self._run_kwargs = {}
        self._pid = pid
        self._pname = pname
        self._lock = lock
        self._callback_fun = callback_fun
        self._set_daemon = set_daemon
        self._logger = logger
        if self._logger is None and is_use_global_logger:
            # 使用全局logger
            self._logger = RunTool.get_global_logger()
        self._log_level = log_level
        self._use_distributed_logger = use_distributed_logger
        self._distributed_logger_module_name = distributed_logger_module_name
        self._distributed_logger_class_name = distributed_logger_class_name
        self._distributed_logger_args = distributed_logger_args
        if distributed_logger_args is None:
            self._distributed_logger_args = ()
        self._distributed_logger_kwargs = distributed_logger_kwargs
        if distributed_logger_kwargs is None:
            self._distributed_logger_kwargs = {}
        self._distributed_logger_replace_para = distributed_logger_replace_para
        if self._distributed_logger_replace_para is None:
            self._distributed_logger_replace_para = {}
        self._is_logger_to_deal_fun = is_logger_to_deal_fun
        self._init_kwargs = kwargs
        self._unique_id = str(uuid.uuid1())
        self._stat_lock = self._create_stat_lock()
        self._is_running = self._create_is_running_obj()
        self._set_is_running(self._is_running, False)
        # 初始化并发对象
        self._init()
        # 是否自动启动
        if auto_start:
            self.start()

    def start(self, run_args=None, run_kwargs=None, **kwargs):
        """
        执行并发任务

        @param {tuple} run_args=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {dict} run_kwargs=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        @throws {AlreadyRunning} - 当任务已经在执行状态, 将抛出该异常

        """
        self._stat_lock.acquire()
        try:
            if self._get_is_running():
                # 正在运行, 抛出异常
                raise AlreadyRunning

            try:
                # 启动任务执行
                self._start_time = datetime.datetime.now()
                self._set_is_running(self._is_running, True)
                self._start(run_args=run_args, run_kwargs=run_kwargs, **kwargs)
            except Exception as e:
                self._set_is_running(self._is_running, False)
                # 写异常日志
                if self._logger is not None:
                    self._logger.log(
                        logging.ERROR,
                        '[USE:%ss][EX:%s]start parallel [%s:%s] error: %s' % (
                            str((datetime.datetime.now() - self._start_time).total_seconds()),
                            str(type(e)),
                            self._pid,
                            self._pname,
                            traceback.format_exc()
                        )
                    )
        finally:
            self._stat_lock.release()

    def force_stop(self, **kwargs):
        """
        强制中止并行任务

        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        """
        self._stat_lock.acquire()
        try:
            if not self._get_is_running():
                # 不在执行, 直接返回
                return

            # 执行强制执行方法
            self._force_stop(**kwargs)

            # 执行成功, 更新状态
            self._set_is_running(self._is_running, False)

            # 写日志
            if self._logger is not None:
                self._logger.log(
                    self._log_level,
                    '[USE:%ss]force stop parallel [%s:%s]' % (
                        str((datetime.datetime.now() - self._start_time).total_seconds()),
                        self._pid,
                        self._pname
                    )
                )
        except Exception as e:
            # 出现异常, 写日志, 然后继续抛出异常
            if self._logger is not None:
                self._logger.log(
                    logging.ERROR,
                    '[EX:%s]force stop parallel [%s:%s] error: %s' % (
                        str(type(e)),
                        self._pid,
                        self._pname,
                        traceback.format_exc()
                    )
                )
            raise e
        finally:
            self._stat_lock.release()

        # 没有抛出异常, 说明执行成功, 执行callback函数
        _call_result = CResult(code='21004')  # 强行中止
        _deal_fun_ret = None
        with ExceptionTool.ignored_all():
            self._self_callback(_call_result, _deal_fun_ret)

    def join(self, overtime=0, **kwargs):
        """
        阻塞等待并发任务完成

        @param {number}} overtime - 超时时间, 单位为秒, 如果超时则抛出异常
        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        @throws {CallOverTime} - 当设置了超时时间且执行超时时, 抛出该异常

        """
        while self._set_daemon:
            # 只有设置了守护的情况才处理
            _start = datetime.datetime.now()

            self._stat_lock.acquire()
            try:
                if not self._get_is_running():
                    # 已执行完成
                    return
            finally:
                self._stat_lock.release()

            # 判断是否超时
            if overtime > 0 and (datetime.datetime.now() - _start).total_seconds() > overtime:
                raise CallOverTime
            RunTool.sleep(0.001)  # 准备下一次循环

    #############################
    # 内部函数
    #############################
    def _get_thread_fun_kwargs(self):
        """
        获取默认线程执行的输入参数

        @returns {dict} - 按入参组织好的字典

        """
        _dict = {
            'pid': self._pid,
            'pname': self._pname,
            'start_time': self._start_time,
            'stat_lock': self._stat_lock,
            'is_running_obj': self._is_running,
            'deal_fun': self._deal_fun,
            'run_args': self._run_args,
            'run_kwargs': self._run_kwargs,
            'lock': self._lock,
            'callback_fun': self._callback_fun,
            'logger': self._logger,
            'log_level': self._log_level,
            'use_distributed_logger': self._use_distributed_logger,
            'distributed_logger_module_name': self._distributed_logger_module_name,
            'distributed_logger_class_name': self._distributed_logger_class_name,
            'distributed_logger_args': self._distributed_logger_args,
            'distributed_logger_kwargs': self._distributed_logger_kwargs,
            'distributed_logger_replace_para': self._distributed_logger_replace_para,
            'is_logger_to_deal_fun': self._is_logger_to_deal_fun
        }
        return _dict

    @classmethod
    def _replace_distributed_logger_para(cls, args, kwargs, replace_para, value_para):
        """
        替换logger初始化参数

        @param {tuple} args - 固定参数
        @param {dict} kwargs - 动态参数
        @param {dict} replace_para - 替换参数
        @param {dict} value_para - 取值参数

        """
        for _key in replace_para.keys():
            if isinstance(_key, str):
                # 修改kwargs
                kwargs[_key] = cls.replace_distributed_logger_para_str(
                    kwargs[_key], replace_para[_key], value_para)
            else:
                # 修改args
                args[_key] = cls.replace_distributed_logger_para_str(
                    args[_key], replace_para[_key], value_para)

    @classmethod
    def replace_distributed_logger_para_str(cls, value, replace_para_dict, value_para):
        """
        单个字符串执行替换处理

        @param {string} value - 字符串
        @param {dict} replace_para_dict - 替换参数字典
        @param {dict} value_para - 取值参数

        @returns {string} - 替换后的值
        """
        _ret = value
        for _key in replace_para_dict.keys():
            # 先获取实际要替换的值
            _replace = ValueTool.get_dict_value(
                replace_para_dict[_key], value_para, default_value='')
            _pattern = None
            if _key is not None:
                _pattern = re.compile(_key)
                re.sub(_pattern, _replace, _ret)
            else:
                # 整个替换
                _ret = _replace
        return _ret

    @classmethod
    def _base_callback(cls, call_result, deal_fun_ret, **kwargs):
        """
        内部并发任务回调处理函数

        @param {CResult} call_result - 线程执行的结果,如果执行无异常返回'00000'；
            如果发生异常, 返回'21399', 并登记异常信息
            如果被强制中止, 返回'21004', 并登记异常信息
        @param {object} deal_fun_ret - deal_fun函数执行的返回值
        @param {dict} kwargs={} - 回调函数所需用到的所有参数, 包括:
            logger {logging.Logger} -  日志对象
            callback_fun {fuction}  - 真正的回调函数
            pid {string} - 并发任务标识
            pname {string} - 并发任务标识名
            start_time {datetime} - 并发任务启动时间
            log_level {int} - 正常日志的输出级别

        """
        # 执行回调函数
        if kwargs['callback_fun'] is not None:
            try:
                kwargs['callback_fun'](kwargs['pid'], kwargs['pname'], call_result, deal_fun_ret)
            except Exception as e:
                # 写异常日志
                if kwargs['logger'] is not None:
                    kwargs['logger'].log(
                        logging.ERROR,
                        '[EX:%s]execute parallel [%s:%s]  callback error: %s' % (
                            str(type(e)),
                            kwargs['pid'],
                            kwargs['pname'],
                            traceback.format_exc()
                        )
                    )

        # 写执行日志
        _use = str((datetime.datetime.now() - kwargs['start_time']).total_seconds())
        if kwargs['logger'] is not None:
            if call_result.code[0] == '0':
                kwargs['logger'].log(
                    kwargs['log_level'],
                    '[USE:%ss]finish parallel [%s:%s]' % (
                        _use,
                        kwargs['pid'],
                        kwargs['pname']
                    )
                )
            else:
                # 执行异常
                kwargs['logger'].log(
                    logging.ERROR,
                    '[USE:%ss][EX:%s]execute parallel [%s:%s] error: %s' % (
                        _use,
                        str(type(call_result.error)),
                        kwargs['pid'],
                        kwargs['pname'],
                        call_result.trace_str
                    )
                )

    @classmethod
    def _base_parallel_thread_fun(cls, **kwargs):
        """
        实际执行线程处理的内部函数

        @param {dict} kwargs={} - 执行函数所需用到的所有参数, 包括:
            pid {string} - 并发任务标识
            pname {string} - 并发任务标识名
            start_time {datetime} - 并发任务启动时间
            stat_lock {ParallelLockFw} - 更新任务完成状态的锁
            is_running_obj {object} - 可直接更新的任务完成状态对象
            deal_fun {fuction} - 实际执行函数
            run_args {tuple} - 执行函数固定参数
            run_kwargs {dict} - 执行函数可变参数
            lock {ParallelLockFw} - 并行任务处理锁
            callback_fun {fuction}  - 真正的回调函数
            logger {logging.Logger} -  日志对象
            use_distributed_logger
            distributed_logger_module_name
            distributed_logger_class_name
            distributed_logger_args
            distributed_logger_kwargs
            distributed_logger_replace_para
            is_logger_to_deal_fun

        """
        # 日志函数
        if kwargs['logger'] is None and kwargs['use_distributed_logger']:
            # 修改参数
            # TODO(黎慧剑): 获取线程id的方法暂不可用, 需继续研究补充
            _value_para = {
                'pid': kwargs['pid'],
                'pname': kwargs['pname'],
                'pocess_id': str(os.getpid()),
                'thread_id': '0'  # str(threading.current_thread().get_ident())
            }

            _log_args = copy.deepcopy(kwargs['distributed_logger_args'])
            _log_kwargs = copy.deepcopy(kwargs['distributed_logger_kwargs'])
            cls._replace_distributed_logger_para(
                _log_args, _log_kwargs,
                kwargs['distributed_logger_replace_para'],
                _value_para
            )

            kwargs['logger'] = cls._create_distributed_log_fun(
                kwargs['use_distributed_logger'], kwargs['distributed_logger_module_name'],
                kwargs['distributed_logger_class_name'], _log_args,
                _log_kwargs
            )

        # 传递日志函数到处理函数
        if kwargs['is_logger_to_deal_fun']:
            kwargs['run_kwargs']['logger'] = kwargs['logger']

        # 写启动日志
        if kwargs['logger'] is not None:
            kwargs['logger'].log(
                kwargs['log_level'],
                'start parallel [%s:%s]' % (
                    kwargs['pid'],
                    kwargs['pname']
                )
            )

        _call_result = CResult(code='00000')  # 成功
        _deal_fun_ret = None

        # 执行处理函数
        if kwargs['lock'] is not None:
            kwargs['lock'].acquire()  # 获取锁

        with ExceptionTool.ignored_cresult(_call_result):
            _deal_fun_ret = kwargs['deal_fun'](*kwargs['run_args'], **kwargs['run_kwargs'])

        if kwargs['lock'] is not None:
            kwargs['lock'].release()  # 释放锁

        # 执行回调函数
        with ExceptionTool.ignored_all():
            cls._base_callback(_call_result, _deal_fun_ret, **kwargs)

        # 修改执行状态
        kwargs['stat_lock'].acquire()
        cls._set_is_running(kwargs['is_running_obj'], False)
        kwargs['stat_lock'].release()

    @classmethod
    def _create_distributed_log_fun(
        cls, use_distributed_logger, distributed_logger_module_name,
        distributed_logger_class_name, distributed_logger_args, distributed_logger_kwargs
    ):
        """
        创建分布式日志函数数组

        """
        _logger = None
        if (
            use_distributed_logger and
            distributed_logger_module_name != '' and
            distributed_logger_class_name != ''
        ):
            with ExceptionTool.ignored_all():
                _class_obj = getattr(
                    ImportTool.import_module(distributed_logger_module_name),
                    distributed_logger_class_name
                )
                _logger = _class_obj(*distributed_logger_args, **distributed_logger_kwargs)
        return _logger

    #############################
    # 内部函数 - 需继承实现
    #############################
    def _init(self):
        """
        初始化并发对象

        """
        return

    @abstractmethod
    def _start(self, run_args=None, run_kwargs=None, **kwargs):
        """
        执行并发任务
        对实现类的要求如下:
        1、在并发任务启动中, 如果出现异常_start可捕获到的, 可直接抛出异常
        2、并发任务执行中出现的异常(_start捕获不到的), 应由实现类进行捕获处理, 不应抛出
        3、并发任务在执行deal_fun前应根据锁要求先获取锁, 执行完deal_fun后释放锁
        4、并发任务执行完成后(包括出现异常中止), 需调用self._self_callback通知框架进行后续处理

        @param {tuple} run_args=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {dict} run_kwargs=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        """
        raise NotImplementedError

    @abstractmethod
    def _force_stop(self, **kwargs):
        """
        强制中止并行任务

        @param {**kwargs} kwargs - 处理参数, 具体参数定义参考具体实现类

        """
        raise NotImplementedError

    def _create_stat_lock(self):
        """
        创建线程执行状态更新锁

        @returns {ParallelLockFw} - 返回指定的锁

        """
        return ProcessParallelLock()

    def _create_is_running_obj(self):
        """
        创建是否运行状态的共享变量

        """
        return ProcessParallelShareDict(self._unique_id)

    def _get_is_running(self):
        """
        返回是否运行的状态

        """
        return self._is_running['is_running']

    @classmethod
    def _set_is_running(cls, is_running_obj, status):
        """
        设置是否运行标记

        @decorators classmethod - [description]

        @param {bool} is_running_obj - <description>
        @param {[type]} status - <description>

        """
        is_running_obj['is_running'] = status


class ParallelPool(object):
    """
    并发任务池(线程池、进程池)

    @param {fuction} deal_fun - 并发任务处理主函数, 按顺序入参, 可以有返回值
            注: 该函数内部需自行实现获取数据并处理的流程, 但约定如果无处理数据, 函数应返回None(用于并发池判断是否释放任务)
    @param {ParallelFw} parallel_class=None - 并行任务类定义对象, 获取方法如下:
        (1)import对象后, 直接取类名: parallel_class=ThreadParallel
        (2)未import的对象, 使用ImportTool的方式:
            parallel_class=getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ThreadParallel')
        (3)已有动态的对象, 直接取对象的所属类: parallel_class=obj.__class__
    @param {tuple} run_args=None - 并发任务处理主函数的入参列表
    @param {dict} run_kwargs=None - 并发任务处理主函数的动态入参列表
    @param {string} pname='' - 并发任务处理主函数的标识名
    @param {ParallelLockFw} lock=None - 并发锁对象, 控制多个并发对象根据该锁控制单一处理
    @param {fuction} callback_fun=None - 回调函数, 在执行完函数后执行, 定义如下
        fun(id, name, call_result, deal_fun_ret)
            id - 并发对象的id
            name - 并发对象的标识名
            call_result - 线程执行的结果, CResult对象, 如果执行无异常返回'00000'；
                如果发生异常, 返回'21399', 并登记异常信息
            deal_fun_ret - deal_fun函数执行的返回值

    @param {Logger} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
        1、标准logging的logger对象
        2、自定义的日志类对象, 但应实现info、warning、error等标准方法
    @param {bool} is_use_global_logger=True - 当logger=None时, 是否使用全局logger对象
        注: 通过RunTool.set_global_logger进行设置
    @param {int} log_level=logging.INFO - 打印日志的级别
    @param {bool} use_distributed_logger=False - 是否使用分布式logger, 如果是, 则每个分布任务自行创建独立logger记录日志
        注: 对于多进程及分布式并发任务, 应采取该日志模式
    @param {string} distributed_logger_module_name='' - 分布式日志类模块名
    @param {string} distributed_logger_class_name='' - 分布式日志类类名
    @param {tuple} distributed_logger_args=None - 分布式日志类创建参数
    @param {dict} distributed_logger_kwargs=None - 分布式日志类创建参数
    @param {dict} distributed_logger_replace_para=dict() - 分布式日志动态参数替换, 在每创建一个并发任务通过该参数修改日志参数
        key - 如果是int类型, 代表替换distributed_logger_args的第几个参数；如果是string, 代表替换distributed_logger_kwargs的指定参数
        value - 替换参数字典, key为要替换正则表达式字符, value为要替换的动态值
            要替换的动态值, 可选值有以下几种:
                'pid' - 并发任务id
                'pname' - 并发任务名
                'pocess_id' - 进程ID
                'thread_id' - 线程ID
    @param {bool} is_logger_to_deal_fun=False - 是否传递并发任务logger到deal_fun中
        注意: 传递通过kwargs, 参数名为logger
    @param {bool} auto_start=False - 是否自动启动并发池
    @param {bool} auto_stop=False - 是否自动关闭并发池(当任务都已全部完成处理)
    @param {QueueFw} task_queue=None - 并发池需要处理的任务队列
        注: 如果有指定队列, get_task_num_fun参数无效, 则自动根据队列长度检查待处理任务
    @param {function} get_task_num_fun=None - 获取待处理任务数量的函数
        注: 如果task_queue和get_task_num_fun均为None, 则直接创建最大数量的线程数, 且不释放空闲任务
    @param {list} get_task_num_fun_args=None - 获取待处理任务数量的函数, 的入参列表
    @param {int} maxsize=10 - 并发池最大并发对象数
    @param {int} minsize=0 - 并发池最小并发对象数
    @param {number} worker_release_time=10 - 空闲工作并发对象释放时间, 单位为秒, 0代表不控制空闲释放
    @param {number} worker_overtime=0 - 正在执行的任务超时时间(秒), 0代表不控制超时
        注: 对于超时执行任务, 将视为失效任务, 可以选择直接忽略或强制中止
    @param {bool} force_kill_overtime_worker=False - 是否强制中止失效任务
    @param {bool} replace_overtime_worker=False - 是否创建新任务替代超时任务
        注: 仅当force_kill_overtime_worker=False时才会进行替代
    @param {number} daemon_thread_time=0.01 - 守护线程的间隔时间
    @param {ParallelShareDictFw} sharedict_class=None - 进程间共享字典对象的类对象, 获取方法参考parallel_class:
        sharedict_class=ThreadParallelShareDict
    @param {ParallelLockFw} parallel_lock_class=None - 进程间锁对象的类对象, 获取方法参考parallel_class:
        parallel_lock_class=ThreadParallelLock
    @param {**kwargs} kwargs - 并行任务类对应的初始化参数, 具体参数定义参考具体实现类

    """
    #############################
    # 公共函数
    #############################

    def __init__(
        self, deal_fun, parallel_class=None, run_args=None, run_kwargs=None,
        pname='', lock=None, callback_fun=None,
        logger=None, is_use_global_logger=True, log_level=logging.INFO,
        use_distributed_logger=False, distributed_logger_module_name='',
        distributed_logger_class_name='',
        distributed_logger_args=None, distributed_logger_kwargs=None,
        distributed_logger_replace_para=None, is_logger_to_deal_fun=False,
        auto_start=False, auto_stop=False, task_queue=None, get_task_num_fun=None, get_task_num_fun_args=None,
        maxsize=10, minsize=0, worker_release_time=10, worker_overtime=0,
        force_kill_overtime_worker=False, replace_overtime_worker=False, daemon_thread_time=0.01,
        sharedict_class=None, parallel_lock_class=None,
        **kwargs
    ):
        """
        构造函数, 创建任务池

        @param {fuction} deal_fun - 并发任务处理主函数, 按顺序入参, 可以有返回值
            注: 该函数内部需自行实现获取数据并处理的流程, 但约定如果无处理数据, 函数应返回None(用于并发池判断是否释放任务)
        @param {ParallelFw} parallel_class=None - 并行任务类定义对象, 获取方法如下:
            (1)import对象后, 直接取类名: parallel_class=ThreadParallel
            (2)未import的对象, 使用ImportTool的方式:
                parallel_class=getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ThreadParallel')
            (3)已有动态的对象, 直接取对象的所属类: parallel_class=obj.__class__
        @param {tuple} run_args=None - 并发任务处理主函数的入参列表
        @param {dict} run_kwargs=None - 并发任务处理主函数的动态入参列表
        @param {string} pname='' - 并发任务处理主函数的标识名
        @param {ParallelLockFw} lock=None - 并发锁对象, 控制多个并发对象根据该锁控制单一处理
        @param {fuction} callback_fun=None - 回调函数, 在执行完函数后执行, 定义如下
            fun(id, name, call_result, deal_fun_ret)
                id - 并发对象的id
                name - 并发对象的标识名
                call_result - 线程执行的结果, CResult对象, 如果执行无异常返回'00000'；
                    如果发生异常, 返回'21399', 并登记异常信息
                deal_fun_ret - deal_fun函数执行的返回值

        @param {Logger} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现info、warning、error等标准方法
        @param {bool} is_use_global_logger=True - 当logger=None时, 是否使用全局logger对象
            注: 通过RunTool.set_global_logger进行设置
        @param {int} log_level=logging.INFO - 打印日志的级别
        @param {bool} use_distributed_logger=False - 是否使用分布式logger, 如果是, 则每个分布任务自行创建独立logger记录日志
            注: 对于多进程及分布式并发任务, 应采取该日志模式
        @param {string} distributed_logger_module_name='' - 分布式日志类模块名
        @param {string} distributed_logger_class_name='' - 分布式日志类类名
        @param {tuple} distributed_logger_args=None - 分布式日志类创建参数
        @param {dict} distributed_logger_kwargs=None - 分布式日志类创建参数
        @param {dict} distributed_logger_replace_para=dict() - 分布式日志动态参数替换, 在每创建一个并发任务通过该参数修改日志参数
            key - 如果是int类型, 代表替换distributed_logger_args的第几个参数；如果是string, 代表替换distributed_logger_kwargs的指定参数
            value - 替换参数字典, key为要替换正则表达式字符, value为要替换的动态值
                要替换的动态值, 可选值有以下几种:
                    'pid' - 并发任务id
                    'pname' - 并发任务名
                    'pocess_id' - 进程ID
                    'thread_id' - 线程ID
        @param {bool} is_logger_to_deal_fun=False - 是否传递并发任务logger到deal_fun中
            注意: 传递通过kwargs, 参数名为logger
        @param {bool} auto_start=False - 是否自动启动并发池
        @param {bool} auto_stop=False - 是否自动关闭并发池(当任务都已全部完成处理)
        @param {QueueFw} task_queue=None - 并发池需要处理的任务队列
            注: 如果有指定队列, get_task_num_fun参数无效, 则自动根据队列长度检查待处理任务
        @param {function} get_task_num_fun=None - 获取待处理任务数量的函数
            注: 如果task_queue和get_task_num_fun均为None, 则直接创建最大数量的线程数, 且不释放空闲任务
        @param {list} get_task_num_fun_args=None - 获取待处理任务数量的函数, 的入参列表
        @param {int} maxsize=10 - 并发池最大并发对象数
        @param {int} minsize=0 - 并发池最小并发对象数
        @param {number} worker_release_time=10 - 空闲工作并发对象释放时间, 单位为秒, 0代表不控制空闲释放
        @param {number} worker_overtime=0 - 正在执行的任务超时时间(秒), 0代表不控制超时
            注: 对于超时执行任务, 将视为失效任务, 可以选择直接忽略或强制中止
        @param {bool} force_kill_overtime_worker=False - 是否强制中止失效任务
        @param {bool} replace_overtime_worker=False - 是否创建新任务替代超时任务
            注: 仅当force_kill_overtime_worker=False时才会进行替代
        @param {number} daemon_thread_time=0.01 - 守护线程的间隔时间
        @param {ParallelShareDictFw} sharedict_class=None - 进程间共享字典对象的类对象, 获取方法参考parallel_class:
            sharedict_class=ThreadParallelShareDict
        @param {ParallelLockFw} parallel_lock_class=None - 进程间锁对象的类对象, 获取方法参考parallel_class:
            parallel_lock_class=ThreadParallelLock
        @param {**kwargs} kwargs - 并行任务类对应的初始化参数, 具体参数定义参考具体实现类

        """
        self._parallel_class = parallel_class
        if parallel_class is None:
            self._parallel_class = ThreadParallel
        self._deal_fun = deal_fun
        self._run_args = run_args
        if run_args is None:
            self._run_args = ()
        self._run_kwargs = run_kwargs
        if run_kwargs is None:
            self._run_kwargs = {}
        self._pname = pname
        self._lock = lock
        self._callback_fun = callback_fun
        self._logger = logger
        if self._logger is None and is_use_global_logger:
            # 使用全局logger
            self._logger = RunTool.get_global_logger()
        self._log_level = log_level
        self._use_distributed_logger = use_distributed_logger
        self._distributed_logger_module_name = distributed_logger_module_name
        self._distributed_logger_class_name = distributed_logger_class_name
        self._distributed_logger_args = distributed_logger_args
        if distributed_logger_args is None:
            self._distributed_logger_args = ()
        self._distributed_logger_kwargs = distributed_logger_kwargs
        if distributed_logger_kwargs is None:
            self._distributed_logger_kwargs = {}
        self._distributed_logger_replace_para = distributed_logger_replace_para
        if distributed_logger_replace_para is None:
            self._distributed_logger_replace_para = {}
        self._is_logger_to_deal_fun = is_logger_to_deal_fun

        self._auto_stop = auto_stop
        self._task_queue = task_queue
        self._get_task_num_fun = get_task_num_fun
        self._get_task_num_fun_args = get_task_num_fun_args
        if task_queue is not None:
            # 指定处理队列, self._get_task_num_fun采用自己的函数
            self._get_task_num_fun = self._get_queue_num
            self._get_task_num_fun_args = list()
        elif get_task_num_fun_args is None:
            self._get_task_num_fun_args = list()

        self._maxsize = maxsize
        self._minsize = minsize
        self._worker_release_time = worker_release_time
        self._worker_overtime = worker_overtime
        self._force_kill_overtime_worker = force_kill_overtime_worker
        self._replace_overtime_worker = replace_overtime_worker
        self._daemon_thread_time = daemon_thread_time
        self._sharedict_class = sharedict_class
        if sharedict_class is None:
            self._sharedict_class = ThreadParallelShareDict
        self._parallel_lock_class = parallel_lock_class
        if parallel_lock_class is None:
            self._parallel_lock_class = ThreadParallelLock
        self._kwargs = kwargs

        # 初始化内部处理的变量
        self._pool_id = str(uuid.uuid1())
        self._status = 0  # 并发池的状态, 0-未运行, 1-正在运行, 2- 暂停
        self._daemon = None  # 守护线程
        self._workers_lock = threading.RLock()  # 工作任务清单的访问锁
        self._overtime_workers = dict()  # 超时执行的工作任务清单, key为工作任务标识uuid

        # 公共共享信息, key包括:
        # working_num  - 正在执行任务的任务数, 开始执行任务时+1, 任务完成后-1
        self._share_info = None

        # 工作任务清单, key为工作任务的标识uuid, value为[进程对象, 共享对象信息]self._sharedict_class对应的共享对象(每个任务创建1个)
        # 共享对象的信息包括(key):
        #   status - 执行状态(0-空闲, 1-正在执行, 2-暂停, 3-已销毁)
        #   cmd - 任务指令通知(0-无指令, 2-暂停任务, 3-结束任务, 4-因空闲结束任务)
        #   starttime - 启动时间(datetime)
        #   taskbegin - 开始执行任务时间(datetime)
        #   freebegin - 空闲开始时间
        self._workers = dict()

        if auto_start:
            # 自动启动任务池
            self.start()

    def start(self):
        """
        启动并发池

        """
        if self._status != 0:
            raise AlreadyRunning

        # 初始化状态
        self._status = 1
        self._overtime_workers.clear()
        self._share_info = self._sharedict_class(self._pool_id)
        self._share_info['working_num'] = 0
        self._workers.clear()

        # 直接启动daemon线程即可
        self._daemon = ThreadParallel(
            self._daemon_fun, auto_start=True, pname='daemon', set_daemon=True,
            logger=self._logger, log_level=self._log_level
        )

    def stop(self, overtime=0, force=False):
        """
        停止并发池

        @param {number} overtime=0 - 等待超时时间, 单位为秒, 超过时间抛出异常
        @param {bool} force_stop=False - 是否强制关闭并发池, 直接中止所有任务

        @throws {CallOverTime} - 等待超时时抛出异常

        """
        if self._status == 0:
            # 已经是停止状态
            raise NotRunning

        # 发送命令
        self._status = 5  # 通知停止
        if force:
            # 强制停止所有进程
            self._workers_lock.acquire()
            _keys = list(self._workers.keys())
            for _key in _keys:
                self._force_kill_worker(_key)
            self._workers_lock.release()
        elif overtime > 0:
            # 等待
            _starttime = datetime.datetime.now()
            while self._status != 0:
                RunTool.sleep(0.01)
                if (datetime.datetime.now() - _starttime).total_seconds() > overtime:
                    # 超时抛出异常
                    raise CallOverTime

    def pause(self, overtime=0):
        """
        暂停并发任务处理

        @param {number} overtime=0 - 等待超时时间, 单位为秒, 超过时间抛出异常

        @throws {CallOverTime} - 等待超时时抛出异常

        """
        if self._status == 0:
            # 已经是停止状态
            raise NotRunning

        # 发送命令
        self._status = 3  # 通知暂停
        if overtime > 0:
            # 等待
            _starttime = datetime.datetime.now()
            while self._status == 3:
                RunTool.sleep(0.01)
                if (datetime.datetime.now() - _starttime).total_seconds() > overtime:
                    # 超时抛出异常
                    raise CallOverTime

    def resume(self, overtime=0):
        """
        继续并发任务处理

        @param {number} overtime=0 - 等待超时时间, 单位为秒, 超过时间抛出异常

        @throws {CallOverTime} - 等待超时时抛出异常

        """
        if self._status == 0:
            # 已经是停止状态
            raise NotRunning

        # 发送命令
        self._status = 4  # 通知暂停
        if overtime > 0:
            # 等待
            _starttime = datetime.datetime.now()
            while self._status == 4:
                RunTool.sleep(0.01)
                if (datetime.datetime.now() - _starttime).total_seconds() > overtime:
                    # 超时抛出异常
                    raise CallOverTime

    @property
    def is_stop(self):
        """
        并发池是否停止状态

        @property {bool}

        """
        return self._status == 0

    #############################
    # 公共静态函数
    #############################
    @staticmethod
    def allways_return_fix_number(num=1000):
        """
        get_task_num_fun的可选函数, 永远返回固定的任务值

        @param {int} num=1000 - 要返回的任务数

        @returns {int} - 返回输入的任务数

        """
        return num

    #############################
    # 内部函数
    #############################
    def _get_queue_num(self):
        """
        获取任务队列长度

        """
        return self._task_queue.qsize()

    def _force_kill_worker(self, tid):
        """
        强制销毁指定任务

        @param {uuid} tid - 任务id

        """
        if tid in self._workers.keys():
            self._workers[tid][0].force_stop()
            del self._workers[tid]
        if tid in self._overtime_workers.keys():
            del self._overtime_workers[tid]
        if self._logger is not None:
            self._logger.log(
                self._log_level,
                'ParallelPool[%s] force kill Worker[%s: %s]' % (self._pool_id, self._pname, tid)
            )

    @classmethod
    def _worker_deal_fun(cls, tid, share_info, worker_info, **kwargs):
        """
        工作进程(线程)实际执行函数, 循环调用self._deal_fun进行任务处理
        kwargs的参数包括:
            logger
            log_level
            pool_id
            pname
            worker_release_time
            lock
            deal_fun
            run_args
            run_kwargs
            callback_fun
            is_logger_to_deal_fun

        """
        if kwargs['logger'] is not None:
            kwargs['logger'].log(
                kwargs['log_level'],
                'ParallelPool[%s] start Worker[%s: %s]' % (kwargs['pool_id'], kwargs['pname'], tid)
            )

        # 循环进行处理
        _ret_info = ''
        worker_info['freebegin'] = datetime.datetime.now()
        while True:
            try:
                # 检查退出处理的条件
                if worker_info['cmd'] == 3:
                    # 结束任务
                    _ret_info = 'exit by ParallelPool stop command'
                    break
                elif worker_info['cmd'] == 4:
                    # 因空闲结束任务
                    if (datetime.datetime.now() - worker_info['freebegin']).total_seconds() > kwargs['worker_release_time']:
                        _ret_info = 'exit by ParallelPool free release command '
                        break
                    else:
                        # 判断多一次, 避免时间差的误判
                        worker_info['cmd'] = 0
                elif worker_info['cmd'] == 2:
                    # 暂停任务, 直接往下循环
                    worker_info['status'] = 2
                    RunTool.sleep(0.001)
                    continue

                # 执行处理函数
                share_info['working_num'] += 1
                worker_info['status'] = 1
                _taskbegin = datetime.datetime.now()
                worker_info['taskbegin'] = _taskbegin

                _call_result = CResult(code='00000')  # 成功
                _deal_fun_ret = None

                # 是否传递logger
                if kwargs['is_logger_to_deal_fun']:
                    kwargs['run_kwargs']['logger'] = kwargs['logger']

                # 执行处理函数
                if kwargs['lock'] is not None:
                    kwargs['lock'].acquire()  # 获取锁

                with ExceptionTool.ignored_cresult(_call_result):
                    _deal_fun_ret = kwargs['deal_fun'](*kwargs['run_args'], **kwargs['run_kwargs'])

                if kwargs['lock'] is not None:
                    kwargs['lock'].release()  # 释放锁

                if not (_call_result.code[0] == '0' and _deal_fun_ret is None):
                    # 返回值不为None, 认为有获取任务及执行
                    worker_info['freebegin'] = datetime.datetime.now()

                    # 执行回调函数
                    if kwargs['callback_fun'] is not None:
                        try:
                            kwargs['callback_fun'](tid, kwargs['pname'],
                                                   _call_result, _deal_fun_ret)
                        except Exception as e:
                            # 写异常日志
                            if kwargs['logger'] is not None:
                                kwargs['logger'].log(
                                    logging.ERROR,
                                    '[EX:%s]ParallelPool[%s] execute Worker[%s: %s] job callback error: %s' % (
                                        str(type(e)),
                                        kwargs['pool_id'],
                                        kwargs['pname'],
                                        tid,
                                        traceback.format_exc()
                                    )
                                )

                    # 写执行日志
                    _use = str((datetime.datetime.now() - _taskbegin).total_seconds())
                    if kwargs['logger'] is not None:
                        if _call_result.code[0] == '0':
                            kwargs['logger'].log(
                                kwargs['log_level'],
                                '[USE:%ss]ParallelPool[%s] Worker[%s: %s] finished job' % (
                                    _use,
                                    kwargs['pool_id'],
                                    kwargs['pname'],
                                    tid
                                )
                            )
                        else:
                            # 执行异常
                            kwargs['logger'].log(
                                logging.ERROR,
                                '[USE:%ss][EX:%s]ParallelPool[%s] execute Worker[%s: %s] job error: %s' % (
                                    _use,
                                    str(type(_call_result.error)),
                                    kwargs['pool_id'],
                                    kwargs['pname'],
                                    tid,
                                    _call_result.trace_str
                                )
                            )

                # 执行完成
                share_info['working_num'] -= 1
                worker_info['status'] = 0

            except Exception as e:
                # 出现异常, 退出线程
                if kwargs['logger'] is not None:
                    kwargs['logger'].log(
                        logging.ERROR,
                        '[EX:%s]ParallelPool[%s]  Worker[%s: %s] error: %s' % (
                            str(type(e)
                                ), kwargs['pool_id'], kwargs['pname'], tid, traceback.format_exc()
                        )
                    )
                _ret_info = 'exit by excepiton'
                break

        # 退出任务
        worker_info['status'] = 3  # 通知外面自己已销毁
        if kwargs['logger'] is not None:
            kwargs['logger'].log(
                kwargs['log_level'],
                'ParallelPool[%s] Worker[%s: %s] stoped : %s' % (
                    kwargs['pool_id'], kwargs['pname'], tid, _ret_info)
            )

    def _create_worker(self):
        """
        创建一个新的工作任务

        @returns {bool} - 是否创建成功

        """
        # 基础数据
        _tid = str(uuid.uuid1())
        _worker_info = self._sharedict_class(_tid)
        _worker_info['status'] = 0  # 执行状态(0-空闲, 1-正在执行, 2-暂停, 3-已销毁)
        _worker_info['cmd'] = 0  # 任务指令通知(0-无指令, 2-暂停任务, 3-结束任务, 4-因空闲结束任务)
        _now = datetime.datetime.now()
        _worker_info['starttime'] = _now  # 启动时间(datetime)
        _worker_info['taskbegin'] = _now  # 开始执行任务时间(datetime)
        _worker_info['freebegin'] = _now  # 空闲开始时间
        self._workers_lock.acquire()
        self._workers[_tid] = [None, _worker_info]

        _kwargs = {
            'log_level': self._log_level,
            'pool_id': self._pool_id,
            'pname': self._pool_id,
            'worker_release_time': self._worker_release_time,
            'lock': self._lock,
            'deal_fun': self._deal_fun,
            'run_args': self._run_args,
            'run_kwargs': self._run_kwargs,
            'callback_fun': self._callback_fun,
            'is_logger_to_deal_fun': self._is_logger_to_deal_fun
        }

        # 创建线程
        try:
            _task = self._parallel_class(
                self._worker_deal_fun, run_args=(
                    _tid, self._share_info, _worker_info), run_kwargs=_kwargs,
                auto_start=True, pid=_tid, pname=self._pname, lock=None,
                callback_fun=None, set_daemon=True, logger=self._logger,
                use_distributed_logger=self._use_distributed_logger,
                distributed_logger_module_name=self._distributed_logger_module_name,
                distributed_logger_class_name=self._distributed_logger_class_name,
                distributed_logger_args=self._distributed_logger_args,
                distributed_logger_kwargs=self._distributed_logger_kwargs,
                is_logger_to_deal_fun=True,
                log_level=self._log_level, **self._kwargs
            )
            self._workers[_tid][0] = _task
        except Exception as e:
            # 记录日志
            if self._logger is not None:
                self._logger.log(
                    logging.ERROR,
                    '[EX:%s]ParallelPool[%s]  create Worker[%s: %s] error: %s' % (
                        str(type(e)), self._pool_id, self._pname, _tid, traceback.format_exc()
                    )
                )
            return False
        finally:
            self._workers_lock.release()
        return True

    def _daemon_fun(self):
        """
        守护进程, 对任务的控制由该进程处理

        """
        self._status = 1  # 并发池的状态, 0-未运行, 1-正在运行, 2- 暂停, 3-通知暂停, 4-通知恢复, 5-通知停止
        # 循环进行处理
        while True:
            try:
                # 状态处理
                if self._status == 3:
                    # 通知暂停
                    if self._logger is not None:
                        self._logger.log(
                            self._log_level,
                            'ParallelPool[%s: %s] get pause cmd, waiting workers pause...' % (
                                self._pool_id, self._pname)
                        )
                    self._workers_lock.acquire()
                    for _key in self._workers.keys():
                        if self._workers[_key][1]['cmd'] == 0:
                            self._workers[_key][1]['cmd'] = 2
                    self._workers_lock.release()
                    # 内部循环等待所有任务状态为暂停
                    while self._status == 3:
                        RunTool.sleep(self._daemon_thread_time)
                        _all_pause = True
                        self._workers_lock.acquire()
                        for _key in self._workers.keys():
                            if _key not in self._overtime_workers.keys() and self._workers[_key][1]['status'] in (0, 1):
                                _all_pause = False
                                break
                        self._workers_lock.release()
                        if _all_pause:
                            self._status = 2  # 全部任务已经为暂停状态
                            if self._logger is not None:
                                self._logger.log(
                                    self._log_level,
                                    'ParallelPool[%s: %s]  pause success' % (
                                        self._pool_id, self._pname)
                                )

                if self._status == 4:
                    # 通知恢复
                    if self._logger is not None:
                        self._logger.log(
                            self._log_level,
                            'ParallelPool[%s: %s] get resume cmd, waiting workers resume...' % (
                                self._pool_id, self._pname)
                        )
                    self._workers_lock.acquire()
                    for _key in self._workers.keys():
                        if self._workers[_key][1]['cmd'] == 2:
                            self._workers[_key][1]['cmd'] = 0
                    self._workers_lock.release()
                    # 内部循环等待所有任务状态为非暂停
                    while self._status == 4:
                        RunTool.sleep(self._daemon_thread_time)
                        _all_resume = True
                        self._workers_lock.acquire()
                        for _key in self._workers.keys():
                            if self._workers[_key][1]['status'] == 2:
                                _all_resume = False
                                break
                        self._workers_lock.release()
                        if _all_resume:
                            self._status = 1  # 全部任务已经为恢复状态
                            if self._logger is not None:
                                self._logger.log(
                                    self._log_level,
                                    'ParallelPool[%s: %s]  resume success' % (
                                        self._pool_id, self._pname
                                    )
                                )

                if self._status == 5:
                    # 通知停止
                    if self._logger is not None:
                        self._logger.log(
                            self._log_level,
                            'ParallelPool[%s: %s] get stop cmd, waiting workers stop...' % (
                                self._pool_id, self._pname
                            )
                        )
                    self._workers_lock.acquire()
                    for _key in self._workers.keys():
                        self._workers[_key][1]['cmd'] = 3
                    self._workers_lock.release()
                    # 内部循环等待所有任务状态为停止
                    while self._status == 5:
                        RunTool.sleep(self._daemon_thread_time)
                        _all_stop = True
                        self._workers_lock.acquire()
                        for _key in self._workers.keys():
                            if self._workers[_key][1]['status'] != 3:
                                _all_stop = False
                                break
                        self._workers_lock.release()
                        if _all_stop:
                            self._status = 0  # 全部任务已经为销毁状态
                            if self._logger is not None:
                                self._logger.log(
                                    self._log_level,
                                    'ParallelPool[%s: %s]  stop success' % (
                                        self._pool_id, self._pname)
                                )

                if self._status == 2:
                    # 暂停
                    RunTool.sleep(self._daemon_thread_time)
                    continue

                if self._status == 0:
                    # 停止
                    break

                # 清理已销毁任务,释放空闲线程, 以及判断超时情况
                self._workers_lock.acquire()
                _current_worker_count = len(self._workers)
                _keys = list(self._workers.keys())
                for _key in _keys:
                    if self._workers[_key][1]['status'] == 3:
                        # 已销毁, 直接从清单删除就可以了
                        del self._workers[_key]
                        continue

                    if (
                        self._get_task_num_fun is not None and
                        self._worker_release_time > 0 and
                        self._workers[_key][1]['status'] == 0 and
                        (datetime.datetime.now() -
                         self._workers[_key][1]['freebegin']).total_seconds() > self._worker_release_time
                    ):
                        # 空闲时间比较久, 释放任务, 但注意要保持最小的并发任务数
                        if _current_worker_count > self._minsize:
                            self._workers[_key][1]['cmd'] = 4
                            _current_worker_count -= 1

                    if (
                        self._worker_overtime > 0 and
                        _key not in self._overtime_workers.keys() and
                        self._workers[_key][1]['status'] == 1 and
                        (datetime.datetime.now() -
                         self._workers[_key][1]['taskbegin']).total_seconds() > self._worker_overtime
                    ):
                        # 任务执行超时
                        if self._force_kill_overtime_worker:
                            # 强制杀掉任务
                            if self._logger is not None:
                                self._logger.log(
                                    self._log_level,
                                    'ParallelPool[%s] worker[%s: %s] overtime[%ss] from %s, auto force killed' % (
                                        self._pool_id, self._pname, _key, str(
                                            self._worker_overtime),
                                        str(self._workers[_key][1]['taskbegin'])
                                    )
                                )
                            self._force_kill_worker(_key)
                        else:
                            # 放入超时清单
                            if self._logger is not None:
                                self._logger.log(
                                    self._log_level,
                                    'ParallelPool[%s] worker[%s: %s] overtime[%ss] from %s' % (
                                        self._pool_id, self._pname, _key, str(
                                            self._worker_overtime),
                                        str(self._workers[_key][1]['taskbegin'])
                                    )
                                )
                            self._overtime_workers[_key] = self._workers[_key]

                    if (
                        _key in self._overtime_workers.keys() and
                        (
                            self._workers[_key][1]['status'] != 1 or
                            (datetime.datetime.now() -
                             self._workers[_key][1]['taskbegin']).total_seconds() <= self._worker_overtime
                        )
                    ):
                        # 原理任务超时了, 将任务从超时列表中删除
                        del self._overtime_workers[_key]
                self._workers_lock.release()

                # 根据任务状态检查是否要自动停止
                if self._auto_stop and self._task_queue is not None:
                    # 检查队列是否已为空, 如果是, 发命令通知任务关闭
                    if self._task_queue.qsize() == 0:
                        self._status = 5
                        if self._logger is not None:
                            self._logger.log(
                                self._log_level,
                                'ParallelPool[%s: %s] queue is empty, auto stop pool, send stop cmd' % (
                                    self._pool_id, self._pname
                                )
                            )
                        # 重新检查
                        continue

                # 根据需要新增任务
                if self._status == 1:
                    # 获取任务数量
                    _all_thread_num = len(self._workers)
                    if self._replace_overtime_worker:
                        _all_thread_num = _all_thread_num - len(self._overtime_workers)
                    _create_num = self._maxsize - _all_thread_num
                    if self._get_task_num_fun is not None:
                        _task_num = self._get_task_num_fun(*self._get_task_num_fun_args)
                        if _create_num > _task_num:
                            _create_num = _task_num
                        if _all_thread_num + _create_num < self._minsize:
                            _create_num = self._minsize - _all_thread_num

                    if _create_num > 0 and self._logger is not None:
                        self._logger.log(
                            self._log_level,
                            'ParallelPool[%s: %s] auto create %s worker' % (
                                self._pool_id, self._pname, str(_create_num)
                            )
                        )

                    while _create_num > 0:
                        self._create_worker()
                        _create_num = _create_num - 1

                RunTool.sleep(self._daemon_thread_time)

            except Exception as e:
                # 异常, 写日志, 但不退出
                if self._logger is not None:
                    self._logger.log(
                        logging.ERROR,
                        '[EX:%s]ParallelPool[%s: %s] daemon error: %s' % (
                            str(type(e)), self._pool_id, self._pname, traceback.format_exc()
                        )
                    )
                RunTool.sleep(self._daemon_thread_time)


class ThreadParallelLock(ParallelLockFw):
    """
    线程并发锁(基于ParallelLockFw的实现)

    @param {**kwargs} kwargs - 初始化参数, 暂无用

    """
    #############################
    # 内部函数, 继承
    #############################

    def _init(self, **kwargs):
        """
        初始化并发锁

        @param {**kwargs} kwargs - 初始化参数, 暂无用

        """
        self._lock_object = threading.RLock()

    def _acquire(self, **kwargs):
        """
        获取并发锁

        @param {**kwargs} kwargs - 处理参数, 暂无用

        """
        self._lock_object.acquire()

    def _release(self, **kwargs):
        """
        释放并发锁

        @param {**kwargs} kwargs - 处理参数, 暂无用

        """
        self._lock_object.release()


class ProcessParallelLock(ParallelLockFw):
    """
    进程并发锁(基于ParallelLockFw的实现)

    @param {**kwargs} kwargs - 初始化参数, 暂无用

    """
    #############################
    # 内部函数, 继承
    #############################

    def _init(self, **kwargs):
        """
        初始化并发锁

        @param {**kwargs} kwargs - 初始化参数, 暂无用

        """
        self._lock_object = Lock()

    def _acquire(self, **kwargs):
        """
        获取并发锁

        @param {**kwargs} kwargs - 处理参数, 暂无用

        """
        self._lock_object.acquire()

    def _release(self, **kwargs):
        """
        释放并发锁

        @param {**kwargs} kwargs - 处理参数, 暂无用

        """
        self._lock_object.release()


class ThreadParallelShareDict(ParallelShareDictFw):
    """
    线程共享字典对象(基于ParallelShareDictFw的实现)

    """
    #############################
    # 需实现类实现的接口定义
    #############################

    def _init(self, tag):
        """
        初始化对象(比如从服务端下载后进行初始化)

        @param {string} tag - 唯一标识

        @returns {object} - 需要返回初始化后的本地对象, 存放在self._dict中

        """
        # 检查全局变量是否有该对象
        _gdict = RunTool.get_global_var('ThreadParallelShareDict' + tag)
        if _gdict is None:
            # 直接初始化就好
            _gdict = dict()
            RunTool.set_global_var('ThreadParallelShareDict' + tag, _gdict)

        return _gdict

    def _refresh(self, key):
        """
        刷新自身对象指定key的值(比如从服务端下载)

        @param {object} key - 要刷新的key

        @returns {object} - 返回具体的值

        """
        self._dict = RunTool.get_global_var('ThreadParallelShareDict' + self._tag)
        return self._dict[key]

    def _update(self, key, value):
        """
        更新自身对象指定key的值(比如上传到服务端)

        @param {object} key - 索引
        @param {object} value - 要设置的值

        """
        self._dict = RunTool.get_global_var('ThreadParallelShareDict' + self._tag)
        self._dict[key] = value
        RunTool.set_global_var('ThreadParallelShareDict' + self._tag, self._dict)


class ProcessParallelShareDict(ParallelShareDictFw):
    """
    线程共享字典对象(基于ParallelShareDictFw的实现)

    """
    #############################
    # 需实现类实现的接口定义
    #############################

    def _init(self, tag):
        """
        初始化对象(比如从服务端下载后进行初始化)

        @param {string} tag - 唯一标识

        @returns {object} - 需要返回初始化后的本地对象, 存放在self._dict中

        """
        return Manager().dict()

    def _refresh(self, key):
        """
        刷新自身对象指定key的值(比如从服务端下载)

        @param {object} key - 要刷新的key

        @returns {object} - 返回具体的值

        """
        return self._dict[key]

    def _update(self, key, value):
        """
        更新自身对象指定key的值(比如上传到服务端)

        @param {object} key - 索引
        @param {object} value - 要设置的值

        """
        self._dict[key] = value


class ThreadParallel(ParallelFw):
    """
    多线程并行任务处理

    """
    #############################
    # 内部变量
    #############################
    _start_args = None
    _start_kwargs = None
    _thread = None

    #############################
    # 内部函数
    #############################
    @classmethod
    def _async_raise(cls, tid, exctype):
        """
        强制中止线程处理, 网上找到的方法

        """
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    #############################
    # 内部函数 - 具体实现
    #############################
    def _start(self, run_args=None, run_kwargs=None, **kwargs):
        """
        执行并发任务
        1、在并发任务启动中, 如果出现异常_start可捕获到的, 可直接抛出异常
        2、并发任务执行中出现的异常(_start捕获不到的), 应由实现类进行捕获处理, 不应抛出
        3、并发任务在执行deal_fun前应根据锁要求先获取锁, 执行完deal_fun后释放锁
        4、并发任务执行完成后(包括出现异常中止), 需调用self._self_callback通知框架进行后续处理

        @param {tuple} run_args=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {dict} run_kwargs=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {**kwargs} kwargs - 处理参数, 暂不使用

        """
        # 先初始化多线程对象
        _thread_fun_kwargs = self._get_thread_fun_kwargs()

        if run_args is not None:
            _thread_fun_kwargs['run_args'] = run_args

        if run_kwargs is not None:
            _thread_fun_kwargs['run_kwargs'] = run_kwargs

        if _thread_fun_kwargs['logger'] is not None and self._use_distributed_logger:
            # 使用独立日志
            _thread_fun_kwargs['logger'] = None

        self._thread = threading.Thread(
            target=self._base_parallel_thread_fun,
            name=self._pname,
            kwargs=_thread_fun_kwargs,
            daemon=self._set_daemon
        )
        # 启动线程
        self._thread.start()

    def _force_stop(self, **kwargs):
        """
        强制中止并行任务

        @param {**kwargs} kwargs - 处理参数, 暂不使用

        """
        self._async_raise(self._thread.ident, SystemExit)

    def _create_stat_lock(self):
        """
        创建线程执行状态更新锁

        @returns {ParallelLockFw} - 返回指定的锁

        """
        return ThreadParallelLock()

    def _create_is_running_obj(self):
        """
        创建是否运行状态的共享变量

        """
        return {'is_running': False}


class ProcessParallel(ParallelFw):
    """
    多进程并行任务处理
    部分沿用了多线程的代码, 只是部分函数重载

    """

    #############################
    # 自身特定的函数
    #############################
    def bind_cpu(self, cpu_num=1):
        """
        绑定进程在指定CPU上执行
        注: 暂时只支持windows和linux

        @param {long} cpu_num=1L - 要指定的CPU

        @throws {NotRunning} - 当进程未运行时, 抛出该异常

        """
        self._stat_lock.acquire()
        try:
            if not self._get_is_running():
                raise NotRunning

            _pid = self._thread.pid
        finally:
            self._stat_lock.release()

        if sys.platform in ('win32', 'linux2'):
            try:
                _last_cpu = affinity.set_process_affinity_mask(_pid, cpu_num)
                # 打印日志
                if self._logger is not None:
                    self._logger.log(
                        self._log_level,
                        'set process [%s:%s] bind cpu - [pid:%s] from %s to %s' % (
                            self._pid,
                            self._pname,
                            str(_pid),
                            str(_last_cpu),
                            str(cpu_num)
                        )
                    )
            except:
                if self._logger is not None:
                    self._logger.log(
                        'affinity for python 3 incorrect, change affinity/__init__.py to fix'
                    )

    def get_runing_cpu(self):
        """
        获取当前进程运行所在的CPU

        @returns {long} - 当前CPU标识

        """
        self._stat_lock.acquire()
        try:
            if not self._get_is_running():
                raise NotRunning

            _pid = self._thread.pid
        finally:
            self._stat_lock.release()

        # 更换处理方式
        _proess = psutil.Process(_pid)
        return _proess.cpu_num()

    #############################
    # 内部函数 - 具体实现_is_running
    #############################
    def _init(self):
        """
        重载初始化对象, 部分公共访问对象修改为支持多进程访问

        """
        return

    def _start(self, run_args=None, run_kwargs=None, **kwargs):
        """
        执行并发任务
        1、在并发任务启动中, 如果出现异常_start可捕获到的, 可直接抛出异常
        2、并发任务执行中出现的异常(_start捕获不到的), 应由实现类进行捕获处理, 不应抛出
        3、并发任务在执行deal_fun前应根据锁要求先获取锁, 执行完deal_fun后释放锁
        4、并发任务执行完成后(包括出现异常中止), 需调用self._self_callback通知框架进行后续处理

        @param {tuple} run_args=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {dict} run_kwargs=None - 启动时重新指定执行参数, 如果为None代表按初始化的参数执行
        @param {**kwargs} kwargs - 处理参数, 暂不使用

        """
        # 先初始化多进程对象
        _thread_fun_kwargs = self._get_thread_fun_kwargs()

        if run_args is not None:
            _thread_fun_kwargs['run_args'] = run_args

        if run_kwargs is not None:
            _thread_fun_kwargs['run_kwargs'] = run_kwargs

        # 使用独立日志
        _thread_fun_kwargs['logger'] = None

        self._thread = Process(
            target=self._base_parallel_thread_fun,
            name=self._pname,
            kwargs=_thread_fun_kwargs
        )

        # 启动进程
        self._thread.start()

    def _force_stop(self, **kwargs):
        """
        强制中止并行任务

        @param {**kwargs} kwargs - 处理参数, 暂不使用

        """
        self._thread.terminate()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
