#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
库导入工具

@module import_tool
@file import_tool.py

"""

import sys
import os


__MOUDLE__ = 'import_tool'  # 模块名
__DESCRIPT__ = u'库导入工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class ImportTool(object):
    """
    库导入工具
    提供库导入相关功能, 包括动态导入库的支持

    """

    @staticmethod
    def check_module_imported(module_name):
        """
        检查指定模块名是否已导入

        @param {string} module_name - 要检查的模块名, 形式有以下几种:
            (1)基础库的情况, 例如'sys'
            (2)子库情况, 例如'simple_log.Logger'

        @returns {bool} - True-模块已导入, False-模块未导入
        """
        return module_name in sys.modules.keys()

    @staticmethod
    def get_imported_module(module_name):
        """
        根据模块名称获取已导入的模块, 如果模块不存在返回None

         @param {string} module_name - 要获取的模块名, 形式有以下几种:
            (1)基础库的情况, 例如'sys'
            (2)子库情况, 例如'simple_log.Logger'

        @returns {Module} - 已导入的模块对象, 可以直接引用该对象执行操作
        """
        if ImportTool.check_module_imported(module_name):
            return sys.modules[module_name]
        else:
            return None

    @staticmethod
    def get_member_from_module(module, member_name):
        """
        从指定模块中获取成员对象( 例如类)

        @param {Module} module - 要处理的模块对象
        @param {string} member_name - 成员对象名

        @return {object} - 返回成员对象
        """
        return getattr(module, member_name)

    @staticmethod
    def import_module(module_name, as_name=None, extend_path=None, import_member=None, is_force=False):
        """
        导入指定模块
        如果不指定is_force参数强制加载, 已经加载过的模块不会重新加载, 对使用有import_member模式的
        使用方式可能会存在问题

        @param {string} module_name - 要导入的模块名
        @param {string} as_name=None - 对导入的模块名设置的别名
        @param {string} extend_path=None - 对于存放在非python搜索路径( sys.path) 外的模块, 需要指定扩展搜索路径
        @param {string} import_member=None - 指定导入模块对应的成员对象, None代表不指定导入对象, "*"代表导入模块的所有对象:
            效果如from module_name import import_member
        @param {bool} is_force=False - 是否强制执行导入的命令动作, True-强制再执行导入命令, Fasle-如果模块已存在则不导入

        @returns {Module} - 已导入的模块对象, 可以直接引用该对象执行操作

        @example
            lib_obj = ImportTools.import_module('os')
            print(lib_obj.path.realpath(''))

        """
        if is_force or not ImportTool.check_module_imported(module_name):
            # 模块未导入, 导入模块
            if extend_path is not None:
                # 指定了路径, 组装路径
                lib_path = os.path.realpath(extend_path)
                if lib_path not in sys.path:
                    sys.path.append(lib_path)

            # 导入对象
            _exec_code = ''
            if import_member is None or import_member == '':
                # 无需指定对象导入
                _exec_code = 'import %s' % module_name
                if as_name is not None:
                    _exec_code = '%s as %s' % (_exec_code, as_name)
            else:
                _exec_code = 'from %s import %s' % (module_name, import_member)

            # 执行导入动作
            exec(_exec_code)

        # 返回模块
        return sys.modules[module_name]

    @staticmethod
    def unimport_module(module_name):
        """
        卸载已导入的模块

        @param {string} module_name - 要卸载的模块名
        """
        if module_name in sys.modules.keys():
            del sys.modules[module_name]

    @staticmethod
    def has_attr(module_obj, attr_name):
        """
        检查模块或对象是否有指定名称的属性

        @param {Module} module_obj - 模块对象
        @param {string} attr_name - 属性名( 类名/函数名/属性名)

        @returns {bool} - 是否包含属性, True-包含, False-不包含

        """
        return hasattr(module_obj, attr_name)

    @staticmethod
    def get_attr(module_obj, attr_name):
        """
        获取对象的指定属性( 直接使用)

        @param {Module} module_obj - 模块对象
        @param {string} attr_name - 属性名( 类名/函数名/属性名)

        @returns {object} - 具体属性引用, 可以直接使用

        """
        return getattr(module_obj, attr_name)

    @staticmethod
    def get_module_name(module_obj):
        """
        获取模块名, 如果模块是包中, 模块名会包括包路径

        @param {Module} module_obj - 模块对象

        @returns {string} - 模块对象的名称

        """
        return module_obj.__name__


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
