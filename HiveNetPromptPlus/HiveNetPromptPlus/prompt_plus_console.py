#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
命令行扩展处理窗口应用

@module prompt_plus_console
@file prompt_plus_console.py
"""
import os
import sys
import copy
from threading import Thread
import traceback

from prompt_toolkit.layout.containers import to_container
from prompt_toolkit.eventloop import get_event_loop, run_in_executor_with_context
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.key_bindings import KeyBindings, merge_key_bindings
from prompt_toolkit.completion import Completer
from prompt_toolkit.styles.base import DummyStyle, BaseStyle
from prompt_toolkit.shortcuts.dialogs import (
    input_dialog, message_dialog, yes_no_dialog, radiolist_dialog,
    checkboxlist_dialog, progress_dialog
)
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    has_focus,
    is_done,
    is_true,
    to_filter,
)
from prompt_toolkit.application.current import get_app
from prompt_toolkit import Application
from prompt_toolkit.filters import has_focus, Condition, has_selection
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.document import Document
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.keys import KEY_ALIASES, Keys
from prompt_toolkit.widgets import (
    Box,
    Button,
    CheckboxList,
    Dialog,
    Label,
    ProgressBar,
    RadioList,
    TextArea,
    ValidationToolbar,
    Frame,
    HorizontalLine,
    SearchToolbar
)
from prompt_toolkit.lexers import DynamicLexer, Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, HSplit, VSplit, DynamicContainer, Float, FloatContainer, ConditionalContainer
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.menus import CompletionsMenu
from pyparsing import col
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetPromptPlus.prompt_plus import PromptPlus
from HiveNetPromptPlus.layout.extend_text_area import ExtendTextArea, StdOutputTextArea, StdOutputTextAreaOutput
from HiveNetPromptPlus.layout.extend_patch_stdout import extend_patch_stdout
from HiveNetPromptPlus.layout.extend_list import ExtendRadioList, ExtendCheckboxList
from HiveNetCore.generic import CResult


__MOUDLE__ = 'prompt_plus_console'  # 模块名
__DESCRIPT__ = u'增强的交互命令行交互应用, 基于prompt_toolkit进行封装和扩展'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.09.18'  # 发布日期


class PromptPlusConsoleApp(PromptPlus):
    """
    命令行扩展处理窗口应用
    Ctrl + C : abort,取消本次输入
    Ctrl + D : exit,关闭窗口应用
    """
    #############################
    # 静态方法 - 对话窗口模式
    #############################
    @classmethod
    def input_dialog(cls, title: str = '', text: str = '', ok_text: str = 'OK',
            cancel_text: str = 'Cancel', completer: Completer = None,
            password: bool = False, style: BaseStyle = None, default: str = ''):
        """
        输入对话框

        @param {str} title='' - 对话框标题
        @param {str} text='' - 对话框提示文本
        @param {str} ok_text='OK' - 对话框确认按钮文字
        @param {str} cancel_text='Cancel' - 对话框取消按钮文字
        @param {Completer} completer=None - 自动完成提示信息对象
            注: 可以直接使用prompt_toolkit.completion.WordCompleter的实例类
        @param {bool} password=False - 是否密码输入(显示为*)
        @param {BaseStyle} style=None - 对话框样式对象
        @param {str} default='' - 默认值

        @returns {str} - 获取到的输入信息, 如果点击取消按钮返回None
        """
        return input_dialog(
            title=title, text=text, ok_text=ok_text, cancel_text=cancel_text, completer=completer,
            password=password, style=style, default=default
        ).run()

    @classmethod
    def message_dialog(cls, title: str = '', text: str = '', ok_text: str = 'Ok', style: BaseStyle = None):
        """
        提示信息对话框

        @param {str} title='' - 对话框标题
        @param {str} text='' - 对话框提示文本
        @param {str} ok_text='OK' - 对话框确认按钮文字
        @param {BaseStyle} style=None - 对话框样式对象
        """
        return message_dialog(
            title=title, text=text, ok_text=ok_text, style=style
        ).run()

    @classmethod
    def confirm_dialog(cls, title: str = '', text: str = '', yes_text: str = 'Yes',
            no_text: str = 'No', style: BaseStyle = None) -> bool:
        """
        确认对话框

        @param {str} title='' - 对话框标题
        @param {str} text='' - 对话框提示文本
        @param {str} yes_text='Yes' - 确认按钮文本
        @param {str} no_text='No' - 否认按钮文本
        @param {BaseStyle} style=None - 对话框样式对象

        @returns {bool} - 确认结果
        """
        return yes_no_dialog(
            title=title, text=text, yes_text=yes_text, no_text=no_text, style=style
        ).run()

    @classmethod
    def radiolist_dialog(cls, title: str = '', text: str = '', ok_text: str = 'Ok',
            cancel_text: str = 'Cancel', values: list = None, default: str = None,
            style: BaseStyle = None) -> str:
        """
        单选对话框

        @param {str} title='' - 对话框标题
        @param {str} text='' - 对话框提示文本
        @param {str} ok_text='OK' - 对话框确认按钮文字
        @param {str} cancel_text='Cancel' - 对话框取消按钮文字
        @param {list} values=None - 可选的选项列表, 格式如下:
            [
                ('选项值', '选项显示文本'),
                ...
            ]
            注: 选项显示文本可以支持样式, 例如设置为: HTML('<style bg="red" fg="white">Red</style>')
        @param {str} default=None - 默认选中的选项值
        @param {BaseStyle} style=None - 对话框样式对象

        @returns {str} - 选中的选项值, 如果取消返回None
        """
        return radiolist_dialog(
            title=title, text=text, ok_text=ok_text, cancel_text=cancel_text,
            values=values, default=default, style=style
        ).run()

    @classmethod
    def checkboxlist_dialog(cls, title: str = '', text: str = '', ok_text: str = 'Ok',
            cancel_text: str = 'Cancel', values: list = None, default_values: list = None,
            style: BaseStyle = None) -> list:
        """
        复选对话框

        @param {str} title='' - 对话框标题
        @param {str} text='' - 对话框提示文本
        @param {str} ok_text='OK' - 对话框确认按钮文字
        @param {str} cancel_text='Cancel' - 对话框取消按钮文字
        @param {list} values=None - 可选的选项列表, 格式如下:
            [
                ('选项值', '选项显示文本'),
                ...
            ]
            注: 选项显示文本可以支持样式, 例如设置为: HTML('<style bg="red" fg="white">Red</style>')
        @param {list} default_values=None - 默认选中的选项值列表
        @param {BaseStyle} style=None - 对话框样式对象

        @returns {list} - 选中的选项值列表, 如果取消返回None
        """
        return checkboxlist_dialog(
            title=title, text=text, ok_text=ok_text, cancel_text=cancel_text,
            values=values, default_values=default_values, style=style
        ).run()

    @classmethod
    def progress_dialog(cls, title: str = '', text: str = '', run_callback=(lambda *a: None), style: BaseStyle = None):
        """
        进度对话框

        @param {str} title='' - 对话框标题
        @param {str} text='' - 对话框提示文本
        @param {function} run_callback=None - 进度回调函数, 该函数为实际执行操作的函数, 并按实际情况更新进度
            函数格式如下: fun(set_percentage, log_text) -> None
            函数内部可以使用 set_percentage 函数实时设置对话框的进度, 例如: set_percentage(30)
            函数内部可以使用 log_text 函数将进度内容输出到对话框的提示信息框中, 例如: log_text('正在处理xxx')
            注意: 函数结束时对话框也会关闭, 因此正常结束时应将进度设置为 100
        @param {BaseStyle} style=None - 对话框样式对象
        """
        return progress_dialog(
            title=title, text=text, run_callback=run_callback, style=style
        ).run()

    #############################
    # 静态方法 - 全屏模式
    #############################
    @classmethod
    def simple_prompt(cls, title: str = '', text: str = '', text_split: str = ': ',
            default: str = '', multiline: bool = False,
            wrap_lines: bool = True, height: int = None, completer: Completer = None, lexer: Lexer = None,
            show_title: bool = True, color_set: dict = None) -> str:
        """
        获取输入文本

        @param {str} title='' - 界面标题
        @param {str} text='' - 界面提示文本
        @param {str} text_split= ': ' - 提示文本和输入文本的间隔赋
        @param {str} default='' - 输入默认值
        @param {bool} multiline=False - 是否支持多行模式
            注: 如果多行模式, 提交快捷键是 ctrl + s
        @param {bool} wrap_lines=True - 当一行宽度超过屏幕时是否自动换行
        @param {int} height=None - 输入栏位高度
        param {Completer} completer=None - 自动完成提示信息对象
            注: 可以直接使用prompt_toolkit.completion.WordCompleter的实例类
        @param {Lexer} lexer=None - 显示文本的格式化样式对象, 可以直接使用第三方pygments包支持的样式, 例如:
            from pygments.lexers.python import PythonLexer
            设置lexer=PythonLexer()
        @param {bool} show_title=True - 是否显示标题
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
            'win-title-field': 'reverse',  # 窗口标题栏配色
            'win-input-field': '',  # 窗口输入框配色

        @returns {str} - 返回输入的文本, 如果取消返回None
        """
        return cls._get_simple_prompt_app(
            title=title, text=text, text_split=text_split, default=default,
            multiline=multiline, wrap_lines=wrap_lines, height=height, completer=completer,
            lexer=lexer, show_title=show_title, color_set=color_set
        ).run()

    @classmethod
    def confirm(cls, title: str = '', text: str = '', text_split: str = ' ', default: bool = False,
            yes_text: str = 'Yes', no_text: str = 'No',
            yes_key_binding: str = 'y', no_key_binding: str = 'n',
            show_title: bool = True, color_set: dict = None) -> bool:
        """
        获取确认结果

        @param {str} title='' - 界面标题
        @param {str} text='' - 界面提示文本
        @param {str} text_split=' ' - 提示文本和输入文本的间隔赋
        @param {bool} default=False - 默认选中
        @param {str} yes_text='Yes' - 确认显示内容
        @param {str} no_text='No' - 否决显示内容
        @param {str} yes_key_binding='y' - 确认快捷键
        @param {str} no_key_binding='n' - 否决快捷键
        @param {bool} show_title=True - 是否显示标题
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
            'win-title-field': 'reverse',  # 窗口标题栏配色
            'win-confirm-field': '',  # 确认信息栏位配色
            'win-confirm-selected': 'reverse',  # 选中选项颜色

        @returns {bool} - 确认结果, 取消情况返回None
        """
        _app = cls._get_confirm_app(
            title=title, text=text, text_split=text_split, default=default,
            yes_text=yes_text, no_text=no_text, yes_key_binding=yes_key_binding,
            no_key_binding=no_key_binding, show_title=show_title, color_set=color_set
        )
        return _app.run()

    @classmethod
    def radiolist(cls, title: str = '', text: str = '', values: list = None, default: str = None,
            show_title: bool = True, color_set: dict = None) -> str:
        """
        单选选择

        @param {str} title='' - 界面标题
        @param {str} text='' - 界面提示文本
        @param {list} values=None - 可选的选项列表, 格式如下:
            [
                ('选项值', '选项显示文本'),
                ...
            ]
            注: 选项显示文本可以支持样式, 例如设置为: HTML('<style bg="red" fg="white">Red</style>')
        @param {str} default=None - 默认选中的值
        @param {bool} show_title=True - 是否显示标题
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
            'win-title-field': 'reverse',  # 窗口标题栏配色
            'win-radio-text-field': '',  # 提示文本样式
            'radio-list': '',  # 选项容器样式
            'radio': '',  # 选项文本样式
            'radio-selected': '', # 选项光标样式
            'radio-checked': '',  # 当前选项样式

        @returns {str} - 选中的值, 取消情况返回None
        """
        return cls._get_radiolist_app(
            title=title, text=text, values=values, default=default, show_title=show_title,
            color_set=color_set
        ).run()

    @classmethod
    def checkboxlist(cls, title: str = '', text: str = '', values: list = None, default: list = None,
            show_title: bool = True, color_set: dict = None) -> list:
        """
        多选选择

        @param {str} title='' - 界面标题
        @param {str} text='' - 界面提示文本
        @param {list} values=None - 可选的选项列表, 格式如下:
            [
                ('选项值', '选项显示文本'),
                ...
            ]
            注: 选项显示文本可以支持样式, 例如设置为: HTML('<style bg="red" fg="white">Red</style>')
        @param {list} default=None - 默认选中的值列表
        @param {bool} show_title=True - 是否显示标题
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
            'win-title-field': 'reverse',  # 窗口标题栏配色
            'win-radio-text-field': '',  # 提示文本样式
            'checkbox-list': '',  # 选项容器样式
            'checkbox': '',  # 选项文本样式
            'checkbox-selected': '', # 选项光标样式
            'checkbox-checked': '',  # 当前选项样式

        @returns {list} - 选中的值列表, 取消情况返回None
        """
        return cls._get_checkboxlist_app(
            title=title, text=text, values=values, default=default, show_title=show_title,
            color_set=color_set
        ).run()

    @classmethod
    def progress(cls, title: str = '', text: str = '', run_callback=(lambda *a: None),
            show_title: bool = True, show_progress_text: bool = True, color_set: dict = None):
        """
        显示进度信息

        @param {str} title='' - 界面标题
        @param {str} text='' - 界面提示文本
        @param {function} run_callback=None - 进度回调函数, 该函数为实际执行操作的函数, 并按实际情况更新进度
            函数格式如下: fun(set_percentage, log_text) -> None
            函数内部可以使用 set_percentage 函数实时设置对话框的进度, 例如: set_percentage(30)
            函数内部可以使用 log_text 函数将进度内容输出到对话框的提示信息框中, 例如: log_text('正在处理xxx')
            注意: 函数结束时对话框也会关闭, 因此正常结束时应将进度设置为 100
        @param {bool} show_title=True - 是否显示标题
        @param {bool} show_progress_text=True - 是否显示进度信息
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
            'win-title-field': 'reverse',  # 窗口标题栏配色
            'win-progress-text-field': '',  # 提示文本样式
            'win-progress-info-field': '',  # 进度信息展示框样式
            'progress-bar': 'bg:#505050',  # 进度条样式
            'progress-bar.used': 'reverse', # 已使用的进度样式
        """
        # 异步事件循环对象
        _loop = get_event_loop()

        # 颜色配置
        _style_default = {
            'win-title-field': 'reverse', 'progress-bar': 'bg:#505050', 'progress-bar.used': 'reverse'
        }
        if color_set is not None:
            _style_default.update(color_set)

        # 输入框的快捷键绑定
        _kb = KeyBindings()

        # 标题框
        _title_field = Label(
            title, style='class:win-title-field', wrap_lines=False,
        )

        # 提示文本
        _text_field = Label(
            text, style='class:win-progress-text-field', wrap_lines=True,
        )

        # 进度信息显示
        _progress_text_field = ExtendTextArea(
            focusable=False, height=D(preferred=10**10), style='class:win-progress-info-field'
        )

        # 进度条
        _progressbar = ProgressBar()

        # 显示容器
        _container = FloatContainer(
            content=HSplit(
                [
                    # 标题
                    ConditionalContainer(
                        content=_title_field, filter=Condition(lambda: show_title)
                    ),
                    # 提示行
                    ConditionalContainer(
                        content=_text_field, filter=Condition(lambda: text is not None and text != '')
                    ),
                    # 进度信息
                    ConditionalContainer(
                        content=_progress_text_field, filter=Condition(lambda: show_progress_text)
                    ),
                    _progressbar,
                ], padding=0
            ),
            floats=[],
        )

        # 创建应用并设置默认值
        _app = Application(
            layout=Layout(_container),
            key_bindings=merge_key_bindings([load_key_bindings(), _kb]),
            mouse_support=True,
            style=Style.from_dict(_style_default),
            full_screen=True,
        )

        # 进度处理相关函数
        def set_percentage(value: int) -> None:
            _progressbar.percentage = int(value)
            _app.invalidate()

        def log_text(text: str) -> None:
            _loop.call_soon_threadsafe(_progress_text_field.buffer.insert_text, text)
            _app.invalidate()

        # Run the callback in the executor. When done, set a return value for the
        # UI, so that it quits.
        def start() -> None:
            try:
                run_callback(set_percentage, log_text)
            finally:
                _app.exit()

        def pre_run() -> None:
            run_in_executor_with_context(start)

        _app.pre_run_callables.append(pre_run)

        return _app.run()

    @classmethod
    def prompt_continuous_step(cls, step: dict, show_title: bool = True, color_set: dict = None,
            results: dict = {}, show_contents: list = [], type_mapping: dict = None):
        """
        单步执行连续输入处理

        @param {dict} step - 执行参数
            {
                'id': '步骤id',
                'type': 'simple_prompt',  # 输入类型, 支持simple_prompt、confirm、radiolist、checkboxlist
                'para': {...}, # 输入参数, 与对应的单个显示函数参数一致(show_title、color_set无需送入)
                'show_last_content': True,  # 是否显示此前输入的结果
                'show_current_content': True,  # 是否将当前输入结果放入此前输入结果清单(下一次输入可显示)
            }
        @param {bool} show_title=True - 是否显示标题
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集
        @param {dict} results={} - 执行结果字典, 执行完成将自动将当前步骤的结果更新到该字典上
        @param {list} show_contents=[] - 持续显示的结果组件
        @param {dict} type_mapping=None - 支持类型的函数映射字典
        """
        # 要处理的函数映射字典
        _type_mapping = type_mapping
        if type_mapping is None:
            _type_mapping = {
                'simple_prompt': {
                    'style': cls._get_simple_prompt_style,
                    'content': cls._get_simple_prompt_content,
                    'app': cls._get_simple_prompt_app
                },
                'confirm': {
                    'style': cls._get_confirm_style,
                    'content': cls._get_confirm_content,
                    'app': cls._get_confirm_app
                },
                'radiolist': {
                    'style': cls._get_radiolist_style,
                    'content': cls._get_radiolist_content,
                    'app': cls._get_radiolist_app
                },
                'checkboxlist': {
                    'style': cls._get_checkboxlist_style,
                    'content': cls._get_checkboxlist_content,
                    'app': cls._get_checkboxlist_app
                },
            }

        # 获取映射配置
        _type_para = _type_mapping.get(
            step.get('type', ''), None
        )
        if _type_para is None:
            raise ModuleNotFoundError('not support prompt type: %s' % step.get('type', ''))

        # 设置样式
        _style = _type_para['style'](color_set=color_set)

        # 生成app应用
        _app_kwargs = copy.copy(step.get('para', {}))
        _app_kwargs['show_title'] = False  # 自行控制标题的显示
        _app_kwargs['color_set'] = _style
        _app: Application = _type_para['app'](**_app_kwargs)

        # 显示此前处理结果
        if step.get('show_last_content', True):
            for _i in range(len(show_contents)):
                _app.layout.container.content.children.insert(
                    _i, to_container(show_contents[_i])
                )

        # 添加标题
        if show_title:
            _title_field = to_container(Label(
                _app_kwargs.get('title'), style='class:win-title-field', wrap_lines=False,
            ))
            _app.layout.container.content.children.insert(0, _title_field)

        # 获取输入结果, 并更新结果信息
        _result = _app.run()
        if _result is not None:
            results[step['id']] = _result
            if step.get('show_current_content', True):
                _result_kwargs = copy.copy(step.get('para', {}))
                _result_kwargs['result'] = _result
                _result_content = _type_para['content'](**_result_kwargs)
                if type(_result_content) == list:
                    show_contents.extend(_result_content)
                else:
                    show_contents.append(_result_content)

    @classmethod
    def prompt_continuous(cls, steps: list, show_title: bool = True, color_set: dict = None) -> dict:
        """
        处理连续的输入请求

        @param {list} steps - 输入请求步骤, 每一步是一个输入配置字典:
            [
                {
                    'id': '步骤id', # 必填
                    'type': 'simple_prompt',  # 输入类型, 支持simple_prompt、confirm、radiolist、checkboxlist
                    'para': {...}, # 输入参数, 与对应的单个显示函数参数一致(show_title、color_set无需送入)
                    'show_last_content': True,  # 是否显示此前输入的结果
                    'show_current_content': True,  # 是否将当前输入结果放入此前输入结果清单(下一次输入可显示)
                },
                ...
            ]
        @param {bool} show_title=True - 是否显示标题
        @param {dict} color_set=None - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
            'win-title-field': 'reverse',  # 窗口标题栏配色
            'win-progress-text-field': '',  # 提示文本样式
            'win-progress-info-field': '',  # 进度信息展示框样式
            'progress-bar': 'bg:#505050',  # 进度条样式
            'progress-bar.used': 'reverse', # 已使用的进度样式

        @returns {dict} - 获取到的输出结果
        """
        # 要处理的函数映射字典
        _type_mapping = {
            'simple_prompt': {
                'style': cls._get_simple_prompt_style,
                'content': cls._get_simple_prompt_content,
                'app': cls._get_simple_prompt_app
            },
            'confirm': {
                'style': cls._get_confirm_style,
                'content': cls._get_confirm_content,
                'app': cls._get_confirm_app
            },
            'radiolist': {
                'style': cls._get_radiolist_style,
                'content': cls._get_radiolist_content,
                'app': cls._get_radiolist_app
            },
            'checkboxlist': {
                'style': cls._get_checkboxlist_style,
                'content': cls._get_checkboxlist_content,
                'app': cls._get_checkboxlist_app
            },
        }

        # 处理样式集合
        _color_set = {} if color_set is None else color_set
        for _input_step in steps:
            _style_func = _type_mapping.get(_input_step.get('type', ''), {}).get('style', None)
            if _style_func is not None:
                _color_set = _style_func(color_set=_color_set)

        # 用于显示前面获取结果的信息以及内容组件列表
        _results = {}
        _show_contents = []

        # 循环处理输入
        for _input_step in steps:
            # 执行单步
            cls.prompt_continuous_step(
                _input_step, show_title=show_title, color_set=_color_set,
                results=_results, show_contents=_show_contents, type_mapping=_type_mapping
            )

            # 判断结果
            if _results.get(_input_step['id'], None) is None:
                # 取消了输入, 直接跳出处理
                return None

        return _results

    #############################
    # 静态方法 - 全屏模式(内部函数)
    #############################
    @classmethod
    def _get_simple_prompt_style(cls, color_set: dict = None) -> dict:
        """
        获取输入文本的样式字典
        """
        _style_default = {
            'win-title-field': 'reverse'
        }
        if color_set is not None:
            _style_default.update(color_set)

        return _style_default

    @classmethod
    def _get_simple_prompt_content(cls, text: str = '', text_split: str = ': ',
            default: str = '', multiline: bool = False,
            wrap_lines: bool = True, height: int = None, completer: Completer = None, lexer: Lexer = None,
            result=None, **kwargs) -> list:
        """
        获取输入文本的主体内容清单
        注: 如果result设置为None代表生成可输入组件清单, 否则生成只读的结果清单
        """
        # 输入框
        _kwargs = {
            'text': default if result is None else result,
            'prompt': '%s%s' % (text, text_split),
            'style': 'class:win-input-field',
            'multiline': multiline,
            'wrap_lines': wrap_lines,
            'height': D(min=1) if height is None else height,
            'focus_on_click': True if result is None else False,
            'read_only': False if result is None else True,
            'scrollbar': True,
            'completer': completer,
            'lexer': lexer,
        }
        _input_field = ExtendTextArea(**_kwargs)
        if result is not None:
            # 控制高度为实际高度
            _size = get_app().output.get_size()
            _input_field.window.height = _input_field.window.preferred_height(
                _size.columns, _size.rows
            ).preferred
        return _input_field

    @classmethod
    def _get_simple_prompt_app(cls, title: str = '', text: str = '', text_split: str = ': ',
            default: str = '', multiline: bool = False,
            wrap_lines: bool = True, height: int = None, completer: Completer = None, lexer: Lexer = None,
            show_title: bool = True, color_set: dict = None) -> Application:
        """
        获取输入文本的应用
        """
        # 颜色配置
        _style_default = cls._get_simple_prompt_style(color_set=color_set)

        # 输入框的快捷键绑定
        _kb = KeyBindings()

        # 标题框
        _title_field = Label(
            title, style='class:win-title-field', wrap_lines=False,
        )

        # 输入框
        _input_field = cls._get_simple_prompt_content(
            text=text, text_split=text_split, default=default, multiline=multiline,
            wrap_lines=wrap_lines, height=height, completer=completer, lexer=lexer
        )

        # 显示容器
        _container = FloatContainer(
            content=HSplit(
                [
                    # 首行提示行
                    ConditionalContainer(
                        content=_title_field, filter=Condition(lambda: show_title)
                    ),
                    _input_field,
                ], padding=0
            ),
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                ),
            ],
        )

        # 取消输入内容快捷键函数
        @_kb.add('c-c')
        def __cancle_input(event):
            get_app().exit(result=None)

        # 多行模式使用enter换行, ctrl + s提交
        @_kb.add('c-s')
        @_kb.add('enter', filter=(not multiline))
        def __input_field_accept(event):
            get_app().exit(result=_input_field.text)

        return Application(
            layout=Layout(_container),
            key_bindings=merge_key_bindings([load_key_bindings(), _kb]),
            mouse_support=True,
            style=Style.from_dict(_style_default),
            full_screen=True,
        )

    @classmethod
    def _get_confirm_style(cls, color_set: dict = None) -> dict:
        """
        获取输入文本的样式字典
        """
        _style_default = {
            'win-title-field': 'reverse', 'win-confirm-selected': 'reverse'
        }
        if color_set is not None:
            _style_default.update(color_set)

        return _style_default

    @classmethod
    def _get_confirm_content(cls, title: str = '', text: str = '', text_split: str = ' ', default: bool = False,
            yes_text: str = 'Yes', no_text: str = 'No',
            yes_key_binding: str = 'y', no_key_binding: str = 'n',
            result=None, **kwargs):
        """
        获取获取结果的主体内容清单
        注: 如果result设置为None代表生成可输入组件清单, 否则生成只读的结果清单
        """
        # 文本格式处理函数
        def __get_confirm_formated_text(self_result):
            return FormattedText([
                ('', '%s%s' % (text, text_split)),
                ('%s' % 'class:win-confirm-selected' if self_result else '', yes_text),
                ('', ' / '),
                ('%s' % 'class:win-confirm-selected' if not self_result else '', no_text)
            ])

        # 提示文本
        _confirm_field = Label(
            text=__get_confirm_formated_text(default if result is None else result),
            style='class:win-confirm-field', dont_extend_height=True, wrap_lines=True
        )
        return _confirm_field

    @classmethod
    def _get_confirm_app(cls, title: str = '', text: str = '', text_split: str = ' ', default: bool = False,
            yes_text: str = 'Yes', no_text: str = 'No',
            yes_key_binding: str = 'y', no_key_binding: str = 'n',
            show_title: bool = True, color_set: dict = None) -> Application:
        """
        获取确认结果的应用
        """
        # 颜色配置
        _style_default = cls._get_confirm_style(color_set=color_set)

        # 输入框的快捷键绑定
        _kb = KeyBindings()

        # 标题框
        _title_field = Label(
            title, style='class:win-title-field', wrap_lines=False,
        )

        # 文本格式处理函数
        def __get_confirm_formated_text(result):
            return FormattedText([
                ('', '%s%s' % (text, text_split)),
                ('%s' % 'class:win-confirm-selected' if result else '', yes_text),
                ('', ' / '),
                ('%s' % 'class:win-confirm-selected' if not result else '', no_text)
            ])

        # 提示文本
        _confirm_field = cls._get_confirm_content(
            title=title, text=text, text_split=text_split, default=default,
            yes_text=yes_text, no_text=no_text, yes_key_binding=yes_key_binding,
            no_key_binding=no_key_binding
        )

        # 显示容器
        _container = FloatContainer(
            content=HSplit(
                [
                    # 首行提示行
                    ConditionalContainer(
                        content=_title_field, filter=Condition(lambda: show_title)
                    ),
                    _confirm_field,
                ], padding=0
            ),
            floats=[],
        )

        # 取消输入内容快捷键函数
        @_kb.add('c-c')
        def __cancle_input(event):
            get_app().exit(result=None)

        # tab切换结果
        @_kb.add('c-i')
        def __switch_input(event):
            _app = get_app()
            _new_data = (not _app.clipboard.get_data())
            _app.clipboard.set_data(_new_data)
            _confirm_field.text = __get_confirm_formated_text(_new_data)

        # 按方向键切换结果
        @_kb.add('left')
        def __switch_yes(event):
            _app = get_app()
            _app.clipboard.set_data(True)
            _confirm_field.text = __get_confirm_formated_text(True)

        @_kb.add('right')
        def __switch_no(event):
            _app = get_app()
            _app.clipboard.set_data(False)
            _confirm_field.text = __get_confirm_formated_text(False)

        # 按回车返回结果
        @_kb.add('enter')
        def __accept_input(event):
            _app = get_app()
            _app.exit(result=_app.clipboard.get_data())

        # 直接按确认按钮
        if yes_key_binding is not None and yes_key_binding != '':
            @_kb.add(yes_key_binding)
            def __accept_yes(event):
                get_app().exit(result=True)

        # 直接按否决按钮
        if no_key_binding is not None and no_key_binding != '':
            @_kb.add(no_key_binding)
            def __accept_no(event):
                get_app().exit(result=False)

        # 创建应用并设置默认值
        _app = Application(
            layout=Layout(_container),
            key_bindings=merge_key_bindings([load_key_bindings(), _kb]),
            mouse_support=True,
            style=Style.from_dict(_style_default),
            full_screen=True,
        )
        _app.clipboard.set_data(default)

        return _app

    @classmethod
    def _get_radiolist_style(cls, color_set: dict = None) -> dict:
        """
        获取单选选择的样式字典
        """
        _style_default = {
            'win-title-field': 'reverse'
        }
        if color_set is not None:
            _style_default.update(color_set)

        return _style_default

    @classmethod
    def _get_radiolist_content(cls, title: str = '', text: str = '', values: list = None, default: str = None,
            result=None, **kwargs):
        """
        获取单选选择的主体内容清单
        注: 如果result设置为None代表生成可输入组件清单, 否则生成只读的结果清单
        """
        # 提示文本
        _text_field = Label(
            text, style='class:win-radio-text-field', wrap_lines=True,
        )
        _text_container = ConditionalContainer(
            content=_text_field, filter=Condition(lambda: text is not None and text != '')
        )

        # 选项
        if values is None:
            values = []

        _radio_list = ExtendRadioList(
            values=values, default=(default if result is None else result),
            realonly=(False if result is None else True)
        )

        return [_text_container, _radio_list]

    @classmethod
    def _get_radiolist_app(cls, title: str = '', text: str = '', values: list = None, default: str = None,
            show_title: bool = True, color_set: dict = None) -> Application:
        """
        获取单选选择的应用
        """
        # 颜色配置
        _style_default = cls._get_radiolist_style(color_set=color_set)

        # 输入框的快捷键绑定
        _kb = KeyBindings()

        # 标题框
        _title_field = Label(
            title, style='class:win-title-field', wrap_lines=False,
        )

        # 提示文本和选项
        _contents = cls._get_radiolist_content(
            title=title, text=text, values=values, default=default
        )
        _text_container = _contents[0]
        _radio_list = _contents[1]

        # 显示容器
        _container = FloatContainer(
            content=HSplit(
                [
                    # 标题
                    ConditionalContainer(
                        content=_title_field, filter=Condition(lambda: show_title)
                    ),
                    # 提示行
                    _text_container,
                    _radio_list,
                ], padding=0
            ),
            floats=[],
        )

        # 取消输入内容快捷键函数
        @_kb.add('c-c')
        def __cancle_input(event):
            get_app().exit(result=None)

        # 按enter返回结果
        @_kb.add('enter')
        def __accept_input(event):
            _app = get_app()
            _app.exit(result=_radio_list.current_value)

        # 创建应用并设置默认值
        _app = Application(
            layout=Layout(_container),
            key_bindings=merge_key_bindings([load_key_bindings(), _kb]),
            mouse_support=True,
            style=Style.from_dict(_style_default),
            full_screen=True,
        )
        return _app

    @classmethod
    def _get_checkboxlist_style(cls, color_set: dict = None) -> dict:
        """
        获取多选选择的样式字典
        """
        _style_default = {
            'win-title-field': 'reverse'
        }
        if color_set is not None:
            _style_default.update(color_set)

        return _style_default

    @classmethod
    def _get_checkboxlist_content(cls, title: str = '', text: str = '', values: list = None, default: list = None,
            result=None, **kwargs):
        """
        获取多选选择的主体内容清单
        注: 如果result设置为None代表生成可输入组件清单, 否则生成只读的结果清单
        """
        # 提示文本
        _text_field = Label(
            text, style='class:win-radio-text-field', wrap_lines=True,
        )
        _text_container = ConditionalContainer(
            content=_text_field, filter=Condition(lambda: text is not None and text != '')
        )

        # 选项
        if values is None:
            values = []

        _cb_list = ExtendCheckboxList(
            values=values, default_values=(default if result is None else result),
            realonly=(False if result is None else True)
        )

        return [_text_container, _cb_list]

    @classmethod
    def _get_checkboxlist_app(cls, title: str = '', text: str = '', values: list = None, default: list = None,
            show_title: bool = True, color_set: dict = None) -> Application:
        """
        获取多选选择的应用
        """
        # 颜色配置
        _style_default = cls._get_checkboxlist_style(color_set=color_set)

        # 输入框的快捷键绑定
        _kb = KeyBindings()

        # 标题框
        _title_field = Label(
            title, style='class:win-title-field', wrap_lines=False,
        )

        # 提示文本和选项
        _contents = cls._get_checkboxlist_content(
            title=title, text=text, values=values, default=default
        )
        _text_field = _contents[0]
        _cb_list = _contents[1]

        # 显示容器
        _container = FloatContainer(
            content=HSplit(
                [
                    # 标题
                    ConditionalContainer(
                        content=_title_field, filter=Condition(lambda: show_title)
                    ),
                    # 提示行
                    _text_field,
                    _cb_list,
                ], padding=0
            ),
            floats=[],
        )

        # 取消输入内容快捷键函数
        @_kb.add('c-c')
        def __cancle_input(event):
            get_app().exit(result=None)

        # 按enter返回结果
        @_kb.add('enter')
        def __accept_input(event):
            _app = get_app()
            _app.exit(result=_cb_list.current_values)

        # 创建应用并设置默认值
        _app = Application(
            layout=Layout(_container),
            key_bindings=merge_key_bindings([load_key_bindings(), _kb]),
            mouse_support=True,
            style=Style.from_dict(_style_default),
            full_screen=True,
        )
        return _app

    #############################
    # 构造函数
    #############################
    def __init__(self, message='CMD>', default='', **kwargs):
        """
        构造函数

        @param {string} message='CMD>' - 命令行提示符内容
        @param {string} default='' - string 交互输入的默认值, 直接显示在界面上, 可以进行修改后回车输入
        @param {kwargs} kwargs - 扩展参数, 分为两部分, 第一部分为类自行封装的扩展参数,
            第二部分为python-prompt-toolki的原生prompt参数(自行到到官网查找)
            第一部分扩展参数说明如下:
                cmd_para {cmdpara} - 命令参数字典
                ignore_case {bool} - 匹配命令是否忽略大小写, 默认值为False
                default_dealfun {function} - 在命令处理函数字典中没有匹配到的命令, 默认执行的处理函数
                    函数定义为fun(message='', cmd='', cmd_para=''), 返回值为string, 是执行命令函数要输出的内容
                on_abort {function} - 当用户取消输入(Ctrl + C)时执行的函数:
                    函数定义为fun(message=''), 返回值为string、string_iter或CResult, 是执行命令函数要输出的内容
                    如果结果为CResult, 实际打印内容为CResult.msg, 并可通过错误码10101退出命令行
                on_exit {fun} - 当用户退出(Ctrl + D)时执行的函数, 注意如果已输入部分内容, Ctrl + D将不生效:
                    函数定义为fun(message=''), 返回值为string、string_iter或CResult, 是执行命令函数要输出的内容
                    如果结果为CResult, 实际打印内容为CResult.msg, 并可通过错误码10101退出命令行
                logger {object} - logger 日志对象, 服务过程中通过该函数写日志:
                    可以为标准的logging日志库对象, 也可以为simple_log对象, 但要求对象实现:
                    标准的info、debug、warning、error、critical五个日志方法
                enable_color_set {bool} - 默认True, 使用配色集方案:
                    如果选否则自行通过python-prompt-toolkit的方式设定配色方案
                color_set {dict} - 要使用的配色集方案, 如果传None则使用系统默认配色集, 可自定义配色, 自定义的默认值如下:
                    '': '#F2F2F2',  # 默认字体配色
                    'cmd': '#13A10E',  # 命令
                    'name_para': '#C19C00',  # key-value形式参数名
                    'short_para': '#3B78FF',  # -char形式的短参数字符
                    'long_para': '#FFFF00',  # -name形式的长参数字符
                    'word_para': '#C19C00',  # word 形式的词字符
                    'wrong_tip': '#FF0000 bg:#303030',  # 错误的命令或参数名提示 #ff0000 bg:#ffffff reverse
                    'prompt': '#F2F2F2',  # prompt提示信息
                    'win-title-field': 'reverse',  # 窗口标题栏配色
                    'win-tips-field': 'reverse', # 窗口提示区域栏配色
                    'win-help-box': 'reverse', # 帮助窗口配色
                    'win-input-field': '',  # 窗口输入框配色
                    'win-output-field': '',  # 窗口输出区域配色
                    'horizontal-line': '',  # 横线配色
                    'line': '', # 横线和纵线的统一配色
                enable_cmd_auto_complete {bool} - 默认True, 是否启用命令行自动完成提示
                    1、如果启用, 则使用命令行自带的completer, 实现命令、参数的自动完成功能；
                        不启用则可以自行传入completer、complete_in_thread等原生参数
                    2、可以与complete_while_typing参数共同生效, 控制是按tab提示还是输入自动提示
                cmd_auto_complete_slow_time {float} - 默认0, 输入后延迟多久提示完成菜单
                enable_cmd_path_auto_complete {bool} - 默认True, 是否启动路径输入的自动提示
            窗口应用的扩展参数说明:
                win_show_title {bool} - 是否显示窗口标题, 默认为True
                win_title {str} - 窗口标题, 默认为'Prompt Plus Console'
                win_show_tips {bool} - 是否显示窗口提示栏, 默认为True
                win_tips_prompt {str} - 提示栏的前缀信息, 默认为'F1 打开帮助'
                win_help_box_para {dict} - 帮助窗口设置参数
                    help_text {str} - 帮助信息内容, 如果不想使用默认帮助文档, 请进行设置
                    title {str} - 帮助窗口标题, 默认为'帮助(q退出)'
                    preferred_width {int} - 最适合的宽度设置, 默认为45
                    preferred_height {int} - 最适合的高度设置, 默认为12
                    lexer {Lexer} - 显示文本的格式化样式对象, 可以直接使用第三方pygments包支持的样式, 例如:
                        from pygments.lexers.python import PythonLexer
                        设置lexer=PythonLexer()
                win_output_para {dict} - 输出区域的设置参数：
                    text {str} - 默认显示的内容, 默认为'命令处理窗口应用(输入过程中可通过Ctrl+C取消输入, 通过Ctrl+D退出命令行处理窗口)'
                    wrap_lines {bool} - 超长字符串是否换行显示, 默认为True
                    line_numbers {bool} - 是否显示行号, 默认为False
                    lexer {Lexer} - 显示文本的格式化样式对象, 可以直接使用第三方pygments包支持的样式, 例如:
                        from pygments.lexers.python import PythonLexer
                        设置lexer=PythonLexer()
                    cache_size {int} - 最大缓存文本的行数, 文本行数超过时将会删除前面的信息, 默认为800
                    selectable {bool} - 是否允许选中文本(获得焦点), 默认为True
                    enable_copy {bool} - 是否启用选中复制, 默认为True
                    action_tips {dict} 提示的转换字典, 可支持的提示信息包括:
                        {
                            'copy_to_clipboard': 'Copy Selection to clipboard Success'
                        }
                win_input_para {dict} - 输入框的设置参数:
                    height {int} - 输入框高度(支持多少行), 默认为1
                    multiline {bool} - 是否支持多行输入, 默认为False
                    wrap_lines {bool} - 超出屏幕的句子是否自动换行, 默认为True
                    scrollbar {bool} - 是否支持滚动, 默认为True
                win_key_bindings {dict} - 窗口的快捷键设置字典
                    {
                        #  全局快捷键
                        'exit': 'c-d',  # ctrl+d, 退出应用
                        'open_help_box': 'f1',  # f1, 开启帮助窗口, 如果不想打开帮助窗口, 请设置键值为''
                        # 输入框快捷键
                        'cancel': 'c-c',  # ctrl+c, 取消输入(输入框有焦点时)
                        'accept': 'enter', # 回车, 非multiline模式的提交
                        'mutiline_accept': ('c-s'),  # ctrl+s, multiline模式的提交
                        # 输出区域快捷键
                        'copy_to_clipboard': 'c-c',  # ctrl+c输出内容选中文本的复制快捷键, 仅win_output_para的enable_copy开启后有效
                        # 帮助窗口快捷键
                        'exit_help_box': 'q',  # q, 关闭帮助窗口
                    }
        """
        # 指定不初始化PromptSession对象
        self._is_init_prompt_instance = False

        # 父类的初始化处理
        super().__init__(message=message, default=default, **kwargs)

        # 控制是否显示某个栏位的参数
        self.win_show_title = kwargs.get('win_show_title', True)
        self.win_show_tips = kwargs.get('win_show_tips', True)
        self._win_show_help_box = False

        # 应用自己的参数
        self._win_title = kwargs.get('win_title', 'Prompt Plus Console')
        self._win_tips_prompt = kwargs.get('win_tips_prompt', 'F1 打开帮助')
        self._win_help_box_para = {
            'help_text': (
                '全局快捷键:\n'
                '  Ctrl + D > 退出窗口\n'
                '  Ctrl + H > 打开帮助窗口\n'
                '\n'
                '输入栏位快捷键:\n'
                '  Enter > 单行输入模式提交命令\n'
                '  Ctrl + S > 多行输入模式提交命令\n'
                '  Ctrl + C > 取消当前输入内容\n'
                '\n'
                '屏幕输出内容快捷键:\n'
                '  Ctrl + C > 复制选中内容到操作系统剪贴版'
            ),
            'title': '帮助(q退出)',
            'preferred_width': 45,
            'preferred_height': 12
        }
        self._win_help_box_para.update(kwargs.get('win_help_box_para', {}))
        self._win_help_text = self._win_help_box_para['help_text']

        # 配色处理
        self._win_style_default = {
            'win-title-field': 'reverse', 'win-tips-field': 'reverse', 'win-help-box': 'reverse'
        }
        self._win_style = copy.deepcopy(self._win_style_default)
        if self._prompt_init_para['enable_color_set']:
            # 启用自定义颜色
            self._win_style.update(self._prompt_init_para['color_set'])

        # 输出区域的样式设置
        self._win_output_para = {
            'text': '命令处理窗口应用(输入过程中可通过Ctrl+C取消输入, 通过Ctrl+D退出命令行处理窗口)',
            'wrap_lines': True, 'line_numbers': False, 'cache_size': 800, 'selectable': True,
            'enable_copy': True
        }
        self._win_output_para.update(kwargs.get('win_output_para', {}))

        # 输入框的样式设置
        self._win_input_para = {
            'height': 1, 'multiline': False, 'wrap_lines': True, 'scrollbar': True
        }
        self._win_input_para.update(kwargs.get('win_input_para', {}))

        # 快捷键
        self._win_key_bindings = {
            #  全局快捷键
            'exit': 'c-d',  # ctrl+d, 退出应用
            'open_help_box': 'f1',  # f1, 开启帮助窗口, 如果不想打开帮助窗口, 请设置键值为''
            # 输入框快捷键
            'cancel': 'c-c',  # ctrl+c, 取消输入(输入框有焦点时)
            'accept': 'enter', # 回车, 非multiline模式的提交
            'mutiline_accept': ('c-s'),  # ctrl+s, multiline模式的提交
            # 输出区域快捷键
            'copy_to_clipboard': 'c-c',  # ctrl+c输出内容选中文本的复制快捷键, 仅win_output_para的enable_copy开启后有效
            # 帮助窗口快捷键
            'exit_help_box': 'q',  # q, 关闭帮助窗口
        }
        self._win_key_bindings.update(kwargs.get('win_key_bindings', {}))
        for _key, _val in self._win_key_bindings.items():
            # 转换为标准的数组模式
            if type(_val) == str:
                self._win_key_bindings[_key] = (_val, )

        self._global_key_bindings = KeyBindings()  # 全局的快捷键绑定

        # 输出区域的参数标准化处理
        _enable_copy = self._win_output_para.pop('enable_copy', False)
        if _enable_copy:
            self._win_output_para['key_bindings'] = {
                'copy_to_clipboard': self._win_key_bindings['copy_to_clipboard']
            }

        # 初始化窗口应用
        self._init_application()

    #############################
    # 重载的公共函数
    #############################
    def start_prompt_service(self, title=None, text=None):
        """
        启动命令行服务(循环获取用户输入并执行相应命令)

        @param {str} title=None - 窗口标题
        @param {str} text=None - 窗口初始显示信息
        """
        # 重置窗口应用
        self._reset_application(title, text)

        # with extend_patch_stdout(output=self._output_redirect_obj):
        with extend_patch_stdout(output=self._output_redirect_obj):
            self._app.run()

    def output(self, text: str, end: str = '\n'):
        """
        将指定内容输出到屏幕

        @param {str} text - 要输出的文本内容
        @param {str} end='\n' - 文本结束内容, 如果不想换行可以传入''
        """
        self._output_field.output(text, end=end)

    def clear(self):
        """
        清空输出文本
        """
        self._output_field.clear()

    def show_tips(self, tips: str):
        """
        显示提示信息

        @param {str} tips - 提示信息
        """
        if self.win_show_tips:
            self._tips_field.text = '%s - %s' % (self._win_tips_prompt, tips)

    def open_help_box(self, text: str = None):
        """
        开启帮助窗口

        @param {str} text=None - 如果开启时要改变帮助窗口的显示内容, 可传入值
        """
        if text is not None:
            self._help_box.body.text = text

        self._win_show_help_box = True
        get_app().layout.focus(self._help_box)

    def close_help_box(self):
        """
        关闭帮助窗口
        """
        self._win_show_help_box = False
        get_app().layout.focus(self._input_field)

    def prompt_once(self, input_text: str):
        """
        处理一次命令输入

        @returns {CResult} - 处理结果, code定义如下:
            '00000' - 成功
            '29999' - 其他系统失败
            '10100' - 用户中断输入(Ctrl + C)
            '10101' - 用户退出应用(Ctrl + D)

        """
        _run_result = CResult(code='00000', msg=u'success')  # 执行某个方法的结果
        try:
            _cmd_str = input_text

            # 处理输入
            if len(_cmd_str) > 0:
                _run_result = self._call_on_cmd(message=self._message, cmd_str=_cmd_str)
            else:
                # self.prompt_print('')
                return CResult(code='00000')
        except KeyboardInterrupt:
            # 执行on_abort函数
            _run_result = self._call_on_abort(message=self._message)
        except EOFError:
            # 执行on_exit函数
            _run_result = self._call_on_exit(message=self._message)
        except:
            # 其他异常
            _run_result = CResult(
                code='29999', error=str(sys.exc_info()), trace_str=traceback.format_exc()
            )
            self.prompt_print('prompt_once run exception (%s):\r\n%s' %
                              (_run_result.error, _run_result.trace_str))

        _real_result = self._deal_run_result(_run_result)

        return _real_result

    #############################
    # 内部函数
    #############################
    def _init_application(self):
        """
        初始化应用
        """
        # 窗口标题行
        self._title_field = self._create_title_field()

        # 上方屏幕输出区域
        self._output_field = self._create_output_field()
        self._output_redirect_obj = StdOutputTextAreaOutput(self._output_field)

        # 命令输入框
        self._input_field = self._create_input_field()

        # 提示栏
        self._tips_field = self._create_tips_field()

        # 帮助窗口
        self._help_box = self._create_help_box()

        self._container = FloatContainer(
            content=HSplit(
                [
                    # 首行提示行
                    ConditionalContainer(
                        content=self._title_field, filter=Condition(lambda: self.win_show_title)
                    ),
                    # 输出区域
                    self._output_field.text_area,
                    # 分割线
                    HorizontalLine(),
                    self._input_field,
                    # 提示栏
                    ConditionalContainer(
                        content=self._tips_field, filter=Condition(lambda: self.win_show_tips)
                    ),
                ]
            ),
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                ),
                Float(
                    ConditionalContainer(
                        content=self._help_box,
                        filter=Condition(lambda: self._win_show_help_box and has_focus(self._help_box)())
                    )
                ),
            ],
        )

        # 关闭窗口快捷键函数
        @self._global_key_bindings.add(*self._win_key_bindings['exit'])
        def __exit_app(event):
            # 执行on_exit函数
            _run_result = self._call_on_exit(message=self._message)
            _real_result = self._deal_run_result(_run_result)
            if _real_result.code == '10101':
                # 指令要求退出窗口
                event.app.exit()

        # 打开帮助窗口的快捷函数
        if self._win_key_bindings['open_help_box'] is not None and self._win_key_bindings['open_help_box'] != '':
            @self._global_key_bindings.add(*self._win_key_bindings['open_help_box'])
            def __open_help_box(event):
                self.open_help_box()

        self._app = Application(
            layout=Layout(self._container, focused_element=self._input_field),
            key_bindings=self._global_key_bindings, style=Style.from_dict(self._win_style),
            mouse_support=True, full_screen=True, paste_mode=True, clipboard=PyperclipClipboard(),
            erase_when_done=True
        )

    def _reset_application(self, title, text):
        """
        重置应用参数
        """
        # 重置显示信息
        if self.win_show_title and title is not None:
            self._win_title = title
            self._title_field.text = self._win_title
        if self.win_show_tips:
            self._tips_field.text = self._win_tips_prompt

        if text is not None:
            self._win_output_para['text'] = text

        self._output_field.set_text('%s\n' % text)

        # 设置输出窗口的提示函数, 需要对象初始化成功送入才没有问题
        self._output_field.set_show_tips_func(self.show_tips)

    def _create_title_field(self) -> Label:
        """
        创建标题区域

        @returns {Label} - 标题窗口对象
        """
        return Label(
            self._win_title, style='class:win-title-field', wrap_lines=False,
        )

    def _create_tips_field(self) -> Label:
        """
        创建提示区域

        @returns {Label} - 其实区域窗口对象
        """
        return Label(
            self._win_tips_prompt, style='class:win-tips-field', wrap_lines=False,
        )

    def _create_help_box(self) -> Frame:
        """
        创建帮助提示框

        @returns {Frame} - 帮助窗口对象
        """
        _app_size = get_app().output.get_size()
        _kb = KeyBindings()

        @_kb.add(*self._win_key_bindings['exit_help_box'])
        def __exit_help_box(event):
            self.close_help_box()

        _area_kwargs = {
            'text': self._win_help_text,
            'width': D(min=5, max=(_app_size.columns - 10), preferred=self._win_help_box_para['preferred_width']),
            'height': D(min=1, max=(_app_size.rows - 4), preferred=self._win_help_box_para['preferred_height']),
            'lexer': self._win_help_box_para.get('lexer', None),
            'dont_extend_height': True,
            'dont_extend_width': True,
            'read_only': True,
            'focusable': True,
            'focus_on_click': True,
            'scrollbar': True,
            'buffer_control_kwargs': {
                'key_bindings': _kb
            }
        }

        return Frame(
            ExtendTextArea(**_area_kwargs), title=self._win_help_box_para['title'], style='class:win-help-box'
        )

    def _create_output_field(self) -> StdOutputTextArea:
        """
        生成输出文本区域

        @returns {ExtendTextArea} - 生成的区域对象
        """
        # 处理创建参数
        _kwargs = copy.deepcopy(self._win_output_para)
        _kwargs.update({
            'text': '',
            'style': 'class:win-output-field',
        })
        _text_field = StdOutputTextArea(**_kwargs)
        return _text_field

    def _create_input_field(self) -> ExtendTextArea:
        """
        生成输入文本区域

        @returns {ExtendTextArea} - 生成的区域对象
        """
        # 输入框的快捷键绑定
        _kb = KeyBindings()

        # 取消输入内容快捷键函数
        @_kb.add(*self._win_key_bindings['cancel'])
        def __clear_input(event):
            self._clear_input_field()

        # 多行模式使用enter换行, ctrl + enter提交
        @_kb.add(*self._win_key_bindings['mutiline_accept'])
        @_kb.add(*self._win_key_bindings['accept'], filter=(not self._win_input_para['multiline']))
        def __input_field_accept(event):
            self._input_field_accept()
            self._clear_input_field()

        _kwargs = {
            'text': '',
            'prompt': self._message,
            'style': 'class:win-input-field',
            'multiline': self._win_input_para['multiline'],
            'wrap_lines': self._win_input_para['wrap_lines'],
            'height': self._win_input_para['height'],
            'focus_on_click': True,
            'read_only': False,
            'scrollbar': self._win_input_para['multiline'],
            'buffer_control_kwargs': {
                'key_bindings': _kb
            }
        }

        if self._prompt_init_para['enable_cmd_auto_complete']:
            _kwargs['completer'] = self._prompt_init_para['completer']

        if self._prompt_init_para['enable_color_set']:
            _kwargs['lexer'] = self._prompt_init_para['lexer']

        _text_field = ExtendTextArea(**_kwargs)
        return _text_field

    # TODO(lhj): 未解决日志输出无法重定向的问题
    # TODO(lhj): 未解决执行函数输出无法在执行期间显示在界面的问题
    def _input_field_accept(self):
        """
        输入区域提交输入内容
        """
        _text = self._input_field.text
        self._clear_input_field()  # 清空输入框内容

        # 获取命令执行结果
        _result = self.prompt_once(_text)

        if _result.code == '10101':
            # 退出获取命令处理
            get_app().exit()

    def _clear_input_field(self):
        """
        清空输入框内容
        """
        self._input_field.text = ''


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
    import time

    def run_callback(set_percentage, log_text):
        for i in range(10):
            set_percentage(i*10)
            log_text('haha: %d\n' % i)
            time.sleep(1)

        set_percentage(100)

    print(PromptPlusConsoleApp.prompt_continuous(
        [
            {
                'id': 'id1', 'type': 'simple_prompt', 'para': {
                    'title': 'title1', 'text': 'text1', 'height': None
                }
            },
            {
                'id': 'id4', 'type': 'confirm', 'para': {
                    'title': 'title4', 'text': 'text4',
                }
            },
            {
                'id': 'id5', 'type': 'radiolist', 'para': {
                    'title': 'title5', 'text': 'text5', 'values': [
                        ('a', 'atext'), ('b', 'btext'), ('c', 'ctext')
                    ],
                    'default': 'b'
                }
            },
            {
                'id': 'id6', 'type': 'checkboxlist', 'para': {
                    'title': 'title6', 'text': 'text6', 'values': [
                        ('a', 'atext'), ('b', 'btext'), ('c', 'ctext')
                    ],
                    'default': ['b', 'c']
                }
            },
            {
                'id': 'id2', 'type': 'simple_prompt', 'para': {
                    'title': 'title2', 'text': 'text2',
                }
            },
            {
                'id': 'id3', 'type': 'simple_prompt', 'para': {
                    'title': 'title3', 'text': 'text3',
                }
            }
        ]
    ))
