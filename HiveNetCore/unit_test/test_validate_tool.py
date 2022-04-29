#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试通用验证工具
@module test_validate_tool
@file test_validate_tool.py
"""

import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.utils.validate_tool import ValidateTool


SWITCH = {
    'test_str_validate_fun': True,
    'test_validate_fun': True,
    'test_validate_rule': True,
    'test_dict_validate': True,
    'test_pre_obj_id': True,
}


class TestValidateTool(unittest.TestCase):
    """
    测试通用验证工具
    """

    # 整个Test类的开始和结束执行
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    # 每个用例的开始和结束执行
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_str_validate_fun(self):
        """
        测试字符验证函数
        """
        if not SWITCH['test_str_validate_fun']:
            return

        print("测试字符验证函数")
        print("测试 str_not_null ============>")
        self.assertTrue(ValidateTool.str_not_null('abc'), '测试str_not_null失败 - 正常字符串')
        self.assertTrue(not ValidateTool.str_not_null(''), '测试str_not_null失败 - 空字符串')
        self.assertTrue(not ValidateTool.str_not_null(None), '测试str_not_null失败 - None值')
        self.assertTrue(not ValidateTool.str_not_null(10), '测试str_not_null失败 - 非字符串')

        print("测试 str_len ============>")
        self.assertTrue(ValidateTool.str_len('abc', 2, 5),
                        '测试str_len失败 - 正常范围')
        self.assertTrue(ValidateTool.str_len('ab', 2, 3),
                        '测试str_len失败 - 正常范围，最小值')
        self.assertTrue(ValidateTool.str_len('abc', 2, 3),
                        '测试str_len失败 - 正常范围，最大值')
        self.assertTrue(not ValidateTool.str_len('a', 2, 3),
                        '测试str_len失败 - 小于最小值')
        self.assertTrue(not ValidateTool.str_len('abcd', 2, 3),
                        '测试str_len失败 - 大于最大值')
        self.assertTrue(ValidateTool.str_len('中文', 2, 3),
                        '测试str_len失败 - 中文正常范围')
        self.assertTrue(ValidateTool.str_len('中文正', 2, 3),
                        '测试str_len失败 - 中文正常范围，最大值')
        self.assertTrue(not ValidateTool.str_len('中文超过', 2, 3),
                        '测试str_len失败 - 中文大于最大值')

        print("测试str_lenb ============>")
        self.assertTrue(ValidateTool.str_lenb('abc', 2, 5),
                        '测试str_lenb失败 - 正常范围')
        self.assertTrue(ValidateTool.str_lenb('ab', 2, 3),
                        '测试str_lenb失败 - 正常范围，最小值')
        self.assertTrue(ValidateTool.str_lenb('abc', 2, 3),
                        '测试str_lenb失败 - 正常范围，最大值')
        self.assertTrue(not ValidateTool.str_lenb('a', 2, 3),
                        '测试str_lenb失败 - 小于最小值')
        self.assertTrue(not ValidateTool.str_lenb('abcd', 2, 3),
                        '测试str_lenb失败 - 大于最大值')
        self.assertTrue(ValidateTool.str_lenb('中文', 2, 5, encoding='gbk'),
                        '测试str_lenb失败 - 中文正常范围')
        self.assertTrue(ValidateTool.str_lenb('中文', 2, 4, encoding='gbk'),
                        '测试str_lenb失败 - 中文正常范围，最大值')
        self.assertTrue(not ValidateTool.str_lenb('中文超', 2, 4, encoding='gbk'),
                        '测试str_lenb失败 - 中文大于最大值')

        print("测试 str_is_int ============>")
        self.assertTrue(ValidateTool.str_is_int('123'),
                        '测试 str_is_int 失败 - 正常值')
        self.assertTrue(ValidateTool.str_is_int('+123'),
                        '测试 str_is_int 失败 - 带符号+')
        self.assertTrue(ValidateTool.str_is_int('-123'),
                        '测试 str_is_int 失败 - 带符号-')
        self.assertTrue(not ValidateTool.str_is_int('123a'),
                        '测试 str_is_int 失败 - 含字母')
        self.assertTrue(not ValidateTool.str_is_int('123.23'),
                        '测试 str_is_int 失败 - 带小数')
        self.assertTrue(ValidateTool.str_is_int(''),
                        '测试 str_is_int 失败 - 空值')

        print("测试 str_is_float ============>")
        self.assertTrue(ValidateTool.str_is_float('123.01'),
                        '测试 str_is_float 失败 - 正常值')
        self.assertTrue(ValidateTool.str_is_float('123'),
                        '测试 str_is_float 失败 - 只有整数')
        self.assertTrue(ValidateTool.str_is_float('0.12'),
                        '测试 str_is_float 失败 - 只有小数')
        self.assertTrue(ValidateTool.str_is_float('123.'),
                        '测试 str_is_float 失败 - 整数带小数点')
        self.assertTrue(ValidateTool.str_is_float('+123.01'),
                        '测试 str_is_float 失败 - 带符号+')
        self.assertTrue(ValidateTool.str_is_float('-123.01'),
                        '测试 str_is_float 失败 - 带符号-')
        self.assertTrue(not ValidateTool.str_is_float('.01'),
                        '测试 str_is_float 失败 - 单纯只有小数')
        self.assertTrue(not ValidateTool.str_is_float('123.a13'),
                        '测试 str_is_float 失败 - 带字母')
        self.assertTrue(ValidateTool.str_is_float(''),
                        '测试 str_is_float 失败 - 空值')

        print("测试 str_is_email ============>")
        self.assertTrue(ValidateTool.str_is_email('abc@33.com'),
                        '测试 str_is_email 失败 - 正常值')
        self.assertTrue(ValidateTool.str_is_email('abc@33'),
                        '测试 str_is_email 失败 - 正常值2')
        self.assertTrue(not ValidateTool.str_is_email('abc.33'),
                        '测试 str_is_email 失败 - 无@')
        self.assertTrue(ValidateTool.str_is_email(''),
                        '测试 str_is_email 失败 - 空值')

        print("测试 str_is_datetime ============>")
        self.assertTrue(ValidateTool.str_is_datetime('2019-11-22', format_str='yyyy-MM-dd'),
                        '测试 str_is_datetime 失败 - 正常值')
        self.assertTrue(ValidateTool.str_is_datetime('2019-11-22 12:01:02', format_str='yyyy-MM-dd hh:mm:ss'),
                        '测试 str_is_datetime 失败 - 带时间')
        self.assertTrue(ValidateTool.str_is_datetime('2019\\11\\22', format_str='yyyy\\MM\\dd'),
                        '测试 str_is_datetime 失败 - 特殊符号')
        self.assertTrue(ValidateTool.str_is_datetime('a2019\\b11\\22c', format_str='ayyyy\\bMM\\ddc'),
                        '测试 str_is_datetime 失败 - 带其他字符')
        self.assertTrue(not ValidateTool.str_is_datetime('2019-ab-22', format_str='yyyy-MM-dd'),
                        '测试 str_is_datetime 失败 - 带字母')
        self.assertTrue(not ValidateTool.str_is_datetime('2019-2-22', format_str='yyyy-MM-dd'),
                        '测试 str_is_datetime 失败 - 月份格式不符合')
        self.assertTrue(not ValidateTool.str_is_datetime('19-02-22', format_str='yyyy-MM-dd'),
                        '测试 str_is_datetime 失败 - 年份格式不符合')
        self.assertTrue(ValidateTool.str_is_datetime(''),
                        '测试 str_is_datetime 失败 - 空值')

        print("测试 str_check_date ============>")
        self.assertTrue(ValidateTool.str_check_date('2019-11-22', format_str='yyyy-MM-dd'),
                        '测试 str_check_date 失败 - 正常值')
        self.assertTrue(ValidateTool.str_check_date('2019/11/22', format_str='yyyy/MM/dd'),
                        '测试 str_check_date 失败 - 分隔符')
        self.assertTrue(ValidateTool.str_check_date('2019/1/22', format_str='yyyy/MM/dd'),
                        '测试 str_check_date 失败 - 1位月份')
        self.assertTrue(ValidateTool.str_check_date('2019/01/22', format_str='yyyy/MM/dd'),
                        '测试 str_check_date 失败 - 2位月份')
        self.assertTrue(not ValidateTool.str_check_date('2019/02/31', format_str='yyyy/MM/dd'),
                        '测试 str_check_date 失败 - 不存在的日期')
        self.assertTrue(not ValidateTool.str_check_date('2019/02/14', format_str='yyyy-MM-dd'),
                        '测试 str_check_date 失败 - 分隔符不一致')
        self.assertTrue(not ValidateTool.str_check_date('2019/ab/31', format_str='yyyy/MM/dd'),
                        '测试 str_check_date 失败 - 带字母')
        self.assertTrue(ValidateTool.str_check_date(''),
                        '测试 str_check_date 失败 - 空值')

        print("测试 str_check_num_area ============>")
        self.assertTrue(ValidateTool.str_check_num_area('10', 3.5, 40.5),
                        '测试 str_check_num_area 失败 - 正常值')
        self.assertTrue(ValidateTool.str_check_num_area('3.5', 3.5, 40.5),
                        '测试 str_check_num_area 失败 - 等于最小值')
        self.assertTrue(ValidateTool.str_check_num_area('40.5', 3.5, 40.5),
                        '测试 str_check_num_area 失败 - 等于最大值')
        self.assertTrue(not ValidateTool.str_check_num_area('2', 3.5, 40.5),
                        '测试 str_check_num_area 失败 - 小于最小值')
        self.assertTrue(not ValidateTool.str_check_num_area('41', 3.5, 40.5),
                        '测试 str_check_num_area 失败 - 大于最大值')
        self.assertTrue(not ValidateTool.str_check_num_area('3.5', 3.5, 40.5, is_eq_min=False),
                        '测试 str_check_num_area 失败 - 不应等于最小值')
        self.assertTrue(not ValidateTool.str_check_num_area('40.5', 3.5, 40.5, is_eq_max=False),
                        '测试 str_check_num_area 失败 - 不应等于最大值')
        self.assertTrue(ValidateTool.str_check_num_area('', 3.5, 40.5),
                        '测试 str_check_num_area 失败 - 空值')

        print("测试 str_check_float_size ============>")
        self.assertTrue(ValidateTool.str_check_float_size('10', 5, 2),
                        '测试 str_check_float_size 失败 - 整数正常值')
        self.assertTrue(ValidateTool.str_check_float_size('0.01', 5, 2),
                        '测试 str_check_float_size 失败 - 小数正常值')
        self.assertTrue(ValidateTool.str_check_float_size('54321.01', 5, 2),
                        '测试 str_check_float_size 失败 - 浮点数正常值')
        self.assertTrue(not ValidateTool.str_check_float_size('654321.01', 5, 2),
                        '测试 str_check_float_size 失败 - 整数超范围')
        self.assertTrue(not ValidateTool.str_check_float_size('54321.012', 5, 2),
                        '测试 str_check_float_size 失败 - 小数超范围')
        self.assertTrue(not ValidateTool.str_check_float_size('54321.a1', 5, 2),
                        '测试 str_check_float_size 失败 - 带字母')
        self.assertTrue(ValidateTool.str_check_float_size('', 5, 2),
                        '测试 str_check_float_size 失败 - 空值')

        print("测试 str_check_regex ============>")
        self.assertTrue(ValidateTool.str_check_regex('abc', '^[abc]{2,}', flags='0'),
                        '测试 str_check_regex 失败 - 正常值1')
        self.assertTrue(ValidateTool.str_check_regex('abbc', '^[abc]{2,}', flags='0'),
                        '测试 str_check_regex 失败 - 正常值2')
        self.assertTrue(ValidateTool.str_check_regex('Abbc', '^[abc]{2,}', flags='re.I'),
                        '测试 str_check_regex 失败 - 带大写参数')
        self.assertTrue(not ValidateTool.str_check_regex('Abc', '^[abc]{2,}', flags='0'),
                        '测试 str_check_regex 失败 - 大小写不匹配')
        self.assertTrue(not ValidateTool.str_check_regex('a', '[abc]{2,}', flags='0'),
                        '测试 str_check_regex 失败 - 数量不匹配')
        self.assertTrue(ValidateTool.str_check_regex('', ''),
                        '测试 str_check_regex 失败 - 空值')

    def test_validate_fun(self):
        """
        测试非字符串校验函数
        """
        if not SWITCH['test_validate_fun']:
            return

        print("测试非字符串校验函数")
        print("测试 not_null ============>")
        self.assertTrue(ValidateTool.not_null('1'),
                        '测试 not_null 失败 - 正常值1')
        self.assertTrue(ValidateTool.not_null(10),
                        '测试 not_null 失败 - 正常值2')
        self.assertTrue(not ValidateTool.not_null(''),
                        '测试 not_null 失败 - 空字符串')
        self.assertTrue(not ValidateTool.not_null(None),
                        '测试 not_null 失败 - None')

        print("测试 check_fun ============>")

        def test_fun1(obj, a, b, c=10):
            print("obj: %s, a: %s, b: %s, c: %s" % (obj, a, b, c))
            if a != 'a':
                return False
            return True
        self.assertTrue(ValidateTool.check_fun('abc1', test_fun1, a='a', b='b', c=12),
                        '测试 check_fun 失败 - 正常值1')
        self.assertTrue(ValidateTool.check_fun('abc2', test_fun1, a='a', b='b1', c='c'),
                        '测试 check_fun 失败 - 正常值2')
        self.assertTrue(ValidateTool.check_fun('abc3', test_fun1, 'a', b='b3', c='c3'),
                        '测试 check_fun 失败 - 正常值3')
        self.assertTrue(not ValidateTool.check_fun('abc3', test_fun1, a='a2', b='b2', c='c2'),
                        '测试 check_fun 失败 - 应返回失败')
        self.assertTrue(not ValidateTool.check_fun('abc3', test_fun1, a='a2', b='b2', c='c2'),
                        '测试 check_fun 失败 - 应返回失败')
        self.assertTrue(ValidateTool.check_fun(10, lambda n: 8 < n < 11),
                        '测试 check_fun 失败 - lambda模式1')
        self.assertTrue(not ValidateTool.check_fun(10, lambda n: 11 < n < 12),
                        '测试 check_fun 失败 - lambda模式2')
        self.assertTrue(ValidateTool.check_fun(10, (lambda n, m: 15 < (n + m) < 30), 15),
                        '测试 check_fun 失败 - lambda模式3')

    def test_validate_rule(self):
        """
        测试通用校验函数
        """
        if not SWITCH['test_validate_rule']:
            return

        print("测试通用校验函数")
        print("测试 单个规则验证单个对象 ============>")
        _rule = 'str_is_float'
        _obj_s = '32.4'  # 通过
        _obj_f = '32.4a'  # 不通过
        _i = 1
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        print(_result_f.msg)
        self.assertTrue(_result_s.is_success(), '测试 单个规则验证单个对象 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 单个规则验证单个对象 - 规则%d - 不通过 失败' % (_i, ))

        _rule = ValidateTool.str_is_float
        _obj_s = '32.4'  # 通过
        _obj_f = '32.5a'   # 不通过
        _i = 2
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        print(_result_f.msg)
        self.assertTrue(_result_s.is_success(), '测试 单个规则验证单个对象 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 单个规则验证单个对象 - 规则%d - 不通过 失败' % (_i, ))

        _rule = ('str_len', (3, 4))
        _obj_s = '123'  # 通过
        _obj_f = '12345'   # 不通过
        _i = 3
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        print(_result_f.msg)
        self.assertTrue(_result_s.is_success(), '测试 单个规则验证单个对象 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 单个规则验证单个对象 - 规则%d - 不通过 失败' % (_i, ))

        _rule = ('str_is_datetime', None, {'format_str': 'yyyy/MM/dd'}, '自定义错误$1 - $2 -$3')
        _obj_s = '2001/12/11'  # 通过
        _obj_f = '2001/2/33'   # 不通过
        _i = 4
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        print(_result_f.msg)
        self.assertTrue(_result_s.is_success(), '测试 单个规则验证单个对象 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 单个规则验证单个对象 - 规则%d - 不通过 失败' % (_i, ))

        print("测试 And和Or处理 ============>")
        _rule = ('And', ['str_not_null', ('str_len', (3, 4), ), ], )
        _obj_s = '123'  # 通过
        _obj_f = ''   # 不通过
        _obj_1 = '12'   # 不通过
        _i = 1
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        _result_1 = ValidateTool.check_by_rule(_rule, _obj_1, obj_id='my_obj%d' % _i)
        print('%s : %s' % (_result_f.msg, _result_1.msg, ))
        self.assertTrue(_result_s.is_success(), '测试 And和Or处理 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 And和Or处理 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(not _result_1.is_success(), '测试 And和Or处理 - 规则%d - 不通过 失败' % (_i, ))

        _rule = ('Or', ['str_is_int', ('str_len', (3, 4), ), ], )
        _obj_s = '1'  # 通过
        _obj_f = 'a'   # 不通过
        _obj_1 = 'abc'   # 通过
        _i = 2
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        _result_1 = ValidateTool.check_by_rule(_rule, _obj_1, obj_id='my_obj%d' % _i)
        print('%s : %s' % (_result_f.msg, _result_1.msg, ))
        self.assertTrue(_result_s.is_success(), '测试 And和Or处理 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 And和Or处理 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(_result_1.is_success(), '测试 And和Or处理 - 规则%d - 不通过 失败' % (_i, ))

        _rule = ('Or', ['str_is_int', ('And', [('str_len', (3, 4), ), 'str_is_float']), ], )
        _obj_s = '1'  # 通过
        _obj_f = 'abc'   # 不通过
        _obj_1 = '12.4'   # 通过
        _i = 3
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        _result_1 = ValidateTool.check_by_rule(_rule, _obj_1, obj_id='my_obj%d' % _i)
        print('%s : %s' % (_result_f.msg, _result_1.msg, ))
        self.assertTrue(_result_s.is_success(), '测试 And和Or处理 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 And和Or处理 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(_result_1.is_success(), '测试 And和Or处理 - 规则%d - 不通过 失败' % (_i, ))

        print("测试 列表形式一一对应校验 ============>")
        _rule = ['str_not_null', 'str_is_int', ('str_len', (3, 4), ), ]
        _obj_s = ['not null', '123', '123', ]  # 通过
        _obj_f = ['not null', '123', '12345', ]   # 不通过
        _obj_1 = ['not null', '123', ]  # 不通过
        _i = 1
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        _result_1 = ValidateTool.check_by_rule(_rule, _obj_1, obj_id='my_obj%d' % _i)
        _result_2 = ValidateTool.check_by_rule(
            _rule, _obj_1, obj_id='my_obj%d' % _i, ignore_list_miss_value=False)
        print('%s : %s' % (_result_f.msg, _result_2.msg, ))
        self.assertTrue(_result_s.is_success(), '测试 列表形式一一对应校验 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 列表形式一一对应校验 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(_result_1.is_success(), '测试 列表形式一一对应校验 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(not _result_2.is_success(), '测试 列表形式一一对应校验 - 规则%d - 不通过 失败' % (_i, ))

        print("测试 List方式验证 ============>")
        _rule = ('List', [('And', ['str_is_int', ('str_len', (3, 4), ), ]), ])
        _obj_s = '123'  # 通过
        _obj_f = '12345'   # 不通过
        _obj_1 = ['123', '234', '3456']  # 通过
        _obj_2 = ['123', '234', '123456']  # 不通过
        _i = 1
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        _result_1 = ValidateTool.check_by_rule(_rule, _obj_1, obj_id='my_obj%d' % _i)
        _result_2 = ValidateTool.check_by_rule(_rule, _obj_2, obj_id='my_obj%d' % _i)
        print('%s : %s' % (_result_f.msg, _result_2.msg, ))
        self.assertTrue(_result_s.is_success(), '测试 List方式验证 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 List方式验证 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(_result_1.is_success(), '测试 List方式验证 - 规则%d - 不通过 失败' % (_i, ))
        self.assertTrue(not _result_2.is_success(), '测试 List方式验证 - 规则%d - 不通过 失败' % (_i, ))

        print("测试 List方式-表格数据 ============>")
        _rule = ('List', ['str_not_null', 'str_is_int', ('str_len', (3, 4), ), ], )
        _obj_s = (
            ['not null', '123', '123', ],
            ['not', '124', '1234', ],
            ['not', '124', '1235', ],
        )  # 通过
        _obj_f = [
            ['not null', '123', '123', ],
            ['not', '124', '1234', ],
            ['not', '124', '12356', ],
        ]  # 不通过
        _i = 1
        _result_s = ValidateTool.check_by_rule(_rule, _obj_s, obj_id='my_obj%d' % _i)
        _result_f = ValidateTool.check_by_rule(_rule, _obj_f, obj_id='my_obj%d' % _i)
        print('%s' % (_result_f.msg, ))
        self.assertTrue(_result_s.is_success(), '测试 List方式-表格数据 - 规则%d - 通过 失败' % (_i, ))
        self.assertTrue(not _result_f.is_success(), '测试 List方式-表格数据 - 规则%d - 不通过 失败' % (_i, ))

    def test_dict_validate(self):
        """
        测试字典校验
        """
        if not SWITCH['test_dict_validate']:
            return

        print("测试字典校验")
        _rule = {
            'a': 'str_not_null',
            'b': ('And', ['str_not_null', ('str_len', (3, 4))]),
            'c': {
                'c1': 'str_not_null',
                'c2': ['str_not_null', ('str_len', (3, 4)), 'str_is_email'],
                'c3': ('List', ['str_not_null', ('str_len', (3, 4)), 'str_is_email'])
            }
        }

        print("测试 数据1-通过 ============>")
        _data = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c1': 'not null',
                'c2': ['not null', 'abc', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['not null2', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 1
        _result = ValidateTool.check_by_rule(_rule, _data, obj_id='my_obj%d' % _i)
        print('%s' % (_result.msg, ))
        self.assertTrue(_result.is_success(), '测试 数据1-通过 - 规则%d 失败' % (_i, ))

        print("测试 数据2缺失字典-通过 ============>")
        _data = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c2': ['not null', 'abc', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['not null2', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 2
        _result = ValidateTool.check_by_rule(_rule, _data, obj_id='my_obj%d' % _i)
        print('%s' % (_result.msg, ))
        self.assertTrue(_result.is_success(), '测试 数据2缺失字典 - 规则%d 失败' % (_i, ))

        print("测试 数据3缺失字典-不通过 ============>")
        _data = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c2': ['not null', 'abc', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['not null2', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 3
        _result = ValidateTool.check_by_rule(
            _rule, _data, obj_id='my_obj%d' % _i, ignore_extra_keys=False)
        print('%s' % (_result.msg, ))
        self.assertTrue(not _result.is_success(), '测试 数据2缺失字典 - 规则%d 失败' % (_i, ))

        print("测试 数据4有空值-通过 ============>")
        _data = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c1': 'not null',
                'c2': ['not null', '', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['not null2', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 4
        _result = ValidateTool.check_by_rule(_rule, _data, obj_id='my_obj%d' % _i)
        print('%s' % (_result.msg, ))
        self.assertTrue(_result.is_success(), '测试 数据4有空值-通过 - 规则%d 失败' % (_i, ))

        print("测试 数据5列表有问题-不通过 ============>")
        _data = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c1': 'not null',
                'c2': ['not null', 'abc', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 5
        _result = ValidateTool.check_by_rule(_rule, _data, obj_id='my_obj%d' % _i)
        print('%s' % (_result.msg, ))
        self.assertTrue(not _result.is_success(), '测试 数据5列表有问题-不通过 - 规则%d 失败' % (_i, ))

        print("测试 数据6字典列表-通过 ============>")
        _data = [
            {
                'a': 'not null',
                'b': 'abc',
                'c': {
                    'c1': 'not null',
                    'c2': ['not null', 'abc', 'abc@123.com'],
                    'c3': [
                        ['not null1', 'abc1', 'abc@123.com1'],
                        ['not null2', 'abc2', 'abc@123.com2'],
                        ['not null3', 'abc3', 'abc@123.com3'],
                    ]
                }
            },
            {
                'a': 'not',
                'b': 'abc',
                'c': {
                    'c1': 'not null',
                    'c2': ['not null', 'abc', 'abc@123.com'],
                    'c3': [
                        ['not null1', 'abc1', 'abc@123.com1'],
                        ['not null2', 'abc2', 'abc@123.com2'],
                        ['not null3', 'abc3', 'abc@123.com3'],
                    ]
                }
            },
        ]
        _i = 6
        _result = ValidateTool.check_by_rule(_rule, _data, obj_id='my_obj%d' % _i)
        print('%s' % (_result.msg, ))
        self.assertTrue(_result.is_success(), '测试 数据6字典列表-通过 - 规则%d 失败' % (_i, ))

    def test_pre_obj_id(self):
        """
        测试obj_id的显示
        """
        if not SWITCH['test_pre_obj_id']:
            return

        print("测试obj_id的显示")
        _rule = ['str_is_float', 'str_not_null', 'str_is_int']
        _obj = ['32.4', '', '10']
        _i = 1
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='my_obj%d' % _i)
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'my_obj%d~1' %
                        _i, '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _obj = ['32.4', 'notnull', ]
        _i = 1.1
        _result = ValidateTool.check_by_rule(
            _rule, _obj, obj_id='my_obj%d' % _i, ignore_list_miss_value=False)
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'my_obj%d' %
                        _i, '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _rule = ('List', 'str_not_null')
        _obj = ['32.4', '', '10']
        _i = 2
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='my_obj%d' % _i)
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'my_obj%d~1' %
                        _i, '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _rule = ('List', ['str_is_float', 'str_not_null', 'str_is_int'])
        _obj = [
            ['32.4', '123', '10'],
            ['32.4', '12', 'a'],
            ['32.4', '1', '10'],
        ]
        _i = 3
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='my_obj%d' % _i)
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'my_obj%d~1~2' %
                        _i, '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _rule = {
            'a': 'str_not_null',
            'b': ('And', ['str_not_null', ('str_len', (3, 4))]),
            'c': {
                'c1': 'str_not_null',
                'c2': ['str_not_null', ('str_len', (3, 4)), 'str_is_email'],
                'c3': ('List', ['str_not_null', ('str_len', (3, 4)), 'str_is_email'])
            }
        }

        _obj = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c1': '',
                'c2': ['not null', 'abc', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['not null2', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 4
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='my_obj%d' % _i)
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'my_obj%d->c->c1' % _i,
                        '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        # 如果obj_id为空，则直接以key开头
        _i = 5
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='')
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'c->c1',
                        '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _obj = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c1': 'not null',
                'c2': ['not null', 'abc', 'abc@123.com'],
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 6
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='')
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'c->c3~1~0',
                        '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _obj = [
            {
                'a': 'not null',
                'b': 'abc',
                'c': {
                    'c1': 'not null',
                    'c2': ['not null', 'abc', 'abc@123.com'],
                    'c3': [
                        ['not null1', 'abc1', 'abc@123.com1'],
                        ['not null2', 'abc2', 'abc@123.com2'],
                        ['not null3', 'abc3', 'abc@123.com3'],
                    ]
                }
            },
            {
                'a': 'not null',
                'b': 'abc',
                'c': {
                    'c1': 'not null',
                    'c2': ['not null', 'abc', 'abc@123.com'],
                    'c3': [
                        ['not null1', 'abc1', 'abc@123.com1'],
                        ['', 'abc2', 'abc@123.com2'],
                        ['not null3', 'abc3', 'abc@123.com3'],
                    ]
                }
            },
        ]
        _i = 7
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='')
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == '~1->c->c3~1~0',
                        '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))

        _obj = {
            'a': 'not null',
            'b': 'abc',
            'c': {
                'c1': 'not null',
                'c3': [
                    ['not null1', 'abc1', 'abc@123.com1'],
                    ['not null2', 'abc2', 'abc@123.com2'],
                    ['not null3', 'abc3', 'abc@123.com3'],
                ]
            }
        }
        _i = 6
        _result = ValidateTool.check_by_rule(_rule, _obj, obj_id='', ignore_extra_keys=False)
        print(_result.msg)
        self.assertTrue(_result.i18n_msg_paras[1] == 'c->c2',
                        '测试 测试obj_id的显示 - 规则%d 失败 - %s' % (_i, _result.i18n_msg_paras[1]))


if __name__ == '__main__':
    unittest.main()
