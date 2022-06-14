#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
#  Copyright 2022 黎慧剑
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""The setup.py file for Python HiveNetPromptPlus."""

import sys
from setuptools import setup, find_packages


LONG_DESCRIPTION = """
HiveNetPromptPlus is an enhanced interactive command line extension processing module provided by HiveNetAssemble.

HiveNetPromptPlus是HiveNetAssemble提供的增强的交互命令行扩展处理模块。
""".strip()

SHORT_DESCRIPTION = """
An enhanced interactive command line extension processing module.""".strip()

DEPENDENCIES = [
    'HiveNetCore>=0.1.2',
    'prompt-toolkit2'
]

TEST_DEPENDENCIES = []

VERSION = '0.1.0'
URL = 'https://github.com/snakeclub/HiveNetAssemble/HiveNetPromptPlus'

setup(
    # pypi中的名称, pip或者easy_install安装时使用的名称
    name="HiveNetPromptPlus",
    version=VERSION,
    author="黎慧剑",
    author_email="snakeclub@163.com",
    maintainer='黎慧剑',
    maintainer_email='snakeclub@163.com',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license="Mozilla Public License 2.0",
    keywords="HiveNetAssemble HiveNetPromptPlus prompt development python lib",
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
