#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
#  Copyright 2022 黎慧剑
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""The setup.py file for Python HiveNetGRpc."""

import sys
from setuptools import setup, find_packages


LONG_DESCRIPTION = """
HiveNetGRpc is the package of gRpc provided by HiveNetAssemble. It can be easily implemented to be compatible with the server and client of functionsHiveNetWebUtils.server.ServerBaseFW and HiveNetWebUtils.client.ClientBaseFw.

HiveNetGRpc是HiveNetAssemble提供的gRpc的封装, 可以简单实现兼容 HiveNetWebUtils.server.ServerBaseFW 和 HiveNetWebUtils.client.ClientBaseFw 的服务器和客户端功能。
""".strip()

SHORT_DESCRIPTION = """
Simple function application package of gRpc""".strip()

DEPENDENCIES = [
    'HiveNetCore>=0.1.2',
    'HiveNetWebUtils>=0.1.1',
    'grpcio>=1.21.1',
    'grpcio-health-checking>=1.21.1',
    'googleapis-common-protos',
    'grpcio-tools'
]

TEST_DEPENDENCIES = []

VERSION = '0.1.0'
URL = 'https://github.com/snakeclub/HiveNetAssemble/HiveNetGRPC'

setup(
    # pypi中的名称, pip或者easy_install安装时使用的名称
    name="HiveNetGRPC",
    version=VERSION,
    author="黎慧剑",
    author_email="snakeclub@163.com",
    maintainer='黎慧剑',
    maintainer_email='snakeclub@163.com',
    description=SHORT_DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license="Mozilla Public License 2.0",
    keywords="HiveNetAssemble HiveNetGRPC grpc development python lib",
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
    entry_points={'console_scripts': [
        "proto_generate=HiveNetGRPC.proto.proto_generate:main"
    ]},
    # 此项需要, 否则卸载时报windows error
    zip_safe=False
)
