#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
构建工具管道插件-打印上下文指定信息

@module processer_print
@file processer_print.py
"""
import json
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetPipeline import PipelineProcesser


class ProcesserBuildPrint(PipelineProcesser):
    """
    打印上下文指定信息
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildPrint'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值, 供下一个处理器处理, 异步执行的情况返回None
        """
        # 获取当前要处理的标识
        _current_key = context.get('current_key', 'print')
        _config = context['build_config'].get(_current_key, None)

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 进行上下文打印处理
        for _step, _print_para in _config.items():
            _obj = ValueTool.get_dict_value_by_path(
                _print_para['path'], context, default_value=_print_para.get('default', None)
            )
            _show_tips = _print_para.get('showTips', None)
            _show_tips = '' if _show_tips is None else '%s: ' % _show_tips
            _obj_str = None

            # 尝试使用json方式打印
            if _obj is not None and _print_para.get('jsonPrint', True):
                try:
                    _obj_str = json.dumps(_obj, ensure_ascii=False, indent=2)
                except:
                    pass

            if _obj_str is None:
                _obj_str = str(_obj)

            print('%s%s' % (_show_tips, _obj_str))

        # 返回输出结果
        return input_data
