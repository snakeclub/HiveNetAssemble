#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试formula模块
@module test_formula
@file test_formula.py
"""

import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.formula import EnumFormulaSearchSortOrder, StructFormulaKeywordPara, FormulaTool
from HiveNetCore.utils.test_tool import TestTool


__MOUDLE__ = 'test_formula'  # 模块名
__DESCRIPT__ = u'测试formula模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.02'  # 发布日期


def formula_deal_fun_test(f_obj, my_string='my_string', my_list=['my_list'], **kwargs):
    """
    自定义公式处理函数
    """
    f_obj.formula_value = '[自定义内容开始]' + f_obj.content_string + '[自定义内容结束]'


class TestFormulaTool(unittest.TestCase):
    """
    测试FormulaTool类
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

    def test_search(self):
        """
        测试静态方法search
        """
        # 尝试解析SQL语句的关键字
        _source_str = 'select * From test where t.name \tlike \'%fromxxx\' order by name order'
        _split_common = ('\\^', '\r', '\n', ' ', '\t', '\\$')  # 关键字前置及后置字符
        _match_list = {
            'select': (_split_common, _split_common),
            'from': (_split_common, _split_common),
            'where': (_split_common, _split_common),
            'like': (_split_common, _split_common),
            'order': (_split_common, _split_common),
            'by': (_split_common, _split_common),
            'name': (tuple(), tuple()),
            'na': (tuple(), tuple())
        }
        _match_result = FormulaTool.search(source_str=_source_str, match_list=_match_list, ignore_case=True,
                                           multiple_match=False, sort_oder=EnumFormulaSearchSortOrder.ListDesc)
        # print(StringTool.format_obj_property_str(_match_result, is_deal_subobj=True))
        _match_result_list = FormulaTool.match_result_to_sorted_list(_match_result)
        _compare_match_result_list = [
            # 格式为[match_str, source_str, start_pos, end_pos, front_char, end_char]
            ['select', 'select', 0, 6, '\\^', ' '],
            ['from', 'From', 9, 13, ' ', ' '],
            ['where', 'where', 19, 24, ' ', ' '],
            ['na', 'na', 27, 29, '', ''],
            ['like', 'like', 33, 37, '\t', ' '],
            ['order', 'order', 49, 54, ' ', ' '],
            ['by', 'by', 55, 57, ' ', ' '],
            ['na', 'na', 58, 60, '', ''],
            ['order', 'order', 63, 68, ' ', '\\$']
        ]
        self.assertTrue(TestTool.cmp_list(_match_result_list,
                                          _compare_match_result_list), 'search执行结果不通过')

    def test_analyse_formula(self):
        """
        测试静态方法analyse_formula
        """
        # 解析带公式的字符串
        _source_str = '[full begin] formula {$PY=[PY1 begin] xxxx{$single=$}xx{$PY=[PY2 begin]eeeee[PY2 end]$}x [PY1 end]$} from {$end=[End begin]abc {$abc=[abc begin]"[string begin]kkkaf{$PY=not formula$}dfdf,\\",""haha[string end]"[abc end]$} PY=eeffff [full end]'

        # 定义字符串公式的公共关键字参数，例如python中的""引起来的认为是字符串
        _string_para = StructFormulaKeywordPara()
        _string_para.is_string = True  # 声明是字符串参数
        _string_para.has_sub_formula = False  # 声明公式中不会有子公式
        # 在查找字符串结束关键字时忽略的转义情况，例如"this is a string ,ignore \" , this is real end"
        _string_para.string_ignore_chars = ['\\"', '""']

        # 定义单关键字公式的公共参数（没有结束关键字）
        _single_para = StructFormulaKeywordPara()
        _single_para.is_single_tag = True  # 声明是单标签公式关键字

        # 定义以字符串结尾为结束标签的公共参数
        _end_para = StructFormulaKeywordPara()
        _end_para.end_tags = ['\\$']

        # 定义公式解析的关键字参数
        _keywords = {
            # 第一个定义了字符串的公式匹配参数
            'String': [
                ['"', list(), list()],  # 公式开始标签
                ['"', list(), list()],  # 公式结束标签
                _string_para  # 公式检索参数
            ],
            'PY': [
                ['{$PY=', list(), list()],  # 公式开始标签
                ['$}', list(), list()],  # 公式结束标签
                StructFormulaKeywordPara()  # 公式检索参数
            ],
            'abc': [
                ['{$abc=', list(), list()],
                ['$}', list(), list()],
                StructFormulaKeywordPara()
            ],
            'Single': [
                ['{$single=$}', list(), list()],
                None,
                _single_para
            ],
            'End': [
                ['{$end=', list(), list()],
                None,
                _end_para
            ]
        }

        # 解析公式
        _formula = FormulaTool.analyse_formula(
            formula_str=_source_str, keywords=_keywords, ignore_case=False)
        # print(StringTool.format_obj_property_str(deal_obj=_formula, is_deal_subobj=True))

        # 检查公式结果
        temp_formula = _formula
        if temp_formula.keyword != '' or temp_formula.content_string != _source_str:
            # 整个字符串
            self.assertTrue(False, '公式1匹配不通过')

        temp_formula = _formula.sub_formula_list[0]
        if temp_formula.keyword != 'PY' or temp_formula.content_string != '[PY1 begin] xxxx{$single=$}xx{$PY=[PY2 begin]eeeee[PY2 end]$}x [PY1 end]':
            # 整个字符串
            self.assertTrue(False, '公式2匹配不通过')

        temp_formula = _formula.sub_formula_list[0].sub_formula_list[0]
        if temp_formula.keyword != 'Single' or temp_formula.formula_string != '{$single=$}':
            # 整个字符串
            self.assertTrue(False, '公式3匹配不通过')

        temp_formula = _formula.sub_formula_list[0].sub_formula_list[1]
        if temp_formula.keyword != 'PY' or temp_formula.content_string != '[PY2 begin]eeeee[PY2 end]':
            # 整个字符串
            self.assertTrue(False, '公式4匹配不通过')

        temp_formula = _formula.sub_formula_list[1]
        if temp_formula.keyword != 'End' or temp_formula.content_string != '[End begin]abc {$abc=[abc begin]"[string begin]kkkaf{$PY=not formula$}dfdf,\\",""haha[string end]"[abc end]$} PY=eeffff [full end]':
            # 整个字符串
            self.assertTrue(False, '公式5匹配不通过')

        temp_formula = _formula.sub_formula_list[1].sub_formula_list[0]
        if temp_formula.keyword != 'abc' or temp_formula.content_string != '[abc begin]"[string begin]kkkaf{$PY=not formula$}dfdf,\\",""haha[string end]"[abc end]':
            # 整个字符串
            self.assertTrue(False, '公式6匹配不通过')

        temp_formula = _formula.sub_formula_list[1].sub_formula_list[0].sub_formula_list[0]
        if temp_formula.keyword != 'String' or temp_formula.content_string != '[string begin]kkkaf{$PY=not formula$}dfdf,\\",""haha[string end]':
            # 整个字符串
            self.assertTrue(False, '公式7配不通过')

    def test_formula(self):
        """
        测试公式解析和计算
        """
        # 要解析的公式
        _source_str = '[开始] {$PY=10 + 21$} {$PY=\'[PY1开始]{$ab=[ab开始]testab[时间开始]{$single=$}[时间结束][ab结束]$}} [PY1结束]\'$} "[string 开始]{$PY=string py$} [string 结束]" [结束]'

        # 定义字符串公式的公共关键字参数，例如python中的""引起来的认为是字符串
        _string_para = StructFormulaKeywordPara()
        _string_para.is_string = True  # 声明是字符串参数
        _string_para.has_sub_formula = False  # 声明公式中不会有子公式
        # 在查找字符串结束关键字时忽略的转义情况，例如"this is a string ,ignore \" , this is real end"
        _string_para.string_ignore_chars = ['\\"', '""']

        # 定义单关键字公式的公共参数（没有结束关键字）
        _single_para = StructFormulaKeywordPara()
        _single_para.is_single_tag = True  # 声明是单标签公式关键字

        # 定义公式解析的关键字参数
        _keywords = {
            # 第一个定义了字符串的公式匹配参数
            'String': [
                ['"', list(), list()],  # 公式开始标签
                ['"', list(), list()],  # 公式结束标签
                _string_para  # 公式检索参数
            ],
            'PY': [
                ['{$PY=', list(), list()],  # 公式开始标签
                ['$}', list(), list()],  # 公式结束标签
                StructFormulaKeywordPara()  # 公式检索参数
            ],
            'ab': [
                ['{$ab=', list(), list()],
                ['$}', list(), list()],
                StructFormulaKeywordPara()
            ],
            'Single': [
                ['{$single=$}', list(), list()],
                None,
                _single_para
            ]
        }

        # 定义公式对象处理函数
        _deal_fun_list = {
            'PY': FormulaTool.default_deal_fun_python,  # 执行python语句
            'String': FormulaTool.default_deal_fun_string_content,  # 只保留标签内容
            'ab': formula_deal_fun_test,  # 自定义公式处理函数
            'Single': FormulaTool.default_deal_fun_string_content  # 只保留标签内容
        }

        # 初始化公式类
        _formula_obj = FormulaTool(
            keywords=_keywords,
            ignore_case=False,
            deal_fun_list=_deal_fun_list,
            default_deal_fun=None
        )

        # 计算公式
        _formula = _formula_obj.run_formula_as_string(_source_str)

        # print(_formula.formula_value)

        self.assertTrue(_formula.formula_value ==
                        '[开始] 31 [PY1开始][自定义内容开始][ab开始]testab[时间开始][时间结束][ab结束][自定义内容结束]} [PY1结束] [string 开始]{$PY=string py$} [string 结束] [结束]', '公式计算失败')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
