#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
文件传输库的自定义异常类

@module exceptions
@file exceptions.py
"""


__MOUDLE__ = 'exceptions'  # 模块名
__DESCRIPT__ = u'文件传输库的自定义异常类'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.08.23'  # 发布日期


class InfoFileLockError(Exception):
    """
    信息文件已锁住异常
    """
    pass


class AlreadyKnowFileSizeError(Exception):
    """
    已知文件大小模式异常
    """
    pass


class Md5VerifyError(Exception):
    """
    MD5校验失败
    """
    pass


class TransferFinishedError(Exception):
    """
    文件传输已完成异常
    """
    pass


class FileDataNullError(Exception):
    """
    文件数据为空异常
    """
    pass


class FileDataPosMatchError(Exception):
    """
    文件数据位置匹配异常
    """
    pass


class FileNotUnderWorkDirError(Exception):
    """
    文件不在工作目录下异常
    """
    pass


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
