#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
测试相关工具

@module test_tool
@file test_tool.py

"""

import sys
import os
import json
import operator
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.utils.string_tool import StringTool


__MOUDLE__ = 'test_tool'  # 模块名
__DESCRIPT__ = u'测试相关工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.30'  # 发布日期


class TestTool(object):
    """
    测试相关工具, 提供各类检查比较函数

    """

    @classmethod
    def cmp_list(cls, src_data, dst_data, sorted: bool = False, print_if_diff=True):
        """
        比较两个列表( list) 是否一致

        @param {list} src_data - 第1个list对象
        @param {list} dst_data - 第2个list对象
        @param {bool} sorted=Fasle - 是否比较前先排序
        @param {bool} print_if_diff=True - 当两个list不一致时是否打印对象信息

        @returns {bool} - True-两个list一致, False-两个list不一致

        """
        if sorted:
            src_data.sort()
            dst_data.sort()

        is_same = True
        try:
            if len(src_data) != len(dst_data):
                is_same = False
            else:
                i = 0
                while i < len(src_data):
                    is_sub_same = True
                    if type(src_data[i]) == list:
                        # 针对有子列表的情况, 递归处理
                        is_sub_same = TestTool.cmp_list(
                            src_data[i], dst_data[i], print_if_diff=False)
                        # print('list is_sub_same:'+str(is_sub_same) + str(i))
                    else:
                        is_sub_same = (src_data[i] == dst_data[i])
                        # print('obj is_sub_same:'+str(is_sub_same) + str(i))
                    if not is_sub_same:
                        is_same = False
                        break
                    i = i + 1

        except Exception:
            is_same = False

        if not is_same and print_if_diff:
            print('src_data :' + str(src_data))
            print('dst_data :' + str(dst_data))
        return is_same

    @classmethod
    def cmp_dict(cls, src_data, dst_data, print_if_diff=True):
        """
        比较两个字典是否一致

        @param {string/dict} src_data - 第1个字典对象( 或对象JSON字符串)
        @param {string/dict} dst_data - 第2个字典对象( 或对象JSON字符串)
        @param {bool} print_if_diff=True - 当两个字典不一致时是否打印对象信息

        @returns {bool} - True-两个字典一致, False-两个字典不一致

        """
        is_same = False
        if isinstance(src_data, str):
            src_data = json.dumps(src_data, ensure_ascii=False)
        if isinstance(dst_data, str):
            dst_data = json.dumps(dst_data, ensure_ascii=False)
        if len(src_data) != len(dst_data):
            if print_if_diff:
                print('cmp_dict: len difference!')
        else:
            src_key = list(src_data.keys())
            src_key.sort()
            dst_key = list(dst_data.keys())
            dst_key.sort()
            if operator.eq(src_key, dst_key):
                is_break = False
                for key in src_data.keys():
                    if src_data[key] != dst_data[key]:
                        # print(src_data1[key])
                        print('cmp_dict: value difference in key "%s"!' % (key))
                        is_break = True
                        break
                if not is_break:
                    # 如果没有中断过, 则代表比较成功
                    return True
            else:
                print('cmp_dict: key list difference!')
        if print_if_diff:
            print('src_data :' + StringTool.format_obj_property_str(src_data,
                                                                    is_deal_subobj=True, c_level=2))
            print('dst_data :' + StringTool.format_obj_property_str(dst_data,
                                                                    is_deal_subobj=True, c_level=2))
        return is_same

    @classmethod
    def is_contain_dict(cls, src_data, dst_data):
        """
        检查字典1是否包含在字典2中(字典1为字典2的子集)

        @param {string/dict} src_data - 第1个字典对象( 或对象JSON字符串)
        @param {string/dict} dst_data - 第2个字典对象( 或对象JSON字符串)

        @returns {bool} - True-字典1包含在字典2中, False-字典1未包含在字典2中

        """
        if isinstance(src_data, str):
            src_data = json.dumps(src_data, ensure_ascii=False)
        if isinstance(dst_data, str):
            dst_data = json.dumps(dst_data, ensure_ascii=False)
        else:
            src_key = list(src_data.keys())
            dst_key = list(dst_data.keys())
            # print(str(src_key))
            # print(str(dst_key))
            pd = [False for c in src_key if c not in dst_key]
            if pd:
                return False
            else:
                src_val = list(src_data.values())
                dst_val = list(dst_data.values())
                pds = [False for c in src_val if c not in dst_val]
                if pds:
                    return False
                else:
                    return True

    @classmethod
    def compare_binary_file(cls, src_file: str, dst_file: str, block_size: int = 1, cache_size: int = 1024):
        """
        比较两个二进制文件

        @param {str} src_file - 要比较的源文件路径
        @param {str} dst_file - 要比较的目标文件路径
        @param {int} block_size=1 - 要比较的块单位, 单位为byte
            注: 指定块大小大于1的情况, 将按块做比较, 有差异也是认为块存在差异
        @param {int} cache_size=1024 - 文件信息获取缓存大小, 单位为kb
            注: 实际将占用2个缓存区的内存控件

        @returns {list} - 比较出存在差异的地方, 形成差异数组, 格式如下:
            [
                ['^/-/+', start_pos, end_pos, size, block_count],
                ...
            ]
            注: ^代表两个文件存在差异的位置, -代表第一个文件长于第二个文件的大小, +代表第二个文件长于第一个文件的大小
                end_pos为结束位置, 也就是相同的下一个字节的开始位置
        """
        _cache_size = cache_size * 1024
        _differs = list()

        with open(src_file, 'rb') as _src_file, open(dst_file, 'rb') as _dst_file:
            # 获取文件大小
            _src_size = _src_file.seek(0, 2)
            _dst_size = _dst_file.seek(0, 2)

            # 准备参数
            _current_pos = 0  # 当前正在比较的位置
            _diff_start_pos = -1  # 当前差异开始位置
            _diff_end_pos = -1  # 当前差异结束位置

            # 循环获取文件进行比较
            while True:
                # 获取文件数据到内存
                _src_file.seek(_current_pos)
                _dst_file.seek(_current_pos)
                _src_cache = _src_file.read(_cache_size)
                _dst_cache = _dst_file.read(_cache_size)

                # 用于判断是否中止的已获取数据长度
                _src_cache_len = len(_src_cache)
                _dst_cache_len = len(_dst_cache)

                # 按块循环比较
                _cache_pos = 0
                _get_block_size = block_size
                while True:
                    # 判断可获取的数据大小
                    _get_block_size = min(
                        min(_src_cache_len - _cache_pos, block_size),
                        min(_dst_cache_len - _cache_pos, block_size)
                    )
                    if _get_block_size <= 0:
                        # 全部数据已经对比完
                        break

                    # 进行比较
                    _src_block = _src_cache[_cache_pos: _cache_pos + _get_block_size]
                    _dst_block = _dst_cache[_cache_pos: _cache_pos + _get_block_size]

                    if _src_block == _dst_block:
                        # 数据一致
                        if _diff_start_pos >= 0:
                            # 原来有差异
                            _differs.append([
                                '^', _diff_start_pos, _diff_end_pos, _diff_end_pos - _diff_start_pos + 1,
                                (_diff_end_pos - _diff_start_pos + 1) / block_size
                            ])
                            _diff_start_pos = -1
                            _diff_end_pos = -1
                    else:
                        # 数据不一致
                        if _diff_start_pos >= 0:
                            # 原来有差异, 将差异结束位置增加就好
                            _diff_end_pos = _current_pos + _get_block_size - 1
                        else:
                            # 原来没有差异, 增加差异信息
                            _diff_start_pos = _current_pos
                            _diff_end_pos = _current_pos + _get_block_size - 1

                    # 更新当前位置
                    _current_pos += _get_block_size
                    _cache_pos += _get_block_size

                # 判断是否要跳出循环
                if _src_cache_len < _cache_size or _dst_cache_len < _cache_size:
                    # 已经处理完成
                    break

            # 判断差异是否已完结
            if _diff_start_pos >= 0:
                _differs.append([
                    '^', _diff_start_pos, _diff_end_pos, _diff_end_pos - _diff_start_pos,
                    (_diff_end_pos - _diff_start_pos + 1) / block_size
                ])

            # 判断两个文件大小是否不一样
            if _src_size != _dst_size:
                _diff_start_pos = _current_pos
                _diff_end_pos = max(_src_size, _dst_size) - 1
                _differs.append([
                    '-' if _src_size > _dst_size else '+',
                    _diff_start_pos, _diff_end_pos, _diff_end_pos - _diff_start_pos + 1,
                    (_diff_end_pos - _diff_start_pos) / block_size
                ])

            # 返回结果
            return _differs


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
