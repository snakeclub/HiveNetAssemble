#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
管道通用处理器插件模块
@module embed_processer
@file embed_processer.py
"""
import os
import sys
import uuid
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetPipeline import Pipeline, PipelineProcesser, SubPipeLineProcesser


class Null(PipelineProcesser):
    """
    不做任何操作的处理器
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称, 唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'Null'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str, **kwargs):
        """
        执行处理
        (可以为同步也可以为异步方法)

        @param {object} input_data - 处理器输入数据值, 除第一个处理器外, 该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文, 该字典信息将在整个管道处理过程中一直向下传递, 可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象, 作用如下:
            1、更新执行进度
            2、输出执行日志
            3、异步执行的情况主动通知继续执行管道处理
        @param {str} run_id - 当前管道的运行id
        @param {kwargs} - 传入的运行扩展参数

        @returns {object} - 处理结果输出数据值, 供下一个处理器处理, 异步执行的情况返回None
        """
        return input_data


class SubPipeline(SubPipeLineProcesser):
    """
    通用的子管道处理器
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'SubPipeline'

    @classmethod
    def get_sub_pipeline(cls, input_data, context: dict, pipeline_obj: Pipeline, run_id: str, sub_pipeline_para: dict):
        """
        获取子管道对象的函数

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 发起的管道对象
        @param {str} run_id - 当前管道的运行id
        @param {dict} sub_pipeline_para - 获取子管道对象的参数字典, 直接就是管道配置

        @returns {Pipeline} - 返回获取到的子管道对象
        """
        return Pipeline(
            str(uuid.uuid1()), sub_pipeline_para, is_asyn=False,
            asyn_notify_fun=pipeline_obj.asyn_notify_fun,
            running_notify_fun=pipeline_obj.running_notify_fun,
            end_running_notify_fun=pipeline_obj.end_running_notify_fun,
            logger=pipeline_obj.logger
        )
