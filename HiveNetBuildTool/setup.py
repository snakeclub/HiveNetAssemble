#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
#  Copyright 2022 黎慧剑
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""The setup.py file for Python HiveNetBuildTool."""

import sys
from setuptools import setup, find_packages


LONG_DESCRIPTION = """
HiveNetBuildTool is a universal code building tool of HiveNetAssembly. It provides a code extensible code building framework based on the execution of HiveNetPipeline. Different applications can quickly implement custom building logic by developing HiveNetPipeline process plugins.

HiveNetBuildTool是HiveNetAssemble的通用代码构建工具, 基于HiveNetPipeline管道执行的方式提供代码可扩展的代码构建框架, 不同应用可通过开发HiveNetPipeline管道插件的方式快速实现自定义的构建逻辑。
""".strip()

SHORT_DESCRIPTION = """
A universal code building tool.""".strip()

DEPENDENCIES = [
    'HiveNetPipeline>=0.1.0',
]


TEST_DEPENDENCIES = []

VERSION = '0.1.1'
URL = 'https://github.com/snakeclub/HiveNetAssemble/HiveNetBuildTool'

setup(
    # pypi中的名称, pip或者easy_install安装时使用的名称
    name="HiveNetBuildTool",
    version=VERSION,
    author="黎慧剑",
    author_email="snakeclub@163.com",
    maintainer='黎慧剑',
    maintainer_email='snakeclub@163.com',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license="Mozilla Public License 2.0",
    keywords="HiveNetAssemble HiveNetBuildTool development python lib",
    url=URL,
    platforms=["all"],
    # 需要打包的目录列表, 可以指定路径packages=['path1', 'path2', ...]
    packages=find_packages(),
    install_requires=DEPENDENCIES,
    tests_require=TEST_DEPENDENCIES,
    package_data={'': ['*.json', '*.xml', '*.proto']},  # 这里将打包所有的json文件
    classifiers=[
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries'
    ],
    # 此项需要, 否则卸载时报windows error
    zip_safe=False
)
