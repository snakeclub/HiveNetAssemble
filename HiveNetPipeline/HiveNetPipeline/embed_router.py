# !/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
管道通用路由插件模块
@module extend_router
@file extend_router.py
"""

import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetPipeline import Tools, PipelineRouter
from HiveNetCore.utils.condition_tool import ConditionTool


__MOUDLE__ = 'extend_router'  # 模块名
__DESCRIPT__ = u'管道通用路由插件模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.10.16'  # 发布日期


class GoToNode(PipelineRouter):
    """
    跳转到指定节点
    """
    @classmethod
    def router_name(cls) -> str:
        """
        路由器名称, 唯一标识路由器

        @returns {str} - 当前路由器名称
        """
        return 'GoToNode'

    @classmethod
    def get_next(cls, output, context: dict, pipeline_obj, run_id: str, **kwargs):
        """
        获取路由下一节点

        @param {object} output - 上一个节点的输出结果
        @param {dict} context - 上下文字典
        @param {Pipeline} pipeline_obj - 管道对象
        @param {str} run_id - 当前管道的运行id
        @param {kwargs} - 传入的扩展参数
            default_to_next {bool} - 当没有给出上下文参数及扩展参数的时候是否默跳转到下一个节点, 默认为False
            可在上下文设置或直接管道配置传入的参数:
            goto_node_id {str} - 可选, 要跳转到的节点id, 与goto_node_name传入一个即可
            goto_node_name {str} - 可选, 要跳转到的节点名, 与goto_node_id传入一个即可

        @returns {str} - 下一节点的配置id, 如果是最后的节点, 返回None
        """
        # 优先以context的参数进行处理
        _goto_node_id = str(context.pop('goto_node_id', ''))
        _goto_node_name = context.pop('goto_node_name', '')

        # 尝试从管道参数中获取跳转参数
        if _goto_node_id == '' and _goto_node_name == '':
            _goto_node_id = str(kwargs.get('goto_node_id', ''))
            _goto_node_name = kwargs.get('goto_node_name', '')

        # 处理跳转
        if _goto_node_id != '':
            _next_id = _goto_node_id
        elif _goto_node_name != '':
            _next_id = Tools.get_node_id_by_name(_goto_node_name, pipeline_obj)
            if _next_id is None:
                raise RuntimeError(
                    'GoToNode Router Error: goto_node_name[%s] not found!' % _goto_node_name)
        else:
            # 没有跳转参数
            if kwargs.get('default_to_next', False):
                # 跳转到下一个节点
                _next_id = None
                _temp_id = str(int(pipeline_obj.current_node_id(run_id=run_id)) + 1)
                if _temp_id in pipeline_obj.pipeline.keys():
                    _next_id = _temp_id
            else:
                raise RuntimeError(
                    'GoToNode Router Error: goto para not found in context or pipeline para!')

        # 返回路由节点
        return _next_id


class IfGotoNode(PipelineRouter):
    """
    根据指定条件跳转到对应节点
    """

    @classmethod
    def router_name(cls) -> str:
        """
        路由器名称, 唯一标识路由器

        @returns {str} - 当前路由器名称
        """
        return 'IfGotoNode'

    @classmethod
    def get_next(cls, output, context: dict, pipeline_obj, run_id: str, **kwargs):
        """
        获取路由下一节点

        @param {object} output - 上一个节点的输出结果
        @param {dict} context - 上下文字典
        @param {Pipeline} pipeline_obj - 管道对象
        @param {str} run_id - 当前管道的运行id
        @param {kwargs} - 传入的扩展参数
            default_to_next {bool} - 当没有给出上下文参数及扩展参数的时候是否默跳转到下一个节点, 默认为False
            可在上下文设置或直接管道配置传入的参数:
            if_goto_node_conditions {dict} - IF判断条件,  格式如下:
                {'操作符': [('条件类型', {条件参数}), ...]}
                操作符支持: '$and' - 数组中的条件以and方式联合判断, '$or' - 数组中的条件以or方式联合判断, '$not' - 数组中的条件以and联合并对结果取反
                一个字典那的多个操作符以and联合, 例如: {'$and': [条件集合1], '$or': [条件集合2], '$not': [条件集合3]} 代表 (条件集合1结果) and (条件集合2结果) and (条件集合3结果)
                支持条件的嵌套, 例如 {'$and': [(条件1), {'$or': [(条件2), (条件3)]}]} 代表 (条件1结果) and (条件2 or 条件3)
                目前支持的条件类型包括:
                    pyexp - python脚本表达式, 条件参数为{'exp': '表达式脚本'}, 脚本中可以直接使用context和output变量
                        例如: {'$and': [('pyexp', {'exp': 'context["a"] == 10'}),]}
                    exists - 值(或key)是否在指定对象中, 条件参数为{'value': '判断值(或key)', 'obj_type': '检查对象获取类型', 'obj': 检查对象}
                        obj_type可设置为以下值:
                            instance - obj为直接给出的对象(默认)
                            strexp - obj为字符格式的对象(json), 例如: '{"a": "aval", "b": "bval"}', '[1, 2, 3]'
                            pyexp - obj为python表达式指定的变量, 脚本中可以直接使用context和output变量
                        例如: {'$and': [('exists', {'value': 'key', 'context["my_var"]'}),]}
            if_goto_node_id {str} - 可选, 条件为True时要跳转到的节点id, 与if_goto_node_id_name传入一个即可
            if_goto_node_name {str} - 可选, 条件为True时要跳转到的节点name, 与if_goto_node_id传入一个即可
            if_goto_node_else_id {str} - 可选, 条件为False时要跳转到的节点id, 与if_goto_node_else_name传入一个即可
            if_goto_node_else_name {str} - 可选, 条件为True时要跳转到的节点name, 与if_goto_node_else_id传入一个即可
        @returns {str} - 下一节点的配置id, 如果是最后的节点, 返回None
        """
        # 获取条件并进行判断
        _if_goto_node_conditions = context.pop(
            'if_goto_node_conditions', kwargs.get('if_goto_node_conditions', None)
        )
        _condition_result = True
        if _if_goto_node_conditions is not None:
            _condition_result = ConditionTool.run_conditions(
                _if_goto_node_conditions, globals={},
                locals={'context': context, 'output': output}
            )

        # 处理跳转的上下文参数
        _if_goto_node_id = str(context.pop('if_goto_node_id', ''))
        _if_goto_node_name = context.pop('if_goto_node_name', '')
        _if_goto_node_else_id = str(context.pop('if_goto_node_else_id', ''))
        _if_goto_node_else_name = context.pop('if_goto_node_else_name', '')

        # 处理跳转
        _goto_node_id = ''
        _goto_node_name = ''
        if _condition_result:
            if _if_goto_node_id == '' and _if_goto_node_name == '':
                _if_goto_node_id = str(kwargs.get('if_goto_node_id', ''))
                _if_goto_node_name = kwargs.get('if_goto_node_name', '')

            _goto_node_id = _if_goto_node_id
            _goto_node_name = _if_goto_node_name
        else:
            if _if_goto_node_else_id == '' and _if_goto_node_else_name == '':
                _if_goto_node_else_id = str(kwargs.get('if_goto_node_else_id', ''))
                _if_goto_node_else_name = kwargs.get('if_goto_node_else_name', '')

            _goto_node_id = _if_goto_node_else_id
            _goto_node_name = _if_goto_node_else_name

        # 处理跳转
        if _goto_node_id != '':
            _next_id = _goto_node_id
        elif _goto_node_name != '':
            _next_id = Tools.get_node_id_by_name(_goto_node_name, pipeline_obj)
            if _next_id is None:
                raise RuntimeError(
                    'IfGoToNode Router Error: goto_node_name[%s] not found!' % _goto_node_name)
        else:
            # 没有跳转参数
            if kwargs.get('default_to_next', False):
                # 跳转到下一个节点
                _next_id = None
                _temp_id = str(int(pipeline_obj.current_node_id(run_id=run_id)) + 1)
                if _temp_id in pipeline_obj.pipeline.keys():
                    _next_id = _temp_id
            else:
                raise RuntimeError(
                    'IfGoToNode Router Error: goto para not found in context or pipeline para!')

        # 返回路由节点
        return _next_id


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

