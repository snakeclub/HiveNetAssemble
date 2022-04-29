#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
依赖包安装工具包
@module deps_tool
@file deps_tool.py
"""

import sys
import subprocess
import json


__MOUDLE__ = 'deps_tool'  # 模块名
__DESCRIPT__ = u'依赖包安装工具包'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.11.30'  # 发布日期


def install_package(package_name: str, force_reinstall: bool = False, dependencies_dict: dict = {}) -> tuple:
    """
    安装指定依赖包

    @param {str} package_name - 要安装的包名(dependencies_dict 中的 key)
        注意: 如果dependencies_dict中没有相应的配置, 会尝试直接使用 package_name 进行安装
    @param {bool} force_reinstall=False - 是否强制重新安装
    @param {dict} dependencies_dict={} - 依赖字典, key为依赖的包名,value为{'install': '实际安装包名和版本要求'}

    @returns {tuple[int, str]} - 安装结果,
        第一位为运行结果,0代表成本,其他代表失败
        第二位为命令安装结果输出内容
    """
    # 获取安装包和版本要求
    _dependencies_dict = dependencies_dict
    _install_name = _dependencies_dict.get(package_name, {}).get('install', package_name)

    _result = subprocess.getstatusoutput(
        'pip install %s%s' % (
            '--force-reinstall ' if force_reinstall else '',
            _install_name
        )
    )
    if _result[0] == 0:
        # 安装成功
        print('安装依赖包 %s 成功' % package_name)
    else:
        # 安装失败
        print('安装依赖包 %s 失败\n%s\n' % (package_name, _result))

    return _result


def install_all(force_reinstall: bool = False, dependencies_dict: dict = {}) -> bool:
    """
    安装所有依赖包

    @param {bool} force_reinstall=False - 是否强制重新安装
    @param {dict} dependencies_dict=None - 依赖字典, key为依赖的包名,value为{'install': '实际安装包名和版本要求'}

    @returns {bool} - 最后安装情况
    """
    _dependencies_dict = dependencies_dict

    _fail_list = []
    for _key in _dependencies_dict.keys():
        _result = install_package(_key, force_reinstall=force_reinstall)
        if _result[0] != 0:
            # 安装失败
            _fail_list.append(_key)

    # 打印最后结果
    if len(_fail_list) > 0:
        print('以下依赖包安装失败: %s' % ', '.join(_fail_list))
        return False
    else:
        return True


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    if len(sys.argv) <= 1:
        # 打印版本信息
        print(('模块名: %s  -  %s\n'
               '作者: %s\n'
               '发布日期: %s\n'
               '版本: %s\n'
               '使用方法:\n%s'
               % (
                   __MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__,
                   '\n'.join([
                       '通过执行python文件的方式启动:',
                       '    安装全部依赖包: python deps_tool.py install -f 依赖字典文件.json',
                       '    安装单个依赖包: python deps_tool.py install flask -f 依赖字典文件.json',
                       '    强制重新安装全部依赖包: python deps_tool.py install --force',
                       '直接通过编译后命令方式启动:',
                       '    安装全部依赖包: depstool install -f 依赖字典文件.json',
                       '    ...'
                   ])
               )))
    else:
        # 按命令参数执行
        _force_reinstall = False
        _package_name = None
        _dependencies_file = None
        _index = 2
        _len = len(sys.argv)
        while _index < _len:
            _opts = sys.argv[_index]
            if _opts == '-f':
                _dependencies_file = sys.argv[_index + 1]
                _index += 1
            elif _opts == '--force':
                _force_reinstall = True
            else:
                if _package_name is None:
                    _package_name = sys.argv[_index]

            # 下一个循环
            _index += 1

        # 从指定的文件获取配置字典
        if _dependencies_file is not None:
            with open(_dependencies_file, 'rb') as _f:
                _dependencies_dict = json.loads(_f.read())
        else:
            _dependencies_dict = {}

        if sys.argv[1] == 'install':
            # 安装依赖包
            if _package_name is not None:
                # 安装单个包
                _package_name = sys.argv[-1]
                install_package(
                    _package_name, force_reinstall=_force_reinstall, dependencies_dict=_dependencies_dict
                )
            else:
                # 安装全部
                install_all(force_reinstall=_force_reinstall, dependencies_dict=_dependencies_dict)
