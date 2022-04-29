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
                if _key not in base_dict.keys() or type(base_dict[_key]) != dict or type(_val) != dict:
                    # 非字典形式, 直接覆盖即可
                    base_dict[_key] = _val
                    continue

                # 字典形式, 使用自身处理下一级
                base_dict[_key] = cls.merge_dict(base_dict[_key], _val)

        return base_dict


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

