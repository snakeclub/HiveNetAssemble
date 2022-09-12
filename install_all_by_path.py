#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
通过源码路径安装所有组件

@module install_all_by_path
@file install_all_by_path.py
"""
import os
import subprocess


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _packages = [
        'HiveNetCore',
        'HiveNetWebUtils',
        'HiveNetSimpleSanic',
        'HiveNetSimpleFlask',
        'HiveNetGRpc',
        'HiveNetPipeline',
        'HiveNetPromptPlus',
        'HiveNetConsole',
        'HiveNetFileTransfer',
        'HiveNetNoSql',
        'HiveNetBuildTool'
    ]
    _pyenv_tool_file = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'HiveNetCore/HiveNetCore/utils/pyenv_tool.py'
    ))
    for _package_name in _packages:
        _path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), _package_name
        ))
        _result = subprocess.getstatusoutput(
            'python "%s" -s %s "%s"' % (
                _pyenv_tool_file, _package_name, _path
            )
        )
        if _result[0] == 0:
            # 安装成功
            print('安装包 %s 成功' % _package_name)
        else:
            # 安装失败
            print('安装包 %s 失败\n%s\n' % (_package_name, _result))
            exit(1)
