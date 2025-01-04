#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
管道处理框架

@module pipeline
@file pipeline.py
"""

import os
import sys
import json
import copy
import inspect
import datetime
import threading
import traceback
from typing import List
import uuid
from collections import OrderedDict
from HiveNetCore.utils.run_tool import RunTool, AsyncTools
from HiveNetCore.utils.import_tool import ImportTool
from HiveNetCore.utils.file_tool import FileTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


PIPELINE_PLUGINS_VAR_NAME = 'PIPELINE_PLUGINS'  # 插件装载全局变量名


class Tools(object):
    """
    管道开发的工具函数
    """

    @classmethod
    def get_node_id_by_name(cls, node_name: str, pipeline_obj):
        """
        通过节点配置名获取节点id

        @param {str} node_name - 节点配置名
        @param {Pipeline} pipeline_obj - 管道对象

        @return {str} - 对应的节点id, 找不到返回None
        """
        for _key in pipeline_obj.pipeline.keys():
            if pipeline_obj.pipeline[_key]['name'] == node_name:
                return _key

        return None


class PipelinePredealer(object):
    """
    管道预处理器框架类
    """

    @classmethod
    def initialize(cls):
        """
        初始化处理类, 仅在装载的时候执行一次初始化动作
        """
        pass

    @classmethod
    def predealer_name(cls) -> str:
        """
        预处理器名称, 唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        raise NotImplementedError()

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

        @returns {bool} - 是否继续执行该节点, True - 继续执行该节点, False - 跳过该节点直接执行下一个节点
        """
        return True


class PipelineProcesser(object):
    """
    管道处理器框架类
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类, 仅在装载的时候执行一次初始化动作
        """
        pass

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称, 唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        raise NotImplementedError()

    @classmethod
    def is_asyn(cls) -> bool:
        """
        是否异步处理

        @returns {bool} - 标识处理器是否异步处理, 返回Fasle代表管道要等待处理器执行完成
        """
        return False

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
        raise NotImplementedError()


class PipelineRouter(object):
    """
    管道路由器框架类
    """

    @classmethod
    def initialize(cls):
        """
        初始化处理类, 仅在装载的时候执行一次初始化动作
        """
        pass

    @classmethod
    def router_name(cls) -> str:
        """
        路由器名称, 唯一标识路由器

        @returns {str} - 当前路由器名称
        """
        raise NotImplementedError()

    @classmethod
    def get_next(cls, output, context: dict, pipeline_obj, run_id: str, **kwargs):
        """
        获取路由下一节点

        @param {object} output - 上一个节点的输出结果
        @param {dict} context - 上下文字典
        @param {Pipeline} pipeline_obj - 管道对象
        @param {str} run_id - 当前管道的运行id
        @param {kwargs} - 传入的扩展参数

        @returns {str} - 下一节点的配置id, 如果是最后的节点, 返回None
        """
        raise NotImplementedError()


class SubPipeLineProcesser(object):
    """
    子管道处理器
    """
    @classmethod
    def initialize(cls):
        """
        初始化处理类, 仅在装载的时候执行一次初始化动作
        """
        pass

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称, 唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        raise NotImplementedError()

    @classmethod
    def is_asyn(cls) -> bool:
        """
        是否异步处理

        @returns {bool} - 标识处理器是否异步处理, 返回Fasle代表管道要等待处理器执行完成
        """
        return False

    @classmethod
    def get_sub_pipeline(cls, input_data, context: dict, pipeline_obj, run_id: str, sub_pipeline_para: dict, **kwargs):
        """
        获取子管道对象的函数

        @param {object} input_data - 处理器输入数据值, 除第一个处理器外, 该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文, 该字典信息将在整个管道处理过程中一直向下传递, 可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 发起的管道对象
        @param {str} run_id - 当前管道的运行id
        @param {dict} sub_pipeline_para - 获取子管道对象的参数字典
        @param {kwargs} - 传入的运行扩展参数

        @returns {Pipeline} - 返回获取到的子管道对象(注意该子管道对象的使用模式必须与is_asyn一致)
        """
        raise NotImplementedError()

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str, sub_pipeline_obj,
                is_step_by_step: bool = False,
                is_resume: bool = False, run_to_end: bool = False, **kwargs):
        """
        执行处理
        (可以为同步也可以为异步方法)

        @param {object} input_data - 处理器输入数据值, 除第一个处理器外, 该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文, 该字典信息将在整个管道处理过程中一直向下传递, 可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 发起的管道对象
        @param {str} run_id - 当前管道的运行id
        @param {Pipeline} sub_pipeline_obj - 要执行的子管道对象
        @param {bool} is_step_by_step=False - 是否逐步执行, 即执行一步就pause, 通过resume执行下一步
        @param {bool} is_resume=False - 是否恢复执行的模式
        @param {bool} run_to_end=False - 当设置了step_by_step模式时, 可以通过该参数指定执行到结尾
        @param {kwargs} - 传入的运行扩展参数

        @returns {str, str, object} - 同步情况返回 run_id, status, output, 异步情况返回的status为R
        """
        if is_resume:
            # 恢复模式
            return sub_pipeline_obj.resume(run_id=run_id, run_to_end=run_to_end)
        else:
            # 重新启动模式
            return sub_pipeline_obj.start(
                input_data=input_data, context=context, run_id=run_id, is_step_by_step=is_step_by_step
            )


class Pipeline(object):
    """
    管道控制框架
    """

    #############################
    # 静态工具函数
    #############################
    @classmethod
    def add_plugin(cls, class_obj):
        """
        添加插件

        @param {object} class_obj - 插件类
        """
        # 获取插件字典
        _plugins = RunTool.get_global_var(PIPELINE_PLUGINS_VAR_NAME)
        if _plugins is None:
            _plugins = {
                'predealer': dict(),
                'processer': dict(),
                'router': dict()
            }
            RunTool.set_global_var(PIPELINE_PLUGINS_VAR_NAME, _plugins)

        # 判断类型
        _type_fun = getattr(class_obj, 'processer_name', None)
        if _type_fun is not None and callable(_type_fun):
            _plugin_type = 'processer'
        else:
            _type_fun = getattr(class_obj, 'router_name', None)
            if _type_fun is not None and callable(_type_fun):
                _plugin_type = 'router'
            else:
                _type_fun = getattr(class_obj, 'predealer_name', None)
                if _type_fun is not None and callable(_type_fun):
                    _plugin_type = 'predealer'
                else:
                    # 不是标准插件类
                    return

        # 执行初始化
        class_obj.initialize()

        # 放入插件配置
        _plugins[_plugin_type][_type_fun()] = class_obj

    @classmethod
    def load_plugins_by_path(cls, path: str):
        """
        装载指定目录下的管道插件(处理器和路由器)

        @param {str} path - 要装载的目录
        """
        _file_list = FileTool.get_filelist(path=path, regex_str=r'.*\.py$', is_fullname=True)
        for _file in _file_list:
            if _file == '__init__.py':
                continue

            cls.load_plugins_by_file(_file)

    @classmethod
    def load_plugins_by_file(cls, file: str):
        """
        装载指定文件的管道插件

        @param {str} file - 模块文件路径
        """
        # 执行加载
        _file = os.path.realpath(file)
        if not _file.endswith('.py'):
            raise AttributeError('not supported plugins file [%s]!' % _file)

        _module_name = os.path.split(_file)[1][0: -3]
        _module = ImportTool.import_module(
            _module_name, extend_path=os.path.split(_file)[0], is_force=True)
        _clsmembers = inspect.getmembers(_module, inspect.isclass)
        for (_class_name, _class) in _clsmembers:
            if _module.__name__ != _class.__module__:
                # 不是当前模块定义的函数
                continue

            cls.add_plugin(_class)

    @classmethod
    def load_plugins_embed(cls):
        """
        装载集成的管道插件
        """
        _path = os.path.abspath(os.path.dirname(__file__))
        cls.load_plugins_by_file(os.path.join(_path, 'embed_predealer.py'))
        cls.load_plugins_by_file(os.path.join(_path, 'embed_router.py'))
        cls.load_plugins_by_file(os.path.join(_path, 'embed_processer.py'))

    @classmethod
    def get_plugin(cls, plugin_type: str, name: str):
        """
        获取制定插件

        @param {str} plugin_type - 插件类型
            predealer - 预处理器
            processer - 处理器
            router - 路由器
        @param {str} name - 插件名称

        @returns {object} - 插件类对象, 如果找不到返回None
        """
        # 获取插件字典
        _plugins = RunTool.get_global_var(PIPELINE_PLUGINS_VAR_NAME)
        if _plugins is None:
            _plugins = {
                'predealer': dict(),
                'processer': dict(),
                'router': dict()
            }
            RunTool.set_global_var(PIPELINE_PLUGINS_VAR_NAME, _plugins)

        return _plugins.get(plugin_type, dict()).get(name, None)

    #############################
    # 构造函数
    #############################
    def __init__(self, name: str, pipeline_config, is_asyn=False, asyn_notify_fun=None,
                 running_notify_fun=None, end_running_notify_fun=None,
                 logger=None):
        """
        构造函数

        @param {str} name - 管道名称
        @param {str|dict|list} pipeline_config - 管道配置, 支持传入3种类型:
            str - json字符(可以是字典模式或数组模式)
            dict - 配置字典, 例如{"1": {节点1配置}, "2": {节点2配置}, ...}, 注意节点顺序必须是从1开始的连续整数
            list - 配置数组, 例如[{节点1配置}, {节点2配置}, ...], 比字典模式简单, 会自动生成连续的节点顺序
               注: 节点配置说明如下
               {
                    "name": "节点配置名",
                    "predealer": "预处理器名",  # 在正式执行节点前先执行预处理器, 预处理器的返回值可以控制是否跳过当前节点, 置空代表不执行预处理
                    "predealer_execute_para": {},  # 预处理器执行的传入参数, 作为**kwargs传入预处理器, 置空或不设置值的情况传入{}
                    "processor": "处理器名",
                    "processor_execute_para": {},  # 处理器执行的传入参数, 作为**kwargs传入执行函数, 置空或不设置值的情况传入{}
                    "is_sub_pipeline": False,  # 该子节点处理器是否子管道处理器
                    "sub_pipeline_para": {},  # 生成子管道的参数, 由处理器具体实现来定义
                    "context": {},  # 要更新的上下文字典, 执行处理器前将更新该上下文
                    "router": "",  # 路由器名, 执行完将执行该路由器找下一个执行节点, 置空或不设置值的情况直接按顺序找下一个节点
                    "router_para": {}, # 路由器的传入参数, 作为**kwargs传入路由器, 置空或不设置值的情况传入{}
                    "exception_router": "", 执行处理器出现异常时执行的路由器名, 置空或不设置值将抛出异常并结束管道执行
                    "exception_router_para": {}  # 异常路由器的传入参数,  作为**kwargs传入路由器, 置空或不设置值的情况传入{}
                }
        @param {bool} is_asyn=False - 是否异步返回结果
        @param {function} asyn_notify_fun=None - 异步结果通知函数, 格式如下:
            fun(name, run_id, status, context, output, pipeline)
                name {str} - 管道名称
                run_id {str} - 运行id
                status {str} - 管道状态
                context {dict} - 当前上下文
                output {object} - 管道输出数据
                pipeline {Pipeline} - 管道对象
            注: 该函数可以为同步也可以为异步函数
        @param {function} running_notify_fun=None = 节点运行通知函数, 格式如下:
            fun(name, run_id, node_id, node_name, pipeline)
                name {str} - 管道名称
                run_id {str} - 运行id
                node_id {str} - 运行节点id
                node_name {str} - 运行节点配置名
                pipeline {Pipeline} - 管道对象
            注: 该函数可以为同步也可以为异步函数
        @param {function} end_running_notify_fun=None = 节点运行完成通知函数, 格式如下:
            fun(name, run_id, node_id, node_name, status, status_msg, pipeline)
                name {str} - 管道名称
                run_id {str} - 运行id
                node_id {str} - 运行节点id
                node_name {str} - 运行节点配置名
                status {str} 执行状态, 'S' - 成功, 'E' - 出现异常, 'K' - 跳过节点
                status_msg {str} 状态描述, 当异常时送入异常信息
                pipeline {Pipeline} - 管道对象
            注: 该函数可以为同步也可以为异步函数
        @param {Simple_log.Logger} logger=None - 日志对象
        """
        self.logger = logger
        self.name = name

        # 处理节点配置参数
        _temp_pipeline = None
        if type(pipeline_config) == str:
            _temp_pipeline = json.loads(pipeline_config)
        else:
            _temp_pipeline = copy.deepcopy(pipeline_config)

        if isinstance(_temp_pipeline, (frozenset, list, set, tuple,)):
            # 数组处理
            self.pipeline = dict()
            _current_index = 1
            for _node_config in pipeline_config:
                self.pipeline[str(_current_index)] = _node_config
                _current_index += 1
        else:
            self.pipeline = _temp_pipeline

        # 其他参数设置
        self.is_asyn = is_asyn  # 是否异步
        self.asyn_notify_fun = asyn_notify_fun  # 异步结果通知函数
        self.running_notify_fun = running_notify_fun
        self.end_running_notify_fun = end_running_notify_fun

        # 如果是同步模式, 检查每个节点的插件是否有异步的情况
        if not self.is_asyn:
            for _node in self.pipeline.values():
                if self.get_plugin('processer', _node['processor']).is_asyn():
                    raise AttributeError('Pipeline has asynchronous processor!')

        # 管道状态及临时变量缓存字典(采取有序字典), key为run_id, value为字典:
        #   status_lock {Lock} - 异步运行的线程锁, threading.Lock()
        #   status {str} - 执行状态, 默认为 'I'
        #   context {dict} - 上下文对象
        #   current_input {object} - 当前执行环节输入数据
        #   current_process_info {dict} - 当前节点的运行状态
        #       total {int} - 总任务数
        #       done {int} - 已完成任务数
        #       job_msg {str} - 当前任务执行信息
        #   output {object} - 最终输出结果
        #   thread_running {bool} - 标识线程是否还在运行
        #   is_step_by_step {bool} - 是否采取逐步执行的方式处理
        #   running_sub_node_id {str} - 正在执行的子管道节点id
        #   is_resume {bool} - 是否通过resume恢复执行
        #   run_to_end {bool} - resume的run_to_end参数值
        #   trace_list {list} - 执行追踪列表, 按顺序放入执行信息, 每个执行信息包括
        #       node_id {str} 节点配置id
        #       node_name {str} 节点配置名
        #       processor_name {str} 处理器名
        #       start_time {str} 开始时间, 格式为'%Y-%m-%d %H:%M:%S.%f'
        #       end_time {str} 结束时间, 格式为'%Y-%m-%d %H:%M:%S.%f'
        #       status {str} 执行状态, 'S' - 成功, 'E' - 出现异常, 'K' - 跳过节点
        #       status_msg {str} 状态描述, 当异常时送入异常信息
        #       router_name : 路由名(直线路由可以不设置路由器)
        #       is_sub_pipeline {bool} 是否子管道执行
        #       sub_name {str} - 子管道名称
        #       sub_trace_list {list} 子管道执行的trace_list
        #   node_id {str} 当前节点配置id
        #   node_status {str} I-初始化, R-正在执行, E-执行失败,  S-执行成功, P-子管道暂停
        #   node_status_msg {str} - 当前节点执行状态信息
        #   start_time {str} 当前节点执行开始时间, 格式为'%Y-%m-%d %H:%M:%S.%f'
        self._cache = OrderedDict()

        # 管道线程锁对象, 主要目的是要将线程锁对象从缓存中剥离出来, 保证缓存的可序列化
        # key为run_id, value为异步运行的线程锁, threading.Lock()
        self._status_locks = dict()

        # 缓存的正在执行的子管道对象, key为run_id, value为子管道对象
        self.running_sub_pipeline = dict()

        # 最后一次执行的管道运行ID
        self._last_run_id = ''
        self._last_run_id_lock = threading.Lock()  # id处理的锁

    #############################
    # 管道状态查询
    #############################
    def status(self, run_id: str = None):
        """
        获取管道运行状态

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {str} - 当前状态, I-初始化, P-暂停, R-运行中, S-成功结束, E-异常结束
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        self._status_locks[_run_id].acquire()
        try:
            return _run_cache['status']
        finally:
            self._status_locks[_run_id].release()

    def output(self, run_id: str = None):
        """
        获取管道运行输出结果

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {object} - 管道输出结果, 如果管道运行未完成则返回None
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        self._status_locks[_run_id].acquire()
        try:
            if _run_cache['status'] == 'S':
                return _run_cache['output']
            else:
                return None
        finally:
            self._status_locks[_run_id].release()

    def context(self, run_id: str = None):
        """
        获取管道当前上下文

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {dict} - 当前上下文字典
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        return _run_cache['context']

    def trace_list(self, run_id: str = None):
        """
        获取管道当前执行追踪列表

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {list} - 当前执行追踪列表
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        return _run_cache['trace_list']

    def current_node_id(self, run_id: str = None) -> str:
        """
        获取管道运行的当前节点ID

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {str} - 当前运行的节点id
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        return _run_cache.get('node_id', '')

    def current_node_status(self, run_id: str = None) -> str:
        """
        获取管道运行的当前节点状态

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {str} - 当前节点运行状态, I-初始化, R-正在执行, E-执行失败,  S-执行成功, P-子管道暂停
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        return _run_cache.get('node_status', '')

    def current_node_status_msg(self, run_id: str = None) -> str:
        """
        获取管道运行的当前节点状态信息
        异常时可以获取异常报错信息

        @param {str} run_id=None - 要获取的管道运行ID
            注: 如果不传入则获取最后执行的管道ID

        @returns {str} - 执行状态信息
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        return _run_cache.get('node_status_msg', '')

    #############################
    # 处理函数
    #############################
    def start(self, input_data=None, context: dict = None, run_id: str = None, is_step_by_step: bool = False):
        """
        执行管道(从第一个节点开始执行)

        @param {object} input_data=None - 初始输入数据值
        @param {dict} context=None - 初始上下文
        @param {str} run_id=None - 指定的管道运行ID
        @param {bool} is_step_by_step=False - 是否逐步执行, 即执行一步就pause, 通过resume执行下一步

        @returns {str, str, object} - 同步情况返回 run_id, status, output, 异步情况返回status为R

        @throws {RuntimeError} - 当状态为R、P时抛出异常
        """
        # 处理运行id
        _run_id = run_id
        if _run_id is None:
            _run_id = str(uuid.uuid1())

        _temp_id, _run_cache = self._get_run_cache(_run_id)
        if _run_cache is None:
            _run_cache = {
                'status': 'I',
                'context': {},
                'current_input': None,
                'current_process_info': dict(),
                'output': None,
                'thread_running': False,
                'is_step_by_step': is_step_by_step,
                'trace_list': list()
            }
            # 加入到清单
            self._cache[_run_id] = _run_cache
            self._status_locks[_run_id] = threading.Lock()
            self._change_last_run_id(_run_id)

        # 初始化变量
        self._status_locks[_run_id].acquire()
        try:
            if _run_cache['status'] in ('R', 'P'):
                _msg = 'Pipeline [%s] is running!' % self.name
                self.log_error('Error: ' % _msg)
                raise RuntimeError(_msg)

            # 初始化变量
            _run_cache['current_input'] = input_data
            # 注意字典不能直接附值, 否则可能会出现两次运行地址一样的情况
            if context is None:
                _run_cache['context'] = dict()
            else:
                _run_cache['context'] = copy.deepcopy(context)
            _run_cache['node_id'] = "1"
            _run_cache['node_status'] = 'I'
            _run_cache['trace_list'] = list()
            _run_cache['output'] = None
            _run_cache['status'] = 'R'
            _run_cache['running_sub_node_id'] = ''
            _run_cache['is_resume'] = False
            _run_cache['run_to_end'] = False
        finally:
            self._status_locks[_run_id].release()

        if self.is_asyn:
            # 异步执行, 启动任务执行线程
            self._start_running_thread(_run_id)
            return _run_id, 'R', None
        else:
            # 同步执行, 直接执行线程函数就好
            self._running_thread_fun(_run_id)
            return _run_id, _run_cache['status'], _run_cache['output']

    def pause(self, run_id: str = None):
        """
        暂停管道执行

        @param {str} run_id=None - 要暂停的管道运行ID
            注: 如果不传入则获取最后执行的管道ID
        """
        if not self.is_asyn:
            # 非异步模式不支持
            raise RuntimeError("Pipeline is not asynchronous!")

        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        if _run_cache['status'] != 'R':
            _msg = 'Pipeline [%s] not running!' % self.name
            self.log_error('Error: ' % _msg)
            raise RuntimeError(_msg)

        # 只要设置管道状态为 P 即可
        self._set_status('P', run_id=_run_id)
        if self.pipeline[_run_cache['node_id']].get('is_sub_pipeline', False):
            # 正在执行子管道, 对子管道也添加暂停的指令
            try:
                self.running_sub_pipeline[_run_id].pause(run_id=_run_id)
            except:
                pass

        while _run_cache['thread_running']:
            # 等待运行线程结束
            RunTool.sleep(0.01)

        # 记录日志
        self.log_info('Pipeline [%s] pause!' % self.name)

    def resume(self, run_id: str = None, run_to_end: bool = False):
        """
        从中断点重新执行

        @param {str} run_id=None - 要处理的管道运行ID
            注: 如果不传入则获取最后执行的管道ID
        @param {bool} run_to_end=False - 当设置了step_by_step模式时, 可以通过该参数指定执行到结尾

        @returns {str, str, object} - 同步情况返回 run_id, status, output, 异步情况返回的status为R
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        if _run_cache['status'] not in ['P', 'E']:
            _msg = 'Pipeline [%s] status is not pause or exception!' % self.name
            self.log_error('Error: ' % _msg)
            raise RuntimeError(_msg)

        if _run_cache['status'] == 'E':
            # 从异常的节点重新发起
            _run_cache['node_status'] = 'I'

        # 修改状态为运行中
        self._set_status('R', _run_id)

        # 设置重新执行的标识
        _run_cache['is_resume'] = True
        _run_cache['run_to_end'] = run_to_end

        # 将step_by_step模式关闭
        if run_to_end:
            _run_cache['is_step_by_step'] = False

        # 恢复处理
        if self.is_asyn:
            # 异步模式
            self._start_running_thread(_run_id)
            self.log_info('Pipeline [%s] resume!' % self.name)
            return _run_id, 'R', None
        else:
            # 同步模式
            self._running_thread_fun(_run_id)
            return _run_id, _run_cache['status'], _run_cache['output']

    def remove(self, run_id: str = None):
        """
        删除指定管道执行

        @param {str} run_id=None - 要处理的管道运行ID
            注: 如果不传入则获取最后执行的管道ID
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        if _run_cache['status'] == 'R':
            _msg = 'Pipeline [%s] [%s] status is running!' % (self.name, _run_id)
            self.log_error('Error: ' % _msg)
            raise RuntimeError(_msg)

        # 删除管道
        self._last_run_id_lock.acquire()
        try:
            self._cache.pop(_run_id)
            self._status_locks.pop(_run_id)
            if _run_id == self._last_run_id:
                # 将最后一个id置值
                if len(self._cache) > 0:
                    self._last_run_id = next(reversed(self._cache))
                else:
                    self._last_run_id = ''
        finally:
            self._last_run_id_lock.release()

    def save_checkpoint(self, run_id: str = None) -> str:
        """
        将运行状态保存为json串, 用于后续恢复

        @param {str} run_id=None - 管道运行id, 如果不传代表保存所有管道当前状态

        @param {str} - 所保存的管道运行状态json串
        """
        if run_id is None:
            _run_id_list = list(self._cache.keys())
        else:
            if run_id not in self._cache.keys():
                raise RuntimeError("Run id not exists!")
            _run_id_list = [run_id, ]

        # 进行转换处理
        _cache = OrderedDict()
        for _run_id in _run_id_list:
            if self.status(_run_id) == 'R':
                raise RuntimeError("Run id [%s] is running!" % _run_id)

            _cache[_run_id] = self._cache[_run_id]

            # 增加对正在运行的子管道的保存
            if self.running_sub_pipeline.get(_run_id, None) is not None:
                _cache[_run_id]['running_sub_pipeline'] = self.running_sub_pipeline[_run_id].save_checkpoint(
                    run_id=_run_id
                )

        return json.dumps(_cache, ensure_ascii=False)

    def load_checkpoint(self, json_str: str, ignore_exists: bool = False):
        """
        装载所保存的运行状态
        注: 如果run_id重复则不导入

        @param {str} json_str - 所保存的管道运行状态json串
        @param {bool} ignore_exists=False - 是否忽略已存在运行管道
        """
        _cache: OrderedDict = json.loads(
            json_str, object_pairs_hook=OrderedDict
        )

        # 检查是否run_id已存在
        if not ignore_exists:
            for _run_id in _cache.keys():
                if _run_id in self._cache.keys():
                    # 如果运行id已存在则抛出异常
                    raise RuntimeError('run id [%s] already exists!' % _run_id)

        # 遍历放入运行状态
        for _run_id, _run_cache in _cache.items():
            if _run_id in self._cache.keys():
                # 如果运行id已存在, 不处理
                continue

            # 正在运行的子管道支持
            _sub_pipeline_json = _run_cache.get('running_sub_pipeline', None)
            if _sub_pipeline_json is not None:
                # 装载子管道
                _node_config = self.pipeline[_run_cache['node_id']]
                _processer = self.get_plugin('processer', _node_config['processor'])
                _sub_pipeline = _processer.get_sub_pipeline(
                    _run_cache['current_input'], _run_cache['context'], self, _run_id,
                    _node_config.get('sub_pipeline_para', {}),
                    **_node_config.get('processor_execute_para', {})
                )
                _sub_pipeline.load_checkpoint(_sub_pipeline_json, ignore_exists)
                self.running_sub_pipeline[_run_id] = _sub_pipeline

                # 移除配置子管道配置
                _run_cache.pop('running_sub_pipeline')

            self._cache[_run_id] = _run_cache
            self._status_locks[_run_id] = threading.Lock()
            self._change_last_run_id(_run_id)

    def asyn_node_feeback(self, run_id: str, node_id: str, output=None, status: str = 'S',
                          status_msg: str = 'S', context: dict = {}):
        """
        异步节点执行结果反馈

        @param {str} run_id - 运行id
        @param {str} node_id - 节点配置id
        @param {object} output=None - 节点执行输出结果
        @param {str} status='S' - 节点运行状态, 'S' - 成功, 'E' - 出现异常, 'P' - 暂停
        @param {str} status_msg='success' - 运行状态描述
        @param {dict} context={} - 要修改的上下文信息
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            _msg = '[Pipeline:%s] run_id [%s] not exists!' % (self.name, run_id)
            self.log_error('Error: ' % _msg)
            raise AttributeError(_msg)

        if _run_cache['node_id'] != node_id:
            _msg = '[Pipeline:%s] Not correct node id [%s]!' % (self.name, node_id)
            self.log_error('Error: ' % _msg)
            raise AttributeError(_msg)

        _run_cache['context'].update(context)
        _next_id = self._run_router(_run_id, node_id, output=output,
                                    status=status, status_msg=status_msg)
        if _next_id is not None:
            # 设置上下文, 执行下一个节点
            _run_cache['node_id'] = _next_id
            _run_cache['node_status'] = 'I'

            # 启动处理线程
            if _run_cache['status'] == 'R':
                self._start_running_thread(_run_id)

    def node_process_feeback(self, run_id: str, node_id: str,
                             total: int = None, done: int = None, job_msg: str = None):
        """
        节点进度反馈函数
        供节点运行过程中更新进度信息

        @param {str} run_id - 运行id
        @param {str} node_id - 节点id
        @param {int} total=None - 节点运行进度总任务数, 不送代表不更新
        @param {int} done=None - 节点运行进度当前完成数, 不送代表不更新
        @param {str} job_msg=None - 任务信息, 不送代表不更新
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            _msg = '[Pipeline:%s] run_id [%s] not exists!' % (self.name, run_id)
            self.log_error('Error: ' % _msg)
            raise AttributeError(_msg)

        if _run_cache['node_id'] == node_id:
            if total is not None:
                _run_cache['current_process_info']['total'] = total
            if done is not None:
                _run_cache['current_process_info']['done'] = done
            if job_msg is not None:
                _run_cache['current_process_info']['job_msg'] = job_msg

            self.log_debug('[Pipeline:%s] [%s] Node [%s] process %s/%s: %s!' %
                           (
                               self.name, _run_id, node_id,
                               str(_run_cache['current_process_info'].get('done', 0)),
                               str(_run_cache['current_process_info'].get('total', 1)),
                               _run_cache['current_process_info'].get('job_msg', '')
                           ))

    def get_node_process(self, run_id: str, node_id: str):
        """
        获取当前节点运行进度

        @param {str} run_id - 运行id
        @param {str} node_id - 节点配置id

        @returns {int, int, str} - 返回 total, done, job_msg 进度信息
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            _msg = '[Pipeline:%s] run_id [%s] not exists!' % (self.name, run_id)
            self.log_error('Error: ' % _msg)
            raise AttributeError(_msg)

        if _run_cache['node_id'] == node_id:
            _total = _run_cache['current_process_info'].get('total', 1)
            _done = _run_cache['current_process_info'].get('done', 0)
            _job_msg = _run_cache['current_process_info'].get('job_msg', '')
            return _total, _done, _job_msg
        else:
            # 非当前节点, 返回完成状态
            return 1, 1, ''

    #############################
    # 日志函数
    #############################

    def log_info(self, msg: str, *args, **kwargs):
        """
        输出info日志

        @param {str} msg - 要输出的日志
        """
        if self.logger:
            if 'extra' not in kwargs:
                kwargs['extra'] = {'callFunLevel': 2}

            self.logger.info(msg, *args, **kwargs)

    def log_debug(self, msg: str, *args, **kwargs):
        """
        输出debug日志

        @param {str} msg - 要输出的日志
        """
        if self.logger:
            if 'extra' not in kwargs:
                kwargs['extra'] = {'callFunLevel': 2}

            self.logger.debug(msg, *args, **kwargs)

    def log_error(self, msg: str, *args, **kwargs):
        """
        输出error日志

        @param {str} msg - 要输出的日志
        """
        if self.logger:
            if 'extra' not in kwargs:
                kwargs['extra'] = {'callFunLevel': 2}

            self.logger.error(msg, *args, **kwargs)

    def log_warning(self, msg: str, *args, **kwargs):
        """
        输出warning日志

        @param {str} msg - 要输出的日志
        """
        if self.logger:
            if 'extra' not in kwargs:
                kwargs['extra'] = {'callFunLevel': 2}

            self.logger.warning(msg, *args, **kwargs)

    #############################
    # 内部函数
    #############################

    def _get_run_cache(self, run_id: str) -> dict:
        """
        获取指定管道运行id的运行缓存

        @param {str} run_id - 要获取的管道运行id

        @returns {str, dict} - 运行id, 运行缓存字典, 如果获取不到则返回 None, None
        """
        _run_id = run_id if run_id is not None else self._last_run_id
        _run_cache = self._cache.get(_run_id, None)
        if _run_cache is None:
            _run_id = None
        return _run_id, _run_cache

    def _change_last_run_id(self, run_id: str):
        """
        更新最后一个run_id的值

        @param {str} run_id - 要更新的运行id值
        """
        self._last_run_id_lock.acquire()
        self._last_run_id = run_id
        self._last_run_id_lock.release()

    def _set_status(self, status: str, run_id: str):
        """
        设置状态值

        @param {str} status - 要设置的状态字符串
        @param {str} run_id - 要处理的管道运行ID
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            raise RuntimeError("Run id not exists!")

        self._status_locks[_run_id].acquire()
        try:
            _run_cache['status'] = status
        finally:
            self._status_locks[_run_id].release()

    def _run_node(self, run_id: str, node_id: str):
        """
        执行处理节点

        @param {str} run_id - 运行id
        @param {str} node_id - 要执行的节点ID

        @returns {str} - 返回下一节点ID, 返回None代表结束管道执行, 返回空字符串''代表异步处理
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            _msg = '[Pipeline:%s] run_id [%s] not exists!' % (self.name, run_id)
            self.log_error('Error: ' % _msg)
            raise RuntimeError(_msg)

        _node_config = self.pipeline[node_id]
        # 执行节点处理器
        try:
            _run_cache['node_id'] = node_id
            _run_cache['node_status'] = 'R'
            _run_cache['start_time'] = datetime.datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S.%f')
            _run_cache['current_process_info']['total'] = 1
            _run_cache['current_process_info']['done'] = 0
            _run_cache['current_process_info']['job_msg'] = ''
            _run_cache['context'].update(_node_config.get('context', {}))

            # 通知开始运行节点
            self.log_debug('[Pipeline:%s] Start running [%s] node [%s]' %
                           (self.name, _run_id, node_id))
            if self.running_notify_fun is not None:
                AsyncTools.sync_run_coroutine(
                    self.running_notify_fun(
                        self.name, _run_id, node_id,
                        _node_config.get('name', ''), self
                    )
                )

            # 执行节点的预处理
            _predealer_name = _node_config.get('predealer', None)
            if _predealer_name is not None:
                _predealer: PipelinePredealer = self.get_plugin('predealer', _predealer_name)
                if _predealer is None:
                    raise ModuleNotFoundError('predealer [%s] is not found' % _predealer_name)

                # 执行获取当前节点的处理指令
                self.log_debug('[Pipeline:%s] Running [%s] node [%s] predealer [%s]' %
                    (self.name, _run_id, node_id, _predealer_name)
                )
                _predeal_result = _predealer.pre_deal(
                    _run_cache['current_input'], _run_cache['context'], self, _run_id,
                    **_node_config.get('predealer_execute_para', {})
                )

                if not _predeal_result:
                    # 需要跳过当前节点的执行
                    return self._run_router(
                        _run_id, node_id, output=_run_cache['current_input'], status='K', status_msg='skip'
                    )

            # 运行节点
            _processer: PipelineProcesser = self.get_plugin('processer', _node_config['processor'])
            if _node_config.get('is_sub_pipeline', False):
                # 运行的是子管道, 首先获取当前管道对象, 如果是已存在的管道对象, 按恢复方式获取
                _sub_pipeline = self.running_sub_pipeline.get(_run_id, None)
                if _sub_pipeline is None:
                    _sub_pipeline = _processer.get_sub_pipeline(
                        _run_cache['current_input'], _run_cache['context'], self, _run_id,
                        _node_config.get('sub_pipeline_para', {}),
                        **_node_config.get('processor_execute_para', {})
                    )
                    self.running_sub_pipeline[_run_id] = _sub_pipeline  # 缓存子管道

                # 检查启动参数是否与当前节点一致, 如果不一致修改为准确的值
                if _run_cache.get('running_sub_node_id', '-1') != node_id:
                    _run_cache['running_sub_node_id'] = node_id
                    _run_cache['is_resume'] = False
                    _run_cache['run_to_end'] = False

                if _processer.is_asyn():
                    # 异步处理, 发起执行后直接返回''
                    AsyncTools.sync_run_coroutine(
                        _processer.execute(
                            _run_cache['current_input'], _run_cache['context'], self, _run_id,
                            _sub_pipeline, is_step_by_step=_run_cache['is_step_by_step'],
                            is_resume=_run_cache.get('is_resume', False),
                            run_to_end=_run_cache.get('run_to_end', False),
                            **_node_config.get('processor_execute_para', {})
                        )
                    )
                    return ''
                else:
                    # 同步处理, 获取执行3个返回要素
                    _, _status, _output = AsyncTools.sync_run_coroutine(
                        _processer.execute(
                            _run_cache['current_input'], _run_cache['context'], self, _run_id,
                            _sub_pipeline, is_step_by_step=_run_cache['is_step_by_step'],
                            is_resume=_run_cache.get('is_resume', False),
                            run_to_end=_run_cache.get('run_to_end', False),
                            **_node_config.get('processor_execute_para', {})
                        )
                    )
                    return self._run_router(
                        _run_id, node_id, output=_output, status=_status,
                        status_msg=_sub_pipeline.current_node_status_msg(run_id=_run_id)
                    )
            else:
                # 运行当前管道任务
                if _processer.is_asyn():
                    # 异步处理, 发起执行后直接返回''
                    AsyncTools.sync_run_coroutine(
                        _processer.execute(
                            _run_cache['current_input'], _run_cache['context'], self, _run_id,
                            **_node_config.get('processor_execute_para', {})
                        )
                    )
                    return ''
                else:
                    # 同步处理
                    _output = AsyncTools.sync_run_coroutine(
                        _processer.execute(
                            _run_cache['current_input'], _run_cache['context'], self, _run_id,
                            **_node_config.get('processor_execute_para', {})
                        )
                    )
                    return self._run_router(_run_id, node_id, output=_output, status='S', status_msg='success')
        except:
            _status_msg = traceback.format_exc()
            self.log_warning('Warning: [Pipeline:%s] Running [%s] node [%s] error: %s' %
                             (self.name, _run_id, node_id, _status_msg))
            # 异常情况, output跟原来的input一致
            return self._run_router(_run_id, node_id, output=_run_cache['current_input'], status='E', status_msg=_status_msg)

    def _run_router(self, run_id: str, node_id: str, output=None, status: str = 'S', status_msg: str = 'success') -> str:
        """
        执行路由判断

        @param {str} run_id - 运行id
        @param {str} node_id - 当前运行的节点
        @param {object} output=None - 节点执行输出结果
        @param {str} status='S' - 节点运行状态, 'S' - 成功, 'E' - 出现异常, 'P' - 子管道暂停, 'K' - 跳过节点执行
        @param {str} status_msg='success' - 运行状态描述

        @returns {str} - 返回下一节点ID, 如果已是最后节点返回None
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            _msg = '[Pipeline:%s] run_id [%s] not exists!' % (self.name, run_id)
            self.log_error('Error: ' % _msg)
            raise RuntimeError(_msg)

        # 登记执行任务
        _run_cache['node_status_msg'] = status_msg

        _node_config = self.pipeline[node_id]
        _router_name = ''
        _router_para = {}
        if status == 'E' and _node_config.get('exception_router', '') != '':
            _router_name = _node_config['exception_router']
            _router_para = _node_config.get('exception_router_para', {})
        elif status == 'S':
            _router_name = _node_config.get('router', '')
            _router_para = _node_config.get('router_para', {})
        elif status == 'K':
            # 跳过节点
            _router_name = ''
            _router_para = {}

        # 对子管道执行进行处理
        _is_sub_pipeline = _node_config.get('is_sub_pipeline', False)
        _sub_name = ''
        _sub_trace_list = []
        if status != 'K' and _is_sub_pipeline:
            _sub_name = self.running_sub_pipeline[_run_id].name
            _sub_trace_list = copy.deepcopy(
                self.running_sub_pipeline[_run_id].trace_list(run_id=_run_id)
            )
            if status == 'S' or _router_name != '':
                # 无需再使用子管道
                self.running_sub_pipeline[_run_id].remove(run_id=_run_id)
                self.running_sub_pipeline.pop(_run_id, None)
                _run_cache['running_sub_node_id'] = node_id
                _run_cache['is_resume'] = False
                _run_cache['run_to_end'] = False

        # 登记记录
        _run_cache['trace_list'].append({
            'node_id': node_id,
            'node_name': _node_config.get('name', ''),
            'processor_name': _node_config['processor'],
            'start_time': _run_cache['start_time'],
            'end_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
            'status': status,
            'status_msg': status_msg,
            'router_name': _router_name,
            'is_sub_pipeline': _is_sub_pipeline,
            'sub_name': _sub_name,
            'sub_trace_list': _sub_trace_list
        })

        # 通知运行结束节点
        self.log_debug('[Pipeline:%s]Running [%s] node [%s] end: status[%s] status_msg[%s]' %
                       (self.name, _run_id, node_id, status, status_msg))
        if self.end_running_notify_fun is not None:
            AsyncTools.sync_run_coroutine(
                self.end_running_notify_fun(
                    self.name, _run_id, node_id, _node_config.get('name', ''), status, status_msg, self
                )
            )

        # 尝试获取下一个处理节点
        _next_id = None
        if status not in ('S', 'K') and _router_name == '':
            # 异常或暂停, 结束管道运行
            _run_cache['node_status'] = status
            self._set_status(status, _run_id)
            _run_cache['output'] = None
        else:
            # 更新临时变量
            _run_cache['node_status'] = (status if status != 'K' else 'S')
            _run_cache['current_input'] = output
            _run_cache['output'] = output  # 中间步骤也放到output项中, 供暂停时查看

            # 获取下一个节点
            if _router_name == '':
                # 没有设置路由器, 按顺序获取下一个节点(已排除了异常情况)
                _temp_id = str(int(node_id) + 1)
                if _temp_id in self.pipeline.keys():
                    _next_id = _temp_id
            else:
                _router: PipelineRouter = self.get_plugin('router', _router_name)
                _next_id = _router.get_next(
                    output, _run_cache['context'], self, _run_id, **_router_para)

            # 判断是否完结
            if _next_id is None:
                self._set_status('S', _run_id)

        # 异步情况通知结果
        if _next_id is None and self.is_asyn:
            AsyncTools.sync_run_coroutine(
                self.asyn_notify_fun(
                    self.name, _run_id,
                    _run_cache['status'], _run_cache['context'], _run_cache['output'], self
                )
            )

        return _next_id

    def _start_running_thread(self, run_id: str):
        """
        启动运行线程

        @param {str} run_id - 运行id
        """
        # 启动运行线程
        _running_thread = threading.Thread(
            target=self._running_thread_fun,
            name='Thread-Pipeline-Running %s' % run_id,
            args=(run_id,)
        )
        _running_thread.setDaemon(True)
        _running_thread.start()

    def _running_thread_fun(self, run_id: str):
        """
        启动管道运行线程

        @param {str} run_id - 运行id
        """
        _run_id, _run_cache = self._get_run_cache(run_id)
        if _run_cache is None:
            _msg = '[Pipeline:%s] run_id [%s] not exists!' % (self.name, run_id)
            self.log_error('Error: ' % _msg)
            raise RuntimeError(_msg)

        _run_cache['thread_running'] = True
        try:
            while _run_cache['status'] == 'R':
                if _run_cache['node_status'] == 'R':
                    # 当前节点正在执行, 未返回执行结果
                    break

                # 执行当前节点
                _next_id = self._run_node(_run_id, _run_cache['node_id'])
                if _next_id is None:
                    # 已经是最后一个节点
                    break
                else:
                    # 判断是否要逐步执行
                    if _run_cache['is_step_by_step']:
                        # 执行一步就设置状态为暂停
                        self._set_status('P', _run_id)

                    if _next_id == '':
                        # 异步模式, 直接退出线程处理
                        break
                    else:
                        # 设置上下文, 执行下一个节点
                        _run_cache['node_id'] = _next_id
                        _run_cache['node_status'] = 'I'
                        _run_cache['node_status_msg'] = ''
                        RunTool.sleep(0.0001)
        except:
            # 如果在线程中出了异常, 结束掉执行
            _run_cache['node_status'] = 'E'
            self._set_status('E', _run_id)
            _run_cache['output'] = None
            raise
        finally:
            _run_cache['thread_running'] = False
