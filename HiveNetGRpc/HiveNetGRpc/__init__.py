#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

__all__ = [
    'extend_router', 'pipeline'
]

import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
