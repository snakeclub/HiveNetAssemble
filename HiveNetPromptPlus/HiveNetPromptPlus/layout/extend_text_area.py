#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
扩展的TextArea组件

@module extend_text_area
@file extend_text_area.py
"""
from prompt_toolkit.widgets import TextArea, SearchToolbar
from functools import partial
from typing import Callable, Generic, List, Optional, Sequence, Tuple, TypeVar, Union

from prompt_toolkit.output import Output, DummyOutput
from prompt_toolkit.application.current import get_app
from prompt_toolkit.auto_suggest import AutoSuggest, DynamicAutoSuggest
from prompt_toolkit.buffer import Buffer, BufferAcceptHandler
from prompt_toolkit.completion import Completer, DynamicCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.filters import (
    Condition,
    FilterOrBool,
    has_focus,
    is_done,
    is_true,
    to_filter,
)
from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    StyleAndTextTuples,
    Template,
    to_formatted_text,
)
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.history import History
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import (
    AnyContainer,
    ConditionalContainer,
    Container,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import (
    BufferControl,
    FormattedTextControl,
    GetLinePrefixCallable,
)
from prompt_toolkit.layout.dimension import AnyDimension
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.dimension import to_dimension
from prompt_toolkit.layout.margins import (
    ConditionalMargin,
    NumberedMargin,
    ScrollbarMargin,
)
from prompt_toolkit.layout.processors import (
    AppendAutoSuggestion,
    BeforeInput,
    ConditionalProcessor,
    PasswordProcessor,
    Processor,
)
from prompt_toolkit.lexers import DynamicLexer, Lexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.validation import DynamicValidator, Validator

from HiveNetCore.utils.string_tool import StringTool


class ExtendBuffer(Buffer):
    """
    扩展的Buffer对象, 支持在read_only的状态下修改文本信息
    """

    @property
    def text(self) -> str:
        return self._working_lines[self.working_index]

    @text.setter
    def text(self, value: str) -> None:
        """
        Setting text. (When doing this, make sure that the cursor_position is
        valid for this text. text/cursor_position should be consistent at any time,
        otherwise set a Document instead.)
        """
        # Ensure cursor position remains within the size of the text.
        if self.cursor_position > len(value):
            self.cursor_position = len(value)

        # 屏蔽不允许修改的情况
        # Don't allow editing of read-only buffers.
        # if self.read_only():
        #     raise EditReadOnlyBuffer()

        changed = self._set_text(value)

        if changed:
            self._text_changed()

            # Reset history search text.
            # (Note that this doesn't need to happen when working_index
            #  changes, which is when we traverse the history. That's why we
            #  don't do this in `self._text_changed`.)
            self.history_search_text = None

    def set_document(self, value: Document, bypass_readonly: bool = False) -> None:
        """
        Set :class:`~prompt_toolkit.document.Document` instance. Like the
        ``document`` property, but accept an ``bypass_readonly`` argument.

        :param bypass_readonly: When True, don't raise an
                                :class:`.EditReadOnlyBuffer` exception, even
                                when the buffer is read-only.

        .. warning::

            When this buffer is read-only and `bypass_readonly` was not passed,
            the `EditReadOnlyBuffer` exception will be caught by the
            `KeyProcessor` and is silently suppressed. This is important to
            keep in mind when writing key bindings, because it won't do what
            you expect, and there won't be a stack trace. Use try/finally
            around this function if you need some cleanup code.
        """
        # 屏蔽不允许修改的情况
        # Don't allow editing of read-only buffers.
        # if not bypass_readonly and self.read_only():
        #     raise EditReadOnlyBuffer()

        # Set text and cursor position first.
        text_changed = self._set_text(value.text)
        cursor_position_changed = self._set_cursor_position(value.cursor_position)

        # Now handle change events. (We do this when text/cursor position is
        # both set and consistent.)
        if text_changed:
            self._text_changed()
            self.history_search_text = None

        if cursor_position_changed:
            self._cursor_position_changed()


class ExtendTextArea(TextArea):
    """
    扩展的TextArea组件, 扩展更多的参数支持

    A simple input field.

    This is a higher level abstraction on top of several other classes with
    sane defaults.

    This widget does have the most common options, but it does not intend to
    cover every single use case. For more configurations options, you can
    always build a text area manually, using a
    :class:`~prompt_toolkit.buffer.Buffer`,
    :class:`~prompt_toolkit.layout.BufferControl` and
    :class:`~prompt_toolkit.layout.Window`.

    Buffer attributes:

    :param text: The initial text.
    :param multiline: If True, allow multiline input.
    :param completer: :class:`~prompt_toolkit.completion.Completer` instance
        for auto completion.
    :param complete_while_typing: Boolean.
    :param accept_handler: Called when `Enter` is pressed (This should be a
        callable that takes a buffer as input).
    :param history: :class:`~prompt_toolkit.history.History` instance.
    :param auto_suggest: :class:`~prompt_toolkit.auto_suggest.AutoSuggest`
        instance for input suggestions.

    BufferControl attributes:

    :param password: When `True`, display using asterisks.
    :param focusable: When `True`, allow this widget to receive the focus.
    :param focus_on_click: When `True`, focus after mouse click.
    :param input_processors: `None` or a list of
        :class:`~prompt_toolkit.layout.Processor` objects.
    :param validator: `None` or a :class:`~prompt_toolkit.validation.Validator`
        object.

    Window attributes:

    :param lexer: :class:`~prompt_toolkit.lexers.Lexer` instance for syntax
        highlighting.
    :param wrap_lines: When `True`, don't scroll horizontally, but wrap lines.
    :param width: Window width. (:class:`~prompt_toolkit.layout.Dimension` object.)
    :param height: Window height. (:class:`~prompt_toolkit.layout.Dimension` object.)
    :param scrollbar: When `True`, display a scroll bar.
    :param style: A style string.
    :param dont_extend_width: When `True`, don't take up more width then the
                              preferred width reported by the control.
    :param dont_extend_height: When `True`, don't take up more width then the
                               preferred height reported by the control.
    :param get_line_prefix: None or a callable that returns formatted text to
        be inserted before a line. It takes a line number (int) and a
        wrap_count and returns formatted text. This can be used for
        implementation of line continuations, things like Vim "breakindent" and
        so on.

    Other attributes:

    :param search_field: An optional `SearchToolbar` object.
    """

    #############################
    # 构造函数扩展
    #############################
    def __init__(
        self,
        text: str = "",
        multiline: FilterOrBool = True,
        password: FilterOrBool = False,
        lexer: Optional[Lexer] = None,
        auto_suggest: Optional[AutoSuggest] = None,
        completer: Optional[Completer] = None,
        complete_while_typing: FilterOrBool = True,
        validator: Optional[Validator] = None,
        accept_handler: Optional[BufferAcceptHandler] = None,
        history: Optional[History] = None,
        focusable: FilterOrBool = True,
        focus_on_click: FilterOrBool = False,
        wrap_lines: FilterOrBool = True,
        read_only: FilterOrBool = False,
        width: AnyDimension = None,
        height: AnyDimension = None,
        dont_extend_height: FilterOrBool = False,
        dont_extend_width: FilterOrBool = False,
        line_numbers: bool = False,
        get_line_prefix: Optional[GetLinePrefixCallable] = None,
        scrollbar: bool = False,
        style: str = "",
        search_field: Optional[SearchToolbar] = None,
        preview_search: FilterOrBool = True,
        prompt: AnyFormattedText = "",
        input_processors: Optional[List[Processor]] = None,
        name: str = "",
        buffer_kwargs: dict = {},
        buffer_control_kwargs: dict = {},
        window_kwargs: dict = {}
    ) -> None:
        if search_field is None:
            search_control = None
        elif isinstance(search_field, SearchToolbar):
            search_control = search_field.control

        if input_processors is None:
            input_processors = []

        # Writeable attributes.
        self.completer = completer
        self.complete_while_typing = complete_while_typing
        self.lexer = lexer
        self.auto_suggest = auto_suggest
        self.read_only = read_only
        self.wrap_lines = wrap_lines
        self.validator = validator

        self.buffer = ExtendBuffer(
            document=Document(text, 0),
            multiline=multiline,
            read_only=Condition(lambda: is_true(self.read_only)),
            completer=DynamicCompleter(lambda: self.completer),
            complete_while_typing=Condition(
                lambda: is_true(self.complete_while_typing)
            ),
            validator=DynamicValidator(lambda: self.validator),
            auto_suggest=DynamicAutoSuggest(lambda: self.auto_suggest),
            accept_handler=accept_handler,
            history=history,
            name=name,
            **buffer_kwargs
        )

        self.control = BufferControl(
            buffer=self.buffer,
            lexer=DynamicLexer(lambda: self.lexer),
            input_processors=[
                ConditionalProcessor(
                    AppendAutoSuggestion(), has_focus(self.buffer) & ~is_done
                ),
                ConditionalProcessor(
                    processor=PasswordProcessor(), filter=to_filter(password)
                ),
                BeforeInput(prompt, style="class:text-area.prompt"),
            ]
            + input_processors,
            search_buffer_control=search_control,
            preview_search=preview_search,
            focusable=focusable,
            focus_on_click=focus_on_click,
            **buffer_control_kwargs
        )

        if multiline:
            if scrollbar:
                right_margins = [ScrollbarMargin(display_arrows=True)]
            else:
                right_margins = []
            if line_numbers:
                left_margins = [NumberedMargin()]
            else:
                left_margins = []
        else:
            # height = D.exact(1)
            left_margins = []
            right_margins = []

        style = "class:text-area " + style

        # If no height was given, guarantee height of at least 1.
        if height is None:
            height = D(min=1)

        self.window = Window(
            height=height,
            width=width,
            dont_extend_height=dont_extend_height,
            dont_extend_width=dont_extend_width,
            content=self.control,
            style=style,
            wrap_lines=Condition(lambda: is_true(self.wrap_lines)),
            left_margins=left_margins,
            right_margins=right_margins,
            get_line_prefix=get_line_prefix,
            **window_kwargs
        )


#############################
# StdOutputTextArea
#############################
class StdOutputTextAreaOutput(DummyOutput):
    """
    针对StdOutputTextArea重定向输出的处理类
    """
    def __init__(self, output_obj) -> None:
        """
        构造函数

        @param {StdOutputTextArea} output_obj - 要输出的对象
        """
        super().__init__()
        self.output_obj = output_obj

    def write(self, data: str) -> None:
        self.output_obj.output(data, end='')  # 输出到区域, 不添加换行

    def write_raw(self, data: str) -> None:
        self.output_obj.output(data, end='')  # 输出到区域, 不添加换行


class StdOutputTextArea(object):
    """
    屏幕标准输出区域
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, text: str = '', wrap_lines: bool = True, line_numbers: bool = False,
            lexer: Lexer = None, style: str = '', cache_size: int = 800, selectable: bool = True,
            key_bindings: dict = None, show_tips_func=None, action_tips: dict = None) -> None:
        """
        构造函数

        @param {str} text - 初始对象的文本
        @param {bool} wrap_lines=True - 超长字符串是否换行显示
        @param {bool} line_numbers=False - 是否显示行号
        @param {Lexer} lexer=None - 显示文本的格式化样式对象, 可以直接使用第三方pygments包支持的样式, 例如:
            from pygments.lexers.python import PythonLexer
            设置lexer=PythonLexer()
        @param {str} style - 对象样式(例如'class:win-output-field')
        @param {int} cache_size=800 - 最大缓存文本的行数, 文本行数超过时将会删除前面的信息
        @param {bool} selectable=True - 是否允许选中文本(获得焦点)
        @param {dict} key_bindings=None - 设置快捷键, 如果有设置快捷键代表启用相关功能, 支持快捷键如下:
            {
                'copy_to_clipboard': 'c-c',  # 复制选中文本到剪贴板, 可以设置为ctrl+c
            }
        @param {function} show_tips_func=None - 外部送入可以显示操作提示的函数, 部分操作进行提示处理
        @param {dict} action_tips=None - 提示的转换字典, 可支持的提示信息包括:
            {
                'copy_to_clipboard': 'Copy Selection to clipboard Success'
            }

        """
        # 保存参数
        self.cache_size = cache_size
        self._show_tips_func = show_tips_func
        self._action_tips = {
            'copy_to_clipboard': 'Copy Selection to clipboard Success'
        }
        if action_tips is not None:
            self._action_tips.update(action_tips)

        # 内部变量
        self._line_count = StringTool.lines_count(text)

        # 创建输出对象的参数
        _area_kwargs = {
            'text': text,
            'style': style,
            'read_only': True,
            'scrollbar': True,
            'focusable': selectable,
            'focus_on_click': selectable,
            'wrap_lines': wrap_lines,
            'line_numbers': line_numbers,
            'lexer': lexer,
            'buffer_control_kwargs': {},
        }

        # 处理快捷键
        if key_bindings is not None:
            _kb = KeyBindings()

            # 复制选中文本到剪贴板
            _keys = key_bindings.get('copy_to_clipboard', None)
            if _keys is not None:
                if type(_keys) == str:
                    _keys = (_keys, )

                # 定义快捷键处理函数
                @_kb.add(*_keys)
                def __copy_to_clipboard(event):
                    self.copy_selection_to_clipboard()
                    if self._show_tips_func is not None:
                        self._show_tips_func(self._action_tips['copy_to_clipboard'])

            # 添加到创建参数
            _area_kwargs['buffer_control_kwargs']['key_bindings'] = _kb

        self.text_area = ExtendTextArea(**_area_kwargs)

    #############################
    # 公共处理函数
    #############################
    def clear(self):
        """
        清空输出文本
        """
        self.text_area.text = ''
        self._line_count = 1

    def output(self, text: str, end: str = '\n'):
        """
        向屏幕输出信息

        @param {str} text - 要输出的文本内容
        @param {str} end='\n' - 文本结束内容, 如果不想换行可以传入''
        """
        _add_text = '%s%s' % (text, end)
        _new_count = StringTool.lines_count(_add_text) - 1
        _count = self._line_count + _new_count
        if _count > self.cache_size:
            _cut_line = _count - self.cache_size
            if _cut_line >= self._line_count:
                # 要删除的行大于原来的内容
                _append = _add_text
                _cut_line = _cut_line - self._line_count
                if _cut_line > 0:
                    # 需要继续删除
                    _index = StringTool.find_nth_index(
                        _append, '\n', n=_cut_line
                    )
                    if _index >= 0:
                        _append = _append[_index + 1:]
                        _new_count = _new_count - _cut_line
                self._line_count = _new_count
            else:
                # 需要截取前面的文本并去掉
                _last_text = self.text_area.text
                _index = StringTool.find_nth_index(
                    _last_text, '\n', n=_cut_line
                )
                if _index < 0:
                    # 有异常情况, 直接全部显示
                    _append = '%s%s' % (_last_text, _add_text)
                    self._line_count = StringTool.lines_count(_append)
                else:
                    _append = '%s%s' % (_last_text[_index + 1:], _add_text)
                    self._line_count = self.cache_size
        else:
            _append = '%s%s' % (self.text_area.text, _add_text)
            self._line_count = _count

        self.text_area.buffer.document = Document(
            text=_append, cursor_position=len(_append)
        )

    def set_text(self, text: str):
        """
        设置输出对象默认文本

        @param {str} text - <description>
        """
        self.text_area.text = text
        self._line_count = StringTool.lines_count(text)

    def get_selection(self) -> str:
        """
        获取选中的文本内容

        @returns {str} - 返回选中的文本内容
        """
        _data = self.text_area.buffer.copy_selection()
        return _data.text

    def copy_selection_to_clipboard(self):
        """
        复制选中的文本内容到系统剪贴板
        """
        _data = self.text_area.buffer.copy_selection()
        get_app().clipboard.set_data(_data)

    def set_show_tips_func(self, show_tips_func):
        """
        设置提示函数

        @param {function} show_tips_func - 提示函数
        """
        self._show_tips_func = show_tips_func
