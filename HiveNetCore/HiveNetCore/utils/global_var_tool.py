#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
全局变量工具类

@module global_var_tool
@file global_var_tool.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


# 全局变量
# 用于存储全局变量的值
# key为全局变量名( string) , value为全局变量的值
RUNTOOL_GLOBAL_VAR_LIST = dict()


class GlobalVarTool(object):
    """
    全局变量处理类
    """

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
