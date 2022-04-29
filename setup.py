#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
#  Copyright 2022 黎慧剑
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""The setup.py file for Python HiveNetAssemble."""

import sys
from setuptools import setup, find_packages


LONG_DESCRIPTION = """
Hivenetassemble is a set of Python libraries convenient for developers to use. It aims to enable developers to realize the most commonly used functions in the simplest way, improve development efficiency, and pay attention to specific function logic rather than specific technical implementation.

HiveNetAssemble 一组方便开发人员使用的Python库集合, 旨在让开发人员用最简单的方法实现最常用的功能, 提高开发效率, 关注具体功能逻辑而非具体技术实现。
""".strip()

SHORT_DESCRIPTION = """
A collection of Python libraries that are easy for developers to use.""".strip()

DEPENDENCIES = [
    'HiveNetCore'
]

TEST_DEPENDENCIES = []

VERSION = '0.1.0'
URL = 'https://github.com/snakeclub/HiveNetAssemble'

setup(
    # pypi中的名称, pip或者easy_install安装时使用的名称
    name="HiveNetAssemble",
    version=VERSION,
    author="黎慧剑",
    author_email="snakeclub@163.com",
    maintainer='黎慧剑',
    maintainer_email='snakeclub@163.com',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license="Mozilla Public License 2.0",
    keywords="HiveNetAssemble development python lib",
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
        'Programming Language :: Python :: 3.6+',
        'Topic :: Software Development :: Libraries'
    ],
    # 此项需要, 否则卸载时报windows error
    zip_safe=False
)
