#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
构建工具管道插件-获取系统信息并放入上下文

@module processer_get_sys_infos
@file processer_get_sys_infos.py
"""
import os
from HiveNetCore.utils.import_tool import DynamicLibManager
from HiveNetPipeline import PipelineProcesser
from HiveNetBuildTool.build import BuildPipeline


class ProcesserBuildGetSysInfos(PipelineProcesser):
    """
    获取系统信息(获取并放置到管道上下文的配置)

    建议节点配置标识(current_key): getSysInfos
    配置说明:
    Item Key: 获取信息唯一标识(自定义)
        infoType: str, 信息类型标识(extend_para.yaml中ProcesserGetSysInfos下的信息类型)
            注: 如果不设置代表使用Item Key作为信息类型标识
        getKey: str, 自定义写入上下文的信息获取key, 如果不设置则使用extend_para.yaml中对应信息类型的默认值
        args: list, 调用获取信息函数的固定位置入参, 根据实际extend_para.yaml中对应信息类型的获取函数要求传参
        kwargs: dict, 调用获取信息函数的key-value入参, 根据实际extend_para.yaml中对应信息类型的获取函数要求传参
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildGetSysInfos'

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
        _current_key = context.get('current_key', 'getSysInfos')
        _context_set_key = context.get('sys_infos_set_key', 'sysInfos')  # 要设置到上下文的系统信息key
        _config = context['build_config'].get(_current_key, None)

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 获取扩展参数配置
        _extend_para = BuildPipeline.get_processer_extend_para(cls.processer_name(), default={})

        # 初始化插件管理模块
        _lib_manager = DynamicLibManager(os.getcwd())

        # 遍历参数查询可支持的系统信息
        _infos = {}
        for _get_id, _get_para in _config.items():
            if _get_para is None:
                _get_para = {}

            # 获取信息查询函数
            _info_type = _get_para.get('infoType', _get_id)
            _info_para = _extend_para.get(_info_type, None)
            if _info_para is None:
                raise ModuleNotFoundError('Info type [%s] not found in extend para!' % _info_type)

            _func = _info_para.get('func', None)
            if _func is None:
                _func = _lib_manager.load_by_config(_info_para['libConfig'])
                if not callable(_func):
                    raise AttributeError('Info type [%s] is not callable!' % _info_type)

                _info_para['func'] = _func

            # 执行函数
            _get_key = _get_para.get('getKey', _info_para.get('getKey', _info_type))
            _infos[_get_key] = _func(
                *_get_para.get('args', []), **_get_para.get('kwargs', {})
            )

        # 将获取到的参数放入上下文
        context[_context_set_key] = _infos

        # 返回输出结果
        return input_data
