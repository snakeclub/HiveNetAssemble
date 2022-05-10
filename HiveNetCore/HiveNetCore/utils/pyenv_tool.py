#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Python运行环境的工具类

@module pyenv_tool
@file pyenv_tool.py
"""
import sys
import os
import site

__MOUDLE__ = 'pyenv_tool'  # 模块名
__DESCRIPT__ = u'Python运行环境的工具类'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.04.29'  # 发布日期


class PythonEnvTools(object):

    @classmethod
    def get_site_packages_path(cls) -> str:
        """
        获取site_packages所在目录

        @returns {str} - 目录
        """
        return site.getsitepackages()[0]

    @classmethod
    def set_local_packages(cls, name: str, path: str):
        """
        将指定目录设置为本地部署包
        注: 无需安装本机可直接使用

        @param {str} name - 包名
        @param {str} path - 包所在路径(包目录的上一级目录)
        """
        _site_packages_path = cls.get_site_packages_path()
        _content = '# .pth file for the %s extensions\n%s' % (name, path)
        _filename = '%s.pth' % name

        # 写入文件
        with open(os.path.join(_site_packages_path, _filename), 'wb') as _f:
            _f.write(_content.encode('utf-8'))

    @classmethod
    def remove_local_packages(cls, name: str):
        """
        删除本地部署包配置

        @param {str} name - 包名
        """
        _site_packages_path = cls.get_site_packages_path()
        _filename = '%s.pth' % name
        os.remove(os.path.join(_site_packages_path, _filename))


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
                       '    获取site_packages所在目录: python pyenv_tool.py -g',
                       '    将指定目录设置为本地部署包: python pyenv_tool.py -s HiveNetCore "/users/l/path"',
                       '    删除本地部署包配置: python pyenv_tool.py -r HiveNetCore',
                       '直接通过编译后命令方式启动:',
                       '    获取site_packages所在目录: pyenvtool -g',
                       '    ...'
                   ])
               )))
    else:
        # 按命令参数执行
        if '-g' in sys.argv:
            # 获取路径
            print('site_packages: %s' % PythonEnvTools.get_site_packages_path())
        elif '-r' in sys.argv:
            _name = sys.argv[2]
            PythonEnvTools.remove_local_packages(_name)
            print('remove success!')
        elif '-s' in sys.argv:
            _name = sys.argv[2]
            _path = sys.argv[3].strip('"')
            if not os.path.exists(_path):
                print('path not exists: [%s]' % _path)
            else:
                PythonEnvTools.set_local_packages(_name, _path)
                print('set success!')
        else:
            print('run paras error!')
