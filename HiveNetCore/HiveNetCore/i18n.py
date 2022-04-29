#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
国际化文本处理模块

@module i18n
@file i18n.py

"""

import os
import sys
import copy
import json
import re
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.file_tool import FileTool


__MOUDLE__ = 'i18n'  # 模块名
__DESCRIPT__ = u'国际化文本处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


def set_global_i18n(i18n_obj):
    """
    设置通用的SimpleI18N实例对象

    @param {object} i18n_obj - SimpleI18N实例对象

    """
    RunTool.set_global_var('SIMPLE_I18N_GLOBAL_OBJECT', i18n_obj)


def get_global_i18n():
    """
    获取全局SimpleI18N实例对象

    @returns {SimpleI18N} - 如果未设置返回None

    """
    return RunTool.get_global_var('SIMPLE_I18N_GLOBAL_OBJECT')


def _(s, *args):
    """
    封装对字符串的国际化简化处理函数

    @param {string} s - 要进行国际化处理的字符串
    @param {tuple} args - 进行占位符替换的变量

    @returns {string} - 国际化转换后的字符串

    @example
        1、直接进行字符串转换
            print(_('success!'))

        2、通过占位符替换的情况
            print(_('my name is $1, i am $2 years old', 'snaker', '30'))

    """
    i18n_obj = RunTool.get_global_var('SIMPLE_I18N_GLOBAL_OBJECT')
    if i18n_obj is None:
        return s
    else:
        return i18n_obj.translate(s, args)


def init_global_i18n():
    """
    初始化HiveNetCore的国际化控件, 包括:
    1、生成SimpleI18N类, 并设置到全局变量
    2、装载HiveNetCore的基础国际化配置信息

    """
    _i18n_obj = get_global_i18n()
    if _i18n_obj is None:
        _i18n_obj = SimpleI18N()
        set_global_i18n(_i18n_obj)

    # 装载所需的配置信息, 错误码
    _base_path = os.path.abspath(os.path.dirname(__file__) + '/')
    _error_code_path = os.path.realpath(_base_path + '/hivenet_error_code/')
    _i18n_obj.load_trans_from_dir(
        trans_file_path=_error_code_path,
        trans_file_prefix='errorcode',
        encoding='utf-8',
        append=True
    )


class SimpleI18N(object):
    """
    国际化文本处理类

    """

    #############################
    # 变量
    #############################
    lang = 'en'  # 默认语言
    __trans_dict = None  # 语言信息字典

    @property
    def trans_dict(self):
        """
        返回已装载的多国语言字典
        格式如下:
        {
            'en': {
                'success' : 'success',
                'failed' : 'failed',
                'my name is $1' : 'my name is $1'
            },
            'zh': {
                'success' : '成功',
                'failed' : '失败',
                'my name is $1' : '我的名字是$1'
            }
        }

        @property {dict}

        """
        return self.__trans_dict

    def __init__(self, lang='en', trans_file_path=None, trans_file_prefix='',
                 encoding='utf-8', auto_loads=False):
        """
        构造函数

        @param {string} lang='en' - 指定默认语言, 例如en、zh等
        @param {string} trans_file_path=None - 语言信息文件所在路径, 如果为None则代表不处理信息文件
        @param {string} trans_file_prefix='' - 语言信息文件前缀,
            例如前缀为test, 信息文件名为test_en.json、test_zh.json等
        @param {string} encoding='utf-8' - 解析文件的编码
        @param {bool} auto_loads=False - 是否自动加载语言信息文件

        """
        self.__trans_dict = dict()
        self.lang = lang
        if auto_loads and trans_file_path is not None:
            # 加载语言信息文件
            self.load_trans_from_dir(
                trans_file_path=trans_file_path,
                trans_file_prefix=trans_file_prefix,
                encoding=encoding,
                append=False
            )

    def load_trans_from_dir(self, trans_file_path, trans_file_prefix, encoding='utf-8', append=True):
        """
        从指定路径加载语言信息文件到对象中

        @param {string} trans_file_path - 语言信息文件所在路径, 如果为None则代表不处理信息文件
        @param {string} trans_file_prefix - 语言信息文件前缀,
            例如前缀为test, 信息文件名为test_en.json、test_zh.json等
        @param {string} encoding='utf-8' - 解析文件的编码
        @param {bool} append=True - 是否追加模式, 如果是则以增量方式更新, 否则覆盖原来的配置

        """
        file_list = FileTool.get_filelist(
            path=trans_file_path,
            regex_str=r'^' + trans_file_prefix + r'_\S+\.json$',
            is_fullname=True
        )
        for file in file_list:
            # 循环加载语言信息文件
            file_name = os.path.split(os.path.realpath(file))[1]
            file_lang = re.sub(r'\.json$', '', re.sub(
                r'^' + trans_file_prefix + r'_', '', file_name))
            self.load_trans_from_file(file_full_path=file, lang=file_lang,
                                      encoding=encoding, append=append)

    def load_trans_from_file(self, file_full_path, lang, encoding='utf-8', append=True):
        """
        从语言信息文件加载到对象中

        @param {string} file_full_path - 语言信息文件全路径( 含文件名)
        @param {string} lang - 对应的语言, 例如en、zh等
        @param {string} encoding='utf-8' - 解析文件的编码
        @param {bool} append=True - 是否追加模式, 如果是则以增量方式更新, 否则覆盖原来的配置

        """
        json_obj = {}
        with open(file_full_path, 'rt', encoding=encoding) as f:
            json_obj = json.load(f)
        self.load_trans_from_json(json_obj, lang=lang, append=append)

    def load_trans_from_str(self, json_str, lang, append=True):
        """
        从JSON字符串中加载语言信息到对象中

        @param {string} json_str - JSON字符串
        @param {string} lang - 对应的语言, 例如en、zh等
        @param {bool} append=True - 是否追加模式, 如果是则以增量方式更新, 否则覆盖原来的配置

        """
        json_obj = json.loads(json_str)
        self.load_trans_from_json(json_obj, lang=lang, append=append)

    def load_trans_from_json(self, json_obj, lang, append=True):
        """
        从JSON实例变量中加载语言信息到对象中

        @param {object} json_obj - 信息字典的json对象
        @param {string} lang - 对应的语言, 例如en、zh等
        @param {bool} append=True - 是否追加模式, 如果是则以增量方式更新, 否则覆盖原来的配置

        """
        if append and lang in self.__trans_dict.keys():
            # 追加模式, 逐条更新
            for key in json_obj.keys():
                self.__trans_dict[lang][key] = json_obj[key]
        else:
            # 覆盖模式, 直接重新设置值即可
            self.__trans_dict[lang] = copy.deepcopy(json_obj)

    def translate(self, msg_id, replace_para=(), lang=None):
        """
        返回指定语言的文本

        @param {string} msg_id - 要翻译的语言ID标识
        @param {tuple} replace_para=() - 进行占位符替换的变量
        @param {string} lang=None - 要翻译的语言, 如果不指定则采用初始化对象的默认语言

        @returns {string} - 国际化转换后的字符串

        """
        temp_lang = lang
        if lang is None:
            temp_lang = self.lang
        s = msg_id
        if temp_lang in self.__trans_dict.keys() and msg_id in self.__trans_dict[temp_lang].keys():
            # 可以找到对应的语言信息
            s = self.__trans_dict[temp_lang][msg_id]
        # 替换占位符
        i = 1  # 记录是第几个
        for para in replace_para:
            if s.find('$' + str(i)) >= 0:
                s = re.sub(r'\$' + str(i), str(para).replace('\\', '\\\\'), s)  # 如果字符串有'\'会抛异常
            i = i + 1
        # 处理完成
        return s


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
