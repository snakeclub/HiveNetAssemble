#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
控制台基本命令框架
@module base_cmd
@file base_cmd.py
"""
import os
import sys
import subprocess
import warnings
import copy
import ruamel.yaml as yaml
from collections.abc import Iterator
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _, get_global_i18n  # 装载全局的i18n快捷函数
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.string_tool import StringTool
from HiveNetPromptPlus import PromptPlus
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))


__MOUDLE__ = 'base_cmd'  # 模块名
__DESCRIPT__ = u'控制台基本命令框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.12.15'  # 发布日期


class CmdBaseFW(object):
    """
    命令处理类框架类
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        构造函数

        @param {kwargs} - 传入初始化参数字典(config.yaml的init_kwargs字典)
            参数中可以设置的特殊参数如下:
            is_i18n=False {bool} - 是否对返回输出的信息进行国际化转换(如果需要父类进行国际化, 则应设置为True)
            ignore_case=False {bool} - 匹配命令是否忽略大小写(视需要传入, 默认不区分大小写)

        @throws {Exception} - 如果初始化异常会抛出异常
        """
        self._kwargs = kwargs  # 初始化传入字典
        self._console_global_para = RunTool.get_global_var('CONSOLE_GLOBAL_PARA')
        self._CMD_DEALFUN_DICT = dict()  # 通用的命令与处理函数映射字典
        self._init(**kwargs)

    def cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        warnings.simplefilter('ignore', ResourceWarning)  # 指定屏蔽资源警告
        _temp_kwargs = copy.deepcopy(self._kwargs)
        _temp_kwargs.update(kwargs)

        _result = self._cmd_dealfun(message=message, cmd=cmd,
                                    cmd_para=cmd_para, prompt_obj=prompt_obj, **_temp_kwargs)

        _real_result = self._i18n_result_obj(
            _result, prompt_obj=prompt_obj,
            is_i18n=('is_i18n' in self._kwargs.keys() and self._kwargs['is_i18n'])
        )
        prompt_obj.prompt_print('')

        yield _real_result

    #############################
    # 内部处理函数
    #############################
    def _i18n_result_obj(self, result, prompt_obj=None, is_i18n=True):
        """
        公共的处理返回结果国际化处理及打印函数

        @param {CResult} - 处理结果, 如果不是CResult则返回成功的结果
        """
        _type = type(result)
        if _type == CResult:
            # 错误对象
            if hasattr(result, 'print_str') and result.print_str != '':
                prompt_obj.prompt_print(
                    _(result.print_str) if is_i18n else result.print_str
                )
                result.print_str = ''

            if is_i18n:
                result.msg = _(result.i18n_msg_id, result.i18n_msg_paras)
            return result
        elif _type == str:
            # 字符串
            prompt_obj.prompt_print(
                _(result) if is_i18n else result
            )
            return CResult(code='00000')
        elif isinstance(result, Iterator):
            # 是迭代器
            _last_result = CResult(code='00000')
            for _result in result:
                # 回调自己进行处理
                _last_result = self._i18n_result_obj(_result, prompt_obj)

            return _last_result
        else:
            # 当作字符串处理
            prompt_obj.prompt_print(
                _(str(result)) if is_i18n else str(result)
            )
            return CResult(code='00000')

    @classmethod
    def _cmd_para_to_dict(cls, cmd_para, name_with_sign=True, str_char='\'', tran_char='\\'):
        """
        将参数转换为字典格式

        @param {string} cmd_para - 命令参数
        @param {bool} name_with_sign=True - 参数名是否带标识(长短参数带-, 名字参数带=)
        @param {string} str_char='\'' - 字符串标识符
        @param {string} tran_char='\\' - 字符串里的转义字符

        @return {dict} - 参数字典, 获取规则说明如下:
            长短参数、名字参数: key为参数名(如果name_with_sign为True, 长短参数带-, 名字参数带=), value为参数值
            其他参数: key为'{para}序号', value为参数值, 序号从1开始
        """
        # 获取命令执行参数
        _cmd_list = PromptPlus.get_cmd_para_list(
            cmd_para, str_char=str_char, tran_char=tran_char
        )
        _dict = dict()
        _seq = 1
        for _item in _cmd_list:
            if _item[0] != '':
                _para_name = _item[0]
                if not name_with_sign:
                    # 去掉参数名标识
                    if _para_name.startswith('-'):
                        _para_name = _para_name[1:]
                    elif _para_name.endswith('='):
                        _para_name = _para_name[0: -1]

                _dict[_para_name] = _item[1].strip(str_char)
            else:
                _dict['{para}%d' % _seq] = _item[1].strip(str_char)
                _seq += 1
        # 返回字典
        return _dict

    #############################
    # 需具体实现类覆盖实现的类
    #############################
    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数

        @param {kwargs} - 传入初始化参数字典(config.yaml的init_kwargs字典)

        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        pass

    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        实现类需要覆盖实现的命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        # 获取真实执行的函数
        _real_dealfun = None  # 真实调用的函数
        if 'ignore_case' in kwargs.keys() and kwargs['ignore_case']:
            # 区分大小写
            if cmd in self._CMD_DEALFUN_DICT.keys():
                _real_dealfun = self._CMD_DEALFUN_DICT[cmd]
        else:
            # 不区分大小写
            if cmd.lower() in self._CMD_DEALFUN_DICT.keys():
                _real_dealfun = self._CMD_DEALFUN_DICT[cmd.lower()]

        # 执行函数
        if _real_dealfun is not None:
            return _real_dealfun(message=message, cmd=cmd, cmd_para=cmd_para, prompt_obj=prompt_obj, **kwargs)
        else:
            prompt_obj.prompt_print(_("'$1' is not support command!", cmd))
            return CResult(code='11404', i18n_msg_paras=(cmd, ))


class CmdDefault(CmdBaseFW):
    """
    匹配不到命令时执行的处理函数类
    """
    #############################
    # 实际处理函数
    #############################

    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        默认命令处理函数(未匹配到的命令)

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        prompt_obj.prompt_print(_("'$1' is not support command!", cmd))
        return CResult(code='00000')


class CmdOnAbort(CmdBaseFW):
    """
    客户取消本次输入执行的函数类
    Ctrl + C : abort,取消本次输入
    """

    #############################
    # 实际处理函数
    #############################
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        Ctrl + C : abort,取消本次输入

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        return CResult(code='00000')


class CmdOnExit(CmdBaseFW):
    """
    客户关闭命令行执行的函数类
    Ctrl + D : exit,关闭命令行
    """

    #############################
    # 实际处理函数
    #############################
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        Ctrl + D : exit,关闭命令行

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        if self._console_global_para['exit_with_prompt'] == 'n':
            # 不由用户选择直接退出
            prompt_obj.prompt_print(_("Exit $1 Console", self._console_global_para['name']))
            return CResult(code='10101')

        _tip = _('You will shutdown $1 console, continue?(y/N)',
                 self._console_global_para['name'])
        _back = input(_tip)
        if _back.upper() == 'Y':
            # 退出
            prompt_obj.prompt_print(_("Exit $1 Console", self._console_global_para['name']))
            return CResult(code='10101')
        else:
            # 取消退出
            prompt_obj.prompt_print(_("Cancel Exit"))
            return CResult(code='00000')


class CommonCmd(CmdBaseFW):
    """
    通用命令处理
    支持help、syscmd命令
    """
    #############################
    # 构造函数, 在里面增加函数映射字典
    #############################

    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数

        @param {kwargs} - 传入初始化参数字典(config.yaml的init_kwargs字典)

        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        self._CMD_DEALFUN_DICT = {
            'help': self._help_cmd_dealfun,
            'setlanguage': self._setlanguage_cmd_dealfun,
            'syscmd': self._syscmd_cmd_dealfun,
            'pwd': self._pwd_cmd_dealfun,
            'cd': self._cd_cmd_dealfun
        }
        self._console_global_para = RunTool.get_global_var('CONSOLE_GLOBAL_PARA')

    #############################
    # 实际处理函数
    #############################
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        通用处理函数, 通过cmd区别调用实际的处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        # 获取真实执行的函数
        _real_dealfun = None  # 真实调用的函数
        if 'ignore_case' in kwargs.keys() and kwargs['ignore_case']:
            # 区分大小写
            if cmd in self._CMD_DEALFUN_DICT.keys():
                _real_dealfun = self._CMD_DEALFUN_DICT[cmd]
        else:
            # 不区分大小写
            if cmd.lower() in self._CMD_DEALFUN_DICT.keys():
                _real_dealfun = self._CMD_DEALFUN_DICT[cmd.lower()]

        # 执行函数
        if _real_dealfun is not None:
            return _real_dealfun(message=message, cmd=cmd, cmd_para=cmd_para, prompt_obj=prompt_obj, **kwargs)
        else:
            prompt_obj.prompt_print(_("'$1' is not support command!", cmd))
            return CResult(code='11404', i18n_msg_paras=(cmd, ))

    #############################
    # 指令处理函数
    #############################
    def _help_cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        帮助命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        # 命令相关参数
        _CMD_HELP_INFO = self._console_global_para['CMD_HELP_INFO']
        _lang = self._console_global_para['language']

        _cmd_list = PromptPlus.get_cmd_para_list(cmd_para)
        if len(_cmd_list) == 0:
            # 没有传入任何参数, 生成命令提示参数并返回
            # 先计算命令的最大长度
            _max_len = 15
            for _key in _CMD_HELP_INFO.keys():
                _max_len = max(_max_len, len(_key))

            _cmd_list_tips = ''
            for _key in _CMD_HELP_INFO.keys():
                _cmd_title = ''
                if _lang in _CMD_HELP_INFO[_key].keys():
                    _cmd_title = _CMD_HELP_INFO[_key][_lang][0]
                elif 'en' in _CMD_HELP_INFO[_key].keys():
                    _cmd_title = _CMD_HELP_INFO[_key]['en'][0]
                else:
                    _cmd_title = _CMD_HELP_INFO[_key][list(_CMD_HELP_INFO[_key].keys())[0]][0]
                _cmd_list_tips = '%s%s%s\n' % (
                    _cmd_list_tips,
                    StringTool.fill_fix_string(_key, _max_len + 1, ' ', left=False),
                    _cmd_title.replace(
                        '{{VERSION}}', self._console_global_para['version']
                    ).replace(
                        '{{NAME}}', self._console_global_para['name']
                    ).replace(
                        '{{SHELL_CMD_NAME}}', self._console_global_para['shell_cmd_name']
                    )
                )
            # 返回提示信息
            return _cmd_list_tips

        # 处理某个命令的具体帮助信息
        _para_value = ''
        for _item in _cmd_list:
            if _item[0] == '':
                _para_value = _item[1]
                break
            elif _item[0] == '-c' or _item[0] == '-cmd':
                _para_value = _item[1]
                break

        if _para_value in _CMD_HELP_INFO.keys():
            # 显示指定命令帮助
            _help_info = None
            if _lang in _CMD_HELP_INFO[_para_value].keys():
                _help_info = _CMD_HELP_INFO[_para_value][_lang]
            elif 'en' in _CMD_HELP_INFO[_para_value].keys():
                _help_info = _CMD_HELP_INFO[_para_value]['en']
            else:
                _help_info = _CMD_HELP_INFO[_para_value][list(
                    _CMD_HELP_INFO[_para_value].keys())[0]]

            prompt_obj.prompt_print(
                '\n'.join(_help_info).replace(
                    '{{VERSION}}', self._console_global_para['version']
                ).replace(
                    '{{NAME}}', self._console_global_para['name']
                ).replace(
                    '{{SHELL_CMD_NAME}}', self._console_global_para['shell_cmd_name']
                )
            )
        else:
            # 没有匹配到命令
            prompt_obj.prompt_print(_("help not support '$1' command\n", (_para_value, )))

        # 返回结果
        return CResult(code='00000')

    def _syscmd_cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        执行操作系统命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        _shell_encoding = self._console_global_para['shell_encoding']
        _cmd_list = PromptPlus.get_cmd_para_list(cmd_para)
        _is_start_cmd = False
        _is_ni = False
        _is_bg = False
        _is_ns = False
        _real_cmd = ''

        for _item in _cmd_list:
            if not _is_start_cmd:
                # 还要判断是否参数
                if _item[0] in ['-ni', '-bg', '-ns']:
                    if _item[0] == '-ni':
                        _is_ni = True
                    elif _item[0] == '-bg':
                        _is_bg = True
                    else:
                        _is_ns = True

                    # 判断是否开始了命令
                    if _item[1] != '':
                        _real_cmd = _item[1]
                        _is_start_cmd = True

                    # 处理下一个对象
                    continue
                else:
                    # 开始是正式的命令
                    _is_start_cmd = True

            # 开始命令部分的处理
            _real_cmd += (' %s%s%s' % (
                _item[0],
                (' ' if _item[0] != '' and _item[0][0: 1] == '-' and _item[1] != '' else ''),
                _item[1]
            ))

        # 去掉前面的空格
        _real_cmd = _real_cmd.lstrip()

        # 执行进程
        prompt_obj.prompt_print('%s: %s\n\n' % (_('Execute system command'), _real_cmd))
        _sp = subprocess.Popen(
            _real_cmd, close_fds=_is_bg,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True
        )

        # 循环等待执行完成
        _exit_code = None
        try:
            while True:
                try:
                    # 打印内容
                    if not _is_ns:
                        prompt_obj.prompt_print(_sp.stdout.readline().decode(_shell_encoding))
                    _exit_code = _sp.poll()
                    if _exit_code is not None:
                        # 结束, 打印异常日志
                        if not _is_ns:
                            prompt_obj.prompt_print(_sp.stdout.read().decode(_shell_encoding))
                            if _exit_code != 0:
                                prompt_obj.prompt_print(_sp.stderr.read().decode(_shell_encoding))
                        break
                    # 释放一下CPU
                    RunTool.sleep(0.01)
                except KeyboardInterrupt:
                    if _is_ni:
                        # 不允许取消
                        prompt_obj.prompt_print(
                            '\n' + _("ommand Executing, can't exit execute job!"))
                    else:
                        raise KeyboardInterrupt
        except KeyboardInterrupt:
            # 遇到 Ctrl + C 退出
            if not _is_bg:
                # 结束任务
                _sp.terminate()
                _exit_code = _sp.poll()
                prompt_obj.prompt_print('\n' + _("Cancle Command execute, exit job!"))
            else:
                prompt_obj.prompt_print('\n' + _("Command execute in bg, exit monitor!"))

        # 最后返回
        if _exit_code is not None:
            prompt_obj.prompt_print('\n%s : %d' % (_("Command done, exit code"), _exit_code))

        prompt_obj.prompt_print('\n')

        if _exit_code != 0:
            return CResult(code='20999')
        else:
            return CResult(code='00000')

    def _pwd_cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        显示当前工作目录命令

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        prompt_obj.prompt_print(
            _('Current work path is: $1', self._console_global_para['work_path']))
        return CResult(code='00000')

    def _cd_cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        切换当前工作目录命令

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        _word_path = cmd_para.strip()
        os.chdir(_word_path)  # 改变工作目录, 如果没有异常则认为成功
        self._console_global_para['work_path'] = os.getcwd()
        prompt_obj.prompt_print(
            _('Current work path is: $1', self._console_global_para['work_path']))
        return CResult(code='00000')

    def _setlanguage_cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        修改显示语言

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数(命令后的字符串, 去掉第一个空格)
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @returns {CResult} - 命令执行结果, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的
            print_str属性要求框架进行打印处理
        """
        _result = CResult(code='00000')
        _lang = cmd_para.strip()
        if _lang == '':
            prompt_obj.prompt_print(_('language must be not null'))
            return _result
        self._console_global_para['language'] = cmd_para.strip()
        _i18n_obj = get_global_i18n()
        if _i18n_obj is not None:
            _i18n_obj.lang = self._console_global_para['language']

        # 修改配置文件中的默认语言
        with open(self._console_global_para['config_file'], 'r', encoding=self._console_global_para['config_encoding']) as _f:
            _config_str = _f.read()
            _config_dict = yaml.safe_load(_config_str)

        # 修改语言值
        _config_dict['console']['language'] = self._console_global_para['language']

        # 写回文件
        with open(self._console_global_para['config_file'], 'w', encoding=self._console_global_para['config_encoding']) as _f:
            yaml.safe_dump(_config_dict, stream=_f, allow_unicode=True)

        prompt_obj.prompt_print(_("Current language set to '$1'",
                                  self._console_global_para['language']))
        return _result


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
