#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
连接池处理框架
(已经迁移到HiveNetCore, 保留模块保证已有的调用模块可继续使用)

@module connection_pool
@file connection_pool.py
"""

import os
import sys
from HiveNetCore.connection_pool import TooManyConnections, AIOConnectionPool, PoolConnectionFW
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


__MOUDLE__ = 'connection_pool'  # 模块名
__DESCRIPT__ = u'连接池处理框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.04.22'  # 发布日期


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
