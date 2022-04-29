#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# 本模块不执行，用于测试和验证跨模块时的DebugTool行为

import sys
import os
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir
)))
from HiveNetCore.utils.debug_tool import DebugTool


def test_debugtools():
    DebugTool.debug_print("从debug_tool_demo_not_run中的打印信息")
