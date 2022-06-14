#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
文件保存对象

@module saver
@file saver.py
"""

import os
import sys
import json
import threading
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.net_tool import NetTool
from HiveNetCore.utils.run_tool import WaitLockTool
from HiveNetCore.utils.debug_tool import DebugTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetFileTransfer.exceptions import InfoFileLockError, AlreadyKnowFileSizeError, Md5VerifyError


__MOUDLE__ = 'saver'  # 模块名
__DESCRIPT__ = u'文件保存对象'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.08.23'  # 发布日期


class TransferSaver(object):
    """
    文件保存对象
    """

    def __init__(self, file: str, is_resume: bool = True, file_size: int = None, md5: str = None,
                 is_overwrite: bool = False,
                 temp_ext: str = 'tmp', info_ext: str = 'info',
                 extend_info: dict = None, thread_num: int = 1, block_size: int = 4096, cache_size: int = 1024,
                 auto_expand: bool = True):
        """
        初始化文件保存对象

        @param {str} file - 文件保存路径（含文件名）
        @param {bool} is_resume=True - 指定是否续传（自动查找已下载的信息）, 如果不指定续传将自动删除原来已下载临时文件
            注：如果指定续传, 且可以找到原来的临时文件, 则以下参数将使用原来的信息, 如果有传入则会进行差异值的校验：
                file_size、md5
        @param {int} file_size=None - 文件大小, 单位为byte, 如果为None代表未知文件大小, 此时auto_expand参数固定为True
        @param {str} md5=None - 验证文件的md5字符串, 如果不传代表不进行验证
        @param {bool} is_overwrite=False - 是否覆盖已有文件, 如果为否, 则目标文件已存在的情况下抛出异常
        @param {str} temp_ext='tmp' - 处理过程中临时文件扩展名
        @param {str} info_ext='info' - 处理过程中信息文件扩展名
        @param {dict} extend_info=None - 处理过程中要保存的信息字典, 例如保存文件下载路径, 引用页等信息
        @param {int} thread_num=1 - 写入处理线程数量
        @param {int} block_size=4096 - 每次写入块大小, 单位为byte
        @param {int} cache_size=1024 - 单线程缓存大小, 单位为kb（注意：真实缓存大小还需要乘以处理线程数量）
        @param {bool} auto_expand=True - 是否自动扩展文件大小（否则在初始化时会自动创建指定大小的文件）

        @throws {FileExistsError} - 如果下载文件已存在且不允许覆盖的情况抛出异常
        @throws {FileNotFoundError} - 续传情况下临时文件不存在则抛出异常
        @throws {InfoFileLockError} - 如果已打开信息文件进行文件存储处理, 抛出该异常
        """
        # 检查文件是否存在
        self._file = os.path.abspath(file)
        self._path, self._filename = os.path.split(self._file)
        if os.path.exists(self._file):
            # 文件已存在
            if is_overwrite:
                FileTool.remove_file(self._file)
            else:
                raise FileExistsError('file exists: %s' % self._file)
        else:
            # 创建目录
            FileTool.create_dir(self._path, exist_ok=True)

        # 文件信息字典, 该字典登记文件基本信息和写入情况
        self._info: dict = None

        # 锁文件, 控制一个文件不能被多个类处理, 先尝试创建锁文件, 如果创建失败会抛出异常
        self._lock_file = os.path.join(self._path, '%s.%s' % (self._filename, 'lock'))
        try:
            self._lock_file_handle = os.open(
                self._lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR
            )
        except:
            raise InfoFileLockError('info file is locked')

        try:
            # 获取是否debug状态
            self._debug_on = DebugTool.is_debug_on()
            self._lock_print_timeout = None
            if self._debug_on:
                self._lock_print_timeout = 5.0  # 打印锁等待超时时间

            # 处理信息字典、临时文件、信息文件
            self._temp_file = os.path.join(self._path, '%s.%s' % (self._filename, temp_ext))
            self._info_file = os.path.join(self._path, '%s.%s' % (self._filename, info_ext))
            self._auto_expand = auto_expand
            self._thread_num = thread_num
            self._block_size = block_size
            self._cache_size = cache_size * 1024

            # 数据处理锁
            self._cache_info_lock = threading.RLock()  # 缓存信息更新锁
            self._tmp_file_lock = threading.RLock()  # 缓存文件写入锁
            self._is_finished = False  # 要控制的完成状态
            self._dealed_finished_lock = threading.RLock()  # 控制多线程操作结束函数的状态更新锁
            self._dealed_finished = False  # 控制多线程操作结束函数只执行一次的变量

            if is_resume and os.path.exists(self._info_file):
                # 自动续传情况
                self._info_file_handle = open(self._info_file, 'r+', encoding='utf-8')
                self._info_file_handle.seek(0)
                self._info = json.loads(self._info_file_handle.read())

                # 检查传入信息是否一致
                if file_size is not None and file_size != self._info['file_size']:
                    raise AttributeError('resume info [file_size] inconsistency, info file [%s], now [%s]' % (
                        str(self._info['file_size']), str(file_size)
                    ))

                if md5 is not None and md5 != self._info['md5']:
                    raise AttributeError('resume info [md5] inconsistency, info file [%s], now [%s]' % (
                        self._info['md5'], md5
                    ))

                # 检查临时文件
                self._temp_file = os.path.join(self._path, self._info['tmp_file'])
                if not os.path.exists(self._temp_file):
                    # 临时文件不存在
                    raise FileNotFoundError('temp file is not found: %s' % self._temp_file)

                self._tmp_file_handle = open(self._temp_file, 'rb+')
                self._tmp_file_handle.seek(0)
            else:
                # 删除已存在的临时文件信息
                if os.path.exists(self._temp_file):
                    FileTool.remove_file(self._temp_file)

                if os.path.exists(self._info_file):
                    FileTool.remove_file(self._info_file)

                # 形成信息字典
                self._info = {
                    'tmp_file': '%s.%s' % (self._filename, temp_ext),  # 临时文件名称
                    'file_size': -1 if file_size is None else file_size,  # 文件大小
                    'write_size': 0,  # 已写入数据大小
                    'md5': '' if md5 is None else md5,  # md5校验值
                    'extend_info': {} if extend_info is None else extend_info,  # 传入的扩展信息
                    # 存储索引, 按位置顺序在数组中登记未写入区间, 数组每一项登记未写入数据的开始位置和结束位置
                    'store_index': [[0, file_size - 1]]
                }

                # 生成临时文件
                self._tmp_file_handle = open(self._temp_file, 'wb')
                if not auto_expand and file_size is not None:
                    # 直接生成指定大小的文件
                    self._tmp_file_handle.seek(file_size - 1)   # 跳到指定位置
                    self._tmp_file_handle.write(b'\x00')  # 一定要写入一个字符, 否则无效
                    self._tmp_file_handle.flush()

                # 写入信息字典文件
                self._info_file_handle = open(self._info_file, 'w', encoding='utf-8')
                self._write_info_file()

            # 合并存储索引, 把碎片合并成为大块
            self._info['store_index'] = self._f_merge_store_index(self._info['store_index'])

            # 初始化缓存等信息
            if self._info['file_size'] == -1:
                # 如果没有文件大小的情况, 不支持拆分多写入线程和一次性创建指定大小文件的情况
                self._thread_num = 1
                self._auto_expand = True

            # 缓存处理
            self._max_cache_pos = [-1, ]  # 当前缓存分配到的区域最大位置
            self._cache = dict()
            for _i in range(self._thread_num):
                self._cache[_i] = {
                    'start': -1,  # 缓存数据对应文件的写入位置, -1代表没有设置
                    'size': 0,  # 缓存数据大小
                    'buffer': bytes(),  # 具体的缓存数据
                    'end_pos': -1,  # 该缓存对应线程要处理的文件块结束位置
                    'lock': threading.RLock(),  # 用于缓存线程处理的锁）
                    'get_start': -1,  # 当前正在获取的数据的开始位置
                    'get_size': 0,  # 当前要获取数据的大小
                }

            # 分配每个缓存要处理文件区域
            for _i in range(self._thread_num):
                self._set_cache_area(_i)
        except:
            # 如果初始化出现异常, 清理文件句柄及锁文件
            self._clear_file_handle_and_lock()
            raise

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

    def close(self):
        """
        主动关闭保存对象
        """
        # 先写入缓存数据
        self.flush()

        # 关闭所有打开文件
        self._clear_file_handle_and_lock()

        # 清空变量
        self._info.clear()
        self._cache.clear()

    #############################
    # 工具函数
    #############################
    def get_save_info(self) -> dict:
        """
        获取数据保存信息

        @returns {dict} - 数据保存的信息字典
            {
                'file_size': -1,  # 要接收的文件大小, -1 代表不确定文件实际大小
                'write_size': 0,  # 已写入的数据大小
                'md5': '',  # 文件的md5值
            }
        """
        return {
            'file_size': -1 if self._info['file_size'] is None else self._info['file_size'],
            'write_size': self._info['write_size'],
            'md5': self._info['md5']
        }

    def get_extend_info(self) -> dict:
        """
        获取保存的信息字典

        @returns {dict} - 返回保存的信息字典
        """
        return self._info['extend_info']

    def flush(self):
        """
        将缓存中的数据全部写入文件
        """
        for _i in range(self._thread_num):
            self._flush_cache(_i)

    def finished(self):
        """
        对于未知文件大小的情况, 由该函数指定文件写入完成

        @throws {AlreadyKnowFileSizeError} - 对于文件大小已知的处理情况, 如果调用该函数会抛出异常
        """
        if self._info['file_size'] != -1:
            raise AlreadyKnowFileSizeError('already know file size')

        # 先将缓存信息写入临时文件
        self.flush()

        # 将临时文件改名, 清除临时文件
        self._write_finished()

    def write_data(self, index: int = 0, start: int = None, size: int = None,
                   data: bytes = None) -> dict:
        """
        写入数据的处理方法

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
        if index >= self._thread_num:
            # 索引有错误, 直接返回无获取任务的信息, 让前端不再处理该线程索引
            return {'status': 0, 'index': index, 'start': -1, 'size': 0}

        # 单索引线程需要锁定
        with WaitLockTool(
            self._cache[index]['lock'], print_timeout=self._lock_print_timeout,
            label='cache %d' % index, print_acquire_ok=self._debug_on,
            print_release=self._debug_on
        ):
            _status = 0
            if start is not None:
                # 涉及到修改cache, 统一锁定
                with WaitLockTool(
                    self._cache_info_lock, print_timeout=self._lock_print_timeout,
                    label='_cache_info_lock %d' % index, print_acquire_ok=self._debug_on,
                    print_release=self._debug_on
                ):
                    # 写入数据到缓存
                    _status = self._write_data_to_cache(index, start, size, data)

                    # 获取新的获取信息
                    if _status == 0:
                        self._set_cache_area(index, lock_cache=False)

            # 返回下一次获取的数据区间
            _cache = self._cache[index]
            if _cache['start'] == -1:
                # 判断是否全部处理任务已完成
                if self._is_finished:
                    # 全部完成
                    _status = 2

                    self._dealed_finished_lock.acquire()
                    # 将临时文件改名, 清除临时文件
                    try:
                        if not self._dealed_finished:
                            self._dealed_finished = True
                            self._write_finished()
                    except Md5VerifyError:
                        _status = 3
                    except:
                        raise
                    finally:
                        self._dealed_finished_lock.release()

                return {
                    'status': _status, 'index': index, 'start': -1, 'size': 0
                }
            else:
                return {
                    'status': _status, 'index': index,
                    'start': _cache['get_start'],
                    'size': _cache['get_size']
                }

    #############################
    # 内部函数
    #############################

    def _write_info_file(self):
        """
        将内存写入信息文件
        """
        self._info_file_handle.truncate(0)
        self._info_file_handle.seek(0)
        self._info_file_handle.write(
            json.dumps(self._info, ensure_ascii=False, indent=2)
        )
        self._info_file_handle.flush()

    def _clear_file_handle_and_lock(self):
        """
        清理文件句柄及锁文件
        """
        # 关闭文件句柄
        if hasattr(self, '_info_file_handle') and self._info_file_handle is not None:
            self._info_file_handle.close()

        if hasattr(self, '_tmp_file_handle') and self._tmp_file_handle is not None:
            self._tmp_file_handle.close()

        if hasattr(self, '_lock_file_handle'):
            if self._lock_file_handle is not None:
                # 删除锁文件
                os.close(self._lock_file_handle)
                os.remove(self._lock_file)

    def _set_cache_area(self, index: int, lock_cache: bool = True):
        """
        设置缓存的处理区域

        @param {int} index - 要处理的缓存对应处理线程索引

        @throws {KeyError} - 当送入的index超过了写入线程数范围时抛出异常
        """
        if index >= self._thread_num:
            raise KeyError('cache index[%s] error, out of range' % str(index))

        self._f_set_cache_area(
            self._cache, index, self._info['store_index'], self._cache_size,
            self._block_size, self._max_cache_pos,
            cache_info_lock=self._cache_info_lock if lock_cache else None,
            lock_print_timeout=self._lock_print_timeout, debug_on=self._debug_on
        )

    def _flush_cache(self, index: int, lock_cache: bool = True) -> bool:
        """
        将指定缓存数据写入文件

        @param {int} index - 要处理的缓存对应处理线程索引
        @param {bool} lock_cache=True - 是否锁定缓存

        @returns {bool} - 指示是否有正确写入缓存数据

        @throws {KeyError} - 当送入的index超过了写入线程数范围时抛出异常
        """
        if index >= self._thread_num:
            raise KeyError('cache index[%s] error, out of range' % str(index))

        _is_writed = False
        _cache = self._cache[index]

        with WaitLockTool(
            self._tmp_file_lock, print_timeout=self._lock_print_timeout,
            label='_tmp_file_lock %d' % index, print_acquire_ok=self._debug_on,
            print_release=self._debug_on, force_no_acquire=(not lock_cache)
        ):
            if _cache['size'] <= 0:
                # 没有要写入的数据
                return _is_writed

            # 临时参数
            _start_pos = _cache['start']
            _size = _cache['size']

            # 写入文件, 更新info字典
            self._tmp_file_handle.seek(_start_pos)
            _write_size = self._tmp_file_handle.write(_cache['buffer'])
            self._tmp_file_handle.flush()

            # 更新info字典的store_index
            with WaitLockTool(
                self._cache_info_lock, print_timeout=self._lock_print_timeout,
                label='_cache_info_lock %d' % index, print_acquire_ok=self._debug_on,
                print_release=self._debug_on
            ):
                _is_writed = self._f_update_store_index(
                    self._info['store_index'], _start_pos, _size
                )

                if len(self._info['store_index']) == 0:
                    # 如果已经没有区块, 设置完成标志
                    self._is_finished = True

                if _is_writed:
                    # 更新已写入数据大小
                    self._info['write_size'] += _write_size

                    # 写入info文件
                    if not self._is_finished:
                        self._write_info_file()

                    # 更新cache信息
                    _end_pos = _cache['end_pos']
                    if _end_pos is not None and (_start_pos + _size) >= _end_pos:
                        # 区间已经处理完成
                        _cache['start'] = -1
                        _cache['end_pos'] = -1
                    else:
                        _cache['start'] = _start_pos + _size

                    _cache['size'] = 0
                    _cache['buffer'] = bytes()

    def _write_finished(self):
        """
        文件写入结束

        @throws {Md5VerifyError} - 当文件校验失败时抛出异常
        """
        # 关闭文件句柄
        self._info_file_handle.close()
        self._info_file_handle = None
        self._tmp_file_handle.close()
        self._tmp_file_handle = None
        os.close(self._lock_file_handle)
        self._lock_file_handle = None

        # 检查md5
        if self._info['md5'] != '':
            _file_md5 = NetTool.get_file_md5(self._temp_file)
            if self._info['md5'] != _file_md5:
                raise Md5VerifyError('md5 verify error')

        # 修改临时文件名
        os.rename(
            self._temp_file, self._file
        )

        # 删除临时文件
        FileTool.remove_file(self._info_file)
        FileTool.remove_file(self._lock_file)

    def _write_data_to_cache(self, index: int, start: int, size: int, data: bytes) -> int:
        """
        写入数据到缓存

        @param {int} index - 获取缓存数据的线程索引
        @param {int} start - 要写入文件的开始位置
        @param {int} size - 要写入数据的大小
        @param {bytes} data - 要写入的输入

        @returns {int} - 写入结果, 0-成功, 1-开始位置与线程缓存不一致
        """
        # 写入数据到缓存
        _cache = self._cache[index]
        if start != _cache['get_start']:
            # 开始位置与线程缓存不一致, 写入失败
            return 1
        else:
            # 进行写入处理, 添加数据到缓存中, 更新缓存数据需要获取锁

            _cache['size'] += size
            _cache['buffer'] += data
            # 重置正在获取的数据位置
            _cache['get_start'] = -1
            _cache['get_size'] = 0

            # 判断是否需要写入(超过缓存控制大小, 或已写到当前cache的结束位置)
            _end_pos = _cache['end_pos']
            if _cache['size'] >= self._cache_size or (_end_pos != -1 and _end_pos <= (_cache['start'] + _cache['size'])):
                self._flush_cache(index, lock_cache=False)

        # 返回处理成功
        return 0

    #############################
    # 内部静态算法函数, 为了便于测试算法准确性
    #############################
    @classmethod
    def _f_merge_store_index(cls, store_index: list) -> list:
        """
        合并存储索引数组, 将碎片区域合并为大区域

        @param {list} store_index - 索引存储数组
            按位置顺序在数组中登记未写入区间, 数组每一项登记未写入数据的开始位置和结束位置

        @returns {list} - 合并后的存储索引数组
        """
        _index = len(store_index) - 1
        while _index > 0:
            if store_index[_index][0] == store_index[_index - 1][1] + 1:
                # 两个区域可以合并, 将上一项的结尾设置为当前项的结尾, 并删除当前项
                store_index[_index - 1][1] = store_index[_index][1]
                store_index.pop(_index)

            _index -= 1

        return store_index

    @classmethod
    def _f_set_cache_area(cls, cache: dict, index: int, store_index: list, cache_size: int, block_size: int,
                          max_cache_pos: list,
                          cache_info_lock: threading.RLock = None,
                          lock_print_timeout: float = None, debug_on: bool = False):
        """
        设置缓存的处理区域

        @param {dict} cache - 所有缓存信息字典, 格式如下:
            {
                index: {
                    'start': -1,  # 缓存数据对应文件的写入位置, -1代表没有设置
                    'size': 0,  # 缓存数据大小
                    'buffer': bytes(),  # 具体的缓存数据
                    'end_pos': -1,  # 该缓存对应线程要处理的文件块结束位置
                    'lock': threading.RLock,  # 用于锁定缓存数据的锁
                },
                ...
            }
        @param {int} index - 当前要设置的缓存
        @param {list} store_index - 索引存储数组
            按位置顺序在数组中登记未写入区间, 数组每一项登记未写入数据的开始位置和结束位置
        @param {int} cache_size - 单线程缓存大小
        @param {int} block_size - 每次写入块大小, 单位为byte
        @param {list} max_cache_pos - 当前缓存分配到的区域最大位置, 采用数组方式是因为需要更新返回值
        @param {threading.RLock} cache_info_lock=None - 需要传入的缓存信息更新锁, 不传代表无需锁定
        @param {float} lock_print_timeout=None - 锁等待打印超时时间
        @param {bool} debug_on=False - debug状态
        """
        with WaitLockTool(
            cache_info_lock, print_timeout=lock_print_timeout,
            label='_cache_info_lock %d' % index, print_acquire_ok=debug_on,
            print_release=debug_on, force_no_acquire=(cache_info_lock is None)
        ):
            _set_ok = False  # 是否已分配成功的标记

            # 非已完结缓存, 从自身分配即可
            if cache[index]['start'] != -1:
                _set_ok = True

            # 自身无法分配, 需要从其他区域分配
            # 先遍历信息字典中的存储索引, 看是否还有缓存未覆盖的区域
            if not _set_ok:
                for _store_area in store_index:
                    if _store_area[0] > max_cache_pos[0]:
                        # 找到可分配区域
                        cache[index]['start'] = _store_area[0]
                        cache[index]['end_pos'] = _store_area[1]

                        _set_ok = True
                        if _store_area[1] > max_cache_pos[0]:
                            max_cache_pos[0] = _store_area[1]  # 当前缓存分配到的区域最大位置
                        break

            # 已经没有可分配的存储索引, 考虑截断其他缓存的区域
            if not _set_ok:
                # 找到区域最大的缓存
                _max_index = -1
                _max_area = 0
                for _index, _cache_info in cache.items():
                    if _cache_info['start'] == -1 or _cache_info['end_pos'] == -1:
                        # 无法拆分的缓存
                        continue

                    # _area = _cache_info['end_pos'] - _cache_info['start'] - _cache_info['size']
                    _cache_real_start = _cache_info['start'] + _cache_info['size']
                    if _cache_info['get_start'] != -1:
                        _cache_real_start = _cache_info['get_start'] + _cache_info['get_size']
                    _area = _cache_info['end_pos'] - _cache_real_start
                    if _area > _max_area:
                        _max_area = _area
                        _max_index = _index

                if _max_index == -1:
                    # 没有找到可拆分的缓存
                    return

                # 从最大缓存进行拆分
                # _area = cache[_max_index]['end_pos'] - cache[_max_index]['start'] - cache_size
                if cache[_max_index]['start'] == -1:
                    # 过程中已处理, 已经无法再分
                    return

                _cache_real_start = cache[_max_index]['start'] + cache[_max_index]['size']
                if cache[_max_index]['get_start'] != -1:
                    _cache_real_start = cache[_max_index]['get_start'] + \
                        cache[_max_index]['get_size']

                _area = cache[_max_index]['end_pos'] - _cache_real_start
                if _area <= cache_size:
                    # 余下区域小于一个cache, 无需再拆分
                    return

                # 进行切割
                _split_size = round(_area / 2)
                cache[index]['start'] = _cache_real_start + _split_size
                cache[index]['end_pos'] = cache[_max_index]['end_pos']
                cache[_max_index]['end_pos'] = cache[index]['start'] - 1

                _set_ok = True

            # 设置已分配索引的获取位置
            if _set_ok:
                cache[index]['get_start'] = cache[index]['start'] + cache[index]['size']
                cache[index]['get_size'] = min(
                    block_size, cache[index]['end_pos'] - cache[index]['get_start'] + 1
                )

    @classmethod
    def _f_update_store_index(cls, store_index: list, start_pos: int, size: int) -> bool:
        """
        写入数据后更新存储索引数组
        注：该方法不处理跨多个存储块写入的情况

        @param {list} store_index - 索引存储数组
            按位置顺序在数组中登记未写入区间, 数组每一项登记未写入数据的开始位置和结束位置
        @param {int} start_pos - 要写入数据的开始位置
        @param {int} size - 要写入数据的大小

        @param {bool} - 指示是否变更了存储索引数组
        """
        for _i in range(len(store_index)):
            if start_pos == store_index[_i][0]:
                # 直接按顺序向下存储, 同时兼容了区间结尾为None的情况
                store_index[_i][0] += size
            elif start_pos > store_index[_i][0] and start_pos <= store_index[_i][1]:
                # 将区域从中间切割开
                _end_pos = store_index[_i][1]
                store_index[_i][1] = start_pos - 1  # 前面的区域的结束位置设定为写入位置的前一个
                _i += 1  # 要判断的是新区域
                store_index.insert(_i, [start_pos + size, _end_pos])  # 添加新增加的区域
            else:
                # 在下一个区域
                continue

            # 判断当前区域是否已写入完成
            if store_index[_i][1] is not None and store_index[_i][0] > store_index[_i][1]:
                # 整个区域已经处理完成, 直接从数组移走
                store_index.pop(_i)

            # 退出循环处理
            return True

        # 如果能走到结束, 代表没有找到可修改的存储索引
        return False


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
