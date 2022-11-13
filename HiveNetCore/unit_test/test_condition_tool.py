#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
"""
测试条件处理工具
@module test_condition_tool
@file test_condition_tool.py
"""

import sys
import os
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.utils.condition_tool import ConditionTool


class TestConditionTool(unittest.TestCase):
    """
    测试ConditionTool类
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        pass

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_run_conditions(self):
        """
        测试运行条件
        """
        _var1 = 10
        _var2 = 'abc'
        _var3 = True
        _var4 = ['abc', 'bcd']
        print(_var1, _var2, _var3, _var4)

        # 单个条件处理
        _conditions = {
            '$and': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 == "abc"'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, '单个条件 - 条件1执行错误')

        _conditions = {
            '$and': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, '单个条件 - 条件2执行错误')

        _conditions = {
            '$or': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, '单个条件 - 条件3执行错误')

        _conditions = {
            '$or': [
                ('pyexp', {'exp': '_var1 != 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, '单个条件 - 条件4执行错误')

        _conditions = {
            '$not': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, '单个条件 - 条件5执行错误')

        _conditions = {
            '$not': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 == "abc"'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, '单个条件 - 条件6执行错误')

        # 嵌套条件处理
        _conditions = {
            '$and': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 == "abc"'})
            ],
            '$or': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ],
            '$not': [
                ('pyexp', {'exp': '_var1 != 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ]
        }

        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, '嵌套条件 - 条件1执行错误')

        _conditions = {
            '$and': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 == "abc"'})
            ],
            '$or': [
                ('pyexp', {'exp': '_var1 != 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ],
            '$not': [
                ('pyexp', {'exp': '_var1 != 10'}),
                ('pyexp', {'exp': '_var2 != "abc"'})
            ]
        }

        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, '嵌套条件 - 条件2执行错误')

        _conditions = {
            '$and': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 == "abc"'}),
                {
                    '$or': [
                        ('pyexp', {'exp': '_var1 == 10'}),
                        ('pyexp', {'exp': '_var2 != "abc"'})
                    ]
                }
            ],
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, '嵌套条件 - 条件3执行错误')

        _conditions = {
            '$and': [
                ('pyexp', {'exp': '_var1 == 10'}),
                ('pyexp', {'exp': '_var2 == "abc"'}),
                {
                    '$or': [
                        ('pyexp', {'exp': '_var1 != 10'}),
                        ('pyexp', {'exp': '_var2 != "abc"'})
                    ]
                }
            ],
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, '嵌套条件 - 条件4执行错误')

        # exist类型判断
        _conditions = {
            '$and': [
                ('exists', {'value': 'abc', 'obj': {'abc': 'v1', 'bcd': 'v2'}})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, 'exist类型判断 - 条件1执行错误')

        _conditions = {
            '$and': [
                ('exists', {'value': 'efg', 'obj': {'abc': 'v1', 'bcd': 'v2'}})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, 'exist类型判断 - 条件2执行错误')

        _conditions = {
            '$and': [
                ('exists', {'value': 'abc', 'obj': ['abc', 'bcd']})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, 'exist类型判断 - 条件3执行错误')

        _conditions = {
            '$and': [
                ('exists', {'value': 'efg', 'obj': ['abc', 'bcd']})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(not _result, 'exist类型判断 - 条件4执行错误')

        _conditions = {
            '$and': [
                ('exists', {'value': 'abc', 'obj': "{'abc': 'v1', 'bcd': 'v2'}", 'obj_type': 'strexp'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, 'exist类型判断 - 条件5执行错误')

        _conditions = {
            '$and': [
                ('exists', {'value': 'abc', 'obj': "_var4", 'obj_type': 'pyexp'})
            ]
        }
        _result = ConditionTool.run_conditions(_conditions)
        self.assertTrue(_result, 'exist类型判断 - 条件6执行错误')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
