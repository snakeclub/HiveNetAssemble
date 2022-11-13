#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
import time
from HiveNetCore.logging_hivenet import Logger
from HiveNetCore.generic import CResult
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetPromptPlus import PromptPlus


#############################
# 通用的logger
#############################
_logger = Logger()

#############################
# 处理函数的定义
#############################


def on_abort(message='', prompt_obj=None, **kwargs):
    """Ctrl + C : abort,取消本次输入"""
    if prompt_obj is not None:
        prompt_obj.prompt_print('on_abort: %s' % message)
    _result = CResult()
    _result.print_str = 'on_abort done!'
    return _result


def on_exit(message='', prompt_obj=None, **kwargs):
    """Ctrl + D : exit,关闭命令行"""
    if prompt_obj is not None:
        prompt_obj.prompt_print('on_exit: %s' % message)
    _result = CResult(code='10101')
    _result.print_str = 'on_exit done!'
    return _result


def default_cmd_dealfun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
    """默认命令处理函数"""
    if prompt_obj is not None:
        prompt_obj.prompt_print(
            'cmd not define: message[%s], cmd[%s], cmd_para[%s]' % (message, cmd, cmd_para))
    _result = CResult()
    _result.print_str = 'default_cmd_dealfun done!'
    return _result


def dir_cmd_dealfun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
    """dir命令的处理函数"""
    if prompt_obj is not None:
        prompt_obj.prompt_print(
            'dir: message[%s], cmd[%s], cmd_para[%s]' % (message, cmd, cmd_para))
    _result = CResult()
    _result.print_str = 'dir_cmd_dealfun done!'
    return _result


def common_cmd_dealfun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
    """通用命令处理函数，持续10秒每秒输出一个wait的信息"""
    if prompt_obj is not None:
        prompt_obj.prompt_print(
            'common: message[%s], cmd[%s], cmd_para[%s]' % (message, cmd, cmd_para))

    if cmd == 'wait':
        _i = 0
        while _i < 10:
            _logger.info('wait ' + str(_i))
            _i = _i + 1
            time.sleep(1)

    _result = CResult()
    _result.print_str = 'common_cmd_dealfun done!'
    return _result


def help_cmd_dealfun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
    """帮助命令，输出提示信息"""
    if prompt_obj is not None:
        prompt_obj.prompt_print(cmd_para_descript)
    return CResult()


#############################
# 定义命令行参数
#############################
cmd_para_descript = u"""可使用的命令清单如下：
\thelp
\tdir para1=value11 para2=value21
\tcomshort -a value1a -b -c 或 -bc
\tcomlong -abc value1abc -bcd -ci
\tcommix para1=value11 para2=value21 -a value1a -b -c -abc value1abc -bcd -ci
\twait (持续10秒)
"""

test_cmd_para = {
    'help': {
        'deal_fun': help_cmd_dealfun,
        'name_para': None,
        'short_para': None,
        'long_para': None
    },
    'dir': {
        'deal_fun': dir_cmd_dealfun,
        'name_para': {
            'para1': ['value11', 'value12'],
            'para2': ['value21', 'value22']
        },
        'short_para': dict(),
        'long_para': dict()
    },
    'comshort': {
        'deal_fun': common_cmd_dealfun,
        'name_para': None,
        'short_para': {
            'a': ['value1a', 'value2a'],
            'b': None,
            'c': []
        },
        'long_para': dict()
    },
    'comlong': {
        'deal_fun': common_cmd_dealfun,
        'name_para': None,
        'short_para': None,
        'long_para': {
            'abc': ['value1abc', 'value2abc'],
            'bcd': None,
            'ci': []
        }
    },
    'commix': {
        'deal_fun': common_cmd_dealfun,
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
        }
    },
    'wait': {
        'deal_fun': common_cmd_dealfun,
        'name_para': None,
        'short_para': None,
        'long_para': None
    },
}


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    tips = u'命令处理服务(输入过程中可通过Ctrl+C取消输入，通过Ctrl+D退出命令行处理服务)'

    #############################
    # 外部程序自己控制命令循环
    #############################
    prompt1 = PromptPlus(
        message='请输入>',
        default='help',
        cmd_para=test_cmd_para,  # 命令定义参数
        default_dealfun=default_cmd_dealfun,  # 默认处理函数
        on_abort=on_abort,  # Ctrl + C 取消本次输入执行函数
        on_exit=on_exit  # Ctrl + D 关闭命令行执行函数
    )
    # 自己输出提示信息
    print(tips)
    # 循环使用prompt_once一个获取命令和执行
    while True:
        try:
            prompt1_result = prompt1.prompt_once(default='help')
            print('prompt1_result: %s', prompt1_result.msg)
            if prompt1_result.code == '10101':
                break
        except:
            print('excepiton')
    # 结束提示循环
    print('prompt1 stop！')

    #############################
    # 自动命令循环模式-同步
    #############################
    prompt1.start_prompt_service(
        tips=tips + '\n当前模式为同步模式'
    )
