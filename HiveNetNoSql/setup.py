#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
#  Copyright 2022 黎慧剑
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""The setup.py file for Python HiveNetNoSql."""

import sys
from setuptools import setup, find_packages


LONG_DESCRIPTION = """
HiveNetNoSql is a general NoSQL data access driver framework. Referring to the syntax of MongoDB, it abstracts the data access operations of NoSQL to facilitate the data access of various databases (including relational databases and NoSQL databases) using the same set of NoSQL operations. In this package, the driver adaptation of MongoDB, Sqlite, MySQL and Postgresql is implemented, and the adaptation of other databases can be implemented according to their own needs.

HiveNetNoSql是一个通用的NoSql数据访问驱动框架, 参考MongoDB的语法对NoSql的数据访问操作进行了抽象, 便于对各类数据库(包括关系型数据库和NoSql数据库)采用同一套NoSql操作进行数据访问, 在该包中实现了MongoDB、Sqlite、MySQL、Postgresql的驱动适配, 可以根据自己的需要实现其他数据库的适配实现。
""".strip()

SHORT_DESCRIPTION = """
A general NoSQL data access driver framework.""".strip()

DEPENDENCIES = [
    'HiveNetCore>=0.1.2',
    'bson'
]

TEST_DEPENDENCIES = []

VERSION = '0.1.0'
URL = 'https://github.com/snakeclub/HiveNetAssemble/HiveNetNoSql'

setup(
    # pypi中的名称, pip或者easy_install安装时使用的名称
    name="HiveNetNoSql",
    version=VERSION,
    author="黎慧剑",
    author_email="snakeclub@163.com",
    maintainer='黎慧剑',
    maintainer_email='snakeclub@163.com',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license="Mozilla Public License 2.0",
    keywords="HiveNetAssemble HiveNetNoSql NoSQL driver development python lib",
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
