#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetPromptPlus import PromptPlusCmdParaLexer


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _cmd_para = {
        'help': {
            'deal_fun': None,
            'name_para': None,
            'short_para': None,
            'long_para': None,
            'word_para': None
        },
        'dir': {
            'deal_fun': None,
            'name_para': {
                'para1': ['value11', 'value12'],
                'para2': ['value21', 'value22']
            },
            'short_para': dict(),
            'long_para': dict(),
            'word_para': None
        },
        'comshort': {
            'deal_fun': None,
            'name_para': None,
            'short_para': {
                'a': ['value1a', 'value2a'],
                'b': None,
                'c': []
            },
            'long_para': dict(),
            'word_para': None
        },
        'comlong': {
            'deal_fun': None,
            'name_para': None,
            'short_para': None,
            'long_para': {
                'abc': ['value1abc', 'value2abc'],
                'bcd': None,
                'ci': []
            },
            'word_para': None
        },
        'commix': {
            'deal_fun': None,
            'name_para': {
                'para1': ['value11', 'value12'],
                'para2': ['value21', 'value22']
            },
            'short_para': {
                'a': ['value1a', 'value2a'],
                'b': None,
                'c': []
            },
            'long_para': {
                'abc': ['value1abc', 'value2abc'],
                'bcd': None,
                'ci': []
            },
            'word_para': {
                'haha': [],
                'nono': []
            }
        },
        'wait': {
            'deal_fun': None,
            'name_para': None,
            'short_para': None,
            'long_para': None,
            'word_para': None
        },
    }
    _lexer = PromptPlusCmdParaLexer(
        cmd_para=_cmd_para, ignore_case=False
    )

    _info = _lexer._get_line_tokens(
        line='com -a - a para1=haha para1=-bb para=haha -b haha nono no -ab -bcd -c -bc ha', match_cmd='commix'
    )

    print(_info)
