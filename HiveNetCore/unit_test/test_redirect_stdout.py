#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试重定向标准界面输出的处理模块
@module test_redirect_stdout
@file test_redirect_stdout.py
"""

import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.redirect_stdout import EnumOriginalStdoutWriteType, EnumRedirectOutputHandlerType, RedirectOutputHandler, RedirectOutput
from HiveNetCore.utils.test_tool import TestTool


__MOUDLE__ = 'test_redirect_stdout'  # 模块名
__DESCRIPT__ = u'测试重定向标准界面输出的处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.04'  # 发布日期


class TestRedirectOutput(unittest.TestCase):
    """
    测试RedirectOutput类
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

    def test_redirect_output1(self):
        """
        测试输出重定向
        """
        str1 = '同步模式:输出信息1'
        str2 = '同步模式:输出信息2'
        str3 = '同步模式:输出信息3'

        # 定义重定向对象
        str_obj = ['']
        str_handler = RedirectOutputHandler(
            handler_type=EnumRedirectOutputHandlerType.String,
            output_obj=str_obj,
            is_flush=True
        )

        strlist_obj = list()
        strlist_handler = RedirectOutputHandler(
            handler_type=EnumRedirectOutputHandlerType.StringList,
            output_obj=strlist_obj,
            is_flush=True
        )

        # 定义重定向信息
        redirect_obj = RedirectOutput(
            auto_start=False,
            original_stdout_write_type=EnumOriginalStdoutWriteType.NoWrite,
            output_handlers=(str_handler, strlist_handler)
        )

        # 启动重定向处理
        redirect_obj.start_redirect()

        # 输出信息
        print(str1)
        print(str2)
        print(str3)

        # 关闭重定向处理
        redirect_obj.stop_redirect()

        # 回退到原来的输出
        print('同步模式:非重定向信息，输出信息4')

        # print(str(str_obj))
        # print(str(strlist_obj))

        self.assertTrue(str_obj[0] == '同步模式:输出信息1\n同步模式:输出信息2\n同步模式:输出信息3\n', '同步模式: 字符类型校验失败')
        self.assertTrue(TestTool.cmp_list(strlist_obj, [
                        '同步模式:输出信息1', '\n', '同步模式:输出信息2', '\n', '同步模式:输出信息3', '\n']), '同步模式: 字符列表类型校验失败')

    def test_redirect_output2(self):
        """
        测试异步模式
        """
        str1 = '异步模式:输出信息1'
        str2 = '异步模式:输出信息2'
        str3 = '异步模式:输出信息3'

        # 定义重定向对象
        str_obj = ['']
        str_handler = RedirectOutputHandler(
            handler_type=EnumRedirectOutputHandlerType.String,
            output_obj=str_obj,
            is_flush=True
        )

        strlist_obj = list()
        strlist_handler = RedirectOutputHandler(
            handler_type=EnumRedirectOutputHandlerType.StringList,
            output_obj=strlist_obj,
            is_flush=True
        )

        # 定义重定向信息, 并自动启动输出
        redirect_obj = RedirectOutput(
            auto_start=True,
            original_stdout_write_type=EnumOriginalStdoutWriteType.Before,
            output_handlers=(str_handler, strlist_handler),
            is_asyn=True,
            wait_write_end_when_asyn=True
        )

        # 输出信息
        print(str1)
        print(str2)
        print(str3)

        # 关闭重定向处理
        redirect_obj.stop_redirect()

        # 回退到原来的输出
        print('异步模式:非重定向信息，输出信息4')

        # print(str(str_obj))
        # print(str(strlist_obj))

        self.assertTrue(str_obj[0] == '异步模式:输出信息1\n异步模式:输出信息2\n异步模式:输出信息3\n', '异步模式: 字符类型校验失败')
        self.assertTrue(TestTool.cmp_list(strlist_obj, [
                        '异步模式:输出信息1', '\n', '异步模式:输出信息2', '\n', '异步模式:输出信息3', '\n']), '异步模式: 字符列表类型校验失败')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
