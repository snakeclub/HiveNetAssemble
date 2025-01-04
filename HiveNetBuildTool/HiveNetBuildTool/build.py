#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
应用构建工具

@module build
@file build.py
"""
import os
import copy
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetPipeline import Pipeline


class BuildPipeline(object):
    """
    构建管道对象
    """
    #############################
    # 工具函数
    #############################
    @classmethod
    def load_processer_extend_para(cls, config_file: str):
        """
        装载处理插件扩展参数

        @param {str} config_file - 扩展参数配置
        """
        # 获取通用扩展配置字典
        _build_processer_extend_para = RunTool.get_global_var('BUILD_PROCESSER_EXTEND_PARA')
        if _build_processer_extend_para is None:
            _build_processer_extend_para = {}
            RunTool.set_global_var('BUILD_PROCESSER_EXTEND_PARA', _build_processer_extend_para)

        _config = SimpleYaml(config_file, obj_type=EnumYamlObjType.File, encoding='utf-8').yaml_dict
        for _process_name, _para in _config.items():
            if _para is None:
                continue

            # 合并参数
            _old_para = _build_processer_extend_para.get(_process_name, {})
            _new_para = ValueTool.merge_dict(_old_para, _para)
            _build_processer_extend_para[_process_name] = _new_para

    @classmethod
    def get_processer_extend_para(cls, processer_name: str, default=None):
        """
        获取指定处理插件的扩展参数

        @param {str} processer_name - 插件名
        @param {Any} default=None - 如果找不到的默认值

        @returns {Any} - 返回插件扩展参数配置, 如果没有参数返回None
        """
        _build_processer_extend_para = RunTool.get_global_var('BUILD_PROCESSER_EXTEND_PARA', default={})
        return _build_processer_extend_para.get(processer_name, default)

    #############################
    # 构造函数
    #############################

    def __init__(self, base_path: str, config_file: str = None, build_file: str = None, cmd_opts: dict = {}):
        """
        初始化对象

        @param {str} base_path - 自定义的构建器配置基础目录
        @param {str} config_file=None - 构建器配置文件, 不传则自动获取基础目录下的config.yaml文件
        @param {str} build_file=None - 要处理的构建文件(当前工作目录的相对路径), 不传则自动获取当前工作目录下的build.yaml文件
        @param {dict} cmd_opts - 命令行参数
            source: str, 指定构建源码目录(当前工作目录的相对路径), 不传则获取构建文件配置中的路径(build.yaml文件的相对路径), 如果为None则为build.yaml所在的目录
            output: str, 构建结果输出目录(当前工作目录的相对路径), 不传则获取构建文件配置中的路径(build.yaml文件的相对路径), 如果为None则为build.yaml所在的目录
            type: str, 构建类型, 不传则获取构建文件配置中的配置
        """
        # 基础参数
        self._base_path = os.path.abspath(base_path)
        self._config_file = os.path.abspath(os.path.join(
            self._base_path, 'config.yaml' if config_file is None else config_file
        ))
        self._cmd_opts = cmd_opts
        if build_file is None:
            self._build_file_path = os.path.abspath(os.getcwd())
            self._build_file = os.path.join(self._build_file_path, 'build.yaml')
        else:
            self._build_file = os.path.abspath(build_file)
            self._build_file_path = os.path.dirname(build_file)

        # 加载构建配置文件
        self._build_config = SimpleYaml(
            build_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict

        # 处理构建文件的路径
        if cmd_opts.get('source', None) is not None:
            self._source = os.path.abspath(os.path.join(os.getcwd(), cmd_opts['source']))
        else:
            if self._build_config['build'].get('source', None) is None:
                self._source = self._build_file_path
            else:
                self._source = os.path.abspath(
                    os.path.join(self._build_file_path, self._build_config['build']['source'])
                )

        if cmd_opts.get('output', None) is not None:
            self._output = os.path.abspath(os.path.join(os.getcwd(), cmd_opts['output']))
        else:
            if self._build_config['build'].get('output', None) is None:
                self._output = self._build_file_path
            else:
                self._output = os.path.abspath(
                    os.path.join(self._build_file_path, self._build_config['build']['output'])
                )

        # 加载构建工具配置文件
        self._config = SimpleYaml(
            self._config_file, obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict

        # 当前构建类型参数
        if cmd_opts.get('type', None) is None:
            self._type = self._build_config['build']['type']
        else:
            self._type = cmd_opts['type']

        self._type_config = self._config[self._type]

        # 装载集成的管道插件
        Pipeline.load_plugins_embed()

        # 装载管道通用插件
        Pipeline.load_plugins_by_path(os.path.join(os.path.dirname(__file__), 'plugins'))

        # 装载当前构建类型自有的管道插件
        if self._type_config.get('plugins', None) is not None:
            _plugins_paths = list()
            if type(self._type_config['plugins']) == str:
                _plugins_paths.append(self._type_config['plugins'])
            else:
                _plugins_paths = self._type_config['plugins']

            for _plugins_path in _plugins_paths:
                Pipeline.load_plugins_by_path(
                    os.path.join(self._base_path, _plugins_path)
                )

        # 装载管道插件的私有扩展参数
        _base_extend_para_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'extend_para.yaml'
        ))
        if os.path.exists(_base_extend_para_file):
            self.load_processer_extend_para(_base_extend_para_file)

        _extend_para_file = os.path.abspath(os.path.join(
            self._base_path, 'extend_para.yaml'
        ))
        if os.path.exists(_extend_para_file):
            self.load_processer_extend_para(_extend_para_file)

        # 获取管道运行参数
        self._pipeline_config = SimpleYaml(
            os.path.join(self._base_path, self._type_config['pipeline']),
            obj_type=EnumYamlObjType.File, encoding='utf-8'
        ).yaml_dict
        self._pipeline = Pipeline(
            'build', self._pipeline_config, running_notify_fun=self._running_notify_fun,
            end_running_notify_fun=self._end_running_notify_fun
        )

    def start_build(self) -> bool:
        """
        启动构建处理

        @returns {bool} - 是否构建成功
        """
        # 初始化上下文
        _context = {
            'build_type_config': copy.deepcopy(self._type_config),
            'base_path': self._base_path,
            'cmd_opts': self._cmd_opts,
            'build': copy.deepcopy(self._build_config['build']),
            'build_config': copy.deepcopy(self._build_config)
        }

        # 处理构建参数的路径
        _context['build']['type'] = self._type
        _context['build']['source'] = self._source
        _context['build']['output'] = self._output

        # 创建输出目录
        FileTool.create_dir(self._output, exist_ok=True)

        # 运行构建管道
        _run_id, _status, _output = self._pipeline.start(
            context=_context
        )

        # 返回结果
        if _status == 'S':
            print('\nBuild Success\n')
            # 提示信息
            if self._build_config['build'].get('successTips', None) is not None:
                for _line in self._build_config['build']['successTips']:
                    print(_line)
                print('\n')
            return True
        else:
            print('\nBuild Failed\n')
            return False

    #############################
    # 内部函数
    #############################
    def _running_notify_fun(self, name, run_id, node_id, node_name, pipeline_obj):
        """
        节点运行通知函数
        """
        print('[%s] Begin run build step[%s: %s-%s]' % (
            name, node_id, node_name, pipeline_obj.pipeline[node_id].get('tips', '')
        ))

    def _end_running_notify_fun(self, name, run_id, node_id, node_name, status, status_msg, pipeline_obj):
        """
        结束节点运行通知
        """
        print('[%s] End run build step[%s: %s-%s] [status: %s]: %s' % (
            name, node_id, node_name, pipeline_obj.pipeline[node_id].get('tips', ''),
            'S-Success' if status == 'S' else '%s-Failed' % status,
            status_msg
        ))
