#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
简单流数据获取及处理库

@module stream
@file stream.py

"""

import os
import sys
import traceback
import threading
from enum import Enum
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.generic import NullObj
from HiveNetCore.utils.run_tool import RunTool


__MOUDLE__ = 'stream'  # 模块名
__DESCRIPT__ = u'简单流数据获取及处理库'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


class EnumStreamClosedStatus(Enum):
    """
    流中止的状态枚举值

    @enum {string}

    """
    RunOver = 'RunOver'  # 流运行到结尾关闭
    CallStop = 'CallStop'  # 外部调用停止方法关闭
    ForceStop = 'ForceStop'  # 外部调用强制停止方法关闭
    ExceptionExit = 'ExceptionExit'  # 出现异常关闭


class BaseStream(ABC):
    """
    基础流数据处理定义基类, 定义流数据处理的基本框架函数

    @param {bool} back_forward=False - 是否允许反向移动,即跳转回前面已获取过的数据
    @param {bool} keep_wait_data=False - 无数据时是否继续等待新数据进入,即到数据结尾后,关闭处理,还是继续等待扫描新数据
    @param {bool} stop_by_excepiton=False - 当出现异常时是否中止流处理
    @param {object} logger=None - 出现错误时进行error输出的日志类(需实现error方法),None代表不输出日志
    @param {function} dealer_exception_fun=None - 流处理异常时执行的通知函数,函数有6个入参:
        stream_tag : string 流标识
        stream_obj : object 流对象
        deal_obj : object 正在处理的流对象
        position : object 正在处理的流对象的位置
        dealer_handle : fun 出现异常时所执行的处理函数对象
        error_obj : object 异常对象,sys.exc_info()
        trace_str : string 异常的堆栈信息
    @param {function} stream_closed_fun=None - 流处理结束时执行的通知函数,函数有2个入参:
        stream_tag : string 流标识
        stream_obj : object 流对象
        position : object 正在处理的流对象的位置
        closed_status : EnumStreamClosedStatus 关闭状态

    """

    #############################
    # 内部变量
    #############################

    _back_forward = False  # 是否允许反向移动
    _keep_wait_data = False  # 无数据时是否继续等待新数据进入,不关闭流
    _stop_by_excepiton = False  # 当出现异常时是否中止流处理
    _logger = None  # 日志处理类
    _dealer_exception_fun = None  # 流处理异常时执行的通知函数
    _stream_closed_fun = None  # 流处理结束的通知函数
    _dealer_handles = None  # 处理流数据的处理函数句柄字典,key为函数句柄,value统一为None
    _stream_list = None  # 正在处理的流对象列表,key为stream_tag,value为stream_obj
    _stream_list_tag = None  # 正在处理的流对象对应的处理标记,key为stream_tag,value为(_stop_tag, _pause_tag):
    _stream_list_lock = None  # 流处理对象列表更新锁
    _force_stop_tag = False  # 强制关闭所有流处理的标记

    #############################
    # 属性
    #############################

    @property
    def back_forward(self):
        """
        获取是否允许反向移动的标记

        @property {bool}

        """
        return self._back_forward

    @property
    def keep_wait_data(self):
        """
        获取无数据时是否继续等待新数据进入

        @property {bool}

        """
        return self._keep_wait_data

    #############################
    # 构造函数
    #############################

    def __init__(self, back_forward=False, keep_wait_data=False, stop_by_excepiton=False,
                 logger=None, dealer_exception_fun=None, stream_closed_fun=None):
        """
        构造函数

        @param {bool} back_forward=False - 是否允许反向移动,即跳转回前面已获取过的数据
        @param {bool} keep_wait_data=False - 无数据时是否继续等待新数据进入,即到数据结尾后,关闭处理,还是继续等待扫描新数据
        @param {bool} stop_by_excepiton=False - 当出现异常时是否中止流处理
        @param {object} logger=None - 出现错误时进行error输出的日志类(需实现error方法),None代表不输出日志
        @param {function} dealer_exception_fun=None - 流处理异常时执行的通知函数,函数有6个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            deal_obj : object 正在处理的流对象
            position : object 正在处理的流对象的位置
            dealer_handle : fun 出现异常时所执行的处理函数对象
            error_obj : object 异常对象,sys.exc_info()
            trace_str : string 异常的堆栈信息
        @param {function} stream_closed_fun=None - 流处理结束时执行的通知函数,函数有2个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            position : object 正在处理的流对象的位置
            closed_status : EnumStreamClosedStatus 关闭状态

        """
        self._dealer_handles = dict()  # 处理流数据的处理函数句柄字典,key为函数句柄,value统一为None
        self._stream_list = dict()  # 正在处理的流对象列表,key为stream_tag,value为stream_obj
        # 正在处理的流对象对应的处理标记,key为stream_tag,value为(_stop_tag, _pause_tag):
        self._stream_list_tag = dict()
        self._stream_list_lock = threading.RLock()  # 流处理对象列表更新锁

        self._back_forward = back_forward
        self._keep_wait_data = keep_wait_data
        self._stop_by_excepiton = stop_by_excepiton
        self._logger = logger
        self._dealer_exception_fun = dealer_exception_fun
        self._stream_closed_fun = stream_closed_fun

    #############################
    # 内部函数
    #############################

    def _stream_deal_fun(self, tid=0, stream_tag=''):
        """
        流顺序处理函数, 按顺序进行流对象的获取和处理, 每获取一个对象,调用注册的处理函数

        @param {int} tid=0 - 线程ID
        @param {string} stream_tag='' - 流处理标签

        @throws {KeyError} - 当传入错误的stream_tag,抛出该异常

        """
        _closed_status = EnumStreamClosedStatus.RunOver
        self._stream_list_lock.acquire()
        try:
            if stream_tag not in self._stream_list.keys():
                # 传入错误的标识
                raise KeyError(u'Unknow tid!')

            _stream_obj = self._stream_list[stream_tag]
        finally:
            self._stream_list_lock.release()

        try:
            _pos = self._current_position(_stream_obj)
            while True:
                try:
                    # 判断是否暂停或退出
                    if self._force_stop_tag:
                        # 强制退出
                        _closed_status = EnumStreamClosedStatus.ForceStop
                        return
                    if self._stream_list_tag[stream_tag][0]:
                        # 当前流的停止标记
                        _closed_status = EnumStreamClosedStatus.CallStop
                        return
                    if self._stream_list_tag[stream_tag][1]:
                        # 当前流的暂停标记
                        RunTool.sleep(0.01)
                        continue

                    # 循环进行流处理
                    _pos = self._current_position(_stream_obj)
                    _get_obj = self._next(_stream_obj)
                    for _handle in self._dealer_handles:
                        # 根据配置循环进行流处理
                        try:
                            _handle(_get_obj, _pos)
                        except:
                            # 先输出日志
                            _error_obj = sys.exc_info()
                            _trace_str = traceback.format_exc()
                            if self._logger is not None:
                                _log_str = 'stream deal exception(%s):\n%s' % (
                                    str(_handle),
                                    _trace_str
                                )
                            # 通知函数
                            if self._dealer_exception_fun is not None:
                                try:
                                    self._dealer_exception_fun(stream_tag=stream_tag, stream_obj=_stream_obj,
                                                               deal_obj=_get_obj, position=_pos, dealer_handle=_handle,
                                                               error_obj=_error_obj, trace_str=_trace_str)
                                except:
                                    if self._logger is not None:
                                        _log_str = 'call dealer_exception_fun exception(%s):\n%s' % (
                                            str(_handle),
                                            traceback.format_exc()
                                        )
                                        self._logger.error(_log_str)
                            # 判断是否要退出
                            if self._stop_by_excepiton:
                                _closed_status = EnumStreamClosedStatus.ExceptionExit
                                return

                    # 准备执行下一个
                    RunTool.sleep(0.01)
                except StopIteration:
                    if self._keep_wait_data:
                        # 没有获取到数据,但继续循环尝试获取
                        RunTool.sleep(0.01)
                        continue
                    else:
                        # 已经到结尾了,结束流处理
                        return
        finally:
            # 关闭流处理
            try:
                if self._stream_closed_fun is not None:
                    self._stream_closed_fun(stream_tag=stream_tag, stream_obj=_stream_obj,
                                            position=_pos, closed_status=_closed_status)
            except:
                if self._logger is not None:
                    _log_str = 'call stream_closed_fun exception:\n%s' % traceback.format_exc()
                    self._logger.error(_log_str)
            try:
                self._close_stream(stream_obj=_stream_obj)
            except Exception:
                if self._logger is not None:
                    _log_str = 'call close_stream exception:\n%s' % traceback.format_exc()
                    self._logger.error(_log_str)

            # 情况流列表
            self._stream_list_lock.acquire()
            del self._stream_list[stream_tag]
            del self._stream_list_tag[stream_tag]
            self._stream_list_lock.release()

    @classmethod
    def _stream_deal_fun_decorator(cls, tid=0, stream_obj=None, stop_by_excepiton=False, logger=None,
                                   dealer_exception_fun=None, stream_closed_fun=None, stream_tag='stream_dealer',
                                   dealer_fun=None, **kwargs_dealer_fun):
        """
        函数修饰符方式流处理的处理函数

        @param {int} tid=0 - 线程ID
        @param {object} stream_obj=None - 要处理的流对象
        @param {bool} stop_by_excepiton=False - 当出现异常时是否中止流处理
        @param {object} logger=None - 出现错误时进行error输出的日志类(需实现error方法),None代表不输出日志
        @param {function} dealer_exception_fun=None - 流处理异常时执行的通知函数,函数有6个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            deal_obj : object 正在处理的流对象
            position : object 正在处理的流对象的位置
            dealer_handle : fun 出现异常时所执行的处理函数对象
            error_obj : object 异常对象,sys.exc_info()
            trace_str : string 异常的堆栈信息
        @param {function} stream_closed_fun=None - 流处理结束时执行的通知函数,函数有2个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            position : object 正在处理的流对象的位置
            closed_status : EnumStreamClosedStatus 关闭状态
        @param {string} stream_tag='stream_dealer' - 所启动的流处理标签,用于后续调用stop_stream的时候使用
        @param {dict} dealer_fun=None - 原函数对象执行传入的动态key-value参数

        """
        try:
            _closed_status = EnumStreamClosedStatus.RunOver
            _pos = cls._current_position(stream_obj)
            # 组织动态函数,目的是传入对应的参数
            _exec_fun_str = 'dealer_fun(_get_obj, _pos'
            for _key in kwargs_dealer_fun.keys():
                _exec_fun_str = '%s, %s=%s' % (
                    _exec_fun_str,
                    _key,
                    'kwargs_dealer_fun[\'' + _key + '\']'
                )
            _exec_fun_str = _exec_fun_str + ')'
            while True:
                try:
                    # 循环进行流处理
                    _pos = cls._current_position(stream_obj)
                    _get_obj = cls._next(stream_obj=stream_obj)
                    try:
                        # dealer_fun(_get_obj, _pos, kwargs_dealer_fun)
                        exec(_exec_fun_str)
                    except Exception:
                        # 先输出日志
                        _error_obj = sys.exc_info()
                        _trace_str = traceback.format_exc()
                        if logger is not None:
                            _log_str = 'stream decorator deal exception(%s):\n%s' % (
                                str(dealer_fun),
                                _trace_str
                            )
                        # 通知函数
                        if dealer_exception_fun is not None:
                            try:
                                dealer_exception_fun(stream_tag=stream_tag, stream_obj=stream_obj,
                                                     deal_obj=_get_obj, position=_pos, dealer_handle=dealer_fun,
                                                     error_obj=_error_obj, trace_str=_trace_str)
                            except Exception:
                                if logger is not None:
                                    _log_str = 'call dealer_exception_fun exception(%s):\n%s' % (
                                        str(dealer_fun),
                                        traceback.format_exc()
                                    )
                                    logger.error(_log_str)
                        # 判断是否要退出
                        if stop_by_excepiton:
                            _closed_status = EnumStreamClosedStatus.ExceptionExit
                            return

                    # 准备执行下一个
                    RunTool.sleep(0.01)
                except StopIteration:
                    # 已经到结尾了,结束流处理
                    return
        finally:
            # 关闭流处理
            try:
                if stream_closed_fun is not None:
                    stream_closed_fun(stream_tag=stream_tag, stream_obj=stream_obj, position=_pos,
                                      closed_status=_closed_status)
            except Exception:
                if logger is not None:
                    _log_str = 'call stream_closed_fun exception:\n%s' % traceback.format_exc()
                    logger.error(_log_str)
            try:
                cls._close_stream(stream_obj=stream_obj)
            except Exception:
                if logger is not None:
                    _log_str = 'call close_stream exception:\n%s' % traceback.format_exc()
                    logger.error(_log_str)

    #############################
    # 公共处理函数
    #############################
    def add_dealer(self, *args):
        """
        添加流数据处理函数句柄

        @param {*args} args - 要添加的处理函数句柄清单,可以随意增加多个

        """
        for _item in args:
            self._dealer_handles[_item] = None

    def del_dealer(self, *args):
        """
        删除流数据处理函数句柄

        @param {*args} args - 要删除的处理函数句柄清单,可以随意删除多个

        """
        for _item in args:
            if _item in self._dealer_handles.keys():
                del self._dealer_handles[_item]

    def clear_dealer(self):
        """
        清空流数据处理函数句柄集

        """
        self._dealer_handles.clear()

    #############################
    # 需继承类实现的内部处理函数
    #############################

    @staticmethod
    @abstractmethod
    def _init_stream(**kwargs):
        """
        抽象方法,根据传入参数初始化流对象(实现类自定义,也可以是标识),基类将保留该对象并供后续流处理函数调用

        @param {**kwargs} kwargs 启动流处理的动态key-value方式参数

        @returns {object} - 传入后续处理的流对象

        """
        pass

    @staticmethod
    @abstractmethod
    def _next(stream_obj):
        """
        抽象方法,从流中获取下一个对象,并将流指针指向下一个位置

        @param {object} stream_obj - _init_stream生成的流对象

        @throws {StopIteration} - 如果到了流结尾,抛出该异常

        """
        pass

    @staticmethod
    @abstractmethod
    def _close_stream(stream_obj):
        """
        抽象方法,关闭流对象(与_init_stream对应),在中止流处理时调用

        @param {object} stream_obj - _init_stream生成的流对象

        """
        pass

    @staticmethod
    @abstractmethod
    def _seek(stream_obj, position):
        """
        抽象方法,移动到流的指定位置

        @param {object} stream_obj - _init_stream生成的流对象
        @param {object} position - 要移动到的位置(具体类型由实现类确定)

        @throws {AttributeError} - 当流处理不支持向前移动,但操作需要向前移动,则抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        pass

    @staticmethod
    @abstractmethod
    def _move_next(stream_obj, step=1):
        """
        抽象方法,流从当前位置向后移动指定步数

        @param {object} stream_obj - _init_stream生成的流对象
        @param {int} step=1 - 要移动的步数

        @throws {AttributeError} - 流不支持移动时,抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        pass

    @staticmethod
    @abstractmethod
    def _move_forward(stream_obj, step=1):
        """
        抽象方法,流从当前位置向前移动指定步数

        @param {object} stream_obj - _init_stream生成的流对象
        @param {int} step=1 - 要移动的步数

        @throws {AttributeError} - 流不支持移动时,抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        pass

    @staticmethod
    @abstractmethod
    def _current_position(stream_obj):
        """
        抽象方法,获取当前流的位置信息

        @param {object} stream_obj - _init_stream生成的流对象

        @returns {object} - 返回流对象的当前位置(具体类型由实现类确定)

        """
        pass

    #############################
    # 对外的通用流处理函数
    #############################
    def start_stream(self, stream_tag='default', is_sync=True, is_pause=False,
                     seek_position=None, move_next_step=None, move_forward_step=None, **kwargs):
        """
        启动指定的流数据处理

        @param {string} stream_tag='default' - 所启动的流处理标签,用于后续调用stop_stream的时候使用
        @param {bool} is_sync=True - True-同步完成,待流结束后才退出函数; False-异步处理,新启动线程执行流处理,函数直接返回
        @param {bool} is_pause=False - 启动时是否暂停流处理(便于调用其他函数进行移动位置,仅在is_sync为False时有效)
        @param {int} seek_position=None - 执行流处理前先移动到指定的位置(与move_next_step、move_forward_step不能共存)
        @param {int} move_next_step=None - 执行流处理前先向后移动指定步数(seek_position、move_forward_step不能共存)
        @param {int} move_forward_step=None - 执行流处理前先向前移动指定步数(与move_next_step、seek_position不能共存)
        @param {**kwargs} kwargs - 启动流处理的动态key-value方式参数

        @throws {KeyError} - stream_tag已经存在时,抛出该异常

        """
        self._stream_list_lock.acquire()
        try:
            if stream_tag in self._stream_list.keys():
                # 流处理标识不能重复
                raise KeyError(u'处理标识已存在')

            # 打开流对象
            _stream_obj = self._init_stream(**kwargs)
            self._stream_list[stream_tag] = _stream_obj
            self._stream_list_tag[stream_tag] = (False, is_pause)
        finally:
            self._stream_list_lock.release()

        # 处理流位置
        if seek_position is not None:
            self._seek(stream_obj=_stream_obj, position=seek_position)
        elif move_next_step is not None:
            self._move_next(stream_obj=_stream_obj, step=move_next_step)
        elif move_forward_step is not None:
            self._move_forward(stream_obj=_stream_obj, step=move_forward_step)

        if is_sync:
            # 同步模式,直接处理流
            self._stream_deal_fun(stream_tag=stream_tag)
        else:
            # 异步模式,通过线程方式处理
            _dealer_thread = threading.Thread(
                target=self._stream_deal_fun,
                args=(1, stream_tag),
                name='Thread-Deal-Fun'
            )
            _dealer_thread.setDaemon(True)
            _dealer_thread.start()

    def stop_stream(self, stream_tag='default', is_wait=True):
        """
        关闭指定标签的流处理

        @param {string} stream_tag='default' - 需要关闭的流处理标签
        @param {bool} is_wait=True - 是否等待流关闭后再返回

        @throws {AttributeError} - 当keep_wait_data为False时,会自动关闭流,调用本方法应直接抛出异常
        @throws {KeyError} - 当传入的流标识不存在时抛出该异常

        """
        self._stream_list_lock.acquire()
        try:
            if not self._keep_wait_data:
                # 自动关闭流,参数无效
                raise AttributeError(u'流参数为自动关闭,不允许手工关闭')

            if stream_tag not in self._stream_list.keys():
                # 流标识不存在
                raise KeyError(u'处理标识不存在')

            # 设置停止标签
            self._stream_list_tag[stream_tag] = (True, self._stream_list_tag[stream_tag][1])
        finally:
            self._stream_list_lock.release()

        # 是否等待关闭后才返回
        if is_wait:
            while True:
                if stream_tag not in self._stream_list.keys():
                    break
                RunTool.sleep(0.01)

    def pause_stream(self, stream_tag='default'):
        """
        暂停指定标签的流处理

        @param {string} stream_tag='default' - 需要暂停的流处理标签

        @throws {KeyError} - 当传入的流标识不存在时抛出该异常

        """
        self._stream_list_lock.acquire()
        try:
            if stream_tag not in self._stream_list.keys():
                # 流标识不存在
                raise KeyError(u'Unknow stream_tag!')

            # 设置暂停标签
            self._stream_list_tag[stream_tag] = (self._stream_list_tag[stream_tag][0], True)
        finally:
            self._stream_list_lock.release()

    def resume_stream(self, stream_tag='default'):
        """
        恢复指定标签的流处理

        @param {string} stream_tag='default' - 需要恢复的流处理标签

        @throws {KeyError} - 当传入的流标识不存在时抛出该异常

        """
        self._stream_list_lock.acquire()
        try:
            if stream_tag not in self._stream_list.keys():
                # 流标识不存在
                raise KeyError(u'Unknow stream_tag!')

            # 设置暂停标签
            self._stream_list_tag[stream_tag] = (self._stream_list_tag[stream_tag][0], False)
        finally:
            self._stream_list_lock.release()

    def stop_stream_force(self, is_wait=True):
        """
        强制关闭当前所有正在处理的流

        @param {bool} is_wait=True - 是否等待所有流关闭后再返回

        """
        self._force_stop_tag = True
        if is_wait:
            # 检查是否都已停止
            while True:
                if len(self._stream_list_tag.keys()) == 0:
                    break
                RunTool.sleep(0.01)

    def seek(self, position, stream_tag='default'):
        """
        移动到流的指定位置

        @param {int} position - 要移动到的位置(注意位置从0开始)
        @param {string} stream_tag='default' - 需要处理的流处理标签

        @throws {KeyError} - 当传入的流标识不存在时抛出该异常
        @throws {AttributeError} - 当流处理不支持向前移动,但操作需要向前移动,则抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        if not self._move_forward:
            # 不支持向前移动
            raise AttributeError(u'This stream unsupport move forward!')

        self._stream_list_lock.acquire()
        try:
            if stream_tag not in self._stream_list.keys():
                # 流处理标识不能重复
                raise KeyError(u'Unknow stream_tag!')

            # 获取流对象
            _stream_obj = self._stream_list[stream_tag]
        finally:
            self._stream_list_lock.release()

        # 执行移动
        self._seek(stream_obj=_stream_obj, position=position)

    def move_next(self, step=1, stream_tag='default'):
        """
        流从当前位置向后移动指定步数

        @param {int} step=1 - 要移动的步数
        @param {string} stream_tag='default' - 需要处理的流处理标签

        @throws {KeyError} - 当传入的流标识不存在时抛出该异常
        @throws {AttributeError} - 流不支持移动时,抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        self._stream_list_lock.acquire()
        try:
            if stream_tag not in self._stream_list.keys():
                # 流处理标识不能重复
                raise KeyError(u'Unknow stream_tag!')

            # 获取流对象
            _stream_obj = self._stream_list[stream_tag]
        finally:
            self._stream_list_lock.release()

        # 执行移动
        self._move_next(stream_obj=_stream_obj, step=step)

    def move_forward(self, step=1, stream_tag='default'):
        """
        流从当前位置向前移动指定步数

        @param {int} step=1 - 要移动的步数
        @param {string} stream_tag='default' - 需要处理的流处理标签

        @throws {KeyError} - 当传入的流标识不存在时抛出该异常
        @throws {AttributeError} - 流不支持移动时,抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        self._stream_list_lock.acquire()
        try:
            if stream_tag not in self._stream_list.keys():
                # 流处理标识不能重复
                raise KeyError(u'stream_tag has exists!')

            # 获取流对象
            _stream_obj = self._stream_list[stream_tag]
        finally:
            self._stream_list_lock.release()

        # 执行移动
        self._move_forward(stream_obj=_stream_obj, step=step)

    @classmethod
    def stream_decorator(cls, stop_by_excepiton=False, logger=None, dealer_exception_fun=None, stream_closed_fun=None,
                         stream_tag='stream_dealer', is_sync=True, seek_position=None,
                         move_next_step=None, move_forward_step=None):
        """
        流处理修饰函数, 通过该函数来简单实现流定义及处理

        @param {bool} stop_by_excepiton=False - 当出现异常时是否中止流处理
        @param {object} logger=None - 出现错误时进行error输出的日志类(需实现error方法),None代表不输出日志
        @param {function} dealer_exception_fun=None - 流处理异常时执行的通知函数,函数有6个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            deal_obj : object
            position : object 正在处理的流对象的位置
            dealer_handle : fun 出现异常时所执行的处理函数对象
            error_obj : object 异常对象,sys.exc_info()
            trace_str : string 异常的堆栈信息
        @param {function} stream_closed_fun=None - 流处理结束时执行的通知函数,函数有2个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            position : object 正在处理的流对象的位置
            closed_status : EnumStreamClosedStatus 关闭状态
        @param {string} stream_tag='stream_dealer' - 所启动的流处理标签,用于后续调用stop_stream的时候使用
        @param {bool} is_sync=True - True-同步完成,待流结束后才退出函数; False-异步处理,新启动线程执行流处理,函数直接返回
        @param {int} seek_position=None - 执行流处理前先移动到指定的位置(与move_next_step、move_forward_step不能共存)
        @param {int} move_next_step=None - 执行流处理前先向后移动指定步数(seek_position、move_forward_step不能共存)
        @param {int} move_forward_step=None - 执行流处理前先向前移动指定步数(与move_next_step、seek_position不能共存)

        @example
            @BaseStream.stream_decorator(stop_by_excepiton=True)
            def dealer_fun(deal_obj, position, **kwargs):
                # 进行流对象处理,deal_obj为传入的流对象,kwargs为函数自身的传入参数
                pass

            # 然后在实际要执行流处理的地方,启动流处理
            dealer_fun(None, 0, key1=1, key2=2)

        """
        def dealer(func):
            def dealer_args(deal_obj, position, **kwargs_dealer):
                # 打开流对象
                _stream_obj = cls._init_stream(**kwargs_dealer)

                # 处理流位置
                if seek_position is not None:
                    cls._seek(stream_obj=_stream_obj, position=seek_position)
                elif move_next_step is not None:
                    cls._move_next(stream_obj=_stream_obj, step=move_next_step)
                elif move_forward_step is not None:
                    cls._move_forward(stream_obj=_stream_obj, step=move_forward_step)

                if is_sync:
                    # 同步模式,直接处理流
                    cls._stream_deal_fun_decorator(tid=0, stream_obj=_stream_obj, stop_by_excepiton=stop_by_excepiton,
                                                   logger=logger, dealer_exception_fun=dealer_exception_fun,
                                                   stream_closed_fun=stream_closed_fun, stream_tag=stream_tag,
                                                   dealer_fun=func, **kwargs_dealer)
                else:
                    # 异步模式,通过线程方式处理
                    _dealer_thread = threading.Thread(
                        target=cls._stream_deal_fun_decorator,
                        args=(1, _stream_obj, stop_by_excepiton, logger, dealer_exception_fun,
                              stream_closed_fun, stream_tag, func),
                        kwargs=kwargs_dealer,
                        name='Thread-Decorator-Deal-Fun'
                    )
                    _dealer_thread.setDaemon(True)
                    _dealer_thread.start()
            return dealer_args
        return dealer


class StringStream(BaseStream):
    """
    字符串流, 继承BaseStream,实现字符串的流处理

    @param {bool} stop_by_excepiton=False - 当出现异常时是否中止流处理
    @param {object} logger=None - 出现错误时进行error输出的日志类(需实现error方法),None代表不输出日志
    @param {function} dealer_exception_fun=None - 流处理异常时执行的通知函数,函数有6个入参:
        stream_tag : string 流标识
        stream_obj : object 流对象
        deal_obj : object 正在处理的流对象
        position : object 正在处理的流对象的位置
        dealer_handle : fun 出现异常时所执行的处理函数对象
        error_obj : object 异常对象,sys.exc_info()
        trace_str : string 异常的堆栈信息
    @param {function} stream_closed_fun=None - 流处理结束时执行的通知函数,函数有2个入参:
        stream_tag : string 流标识
        stream_obj : object 流对象
        position : object 正在处理的流对象的位置
        closed_status : EnumStreamClosedStatus 关闭状态

    @example
        1、使用实例对象的方法(str_obj为要处理的字符串)
        _stream = StringStream(stop_by_excepiton=False, logger=None, dealer_exception_fun=None, stream_closed_fun=None)
        _stream.add_dealer(dealer_fun1, dealer_fun2, ....)
        _stream.start_stream(stream_tag='default', is_sync=True, is_pause=False,
                     seek_position=None, move_next_step=None, move_forward_step=None, str_obj='my test string')

        2、使用修饰符的方法(str_obj为要处理的字符串)
        @StringStream.stream_decorator(stop_by_excepiton=False, logger=None, dealer_exception_fun=None, stream_closed_fun=None,
                         stream_tag='stream_dealer', is_sync=True, seek_position=None,
                         move_next_step=None, move_forward_step=None)
        def string_stream_dealer_fun(deal_obj=None, position='', str_obj='', self_para1='', self_para2=''):
            do stream deal

        # 启动流处理
        string_stream_dealer_fun(None, 0, str_obj='test', self_para1='', self_para2='')

    """

    #############################
    # 重载构造函数
    #############################
    def __init__(self, stop_by_excepiton=False, logger=None, dealer_exception_fun=None, stream_closed_fun=None):
        """
        重载构造函数,去掉无需设置的参数

        @param {bool} stop_by_excepiton=False - 当出现异常时是否中止流处理
        @param {object} logger=None - 出现错误时进行error输出的日志类(需实现error方法),None代表不输出日志
        @param {function} dealer_exception_fun=None - 流处理异常时执行的通知函数,函数有6个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            deal_obj : object 正在处理的流对象
            position : object 正在处理的流对象的位置
            dealer_handle : fun 出现异常时所执行的处理函数对象
            error_obj : object 异常对象,sys.exc_info()
            trace_str : string 异常的堆栈信息
        @param {function} stream_closed_fun=None - 流处理结束时执行的通知函数,函数有2个入参:
            stream_tag : string 流标识
            stream_obj : object 流对象
            position : object 正在处理的流对象的位置
            closed_status : EnumStreamClosedStatus 关闭状态

        """
        BaseStream.__init__(self, back_forward=True, keep_wait_data=False, stop_by_excepiton=stop_by_excepiton,
                            logger=logger, dealer_exception_fun=dealer_exception_fun,
                            stream_closed_fun=stream_closed_fun)

    #############################
    # 需继承类实现的内部处理函数
    #############################
    @staticmethod
    def _init_stream(**kwargs):
        """
        根据传入参数初始化流对象(实现类自定义,也可以是标识),基类将保留该对象并供后续流处理函数调用

        @param {string} str_obj - 需进行流处理的字符串对象

        @returns {object} - 返回具有两个属性的object对象:
            obj : string 流处理对象
            pos : int 流当前位置

        """
        _stream_obj = NullObj()
        _stream_obj.obj = kwargs['str_obj']
        _stream_obj.pos = 0
        return _stream_obj

    @staticmethod
    def _next(stream_obj):
        """
        从流中获取下一个对象,并将流指针指向下一个位置

        @param {object} stream_obj - _init_stream生成的流对象

        @returns {string} - 获取到的下一个位置的字符

        @throws {StopIteration} - 如果到了流结尾,抛出该异常

        """
        if stream_obj.pos + 1 > len(stream_obj.obj):
            # 已经到结尾了
            raise StopIteration

        # 更新位置
        stream_obj.pos = stream_obj.pos + 1
        return stream_obj.obj[stream_obj.pos - 1: stream_obj.pos]

    @staticmethod
    def _close_stream(stream_obj):
        """
        关闭流对象(与_init_stream对应),在中止流处理时调用

        @param {object} stream_obj - _init_stream生成的流对象

        """
        del stream_obj

    @staticmethod
    def _seek(stream_obj, position):
        """
        移动到流的指定位置

        @param {object} stream_obj - _init_stream生成的流对象
        @param {int} position - 要移动到的位置(注意位置从0开始)

        @throws {AttributeError} - 当流处理不支持向前移动,但操作需要向前移动,则抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        if position < 0 or position >= len(stream_obj.obj):
            # 已经超过结尾
            raise EOFError(u'Position not legal!')
        # 设置位置
        stream_obj.pos = position

    @staticmethod
    def _move_next(stream_obj, step=1):
        """
        流从当前位置向后移动指定步数

        @param {object} stream_obj - _init_stream生成的流对象
        @param {int} step=1 - 要移动的步数

        @throws {AttributeError} - 当流处理不支持向前移动,但操作需要向前移动,则抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        _pos = stream_obj.pos + step
        if _pos < 0 or _pos >= len(stream_obj.obj):
            # 已经超过结尾
            raise EOFError(u'Position not legal!')
        # 设置位置
        stream_obj.pos = _pos

    @staticmethod
    def _move_forward(stream_obj, step=1):
        """
        流从当前位置向前移动指定步数

        @param {object} stream_obj - _init_stream生成的流对象
        @param {int} step=1 - 要移动的步数

        @throws {AttributeError} - 当流处理不支持向前移动,但操作需要向前移动,则抛出该异常
        @throws {EOFError} - 当移动的位置超过流本身数据位置,抛出EOFError异常

        """
        _pos = stream_obj.pos - step
        if _pos < 0 or _pos >= len(stream_obj.obj):
            # 已经超过结尾
            raise EOFError(u'Position not legal!')
        # 设置位置
        stream_obj.pos = _pos

    @staticmethod
    def _current_position(stream_obj):
        """
        获取当前流的位置信息

        @param {object} stream_obj - _init_stream生成的流对象

        @returns {int} - 返回流对象的当前位置

        """
        return stream_obj.pos


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
