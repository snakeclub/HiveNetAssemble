#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
重定向标准界面输出的处理模块

@module redirect_stdout
@file redirect_stdout.py

"""

import os
import sys
import threading
import traceback
import queue
from enum import Enum
# 根据当前文件路径将包路径纳入,在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.utils.run_tool import RunTool


__MOUDLE__ = 'redirect_stdout'  # 模块名
__DESCRIPT__ = u'重定向标准界面输出的处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.04'  # 发布日期


class EnumOriginalStdoutWriteType(Enum):
    """
    对原始的stdout的输出方式

    @enum {string}

    """
    Before = 'Before'  # 在重定向处理前输出
    After = 'After'  # 在重定向处理后输出
    NoWrite = 'NoWrite'  # 不输出


class EnumRedirectOutputHandlerType(Enum):
    """
    重定向输出句柄类型
    @enum {string}
    """
    Consloe = 'Consloe'  # 屏幕输出句柄
    File = 'File'  # 文件输出句柄
    String = 'String'  # 文本对象输出句柄
    StringList = 'StringList'  # 文本数组输出句柄
    Logger = 'Logger'  # 日志输出对象句柄


class RedirectOutputHandler(object):
    """
    输出重定向句柄
    定义RedirectOutput类处理所需的输出句柄,实现真正的输出逻辑,使用方法有两类:
        1、直接使用该类生成默认的重定向句柄对象
        2、自定义输出句柄,继承该类,重载write和flush函数

    @param {EnumRedirectOutputHandlerType} handler_type=EnumRedirectOutputHandlerType.Consloe - 输出句柄类型
    @param {object} output_obj=None - 输出对象,根据handler_type不同传入不同参数
        Consloe :  无需传入
        File :  string, 传入文件名路径
        String : list[0]=string,传入初始字符串,后续在该基础上逐步扩展(注意,是一个长度为1的数组)
        StringList :  list(),传入初始字符对象列表
        Logger : 日志对象,传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象,但应实现info的标准方法
            注意: Logger对象不支持清空flush方法
    @param {bool} is_flush=False - 初始化时是否清空输出缓存(清空输出对象)
    @param {string} encoding='utf-8' - 输出字符编码

    """

    #############################
    # 私有变量
    #############################
    _handler_type = None  # 句柄类型
    _output_obj = ''  # 输出对象
    _encoding = ''  # 编码方式

    #############################
    # 公共函数
    #############################
    def __init__(self, handler_type=EnumRedirectOutputHandlerType.Consloe, output_obj=None,
                 is_flush=False, encoding='utf-8'):
        """
        构造函数

        @param {EnumRedirectOutputHandlerType} handler_type=EnumRedirectOutputHandlerType.Consloe - 输出句柄类型
        @param {object} output_obj=None - 输出对象,根据handler_type不同传入不同参数
            Consloe :  无需传入
            File :  string, 传入文件名路径
            String : list[0]=string,传入初始字符串,后续在该基础上逐步扩展(注意,是一个长度为1的数组)
            StringList :  list(),传入初始字符对象列表
            Logger : 日志对象,传入对象需满足:
                1、标准logging的logger对象
                2、自定义的日志类对象,但应实现info的标准方法
                注意: Logger对象不支持清空flush方法
        @param {bool} is_flush=False - 初始化时是否清空输出缓存(清空输出对象)
        @param {string} encoding='utf-8' - 输出字符编码

        """
        self._handler_type = handler_type
        self._output_obj = output_obj
        self._encoding = encoding
        if is_flush:
            self.flush()

    def write(self, data):
        """
        输出函数,将数据写入输出对象(实现标准输出必须包括的函数)

        @param {string} data - 要输出的文本

        """
        if self._handler_type == EnumRedirectOutputHandlerType.Consloe:
            sys.__stdout__.write(data)
        elif self._handler_type == EnumRedirectOutputHandlerType.String:
            self._output_obj[0] += data  # 不用自己加换行
        elif self._handler_type == EnumRedirectOutputHandlerType.StringList:
            self._output_obj.append(data)
        elif self._handler_type == EnumRedirectOutputHandlerType.Logger:
            # 日志方式
            self._output_obj.info(data)
        else:
            # 文件模式,追加到结尾
            try:
                with open(file=self._output_obj, mode='a+', encoding=self._encoding) as _file:
                    _file.write(data)  # 不用自己加换行
                    _file.flush()
            except Exception:
                # 出现异常,输出异常信息到界面
                sys.stderr.write(traceback.format_exc())

    def flush(self):
        """
        清空输入缓存(清空输出对象, 实现标准输出必须包括的函数)

        """
        if self._handler_type == EnumRedirectOutputHandlerType.Consloe:
            sys.__stdout__.flush()
        elif self._handler_type == EnumRedirectOutputHandlerType.String:
            self._output_obj[0] = ''
        elif self._handler_type == EnumRedirectOutputHandlerType.StringList:
            self._output_obj.clear()
        elif self._handler_type == EnumRedirectOutputHandlerType.Logger:
            # 日志类不清空
            pass
        else:
            # 文件模式,覆盖文件
            try:
                with open(file=self._output_obj, mode='w', encoding=self._encoding):
                    pass
            except Exception:
                # 出现异常,输出异常信息到界面
                sys.stderr.write(traceback.format_exc())


class RedirectOutput(object):
    """
    输出重定向类
    (参考材料: @see https://www.cnblogs.com/turtle-fly/p/3280519.html)

    @param {bool} auto_start=False - 是否初始化时自动启动重定向处理
    @param {object} original_stdout=None - 初始输出对象,如果为None则记录为sys.stdout
    @param {EnumOriginalStdoutWriteType} original_stdout_write_type=EnumOriginalStdoutWriteType.NoWrite - 对原始的stdout的输出处理方式
    @param {bool} is_asyn=False - 是否异步处理(异步处理通过队列缓存通过线程写,可以快速返回结果)
    @param {RedirectOutputHandler[]} output_handlers=list() - 需要重定向到的输出对象(RedirectOutputHandler)列表
    @param {bool} wait_write_end_when_asyn=False - 异步模式关闭重定向时是否等待全部对象写完

    """

    #############################
    # 内部变量
    #############################

    _original_stdout = None  # 登记初始的输出对象,用户关闭重定向时恢复对象
    _original_stdout_write_type = None  # 对原始的stdout的输出处理方式
    _write_lock = None  # 进行输出信息处理的线程锁,支持多线程
    _is_asyn = False  # 是否通过后台线程执行(快速返回)
    _output_handlers = None  # 重定向输出句柄清单
    _wait_write_end_when_asyn = False  # 异步模式关闭重定向时是否等待全部对象写完
    _is_started = False  # 标记是否启动了重定向处理
    _buffer = None  # 输出对象数据缓存队列,FIFO队列
    _is_bg_thread_running = False  # 后台处理线程是否在执行中
    _bg_thread_stop = False  # 通知后台线程停止的标志变量

    #############################
    # 公共函数
    #############################

    def __init__(self, auto_start=True, original_stdout=None,
                 original_stdout_write_type=EnumOriginalStdoutWriteType.Before,
                 is_asyn=False, output_handlers=list(), wait_write_end_when_asyn=False
                 ):
        """
        构造函数

        @param {bool} auto_start=False - 是否初始化时自动启动重定向处理
        @param {object} original_stdout=None - 初始输出对象,如果为None则记录为sys.stdout
        @param {EnumOriginalStdoutWriteType} original_stdout_write_type=EnumOriginalStdoutWriteType.NoWrite - 对原始的stdout的输出处理方式
        @param {bool} is_asyn=False - 是否异步处理(异步处理通过队列缓存通过线程写,可以快速返回结果)
        @param {RedirectOutputHandler[]} output_handlers=list() - 需要重定向到的输出对象(RedirectOutputHandler)列表
        @param {bool} wait_write_end_when_asyn=False - 异步模式关闭重定向时是否等待全部对象写完

        """
        # 初始化变量
        self._write_lock = threading.RLock()  # 进行输出信息处理的线程锁,支持多线程
        self._output_handlers = list()  # 重定向输出句柄清单
        # 赋值
        self._buffer = ''
        if original_stdout is None:
            self._original_stdout = sys.stdout
        else:
            self._original_stdout = original_stdout
        self._original_stdout_write_type = original_stdout_write_type
        self.is_asyn = is_asyn
        self._output_handlers = output_handlers
        self._wait_write_end_when_asyn = wait_write_end_when_asyn
        if auto_start:
            # 自动启动输出重定向
            self.start_redirect()

    def write(self, data):
        """
        输出函数(实现标准输出必须包括的函数)

        @param {string} data - 要输出的文本

        """
        if self._is_started:
            # 只有在启动的时候进行处理
            if self._is_asyn:
                # 异步模式,直接压入队列即可,等待后台线程处理
                self._buffer.put(data)
            else:
                # 同步模式,直接处理,注意加上线程锁
                self._write_lock.acquire()
                try:
                    self.__write(data)
                finally:
                    self._write_lock.release()

    def flush(self):
        """
        清空输入缓存(实现标准输出必须包括的函数)

        """
        if self._is_started:
            # 只有在启动的时候进行处理
            if self._is_asyn:
                # 异步模式,清空队列
                self._buffer.clear()
            # 清空输出缓存
            self._original_stdout.flush()
            self.__flush_handlers()

    def start_redirect(self):
        """
        启动重定向处理

        """
        self._write_lock.acquire()
        try:
            if self._is_asyn:
                # 异步模式,建立缓存队列
                self._buffer = queue.Queue()
                # 启动后台处理线程
                self._bg_thread_stop = False
                _thread = threading.Thread(target=self.__bg_thread_fun)
                _thread.start()
                print('start ok')

            # 启动
            self._is_started = True
            sys.stdout = self  # 将标准输出指向自己
        finally:
            self._write_lock.release()

    def stop_redirect(self):
        """
        停止重定向处理

        """
        self._write_lock.acquire()
        try:
            # 先直接重定向回原输出,保证最新的输出到原始输出对象
            sys.stdout = self._original_stdout
            if self._is_asyn:
                # 异步模式
                self._bg_thread_stop = True  # 通知后台线程停止
                # 等待线程自动停止
                while(self._is_bg_thread_running):
                    RunTool.sleep(0.01)
            self._is_started = False  # 标记重定向关闭
        finally:
            self._write_lock.release()

    #############################
    # 内部处理函数
    #############################

    def __write_to_handlers(self, data):
        """
        写入输出到清单中的缓存对象

        @param {string} data - 要输出的内容

        """
        for _handler in self._output_handlers:
            _handler.write(data)

    def __write(self, data):
        """
        写入输出信息到缓存对象及原输出对象

        @param {string} data - 要输出的内容

        """
        if self._original_stdout_write_type == EnumOriginalStdoutWriteType.Before:
            # 重定向前输出
            self._original_stdout.write(data)
            self.__write_to_handlers(data)
        elif self._original_stdout_write_type == EnumOriginalStdoutWriteType.After:
            # 重定向后输出
            self.__write_to_handlers(data)
            self._original_stdout.write(data)
        else:
            # 只重定向
            self.__write_to_handlers(data)

    def __flush_handlers(self):
        """
        清空清单中的缓存对象

        """
        for _handler in self._output_handlers:
            _handler.flush()

    def __bg_thread_fun(self):
        """
        后台输出的线程执行函数

        """
        self._is_bg_thread_running = True
        while(True):
            print('__bg_thread_fun')
            try:
                if self._bg_thread_stop:
                    # 收到停止标志,结束线程处理,注意如果wait_write_end_when_asyn参数为True,则需要写完
                    if not self._wait_write_end_when_asyn or self._buffer.empty():
                        break
                # 尝试从队列获取要写的对象
                if self._buffer.empty():
                    # 没有数据,下一次循环
                    RunTool.sleep(0.1)
                else:
                    data = self._buffer.get(False)
                    self.__write(data)
            except Exception:
                # 执行出现异常时不退出处理
                RunTool.sleep(0.1)
                continue
        # 线程自然消亡
        self._is_bg_thread_running = False


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
