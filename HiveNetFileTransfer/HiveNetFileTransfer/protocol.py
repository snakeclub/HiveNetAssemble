#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
文件传输协议模块

@module protocol
@file protocol.py
"""

import os
import sys
import threading
from typing import Iterator, Union
from io import FileIO
from HiveNetCore.utils.net_tool import NetTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetFileTransfer.saver import TransferSaver


__MOUDLE__ = 'protocol'  # 模块名
__DESCRIPT__ = u'文件传输协议模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.08.24'  # 发布日期


class ProtocolFw(object):
    """
    文件传输协议框架
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, src_file: str, dest_file: str, is_resume: bool = True, is_overwrite: bool = False,
                 thread_num: int = 1, block_size: int = 4096, cache_size: int = 1024, auto_expand: bool = True,
                 **kwargs):
        """
        初始化文件传输协议类
        注: 实现类必须在初始化中完成目标端 TransferSaver 的初始化处理

        @param {str} src_file - 源文件信息
        @param {str} dest_file - 目标文件信息
        @param {bool} is_resume=True - 指定是否续传(自动查找已下载的信息), 如果不指定续传将自动删除原来已下载临时文件
        @param {bool} is_overwrite=False - 是否覆盖已有文件, 如果为否, 则目标文件已存在的情况下抛出异常
        @param {int} thread_num=1 - 写入处理线程数量
        @param {int} block_size=4096 - 每次传输块大小, 单位为byte
        @param {int} cache_size=1024 - 单线程缓存大小, 单位为kb(注意: 真实缓存大小还需要乘以处理线程数量)
        @param {bool} auto_expand=True - 是否自动扩展文件大小(否则在初始化时会自动创建指定大小的文件)
        @param {kwargs} - 扩展参数, 重载类自行扩展处理所需的参数
        """
        raise NotImplementedError()

    #############################
    # with 方法支持
    #############################
    def __enter__(self):
        """
        with方法进入的处理
        """
        return self

    def __exit__(self, type, value, trace):
        """
        with方法退出函数

        @param {object} type - 执行异常的异常类型
        @param {object} value - 执行异常的异常对象值
        @param {object}} trace - 执行异常的异常trace对象
        """
        # 关闭资源
        self.close()

    #############################
    # 需支持的属性(需继承类实现)
    #############################
    @property
    def file_size(self) -> int:
        """
        获取传输文件大小

        @property {int}
        """
        raise NotImplementedError()

    #############################
    # 工具函数
    #############################

    def pause(self):
        """
        通知协议暂停传输, 保存当前状态
        """
        raise NotImplementedError()

    def close(self):
        """
        关闭传输协议对象
        """
        raise NotImplementedError()

    #############################
    # 文件读取的工具函数(需继承类实现)
    #############################

    def open_file(self, index: int = 0):
        """
        打开文件并返回文件对象

        @param {int} index=0 - 当前的数据处理线程索引

        @returns {dict} - 打开的文件对象属性字典
            {'handle': FileIO, 'close_able': 是否可关闭, lock: 锁对象}
        """
        raise NotImplementedError()

    def close_file(self, index: int, is_force: bool = False):
        """
        关闭打开的文件

        @param {int} index - 要关闭的文件对象对应的处理线程索引
        @param {bool} is_force=False - 指示是否强制关闭
        """
        raise NotImplementedError()

    def read_file_data(self, index: int, handle, start: int, size: int,
                       lock: threading.RLock) -> bytes:
        """
        获取文件指定位置数据

        @param {int} index - 处理读取的线程索引
        @param {object} handle - 打开的文件句柄
        @param {int} start - 要获取的数据开始位置
        @param {int} size - 要获取的数据大小
        @param {threading.RLock} lock - 读取数据的锁对象

        @returns {bytes} - 获取到的数据字典
            注: 如果开始位置超过文件大小, 将返回b''; 如果要获取的数据大小超过文件, 则返回真实的数据大小
                对于无法预知文件大小的情况, 如果返回b''也代表着文件结束
        """
        raise NotImplementedError()

    #############################
    # 写入对象的工具函数(需继承类实现)
    #############################
    def open_writer(self, index: int = 0) -> dict:
        """
        打开写入对象并返回对象属性

        @param {int} index=0 - 当前的数据处理线程索引

        @returns {dict} - 打开的文件对象属性字典
            {'handle': 写入对象, 'close_able': 是否可关闭, lock: 锁对象}
        """
        raise NotImplementedError()

    def close_writer(self, index: int, is_force: bool = False):
        """
        关闭打开的写入对象

        @param {int} index - 要关闭的写入对象对应的处理线程索引
        @param {bool} is_force=False - 指示是否强制关闭
        """
        raise NotImplementedError()

    def write_data(self, handle, lock: threading.RLock, index: int = 0, start: int = None,
                   size: int = None, data: bytes = None) -> dict:
        """
        写入文件数据

        @param {object} handle - 写入对象
        @param {threading.RLock} lock - 锁定写入操作的锁对象
        @param {int} index=0 - 指定写入数据的线程索引
        @param {int} start=None - 数据在文件的开始位置, 如果传空代表请求该线程索引对应的获取任务信息
        @param {int} size=None - 传入数据的长度
        @param {bytes} data=None - 传入数据字节数组

        @returns {dict} - 返回下一个任务要获取的信息字典, 格式为:
            {
                'status': 0,  # 状态, 0-成功, 1-开始位置与线程缓存不一致, 2-全部下载完成, 3-文件md5校验失败
                'index': 0,  # 当前线程索引
                'start': -1,  # 开始位置, 如果传入-1代表该线程已无获取任务
                'size': 0,  # 要获取数据的大小
            }
        """
        raise NotImplementedError()

    def file_finished(self):
        """
        通知数据保存对象文件已结束
        """
        raise NotImplementedError()

    def flush_cache(self):
        """
        强制将缓存数据写入实际文件
        """
        raise NotImplementedError()

    def get_thread_num(self) -> int:
        """
        获取支持处理的线程数

        @returns {int} - 线程数
        """
        raise NotImplementedError()

    def get_saver_info(self) -> dict:
        """
        获取数据保存信息

        @returns {dict} - 已保存的信息字典
            {
                'file_size': -1,  # 要接收的文件大小, -1 代表不确定文件实际大小
                'write_size': 0,  # 已写入的数据大小
                'md5': '',  # 文件的md5值
            }
        """
        raise NotImplementedError()

    def get_extend_info(self) -> dict:
        """
        获取保存的扩展信息字典

        @returns {dict} - 返回保存的扩展信息字典
        """
        raise NotImplementedError()


class LocalProtocol(ProtocolFw):
    """
    本地文件传输至本地的传输协议(复制)
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, src_file: Union[str, FileIO], dest_file: str, is_resume: bool = True, is_overwrite: bool = False,
                 thread_num: int = 1, block_size: int = 4096, cache_size: int = 1024, auto_expand: bool = True,
                 **kwargs):
        """
        初始化文件传输协议类
        注: 实现类必须在初始化中完成目标端 TransferSaver 的初始化处理

        @param {str|FileIO} src_file - 源文件路径或已打开的文件句柄
        @param {str} dest_file - 目标文件路径
        @param {bool} is_resume=True - 指定是否续传(自动查找已下载的信息), 如果不指定续传将自动删除原来已下载临时文件
        @param {bool} is_overwrite=False - 是否覆盖已有文件, 如果为否, 则目标文件已存在的情况下抛出异常
        @param {int} thread_num=1 - 写入处理线程数量
        @param {int} block_size=4096 - 每次传输块大小, 单位为byte
        @param {int} cache_size=1024 - 单线程缓存大小, 单位为kb(注意: 真实缓存大小还需要乘以处理线程数量)
        @param {bool} auto_expand=True - 是否自动扩展文件大小(否则在初始化时会自动创建指定大小的文件)
        @param {kwargs} - 扩展参数, 重载类自行扩展处理所需的参数
        """
        # 要保存的参数
        self.src_file = src_file
        self.dest_file = dest_file
        self.is_resume = is_resume
        self.is_overwrite = is_overwrite
        self.thread_num = thread_num
        self.block_size = block_size
        self.cache_size = cache_size
        self.auto_expand = auto_expand
        self.kwargs = kwargs

        # 文件访问句柄字典, 供open_file处理使用, key为处理线程索引, value为{'handle': ..., 'close_able':..., lock: ...}
        self._file_handles = dict()
        self._file_handles_lock = threading.RLock()  # 控制打开关闭文件的锁
        self._mutiple_read = False  # 控制是否允许多线程读的变量

        # 写入对象字典, 供open_writer处理使用, key为处理线程索引, value为{'handle': ..., 'close_able':..., lock: ...}
        self._writer_handles = dict()
        self._writer_handles_lock = threading.RLock()  # 控制打开关闭文件的锁
        self._mutiple_write = False  # 控制是否允许多线程写的变量

        # 初始化数据接收对象
        self.init_saver()

    #############################
    # 需支持的属性(需继承类实现)
    #############################
    @property
    def file_size(self) -> int:
        """
        获取传输文件大小

        @property {int}
        """
        return self._file_size

    #############################
    # 工具函数
    #############################

    def pause(self):
        """
        通知协议暂停传输, 保存当前状态
        """
        self.flush_cache()

    def close(self):
        """
        关闭传输协议对象
        """
        # 销毁数据接收对象
        self.destroy_saver()

        # 关闭写入对象
        _keys = list(self._writer_handles.keys())
        for _index in _keys:
            self.close_writer(_index, is_force=True)

        # 关闭文件
        if type(self.src_file) == str:
            _keys = list(self._file_handles.keys())
            for _index in _keys:
                self.close_file(_index, is_force=True)

    #############################
    # 文件读取的工具函数
    #############################

    def get_file_size(self) -> int:
        """
        获取文件的大小

        @returns {int} - 文件大小, 如果不支持获取文件大小返回 None
        """
        if type(self.src_file) == str:
            return os.path.getsize(self.src_file)
        else:
            # 移动指针到文件结尾, 指针位置就是文件大小
            return self.src_file.seek(0, 2)

    def get_file_md5(self) -> str:
        """
        获取文件的md5值

        @returns {str} - 文件md5值, 如果获取不到md5值返回None
        """
        return NetTool.get_file_md5(self.src_file)

    #############################
    # 文件读取的工具函数(需继承类实现)
    #############################
    def open_file(self, index: int = 0):
        """
        打开文件并返回文件对象

        @param {int} index=0 - 当前的数据处理线程索引

        @returns {dict} - 打开的文件对象属性字典
            {'handle': FileIO, 'close_able': 是否可关闭, lock: 锁对象}
        """
        self._mutiple_read = False
        if type(self.src_file) != str:
            # FileIO 的对象不允许多线程读
            self._mutiple_read = False

        self._file_handles_lock.acquire()
        try:
            # 获取文件对象属性字典
            if self._mutiple_read:
                # 允许多线程读访问
                _file_dict = self._file_handles.get(index, None)
                if _file_dict is None:
                    # 获取不到, 创建新文件访问对象
                    _lock = threading.RLock()
                    _file_dict = {
                        'handle': open(self.src_file, 'rb'), 'close_able': True, 'lock': _lock
                    }
                    self._file_handles[index] = _file_dict
            else:
                # 单线程读写模式, 只允许访问第0个, 并且文件不允许关闭
                _file_dict = self._file_handles.get(0, None)
                if _file_dict is None:
                    _lock = threading.RLock()
                    if type(self.src_file) == str:
                        # 文件路径
                        _file_dict = {
                            'handle': open(self.src_file, 'rb'), 'close_able': False, 'lock': _lock
                        }
                    else:
                        _file_dict = {
                            'handle': self.src_file, 'close_able': False, 'lock': _lock
                        }
                    self._file_handles[0] = _file_dict
        finally:
            self._file_handles_lock.release()

        # 返回结果
        return _file_dict

    def close_file(self, index: int, is_force: bool = False):
        """
        关闭打开的文件

        @param {int} index - 要关闭的文件对象对应的处理线程索引
        @param {bool} is_force=False - 指示是否强制关闭
        """
        self._file_handles_lock.acquire()
        try:
            _file_dict = self._file_handles.get(index, None)
            if _file_dict is not None and (is_force or _file_dict['close_able']):
                # 允许关闭或强制关闭
                self._file_handles.pop(index, None)
                _file_dict['handle'].close()
        finally:
            self._file_handles_lock.release()

    def read_file_data(self, index: int, handle: FileIO, start: int, size: int,
                       lock: threading.RLock) -> bytes:
        """
        获取文件指定位置数据

        @param {int} index - 处理读取的线程索引
        @param {object} handle - 打开的文件句柄
        @param {int} start - 要获取的数据开始位置
        @param {int} size - 要获取的数据大小
        @param {threading.RLock} lock - 读取数据的锁对象

        @returns {bytes} - 获取到的数据字典
            注: 如果开始位置超过文件大小, 将返回b''; 如果要获取的数据大小超过文件, 则返回真实的数据大小
                对于无法预知文件大小的情况, 如果返回b''也代表着文件结束
        """
        lock.acquire()
        try:
            # 移动到指定位置并获取数据
            handle.seek(start)
            _bytes = handle.read(size)

            return _bytes
        finally:
            lock.release()

    #############################
    # 写入对象的工具函数
    #############################
    def init_saver(self):
        """
        初始化数据保存对象
        """
        # 处理源文件信息
        self._file_size = self.get_file_size()
        self._file_md5 = self.get_file_md5()

        # 处理文件传输接收对象
        self._saver = TransferSaver(
            self.dest_file, is_resume=self.is_resume, file_size=self._file_size, md5=self._file_md5,
            is_overwrite=self.is_overwrite, thread_num=self.thread_num, block_size=self.block_size,
            cache_size=self.cache_size, auto_expand=self.auto_expand
        )
        self.thread_num = self._saver._thread_num  # 线程数有可能被改变

    def destroy_saver(self):
        """
        销毁接收数据对象
        """
        # 写入缓存并删除对象
        self._saver.close()

    #############################
    # 写入对象的工具函数(需继承类实现)
    #############################
    def open_writer(self, index: int = 0) -> dict:
        """
        打开写入对象并返回对象属性

        @param {int} index=0 - 当前的数据处理线程索引

        @returns {dict} - 打开的文件对象属性字典
            {'handle': 写入对象, 'close_able': 是否可关闭, lock: 锁对象}
        """
        # 本地文件无需特别处理, 直接返回None就好
        return {'handle': None, 'close_able': False, 'lock': None}

    def close_writer(self, index: int, is_force: bool = False):
        """
        关闭打开的写入对象

        @param {int} index - 要关闭的写入对象对应的处理线程索引
        @param {bool} is_force=False - 指示是否强制关闭
        """
        # 本地文件无需特别处理
        pass

    def write_data(self, handle, lock: threading.RLock, index: int = 0, start: int = None,
                   size: int = None, data: bytes = None) -> dict:
        """
        写入文件

        @param {object} handle - 写入对象
        @param {threading.RLock} lock - 锁定写入操作的锁对象
        @param {int} index=0 - 指定写入数据的线程索引
        @param {int} start=None - 数据在文件的开始位置, 如果传空代表请求该线程索引对应的获取任务信息
        @param {int} size=None - 传入数据的长度
        @param {bytes} data=None - 传入数据字节数组

        @returns {dict} - 返回下一个任务要获取的信息字典, 格式为:
            {
                'status': 0,  # 状态, 0-成功, 1-开始位置与线程缓存不一致, 2-全部下载完成, 3-文件md5校验失败
                'index': 0,  # 当前线程索引
                'start': -1,  # 开始位置, 如果传入-1代表该线程已无获取任务
                'size': 0,  # 要获取数据的大小
            }
        """
        # 本地文件模式, 无需使用handle和lock参数
        return self._saver.write_data(
            index=index, start=start, size=size, data=data
        )

    def file_finished(self):
        """
        通知数据保存对象文件已结束
        """
        self._saver.finished()

    def flush_cache(self):
        """
        强制将缓存数据写入实际文件
        """
        self._saver.flush()

    def get_thread_num(self) -> int:
        """
        获取支持处理的线程数

        @returns {int} - 线程数
        """
        return self.thread_num

    def get_saver_info(self) -> dict:
        """
        获取数据保存信息

        @returns {dict} - 已保存的信息字典
            {
                'file_size': -1,  # 要接收的文件大小, -1 代表不确定文件实际大小
                'write_size': 0,  # 已写入的数据大小
                'md5': '',  # 文件的md5值
            }
        """
        return self._saver.get_save_info()

    def get_extend_info(self) -> dict:
        """
        获取保存的扩展信息字典

        @returns {dict} - 返回保存的扩展信息字典
        """
        return self._saver.get_extend_info()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
