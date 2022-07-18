#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
yaml文件的处理模块

@module yaml
@file yaml.py
"""
import os
import sys
from enum import Enum
import chardet
import ruamel.yaml
from ruamel.yaml.compat import StringIO
from ruamel.yaml.comments import CommentedSeq
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


__MOUDLE__ = 'yaml'  # 模块名
__DESCRIPT__ = u'yaml文件的处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.07.15'  # 发布日期


class EnumYamlObjType(Enum):
    """
    xml对象类型

    @enum {int}

    """
    File = 0  # 文件
    String = 2  # 字符串


class SimpleYaml(object):
    """
    Yaml配置文件的处理
    """

    #############################
    # 构造函数
    #############################

    def __init__(self, yaml_obj, obj_type: EnumYamlObjType = EnumYamlObjType.File,
            encoding=None, use_chardet=True):
        """
        构造函数

        @param {str} yaml_obj - yaml配置对象(可以为文件名或直接配置字符串)
        @param {EnumYamlObjType} obj_type=EnumYamlObjType.File - 配置对象类型
        @param {string} encoding=encoding - 装载字符编码, 如果传None代表自动判断
        @param {bool} use_chardet=True - 当自动判断的时候, 是否使用chardet库
        """
        # 参数处理
        self.encoding = encoding

        # 配置字符串
        self._yaml_str = ''
        if obj_type == EnumYamlObjType.String:
            self.file = None
            self._yaml_str = yaml_obj
            if encoding is None:
                self.encoding = 'utf-8'
        else:
            self.file = os.path.abspath(yaml_obj)
            with open(self.file, 'rb') as f:
                _yaml_bytes = f.read()

            # 判断字符集
            if self.encoding is None:
                if use_chardet:
                    self.encoding = chardet.detect(_yaml_bytes)['encoding']
                    if self.encoding.startswith('ISO-8859'):
                        self.encoding = 'gbk'
                else:
                    self.encoding = 'utf-8'

            self._yaml_str = str(_yaml_bytes, encoding=self.encoding)

        # 装载yaml对象
        self._yaml = ruamel.yaml.YAML()
        self._yaml.indent(mapping=2, sequence=4, offset=2)  # 配置输出格式
        self._yaml_config = self._yaml.load(self._yaml_str)

    #############################
    # 公共属性
    #############################
    @property
    def yaml_str(self):
        """
        获取yaml配置字符串

        @property {str}
        """
        _stream = StringIO()
        self._yaml.dump(self._yaml_config, stream=_stream)
        return _stream.getvalue()

    @property
    def yaml_config(self):
        """
        获取yaml配置对象
        注: 为兼容OrderedDict的CommentedMap对象

        @property {CommentedMap}
        """
        return dict(self._yaml_config)

    @property
    def yaml_dict(self):
        """
        获取yaml配置字典对象

        @property {dict}
        """
        return self._yaml_config

    #############################
    # 公共函数
    #############################
    def get_value(self, path: str, default=None):
        """
        获取指定配置路径的值

        @param {str} path - 配置路径字符串
            注1: 从根目录开始搜索, 路径下多个key之间使用'/'分隔, 例如 'root/key1/key2'
            注2: 可以通过[索引值]搜索特定key下第几个配置(数组或字典), 例如 'root/key1[0]'搜素key1下第一个对象
        @param {Any} default=None - 路径不存在时的默认值
        """
        try:
            return self._op_by_path(path, op_type='get')
        except:
            return default

    def set_value(self, path: str, val, auto_create: bool = True):
        """
        设置指定配置路径的值

        @param {str} path - 配置路径字符串
            注1: 从根目录开始搜索, 路径下多个key之间使用'/'分隔, 例如 'root/key1/key2'
            注2: 可以通过[索引值]搜索特定key下第几个配置(数组或字典), 例如 'root/key1[0]'搜素key1下第一个对象
        @param {Any} val - 要设置的值
        @param {bool} auto_create - 搜素路径不存在时是否自动创建
            注: 如果有指定索引值搜素则创建为list, 否则创建为dict
        """
        self._op_by_path(path, op_type='set', set_val=val, auto_create=auto_create)

    def remove(self, path: str):
        """
        删除指定配置

        @param {str} path - 配置路径字符串
            注1: 从根目录开始搜索, 路径下多个key之间使用'/'分隔, 例如 'root/key1/key2'
            注2: 可以通过[索引值]搜索特定key下第几个配置(数组或字典), 例如 'root/key1[0]'搜素key1下第一个对象
        """
        self._op_by_path(path, op_type='del')

    def save(self, file: str = None, encoding: str = None):
        """
        保存配置到文件中

        @param {str} file=None - 指定要保存的文件, 如果传None代表使用加载时的文件路径
        @param {str} encoding=None - 指定要保存的文件编码, 如果传None代表使用加载文件时的编码
        """
        _file = self.file if file is None else file
        _encoding = self.encoding if encoding is None else encoding
        with open(_file, 'w', encoding=_encoding) as _f:
            _f.write(self.yaml_str)

    #############################
    # 内部函数
    #############################
    def _op_by_path(self, path: str, op_type: str = 'get', set_val=None, auto_create: bool = False):
        """
        按路径对配置进行操作

        @param {str} path - 配置路径字符串
        @param {str} op_type='get' - 操作类型, get-获取值, set-设置值, del-删除值
        @param {Any} set_val=None - 要设置的值
        @param {bool} auto_create=True - 路径不存在是否自动创建, 该参数仅对set类型有效
            注: 如果有指定索引值搜素则创建为list, 否则创建为dict
        """
        _last_obj = self._yaml_config
        _paths = path.split('/')
        _path_max_index = len(_paths) - 1  # 最后一个路径索引
        for _index in range(_path_max_index + 1):
            # 获取路径中的完整信息
            _key_paths = _paths[_index].split('[')
            _key = _key_paths[0]  # 要搜索的key
            _sub_idxs = []  # key下对象的第几个
            for _sub_idx in range(1, len(_key_paths)):
                _sub_idxs.append(int(_key_paths[_sub_idx][0: -1]))

            _sub_idxs_len = len(_sub_idxs)
            _max_sub_idx = _sub_idxs_len - 1

            # 按照不同的操作进行不同处理
            if op_type == 'del':
                # 删除模式遇到错误代表值不存在，直接返回即可
                try:
                    if _index == _path_max_index:
                        # 是最后一级, 进行删除的判断
                        if _sub_idxs_len == 0:
                            # 没有向下搜索的索引, 直接删除当前key
                            del _last_obj[_key]
                            return
                        else:
                            _last_obj = _last_obj[_key]
                            for _idx in range(_sub_idxs_len):
                                if type(_last_obj) in (CommentedSeq, list):
                                    # 是列表
                                    if _idx == _max_sub_idx:
                                        # 最后一个参数, 进行删除
                                        _last_obj.pop(_sub_idxs[_idx])
                                        return
                                    else:
                                        _last_obj = _last_obj[_sub_idxs[_idx]]
                                else:
                                    # 是字典
                                    _sub_key = list(_last_obj.keys())[_sub_idxs[_idx]]
                                    if _idx == _max_sub_idx:
                                        del _last_obj[_sub_key]
                                        return
                                    else:
                                        _last_obj = _last_obj[_sub_key]
                    else:
                        # 非最后一级, 继续搜索
                        _last_obj = _last_obj[_key]
                        for _idx in range(_sub_idxs_len):
                            if type(_last_obj) in (CommentedSeq, list):
                                _last_obj = _last_obj[_sub_idxs[_idx]]
                            else:
                                _sub_key = list(_last_obj.keys())[_sub_idxs[_idx]]
                                _last_obj = _last_obj[_sub_key]
                except:
                    return
            elif op_type == 'get':
                # 获取模式, 无法搜索的时候直接抛出异常即可
                _last_obj = _last_obj[_key]
                for _idx in range(_sub_idxs_len):
                    if type(_last_obj) in (CommentedSeq, list):
                        _last_obj = _last_obj[_sub_idxs[_idx]]
                    else:
                        _sub_key = list(_last_obj.keys())[_sub_idxs[_idx]]
                        _last_obj = _last_obj[_sub_key]

                if _index == _path_max_index:
                    # 已经是最后一级, 返回对象的值即可
                    return _last_obj
            else:
                # 设置模式
                _key_val = _last_obj.get(_key, None)
                if _sub_idxs_len == 0:
                    # 没有位置索引的情况
                    if _index == _path_max_index:
                        # 最后一级设置
                        _last_obj[_key] = set_val
                        return

                    # 要继续往下搜索
                    if _key_val is None and auto_create:
                        # 创建下一级为dict
                        _last_obj[_key] = {}
                    _last_obj = _last_obj[_key]

                    # 没有位置索引, 继续下一个搜索循环
                    continue

                # 有位置索引的情况
                if _key_val is None and auto_create:
                    # 要创建下一级是list
                    _last_obj[_key] = []
                _last_obj = _last_obj[_key]

                # 逐级处理
                for _idx in range(_sub_idxs_len):
                    if type(_last_obj) in (CommentedSeq, list):
                        # 自动创建数组中不存在的对象
                        if auto_create and len(_last_obj) < _sub_idxs[_idx] + 1:
                            for _add_idx in range(len(_last_obj), _sub_idxs[_idx]):
                                _last_obj.append(None)

                            if _idx == _max_sub_idx:
                                # 是当前path最后一个索引, 下一个必须为dict
                                _last_obj.append({})
                            else:
                                _last_obj.append([])

                        if _idx == _max_sub_idx and _index == _path_max_index:
                            # 最后一级设置
                            _last_obj[_sub_idxs[_idx]] = set_val
                            return
                        else:
                            _last_obj = _last_obj[_sub_idxs[_idx]]
                    else:
                        # 字典情况
                        _sub_key = list(_last_obj.keys())[_sub_idxs[_idx]]
                        if _idx == _max_sub_idx and _index == _path_max_index:
                            _last_obj[_sub_key] = set_val
                            return
                        else:
                            if _last_obj[_sub_key] is None and auto_create:
                                if _idx == _max_sub_idx:
                                    # 是当前path最后一个索引, 下一个必须为dict
                                    _last_obj[_sub_key] = {}
                                else:
                                    _last_obj[_sub_key] = []

                            _last_obj = _last_obj[_sub_key]


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
