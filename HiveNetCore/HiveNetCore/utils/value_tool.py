#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
值处理通用工具

@module value_tool
@file value_tool.py

"""

__MOUDLE__ = 'value_tool'  # 模块名
__DESCRIPT__ = u'值处理通用工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.30'  # 发布日期


from ruamel.yaml.comments import CommentedSeq


class ValueTool(object):
    """
    值处理通用工具

    """

    @classmethod
    def get_dict_value(cls, key, dict_obj, default_value=None):
        """
        获取字典指定值

        @param {object} key - 字典key值
        @param {dict} dict_obj - 要查的字典
        @param {object} default_value=None - 如果取不到的默认值

        @returns {object} - 去到值

        """
        _value = default_value
        if key in dict_obj.keys():
            _value = dict_obj[key]
        return _value

    @classmethod
    def set_dict_nest_value(cls, dict_obj, *args):
        """
        按嵌套方式设置字典的值

        @param {dict} dict_obj - 要设置的字典
        @param {*args} - 除最后一个参数都为str格式的字典key值,最后一个参数为要设置的值
            注: 最后形成的格式类似为 {
                args[0]: {args[1]: {args[2]: {args[3]: 值}}}
            }

        @return {dict} - 返回当前字典对象
        """
        _len = len(args)
        if _len < 2:
            # 没有具体设置值,不处理
            return dict_obj

        # 遍历进行处理
        _dict = dict_obj
        _i = 0
        while _i < _len - 2:
            _dict.setdefault(args[_i], {})
            _dict = _dict[args[_i]]
            _i += 1

        # 最后一个为值
        _dict[args[_i]] = args[_i + 1]

        return dict_obj

    @classmethod
    def get_sorted_list_by_key(cls, dict_obj: dict, reverse=False):
        """
        获取按key值排序后的key列表清单

        @param {dict} dict_obj - 要处理的字典
        @param {bool} reverse=False - 排序规则,reverse = True 降序 , reverse = False 升序(默认)

        @return {list} - 按key值排序后的key列表
        """
        return sorted(dict_obj, reverse=reverse)

    @classmethod
    def get_sorted_list_by_value(cls, dict_obj: dict, reverse=False):
        """
        获取按value值排序后的字典对象清单

        @param {dict} dict_obj - 要处理的字典
        @param {bool} reverse=False - 排序规则,reverse = True 降序 , reverse = False 升序(默认)

        @return {list} - 按key值排序后的对象清单[(key, value), (key, value), ...]
        """
        return sorted(dict_obj.items(), key=lambda kv: (kv[1], kv[0]), reverse=reverse)

    @classmethod
    def merge_dict(cls, base_dict: dict, *args) -> dict:
        """
        嵌套合并字典

        @param {dict} base_dict - 基础字典, 所有字典都在该字典基础上进行合并
            注: 将直接在该字典对象上修改
        @param {*args} - 每一个参数为要合并的一个字典对象

        @returns {dict} - 合并后的字典
        """
        for _dict in args:
            for _key, _val in _dict.items():
                # 逐个key进行合并处理
                if _key not in base_dict.keys() or not isinstance(base_dict[_key], dict) or not isinstance(_val, dict):
                    # 非字典形式, 直接覆盖即可
                    base_dict[_key] = _val
                    continue

                # 字典形式, 使用自身处理下一级
                base_dict[_key] = cls.merge_dict(base_dict[_key], _val)

        return base_dict

    @classmethod
    def get_dict_value_by_path(cls, path: str, dict_obj: dict, default_value=None):
        """
        获取字典指定路径的值

        @param {str} path - 检索路径
            注1: 从根目录开始搜索, 路径下多个key之间使用'/'分隔, 例如 'root/key1/key2'
            注2: 可以通过[索引值]搜索特定key下第几个配置(数组或字典), 例如 'root/key1[0]'搜素key1下第一个对象
        @param {dict} dict_obj - 字典对象

        @param {Any} default_value=None - 如果搜索不到返回的默认值
        """
        _last_obj = dict_obj
        _paths = path.split('/')
        _path_max_index = len(_paths) - 1  # 最后一个路径索引
        try:
            for _index in range(_path_max_index + 1):
                # 获取路径中的完整信息
                _key_paths = _paths[_index].split('[')
                _key = _key_paths[0]  # 要搜索的key
                _sub_idxs = []  # key下对象的第几个
                for _sub_idx in range(1, len(_key_paths)):
                    _sub_idxs.append(int(_key_paths[_sub_idx][0: -1]))

                _sub_idxs_len = len(_sub_idxs)

                _last_obj = _last_obj[_key]
                for _idx in range(_sub_idxs_len):
                    if type(_last_obj) in (CommentedSeq, list):
                        # 按顺序获取指定位置的数组值
                        _last_obj = _last_obj[_sub_idxs[_idx]]
                    else:
                        # 按字典顺序位置获取指定位置的字典
                        _sub_key = list(_last_obj.keys())[_sub_idxs[_idx]]
                        _last_obj = _last_obj[_sub_key]

                if _index == _path_max_index:
                    # 已经是最后一级, 返回对象的值即可
                    return _last_obj
        except:
            # 获取异常, 返回默认值
            return default_value

    @classmethod
    def set_dict_value_by_path(cls, path: str, dict_obj: dict, set_value, auto_create_key: bool = False):
        """
        设置字典指定路径的值

        @param {str} path - 检索路径
            注1: 从根目录开始搜索, 路径下多个key之间使用'/'分隔, 例如 'root/key1/key2'
            注2: 可以通过[索引值]搜索特定key下第几个配置(数组或字典), 例如 'root/key1[0]'搜素key1下第一个对象
        @param {dict} dict_obj - 字典对象
        @param {Any} set_value - 要设置的值
        @param {bool} auto_create_key=False - 是否自动创建不存在的Key
            注: 自动创建的对象固定为dict
        """
        _last_obj = dict_obj
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

            if _sub_idxs_len == 0:
                # 没有位置索引的情况
                if _index == _path_max_index:
                    # 最后一级设置
                    _last_obj[_key] = set_value
                    return

                # 要继续往下搜索
                if auto_create_key and _key not in _last_obj.keys():
                    # 自动创建不存在的key
                    _last_obj[_key] = dict()

                _last_obj = _last_obj[_key]

                # 没有位置索引, 继续下一个搜索循环
                continue

            # 有位置索引的情况
            if auto_create_key and _key not in _last_obj.keys():
                # 自动创建不存在的key
                _last_obj[_key] = dict()

            _last_obj = _last_obj[_key]

            # 逐级处理
            for _idx in range(_sub_idxs_len):
                if type(_last_obj) in (CommentedSeq, list):
                    if _idx == _max_sub_idx and _index == _path_max_index:
                        # 最后一级设置
                        _last_obj[_sub_idxs[_idx]] = set_value
                        return
                    else:
                        _last_obj = _last_obj[_sub_idxs[_idx]]
                else:
                    # 字典情况
                    _sub_key = list(_last_obj.keys())[_sub_idxs[_idx]]
                    if _idx == _max_sub_idx and _index == _path_max_index:
                        _last_obj[_sub_key] = set_value
                        return
                    else:
                        _last_obj = _last_obj[_sub_key]


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
