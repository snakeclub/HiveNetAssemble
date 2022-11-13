#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
条件处理工具模块

@module condition_tool
@file condition_tool.py
"""

import sys
import os
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.utils.run_tool import SafeEval


class ConditionTool(object):
    """
    条件处理工具
    """

    #############################
    # 条件类型映射字典
    #############################
    @classmethod
    def get_default_condition_func_mapping(cls) -> dict:
        """
        获取默认的条件处理函数映射字典

        @returns {dict} - 返回映射字典
        """
        return {
            'pyexp': cls.condition_func_pyexp,
            'exists': cls.condition_func_exists
        }

    #############################
    # 条件类型处理函数
    #############################
    @classmethod
    def condition_func_pyexp(cls, c_type: str, c_para: dict) -> bool:
        """
        python表达式条件处理函数

        @param {str} c_type - 条件类型, 应传入'pyexp'
        @param {dict} c_para - 条件参数, 格式如下:
            {
                'exp': 'xxx',  # 表达式文本
                'globals': None, # 允许访问的全局变量字典
                'locals': None,  # 允许访问的局部变量字典
            }

        @returns {bool} - 返回处理结果
        """
        return SafeEval.eval(
            c_para['exp'],
            globals_dict=c_para.get('globals', sys._getframe(1).f_globals),
            locals_dict=c_para.get('locals', sys._getframe(1).f_locals),
            forbid_import=True, forbid_function=True
        )

    @classmethod
    def condition_func_exists(cls, c_type: str, c_para: dict) -> bool:
        """
        判断是否包含指定值的处理函数
        注: 目前支持字典和列表对象的判断

        @param {str} c_type - 条件类型, 应传入'exists'
        @param {dict} c_para - 条件参数, 格式如下:
            {
                'value': 'xxx',  # 要检查是否包含在对象的值(如果对象是字典, 检查的是key)
                # 检查对象的获取类型:
                #   instance - obj为直接给出的对象(默认)
                #   strexp - obj为字符格式的对象(json), 例如: '{"a": "aval", "b": "bval"}', '[1, 2, 3]'
                #   pyexp - obj为python表达式指定的变量, 可结合globals和locals指定全局变量和局部变量
                'obj_type': 'instance',
                'obj': {},  # 检查对象, 与获取类型相对应的对象或值
                'globals': None, # 允许访问的全局变量字典
                'locals': None,  # 允许访问的局部变量字典
            }

        @returns {bool} - 返回处理结果
        """
        # 获取字典对象
        _obj_type = c_para.get('obj_type', 'instance')
        _obj = c_para['obj']
        if _obj_type == 'strexp':
            _obj = SafeEval.str_to_var(_obj)
        elif _obj_type == 'pyexp':
            _obj = SafeEval.eval(
                _obj,
                globals_dict=c_para.get('globals', sys._getframe(1).f_globals),
                locals_dict=c_para.get('locals', sys._getframe(1).f_locals),
                forbid_import=True, forbid_function=True
            )

        # 区分检查对象的类型进行判断
        if isinstance(_obj, dict):
            # 字典
            return (_obj.get(c_para['value'], None) is not None)
        else:
            # 列表
            return (c_para['value'] in _obj)

    #############################
    # 通用条件组合判断处理
    #############################
    @classmethod
    def run_conditions(cls, conditions: dict, func_mapping: dict = None,
            globals: dict = None, locals: dict = None) -> bool:
        """
        执行条件

        @param {dict} conditions - 条件字典, 格式如下:
            {'操作符': [('条件类型', {条件参数}), ...]}
            操作符支持: '$and' - 数组中的条件以and方式联合判断, '$or' - 数组中的条件以or方式联合判断, '$not' - 数组中的条件以and联合并对结果取反
            一个字典那的多个操作符以and联合, 例如: {'$and': [条件集合1], '$or': [条件集合2], '$not': [条件集合3]} 代表 (条件集合1结果) and (条件集合2结果) and (条件集合3结果)
            支持条件的嵌套, 例如 {'$and': [(条件1), {'$or': [(条件2), (条件3)]}]} 代表 (条件1结果) and (条件2 or 条件3)
        @param {dict} func_mapping=None - 条件处理函数映射字典
            注: 如果不设置默认使用get_default_condition_func_mapping获取初始字典
        @param {dict} globals=None - 内部使用, 指定调用函数自身的全局变量字典
        @param {dict} locals=None - 内部使用, 指定调用函数自身的局部变量字典

        @returns {bool} - 返回判断结果
        """
        # 处理全局变量和局部变量
        _globals = sys._getframe(1).f_globals if globals is None else globals
        _locals = sys._getframe(1).f_locals if locals is None else locals

        # 处理类型函数映射字典
        _func_mapping = func_mapping
        if func_mapping is None:
            _func_mapping = cls.get_default_condition_func_mapping()

        # 进行递归处理
        # 多个条件以and方式递归联合处理
        if len(conditions) > 1:
            for _op, _para in conditions.items():
                if not cls.run_conditions(
                    {_op: _para}, func_mapping=_func_mapping, globals=_globals, locals=_locals
                ):
                    # 多个条件中有一个条件为False
                    return False

        # 单一条件的处理
        _op = list(conditions.keys())[0]
        _para = conditions[_op]
        # 逐个条件执行
        _run_result = True
        for _item in _para:
            if isinstance(_item, dict):
                # 是字典, 继续递归处理
                _result = cls.run_conditions(
                    _item, func_mapping=_func_mapping, globals=_globals, locals=_locals
                )
            else:
                # 非字典, 处理真正的判断函数
                _func = _func_mapping.get(_item[0], None)
                if _func is None:
                    raise ModuleNotFoundError('Unsupport condition type [%s]' % _item[0])

                if _item[0] in ('pyexp', 'exists'):
                    # 局部变量和全局变量的特殊处理
                    if _item[1].get('globals', None) is None:
                        _item[1]['globals'] = _globals
                    if _item[1].get('locals', None) is None:
                        _item[1]['locals'] = _locals

                _result = _func(_item[0], _item[1])

            # 判断是否执行下一个
            if _op in ('$and', '$not') and not _result:
                # and模式, 有一个为False就返回False
                _run_result = False
                break
            elif _op == '$or' and _result:
                # or模式, 有一个为True就返回True
                _run_result = True
                break

            _run_result = _result

        # 返回真正的结果
        if _op == '$not':
            return (not _run_result)
        else:
            return _run_result
