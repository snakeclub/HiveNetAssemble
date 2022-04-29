#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
测试i18n
@module test_i18n
@file test_i18n.py
"""

import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.i18n import SimpleI18N, _, set_global_i18n
from HiveNetCore.utils.test_tool import TestTool


__MOUDLE__ = 'test_i18n'  # 模块名
__DESCRIPT__ = u'测试i18n'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.30'  # 发布日期


class TestSimpleI18N(unittest.TestCase):
    """
    测试SimpleI18N类
    """

    # 测试的多国语言配置
    trans_en = '{"success!": "success!", "failed!": "failed!", "my name is $1, i am $2 years old.": "my name is $1, i am $2 years old."}'
    trans_zh = '{"success!": "成功!", "failed!": "失败!", "my name is $1, i am $2 years old.": "我叫$1, 我今年$2岁."}'
    trans_en_add = '{"test add para":"test add para", "success!": "overwrite success!"}'
    trans_zh_add = '{"test add para":"测试添加参数", "success!": "覆盖成功参数!"}'

    def setUp(self):
        """
        启动测试执行的初始化
        """
        self.dict_trans_en = {"success!": "success!", "failed!": "failed!",
                              "my name is $1, i am $2 years old.": "my name is $1, i am $2 years old."}
        self.dict_trans_zh = {"success!": "成功!", "failed!": "失败!",
                              "my name is $1, i am $2 years old.": "我叫$1, 我今年$2岁."}
        self.dict_trans_en_add = {"test add para": "test add para",
                                  "success!": "overwrite success!"}
        self.dict_trans_zh_add = {"test add para": "测试添加参数", "success!": "覆盖成功参数!"}
        self.i18n_obj = SimpleI18N(lang='zh')

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_auto_load(self):
        """
        测试自动加载
        """
        file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, 'test_data/simple_i18n')
        )

        obj = SimpleI18N(trans_file_path=file_path, trans_file_prefix='test', auto_loads=True)
        self.assertTrue(TestTool.cmp_dict(
            obj.trans_dict['en'], self.dict_trans_en), '自动装载en失败')
        self.assertTrue(TestTool.cmp_dict(
            obj.trans_dict['zh'], self.dict_trans_zh), '自动装载zh失败')

    def test_load_dict(self):
        """
        测试信息装载
        """
        # 装载字符串格式
        self.i18n_obj.load_trans_from_str(json_str=self.trans_en_add, lang='en', append=False)
        self.assertTrue(TestTool.cmp_dict(
            self.i18n_obj.trans_dict['en'], self.dict_trans_en_add), '装载json_str失败')

        # 装载对象格式
        self.i18n_obj.load_trans_from_json(json_obj=self.dict_trans_zh, lang='zh', append=False)
        self.assertTrue(TestTool.cmp_dict(
            self.i18n_obj.trans_dict['zh'], self.dict_trans_zh), '装载json_obj失败')

        # 装载文件格式
        file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, 'test_data/simple_i18n/test_en.json')
        )
        self.i18n_obj.load_trans_from_file(file_full_path=file_path, lang='en', append=False)
        self.assertTrue(TestTool.cmp_dict(
            self.i18n_obj.trans_dict['en'], self.dict_trans_en), '装载json_file失败')

        # 追加内容
        self.i18n_obj.load_trans_from_str(json_str=self.trans_zh_add, lang='zh', append=True)
        self.assertTrue(TestTool.cmp_dict(
            self.i18n_obj.trans_dict['zh'], dict(self.dict_trans_zh, **self.dict_trans_zh_add)),
            '追加json_str失败')

        # 获取翻译内容
        s1 = self.i18n_obj.translate(msg_id='success!', lang='en')
        self.assertTrue(s1 == 'success!', '翻译1失败')

        s2 = self.i18n_obj.translate(msg_id='success!')
        self.assertTrue(s2 == '覆盖成功参数!', '翻译2失败')

        s3 = self.i18n_obj.translate(msg_id='my name is $1, i am $2 years old.',
                                     replace_para=('lhj', 30))
        self.assertTrue(s3 == '我叫lhj, 我今年30岁.', '翻译3失败')

        # 快捷文本处理方式
        set_global_i18n(self.i18n_obj)
        s4 = _('success!')
        self.assertTrue(s4 == '覆盖成功参数!', '翻译4失败')

        s5 = _('my name is $1, i am $2 years old.', 'lhj', 30)
        self.assertTrue(s5 == '我叫lhj, 我今年30岁.', '翻译5失败')

        # 例外的ID
        s6 = _('my name is $1, i am $2 years old. haha！', 'lhj', 30)
        self.assertTrue(s6 == 'my name is lhj, i am 30 years old. haha！', '翻译6失败')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
