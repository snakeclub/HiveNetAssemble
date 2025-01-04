#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试MemoryCache
@module test_build
@file test_build.py
"""

import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetBuildTool.build import BuildPipeline


__MOUDLE__ = 'test_build'  # 模块名
__DESCRIPT__ = u'测试构建'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


class TestBuildPipeline(unittest.TestCase):
    """
    测试BuildPipeline类
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

    def test(self):
        """
        测试示例构建
        """
        _demo_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'test_data/build_demo'
        ))
        _build_file = os.path.join(_demo_path, 'build_src/build.yaml')
        _base_path = os.path.join(_demo_path, 'SelfBuildTool')
        _build_pipeline = BuildPipeline(_base_path, build_file=_build_file)
        self.assertTrue(
            _build_pipeline.start_build(), '构建出错'
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
