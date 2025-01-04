#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
构建工具管道插件-获取用户输入
注意: 该插件根据需要需安装inquirer或HiveNetPromptPlus
inquirer>=3.1.3
HiveNetPromptPlus>=0.1.1

@module processer_prompt
@file processer_prompt.py
"""
from HiveNetCore.utils.value_tool import ValueTool
from HiveNetPipeline import PipelineProcesser
try:
    import inquirer
except:
    pass
try:
    from HiveNetPromptPlus import PromptPlus, PromptPlusConsoleApp
except:
    pass


class ProcesserBuildPrompt(PipelineProcesser):
    """
    获取用户输入

    建议节点配置标识(current_key): prompt
    配置说明: 为顺序交互的配置数组, 每个数组支持的配置参数包括
        engine: 使用的交互引擎, 支持inquirer、PromptPlus、PromptPlusConsoleApp三种类型, 默认为inquirer
        promptType: 交互类型, 支持以下几种类型, 默认为input
            input - 文本输入
            confirm - 操作确认
            radio - 单选
            checkbox - 复选
        text: 提示文本, 可不设置
        isUseEditor: 指示是否使用编辑器, 仅inquirer引擎支持, 默认为False
        isPassword: 指示input输入交互内容是否密码, 默认为False
        default: 默认值, 如果为input设置默认的文本, 如果为radio设置为默认选中的选项值, 如果为checkbox设置为默认选中的选项数组
        title: 对话框标题, 仅PromptPlusConsoleApp引擎使用, 可不设置
        yes_text: 对话框确认按钮文本, 仅PromptPlusConsoleApp引擎使用, 可不设置
        no_text: 对话框取消按钮文本, 仅PromptPlusConsoleApp引擎使用, 可不设置
        values: radio和类型checkbox使用, 选项清单数组, PromptPlus引擎不支持
            [
                ('选项值', '选项显示文本'),
                ...
            ]
            注: 选项显示文本可以支持样式, 例如设置为: HTML('<style bg="red" fg="white">Red</style>')
        setValuePath: 交互结果要设置到context上下文的值路径, 例如'key1/key2', 默认为'prompt'
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildPrompt'

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
        _current_key = context.get('current_key', 'prompt')
        _config = context['build_config'].get(_current_key, None)

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 根据获取到的配置执行交互处理
        for _prompt_config in _config:
            # 获取交互返回值并设置到上下文中
            ValueTool.set_dict_value_by_path(
                _prompt_config.get('setValuePath', 'prompt'), context, cls._get_prompt_result(_prompt_config),
                auto_create_key=True
            )

    @classmethod
    def _get_prompt_result(cls, prompt_config: dict):
        """
        获取交互返回值
        注: 如果获取不到返回None

        @param {dict} prompt_config - 交互配置
        """
        _engine = prompt_config.get('engine', 'inquirer')
        _promptType = prompt_config.get('promptType', 'input')

        if _engine == 'PromptPlus':
            if _promptType == 'input':
                return PromptPlus.prompt(
                    message=prompt_config.get('text', 'Please input: '), default=prompt_config.get('default', ''),
                    is_password=prompt_config.get('isPassword', False)
                )
            elif _promptType == 'confirm':
                return PromptPlus.confirm(
                    message=prompt_config.get('text', 'Confirm?')
                )
            else:
                raise Exception("PromptPlus unsupport prompt type [%s]" % _promptType)
        elif _engine == 'PromptPlusConsoleApp':
            if _promptType == 'input':
                return PromptPlusConsoleApp.input_dialog(
                    title=prompt_config.get('title', 'Operation'), text=prompt_config.get('text', 'Please input'),
                    ok_text=prompt_config.get('yes_text', 'OK'), cancel_text=prompt_config.get('no_text', 'Cancel'),
                    password=prompt_config.get('isPassword', False), default=prompt_config.get('default', '')
                )
            elif _promptType == 'confirm':
                return PromptPlusConsoleApp.confirm_dialog(
                    prompt_config.get('title', 'Confirm'), text=prompt_config.get('text', 'Please confirm'),
                    ok_text=prompt_config.get('yes_text', 'Yes'), cancel_text=prompt_config.get('no_text', 'No')
                )
            elif _promptType == 'radio':
                return PromptPlusConsoleApp.radiolist_dialog(
                    prompt_config.get('title', 'Options'), text=prompt_config.get('text', 'Please select'),
                    ok_text=prompt_config.get('yes_text', 'OK'), cancel_text=prompt_config.get('no_text', 'Cancel'),
                    values=prompt_config.get('values', list()), default=prompt_config.get('default', None)
                )
            elif _promptType == 'checkbox':
                return PromptPlusConsoleApp.checkboxlist_dialog(
                    prompt_config.get('title', 'Options'), text=prompt_config.get('text', 'Please select'),
                    ok_text=prompt_config.get('yes_text', 'OK'), cancel_text=prompt_config.get('no_text', 'Cancel'),
                    values=prompt_config.get('values', list()), default_values=prompt_config.get('default', None)
                )
            else:
                raise Exception("PromptPlusConsoleApp unsupport prompt type [%s]" % _promptType)
        else:
            # inquirer
            if _promptType == 'input':
                if (prompt_config.get('isPassword', False)):
                    return inquirer.password(prompt_config.get('text', 'Please input'))
                elif prompt_config.get('isUseEditor', False):
                    return inquirer.editor(
                        prompt_config.get('text', 'Please input'), default=prompt_config.get('default', '')
                    )
                else:
                    return inquirer.text(
                        prompt_config.get('text', 'Please input'), default=prompt_config.get('default', '')
                    )
            elif _promptType == 'confirm':
                return inquirer.confirm(prompt_config.get('text', 'Please confirm'))
            elif _promptType == 'radio':
                # 需要将显示文本和选项值反过来
                _values = list()
                for _option in prompt_config.get('values', list()):
                    _values.append((_option[1], _option[0]))

                return inquirer.list_input(
                    prompt_config.get('text', 'Please select'), choices=_values,
                    default=prompt_config.get('default', None)
                )
            elif _promptType == 'checkbox':
                # 需要将显示文本和选项值反过来
                _values = list()
                for _option in prompt_config.get('values', list()):
                    _values.append((_option[1], _option[0]))

                return inquirer.checkbox(
                    prompt_config.get('text', 'Please select'), choices=_values,
                    default=prompt_config.get('default', None)
                )
            else:
                raise Exception("inquirer unsupport prompt type [%s]" % _promptType)
