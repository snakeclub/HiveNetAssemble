#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
增强的交互命令行扩展处理, 基于prompt_toolkit进行封装和扩展

@module prompt_plus
@file prompt_plus.py
"""
import threading
import traceback
import copy
import math
import sys
import os
import logging
from queue import Queue
from collections.abc import Iterator
import asyncio
from prompt_toolkit2.shortcuts.prompt import confirm
from prompt_toolkit2 import prompt
from prompt_toolkit2 import PromptSession  # 动态对象要用到, 所以不能删除
from prompt_toolkit2 import print_formatted_text as prompt_toolkit_print
try:
    from prompt_toolkit2.eventloop.defaults import use_asyncio_event_loop
except:
    pass
from prompt_toolkit2.patch_stdout import patch_stdout
from prompt_toolkit2.history import InMemoryHistory
from prompt_toolkit2.styles import Style
from prompt_toolkit2.lexers import Lexer
from prompt_toolkit2.completion import Completer, Completion
from prompt_toolkit2.shortcuts import ProgressBar
from prompt_toolkit2.formatted_text import HTML
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.generic import CResult
from HiveNetCore.stream import StringStream
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


__MOUDLE__ = 'prompt_plus'  # 模块名
__DESCRIPT__ = u'增强的交互命令行扩展处理, 基于prompt_toolkit进行封装和扩展'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


"""
命令参数内部存储结构定义
@typedef {cmdpara} 命令参数 - 定义统一的命令参数内部存储结构, 基本类型是dict, 具体定义如下:
    key为命令标识
    value同样为dict(), value的key为参数名, 参数名与参数值的定义如下:
        deal_fun (匹配到命令要执行的函数) : fun 函数定义(function类型)
            函数固定入参为fun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs)
                @param {string} message - prompt提示信息
                @param {string} cmd - 执行的命令key值
                @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
                @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
                @param {kwargs} - 扩展参数, 建议带上以支持未来的扩展
                @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过
                    CResult对象的print_str属性要求框架进行打印处理
                    注: 控制台也支持处理函数返回string、iter这两类对象, 框架将对这两类对象执行打印处理,
                    但这种模式未来将不再支持, 建议通过prompt_obj.prompt_print自行输出, 或通过CResult的print_str属性进行打印
        name_para (para_name=para_value形式的参数) : dict(para_name: para_value_list)
            para_name {string} - 参数名
            para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
        short_para (-para_char para_value 形式的参数) : dict(para_char, para_value_list)
            para_char {char} - 短参数标识字符(单字符, 不带-)
            para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
            注: 该形式可以支持多个字符写在一个'-'后面, 例如: -xvrt
        long_para (-para_name para_value形式的参数) : dict(para_name, para_value_list)
            para_name {string} - 参数名(可以多字符, 不带-)
            para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
        word_para (直接一个词形式的参数) : dict(word_name, '')
            word_name {string} - 直接参数名

"""


class ProgressRate(object):
    """
    支持多层级函数调用的进度取值处理类
    """
    #############################
    # 静态函数
    #############################
    @classmethod
    def show_cmd_process_bar(cls, rate: float, label: str = '', info: str = '', bar_len: int = 50,
                             bar_finish: str = '▋', bar_unfinish: str = ' ', **kwargs):
        """
        命令行打印进度条

        @param {float} rate - 当前进度值(0-100之间)
        @param {str} label='' - 提示标签, 例如'Installing', 'Error', 'Done', 显示在进度条前面
        @param {str} info='' - 提示信息, 显示在进度条结尾
        @param {int} bar_len=50 - 进度条长度
        @param {str} bar_finish='▋' - 进度条完成进度显示字符
        @param {str} bar_unfinish=' ' - 进度条未完成进度显示字符
            注: 合适的搭配包括('▋', ' '), ('*', '>')
        """
        _rate = rate
        _label = '' if label == '' else '%s: ' % label
        _finish_size = math.floor(bar_len * _rate / 100.0)
        _unfinish_size = bar_len - _finish_size

        # 打印进度信息
        print('\r', end='')
        _end = None if _rate >= 100.0 else ''
        print(
            '\033[K',  # 通过打印这个代码清除当前行上一次输出的信息(擦除到输出结尾)
            '%s%3.1f%%' % (_label, _rate),
            '[%s%s]' % (bar_finish * _finish_size, bar_unfinish * _unfinish_size),
            info, end=_end, flush=True
        )

    #############################
    # 成员函数
    #############################

    def __init__(self, rate: float = 0.0, show_process_bar_fun=None) -> None:
        """
        初始化进度取值处理类

        @param {float} rate=0.0 - 进度初始值
        @param {function} show_process_bar_fun=None - 显示进度条的函数, 如果不传默认为 show_cmd_process_bar
            注: 如需自定义函数, 函数定义必须为fun(rate:float, label:str, info:str, ...)
        """
        # 进度显示函数
        self._show_process_bar_fun = show_process_bar_fun
        self._process_bar_lock = threading.RLock()  # 进度条显示的锁对象, 避免多线程并发时显示串行的问题
        if show_process_bar_fun is None:
            show_process_bar_fun = self.show_cmd_process_bar

        # 当前实际进度信息
        self._current = {
            'rate': rate,  # 当前进度值
            'start_rate': rate,  # 限制区间开始值
            'next_rate': 100.0,  # 限制下一个进度的最大值
            'step': 1.0,  # 默认步长
            'scale': 1.0,  # 当前进度信息的比例, 用于将进度换算为实际进度
            'level': 0,  # 所属层级
            'real_start_rate': 0.0,  # 当前层级0.0对应实际进度位置
        }

        # 进入不同层级处理使用的堆栈
        self._stack = list()

    def show_progress_bar(self, label: str = '', info: str = ''):
        """
        输出进度条现实

        @param {str} label='' - 提示标签, 例如'Installing', 'Error', 'Done', 显示在进度条前面
        @param {str} info='' - 提示信息, 显示在进度条结尾
        """
        _rate = self.get_current_rate()
        self._process_bar_lock.acquire()
        try:
            self._show_process_bar_fun(
                _rate, label=label, info=info
            )
        finally:
            self._process_bar_lock.release()

    def get_current_rate(self) -> float:
        """
        获取当前进度

        @returns {float} - 当前进度
        """
        return self._current['rate']

    def into_next_level(self, rate: float = None, next_rate: float = None):
        """
        进入下一层进度处理

        @param {float} rate=None - 设置当前进度
        @param {float} next_rate=None - 设置下一进度限制
        """
        # 设置当前层级的进度
        self._set_rates(rate=rate, next_rate=next_rate)

        # 添加下一层对象
        _level = len(self._stack) + 1

        if _level == 1:
            _last_pg = self._current
        else:
            _last_pg = self._stack[-1]

        _scale = ((_last_pg['next_rate'] - _last_pg['start_rate']) / 100.0) * _last_pg['scale']

        _real_start_rate = _last_pg['real_start_rate'] + _last_pg['start_rate'] * _last_pg['scale']

        self._stack.append({
            'rate': 0,  # 当前进度值
            'start_rate': 0,  # 限制区间开始值
            'next_rate': 100.0,  # 限制下一个进度的最大值
            'step': 1.0,  # 默认步长
            'scale': _scale,  # 当前进度信息的比例, 用于将进度换算为实际进度
            'level': _level,  # 所属层级
            'real_start_rate': _real_start_rate,  # 当前层级0.0对应实际进度位置
        })

    def exit_current_level(self):
        """
        退出当前进度层级
        """
        if len(self._stack) > 0:
            self._stack.pop(-1)
            if len(self._stack) > 0:
                _last_pg = self._stack[-1]
            else:
                _last_pg = self._current

            # 退出认为进度全部完成
            self._set_rates(rate=_last_pg['next_rate'])

    def add_rate_by_step(self, step: float = None):
        """
        进度增加指定步长

        @param {float} step=None - 指定步长
        """
        _pg = self._current
        if len(self._stack) > 0:
            _pg = self._stack[-1]

        _step = step
        if step is None:
            _step = _pg['step']

        self._set_rates(rate=(_pg['rate'] + _step))

    def set_step(self, step: float):
        """
        设置当前步长

        @param {float} step - 要设置的步长
        """
        _pg = self._current
        if len(self._stack) > 0:
            _pg = self._stack[-1]

        _pg['step'] = step

    def get_step(self) -> float:
        """
        获取当前步长

        @returns {float} - 获取到的步长
        """
        _pg = self._current
        if len(self._stack) > 0:
            _pg = self._stack[-1]

        return _pg['step']

    def set_rate(self, rate: float, next_rate: float = None, split_len: int = None):
        """
        设置当前进度
        注: 无需考虑所在层级, 直接按100的维度设置即可

        @param {float} rate - 当前进度值(传入1.0代表1%)
        @param {float} next_rate=None - 下一个进度的最大值, 如果不设置代表仅设置进度, 不改变限制区间
        @param {int} split_len=None - 对进度限制区间按步数设置步长
        """
        return self._set_rates(rate=rate, next_rate=next_rate, split_len=split_len)

    def set_next_rate(self, next_rate: float, split_len: int = None):
        """
        设置下一个进度的最大值

        @param {float} next_rate - 下一个进度的最大值
        @param {int} split_len=None - 对进度限制区间按步数设置步长
        """
        return self._set_rates(rate=None, next_rate=next_rate, split_len=split_len)

    def set_split_len(self, split_len: int):
        """
        设置补偿

        @param {int} split_len - 对进度限制区间按步数设置步长
        """
        return self._set_rates(rate=None, next_rate=None, split_len=split_len)

    #############################
    # 内部函数
    #############################
    def _set_rates(self, rate: float = None, next_rate: float = None, split_len: int = None):
        """
        设置各项进度值

        @param {float} rate=None - 设置当前进度
        @param {float} next_rate=None - 设置下一个进度的最大值
        @param {int} split_len=None - 对进度限制区间按步数设置步长
        """
        # 获取当前层的进度信息
        _pg = self._current
        if len(self._stack) > 0:
            _pg = self._stack[-1]

        # 设置进度
        if rate is not None:
            _rate = min(100.0, max(0.0, rate))
            _pg['rate'] = _rate
            if _pg['start_rate'] > _pg['rate']:
                # 确保进度不会比开始区间小
                _pg['start_rate'] = _pg['rate']

            # 按比例映射到实际进度上
            if _pg['level'] != 0:
                self._current['rate'] = _pg['real_start_rate'] + (_rate * _pg['scale'])
        else:
            _rate = _pg['start_rate']

        # 设置限制区间
        if next_rate is not None:
            _pg['next_rate'] = min(100.0, max(_rate, next_rate))
            _pg['start_rate'] = _rate

        # 设置步长
        if split_len is not None:
            _pg['step'] = (_pg['next_rate'] - _pg['start_rate']) / max(1, split_len)


class MemoryStringStream(object):
    """
    内存中的字符串流定义类
    用于将流内容输出到字符串中
    """

    def __init__(self, encoding=None):
        """
        构造函数
        """
        self._encoding = encoding
        self._buff = ''

    def write(self, out_stream):
        """
        将内容写入流

        @param {string} out_stream - 要输出的流内容
        """
        if self._encoding is None:
            self._buff += out_stream
        else:
            self._buff += str(out_stream, encoding=self._encoding)

    def __str__(self):
        """
        输出内容
        """
        return self._buff


class SimpleCompleter(Completer):
    """
    简单的自动完成提示类
    """

    def __init__(self, words, ignore_case: bool = False, slow_time: float = 0,
            select_mode: bool = False, sentence: bool = False, words_fun_arg=None):
        """
        简单的自动完成提示类

        @param {list|function} words - 要提示的单词列表或产生单词列表的执行函数对象
            如果是函数, 函数定义为 func(当前词, 完整输入, words_fun_arg) -> 提示词列表
        @param {bool} ignore_case=False - 匹配命令是否忽略大小写
        @param {float} slow_time=0 - 延迟提示的时长(秒), 0代表不延迟
        @param {bool} select_mode=False - 是否选择模式, 如果是则不根据输入内容过滤选项
        @param {bool} sentence=False - 是否句子, 如果是则将整个输入视为一个词进行匹配
        @param {Any} words_fun_arg=None - 当words参数为函数时, 传入该函数的额外参数
        """
        # 初始化可变参数
        self.loading = False
        self._words = words
        self._ignore_case = ignore_case
        self._slow_time = slow_time
        self._select_mode = select_mode
        self._sentence = sentence
        self._words_fun_arg = words_fun_arg

    def get_completions(self, document, complete_event):
        """
        重载Completer的提示函数

        @param {prompt_toolkit.document} document - 要处理的文档
        @param {function} complete_event - 事件

        """
        self.loading = True
        if self._sentence:
            # 将完整输入视为一个词
            _word_before_cursor = document.text
        else:
            _word_before_cursor = self._get_word_before_cursor(document=document)

        # 获取词列表
        if callable(self._words):
            _words = self._words(_word_before_cursor, document.text, self._words_fun_arg)
        else:
            _words = self._words

        if self._slow_time > 0:
            RunTool.sleep(self._slow_time)  # Simulate slowness.

        if self._ignore_case:
            _word_before_cursor = _word_before_cursor.lower()

        for _word in _words:
            if self._ignore_case:
                _word = _word.lower()

            if self._select_mode or _word.startswith(_word_before_cursor):
                yield Completion(_word, -len(_word_before_cursor))

        self.loading = False

    #############################
    # 内部函数
    #############################
    def _get_word_before_cursor(self, document):
        """
        获取当前位置的词, 解决document.get_word_before_cursor不支持-=等字符作为一个词判断的问题

        @param {prompt_toolkit.document} document - 要处理的文档

        @returns {string} - 找到当前位置前的词

        """
        _word_before_cursor = document.get_word_before_cursor()
        # 检查当前词的前一个字符是否空格或文本开头, 如果不是, 则需要向前查找
        _x, _y = document.cursor_position_row, document.cursor_position_col - \
            len(_word_before_cursor)
        _line = document.lines[_x]
        while _y > 0 and _line[_y - 1:_y] != ' ':
            _word_before_cursor = _line[_y - 1:_y] + _word_before_cursor
            _y -= 1

        return _word_before_cursor


class PromptPlusCmdParaLexer(Lexer):
    """
    PromptPlus的命令关键字解析器, 继承prompt_toolkit.Lexer类, 实现自身对命令参数的解析和高亮处理
    参考SimpleLexer(Lexer), 实际上需要实现的接口函数为lex_document(self, document)

    """

    #############################
    # 内部变量
    #############################
    _cmd_para = None  # {type:cmdpara}
    _ignore_case = False
    # _cache = MemoryCache(size=10, sorted_order=EnumCacheSortedOrder.HitTimeFirst)

    #############################
    # 内部函数
    #############################

    def _match_cmd_para_str(self, match_str='', cmd='', match_type=''):
        """
        按类型找到指定词对应的命令行参数key值

        @param {string} match_str='' - 要匹配的词(完整的命令或参数)
        @param {string} cmd='' - 指定要搜索的命令(匹配命令参数时候用到, 如果要匹配命令则无需传入)
        @param {string} match_type='' - 匹配类型(cmd|name_para|short_para|long_para)

        @returns {string} - 没有匹配上返回'', 匹配上返回对应的关键字

        """
        _ret_key = ''
        if match_type == 'cmd':
            # 匹配命令
            if self._ignore_case:
                # 忽略大小写
                for _key in self._cmd_para.keys():
                    if _key.upper() == match_str.upper():
                        _ret_key = _key
                        break
            else:
                # 不忽略大小写
                if match_str in self._cmd_para.keys():
                    _ret_key = match_str
        else:
            # 匹配命令参数名
            if not(cmd not in self._cmd_para.keys() or
                   match_type not in self._cmd_para[cmd].keys() or
                   self._cmd_para[cmd][match_type] is None):
                if self._ignore_case:
                    for _key in self._cmd_para[cmd][match_type].keys():
                        if _key.upper() == match_str.upper():
                            _ret_key = _key
                            break
                else:
                    if match_str in self._cmd_para[cmd][match_type].keys():
                        _ret_key = match_str
        # 最终返回匹配结果
        return _ret_key

    def _match_cmd_para_str_start(self, match_str='', cmd='', match_type=''):
        """
        按类型找到指定词对应的命令行参数key值的开头

        @param {string} match_str='' - 要匹配的词(命令或参数的开头)
        @param {string} cmd='' - 指定要搜索的命令(匹配命令参数时候用到, 如果要匹配命令则无需传入)
        @param {string} match_type='' - 匹配类型(cmd|name_para|short_para|long_para)

        @returns {string} - 没有匹配上返回'', 匹配上返回对应的关键字
        """
        _ret_key = ''
        _match_str = match_str
        if match_type == 'cmd':
            # 匹配命令
            for _key in self._cmd_para.keys():
                _match_key = _key
                if self._ignore_case:
                    _match_key = _match_key.upper()
                    _match_str = _match_str.upper()
                if _match_str == _match_key[0: len(_match_str)]:
                    _ret_key = _key
                    break
        else:
            # 匹配参数
            if not(cmd not in self._cmd_para.keys() or
                   match_type not in self._cmd_para[cmd].keys() or
                   self._cmd_para[cmd][match_type] is None):
                for _key in self._cmd_para[cmd][match_type].keys():
                    _match_key = _key
                    if self._ignore_case:
                        _match_key = _match_key.upper()
                        _match_str = _match_str.upper()
                    if _match_str == _match_key[0: len(_match_str)]:
                        _ret_key = _key
                        break
        # 返回结果
        return _ret_key

    def _analyse_cmd_para_stream_dealer(self, deal_char='', position=0, cmd_para_str='',
                                        match_cmd='', current_info=None,
                                        style_list=None, info_list=None):
        """
        使用StringStream逐个字符解析命令行参数的流处理函数(注意不含cmd部分)
        该函数执行流处理结束后, 会生成info_list(关键字列表)和style_list(关键字样式列表), 用于Lexer显示样式

        @param {string} deal_char='' - 当前处理到的字符
        @param {int} position=0 - 当前字符位置
        @param {string} cmd_para_str='' - 要处理的完整参数字符串
        @param {string} match_cmd='' - 要匹配的命令
        @param {list} current_info=None - 当前正在处理的字符所处的词的处理信息,传入的是上一个字符处理后的状态, 处理中会更新:
            [
                引号是否结束(bool), 引号开始位置(int),
                长短参数是否结束(bool),  长短参数开始位置(int),
                连续词是否结束, 连续词开始位置,
                name_para参数是否结束(bool), word_para参数是否结束(bool)
            ]
            注: 如果需标注参数内容是从字符串开始, 可以通过传入current_info设置, 应对多行处理的情况
        @param {list} style_list=None - 字符样式对应列表, 传入的是上一个字符处理后的列表, 处理中会更新:
            [('style_str','char_str'), ('style_str','char_str'), ...]
            注意: 字符处理完后可能会在最后多一个char_str为空的列表项, 完整结束后需判断和删除
        @param {list} info_list=None - 与style_list一一对应, 等级每个标记的具体信息, 传入的是上一个字符处理后的列表,
            处理中会更新, 格式为:[开始位置(int), 结束位置(int), 标记类型(''|cmd|name_para|short_para|long_para|wrong)]

        """
        # 初始化可变入参
        if current_info is None:
            current_info = list()
        if style_list is None:
            style_list = list()
        if info_list is None:
            info_list = list()

        if position == 0:
            # 进行初始化
            # [引号是否结束(bool), 引号开始位置(int),
            # 长短参数是否结束(bool),  长短参数开始位置(int),
            # 连续词是否结束, 连续词开始位置]
            # name_para参数是否结束(bool), word_para参数是否结束(bool)
            if current_info.count == 0:
                current_info.extend([True, -1, True, -1, False, 0, True, True])
            else:
                _is_in_string = current_info[0]
                current_info.clear()
                current_info.extend([_is_in_string, -1, True, -1, False, 0, True, True])

            # [('style_str','char_str'), ('style_str','char_str'), ...], 注意如果对外部变量直接用=赋值, 传不到外面
            style_list.clear()
            style_list.append(('class:', ''))
            # [开始位置(int), 结束位置(int), 标记类型(''\cmd\name_para\short_para\long_para)]
            info_list.clear()
            info_list.append([0, 0, ''])

        # 开始正式的处理
        _last_index = len(style_list) - 1
        _last_style_word = style_list[_last_index][1]
        if not current_info[0]:
            # 还在双引号里面, 将自己纳入上一个处理中
            style_list[_last_index] = (style_list[_last_index][0], _last_style_word + deal_char)
            info_list[_last_index][1] = position + 1
            if deal_char == '"':
                # 是引号结束
                current_info[0] = True
                current_info[1] = -1
            return  # 继续等待下一个处理

        # 不在引号里面, 判断几个特殊字符
        _last_word = cmd_para_str[current_info[5]: position]
        if deal_char == ' ':
            # 引号外遇到空格, 代表上一个字的结束
            current_info[6] = True  # 一定是name_para的结束
            if current_info[6] and _last_word != '' and _last_word[0:1] == '-':
                current_info[2] = True  # 标注长短词结束
                if _last_word == '-':
                    # 只送一个标识符, 只需要修改为错误
                    style_list[_last_index] = ('class:wrong_tip', _last_word)
                    info_list[_last_index][2] = 'wrong'
                elif len(_last_word) > 2 and self._match_cmd_para_str(match_str=_last_word[1:], cmd=match_cmd,
                                                                      match_type='long_para') == '':
                    # 不是短词, 但也匹配不上长词
                    style_list[_last_index] = ('class:wrong_tip', _last_word)
                    info_list[_last_index][2] = 'wrong'
            elif current_info[6] and _last_word != '' and self._match_cmd_para_str(match_str=_last_word, cmd=match_cmd,
                                                                                   match_type='word_para') != '':
                # 非name_para参数情况, 匹配上词模式
                style_list[_last_index] = ('class:word_para', _last_word)
                info_list[_last_index][2] = 'word_para'
            elif not current_info[7] and self._match_cmd_para_str(match_str=_last_word, cmd=match_cmd,
                                                                  match_type='word_para') == '':
                # 原来匹配到word_para但实际上最终不是
                style_list[_last_index] = ('class:', _last_word)
                info_list[_last_index][2] = ''

            current_info[7] = True  # 处理完成后, 肯定不再在word_para参数中

            # 其他情况无需对原来的样式进行调整单纯关闭和初始化下一个词的开始即可
            if style_list[_last_index][1] == '':
                # 本来就没有词, 不用特殊处理, 把空格放到style_list最后的位置即可
                style_list[_last_index] = ('class:', ' ')
                info_list[_last_index][1] = position + 1
            else:
                # 原来已经有词, 新开一个
                style_list.append(('class:', ' '))
                info_list.append([position, position + 1, ''])
            # 初始化下一个词的处理
            style_list.append(('class:', ''))
            info_list.append([position + 1, position + 1, ''])
            current_info.clear()
            current_info.extend([True, -1, True, -1, False, position + 1, True, True])
            return
        elif deal_char == '"' and _last_word[0:1] != '-':
            # 字符串开始, 与平常处理没有分别, 只是要标注是字符串开始
            style_list[_last_index] = (style_list[_last_index][0], _last_style_word + deal_char)
            info_list[_last_index][1] = position + 1
            current_info[0] = False
            current_info[1] = position
            # print('end %s: %s' % (deal_char, str(current_info)))
            return
        elif deal_char == '-' and (position == 0 or cmd_para_str[position - 1:position] == ' '):
            # 短参数匹配, 且是在词的开始位置
            style_list[_last_index] = ('class:short_para', '-')
            info_list[_last_index][1] = position + 1
            current_info[2] = False
            current_info[3] = position
            # 初始化下一个词的处理
            # style_list.append(('class:', ''))
            # info_list.append([position + 1, position + 1, ''])
            # print('end %s: %s' % (deal_char, str(current_info)))
            return
        elif deal_char == '=' and _last_word != '' and (_last_word[0:1] != '-' and current_info[6]):
            # 遇到等号, 则代表前面是name_para
            current_info[6] = False  # 标记后面一个词处于name_para模式
            if self._match_cmd_para_str(match_str=_last_word,
                                        cmd=match_cmd, match_type='name_para') != '':
                # 匹配上
                style_list[_last_index] = ('class:name_para', _last_word)
                info_list[_last_index][2] = 'name_para'
            else:
                # 匹配不上
                style_list[_last_index] = ('class:wrong_tip', _last_word)
                info_list[_last_index][2] = 'wrong'
            # 加上自身样式同步初始化下一个的处理
            style_list.append(('class:', '='))
            info_list.append([position, position + 1, ''])
            # print('end %s: %s' % (deal_char, str(current_info)))
            return
        else:
            # 延续字符的处理, 只需要特殊判断是否短参数的情况
            if not current_info[2]:
                _temp_para_str = cmd_para_str[current_info[3] + 1: position + 1]
                if len(_temp_para_str) == 1 and self._match_cmd_para_str(match_str=_temp_para_str, cmd=match_cmd,
                                                                         match_type='short_para') != '':
                    # 一个字符, 按短参数匹配成功
                    style_list[_last_index] = ('class:short_para', '-' + _temp_para_str)
                    info_list[_last_index][1] = position + 1
                    info_list[_last_index][2] = 'short_para'
                elif self._match_cmd_para_str_start(match_str=_temp_para_str, cmd=match_cmd,
                                                    match_type='long_para') != '':
                    # 匹配到长参数
                    style_list[_last_index] = ('class:long_para', '-' + _temp_para_str)
                    info_list[_last_index][1] = position + 1
                    info_list[_last_index][2] = 'long_para'
                else:
                    # 匹配不上, 错误提示
                    style_list[_last_index] = ('class:wrong_tip', '-' + _temp_para_str)
                    info_list[_last_index][1] = position + 1
                    info_list[_last_index][2] = 'wrong'

                # 初始化下一个词的处理
                # style_list.append(('class:', ''))
                # info_list.append([position + 1, position + 1, ''])
                # print('end %s: %s' % (deal_char, str(current_info)))
                return
            else:
                # 正常字符增加, 延续上一个的情况, 判断是否word_para
                if current_info[6] and self._match_cmd_para_str_start(match_str=_last_style_word + deal_char, cmd=match_cmd,
                                                                      match_type='word_para') != '':
                    style_list[_last_index] = ('class:word_para', _last_style_word + deal_char)
                    info_list[_last_index][2] = 'word_para'
                    current_info[7] = False
                elif not current_info[7]:
                    # 在word_para中但是匹配不上
                    style_list[_last_index] = ('class:', _last_style_word + deal_char)
                    info_list[_last_index][2] = ''
                    current_info[7] = True
                else:
                    style_list[_last_index] = (style_list[_last_index][0],
                                               _last_style_word + deal_char)
                    current_info[7] = True
                info_list[_last_index][1] = position + 1
                # print('end %s: %s' % (deal_char, str(current_info)))
                return

    def _get_line_tokens(self, line='', match_cmd='', start_in_string=False, current_info=None):
        """
        按行进行解析, 返回一行参数的样式清单(调用_analyse_cmd_para_stream_dealer)
        @todo 通过缓存提升速度

        @param {string} line='' - 要处理的行字符串
        @param {string} match_cmd='' - 要匹配的命令
        @param {bool} start_in_string=False - 当前行是否从字符串内部开始(上一行开始的字符串中间)
        @param {list} current_info=None - 当前正在处理的字符所处的词的处理信息

        @returns {list} - 样式清单列表

        """
        # 初始化可变参数
        if current_info is None:
            current_info = list()

        if line == '':
            return []

        # 从缓存获取处理参数, 缓存唯一标识格式为: match_cmd + str(start_in_string) + line
        # TODO(待办人): 发现换了算法后, 即使不用缓存, 响应速度也能接受, 因此暂时不实现缓存机制
        # _cache_key = match_cmd + str(start_in_string) + line
        _cache_data = None

        if _cache_data is None:
            # 从缓存获取不到数据, 将_cache_data设置为从0位置开始, cache的数据格式如下:
            # [current_position, last_current_info, last_style_list, last_info_list]
            if start_in_string:
                _cache_data = [0, [False, 0, True, -1, False, 0, True, True], list(),
                               list()]  # 从字符串开始行
            else:
                _cache_data = [0, [True, 0, True, -1, False, 0, True, True], list(), list()]
        else:
            _cache_data = copy.deepcopy(x=_cache_data)  # 深度复制, 避免影响原缓存信息

        # 执行处理
        _position = _cache_data[0]
        _str_len = len(line)
        while _position < _str_len:
            self._analyse_cmd_para_stream_dealer(
                deal_char=line[_position: _position + 1],
                position=_position,
                cmd_para_str=line,
                match_cmd=match_cmd,
                current_info=_cache_data[1],
                style_list=_cache_data[2],
                info_list=_cache_data[3]
            )
            _position += 1

        # 加入到缓存
        # self._cache.update_cache(key=_cache_key, data=_cache_data)

        # 返回当前行的最后信息
        current_info.clear()
        current_info.extend(copy.deepcopy(_cache_data[1]))

        # 处理返回值
        _para_style = copy.deepcopy(_cache_data[2])
        _style_len = len(_para_style)
        if _style_len > 0 and _para_style[_style_len - 1][1] == '':
            # 最后一个没有具体数据, 删除
            del _para_style[_style_len - 1]
        return _para_style

    def _get_lexer_tokens(self, lines=None):
        """
        解析传入的字符数组(多行)并返回解析后的样式清单列表(支持多行换行的情况)

        @param {list} lines=None - 要解析的字符串数组

        @returns {list} - 样式清单列表, 每行对应lines的一行, 格式为:
            [
                [('style_str','char_str'), ('style_str','char_str'), ...],
                [('style_str','char_str'), ('style_str','char_str'), ...],
                ...
            ]

        """
        # 初始化可变参数
        if lines is None:
            lines = list()

        _style_list = [[('class:', _line)] for _line in lines]  # 每行一个默认的清单

        # 先判断第一行的信息, 截取命令
        _split_index = lines[0].find(' ')
        _cmd = ''
        if _split_index > 0:
            _cmd = lines[0][0:_split_index]
        else:
            _cmd = lines[0]  # 整行都是命令

        _match_cmd = self._match_cmd_para_str(match_str=_cmd, match_type='cmd')

        if _match_cmd == '':
            # 第一行匹配不到命令
            return _style_list

        _cmd_style = ('class:cmd', _cmd)
        _current_info = list()
        _para_style = self._get_line_tokens(
            line=lines[0][len(_cmd):], match_cmd=_match_cmd, start_in_string=False,
            current_info=_current_info
        )
        _para_style.insert(0, _cmd_style)
        _style_list[0] = _para_style

        # 其他行的处理
        _lineno = 1
        while _lineno < len(lines):
            _start_in_string = False
            if _current_info.count != 0:
                _start_in_string = not _current_info[0]
            _current_info = list()
            _para_style = self._get_line_tokens(
                line=lines[_lineno], match_cmd=_match_cmd,
                start_in_string=_start_in_string, current_info=_current_info
            )
            _style_list[_lineno] = _para_style
            _lineno += 1

        # 完成处理
        return _style_list

    #############################
    # 公共函数
    #############################

    def __init__(self, cmd_para=None, ignore_case=False):
        """
        PromptPlusCmdParaLexer的构造函数

        @param {cmdpara} cmd_para=None - 命令参数字典
        @param {bool} ignore_case=False - ignore_case 匹配命令是否忽略大小写

        """
        # 初始化可变参数
        if cmd_para is None:
            cmd_para = dict()

        self._cmd_para = cmd_para
        self._ignore_case = ignore_case

    def lex_document(self, document):
        """
        实现Lexer类的解析文档函数, 按行解析并返回对应的样式, 字符列表

        @param {prompt_toolkit.document} document - 要解析的lex文档

        """
        lines = document.lines

        # 直接进行所有行的解析, 得到各行的解析数组, 但由于每次全部进行检索性能不好, 输入内容多的时候会卡顿
        # 因此要优化算法, 利用缓存历史数据提升处理速度
        _style_list = []
        try:
            _style_list = self._get_lexer_tokens(lines=lines)
        except Exception:
            _style_list = [[('class:', _line)] for _line in lines]  # 每行一个默认的清单
            print(traceback.format_exc())

        def get_line(lineno):
            " Return the tokens for the given line. "
            try:
                return _style_list[lineno]
            except IndexError:
                return []

        return get_line


class PromptPlusCompleter(Completer):
    """
    PromptPlus的自动完成类, 根据输入的状态以及命令行提示可用的命令和参数输入
    该类继承prompt_toolkit.Completer类, 参考DummyCompleter类, 主要对外提供get_completions接口

    """

    #############################
    # 内部变量
    #############################
    _cmd_para = None  # {type:cmdpara}
    _ignore_case = False
    _slow_time = 0
    _cmd_word = None
    _para_word = None

    #############################
    # 私有函数
    #############################

    def _match_cmd_para_str(self, match_str='', cmd='', match_type=''):
        """
        按类型找到指定词对应的命令行参数key值
        @todo 该函数与Lexer中的函数一样, 看是否要整合为1个

        @param {string} match_str='' - 要匹配的词(完整的命令或参数)
        @param {string} cmd='' - 指定要搜索的命令(匹配命令参数时候用到, 如果要匹配命令则无需传入)
        @param {string} match_type='' - 匹配类型(cmd|name_para|short_para|long_para)

        @returns {string} - 没有匹配上返回'', 匹配上返回对应的关键字

        """
        _ret_key = ''
        if match_type == 'cmd':
            # 匹配命令
            if self._ignore_case:
                # 忽略大小写
                for _key in self._cmd_para.keys():
                    if _key.upper() == match_str.upper():
                        _ret_key = _key
                        break
            else:
                # 不忽略大小写
                if match_str in self._cmd_para.keys():
                    _ret_key = match_str
        else:
            # 匹配命令参数名
            if not(cmd not in self._cmd_para.keys() or
                   match_type not in self._cmd_para[cmd].keys() or
                   self._cmd_para[cmd][match_type] is None):
                if self._ignore_case:
                    for _key in self._cmd_para[cmd][match_type].keys():
                        if _key.upper() == match_str.upper():
                            _ret_key = _key
                            break
                else:
                    if match_str in self._cmd_para[cmd][match_type].keys():
                        _ret_key = match_str
        # 最终返回匹配结果
        return _ret_key

    def _check_position_in_string(self, document):
        """
        检查文档当前的位置是否在引号里面

        @param {prompt_toolkit.document} document - 要检查的文档

        @returns {bool} - 文档当前位置是否在字符串中

        """
        _lineno = document.cursor_position_row
        _lineindex = document.cursor_position_col
        _current_lineno = 0
        _is_in_string = False
        _is_in_para = False  # 是否在长短参数里面(长短参数里的双引号当普通字符处理)
        _is_word_begin = True  # 指示当前位置是否单词的开始
        while _current_lineno <= _lineno:
            _line = document.lines[_current_lineno]
            _current_index = 0
            while ((_current_lineno == _lineno and _current_index < _lineindex) or
                   (_current_lineno < _lineno and _current_index < len(_line))):
                _char = _line[_current_index: _current_index + 1]
                if _is_in_string:
                    if _char == '"':
                        _is_in_string = False
                elif _is_in_para:
                    if _char == ' ':
                        _is_in_para = False
                        _is_word_begin = True
                else:
                    if _char == ' ':
                        # 遇到空格, 代表下一个是词的开始
                        _is_word_begin = True
                    elif _char == '"':
                        # 遇到双引号, 是引号的开始
                        _is_in_string = True
                        _is_word_begin = False
                    elif _is_word_begin and _char == '-':
                        # 在词的开始遇到-, 代表是参数的开始
                        _is_in_para = True
                        _is_word_begin = False
                    else:
                        _is_word_begin = False
                _current_index += 1
            _current_lineno += 1

        return _is_in_string

    def _get_complete_words(self, document):
        """
        获取当前词的自动填充列表

        @param {prompt_toolkit.document} document - 要获取的文档

        @returns {(list, bool)} - 获取到的填充词列表和是否在双引号中的标记

        """
        _cmd = ''
        _current_word = document.get_word_before_cursor()
        if document.cursor_position_row == 0 and document.cursor_position_col == len(_current_word):
            return self._cmd_word, False

        # 非开头的输入, 先判断是否能找到命令参数
        _split_index = document.lines[0].find(' ')
        if _split_index > 0:
            _cmd = self._match_cmd_para_str(
                match_str=document.lines[0][0:_split_index], match_type='cmd')
        if _cmd == '':
            # 匹配不到命令行参数, 返回空词
            return [], False

        # 判断是否在双引号中
        if self._check_position_in_string(document=document):
            # 在引号中, 不进行自动提示
            return [], True

        # 其他情况, 全量匹配即可
        return self._para_word[_cmd], False

    def _get_word_before_cursor(self, document):
        """
        获取当前位置的词, 解决document.get_word_before_cursor不支持-=等字符作为一个词判断的问题

        @param {prompt_toolkit.document} document - 要处理的文档

        @returns {string} - 找到当前位置前的词

        """
        _word_before_cursor = document.get_word_before_cursor()
        # 检查当前词的前一个字符是否空格或文本开头, 如果不是, 则需要向前查找
        _x, _y = document.cursor_position_row, document.cursor_position_col - \
            len(_word_before_cursor)
        _line = document.lines[_x]
        while _y > 0 and _line[_y - 1:_y] != ' ':
            _word_before_cursor = _line[_y - 1:_y] + _word_before_cursor
            _y -= 1

        return _word_before_cursor

    def _get_path_complete_words(self, word_before_cursor: str) -> tuple:
        """
        获取路径提示词列表

        @param {str} word_before_cursor - 光标前的词

        @returns {(list, str)} - 返回提示词列表, 以及在游标前的词数组
        """
        _current_word = word_before_cursor
        if _current_word == '':
            return [], ''

        if _current_word[-1] in ('/', '\\'):
            # 是以路径标识结尾
            if not os.path.exists(_current_word):
                return [], ''
            else:
                # 路径存在
                return os.listdir(_current_word), ''
        else:
            # 非路径标识结尾, 怀疑是部分文件
            _path, _filename = os.path.split(_current_word)
            if not os.path.exists(_path):
                return [], ''

            # 尝试找匹配的子目录或子文件
            _file_names = os.listdir(_path)
            _words = []
            for _fn in _file_names:
                if _fn.startswith(_filename):
                    _words.append(_fn)

            return _words, _filename

    #############################
    # 公共函数
    #############################

    def __init__(self, cmd_para=None, ignore_case=False, slow_time=0, enable_path_suggest: bool = True):
        """
        PromptPlusCompleter的构造函数, 传入命令行参数

        @param {cmdpara} cmd_para=None - 命令参数字典
        @param {bool} ignore_case=False - 匹配命令是否忽略大小写
        @param {int} slow_time=0 - 延迟提示的时长(秒), 0代表不延迟
        @param {bool} enable_path_suggest=True - 是否启动路径选择建议

        """
        # 初始化可变参数
        if cmd_para is None:
            cmd_para = dict()

        self.loading = False
        self._cmd_para = cmd_para
        self._ignore_case = ignore_case
        self._slow_time = slow_time
        self._enable_path_suggest = enable_path_suggest

        # 应在__init__中初始化, 否则会出现两个实例对象引用地址一样的问题
        self._cmd_word = list()
        self._para_word = dict()
        # 初始化词组, 设置self._cmd_word和self._para_word, 用于自动完成快速查找词
        for _cmd in cmd_para.keys():
            self._cmd_word.append(_cmd)
            self._para_word[_cmd] = list()
            # key - value形式的参数
            if cmd_para[_cmd]['name_para'] is not None:
                for _name_para_key in cmd_para[_cmd]['name_para'].keys():
                    self._para_word[_cmd].append(_name_para_key + '=')
                    if cmd_para[_cmd]['name_para'][_name_para_key] is not None:
                        for _name_para_value in cmd_para[_cmd]['name_para'][_name_para_key]:
                            self._para_word[_cmd].append(_name_para_key + '=' + _name_para_value)
            # 长短名
            if cmd_para[_cmd]['long_para'] is not None:
                for _long_para_key in cmd_para[_cmd]['long_para'].keys():
                    self._para_word[_cmd].append('-' + _long_para_key)
                    if cmd_para[_cmd]['long_para'][_long_para_key] is not None:
                        for _long_para_value in cmd_para[_cmd]['long_para'][_long_para_key]:
                            self._para_word[_cmd].append(
                                '-' + _long_para_key + ' ' + _long_para_value)
            if cmd_para[_cmd]['short_para'] is not None:
                for _short_para_key in cmd_para[_cmd]['short_para'].keys():
                    self._para_word[_cmd].append('-' + _short_para_key)
                    if cmd_para[_cmd]['short_para'][_short_para_key] is not None:
                        for _short_para_value in cmd_para[_cmd]['short_para'][_short_para_key]:
                            self._para_word[_cmd].append(
                                '-' + _short_para_key + ' ' + _short_para_value)
            # 词模式
            if cmd_para[_cmd]['word_para'] is not None:
                for _word in cmd_para[_cmd]['word_para'].keys():
                    self._para_word[_cmd].append(_word)

    def get_completions(self, document, complete_event):
        """
        重载Completer的提示函数

        @param {prompt_toolkit.document} document - 要处理的文档
        @param {function} complete_event - 事件

        """
        self.loading = True
        word_before_cursor = self._get_word_before_cursor(document=document)

        _word_list, _in_string = self._get_complete_words(document=document)

        if self._slow_time > 0:
            RunTool.sleep(self._slow_time)  # Simulate slowness.

        if _in_string or len(_word_list) > 0:
            # 命令提示处理方式
            if self._ignore_case:
                word_before_cursor = word_before_cursor.lower()

            for word in _word_list:
                if self._ignore_case:
                    word = word.lower()

                if word.startswith(word_before_cursor):
                    yield Completion(word, -len(word_before_cursor))
        else:
            # 尝试获取路径和文件提示
            _word_list, _path_word_before_cursor = self._get_path_complete_words(word_before_cursor)
            for word in _word_list:
                yield Completion(word, -len(_path_word_before_cursor))

        self.loading = False


class PromptPlus(object):
    """
    命令行扩展处理类,利用python-prompt-toolkit实现人机交互处理, 再补充封装命令处理部分登记注册的功能, 固定的操作:
    Ctrl + C : abort,取消本次输入
    Ctrl + D : exit,关闭命令行

    """

    #############################
    # 静态方法, 无需实例化对象即可使用的方法
    #############################
    @staticmethod
    def get_cmd_para_list(cmd_para_str, str_char='\'', tran_char='\\', with_name_para=True):
        """
        根据字符串获取命令参数字典

        @param {string} cmd_para_str - 命令行参数字符串
        @param {string} str_char='\'' - 字符串标识符
        @param {string} tran_char='\\' - 字符串里的转义字符
        @param {bool} with_name_para=True - 是否同时支持name_para的格式

        @return {list} - 返回参数清单, 格式为: [ ['参数标识': '参数值'], ... ]
            注: 参数标识为对应的name_para、short_para、long_para, 如果是单独的词, 标识为空

        @example
            _cmd_para_str = "abc k1=v1 -a 10 20 -abc 30 -c   'abcd hh=name'"
            _list = get_cmd_para_dict(_cmd_para_str)
            _list 为:
            [
                ['', 'abc'],
                ['k1=', 'v1'],
                ['-a', '10'],
                ['', '20'],
                ['-abc', '30'],
                ['-c', "'abcd hh=name'"]
            ]
        """
        # 临时变量
        _word = ''  # 当前词的缓存
        _para_tag = ''  # 当前匹配的参数标识, 为name_para、short_para、long_para的缓存
        _last_char = ''  # 上一个字符的缓存
        _is_in_str = False  # 标识是否正在字符串中

        # 进行处理
        _list = list()
        _cmd_para_str = cmd_para_str + ' '  # 结尾增加一个空格, 保证在循环内完成处理
        for _char in _cmd_para_str:
            # 逐个字符串遍历进行处理
            if _is_in_str:
                # 正在字符串中
                if _char == tran_char and _last_char == tran_char:
                    # 如果当前字符为转义符, 且上一字符也为转义符, 则抵消当前转义符
                    _last_char = ''

                if _char == str_char and _last_char != tran_char:
                    # 遇到字符串结束标识, 结束字符串的获取
                    _is_in_str = False
                else:
                    # 还在字符串内, 词继续增加
                    _word += _char
                    _last_char = _char
                    continue
            elif _char == str_char:
                # 不在字符串内遇到字符标签, 进入字符串处理
                _is_in_str = True

            if _char == ' ':
                # 遇到空格的情况要考虑分词
                if _word != '':
                    if _para_tag == '':
                        if _word[0: 1] == '-':
                            _para_tag = _word
                        else:
                            # 为独立的参数
                            _list.append(['', _word])
                    else:
                        # 有标签, 如果标签和后面的word都是-开头, 要分开处理
                        if _para_tag[0: 1] == '-' and _word[0: 1] == '-':
                            _list.append([_para_tag, ''])  # 把标签加到清单中
                            # 下一个词要变成标签
                            _para_tag = _word
                        else:
                            _list.append([_para_tag, _word])
                            _para_tag = ''
                    # 清空词并重新开始
                    _word = ''
                    _last_char = ''
                    continue
                else:
                    # 词为空且遇到空格
                    if _para_tag == '' or _para_tag[0: 1] == '-':
                        # 没有标签, 或则为-标签(需要贪婪地获取下一个参数), 直接往下走即可
                        _last_char = ''
                        continue
                    else:
                        # 有标签, 认为值为空
                        _list.append([_para_tag, ''])
                        _para_tag = ''
                        _last_char = ''
                        continue
            elif with_name_para and _char == '=' and _para_tag == '' and _word != '':
                # 第一次遇到=产生_name_para
                _para_tag = _word + _char
                _word = ''  # 已经将词分给标签
                _last_char = _char
                continue
            else:
                # 非特殊情况
                _word += _char
                _last_char = _char
                continue

        # 处理字符串没有结束的清空
        if _is_in_str:
            # 还在字符串里
            if _para_tag != '':
                _list.append([_para_tag, _word])
            else:
                _list.append(['', _word])
        elif _para_tag != '':
            # 有标签, 但结束了, 说明最后一个是标签
            _list.append([_para_tag, ''])

        # 返回结果
        return _list

    @staticmethod
    def simple_prompt(message='', deal_fun=None, **kwargs):
        """
        简单命令行输入处理函数,获取键盘输入, 并返回输入处理结果

        @param {string} message='' - 获取输入的提示信息
        @param {function} deal_fun=None - 获取到输入后执行的处理函数fun(prompt_text=''), 函数要求满足:
            输入参数为prompt_text, 返回值类型按实际需要返回即可
        @param {kwargs} kwargs python-prompt-toolki的prompt参数:
            详细参数见python-prompt-toolki的官方文档, 常用参数见类注释中的《python-prompt-toolki的prompt参数说明》

        @returns {string|object} - 如果deal_fun为None, 直接返回所获取到的输入值;
            如果deal_fun不为None, 则返回deal_fun的执行返回值

        @throws {exception} - 可能会返回deal_fun执行中出现的各种异常

        """
        _prompt_text = prompt(message, **kwargs)
        if deal_fun is not None:
            return deal_fun(_prompt_text)
        else:
            return _prompt_text

    @staticmethod
    def confirm(message: str = 'Confirm?', suffix: str = " (y/n) ") -> bool:
        """
        提示客户输入确认

        @param {str} message='Confirm?' - 获取输入的提示信息
        @param {str} suffix=" (y/n) " - 提示后缀

        @returns {bool} - 确认结果
        """
        return confirm(message=message, suffix=suffix)

    @staticmethod
    def format_html_text(text):
        """
        将html字符串格式化为打印对象

        @param {string} text - 要格式化的html对象, 例如:
            '<u>This is underlined</u>'
            '<ansired>This is red</ansired>'
            '<aaa fg="ansiwhite" bg="ansigreen">White on green</aaa>'

        @return {prompt_toolkit.formatted_text} - 格式化后的打印字符串
        """
        return HTML(text)

    @staticmethod
    def print_formatted_text(*args, **kwargs):
        """
        打印格式化后的文本(带颜色、字体等格式)
        注: 可以兼容print方法

        @param {*args} - 要打印的内容值, 可以传多个值进行打印
        @param {*kwargs} - 打印参数, 包括:
            {string} sep=' ' - 多个内容的分隔符
            {string} end='\n' - 结尾字符
            {stream} file=None - 输出文件流
            {bool} flush=False - 是否强制刷入缓存
            {dict} style=None - 格式字典, 例如以下字典指定两个格式类:
                {
                    'aaa': '#ff0066',
                    'bbb': '#44ff00 italic',
                }
        """
        # 处理style参数
        if 'style' in kwargs.keys() and kwargs['style'] is not None:
            kwargs['style'] = Style.from_dict(kwargs['style'])

        # 格式化打印
        prompt_toolkit_print(*args, **kwargs)

    @staticmethod
    def get_process_bar(**kwargs):
        """
        创建进度条对象

        @param {kwargs} - 进度条扩展参数, 参考prompt_toolkit.shortcuts.ProgressBar的初始化参数, 部分参数说明如下:
            title {string|function|formated text} : 进度条标题, 可以为字符串、执行函数、HTML格式对象(可使用format_html_text生成)

        @return {prompt_toolkit.shortcuts.ProgressBar} - 返回的进度条对象

        @example
        # 每隔0.01秒进度条加1
        with PromptPlus.get_process_bar() as pb:
            for i in pb(range(800)):
                RunTool.sleep(.01)

        # 传入一个自定义的iter对象
        def some_iterable():
            yield ...

        with PromptPlus.get_process_bar(title=title) as pb:
            for i in pb(some_iterable, total=1000, label=label):
                RunTool.sleep(.01)

        注: ProgressBar的__call__方法(pb)参数如下:
            data=None, label='', remove_when_done=False, total=None
            data {iter} - 可自定义iter函数, 或则使用range生成一个区间的数字
            label {string|formated text} - 进度条的标题文字, 可以为字符串或HTML格式对象
            remove_when_done {bool} - 如果为 `True`, 则再完成时隐藏该进度条
            total {int} - 如果data不支持len函数, 则通过该参数定义最大值

        """
        return ProgressBar(**kwargs)

    @staticmethod
    @StringStream.stream_decorator(is_sync=True)
    def _analyse_para_stream_dealer(deal_obj=None, position=0, str_obj='', para_list=None):
        """
        逐个字符检索参数的流函数定义
        算法描述:
        1、para_list既作为结果对象, 也作为堆栈对象进行处理, 每一行的格式如下
            [参数名, 参数值, 关联符('='或' '), 开始位置(int), 结束位置(int), 引号是否结束(bool), 处理是否结束(bool)]
        2、逐个字符进行解析, 如果判断到para_list最后一个信息未完成, 则当前字符是延续上一个处理
        3、优先匹配'-'开头的参数名, 如果该参数名后紧接空格和非'-'开头的词, 则认为这个词是对应的参数值
        4、对于非'-'开头且不认为是'-'参数的参数值的对象, 如果对象中间有'=', 则拆分为参数名和参数值两部分, 否则认为
            直接就是独立的参数值
        5、对于有双引号的情况, 检索到双引号结束, 且下一个字符不是空格的情况, 则认为下一个字符是一起的

        @decorators StringStream - 定义为字符流处理函数

        @param {object} deal_obj=None - 当前处理的字符对象
        @param {int} position=0 - 当前处理位置
        @param {string} str_obj='' - 完整的字符对象
        @param {list} para_list=None - 处理结果缓存列表

        """
        # 初始化可变参数
        if para_list is None:
            para_list = list()

        _last_index = len(para_list) - 1
        if _last_index == -1 or para_list[_last_index][6]:
            # 上一个参数已经处理结束, 开辟新的参数
            if deal_obj == ' ':
                # 遇到空格不处理, 直接返回
                return
            elif deal_obj == '-':
                # 长参数模式, 写入堆栈
                para_list.append([deal_obj, '', '', position, -1, True, False])
                return
            else:
                # 先认为是纯参数值
                _info = ['', deal_obj, '', position, -1, True, False]
                if deal_obj == '"':
                    # 引号的开始, 标记未结束
                    _info[5] = False
                para_list.append(_info)
                return
        else:
            # 延续上一个参数的处理
            if not para_list[_last_index][5]:
                # 还属于引号的处理中
                para_list[_last_index][1] = para_list[_last_index][1] + deal_obj  # 参数值更新
                if deal_obj == '"':
                    # 引号结束
                    para_list[_last_index][5] = True
                return
            elif deal_obj == ' ':
                # 遇到空格且不在引号内, 是参数名或参数值的结束
                if para_list[_last_index][1] == '':
                    # 是参数名的结束, 需要判断再下一个字符是否'-'
                    if position + 1 < len(str_obj) and str_obj[position + 1: position + 2] != '-':
                        # 后面不是新的参数, 并且也没有到结尾, 属于参数值, 更新参数关联字符即可
                        para_list[_last_index][2] = ' '
                    else:
                        # 已经到结尾或新参数, 当前结束
                        para_list[_last_index][4] = position
                        para_list[_last_index][6] = True
                else:
                    # 是参数值的结束
                    para_list[_last_index][4] = position
                    para_list[_last_index][6] = True
                    # 需要判断是否=号模式的参数
                    if para_list[_last_index][0] == '' and para_list[_last_index][1][0:1] != '"':
                        _index = para_list[_last_index][1].find('=')
                        if _index > 0:
                            para_list[_last_index][0] = para_list[_last_index][1][0:_index]
                            para_list[_last_index][1] = para_list[_last_index][1][_index + 1:]
                            para_list[_last_index][2] = '='

            else:
                # 非空格, 如果关联字符不为空就是参数值, 如果关联字符为空就是参数名
                if para_list[_last_index][2] == '' and para_list[_last_index][1] == '':
                    para_list[_last_index][0] = para_list[_last_index][0] + deal_obj
                else:
                    para_list[_last_index][1] = para_list[_last_index][1] + deal_obj
                # 判断是否引号
                if (deal_obj == '"' and
                        (para_list[_last_index][0][0:1] != '-' or para_list[_last_index][2] != '')):
                    para_list[_last_index][5] = False
                return

    @classmethod
    def analyse_cmd_para(cls, cmd_para_str='', is_start_in_string=False):
        """
        解析命令的参数(通过流方式调用_analyse_para_stream_dealer)

        @decorators classmethod - 定义类成员函数, 无需实例化可调用类内部函数

        @param {string} cmd_para_str='' - 要解析的参数字符串
        @param {bool} is_start_in_string=False - 是否在字符串中间启动, 在多行分开解析时使用

        @returns {list} - 解析结果, 格式如下:
            [参数名, 参数值, 关联符('='或' '), 开始位置(int), 结束位置(int), 引号是否结束(bool), 处理是否结束(bool)]

        """
        _para_list = list()
        if is_start_in_string:
            _para_list.append(['', '', '', 0, -1, False, False])
        cls._analyse_para_stream_dealer(deal_obj=None, position=0,
                                        str_obj=cmd_para_str, para_list=_para_list)
        _len = len(_para_list)
        if _len > 0 and not _para_list[_len - 1][6]:
            # 没有结束, 修正数据
            _para_list[_len - 1][6] = True
            _para_list[_len - 1][4] = _len
            # 需要判断是否=号模式的参数
            if _para_list[_len - 1][0] == '' and _para_list[_len - 1][1][0:1] != '"':
                _index = _para_list[_len - 1][1].find('=')
                if _index > 0:
                    _para_list[_len - 1][0] = _para_list[_len - 1][1][0:_index]
                    _para_list[_len - 1][1] = _para_list[_len - 1][1][_index + 1:]
                    _para_list[_len - 1][2] = '='
        return _para_list

    #############################
    # 实例化的命令行处理 - 内部变量
    #############################
    _prompt_instance = None  # 命令输入处理对象(prompt_toolkit.shortcuts.Prompt类)
    _message = 'CMD>'  # 命令行提示符内容
    # 默认输入参数值, 定义了一些必须有默认取值的参数, 用于创建_prompt_init_para并合并实际的调用参数
    _prompt_default_para = None
    _prompt_init_para = None  # 用于初始化输入类的参数字典, key为参数名(string), value为参数值
    # Prompt类初始化支持的参数名清单, 内部使用
    _prompt_para_name_list = None
    # 命令参数的默认设置值, 用于合并至外部参数对象, 避免传入参数有误导致其他问题
    _cmd_para_default = None
    _loop = None  # 异步模式需要的事件循环处理对象
    _async_cmd_queue = None  # 异步模式的命令执行队列
    # 关键字配色方案, 每个配色方案格式为'#000088 bg:#aaaaff underline'
    _default_color_set = None

    #############################
    # 实例化的命令行处理 - 内部函数
    #############################

    def _init_prompt_instance(self):
        """
        根据类的当前参数重新初始化prompt实例对象

        @throws {ValueError} - 当传入的参数值不对的时候抛出该异常

        """
        # 根据传入参数设置一些特殊值, 简化外部处理
        # cmd_para
        if 'cmd_para' in self._prompt_init_para.keys():
            for _key in self._prompt_init_para['cmd_para'].keys():
                _temp_para = copy.deepcopy(self._cmd_para_default)
                _temp_para.update(self._prompt_init_para['cmd_para'][_key])
                self._prompt_init_para['cmd_para'][_key] = _temp_para

        # History
        if 'enable_history_search' in self._prompt_init_para.keys() \
            and self._prompt_init_para['enable_history_search'] \
            and ('history' not in self._prompt_init_para.keys() or
                 self._prompt_init_para['history'] is None):
            # 要启动历史检索功能, 但未指定对象
            self._prompt_init_para['history'] = InMemoryHistory()

        # 颜色处理
        if self._prompt_init_para['enable_color_set']:
            _color_set = self._default_color_set.copy()
            if self._prompt_init_para['color_set'] is not None:
                _color_set.update(self._prompt_init_para['color_set'])
            # 生成style
            _style = Style.from_dict(_color_set)
            self._prompt_init_para['style'] = _style
            _lexer = PromptPlusCmdParaLexer(cmd_para=self._prompt_init_para['cmd_para'],
                                            ignore_case=self._prompt_init_para['ignore_case'])
            self._prompt_init_para['lexer'] = _lexer

        # 自动完成处理
        if self._prompt_init_para['enable_cmd_auto_complete']:
            _completer = PromptPlusCompleter(
                cmd_para=self._prompt_init_para['cmd_para'],
                ignore_case=self._prompt_init_para['ignore_case'],
                slow_time=self._prompt_init_para['cmd_auto_complete_slow_time'],
                enable_path_suggest=self._prompt_init_para['enable_cmd_path_auto_complete']
            )
            self._prompt_init_para['completer'] = _completer
            self._prompt_init_para['complete_in_thread'] = True

        # 实例化输入类
        if self._prompt_instance is not None:
            del self._prompt_instance  # 先清除原来的对象
        # prompt-toolkit似乎取消了default参数的支持, default=self._default'
        _init_str = ('self._prompt_instance = PromptSession('
                     'message=self._get_color_message(self._message)')
        for _para_name in self._prompt_init_para.keys():
            if _para_name in self._prompt_para_name_list:
                _init_str = '%s, %s=self._prompt_init_para[\'%s\']' % (
                    _init_str, _para_name, _para_name)
        _init_str = '%s)' % _init_str
        # 动态执行初始化处理
        exec(_init_str)

    def _get_color_message(self, message):
        """
        根据配色方案返回指定消息的对应值

        @param {string} message - 要处理的消息

        @returns {string} - 返回格式化后的消息

        """
        _message = message
        if self._prompt_init_para['enable_color_set']:
            _message = (lambda: ('class:prompt', message))
        return _message

    def _match_cmd_para(self, cmd=''):
        """
        根据命令字符串匹配命令参数定义, 返回匹配上的命令key(匹配不到返回'')

        @param {string} cmd='' - 要匹配的命令字符串

        @returns {string} - 命令字符串所在的位置

        """
        ret_key = ''
        if self._prompt_init_para['ignore_case']:
            # 忽略大小写
            for _key in self._prompt_init_para['cmd_para'].keys():
                if cmd.upper() == _key.upper():
                    ret_key = _key
                    break
        else:
            # 不忽略大小写
            if cmd in self._prompt_init_para['cmd_para'].keys():
                ret_key = cmd
        return ret_key

    def _deal_run_result(self, run_result):
        """
        处理执行结果(打印和返回最终结果)

        @param {CResult|iter|string}} run_result - 执行返回结果
        """
        _real_result = None
        if type(run_result) == CResult:
            # 标准返回结果
            _real_result = run_result
            if hasattr(run_result, 'print_str') and run_result.print_str != '':
                self.prompt_print(run_result.print_str)
        elif isinstance(run_result, Iterator):
            # 是迭代器, 遍历处理, 返回结果以最后一个为准
            for _result in run_result:
                if type(_result) == CResult:
                    _real_result = _result
                    if hasattr(_result, 'print_str') and _result.print_str != '':
                        self.prompt_print(_result.print_str)
                else:
                    # 当作字符串处理
                    _real_result = CResult(code='00000')
                    if len(str(_result)) > 0:
                        self.prompt_print(_result)
        else:
            # 都当字符串处理
            _real_result = CResult(code='00000')
            if len(str(run_result)) > 0:
                self.prompt_print(run_result)

        # 返回最终结果
        return _real_result

    def _call_on_abort(self, message=''):
        """
        用户取消输入时执行函数

        @param {string} message='' - 传入的提示信息

        @returns {CResult} - 返回执行函数的返回结果
        """
        if ('on_abort' in self._prompt_init_para.keys() and
                self._prompt_init_para['on_abort'] is not None):
            try:
                try:
                    return self._prompt_init_para['on_abort'](message, cmd='{{on_abort}}', prompt_obj=self)
                except TypeError as error:
                    if len(error.args) > 0 and error.args[0].index('unexpected keyword argument') > 0:
                        # 兼容老模式
                        return self._prompt_init_para['on_abort'](message)
                    else:
                        raise error
            except Exception:
                _print_str = 'call on_abort exception: %s' % traceback.format_exc()
                self.prompt_print(_print_str)
                return CResult(code='29999')
        else:
            # 没有处理, 返回用户取消的错误码
            return CResult(code='10100', msg=u'get abort single(KeyboardInterrupt)')

    def _call_on_exit(self, message=''):
        """
        用户退出处理时执行函数

        @param {string} message='' - 传入的提示信息

        @returns {CResult} - 返回执行函数的返回结果

        """
        if ('on_exit' in self._prompt_init_para.keys() and
                self._prompt_init_para['on_exit'] is not None):
            try:
                try:
                    return self._prompt_init_para['on_exit'](message, cmd='{{on_exit}}', prompt_obj=self)
                except TypeError as error:
                    if len(error.args) > 0 and error.args[0].index('unexpected keyword argument') > 0:
                        # 兼容老模式
                        return self._prompt_init_para['on_exit'](message)
                    else:
                        raise error
            except Exception:
                _print_str = 'call on_exit exception: %s' % traceback.format_exc()
                self.prompt_print(_print_str)
                return CResult(code='29999')
        else:
            # 没有处理, 返回用户退出的错误码
            return CResult(code='10101', msg=u'get exit single(EOFError)')

    def _call_on_cmd(self, message='', cmd_str='', shell_cmd: bool = False):
        """
        执行命令处理

        @param {string} message='' - 输入提示信息
        @param {string} cmd_str='' - 要执行的命令字符串(含参数)
        @param {bool} shell_cmd=False - 是否命令行直接执行模式

        @returns {string} - 返回执行函数的返回结果

        """
        _cmd = cmd_str
        _cmd_para_str = ''
        _print_str = ''
        if len(_cmd) == 0:
            return ''  # 空字符, 不处理
        _first_space_index = _cmd.find(' ')
        if _first_space_index > 0:
            _cmd_para_str = _cmd[_first_space_index + 1:]
            _cmd = _cmd[0: _first_space_index]
        elif _first_space_index == 0:
            _cmd = ''
            _cmd_para_str = cmd_str

        # 查找是否有定义处理函数
        _match_cmd = self._match_cmd_para(cmd=_cmd)
        try:
            if _match_cmd == '':
                # 没有匹配上命令
                if self._prompt_init_para['default_dealfun'] is not None:
                    try:
                        return self._prompt_init_para['default_dealfun'](
                            message=message, cmd=_cmd, cmd_para=_cmd_para_str,
                            prompt_obj=self, shell_cmd=shell_cmd
                        )
                    except TypeError as error:
                        if len(error.args) > 0 and error.args[0].index('unexpected keyword argument') > 0:
                            # 兼容老模式
                            return self._prompt_init_para['default_dealfun'](
                                message=message, cmd=_cmd, cmd_para=_cmd_para_str
                            )
                        else:
                            raise error
            else:
                # 匹配到命令
                if self._prompt_init_para['cmd_para'][_match_cmd]['deal_fun'] is not None:
                    try:
                        return self._prompt_init_para['cmd_para'][_match_cmd]['deal_fun'](
                            message=message, cmd=_match_cmd, cmd_para=_cmd_para_str,
                            prompt_obj=self, shell_cmd=shell_cmd
                        )
                    except TypeError as error:
                        if len(error.args) > 0 and error.args[0].index('unexpected keyword argument') > 0:
                            # 兼容老模式
                            return self._prompt_init_para['cmd_para'][_match_cmd]['deal_fun'](
                                message=message, cmd=_match_cmd, cmd_para=_cmd_para_str,
                            )
                        else:
                            raise error
        except KeyboardInterrupt:
            _print_str = '_call_on_cmd (cmd[%s] para[%s]) get KeyboardInterrupt: %s' % (
                _cmd, _cmd_para_str, traceback.format_exc()
            )
            self.prompt_print(_print_str)
            return CResult(code='10100')
        except Exception:
            _print_str = '_call_on_cmd (cmd[%s] para[%s]) exception: %s' % (
                _cmd, _cmd_para_str, traceback.format_exc()
            )
            self.prompt_print(_print_str)
            return CResult(code='29999')

    def _async_call_on_cmd(self, message='', cmd_str='', is_print_async_execute_info=True):
        """
        异步模式执行匹配命令, 直接调用_call_on_cmd, 只是标识为异步模式处理

        @param {string} message='' - 输入提示信息
        @param {string} cmd_str='' - 匹配到的命令
        @param {bool} is_print_async_execute_info=True - 异步执行时是否打印执行信息

        """
        if is_print_async_execute_info:
            _print_str = 'begin execute (message[%s]): cmd[%s]' % (message, cmd_str)
            self.prompt_print(_print_str)

        _run_result = self._call_on_cmd(message=message, cmd_str=cmd_str)
        self._deal_run_result(_run_result)

        if is_print_async_execute_info:
            _print_str = 'done execute (message[%s]): cmd[%s]' % (message, cmd_str)
            self.prompt_print(_print_str)

    async def _async_cmd_service(self):
        """
        异步模式的命令行循环获取命令线程服务, 标识为异步模式
        获取到一个命令后, 将命令放入队列, 然后马上处理下一个命令的接收

        """
        while True:
            _run_result = CResult(code='00000')
            _cmd_str = ''
            _message = self._message
            try:
                _cmd_str = await self._prompt_instance.prompt(message=_message, default=self._default, async_=True)
            except KeyboardInterrupt:
                # 用户取消输入
                # 执行on_abort函数
                _run_result = self._call_on_abort(message=_message)
            except EOFError:
                # 用户退出处理
                # 执行on_exit函数
                _run_result = self._call_on_exit(message=_message)

            _real_result = self._deal_run_result(_run_result)

            if _real_result.code == '10101':
                # 退出获取命令处理
                return

            if len(_cmd_str) > 0:
                # 处理执行函数
                self._async_cmd_queue.put((_message, _cmd_str))

            # 间隔一会, 继续下一个处理
            await asyncio.sleep(0.1)

    async def _async_deal_cmd_from_queue(self, is_print_async_execute_info=True):
        """
        异步模式从队列中获取命令行并启动后台线程执行处理,  标识为异步模式

        @param {bool} is_print_async_execute_info - 异步执行时是否打印执行信息

        """
        while True:
            _cmd = tuple()
            try:
                _cmd = self._async_cmd_queue.get(block=False)
            except Exception:
                await asyncio.sleep(1)
                continue
            if len(_cmd) > 0:
                # 开始处理命令, 用多线程方式
                _job_thread = threading.Thread(
                    target=self._async_call_on_cmd, args=(
                        _cmd[0], _cmd[1], is_print_async_execute_info)
                )
                # 启动线程
                _job_thread.start()
            await asyncio.sleep(1)

    #############################
    # 实例化的命令行处理 - 公共函数
    #############################

    def __init__(
            self,
            message='CMD>',
            default='',
            **kwargs):
        """
        PromptPlus的构造函数

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
                color_set {dict} - 要使用的配色集方案, 如果传None则使用系统默认配色集
                enable_cmd_auto_complete {bool} - 默认True, 是否启用命令行自动完成提示
                    1、如果启用, 则使用命令行自带的completer, 实现命令、参数的自动完成功能；
                        不启用则可以自行传入completer、complete_in_thread等原生参数
                    2、可以与complete_while_typing参数共同生效, 控制是按tab提示还是输入自动提示
                cmd_auto_complete_slow_time {float} - 默认0, 输入后延迟多久提示完成菜单
                enable_cmd_path_auto_complete {bool} - 默认True, 是否启动路径输入的自动提示
        """
        # 内部变量
        self._prompt_default_para = {
            'cmd_para': dict(),
            'ignore_case': False,
            'default_dealfun': None,
            'on_abort': None,
            'on_exit': None,
            'is_async': False,
            'logger': None,
            'enable_color_set': True,
            'color_set': None,
            'enable_cmd_auto_complete': True,
            'cmd_auto_complete_slow_time': 0,
            'enable_cmd_path_auto_complete': True
        }
        # Prompt类初始化支持的参数名清单, 内部使用
        self._prompt_para_name_list = (
            'lexer', 'completer', 'complete_in_thread', 'is_password',
            'editing_mode', 'extra_key_bindings', 'is_password', 'bottom_toolbar',
            'style', 'include_default_pygments_style', 'rprompt', 'multiline',
            'prompt_continuation', 'wrap_lines', 'history',
            'enable_history_search', 'complete_while_typing',
            'validate_while_typing', 'complete_style', 'mouse_support',
            'auto_suggest', 'clipboard', 'validator', 'refresh_interval',
            'extra_input_processor', 'default', 'enable_system_prompt',
            'enable_suspend', 'enable_open_in_editor', 'reserve_space_for_menu',
            'tempfile_suffix', 'inputhook')
        # 命令参数的默认设置值, 用于合并至外部参数对象, 避免传入参数有误导致其他问题
        self._cmd_para_default = {
            'deal_fun': None,
            'name_para': None,
            'short_para': None,
            'long_para': None,
            'word_para': None,
        }
        self._loop = asyncio.get_event_loop()  # 异步模式需要的事件循环处理对象
        self._async_cmd_queue = Queue()  # 异步模式的命令执行队列
        # 关键字配色方案, 每个配色方案格式为'#000088 bg:#aaaaff underline'
        self._default_color_set = {
            # 用户输入
            '': '#F2F2F2',  # 默认输入
            'cmd': '#13A10E',  # 命令
            'name_para': '#C19C00',  # key-value形式参数名
            'short_para': '#3B78FF',  # -char形式的短参数字符
            'long_para': '#FFFF00',  # -name形式的长参数字符
            'word_para': '#C19C00',  # word 形式的词字符
            'wrong_tip': '#FF0000 bg:#303030',  # 错误的命令或参数名提示 #ff0000 bg:#ffffff reverse

            # prompt提示信息
            'prompt': '#F2F2F2'
        }

        # 赋值
        self._message = message
        self._default = default
        self._prompt_init_para = self._prompt_default_para.copy()
        self._prompt_init_para.update(kwargs)  # 将传入的参数合并到默认参数中
        self._init_prompt_instance()

    def prompt_print(self, *args, sep=' ', end='\n', line_head=False, level=logging.INFO,
                     format_print=False, style=None, flush=False, force_logging=False, my_logger=None):
        """
        使用内置打印函数进行输出打印

        @param {*args} - 要打印的内容值, 可以传多个值进行打印
        @param {string} sep=' ' - 多个值之间的分隔符
        @param {string} end='\n' - 打印值结尾追加的字符串, 默认以'\n'换行
        @param {bool} line_head=False - 是否将打印内容重置至行头(覆盖当行已打印的内容)
            注: 该参数对于使用logger打印的情况无效, 即初始化对象时定义了logger的情况
        @param {int} level=logging.INFO - 输出日志级别, 该参数仅对使用logger的情况有效
        @param {bool} format_print=False - 是否格式化打印, 对于使用logger打印的情况无效
        @param {dict} style=None - 格式字符串的样式字典, 例如以下字典指定两个格式类:
                {
                    'aaa': '#ff0066',
                    'bbb': '#44ff00 italic',
                }
            然后再传入format_html_text(<aaa>Hello</aaa> <bbb>world</bbb>!)
        @param {bool} force_logging=False - 是否强制使用日志打印, 默认都是通过print输出
        @param {logger} my_logger=None - 如果该参数传入值, 则使用该日志对象进行打印
        """
        _args = list(args)
        _logger = self._prompt_init_para['logger']
        if my_logger is not None:
            _logger = my_logger
        if _logger is None or not force_logging:
            # 没有日志类, 直接输出
            if line_head and len(_args) > 0:
                _args[0] = '\r%s' % str(_args[0])
            if format_print:
                PromptPlus.print_formatted_text(*_args, sep=sep, end=end, style=style, flush=flush)
            else:
                print(*_args, sep=sep, end=end, flush=flush)
        else:
            _print_str = MemoryStringStream()
            print(*args, sep=sep, end=end, file=_print_str, flush=flush)
            _logger.log(level, _print_str)

    def call_cmd_directly(self, cmd_str, shell_cmd: bool = False):
        """
        外部直接使用实例执行命令, 不通过命令行获取

        @param {string} cmd_str - 要实行的命令(含命令本身和参数)
        @param {bool} shell_cmd=False - 是否命令行直接执行模式

        @return {CResult} - 执行返回结果
        """
        _run_result = CResult(code='00000')
        if len(cmd_str) == 0:
            return _run_result

        try:
            # 执行命令
            _run_result = self._call_on_cmd(
                message=self._message, cmd_str=cmd_str, shell_cmd=shell_cmd
            )
        except:
            # 其他异常
            _run_result = CResult(
                code='29999', error=str(sys.exc_info()), trace_str=traceback.format_exc()
            )
            self.prompt_print('prompt_once run exception (%s):\r\n%s' %
                              (_run_result.error, _run_result.trace_str))

        _real_result = self._deal_run_result(_run_result)

        return _real_result

    def prompt_once(self, message=None, default='', **kwargs):
        """
        处理一次命令输入

        @param {string} message=None - 命令行提示符内容, 如果不传则代表使用实例的默认提示符
        @param {string} default='' - 人机交互输入的默认值, 直接显示在界面上, 可以进行修改后回车输入
        @param {kwargs} kwargs - python-prompt-toolki的原生prompt参数

        @returns {CResult} - 处理结果, code定义如下:
            '00000' - 成功
            '29999' - 其他系统失败
            '10100' - 用户中断输入(Ctrl + C)
            '10101' - 用户退出应用(Ctrl + D)

        """
        _run_result = CResult(code='00000', msg=u'success')  # 执行某个方法的结果
        _message = message
        if message is None:
            _message = self._message

        try:
            _cmd_str = ''
            # 不确定参数数量, 因此用循环方式赋值
            _run_str = u'self._prompt_instance.prompt(message=_message, default=default'
            for _para_name in kwargs:
                if _para_name in self._prompt_para_name_list:
                    _run_str = u'%s, %s=kwargs[\'%s\']' % (_run_str, _para_name, _para_name)
            _run_str = u'%s)' % _run_str

            # 执行获取输入
            _cmd_str = eval(_run_str)

            # 处理输入
            if len(_cmd_str) > 0:
                _run_result = self._call_on_cmd(message=_message, cmd_str=_cmd_str)
            else:
                self.prompt_print('')
                return CResult(code='00000')
        except KeyboardInterrupt:
            # 执行on_abort函数
            _run_result = self._call_on_abort(message=_message)
        except EOFError:
            # 执行on_exit函数
            _run_result = self._call_on_exit(message=_message)
        except:
            # 其他异常
            _run_result = CResult(
                code='29999', error=str(sys.exc_info()), trace_str=traceback.format_exc()
            )
            self.prompt_print('prompt_once run exception (%s):\r\n%s' %
                              (_run_result.error, _run_result.trace_str))

        _real_result = self._deal_run_result(_run_result)

        return _real_result

    # FIXME(黎慧剑): 异步模式, 当任务进程有输出时命令行不能固定在最后一行
    def start_prompt_service(
            self,
            tips=u'命令处理服务(输入过程中可通过Ctrl+C取消输入, 通过Ctrl+D退出命令行处理服务)',
            is_async=False,
            is_print_async_execute_info=True
    ):
        """
        启动命令行服务(循环获取用户输入并执行相应命令)

        @param {string} tips=u'命令处理服务(输入过程中可通过Ctrl+C取消输入, 通过Ctrl+D退出命令行处理服务)'
             - 命令行启动后的提示信息
        @param {bool} is_async=False - 是否异步模式, 即在命令执行完成前就可以接收下一个命令输入,
            否则等待命令结束后才接收下一个命令输入
        @param {bool} is_print_async_execute_info=True - 异步模式下是否打印执行信息(开始、结束)

        """
        # 先打印提示信息
        self.prompt_print(tips)
        if not is_async:
            # 非异步模式, 按部就班完成处理
            while True:
                _result = self.prompt_once(default=self._default)
                if _result.code == '10101':
                    # 退出获取命令处理
                    return

                # 间隔一会, 继续下一个处理
                RunTool.sleep(0.1)
        else:
            # 异步模式, 通知prompt_toolkit使用asyncio event loop
            try:
                use_asyncio_event_loop()
            except:
                # 兼容3.0的处理
                pass
            with patch_stdout():  # 支持重定向屏幕输出, 保证命令行一直在最下面
                shell_task = asyncio.ensure_future(self._async_cmd_service())
                background_task = asyncio.gather(
                    self._async_deal_cmd_from_queue(
                        is_print_async_execute_info=is_print_async_execute_info
                    ),
                    return_exceptions=True
                )

                self._loop.run_until_complete(shell_task)
                background_task.cancel()
                self._loop.run_until_complete(background_task)

    #############################
    # 工具函数
    #############################
    def get_cmd_para(self, cmd: str) -> dict:
        """
        获取指定命令的命令行参数

        @param {str} cmd - 要获取的命令

        @returns {dict} - 返回对应的命令行参数, 如果没有参数返回None
            deal_fun (匹配到命令要执行的函数) : fun 函数定义(function类型)
            name_para (para_name=para_value形式的参数) : dict(para_name: para_value_list)
                para_name {string} - 参数名
                para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
            short_para (-para_char para_value 形式的参数) : dict(para_char, para_value_list)
                para_char {char} - 短参数标识字符(单字符, 不带-)
                para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
                注: 该形式可以支持多个字符写在一个'-'后面, 例如: -xvrt
            long_para (-para_name para_value形式的参数) : dict(para_name, para_value_list)
                para_name {string} - 参数名(可以多字符, 不带-)
                para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
            word_para (直接一个词形式的参数) : dict(word_name, '')
                word_name {string} - 直接参数名
        """
        return self._prompt_init_para['cmd_para'].get(cmd, None)

    def upd_cmd_para(self, cmd: str, cmd_para: dict):
        """
        更新指定的命令的命令行参数

        @param {str} cmd - 要更新的命令
        @param {dict} cmd_para - 命令行参数
            deal_fun (匹配到命令要执行的函数) : fun 函数定义(function类型)
            name_para (para_name=para_value形式的参数) : dict(para_name: para_value_list)
                para_name {string} - 参数名
                para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
            short_para (-para_char para_value 形式的参数) : dict(para_char, para_value_list)
                para_char {char} - 短参数标识字符(单字符, 不带-)
                para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
                注: 该形式可以支持多个字符写在一个'-'后面, 例如: -xvrt
            long_para (-para_name para_value形式的参数) : dict(para_name, para_value_list)
                para_name {string} - 参数名(可以多字符, 不带-)
                para_value_list {string[]} - 对应参数名下的可选参数值清单, 如果para_value_list为None代表可以输入任意值
            word_para (直接一个词形式的参数) : dict(word_name, '')
                word_name {string} - 直接参数名
        """
        self._prompt_init_para['cmd_para'][cmd] = cmd_para
        self._init_prompt_instance()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
