#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#

"""
测试异常工具
@module test_exception_tool
@file test_exception_tool.py
"""

import sys
import os
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.generic import CResult
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetCore.logging_hivenet import Logger


class TestExcepitonTool(unittest.TestCase):
    """
    测试ExcepitonTool类
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

    def test_method(self):
        """
        测试静态方法
        """
        _logger = Logger()
        _result = CResult('00000')
        _result.net_info = None
        with ExceptionTool.ignored_cresult(
            _result,
            logger=_logger,
            expect=(),
            error_map={ImportError: ('20401', None), BlockingIOError: ('20407', None)},
            self_log_msg='test:',
            force_log_level=None
        ):
            _result.test = 'test'

        self.assertTrue(_result.code == '00000' and _result.test == 'test', 'ok result error')

        _result = CResult('00000')
        with ExceptionTool.ignored_cresult(
            _result,
            logger=_logger,
            expect=(),
            error_map={ImportError: ('20401', None), BlockingIOError: ('20407', None)},
            self_log_msg='test:',
            force_log_level=None
        ):
            raise ImportError

        self.assertTrue(_result.code == '20401',
                        '20401 result error, code:' + _result.code)

        _result = CResult('00000')
        with ExceptionTool.ignored_cresult(
            _result,
            logger=_logger,
            expect=(),
            error_map={ImportError: ('20401', None), BlockingIOError: ('20407', None)},
            self_log_msg='test:',
            force_log_level=None
        ):
            raise BlockingIOError

        self.assertTrue(_result.code == '20407', '20407 result error, code:' + _result.code)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
