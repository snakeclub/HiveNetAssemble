#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
通用调试工具

@module debug_tool
@file debug_tool.py

"""

import sys
import os
import json
import logging
import logging.config
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.string_tool import StringTool


__MOUDLE__ = 'debug_tool'  # 模块名
__DESCRIPT__ = u'通用调试工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class DebugTool(object):
    """
    通用调试类, 用于输出各类调试信息

    @example
        1、在主程序的入口设置启动调试
        DebugTools.set_debug(True)

        2、在需要输出调试的地方, 传入要输出的变量
        DebugTools.debug_print(abc,10,'ddf',{'a':33,'b':'33'},name=NullObj(),cb=CResult())

    """

    @staticmethod
    def set_debug(set_on=True):
        """
        启动/关闭debug的输出

        @param {bool} set_on - 是否启动调试

        """
        DEBUG_TOOLS_SWITCH_ON = RunTool.get_global_var('DEBUG_TOOLS_SWITCH_ON')
        if DEBUG_TOOLS_SWITCH_ON is None:
            DEBUG_TOOLS_SWITCH_ON = False
            RunTool.set_global_var('DEBUG_TOOLS_SWITCH_ON', False)

        DEBUG_TOOLS_LOGGER = RunTool.get_global_var('DEBUG_TOOLS_LOGGER')

        if set_on:
            if not DEBUG_TOOLS_SWITCH_ON:
                # 创建输出日志类
                if DEBUG_TOOLS_LOGGER is None:
                    DebugTool.__create_logger()
                RunTool.set_global_var('DEBUG_TOOLS_SWITCH_ON', True)
        else:
            if DEBUG_TOOLS_SWITCH_ON:
                RunTool.set_global_var('DEBUG_TOOLS_SWITCH_ON', False)

    @staticmethod
    def is_debug_on() -> bool:
        """
        判断当前debug状态是否启动

        @returns {bool} - debug状态是否启动
        """
        DEBUG_TOOLS_SWITCH_ON = RunTool.get_global_var('DEBUG_TOOLS_SWITCH_ON')
        if DEBUG_TOOLS_SWITCH_ON is None:
            DEBUG_TOOLS_SWITCH_ON = False

        return DEBUG_TOOLS_SWITCH_ON

    @staticmethod
    def debug_print(*args, **kwargs):
        """
        打印调试信息, 可打印传入的多个对象

        """
        DEBUG_TOOLS_SWITCH_ON = RunTool.get_global_var('DEBUG_TOOLS_SWITCH_ON')
        if DEBUG_TOOLS_SWITCH_ON is None:
            DEBUG_TOOLS_SWITCH_ON = False

        DEBUG_TOOLS_LOGGER = RunTool.get_global_var('DEBUG_TOOLS_LOGGER')

        if not DEBUG_TOOLS_SWITCH_ON:
            # 未启动调试
            return

        # 输出打印信息, 先准备整体信息
        _print_info = u'[%s][%s][行:%s]DEBUG INFO:\n%s' % (
            os.path.split(
                os.path.realpath(
                    sys._getframe().f_back.f_code.co_filename)
            )[1],
            sys._getframe().f_back.f_code.co_name,
            sys._getframe().f_back.f_lineno,
            '\n'.join(DebugTool.__get_print_str_seq(args, kwargs))
        )
        DEBUG_TOOLS_LOGGER.debug(_print_info)

    @staticmethod
    def __create_logger():
        """
        创建logger日志类
        内部函数, 创建debug日志类

        """
        DEBUG_TOOLS_LOGGER = RunTool.get_global_var('DEBUG_TOOLS_LOGGER')
        if DEBUG_TOOLS_LOGGER is None:
            DEBUG_TOOLS_JSON_PARA = u'''{
                "version": 1,
                "disable_existing_loggers": false,
                "formatters": {
                    "DebugToolsFormatter": {
                        "format": "[%(asctime)s][PID:%(process)d][TID:%(thread)d]%(message)s"
                    }
                },

                "handlers": {
                    "DebugToolsConsoleHandler": {
                        "class": "logging.StreamHandler",
                        "level": "DEBUG",
                        "formatter": "DebugToolsFormatter",
                        "stream": "ext://sys.stdout"
                    }
                },

                "loggers": {
                    "DebugToolsConsole": {
                        "level": "DEBUG",
                        "handlers": ["DebugToolsConsoleHandler"]
                    }
                },

                "root": {
                    "level": "DEBUG",
                    "handlers": []
                }
            }
            '''
            _json_config = json.loads(DEBUG_TOOLS_JSON_PARA)
            logging.config.dictConfig(_json_config)
            DEBUG_TOOLS_LOGGER = logging.getLogger('DebugToolsConsole')
            RunTool.set_global_var('DEBUG_TOOLS_LOGGER', DEBUG_TOOLS_LOGGER)

    @staticmethod
    def __get_print_str(var_obj):
        """
        获取对象的打印字符串

        @param {object} var_obj - 要打印的对象

        @returns {string} - 打印的字符串

        """
        _print_str = '[type=%s]%s%s' % (
            str(type(var_obj)),
            ('' if not hasattr(var_obj, '__str__') else str(var_obj)),
            ('' if not hasattr(var_obj, '__dict__')
             else StringTool.format_obj_property_str(var_obj, is_deal_subobj=True, c_level=2))
        )
        return _print_str

    @staticmethod
    def __get_print_str_seq(args, kwargs):
        """
        返回对象清单打印序列, 利用yield逐个输出

        @param {truple} args - 要打印的对象数组
        @param {dict} kwargs - keyvalue的对象字典

        @returns {iterable} - 每次迭代返回一个打印值

        """
        for _obj in args:
            yield '%s[key=]%s' % (
                '    ',
                DebugTool.__get_print_str(_obj)
            )

        for _key in kwargs:
            yield '%s[key=%s]%s' % (
                '    ',
                _key,
                DebugTool.__get_print_str(kwargs[_key])
            )

        return


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
