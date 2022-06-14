#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
文件传输控制模块

@module transfer
@file transfer.py
"""

import os
import sys
import time
import threading
from HiveNetPromptPlus import ProgressRate
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetFileTransfer.protocol import ProtocolFw
from HiveNetFileTransfer.exceptions import Md5VerifyError, TransferFinishedError, FileDataPosMatchError, FileDataNullError


__MOUDLE__ = 'transfer'  # 模块名
__DESCRIPT__ = u'文件传输控制模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.08.24'  # 发布日期


class Transfer(object):
    """
    文件传输控制对象
    """
    #############################
    # 类初始化
    #############################

    def __init__(self, protocol: ProtocolFw, show_process_bar_fun=None,
                 process_bar_label: str = '', process_bar_info: str = '',
                 stop_notify_fun=None, thread_interval: float = 0.001, **kwargs):
        """
        初始化文件传输发送对象

        @param {ProtocolFw} protocol - 要处理的文件传输数据协议对象
        @param {function} show_process_bar_fun=None - 显示进度条的函数，如果不传代表不处理进度显示
            函数定义为 fun(rate:float, label:str, info:str, ...)
            注: 可以直接使用HiveNetPromptPlus.ProgressRate.show_cmd_process_bar
        @param {str} process_bar_label='' - 自定义进度条提示内容
        @param {str} process_bar_info='' - 自定义进度条信息内容
        @param {function} stop_notify_fun=None - 传输停止的通知函数，如果不传代表不通知
            函数定义为 fun(status:str, file_size:int, write_size:int, msg:str)
        @param {float} thread_interval=0.001 - 线程执行循环间隔时间
        """
        self.protocol = protocol
        self.stop_notify_fun = stop_notify_fun
        self.thread_interval = thread_interval
        self.process_bar_label = process_bar_label
        self.process_bar_info = process_bar_info
        self.kwargs = kwargs
        self.thread_num = self.protocol.get_thread_num()

        # 内部控制参数
        self.status = 'stop'  # stop - 停止, running - 正在运行, finished - 已完成, exception - 出现异常
        self.exception = None  # 如果是异常状态，可以通过该变量获取异常对象
        self._status_lock = threading.RLock()  # 控制状态变化的锁
        self._threads = list()  # 正在运行的线程对象数组，如果对应的值为None代表线程已结束

        # 进度显示相关
        self._info = self.protocol.get_saver_info()
        self._rate = None
        if show_process_bar_fun is not None:
            self._rate = ProgressRate(
                rate=0 if self._info['file_size'] == -1 else (
                    self._info['write_size'] / self._info['file_size'] * 100),
                show_process_bar_fun=show_process_bar_fun
            )

    #############################
    # 功能函数
    #############################

    def start(self, wait_finished: bool = False) -> str:
        """
        启动文件传输发送

        @param {bool} wait_finished=False - 是否等待传输结束

        @returns {str} - 返回当前状态值

        @throws {TransferFinishedError} - 当文件传输已完成，再启动会抛出该异常
        """
        self._status_lock.acquire()
        try:
            if self.status == 'running':
                # 正在运行，无需处理
                return self.status
            elif self.status == 'finished':
                # 已完成, 抛出已完成的异常
                raise TransferFinishedError('file trans already finished!')

            # 重新获取一次信息，避免暂停或停止导致的本地进度信息有误的情况
            self._info = self.protocol.get_saver_info()

            # 启动传输线程
            self.status = 'running'  # 设置状态为正在运行
            self._threads.clear()  # 清理数组
            # 根据传输协议对象的类型选择不同的处理线程
            for _index in range(self.thread_num):
                _thread = threading.Thread(
                    target=self._file_trans_thread_fun,
                    name='Thread-TransferReader-Running %s' % _index,
                    args=(_index,)
                )
                self._threads.append(_thread)

                _thread.setDaemon(True)
                _thread.start()

            # 显示当前进度
            if self._rate is not None:
                self._rate.show_progress_bar(
                    label='%s%s/%s' % (
                        '' if self.process_bar_label == '' else '%s:' % self.process_bar_label,
                        str(self._info['write_size']), str(self._info['file_size'])
                    ),
                    info=self.process_bar_info
                )
        finally:
            self._status_lock.release()

        if wait_finished:
            # 等待结束再返回
            while self.status == 'running':
                time.sleep(0.1)

        # 返回结果
        return self.status

    def stop(self):
        """
        停止文件传输
        """
        self._status_lock.acquire()
        try:
            if self.status != 'running':
                # 已经在停止状态
                return

            # 设置状态为停止，同时等待线程自行结束
            self.status = 'stop'
            _is_stoped = False
            while not _is_stoped:
                _is_stoped = True
                for _index in range(self.protocol.get_thread_num()):
                    if self._threads[_index] is not None:
                        # 只要出现线程不为None，则代表还没有处理完成
                        _is_stoped = False
                        break

            # 通知传输对象停止传输
            self.protocol.pause()

            # 停止通知
            if self.stop_notify_fun is not None:
                self.stop_notify_fun(
                    self.status, self._info['file_size'], self._info['write_size'],
                    'stop by function'
                )
        finally:
            self._status_lock.release()

    #############################
    # 内部函数
    #############################
    def _file_trans_thread_fun(self, index: int):
        """
        文件传输线程

        @param {int} index - 线程对应的传输

        @throws {FileDataPosMatchError} - 如果处理的数据位置与传输要求不一致，会抛出该异常
        """
        # 初始参数
        _start = None  # 传输开始位置
        _size = 0  # 传输文件大小
        _file_dict = None  # 传输文件对象属性
        _writer_dict = None  # 写入对象属性

        # 循环执行数据传输处理
        try:
            while self.status == 'running':
                # 获取数据前需要先打开文件对象
                if _start is not None and _file_dict is None:
                    _file_dict = self.protocol.open_file(index)

                # 读取要传输的数据
                _data = None
                _trans_size = 0
                _info_dict = None  # 从写入对象获取到的下一个数据获取范围信息
                if _start is not None:
                    _data = self.protocol.read_file_data(
                        index, _file_dict['handle'], _start, _size, _file_dict['lock']
                    )
                    _trans_size = len(_data)

                    if _trans_size == 0:
                        if self.protocol.file_size is None:
                            # 单线程且文件长度未知情况，发送文件结束标志
                            self.protocol.file_finished()
                            _info_dict = {
                                'status': 2, 'index': index, 'start': -1, 'size': 0
                            }
                        else:
                            # 正常应获取到数据，如果没有抛出异常
                            raise FileDataNullError()

                # 传输文件数据，获取下一次要获取的文件数据范围
                if _info_dict is None:
                    # 打开写入对象
                    if _writer_dict is None:
                        _writer_dict = self.protocol.open_writer(index)

                    _info_dict = self.protocol.write_data(
                        _writer_dict['handle'], _writer_dict['lock'], index=index,
                        start=_start, size=_trans_size, data=_data
                    )  # 传输的数据大小改为使用 trans_size

                # 显示传输进度
                if self._rate is not None and _trans_size > 0:
                    self._info['write_size'] += _trans_size
                    self._rate.set_rate(
                        0 if self._info['file_size'] == -1 else (
                            self._info['write_size'] / self._info['file_size'] * 100)
                    )
                    self._rate.show_progress_bar(
                        label='%s%s/%s' % (
                            '' if self.process_bar_label == '' else '%s:' % self.process_bar_label,
                            str(self._info['write_size']), str(self._info['file_size'])
                        ),
                        info=self.process_bar_info
                    )

                # 判断是否结束
                if _info_dict['status'] == 2:
                    # 所有下载处理已结束
                    self._status_lock.acquire()
                    if self.status == 'running':
                        self.status = 'finished'
                        # 停止通知
                        if self.stop_notify_fun is not None:
                            self.stop_notify_fun(
                                self.status, self._info['file_size'], self._info['write_size'],
                                'finished'
                            )
                    self._status_lock.release()
                    break
                elif _info_dict['status'] == 1:
                    # 开始位置与线程缓存不一致(传输失败)
                    raise FileDataPosMatchError()
                elif _info_dict['status'] == 3:
                    # 文件md5校验失败
                    raise Md5VerifyError()
                elif _info_dict['start'] == -1:
                    # 该线程无需再处理
                    break

                # 处理下一次循环
                _start = _info_dict['start']
                _size = _info_dict['size']
                time.sleep(self.thread_interval)
        except:
            # 执行过程中抛出异常，应中止服务
            self.status = 'exception'
            self.exception = sys.exc_info()[1]
            raise
        finally:
            # 跳出循环，代表线程已结束, 设置线程索引对象为None
            self._threads[index] = None
            # 关闭文件对象
            if _file_dict is not None and _file_dict['close_able']:
                self.protocol.close_file(index)
            # 关闭写入对象
            if _writer_dict is not None and _writer_dict['close_able']:
                self.protocol.close_writer(index)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
