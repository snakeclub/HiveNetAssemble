#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
管道通用预处理器插件模块
@module embed_predealer
@file embed_predealer.py
"""

import os
import sys
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetPipeline import PipelinePredealer
from HiveNetCore.utils.condition_tool import ConditionTool


class ConditionPredealer(PipelinePredealer):
    """
    条件预处理器
    """

    @classmethod
    def predealer_name(cls) -> str:
        """
        预处理器名称, 唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ConditionPredealer'

    @classmethod
    def pre_deal(cls, input_data, context: dict, pipeline_obj, run_id: str, **kwargs):
        """
        执行预处理

        @param {object} input_data - 处理器输入数据值, 除第一个处理器外, 该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文, 该字典信息将在整个管道处理过程中一直向下传递, 可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象, 作用如下:
            1、更新执行进度
            2、输出执行日志
            3、异步执行的情况主动通知继续执行管道处理
        @param {str} run_id - 当前管道的运行id
        @param {kwargs} - 传入的预处理扩展参数
            conditions {dict} - 判断条件, 如果条件为False则跳过当前节点
                {'操作符': [('条件类型', {条件参数}), ...]}
                操作符支持: '$and' - 数组中的条件以and方式联合判断, '$or' - 数组中的条件以or方式联合判断, '$not' - 数组中的条件以and联合并对结果取反
                一个字典那的多个操作符以and联合, 例如: {'$and': [条件集合1], '$or': [条件集合2], '$not': [条件集合3]} 代表 (条件集合1结果) and (条件集合2结果) and (条件集合3结果)
                支持条件的嵌套, 例如 {'$and': [(条件1), {'$or': [(条件2), (条件3)]}]} 代表 (条件1结果) and (条件2 or 条件3)
                目前支持的条件类型包括:
                    pyexp - python脚本表达式, 条件参数为{'exp': '表达式脚本'}, 脚本中可以直接使用context和input_data变量
                        例如: {'$and': [('pyexp', {'exp': 'context["a"] == 10'}),]}
                    exists - 值(或key)是否在指定对象中, 条件参数为{'value': '判断值(或key)', 'obj_type': '检查对象获取类型', 'obj': 检查对象}
                        obj_type可设置为以下值:
                            instance - obj为直接给出的对象(默认)
                            strexp - obj为字符格式的对象(json), 例如: '{"a": "aval", "b": "bval"}', '[1, 2, 3]'
                            pyexp - obj为python表达式指定的变量, 脚本中可以直接使用context和input_data变量
                        例如: {'$and': [('exists', {'value': 'key', 'context["my_var"]'}),]}

        @returns {bool} - 是否继续执行该节点, True - 继续执行该节点, False - 跳过该节点直接执行下一个节点
        """
        _conditions = kwargs.get('conditions', None)
        if _conditions is None:
            # 没有条件, 默认为通过
            return True

        return ConditionTool.run_conditions(
            _conditions, globals={},
            locals={'context': context, 'input_data': input_data}
        )
