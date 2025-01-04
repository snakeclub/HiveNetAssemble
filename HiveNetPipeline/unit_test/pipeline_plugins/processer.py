#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试的管道处理器插件
@module processer
@file processer.py
"""

import os
import sys
import time
import threading
import uuid
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetPipeline import PipelineProcesser, SubPipeLineProcesser, Pipeline


class ProcesserAdd(PipelineProcesser):
    """
    将输入的对象加一个数值，从context获取num的值
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类，仅在装载的时候执行一次初始化动作
        """
        print('initialize processer ProcesserAdd!')

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserAdd'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值，供下一个处理器处理，异步执行的情况返回None
        """
        # 打印信息
        _num = context.get('num', 0)
        print('execute ProcesserAdd: %s + %s' % (str(input_data), str(_num)))
        # print('context: %s' % str(context))
        _output = input_data + _num
        print('ProcesserAdd output: %s' % str(_output))
        return _output


class ProcesserMultiply(PipelineProcesser):
    """
    将输入的对象乘以num再进行输出
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类，仅在装载的时候执行一次初始化动作
        """
        print('initialize processer ProcesserMultiply!')

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserMultiply'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值，供下一个处理器处理，异步执行的情况返回None
        """
        # 打印信息
        _num = context.get('num', 1)
        print('execute ProcesserMultiply: %s * %s' % (str(input_data), str(_num)))
        # print('context: %s' % str(context))
        _output = input_data * _num
        print('ProcesserMultiply output: %s' % str(_output))
        return _output


class ProcesserDivide(PipelineProcesser):
    """
    将输入的对象除以num再进行输出
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类，仅在装载的时候执行一次初始化动作
        """
        print('initialize processer ProcesserDivide!')

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserDivide'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值，供下一个处理器处理，异步执行的情况返回None
        """
        # 打印信息
        _num = context.get('num', 1)
        print('execute ProcesserDivide: %s / %s' % (str(input_data), str(_num)))
        # print('context: %s' % str(context))
        _output = input_data * _num
        print('ProcesserDivide output: %s' % str(_output))
        return _output


class ProcesserDivideBy(PipelineProcesser):
    """
    将以num除以输入的对象再进行输出
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类，仅在装载的时候执行一次初始化动作
        """
        print('initialize processer ProcesserDivideBy!')

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserDivideBy'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值，供下一个处理器处理，异步执行的情况返回None
        """
        # 打印信息
        _num = context.get('num', 1)
        print('execute ProcesserDivideBy: %s / %s' % (str(_num), str(input_data)))
        # print('context: %s' % str(context))
        _output = _num / input_data
        print('ProcesserDivide output: %s' % str(_output))
        return _output


class ProcesserAsynAdd(PipelineProcesser):
    """
    将输入的对象加一个数值，从context获取num的值（异步模式）
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类，仅在装载的时候执行一次初始化动作
        """
        print('initialize processer ProcesserAsynAdd!')

    @classmethod
    def is_asyn(cls) -> bool:
        """
        是否异步处理

        @returns {bool} - 标识处理器是否异步处理，返回Fasle代表管道要等待处理器执行完成
        """
        return True

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserAsynAdd'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值，供下一个处理器处理，异步执行的情况返回None
        """
        # 异步执行
        # 启动运行线程
        _running_thread = threading.Thread(
            target=cls._execute_thread_fun,
            name='ProcesserAsynAdd',
            args=(input_data, context, pipeline_obj, run_id,
                  pipeline_obj.current_node_id(run_id=run_id))
        )
        _running_thread.setDaemon(True)
        _running_thread.start()
        return None

    @classmethod
    def _execute_thread_fun(cls, input_data, context: dict, pipeline_obj, run_id: str, node_id: str):
        """
        异步执行线程函数
        """
        print('execute ProcesserAsynAdd: sleep 5s')
        time.sleep(5)
        # 打印信息
        _num = context.get('num', 0)
        print('execute ProcesserAsynAdd: %s + %s' % (str(input_data), str(_num)))

        _output = input_data + _num
        print('ProcesserAsynAdd output: %s' % str(_output))
        pipeline_obj.asyn_node_feeback(
            run_id, node_id, output=_output
        )
