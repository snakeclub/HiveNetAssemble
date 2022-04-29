#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
运行参数处理通用工具

@module run_tool
@file run_tool.py

"""

import sys
import os
import inspect
import ctypes
import subprocess
import traceback
import logging
import platform
from contextlib import contextmanager
import asyncio
from inspect import isawaitable
from typing import Any
try:
    from gevent import sleep
except ImportError:
    from time import sleep

try:
    # 支持嵌套异步调用处理
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.utils.file_tool import FileTool


__MOUDLE__ = 'run_tool'  # 模块名
__DESCRIPT__ = u'运行参数处理通用工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


# 全局变量
# 用于存储打开的单进程控制文件句柄的字典( dict)
# key为文件路径, value为句柄变量
# 该变量为全局变量, 以支持在不同线程间访问
SINGLE_PROCESS_PID_FILE_LIST = dict()


# 全局变量
# 用于存储全局变量的值
# key为全局变量名( string) , value为全局变量的值
RUNTOOL_GLOBAL_VAR_LIST = dict()


class RunTool(object):
    """
    运行参数处理通用类
    提供各类运行环境处理相关的常用工具函数( 静态方法)

    """
    #############################
    # 系统信息获取
    #############################
    @classmethod
    def platform_info(cls) -> dict:
        """
        获取平台信息

        @returns {dict} - 平台信息字典
            platform - 操作系统平台信息(sys.platform), win32, cygwin, linux, darwin
            machine - 机器类型(platform.machine()), i386, x86, x86_64, AMD64, arm64
            bits - 操作系统位数(platform.architecture()), 32bit, 64bit
            system - 操作系统名(platform.system()), Linux, Windows, Darwin
            release - 操作系统发行版本(platform.release()), 2.0.0, nt
            node - 网络机器名(platform.node())
            platform_alias - 操作系统版本信息(platform.platform()), Windows-7-6.1.7601-SP1, macOS-11.4-arm64-arm-64bit
        """
        _uname = platform.uname()
        platform.system_alias
        _info = {
            'platform': sys.platform,
            'machine': _uname.machine,
            'bits': platform.architecture()[0],
            'system': _uname.system,
            'release': _uname.release,
            'node': _uname.node,
            'platform_alias': platform.platform()
        }
        return _info

    #############################
    # 全局变量
    #############################

    @staticmethod
    def set_global_var(key, value):
        """
        设置全局变量的值, 后续可以通过Key获取到指定的值, 如果如果key存在将覆盖

        @param {string} key - 要设置的全局变量key值
        @param {object} value - 要设置的全局变量值

        """
        global RUNTOOL_GLOBAL_VAR_LIST
        RUNTOOL_GLOBAL_VAR_LIST[key] = value

    @staticmethod
    def get_global_var(key, default=None):
        """
        根据key获取全局变量的值, 如果找不到key则返回None

        @param {string} key - 要获取的全局变量key值
        @param {object} default=None - 获取不到返回的默认值

        @returns {object} - 全局变量的值, 如果找不到key则返回None

        """
        global RUNTOOL_GLOBAL_VAR_LIST
        if key in RUNTOOL_GLOBAL_VAR_LIST.keys():
            return RUNTOOL_GLOBAL_VAR_LIST[key]
        else:
            return default

    @staticmethod
    def del_global_var(key):
        """
        删除key值对应的全局变量

        @param {string} key - 要删除的全局变量key值

        """
        global RUNTOOL_GLOBAL_VAR_LIST
        if key in RUNTOOL_GLOBAL_VAR_LIST.keys():
            del RUNTOOL_GLOBAL_VAR_LIST[key]

    @staticmethod
    def del_all_global_var():
        """
        清空所有全局变量

        """
        global RUNTOOL_GLOBAL_VAR_LIST
        RUNTOOL_GLOBAL_VAR_LIST.clear()

    #############################
    # 参数/变量处理
    #############################
    @staticmethod
    def get_kv_opts():
        """
        获取Key=Value格式的命令行输入参数

        @returns {dict} - 命令行参数字典: key为参数名, value为参数值

        @example
            命令行# python ggeneric.py key1=value1 key2=value2 key3="value 3" "key 4"=value4 "key 5"="value 5"
            input_para = RunTools.get_kv_opts()

        """
        # 建立要返回的字典
        _dict = {}
        # 遍历参数
        i = 1
        _argv_count = len(sys.argv)
        while i < _argv_count:
            _pair = str(sys.argv[i]).split("=")
            _key = _pair[0]
            _value = ""
            if len(_pair) > 1:
                _value = sys.argv[i][len(_key) + 1:]
            _dict[_key] = _value
            i = i + 1
        return _dict

    @staticmethod
    def var_defined(name_str):
        """
        判断变量是否已定义

        @param {string} name_str - 变量名( 注意是名字字符串, 不是传入变量)

        @returns {bool} - 是否已定义, True-已定义, False-未定义

        """
        try:
            type(eval(name_str))
        except:
            return False
        else:
            return True

    #############################
    # 日志处理
    #############################
    @staticmethod
    def set_global_logger(logger):
        """
        设置全局使用的logger对象

        @param {object} logger - logger对象,传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现info、warning、error等标准方法

        """
        RunTool.set_global_var('CALL_CHAIN_TOOL_LOGGER', logger)

    @staticmethod
    def get_global_logger():
        """
        获取全局使用的logger对象

        @returns {object} - 全局使用的logger对象

        """
        return RunTool.get_global_var('CALL_CHAIN_TOOL_LOGGER')

    #############################
    # 命令行执行
    #############################
    @classmethod
    def exec_sys_cmd(cls, cmd: str, shell_encoding: str = None,
                     stop_var: list = None, use_stop_signal: int = None):
        """
        执行系统命令

        @param {str} cmd - 要执行的命令
        @param {str} shell_encoding=None - 传入指定的编码
            注: 如果不传入, 尝试获取全局变量 SHELL_ENCODING, 如果也找不到, 则默认为'utf-8'
        @param {list} stop_var=None - 用于在运行过程中在外部设置停止标志的列表变量, 第一个值为True时停止线程
        @param {int} use_stop_signal=None - 使用指定signal进行中止, 例如 signal.CTRL_C_EVENT

        @returns {(int, list)} - 返回命令执行结果数组, 第一个为 exit_code, 0代表成功; 第二个为输出信息行数组
        """
        _shell_encoding = shell_encoding
        if _shell_encoding is None:
            _shell_encoding = cls.get_global_var('SHELL_ENCODING', default='utf-8')

        _sp = subprocess.Popen(
            cmd, close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True
        )

        # 循环等待执行完成
        _exit_code = None
        _info_str = ''
        while True:
            # 判断是否中止执行
            if stop_var is not None and len(stop_var) > 0:
                if stop_var[0]:
                    # 需要强制结束进程
                    if use_stop_signal is None:
                        _sp.terminate()
                    else:
                        os.kill(_sp.pid, use_stop_signal)

                    _info_str += '\nkilled with singal'
                    _exit_code = 0
                    break

            # 获取输出信息 .replace('\r', '').replace('\n', '')
            _info_str += _sp.stdout.read().decode(
                _shell_encoding
            )

            _exit_code = _sp.poll()
            if _exit_code is not None:
                # 结束, 打印异常日志
                _info_str += _sp.stdout.read().decode(_shell_encoding)
                if _exit_code != 0:
                    _info_str += _sp.stderr.read().decode(_shell_encoding)

                # 关闭输出管道
                _sp.stdout.close()
                break

            # 释放一下CPU
            cls.sleep(0.01)

        # 格式化
        if sys.platform == 'darwin':
            # mac os, \r 代表回车换行
            _info_str = _info_str.replace('\n', '').replace('\r', '\n')
        else:
            # \r 代表回车  \n 代表换行
            _info_str = _info_str.replace('\r', '')

        return (_exit_code, _info_str.split('\n'))

    @classmethod
    def exec_sys_cmd_not_output(cls, cmd: str, shell_encoding: str = None,
                                stop_var: list = None, use_stop_signal: int = None):
        """
        执行系统命令不输出信息

        @param {str} cmd - 要执行的命令
        @param {str} shell_encoding=None - 传入指定的编码
            注: 如果不传入, 尝试获取全局变量 SHELL_ENCODING, 如果也找不到, 则默认为'utf-8'
        @param {list} stop_var=None - 用于在运行过程中在外部设置停止标志的列表变量, 第一个值为True时停止线程
        @param {int} use_stop_signal=None - 使用指定signal进行中止, 例如 signal.CTRL_C_EVENT

        @returns {(int, list)} - 返回命令执行结果数组, 第一个为 exit_code, 0代表成功; 第二个为输出信息行数组
        """
        _shell_encoding = shell_encoding
        if _shell_encoding is None:
            _shell_encoding = cls.get_global_var('SHELL_ENCODING', default='utf-8')

        _sp = subprocess.Popen(
            cmd, close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True
        )

        # 循环等待执行完成
        _exit_code = None
        _info_str = ''
        while True:
            if stop_var is not None and len(stop_var) > 0:
                if stop_var[0]:
                    # 需要强制结束进程
                    if use_stop_signal is None:
                        _sp.terminate()
                    else:
                        os.kill(_sp.pid, use_stop_signal)

                    _info_str = 'killed with singal'
                    _exit_code = 0
                    break

            _exit_code = _sp.poll()
            if _exit_code is not None:
                # 结束
                if _exit_code != 0:
                    _info_str += _sp.stdout.read().decode(_shell_encoding)
                    _info_str += _sp.stderr.read().decode(_shell_encoding)

                # 关闭输出管道
                _sp.stdout.close()
                break

            # 释放一下CPU
            cls.sleep(0.01)

        if sys.platform == 'darwin':
            # mac os, \r 代表回车换行
            _info_str = _info_str.replace('\n', '').replace('\r', '\n')
        else:
            # \r 代表回车  \n 代表换行
            _info_str = _info_str.replace('\r', '')

        return (_exit_code, _info_str.split('\n'))

    #############################
    # 线程处理函数
    #############################
    @classmethod
    def sleep(cls, seconds=0):
        """
        休眠一段时间
        注: 如果有安装gevent则会使用gevent.sleep替代time.sleep

        @param {int} seconds=0 - 休眠时间, 单位为秒
        """
        return sleep(seconds=seconds)

    @classmethod
    def async_raise(cls, tid, exctype):
        """raises the exception, performs cleanup if needed"""
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

    @classmethod
    def stop_thread(cls, thread):
        cls.async_raise(thread.ident, SystemExit)

    #############################
    # 进程锁控制
    #############################
    @staticmethod
    def single_process_get_lockfile(process_name='', base_path=''):
        """
        获取进程锁处理锁文件路径
        进程锁处理的辅助函数, 获取指定进程的锁文件名( 含路径)

        @param {string} process_name='' - 进程锁的进程名, 默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径, 默认值为''；如果为''代表获取执行程序的模块文件目录

        @returns {string} - 锁文件名( 含路径)

        """
        _process_name = process_name
        _base_path = base_path
        if not len(_process_name) > 0:
            # 默认取运行的程序名
            _process_name = FileTool.get_exefile_name_no_ext()
        if not len(_base_path) > 0:
            # 默认取运行程序目录
            _base_path = FileTool.get_exefile_path() + os.sep
        else:
            _base_path = os.path.realpath(_base_path)
            if not os.path.isdir(_base_path):
                # 如果是文件的情况下, 拿文件对应的目录
                _base_path = os.path.split(os.path.realpath(_base_path))[0]
            _base_path = _base_path + os.sep
        return _base_path + _process_name + ".lock"  # 要建立锁的文件名

    @staticmethod
    def single_process_del_lockfile(process_name='', base_path=''):
        """
        强制删除进程锁文件
        进程锁处理的辅助函数, 强制删除进程锁文件

        @param {string} process_name='' - 进程锁的进程名, 默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径, 默认值为''；如果为''代表获取执行程序的模块文件目录

        """
        try:
            _lock_file = RunTool.single_process_get_lockfile(
                process_name=process_name, base_path=base_path)
            if os.path.exists(_lock_file) and os.path.isfile(_lock_file):
                os.remove(_lock_file)
        except:
            return

    @staticmethod
    def single_process_enter(process_name='', base_path='', is_try_del_lockfile=False):
        """
        获取进程锁: 如果获取失败代表锁已被其他进程占有, 可选择结束进程以控制同一时间只有一个进程执行

        @param {string} process_name='' - 进程锁的进程名, 默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径, 默认值为''；如果为''代表获取执行程序的模块文件目录
        @param {bool} is_try_del_lockfile=False - 是否尝试先删除锁文件( 可以应对强制关闭进程未自动删除锁文件的情况)

        @returns {bool} - 是否获取进程锁成功: True - 获取成功并占用锁；False - 获取失败, 应选择关闭进程

        @example
            get_process_lock = RunTool.single_process_enter("CFuntion","c:/test/")
            if not get_process_lock:
                print("已有一个进程在执行状态, 结束本进程")
                exit(1)

            try:
                do something ...
            finally:
                RunTool.single_process_exit("CFuntion","c:/test/")

        """
        global SINGLE_PROCESS_PID_FILE_LIST
        if not RunTool.var_defined("SINGLE_PROCESS_PID_FILE_LIST"):
            SINGLE_PROCESS_PID_FILE_LIST = {}
        # 要建立锁的文件名
        _lock_file = RunTool.single_process_get_lockfile(
            process_name=process_name, base_path=base_path)
        # 尝试自动先删除锁文件
        if is_try_del_lockfile:
            RunTool.single_process_del_lockfile(process_name=process_name, base_path=base_path)
        # 尝试创建锁文件
        try:
            _pid = os.open(_lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            SINGLE_PROCESS_PID_FILE_LIST[_lock_file] = _pid
        except OSError:
            return False
        else:
            return True

    @staticmethod
    def single_process_exit(process_name='', base_path=''):
        """
        结束进程锁控制:
            1、结束单进程控制, 删除锁文件；
            2、注意必须在程序执行完后一定要调用这个函数, 否则会导致一直锁住

        @param {string} process_name='' - 进程锁的进程名, 默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径, 默认值为''；如果为''代表获取执行程序的模块文件目录

        """
        global SINGLE_PROCESS_PID_FILE_LIST
        if not RunTool.var_defined("SINGLE_PROCESS_PID_FILE_LIST"):
            SINGLE_PROCESS_PID_FILE_LIST = {}
        # 要建立锁的文件名
        _lock_file = RunTool.single_process_get_lockfile(
            process_name=process_name, base_path=base_path)
        try:
            os.close(SINGLE_PROCESS_PID_FILE_LIST[_lock_file])
            os.remove(_lock_file)
            return
        except:
            raise sys.exc_info()[1]

    @staticmethod
    @contextmanager
    def single_process_with(process_name='', base_path='', is_try_del_lockfile=False,
                            logger=None, log_level=logging.WARNING, exit_code=1):
        """
        单进程控制的with简单模式,封装with模式的调用方式来实现单进程控制

        @param {string} process_name='' - 进程锁的进程名, 默认值为''；如果为''代表获取执行程序的模块名
        @param {string} base_path='' - 进程锁文件指定的路径, 默认值为''；如果为''代表获取执行程序的模块文件目录
        @param {bool} is_try_del_lockfile=False - 是否尝试先删除锁文件( 可以应对强制关闭进程未自动删除锁文件的情况)
        @param {object} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现warning、error等的标准方法
        @param {int} log_level=logging.WARNING - 需要输出的自定义日志级别
        @param {int} exit_code=1 - 控制获取进程锁失败退出的错误码定义

        @example
            with RunTools.single_process_with():
                # 以下为需要执行的程序逻辑

        """
        _get_process_lock = RunTool.single_process_enter(process_name=process_name,
                                                         base_path=base_path, is_try_del_lockfile=is_try_del_lockfile)
        if not _get_process_lock:
            if logger is not None:
                # 打印日志
                _log_str = u'已存在一个"%s"进程在执行中, 结束本进程' % process_name
                logger.log(log_level, _log_str)
            # 退出进程
            exit(exit_code)
        try:
            yield  # 处理程序逻辑
        finally:
            # 退出进程, 打印日志
            if logger is not None:
                _log_str = u'进程"%s"结束退出, 释放进程锁' % process_name
                logger.log(log_level, _log_str)
            try:
                RunTool.single_process_exit(process_name=process_name, base_path=base_path)
            except:
                # 出现异常, 写日志, 同时抛出异常
                if logger is not None:
                    _log_str = u'进程"%s"结束时释放进程锁发生异常: %s' % (process_name, traceback.format_exc())
                    logger.log(log_level, _log_str)
                raise sys.exc_info()[1]

    #############################
    # 对象处理
    #############################
    @staticmethod
    def get_parent_function_frame(call_fun_level):
        """
        获取指定层级的调用函数框架( fake_frame) , 从当前调用函数开始往逐级向上获取

        @param {int} call_fun_level - 要获取的函数名所属层级:
            -1 - 返回函数自身框架
            0 - 返回调用本函数的函数框架
            1 - 返回调用本函数的函数的上1级函数框架
            n - 返回调用本函数的函数的上n级函数框架

        @returns {fake_frame} - 返回指定层级函数的框架( fake_frame) , 可以通过fake_frame.f_code获取代码相关信息

        """
        _ret_frame = sys._getframe()  # 要返回的函数框架
        if call_fun_level < 0:
            return _ret_frame
        _index = 0
        # 循环获取上一级函数的框架
        while _index <= call_fun_level:
            _ret_frame = _ret_frame.f_back
            _index = _index + 1
        return _ret_frame

    @staticmethod
    def get_object_class(obj):
        """
        获取对象的类

        @param {object} obj - 要获取信息的对象

        @returns {class} - 返回的对象的类, 可以直接创建新对象, 例如:
            _class = get_object_class(obj)
            _newobj = _class(para='')

        """
        return obj.__class__

    @staticmethod
    def get_object_attr_list(obj):
        """
        获取对象的属性清单

        @param {object} obj - 要获取信息的对象

        @returns {list} - 返回的属性清单数组( 属性名列表)

        """
        return dir(obj)

    @staticmethod
    def get_object_class_name(obj):
        """
        获取对象的类名

        @param {object} obj - 要获取信息的对象

        @returns {string} - 返回类名

        """
        return obj.__class__.__name__

    @staticmethod
    def get_object_module_name(obj):
        """
        获取对象的模块名

        @param {object} obj - 要获取信息的对象

        @returns {string} - 返回模块名

        """
        return inspect.getmodule(obj).__name__

    @staticmethod
    def get_method_class_obj(method_object):
        """
        获取类方法对象的所在类实例对象

        @param {method} method_object - 类方法对象

        @return {object} - 类方法对象的所在类实例对象
        """
        return method_object.__self__

    @staticmethod
    def get_function_name(fun_object, is_with_class=True, is_with_module=False):
        """
        获取函数对象的定义名

        @param {function} fun_object - 函数对象
        @param {bool} is_with_class=True - 返回函数名是否含类名
        @param {bool} is_with_module=False - 返回函数名是否含模块名
            注意: 如果该参数为True, 则忽略is_with_class参数

        @return {string} - 函数定义的名字
            注意: 如果函数是类的方法( method, 非静态) 的情况下, 返回的是“类名.方法名”, 而非类实例对象的变量名
        """
        _name = ''
        if is_with_module:
            # 含模块名
            _module_name = inspect.getmodule(fun_object).__name__  # 获取函数对象的所属模块
            if _module_name not in ['__main__', 'builtins']:
                _name = _module_name + '.' + fun_object.__qualname__
            else:
                _name = fun_object.__qualname__
        elif is_with_class:
            # 包含类名, __qualname__为限定名
            _name = fun_object.__qualname__
        else:
            # 只有函数名
            _name = fun_object.__name__
        return _name

    @staticmethod
    def is_function_has_var_parameter(fun_object, var_positional=True, var_keyword=True):
        """
        检查函数是否有动态参数

        @param {function} fun_object -函数对象
        @param {bool} var_positional=True - 检查是否有类似*args的参数
        @param {bool} var_keyword=True - 检查是否有类似类似**kwargs的参数

        @return {bool} - 是否具有相应的函数
        """
        _has_para = False
        if not (var_positional or var_keyword):
            # 两个都不检查
            return _has_para

        _func_signature = inspect.signature(fun_object)
        for k, v in _func_signature.parameters.items():
            if (var_positional and str(v.kind) == 'VAR_POSITIONAL') or (var_keyword and str(v.kind) == 'VAR_KEYWORD'):
                _has_para = True
                break
        # 返回结果
        return _has_para

    @staticmethod
    def get_function_parameter_defines(fun_object):
        """
        获取函数调用参数定义信息

        @param {function} fun_object - 函数对象

        @return {list} - 调用参数定义, 每一个参数是数组的一项, 每一项的格式定义如下:
            {
                'name': para_name,  # 参数名
                'type': para_type,  # 参数类型, 取值为: POSITIONAL_OR_KEYWORD/KEYWORD_ONLY/VAR_POSITIONAL/VAR_KEYWORD
                'has_default': True/False,  # 是否有默认值
                'default': default_value  # 如果有默认值, 值为多少
                'annotation': annotation_type  # 参数声明类型, 例如str
            }
            其中type的说明如下:
            POSITIONAL_OR_KEYWORD - 参数之前没有任何类似*args的参数, 可以通过参数位置或者参数关键字进行调用
            KEYWORD_ONLY - 前面已经出现过类似*args的参数, 只能通过参数关键字进行调用
            VAR_POSITIONAL - 位置变量参数, 类似*args的定义, 允许按位置传入可变数量的参数
            VAR_KEYWORD - key-value形式的变量参数, 类似**kwargs, 允许传入可变数量的kv形式参数
        """
        _func_signature = inspect.signature(fun_object)
        _func_args = []
        # 获取函数所有参数
        for k, v in _func_signature.parameters.items():
            # 获取函数参数后, 需要判断参数类型
            # 当kind为 POSITIONAL_OR_KEYWORD, 说明在这个参数之前没有任何类似*args的参数, 那这个函数可以通过参数位置或者参数关键字进行调用
            # 这两种参数要另外做判断
            if str(v.kind) in ('POSITIONAL_OR_KEYWORD', 'KEYWORD_ONLY'):
                # 通过v.default可以获取到参数的默认值
                # 如果参数没有默认值, 则default的值为: class inspect_empty
                # 所以通过v.default的__name__ 来判断是不是_empty 如果是_empty代表没有默认值
                # 同时, 因为类本身是type类的实例, 所以使用isinstance判断是不是type类的实例
                if isinstance(v.default, type) and v.default.__name__ == '_empty':
                    _func_args.append({
                        'name': k,  # 参数名
                        'type': str(v.kind),  # 参数类型
                        'has_default': False,  # 是否有默认值
                        'default': None,  # 如果有默认值, 值为多少
                        'annotation': v.annotation  # 参数声明类型
                    })
                else:
                    _func_args.append({
                        'name': k,  # 参数名
                        'type': str(v.kind),  # 参数类型
                        'has_default': True,  # 是否有默认值
                        'default': v.default,  # 如果有默认值, 值为多少
                        'annotation': v.annotation  # 参数声明类型
                    })
            else:
                # kind为 VAR_POSITIONAL以及VAR_KEYWORD的情况
                _func_args.append({
                    'name': k,  # 参数名
                    'type': str(v.kind),  # 参数类型
                    'has_default': False,  # 是否有默认值
                    'default': None,  # 如果有默认值, 值为多少
                    'annotation': v.annotation  # 参数声明类型
                })
        # 返回调用参数定义
        return _func_args

    @staticmethod
    def get_current_function_object(frame_obj=None):
        """
        获取当前运行函数的函数对象

        @param {frameobject} frame_obj=None - 不传入frame,获取调用本函数的函数;传入则获取frame对应的函数

        @return {function} - 函数对象, 如果获取不到函数对象, 则返回None
            注意: 该方法无法获取到类的静态函数对象
        """
        # TODO(lihuijian): 该方法无法获取到类的静态函数对象, 暂时没有找到方法解决
        _obj = None
        _fun_frame = frame_obj
        if frame_obj is None:
            _fun_frame = inspect.currentframe().f_back
        # 根据frame获取函数对象
        if 'self' in _fun_frame.f_locals.keys():
            # 是类实例对象
            _code_name = _fun_frame.f_code.co_name
            _obj = getattr(_fun_frame.f_locals["self"].__class__, _code_name)
        else:
            # 静态对象
            _fun_name = inspect.getframeinfo(_fun_frame)[2]
            if _fun_name in _fun_frame.f_globals.keys():
                _obj = _fun_frame.f_globals[_fun_name]
        return _obj

    @staticmethod
    def get_current_function_name(frame_obj=None, is_with_class=True, is_with_module=False):
        """
        @param {frameobject} frame_obj=None - 不传入frame,获取调用本函数的函数;传入则获取frame对应的函数
        @param {bool} is_with_class=True - 返回函数名是否含类名
        @param {bool} is_with_module=False - 返回函数名是否含模块名
            注意: 如果该参数为True, 则忽略is_with_class参数

        @return {string} - 函数定义的名字
            注意: 如果函数是类的方法( method, 非静态) 的情况下, 返回的是“类名.方法名”, 而非类实例对象的变量名
            注意: 如果函数是类的静态函数, 只能返回函数名, 无法返回类名
        """
        _fun_name = ''
        _fun_frame = frame_obj
        if frame_obj is None:
            _fun_frame = inspect.currentframe().f_back
        _fun_obj = RunTool.get_current_function_object(frame_obj=_fun_frame)
        if _fun_obj is None:
            # TODO(lihuijian): 静态函数, 只能返回函数名, 无法返回类名
            _fun_name = inspect.getframeinfo(_fun_frame)[2]
        else:
            _fun_name = RunTool.get_function_name(
                _fun_obj, is_with_class=is_with_class, is_with_module=is_with_module)
        # 返回
        return _fun_name

    @staticmethod
    def get_current_function_parameter_defines(frame_obj=None):
        """
        获取当前运行函数的函数调用参数定义信息

        @param {frameobject} frame_obj=None - 不传入frame,获取调用本函数的函数;传入则获取frame对应的函数

        @return {list} - 调用参数定义, 每一个参数是数组的一项, 每一项的格式定义如下:
            {
                'name': para_name,  # 参数名
                'type': para_type,  # 参数类型, 取值为: POSITIONAL_OR_KEYWORD/KEYWORD_ONLY/VAR_POSITIONAL/VAR_KEYWORD
                'has_default': True/False,  # 是否有默认值
                'default': default_value  # 如果有默认值, 值为多少
            }
            其中type的说明如下:
            POSITIONAL_OR_KEYWORD - 参数之前没有任何类似*args的参数, 可以通过参数位置或者参数关键字进行调用
            KEYWORD_ONLY - 前面已经出现过类似*args的参数, 只能通过参数关键字进行调用
            VAR_POSITIONAL - 位置变量参数, 类似*args的定义, 允许按位置传入可变数量的参数
            VAR_KEYWORD - key-value形式的变量参数, 类似**kwargs, 允许传入可变数量的kv形式参数
            注意: 如果函数是类的静态函数, 无法获取到对象, 直接返回[]
        """
        _fun_frame = frame_obj
        if frame_obj is None:
            _fun_frame = inspect.currentframe().f_back
        _fun_obj = RunTool.get_current_function_object(frame_obj=_fun_frame)
        if _fun_obj is None:
            # TODO(lihuijian): 静态函数, 无法获取到对象, 只能返回空对象
            return []
        else:
            return RunTool.get_function_parameter_defines(_fun_obj)

    @staticmethod
    def get_current_function_parameter_values(frame_obj=None, fun_obj=None, is_simple_mode=False, ignore_first: bool = False):
        """
        获取当前运行函数的函数调用参数取值信息

        @param {frameobject} frame_obj=None - 不传入frame,获取调用本函数的函数;传入则获取frame对应的函数
        @param {function} fun_obj=None - 函数对象, 如不传入则通过frame获取, 传入可兼容静态函数的情况
        @param {bool} is_simple_mode=False - 是否简单模式
        @param {bool} ignore_first=False - 是否忽略第一个参数( 遇到是对象实例成员函数的情况可设置为True)

        @return {list} - 调用参数定义, 每一个参数是数组的一项, 每一项的格式定义如下:
            简单模式:
            [para_name, call_value] : 注意当有*args和**kwargs的情况, 也会拆开每个参数按顺序送入

            非简单模式:
            {
                'name': para_name,  # 参数名
                'type': para_type,  # 参数类型, 取值为: POSITIONAL_OR_KEYWORD/KEYWORD_ONLY/VAR_POSITIONAL/VAR_KEYWORD
                'has_default': True/False,  # 是否有默认值
                'default': default_value,  # 如果有默认值, 值为多少
                'value': call_value  # 函数调用的取值
            }
            其中type的说明如下:
            POSITIONAL_OR_KEYWORD - 参数之前没有任何类似*args的参数, 可以通过参数位置或者参数关键字进行调用
            KEYWORD_ONLY - 前面已经出现过类似*args的参数, 只能通过参数关键字进行调用
            VAR_POSITIONAL - 位置变量参数, 类似*args的定义, 允许按位置传入可变数量的参数
            VAR_KEYWORD - key-value形式的变量参数, 类似**kwargs, 允许传入可变数量的kv形式参数
            注意: 如果函数是类的静态函数, 且未传入函数对象, 无法获取到对象, 直接返回[]
        """
        # 获取函数参数定义
        _fun_frame = frame_obj
        if frame_obj is None:
            _fun_frame = inspect.currentframe().f_back
        _parameters = []
        if fun_obj is not None:
            _parameters = RunTool.get_function_parameter_defines(fun_obj)
        else:
            _parameters = RunTool.get_current_function_parameter_defines(frame_obj=_fun_frame)

        # 忽略第一个参数值
        if ignore_first and len(_parameters) > 0:
            _parameters.pop(0)

        # 获取函数的传入值
        _, _, _, _values = inspect.getargvalues(_fun_frame)
        if is_simple_mode:
            # 简单模式
            _func_args = []
            for _item in _parameters:
                if _item['type'] == 'VAR_POSITIONAL':
                    for _var_pos in _values[_item['name']]:
                        _func_args.append(['', _var_pos])
                elif _item['type'] == 'VAR_KEYWORD':
                    for _var_key in _values[_item['name']].keys():
                        _func_args.append([_var_key, _values[_item['name']][_var_key]])
                else:
                    _func_args.append([_item['name'], _values[_item['name']]])
            return _func_args
        else:
            # 非简单模式
            for _item in _parameters:
                _item['value'] = _values[_item['name']]
            return _parameters


class WaitLockTool(object):
    """
    等待锁处理类
    注: 便于输出锁长时间等待的问题, 跟踪死锁情况
    """

    def __init__(self, lock, print_timeout: float = None, label: str = '', print_acquire_ok: bool = False,
                 print_release: bool = False, force_no_acquire: bool = False):
        """
        初始化简单锁处理类

        @param {<type>} lock - 锁对象
        @param {float} print_timeout=None - 等待超时打印时间, 单位为秒, 如果不设置代表不打印超时信息
            注: 该参数仅为等待超时打印使用, 实际上锁还是会一直等待下去, 不会跳出等待处理
        @param {str} label='' - 打印信息时附带的显示内容
        @param {bool} print_acquire_ok=False - 是否打印锁获取成功信息
        @param {bool} print_release=False - 是否打印锁释放信息
        @param {bool} force_no_acquire=Fasle - 是否强制不等待锁
        """
        self.lock = lock
        self.print_timeout = print_timeout
        self.label = label
        self.print_acquire_ok = print_acquire_ok
        self.print_release = print_release
        self.force_no_acquire = force_no_acquire
        self._fun_name = None

    #############################
    # with 方法支持
    #############################
    def __enter__(self):
        """
        with方法进入的处理, 获取锁
        """
        if self.force_no_acquire:
            # 不处理锁等待
            return

        self._fun_name = None  # 函数名
        if self.print_timeout is None:
            # 不需要打印的情况, 直接一直等待获取即可
            self.lock.acquire()
        else:
            # 需要打印的情况, 通过循环方式进行等待
            while True:
                if self.lock.acquire(blocking=True, timeout=self.print_timeout):
                    # 获取锁成功
                    break

                # 获取函数名信息
                if self._fun_name is None:
                    self._fun_name = self._get_parent_fun_name(level=1)

                # 打印等待超时信息
                print('%s %s: get lock overtime [%s]' %
                      (self._fun_name, self.label, str(self.print_timeout)))

        # 获取到锁, 打印获取成功信息
        if self.print_acquire_ok:
            # 获取函数名信息
            if self._fun_name is None:
                self._fun_name = self._get_parent_fun_name(level=1)

            print('%s %s: get lock ok' % (self._fun_name, self.label))

    def __exit__(self, type, value, trace):
        """
        with方法退出函数, 释放锁

        @param {object} type - 执行异常的异常类型
        @param {object} value - 执行异常的异常对象值
        @param {object}} trace - 执行异常的异常trace对象
        """
        if self.force_no_acquire:
            # 不处理锁等待
            return

        # 关闭资源
        self.lock.release()
        if self.print_release:
            print('%s %s: release ok' % (self._fun_name, self.label))

    #############################
    # 内部函数
    #############################
    def _get_parent_fun_name(self, level: int = 0) -> str:
        """
        获取调用当前函数的父函数名

        @param {int} level=0 - 需要向上最追索的层级数
            注: 执行该函数的函数视为第0级

        @returns {str} - 返回的函数名
        """
        level += 1  # 需要
        _frame = RunTool.get_parent_function_frame(level)

        return RunTool.get_current_function_name(frame_obj=_frame, is_with_module=True)


class AsyncTools(object):
    """
    异步调用的工具类
    """

    @classmethod
    def set_thread_event_loop(cls):
        """
        设置线程的协程参数, 让线程正常运行协程

        @returns {io_loop} - 返回协程循环事件对象
        """
        try:
            loop = asyncio.get_running_loop()
        except:
            try:
                loop = asyncio.get_event_loop()
            except:
                loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)
        return loop

    @classmethod
    def sync_call(cls, func, *args, **kwargs) -> Any:
        """
        同步方式执行函数

        @param {function} func - 要执行的函数对象
        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {Any} - 函数返回值
        """
        _loop = cls.set_thread_event_loop()
        _resp = func(*args, **kwargs)
        if isawaitable(_resp):
            # 是异步调用
            _resp = _loop.run_until_complete(_resp)

        return _resp

    @classmethod
    def sync_run_coroutine(cls, coroutine_obj) -> Any:
        """
        同步方式运行协程函数返回对象
        (相当于await)

        @param {coroutine} coroutine_obj - 协程函数

        @returns {Any} - 处理结果
        """
        if isawaitable(coroutine_obj):
            _loop = cls.set_thread_event_loop()
            return _loop.run_until_complete(coroutine_obj)
        else:
            # 同步对象
            return coroutine_obj

    @classmethod
    async def async_run_coroutine(cls, coroutine_obj) -> Any:
        """
        异步方式执行协程返回结果

        @param {coroutine} coroutine_obj - 协程函数

        @returns {Any} - 处理结果
        """
        if isawaitable(coroutine_obj):
            return await coroutine_obj
        else:
            return coroutine_obj

    @classmethod
    async def async_for_iter(cls, async_iter_obj, func, *args, **kwargs):
        """
        处理异步迭代器的异步函数

        @param {AsyncGenerator|Iterator} AsyncGenerator - 要处理的迭代器对象
        @param {function} func - 处理函数对象
            注: 处理函数的第一个入参是每次迭代的返回对象
        @param {args} - 处理函数的其他固定位置入参
        @param {kwargs} - 处理函数的kv入参
        """
        if type(async_iter_obj).__name__ == 'generator':
            # 普通的迭代
            for _item in async_iter_obj:
                func(_item, *args, **kwargs)
        else:
            # 异步迭代
            async for _item in async_iter_obj:
                func(_item, *args, **kwargs)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
