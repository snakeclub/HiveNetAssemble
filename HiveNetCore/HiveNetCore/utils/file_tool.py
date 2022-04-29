#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
文件处理工具模块

@module file_tool
@file file_tool.py

"""

import sys
import os
import re
from enum import Enum
import platform
import subprocess
import shutil
import hashlib
from io import FileIO
import chardet
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import HiveNetCore.utils.myzipfile as zipfile


__MOUDLE__ = 'file_tool'  # 模块名
__DESCRIPT__ = u'文件处理工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class EnumFileSizeUnit(Enum):
    """
    文件大小单位
    @enum {int}
    """
    B = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024
    TB = 1024 * 1024 * 1024 * 1024


class FileTool(object):
    """
    文件处理工具
    提供各类文件、目录相关的常用工具函数(静态方法)

    """
    @staticmethod
    def is_file_in_subdir(file: str, dir: str) -> bool:
        """
        判断文件是否在指定目录的子目录下
        注: 不判断文件或目录是否存在

        @param {str} file - 文件
        @param {str} dir - 目录

        @returns {bool} - 判断结果
        """
        _real_file = os.path.realpath(file).replace('\\', '/')
        _real_dir = os.path.realpath(dir).replace('\\', '/') + '/'

        return _real_file.startswith(_real_dir)

    @staticmethod
    def get_exefile_fullname():
        """
        获得执行主程序文件名(含路径)

        @returns {string} - 执行主程序文件名(含路径)

        @example
            filepath = FileTool.get_exefile_fullname()

        """
        return os.path.realpath(sys.argv[0])

    @staticmethod
    def get_exefile_name():
        """
        获得执行主程序文件名(不含路径, 含扩展名)

        @returns {string} - 文件名(不含路径, 含扩展名)

        @example
            filepath = FileTool.get_exefile_name()

        """
        return os.path.split(os.path.realpath(sys.argv[0]))[1]

    @staticmethod
    def get_exefile_name_no_ext():
        """
        获得执行主程序文件名(不含路径, 不含扩展名)

        @returns {string} - 文件名(不含路径, 不含扩展名)

        @example
            filepath = FileTool.get_exefile_name_no_ext()

        """
        _filename = os.path.split(os.path.realpath(sys.argv[0]))[1]
        _dot_index = _filename.rfind(".")
        if _dot_index == -1:
            return _filename
        else:
            return _filename[0: _dot_index]

    @staticmethod
    def get_exefile_path():
        """
        获得执行主程序的路径(不含文件名)

        @returns {string} - 程序路径(不含文件名, 最后一个字符不为路径分隔符)

        @example
            filepath = FileTool.get_exefile_path()

        """
        return os.path.split(os.path.realpath(sys.argv[0]))[0]

    @staticmethod
    def get_file_name(file):
        """
        获得执行指定文件的文件名(不含路径, 含扩展名)

        @param {string} file - 文件路径

        @returns {string} - 文件名(不含路径, 含扩展名)
        """
        return os.path.split(os.path.realpath(file))[1]

    @staticmethod
    def get_file_name_no_ext(file):
        """
        获得指定文件的文件名(不含路径, 不含扩展名)

        @param {string} file - 文件路径

        @returns {string} - 文件名(不含路径, 不含扩展名)
        """
        _filename = os.path.split(os.path.realpath(file))[1]
        _dot_index = _filename.rfind(".")
        if _dot_index == -1:
            return _filename
        else:
            return _filename[0: _dot_index]

    @staticmethod
    def get_file_ext(file):
        """
        获得指定文件的扩展名

        @param {string} file - 文件路径

        @returns {string} - 文件扩展名
        """
        _dot_index = file.rfind(".")
        if _dot_index == -1:
            return ''
        else:
            return file[_dot_index + 1:]

    @staticmethod
    def get_file_path(file):
        """
        获得指定文件的路径(不含文件名)

        @param {string} file - 文件路径

        @returns {string} - 程序路径(不含文件名, 最后一个字符不为路径分隔符)

        """
        return os.path.split(os.path.realpath(file))[0]

    @staticmethod
    def get_dir_name(path):
        """
        获取指定目录的目录名

        @param {string} path - 要获取的目录路径

        @returns {string} - 目录名

        """
        _path = os.path.realpath(path).rstrip('\\/').replace('\\', '/')
        _index = _path.rfind('/')
        if _index >= 0:
            return _path[_index + 1:]

        return _path

    @staticmethod
    def create_dir(path, exist_ok=False):
        """
        创建指定的路径

        @param {string} path - 需要创建的路径
        @param {bool} exist_ok=False - 如果路径存在是否不抛异常

        @throws {FileExistsError} - 路径存在的情况抛出文件存在异常

        @example
            FileTool.create_dir("c:/test/")

        """
        os.makedirs(path, exist_ok=exist_ok)

    @staticmethod
    def get_filelist(path='', regex_str='', is_fullname=True):
        """
        获取指定目录下的文件清单

        @param {string} path='' - 需要获取文件的目录
        @param {string} regex_str='' - 需匹配文件名的正则表达式(''代表无需匹配)
        @param {bool} is_fullname=True - 结果的文件名是否包含路径

        @returns {string[]} - 文件清单数组

        @example
            filelist = FileTools.get_filelist(path='c:\\')

        """
        _filelist = []
        _file_names = os.listdir(path)
        _pattern = None
        if len(regex_str) > 0:
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            _full_filename = os.path.join(path, fn)
            if os.path.isfile(_full_filename):
                _temp_filename = fn
                if is_fullname:
                    _temp_filename = _full_filename
                if _pattern is not None:
                    if _pattern.match(fn):
                        _filelist.append(_temp_filename)
                else:
                    _filelist.append(_temp_filename)
        return _filelist

    @staticmethod
    def get_dirlist(path='', regex_str='', is_fullpath=True):
        """
        获取指定目录下的子目录清单

        @param {string} path='' - 需要获取子目录的目录
        @param {string} regex_str='' - 需匹配目录名的正则表达式(''代表无需匹配)
        @param {bool} is_fullpath=True - 结果的目录名是否包含路径

        @returns {string[]} - 目录清单数组(不带最后的分隔符)

        @throws {FileNotFoundError} - 当path不存在的情况下, 会抛出该异常

        """
        _dirlist = []
        _file_names = os.listdir(path)
        _pattern = None
        if regex_str != "":
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            _full_filename = os.path.join(path, fn)
            if not os.path.isfile(_full_filename):
                _temp_filename = fn
                if is_fullpath:
                    _temp_filename = _full_filename
                if _pattern is not None:
                    if _pattern.match(fn):
                        _dirlist.append(_temp_filename)
                else:
                    _dirlist.append(_temp_filename)
        return _dirlist

    @staticmethod
    def get_parent_dir(path):
        """
        获取指定路径或文件的上级路径

        @param {str} path - 路径或文件

        @retrun {str} - 上级路径
        """
        return os.path.abspath(os.path.join(path, '..'))

    @staticmethod
    def remove_dir(path):
        """
        删除指定目录(及目录下的所有文件及目录)
        由于Windows平台在处理删除目录时会存在一些权限异常, 因此采用命令执行方式删除

        @param {string} path - 要删除的目录

        @throws {FileNotFoundError} - 找不到指定的路径时抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常
        @throws {NotADirectoryError} - 如果给出的路径不是目录而是文件时抛出

        """
        if platform.system() == 'Windows':
            real_path = os.path.realpath(path)
            if not os.path.exists(real_path):
                raise FileNotFoundError
            elif os.path.isfile(real_path):
                raise NotADirectoryError
            if subprocess.run('rmdir /S /Q %s' % (real_path.replace('/', '\\')), shell=True).returncode != 0:
                raise PermissionError
        else:
            shutil.rmtree(path=path, ignore_errors=False)

    @staticmethod
    def remove_file(filename):
        """
        删除指定文件

        @param {string} filename - 需要删除的文件路径

        @throws {FileNotFoundError} - 路径不是文件或文件不存在时抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常

        """
        if os.path.isfile(filename):
            os.remove(filename)
        else:
            raise FileNotFoundError

    @staticmethod
    def remove_sub_dirs(path='', regex_str=''):
        """
        删除指定目录下的子目录(及子目录下的文件和目录)

        @param {string} path='' - 需要删除的子目录的目录
        @param {string} regex_str='' - 需匹配目录名的正则表达式(''代表无需匹配)

        @throws {FileNotFoundError} - 当path不存在的情况下, 会抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常
        @throws {NotADirectoryError} - 如果给出的路径不是目录而是文件时抛出

        """
        _dirs = FileTool.get_dirlist(path=path, regex_str=regex_str, is_fullpath=True)
        for _dir in _dirs:
            FileTool.remove_dir(_dir)

    @staticmethod
    def remove_files(path='', regex_str=''):
        """
        删除指定目录下的文件

        @param {string} path='' - 需要删除的文件的目录
        @param {string} regex_str='' - 需匹配文件名的正则表达式(''代表无需匹配)

        @throws {FileNotFoundError} - 当path不存在的情况下, 会抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常
        @throws {NotADirectoryError} - 如果给出的路径不是目录而是文件时抛出

        """
        _files = FileTool.get_filelist(path=path, regex_str=regex_str, is_fullname=True)
        for _file in _files:
            FileTool.remove_file(_file)

    @staticmethod
    def remove_all_with_path(path='', regex_str='', with_sub_path=False):
        """
        删除指定文件夹下的所有文件及文件夹

        @param {string} path='' - 要处理的文件夹
        @param {string} regex_str='' - 文件名匹配的正则表达式
        @param {bool} with_sub_path=False - 是否包含子目录
        """
        _pattern = None
        if regex_str != "":
            _pattern = re.compile(regex_str)

        _path = os.path.realpath(path)
        _file_names = os.listdir(_path)

        for fn in _file_names:
            _match = True
            if _pattern is not None:
                if not _pattern.match(fn):
                    # 没有匹配上
                    _match = False

            _full_filename = os.path.join(_path, fn)
            if os.path.isfile(_full_filename):
                if _match:
                    # 匹配上删除文件
                    FileTool.remove_file(_full_filename)
            else:
                if _match:
                    # 匹配上, 直接删除文件夹
                    FileTool.remove_dir(_full_filename)
                elif with_sub_path:
                    # 处理子文件夹
                    FileTool.remove_all_with_path(
                        path=_full_filename, regex_str=regex_str, with_sub_path=with_sub_path
                    )

    @staticmethod
    def copy_all_with_path(src_path='', dest_path='', regex_str='', exist_ok=False):
        """
        复制指定文件夹下的所有文件及文件夹到目标文件夹

        @param {string} src_path='' - 源文件夹
        @param {string} dest_path='' - 目标文件夹
        @param {string} regex_str='' - 文件名匹配的正则表达式
        @param {bool} exist_ok=Fasle - 遇到文件存在的情况忽略错误

        """
        _pattern = None
        _dest_path = os.path.realpath(dest_path)
        _src_path = os.path.realpath(src_path)
        _file_names = os.listdir(_src_path)
        if regex_str != "":
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            if _pattern is not None:
                if not _pattern.match(fn):
                    # 获取下一个
                    continue

            _full_filename = os.path.join(_src_path, fn)
            _full_destname = os.path.join(_dest_path, fn)
            if os.path.isfile(_full_filename):
                # 复制文件
                if not exist_ok and os.path.exists(_full_destname):
                    raise FileExistsError('file exists: %s' % _full_destname)
                else:
                    # 先创建目录
                    FileTool.create_dir(os.path.split(_full_destname)[0], exist_ok=True)
                    shutil.copyfile(_full_filename, _full_destname)
            else:
                # 复制文件夹, 先创建文件夹
                FileTool.create_dir(_full_destname, exist_ok=True)
                # 递归复制文件夹
                FileTool.copy_all_with_path(
                    src_path=_full_filename, dest_path=_full_destname, exist_ok=exist_ok
                )

    #############################
    # 文件内容处理
    #############################
    @staticmethod
    def get_file_text(filename, encoding='utf-8'):
        """
        获取文件文本

        @param {string} filename - 要获取的文件名(含路径)
        @param {string} encoding='utf-8' - 文件内容的编码
            注: 如果将encoding设置为None, 将使用chardet判断编码

        @return {string} - 返回全部文件内容
        """
        if encoding is not None:
            with open(filename, 'rt', encoding=encoding) as f:
                return f.read()
        else:
            # 使用chardet判断编码
            with open(filename, 'rb') as f:
                _bytes = f.read()
                _encoding = chardet.detect(_bytes)['encoding']
                if _encoding is None:
                    _encoding = 'utf-8'
                elif _encoding.startswith('ISO-8859'):
                    _encoding = 'gbk'
                return str(_bytes, encoding=_encoding)

    @staticmethod
    def create_fix_size_file(filename: str, size: int, unit=EnumFileSizeUnit.B):
        """
        生成指定大小的文件

        @param {str} filename - 要生成的文件
        @param {int} size - 大小
        @param {EnumFileSizeUnit} unit=EnumFileSizeUnit.B - 单位
        """
        with open(filename, 'w') as _file:
            _real_size = size * unit.value
            _file.truncate(_real_size)  # 对于已存在的文件, 有可能比较大, 要进行截断处理
            _file.seek(_real_size - 1)   # 跳到指定位置
            _file.write('\x00')  # 一定要写入一个字符, 否则无效
            _file.flush()

    @staticmethod
    def write_bytes_to_file(filename: str, data: bytes, position=0, file_obj=None):
        """
        在文件指定位置写入字节数组

        @param {str} filename - 要写入的文件
        @param {bytes} data - 写入数据
        @param {int} position=0 - 写入位置
        @param {object} file_obj=None - 已打开的文件对象, 如果传入则代表使用该文件对象执行文件处理
        """
        if file_obj is not None:
            # 使用文件对象处理
            file_obj.seek(position)
            file_obj.write(bytes)
            file_obj.flush()
        else:
            with open(filename, 'wb') as _file:
                _file.seek(position)
                _file.write(bytes)
                _file.flush()

    #############################
    # zip文件处理
    #############################
    @staticmethod
    def zip(src_path, dest_path=None, dest_filename=None, mode='w',
            compression=zipfile.ZIP_DEFLATED, allowZip64=True, pwd=None, **kwargs):
        """
        压缩指定文件或路径

        @param {string} src_path - 要压缩的文件或目录
        @param {string} dest_path=None - 处理后的压缩包存放路径, None代表存放在src_path所在的目录下
        @param {string} dest_filename=None - 处理后的压缩包文件名, None代表使用对应的文件或目录名(增加.zip)
        @param {string} mode='w' - 打开zip文件的模式
            'w' - 表示新建一个zip文档或覆盖一个已经存在的zip文档
            'a' - 表示将数据附加到一个现存的zip文档中
        @param {int} compression=zipfile.ZIP_DEFLATED - 压缩方法, 可以选的值包括:
            zipfile.ZIP_STORED = 0 - 仅打包存储(不压缩)
            zipfile.ZIP_DEFLATED = 8 - 压缩存储
        @param {bool} allowZip64=True - 当要处理的压缩包大于2G时, 建议打开该开关
        @param {bytes} pwd=None - 解压密码(该密码设置无效)
            示例: pwd='123456'.encode('utf-8')
        @param {kwargs} - 动态参数, 支持后续兼容性的扩展

        @throws {FileNotFoundError} - src_path指定的文件或目录不存在时抛出该异常
        """
        if not os.path.exists(src_path):
            raise FileNotFoundError('file or dir [%s] not found!' % src_path)

        # 处理目标文件路径
        _src_realpath = os.path.realpath(src_path)
        _src_path, _src_file = os.path.split(_src_realpath)
        if dest_path is None:
            dest_path = _src_path
        else:
            # 尝试先创建目录
            FileTool.create_dir(dest_path, exist_ok=True)

        if dest_filename is None:
            dest_filename = _src_file + '.zip'

        # 创建zip文件
        _zip = zipfile.ZipFile(os.path.join(dest_path, dest_filename), mode=mode,
                               compression=compression, allowZip64=allowZip64)

        # 设置密码
        if pwd is not None:
            _zip.setpassword(pwd)

        if os.path.isfile(src_path):
            # 文件
            _zip.write(os.path.realpath(src_path), _src_file)
        else:
            # 遍历目录并写入文件
            _src_realpath = _src_realpath.replace('\\', '/')
            for root, dirs, files in os.walk(src_path):
                # 获取相对路径
                _abs_path = os.path.realpath(root).replace('\\', '/').replace(_src_realpath, '', 1)

                # 确保相对路径不能是'/'开头, 否则解压检索的文件信息会有问题
                if len(_abs_path) > 0 and _abs_path[0] == '/':
                    _abs_path = _abs_path[1:]

                if len(files) == 0:
                    # 空目录, 写入目录信息
                    _zip.writestr('./' + _abs_path + '/', '')

                # 写入文件
                for _filename in files:
                    _zip.write(
                        os.path.join(root, _filename),
                        os.path.join('./', _abs_path, _filename)
                    )

        # 保存压缩包
        _zip.close()

    @staticmethod
    def unzip(filename, dest_path=None, members=None, pwd=None, **kwargs):
        """
        解压缩文件到指定路径

        @param {string} filename - 要解压缩的文件
        @param {string} dest_path=None - 解压后目标路径
            注: 为None时解压至文件所在路径, 放入与文件名(去掉扩展名)相同的目录中
        @param {tuple|list}} members=None - 指定单独解压的文件清单(注意路径分隔符为'/'), 不支持解压缩指定目录
            示例: members=['a.txt', 'path/b.txt']
        @param {bytes} pwd=None - 解压密码
            示例: pwd='123456'.encode('utf-8')
        @param {kwargs} - 动态参数, 支持后续兼容性的扩展

        @throws {FileNotFoundError} - src_path指定的文件或目录不存在时抛出该异常
        """
        if not os.path.exists(filename):
            raise FileNotFoundError('file [%s] not found!' % filename)

        # 处理路径
        _src_path, _src_file = os.path.split(os.path.realpath(filename))
        if dest_path is None:
            _file_no_ext = _src_file
            _dot_index = _file_no_ext.rfind(".")
            if _dot_index != -1:
                _file_no_ext = _file_no_ext[0: _dot_index]
            dest_path = _src_path + '/' + _file_no_ext

        # 读取文件
        _zip = zipfile.ZipFile(filename)
        _zip.extractall(dest_path, members=members, pwd=pwd)
        _zip.close()

    @staticmethod
    def read_zip_file(filename, member, pwd=None, **kwargs):
        """
        读取压缩包中的某个文件的二进制数据

        @param {string} filename - 要处理的压缩文件
        @param {string} member - 要读取的包内文件名
        @param {bytes} pwd=None - 解压密码
            示例: pwd='123456'.encode('utf-8')
        @param {kwargs} - 动态参数, 支持后续兼容性的扩展

        @return {bytes} - 读取到文件的二进制数据

        @throws {FileNotFoundError} - src_path指定的文件或目录不存在时抛出该异常
        """
        if not os.path.exists(filename):
            raise FileNotFoundError('file [%s] not found!' % filename)

        # 读取文件
        _zip = zipfile.ZipFile(filename)
        _bytes = _zip.read(member, pwd=pwd)
        _zip.close()
        return _bytes

    @staticmethod
    def is_zip_encrypted(filename: str, **kwargs) -> bool:
        """
        判断压缩文件是否已加密

        @param {string} filename - 压缩文件

        @returns {bool} - 压缩文件是否已加密
        """
        if not os.path.exists(filename):
            raise FileNotFoundError('file [%s] not found!' % filename)

        # 读取信息
        _zip = zipfile.ZipFile(filename)
        for _zinfo in _zip.infolist():
            _is_encrypted = _zinfo.flag_bits & 0x1
            if _is_encrypted:
                return True
            else:
                return False

        return False

    #############################
    # 目录比较功能
    #############################

    @classmethod
    def get_file_md5(self, file, buffer_size: int = 4096):
        """
        获取文件md5值

        @param {str|FileIO|bytes]} file - 文件路径, 或已打开的文件对象, 或文件字节数组
        """
        _md5 = hashlib.md5()  # 创建md5对象

        if type(file) == str:
            # 传入的是文件路径
            with open(file, 'rb') as _f:
                while True:
                    _data = _f.read(buffer_size)
                    if not _data:
                        break
                    _md5.update(_data)  # 更新md5对象
        elif type(file) == FileIO:
            while True:
                _data = file.read(buffer_size)
                if not _data:
                    break
                _md5.update(_data)  # 更新md5对象
        else:
            # 字节
            _md5.update(file)

        return _md5.hexdigest()  # 返回md5对象

    @classmethod
    def cmp_file(cls, file1: str, file2: str) -> bool:
        """
        比较两个文件内容是否一致

        @param {str} file1 - 待比较文件1
        @param {str} file2 - 待比较文件2

        @returns {bool} - 比较结果, 相同返回True
        """
        # 比较文件大小
        if os.path.getsize(file1) != os.path.getsize(file2):
            return False

        # 比较文件md5值
        if cls.get_file_md5(file1) != cls.get_file_md5(file2):
            return False

        return True

    @classmethod
    def cmp_dir(cls, dir1: str, dir2: str, is_cmp_file_content: bool = False, is_sort: bool = False) -> dict:
        """
        比较两个目录

        @param {str} dir1 - 待比较目录1
        @param {str} dir2 - 待比较目录2
        @param {bool} is_cmp_file_content=False - 是否比较文件内容
        @param {bool} is_sort=False - 是否对结果排序

        @returns {dict} - 比较结果, 格式如下:
            {
                'dir1_only_dir': [...目录清单],  # 目录1独有的目录
                'dir1_only_file': [...文件清单],  # 目录1独有的文件
                'dir2_only_dir': [...目录清单],  # 目录2独有的目录
                'dir2_only_file': [...文件清单],  # 目录2独有的文件
                'diff': [...文件清单],  # 双方公用但内容不一致的文件清单
            }
        """
        _cmp_dict = {
            'dir1_only_dir': [], 'dir1_only_file': [], 'dir2_only_dir': [], 'dir2_only_file': [],
            'diff': []
        }
        # 获取文件和目录清单, 以数据比较的方式得到差异
        _dir1_list = cls.get_all_list_by_path(dir1)
        _dir2_list = cls.get_all_list_by_path(dir2)

        # 差集
        _cmp_dict['dir1_only_dir'] = list(set(_dir1_list['dir']).difference(set(_dir2_list['dir'])))
        _cmp_dict['dir1_only_file'] = list(set(_dir1_list['file']).difference(set(_dir2_list['file'])))
        _cmp_dict['dir2_only_dir'] = list(set(_dir2_list['dir']).difference(set(_dir1_list['dir'])))
        _cmp_dict['dir2_only_file'] = list(set(_dir2_list['file']).difference(set(_dir1_list['file'])))

        # 文件比较
        if is_cmp_file_content:
            # 相同的文件清单
            _file_list = list(set(_dir1_list['file']).intersection(set(_dir2_list['file'])))
            for _file in _file_list:
                # 逐个文件比较
                if not cls.cmp_file(os.path.join(dir1, _file), os.path.join(dir2, _file)):
                    _cmp_dict['diff'].append(_file)

        # 排序
        if is_sort:
            _cmp_dict['dir1_only_dir'].sort()
            _cmp_dict['dir1_only_file'].sort()
            _cmp_dict['dir2_only_dir'].sort()
            _cmp_dict['dir2_only_file'].sort()
            _cmp_dict['diff'].sort()

        # 返回比较结果
        return _cmp_dict

    @classmethod
    def get_all_list_by_path(cls, path: str, prefix_path: str = '', is_sort: bool = False) -> dict:
        """
        从指定路径获取文件和目录清单

        @param {str} path - 要获取清单的路径
        @param {str} prefix_path='' - 前缀路径, 自动合并到列表中的目录或文件前面
        @param {bool} is_sort=False - 是否对结果排序

        @returns {dict} - 结果字典:
            {
                'dir': [],  # 目录清单
                'file': [],  # 文件清单
            }
            注: 清单中的路径不包含path部分
        """
        _list_dict = {
            'dir': [], 'file': []
        }
        # 获取清单
        _file_names = os.listdir(path)
        for _fn in _file_names:
            _full_name = os.path.join(path, _fn)
            if os.path.isfile(_full_name):
                # 是文件, 直接添加就好
                _list_dict['file'].append('%s%s' % (prefix_path, _fn))
            else:
                # 是路径, 除添加自己, 还要递归处理目录下的文件
                _list_dict['dir'].append('%s%s' % (prefix_path, _fn))
                _prefix_path = '%s%s/' % (prefix_path, _fn)
                _sub_list = cls.get_all_list_by_path(_full_name, prefix_path=_prefix_path)
                _list_dict['file'].extend(_sub_list['file'])
                _list_dict['dir'].extend(_sub_list['dir'])

        # 对结果排序
        if is_sort:
            _list_dict['dir'].sort()
            _list_dict['file'].sort()

        # 返回结果
        return _list_dict


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
