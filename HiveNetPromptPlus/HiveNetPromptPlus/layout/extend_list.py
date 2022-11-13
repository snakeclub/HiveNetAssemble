#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
扩展的_DialogList支持

@module extend_list
@file extend_list.py
"""
from functools import partial
from typing import Callable, Generic, List, Optional, Sequence, Tuple, TypeVar, Union

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

E = KeyPressEvent
_T = TypeVar("_T")


class _ExtendDialogList(Generic[_T]):
    """
    Common code for `RadioList` and `CheckboxList`.
    注: 增加只读显示的支持
    """

    open_character: str = ""
    close_character: str = ""
    container_style: str = ""
    default_style: str = ""
    selected_style: str = ""
    checked_style: str = ""
    multiple_selection: bool = False
    show_scrollbar: bool = True

    def __init__(
        self,
        values: Sequence[Tuple[_T, AnyFormattedText]],
        default_values: Optional[Sequence[_T]] = None,
        realonly: bool = False
    ) -> None:
        assert len(values) > 0
        default_values = default_values or []

        self.values = values
        # current_values will be used in multiple_selection,
        # current_value will be used otherwise.
        keys: List[_T] = [value for (value, _) in values]
        self.current_values: List[_T] = [
            value for value in default_values if value in keys
        ]
        self.current_value: _T = (
            default_values[0]
            if len(default_values) and default_values[0] in keys
            else values[0][0]
        )

        # Cursor index: take first selected item or first item otherwise.
        if len(self.current_values) > 0:
            self._selected_index = keys.index(self.current_values[0])
        else:
            self._selected_index = 0

        # Key bindings.
        kb = KeyBindings()

        if not realonly:
            @kb.add("up")
            def _up(event: E) -> None:
                self._selected_index = max(0, self._selected_index - 1)

            @kb.add("down")
            def _down(event: E) -> None:
                self._selected_index = min(len(self.values) - 1, self._selected_index + 1)

            @kb.add("pageup")
            def _pageup(event: E) -> None:
                w = event.app.layout.current_window
                if w.render_info:
                    self._selected_index = max(
                        0, self._selected_index - len(w.render_info.displayed_lines)
                    )

            @kb.add("pagedown")
            def _pagedown(event: E) -> None:
                w = event.app.layout.current_window
                if w.render_info:
                    self._selected_index = min(
                        len(self.values) - 1,
                        self._selected_index + len(w.render_info.displayed_lines),
                    )

            # @kb.add("enter")  # 改为回车提交
            @kb.add(" ")
            def _click(event: E) -> None:
                self._handle_enter()

            @kb.add(Keys.Any)
            def _find(event: E) -> None:
                # We first check values after the selected value, then all values.
                values = list(self.values)
                for value in values[self._selected_index + 1:] + values:
                    text = fragment_list_to_text(to_formatted_text(value[1])).lower()

                    if text.startswith(event.data.lower()):
                        self._selected_index = self.values.index(value)
                        return

        # Control and window.
        self.control = FormattedTextControl(
            self._get_text_fragments, key_bindings=kb, focusable=(not realonly)
        )

        self.window = Window(
            content=self.control,
            style=self.container_style,
            right_margins=[
                ConditionalMargin(
                    margin=ScrollbarMargin(display_arrows=True),
                    filter=Condition(lambda: self.show_scrollbar),
                ),
            ],
            dont_extend_height=True,
        )

    def _handle_enter(self) -> None:
        if self.multiple_selection:
            val = self.values[self._selected_index][0]
            if val in self.current_values:
                self.current_values.remove(val)
            else:
                self.current_values.append(val)
        else:
            self.current_value = self.values[self._selected_index][0]

    def _get_text_fragments(self) -> StyleAndTextTuples:
        def mouse_handler(mouse_event: MouseEvent) -> None:
            """
            Set `_selected_index` and `current_value` according to the y
            position of the mouse click event.
            """
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self._selected_index = mouse_event.position.y
                self._handle_enter()

        result: StyleAndTextTuples = []
        for i, value in enumerate(self.values):
            if self.multiple_selection:
                checked = value[0] in self.current_values
            else:
                checked = value[0] == self.current_value
            selected = i == self._selected_index

            style = ""
            if checked:
                style += " " + self.checked_style
            if selected:
                style += " " + self.selected_style

            result.append((style, self.open_character))

            if selected:
                result.append(("[SetCursorPosition]", ""))

            if checked:
                result.append((style, "*"))
            else:
                result.append((style, " "))

            result.append((style, self.close_character))
            result.append((self.default_style, " "))
            result.extend(to_formatted_text(value[1], style=self.default_style))
            result.append(("", "\n"))

        # Add mouse handler to all fragments.
        for i in range(len(result)):
            result[i] = (result[i][0], result[i][1], mouse_handler)

        result.pop()  # Remove last newline.
        return result

    def __pt_container__(self) -> Container:
        return self.window


class ExtendRadioList(_ExtendDialogList[_T]):
    """
    List of radio buttons. Only one can be checked at the same time.

    :param values: List of (value, label) tuples.
    """

    open_character = "("
    close_character = ")"
    container_style = "class:radio-list"
    default_style = "class:radio"
    selected_style = "class:radio-selected"
    checked_style = "class:radio-checked"
    multiple_selection = False

    def __init__(
        self,
        values: Sequence[Tuple[_T, AnyFormattedText]],
        default: Optional[_T] = None,
        realonly: bool = False
    ) -> None:
        if default is None:
            default_values = None
        else:
            default_values = [default]

        super().__init__(values, default_values=default_values, realonly=realonly)


class ExtendCheckboxList(_ExtendDialogList[_T]):
    """
    List of checkbox buttons. Several can be checked at the same time.

    :param values: List of (value, label) tuples.
    """

    open_character = "["
    close_character = "]"
    container_style = "class:checkbox-list"
    default_style = "class:checkbox"
    selected_style = "class:checkbox-selected"
    checked_style = "class:checkbox-checked"
    multiple_selection = True


class ExtendCheckbox(ExtendCheckboxList[str]):
    """Backward compatibility util: creates a 1-sized CheckboxList

    :param text: the text
    """

    show_scrollbar = False

    def __init__(self, text: AnyFormattedText = "", checked: bool = False, realonly: bool = False) -> None:
        values = [("value", text)]
        super().__init__(values=values, realonly=realonly)
        self.checked = checked

    @property
    def checked(self) -> bool:
        return "value" in self.current_values

    @checked.setter
    def checked(self, value: bool) -> None:
        if value:
            self.current_values = ["value"]
        else:
            self.current_values = []
