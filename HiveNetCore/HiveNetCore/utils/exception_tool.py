#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
异常处理工具

@module exception_tool
@file exception_tool.py

"""

import os
import sys
import copy
import traceback
import logging
from contextlib import contextmanager
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _


__MOUDLE__ = 'exception_tool'  # 模块名
__DESCRIPT__ = u'异常处理工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class ExceptionTool(object):
    """
    异常处理工具,提供便捷的异常处理模式

    """

    @staticmethod
    @contextmanager
    def ignored(expect=(), logger=None, self_log_msg='', force_log_level=None, debug=False):
        """
        忽略指定异常, 简化异常捕获代码, 利用该函数忽略指定的异常, 详细说明如下:
            1、对于指定忽略的异常, 忽略不处理( 如果指定logger则会进行日志输出, 使用WARNING级别)
            2、对于非指定的异常, 仍抛出异常( 如果指定logger则会进行日志输出, 使用ERROR级别)
            3、输出的日志为self_log_msg+'\n'+trace_str


        @param {tuple} expect=() - 需要忽略的异常列表, 例如(ZeroDivisionError, ValueError)
        @param {object} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现warning、error的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {int} force_log_level=None - 强制遇到所有异常统一按指定的日志级别输出(logging.INFO/...)
        @param {bool} - debug=False - 是否调试模式, 如果是调试模式, 当没有logger时使用print输出堆栈信息

        @example
            with ignored((ZeroDivisionError, ValueError), logger, '执行XX出现异常'):
                count = 1 / 0
                count = count + 10000

        """
        try:
            yield
        except expect as ex:
            # 匹配到指定异常, 输出日志
            _log_level = logging.WARNING
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(ex)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level, debug=debug)
            pass
        except Exception as e:
            # 其他异常, 输出日志并抛出异常
            _log_level = logging.ERROR
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(e)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level, debug=debug)
            raise sys.exc_info()[1]

    @staticmethod
    @contextmanager
    def ignored_all(unexpect=(), logger=None, self_log_msg='', force_log_level=None, debug=False):
        """
        忽略除指定以外的所有异常,简化异常捕获代码, 利用该函数忽略指定以外的所有异常, 详细说明如下:
            1、对于指定以外的异常, 忽略不处理( 如果指定logger则会进行日志输出, 使用WARNING级别)
            2、对于指定的异常, 仍抛出异常( 如果指定logger则会进行日志输出, 使用ERROR级别)
            3、输出的日志为self_log_msg+'\n'+trace_str

        @param {tuple} unexpect=() - 指定不能忽略的异常列表, 例如(ZeroDivisionError, ValueError)
        @param {object} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现warning、error的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {int} force_log_level=None - 强制遇到所有异常统一按指定的日志级别输出(logging.INFO/...)
        @param {bool} - debug=False - 是否调试模式, 如果是调试模式, 当没有logger时使用print输出堆栈信息

        @example
            with ignored_all((ZeroDivisionError, ValueError), logger, '执行XX出现异常'):
                count = 1 / 0
                count = count + 10000

        """
        try:
            yield
        except unexpect as ue:
            # 匹配到指定异常, 输出日志并抛出异常
            _log_level = logging.ERROR
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(ue)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level, debug=debug)
            raise sys.exc_info()[1]
        except Exception as e:
            # 其他异常, 输出日志并忽略
            _log_level = logging.WARNING
            if force_log_level is not None:
                _log_level = force_log_level
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(e)), self_log_msg),
                                      trace_str=traceback.format_exc(), log_level=_log_level, debug=debug)
            pass

    @staticmethod
    @contextmanager
    def ignored_cresult(result_obj=None, error_map={}, expect=(), expect_no_log=False, expect_use_error_map=True,
                        logger=None, self_log_msg='', force_log_level=None, i18n_obj=None,
                        i18n_msg_paras=(), debug=False):
        """
        忽略异常并设置CResult对象,简化异常捕获代码, 利用该函数忽略指定的异常, 并设置传入的通用结果对象, 详细说明如下:
            1、对于指定忽略的异常, 忽略不处理, 结果为成功( 如果指定logger则会进行日志输出, 使用WARNING级别)
            2、对于非指定的异常, 不抛出异常, 结果为失败( 如果指定logger则会进行日志输出, 使用ERROR级别)
            3、输出的日志为self_log_msg+'\n'+trace_str
            4、根据error_map的映射关系设置错误码和错误信息

        @param {CResult} result_obj=None - 需要设置的错误类对象(对象值会被修改)
        @param {dict} error_map={} - 用来设置错误类对象的映射表, 具体说明如下:
            1、key为异常类, value为(code, msg)的错误码、错误描述二元组, 如果msg=None代表使用标准错误码
            2、应有一个'DEFAULT'的key, 代表没有匹配上的异常映射, 默认value为('29999', None)
            3、应有一个'SUCESS'的key, 代表成功的映射, 默认value为('00000', None)
            注: value也可以为(code, msg, i18n_msg_paras)的错误码、错误描述、国际化替换参数三元组,
                i18n_msg_paras为tuple类型, 使用该模式支持CResult的国际化处理
        @param {tuple} expect=() - 需要忽略的异常列表, 例如(ZeroDivisionError, ValueError)
        @param {bool} expect_no_log=False - 忽略异常列表是否不打印日志
        @param {bool} expect_use_error_map=True - 忽略异常列表所匹配到的异常, 所返回错误码是否使用错误码映射表:
            如果在映射表中匹配上则返回映射表的错误码；匹配不上则返回成功
        @param {object} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现warning、error的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {int} force_log_level=None - 强制遇到所有异常统一按指定的日志级别输出(logging.INFO/...)
        @param {object} i18n_obj=None - 国际化类的实例对象, 该对象需实现translate方法
        @param {tuple} i18n_msg_paras=() - 与self_log_msg配套使用, 当使用国际化时, 可以传入变量, 用于替换self_log_msg中的$1占位符
        @param {bool} - debug=False - 是否调试模式, 如果是调试模式, 当没有logger时使用print输出堆栈信息

        @example
            result = CResult()
            with ExceptionTools.ignored_CResult(result_obj=result, error_map={},expect=(),logger=None,self_log_msg=''):
                i = 1/0
                i = i + 1000
            print(str(result))

        """
        _error_map = copy.deepcopy(error_map)
        try:
            # 初始化对象
            if result_obj is None:
                result_obj = CResult(code='00000', msg=None, i18n_obj=i18n_obj)

            # 确保映射表中有默认值
            if 'SUCESS' not in _error_map.keys():
                _error_map['SUCESS'] = ('00000', None, i18n_msg_paras)
            if 'DEFAULT' not in _error_map.keys():
                _error_map['DEFAULT'] = ('29999', None, i18n_msg_paras)
            # 执行with对应的脚本
            yield
        except expect as ex:
            # 匹配到指定异常, 输出日志
            if not expect_no_log:
                _log_level = logging.WARNING
                if force_log_level is not None:
                    _log_level = force_log_level
                _self_log_msg = ''
                if i18n_obj is not None:
                    _self_log_msg = i18n_obj.translate(self_log_msg, replace_para=i18n_msg_paras)
                else:
                    _self_log_msg = _(self_log_msg, *i18n_msg_paras)
                ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(ex)), _self_log_msg),
                                          trace_str=traceback.format_exc(), log_level=_log_level, debug=debug)
            # 按成功处理
            _error = sys.exc_info()
            _trace_str = traceback.format_exc()
            if expect_use_error_map and _error[0] in _error_map.keys():
                if len(_error_map[_error[0]]) < 3:
                    result_obj.change_code(
                        code=_error_map[_error[0]][0], msg=_error_map[_error[0]][1]
                    )
                else:
                    result_obj.change_code(
                        code=_error_map[_error[0]][0], msg=_error_map[_error[0]][1],
                        i18n_msg_paras=_error_map[_error[0]][2]
                    )
                result_obj.error = str(_error[0])
                result_obj.trace_str = _trace_str
            else:
                # 按成功处理
                pass
        except Exception as e:
            # 其他异常, 输出日志, 获取失败信息
            _error = sys.exc_info()
            _trace_str = traceback.format_exc()
            if _error[0] in _error_map.keys():
                if len(_error_map[_error[0]]) < 3:
                    result_obj.change_code(
                        code=_error_map[_error[0]][0], msg=_error_map[_error[0]][1]
                    )
                else:
                    result_obj.change_code(
                        code=_error_map[_error[0]][0], msg=_error_map[_error[0]][1],
                        i18n_msg_paras=_error_map[_error[0]][2]
                    )
                result_obj.error = str(_error[0])
                result_obj.trace_str = _trace_str
            else:
                # 其他失败
                if len(_error_map['DEFAULT']) < 3:
                    result_obj.change_code(
                        code=_error_map['DEFAULT'][0], msg=_error_map['DEFAULT'][1]
                    )
                else:
                    result_obj.change_code(
                        code=_error_map['DEFAULT'][0], msg=_error_map['DEFAULT'][1],
                        i18n_msg_paras=_error_map['DEFAULT'][2]
                    )
                result_obj.error = str(_error[0])
                result_obj.trace_str = _trace_str

            _log_level = logging.ERROR
            if force_log_level is not None:
                _log_level = force_log_level
            _self_log_msg = ''
            if i18n_obj is not None:
                _self_log_msg = i18n_obj.translate(self_log_msg, replace_para=i18n_msg_paras)
            else:
                _self_log_msg = _(self_log_msg, *i18n_msg_paras)
            ExceptionTool.__print_log(logger=logger, self_log_msg='[EX:%s]%s' % (str(type(e)), _self_log_msg),
                                      trace_str=result_obj.trace_str, log_level=_log_level, debug=debug)

    # 内部函数定义
    @staticmethod
    def __print_log(logger=None, self_log_msg='', trace_str='', log_level=logging.WARNING, debug=False):
        """
        内部进行日志输出处理,  调用日志对象进行日志输出处理

        @param {object} logger=None - 日志对象, 如果为None代表不需要输出日志, 传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象, 但应实现warning、error等的标准方法
        @param {string} self_log_msg='' - 需要输出的自定义日志信息
        @param {string} trace_str='' - 错误追踪堆栈日志, 异常时的traceback.format_exc()
        @param {int} log_level=logging.WARNING - 需要输出的自定义日志级别
        @param {bool} - debug=False - 是否调试模式, 如果是调试模式, 当没有logger时使用print输出堆栈信息

        """
        if logger is not None or debug:
            # 要输出的日志内容
            _log_str = ''
            if len(self_log_msg) > 0:
                _log_str = self_log_msg + '\n' + trace_str
            else:
                _log_str = trace_str
            if logger is not None:
                # 输出日志
                logger.log(log_level, _log_str, extra={'callFunLevel': 3})
            else:
                print(_log_str)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
