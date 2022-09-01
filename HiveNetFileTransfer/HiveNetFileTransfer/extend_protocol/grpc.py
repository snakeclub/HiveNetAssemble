#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
gRpc传输协议模块

@module grpc
@file grpc.py
"""


import os
import sys
import logging
import uuid
import time
import datetime
import threading
import traceback
import queue
from typing import Iterator, Union
from io import FileIO
from HiveNetCore.generic import CResult
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.net_tool import NetTool
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.string_tool import StringTool
from HiveNetCore.connection_pool import AIOConnectionPool
from HiveNetGRpc.enum import EnumCallMode
from HiveNetGRpc.server import GRpcServer, AIOGRpcServer
from HiveNetGRpc.client import AIOGRpcClient, GRpcPoolConnection
from HiveNetGRpc.msg_formater import RemoteCallFormater
from HiveNetGRpc.proto.msg_json_pb2 import RpcRequest as JsonRpcRequest
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetFileTransfer.saver import TransferSaver
from HiveNetFileTransfer.protocol import LocalProtocol
from HiveNetFileTransfer.exceptions import FileNotUnderWorkDirError


__MOUDLE__ = 'grpc'  # 模块名
__DESCRIPT__ = u'gRpc传输协议模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.09.06'  # 发布日期


class GRpcProtocolServer(object):
    """
    GRpc文件传输协议的服务端
    """

    def __init__(self, app_name: str = 'file_transfer_grpc_proto_server', server_config: dict = {},
            work_dir: str = None, lock_in_work_dir: bool = True, push_max_thread_num: int = 0,
            push_max_cache_size: int = 0, push_overtime: float = 60,
            pull_file_handle_overtime: float = 60,
            logger=None, log_level: int = logging.INFO, **kwargs):
        """
        构造函数

        @param {str} app_name='file_transfer_grpc_proto_server' - GRpc服务应用名
        @param {dict} server_config={} - grpc服务配置, 具体配置参考HiveNetGRpc.server.GRpcServer的构造函数
        @param {str} work_dir=None - 默认工作目录, 如果不设置代表使用外部程序实时切换的工作目录
        @param {bool} lock_in_work_dir=True - 是否锁定文件必须传输在工作目录下
        @param {int} push_max_thread_num=0 - 客户端推文件模式传输所支持的最大线程数控制, 如果为0代表不限制
        @param {int} push_max_cache_size=0 - 客户端推文件模式传输所支持的最大缓存大小(单位为kb), 如果为0代表不限制
            注: 单线程缓存大小, 真实缓存大小还需要乘以处理线程数量
        @param {float} push_overtime=60 - 客户端推文件模式传输超时时间(长时间没有收到数据更新请求), 单位为秒
        @param {float} pull_file_handle_overtime=60 - 客户端拉模式文件句柄保持超时时间(长时间没有收到数据请求的情况),单位为秒
        @param {Logger} logger=None - 自定义应用逻辑使用的日志对象
        @param {int} log_level=logging.INFO - 一般信息的记录使用的日志级别
        """
        # 参数处理
        self.push_max_thread_num = push_max_thread_num
        self.push_max_cache_size = push_max_cache_size
        self.work_dir = work_dir
        self.lock_in_work_dir = lock_in_work_dir
        self.push_overtime = push_overtime
        self.pull_file_handle_overtime = pull_file_handle_overtime

        # 内部变量处理, key为uuid, value为字典{'saver': , 'last': }
        self._dealing_saver = dict()

        # 内部变量处理, key为uuid, value为字典{'file_handle': , 'last': , 'lock':}
        self._file_handles = dict()

        # grpc服务
        self._grpc_server = GRpcServer(
            app_name, server_config=server_config, logger=logger, log_level=log_level
        )

        # 添加客户端推模式的处理函数
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_init_saver', self.push_transfer_init_saver
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_get_save_info', self.push_transfer_get_save_info
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_get_extend_info', self.push_transfer_get_extend_info
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_flush', self.push_transfer_flush
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_finished', self.push_transfer_finished
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_close', self.push_transfer_close
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'push_transfer_write_data', self.push_transfer_write_data,
            call_mode=EnumCallMode.BidirectionalStream
        ))  # 写入数据采用双向流的模式

        # 添加客户端拉模式的处理函数
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'pull_transfer_get_file_size', self.pull_transfer_get_file_size
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'pull_transfer_get_file_md5', self.pull_transfer_get_file_md5
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'pull_transfer_open_file_handle', self.pull_transfer_open_file_handle
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'pull_transfer_close_file_handle', self.pull_transfer_close_file_handle
        ))
        AsyncTools.sync_run_coroutine(self._grpc_server.add_service(
            'pull_transfer_read_file_data', self.pull_transfer_read_file_data,
            call_mode=EnumCallMode.BidirectionalStream
        ))

        # 启动检查超时的线程
        self._overtime_thread_running = True
        self._overtime_thread = threading.Thread(
            target=self._overtime_thread_fun,
            name='Thread-Service-Overtime'
        )
        self._overtime_thread.setDaemon(True)
        self._overtime_thread.start()

    def __del__(self):
        """
        析构函数
        """
        # 关闭grpc服务
        AsyncTools.sync_run_coroutine(
            self._grpc_server.stop()
        )

        # 线程关闭
        self._overtime_thread_running = False

        # 关闭所有客户端推文件模式的保存对象
        _ids = list(self._dealing_saver.keys())
        for _id in _ids:
            _dict = self._dealing_saver.pop(_id, None)
            if _dict is not None:
                _dict['saver'].close()

        # 关闭所有客户端拉文件模式的保存对象
        _ids = list(self._file_handles.keys())
        for _id in _ids:
            _dict = self._file_handles.pop(_id, None)
            if _dict is not None:
                _dict['file_handle'].close()

    #############################
    # 工具函数
    #############################
    def start_server(self) -> CResult:
        """
        启动grpc服务

        @returns {CResult} - 异步情况返回启动结果, result.code: '00000'-成功, '21401'-服务不属于停止状态, 其他-异常
        """
        return AsyncTools.sync_run_coroutine(
            self._grpc_server.start(is_asyn=True)
        )

    def stop_server(self) -> CResult:
        """
        停止grpc服务

        @returns {CResult} - 停止结果, result.code: '00000'-成功, '21402'-服务停止失败-服务已关闭,
            '31005'-执行超时, 29999'-其他系统失败
        """
        return AsyncTools.sync_run_coroutine(
            self._grpc_server.stop()
        )

    #############################
    # 推文件模式服务函数
    #############################
    @RemoteCallFormater.format_service(with_request=False)
    def push_transfer_init_saver(self, file: str, is_resume: bool = True, file_size: int = None, md5: str = None,
                                 is_overwrite: bool = False, extend_info: dict = None, thread_num: int = 1,
                                 block_size: int = 4096, cache_size: int = 1024,
                                 auto_expand: bool = True) -> dict:
        """
        初始化文件保存对象

        @param {str} file - 要保存的文件路径(工作目录的相对路径)
        @param {bool} is_resume=True - 指定是否续传(自动查找已下载的信息), 如果不指定续传将自动删除原来已下载临时文件
            注: 如果指定续传, 且可以找到原来的临时文件, 则以下参数将使用原来的信息, 如果有传入则会进行差异值的校验:
                file_size、md5
        @param {int} file_size=None - 文件大小, 单位为byte, 如果为None代表未知文件大小, 此时auto_expand参数固定为True
        @param {str} md5=None - 验证文件的md5字符串, 如果不传代表不进行验证
        @param {bool} is_overwrite=False - 是否覆盖已有文件, 如果为否, 则目标文件已存在的情况下抛出异常
        @param {dict} extend_info=None - 处理过程中要保存的信息字典, 例如保存文件下载路径, 引用页等信息
        @param {int} thread_num=1 - 写入处理线程数量
        @param {int} block_size=4096 - 每次写入块大小, 单位为byte
        @param {int} cache_size=1024 - 单线程缓存大小, 单位为kb(注意: 真实缓存大小还需要乘以处理线程数量)
        @param {bool} auto_expand=True - 是否自动扩展文件大小(否则在初始化时会自动创建指定大小的文件)

        @returns {dict} - 返回文件保存对象的信息
            {
                'id': '生成saver对应的uuid',
                'thread_num': saver的实际线程数
            }
        """
        # 进行参数控制和校验
        _work_dir = os.getcwd() if self.work_dir is None else self.work_dir
        _file = os.path.realpath(
            os.path.join(_work_dir, file)
        )
        if self.lock_in_work_dir and not FileTool.is_file_in_subdir(_file, _work_dir):
            # 控制文件必须在指定目录下
            raise FileNotUnderWorkDirError('file not under work dir')

        _thread_num = thread_num
        if self.push_max_thread_num > 0:
            _thread_num = min(self.push_max_thread_num, _thread_num)

        _cache_size = cache_size
        if self.push_max_cache_size > 0:
            _cache_size = min(self.push_max_cache_size, _cache_size)

        _uuid = str(uuid.uuid1())
        _saver = TransferSaver(
            _file, is_resume=is_resume, file_size=file_size, md5=md5,
            is_overwrite=is_overwrite, extend_info=extend_info, thread_num=_thread_num,
            block_size=block_size, cache_size=_cache_size, auto_expand=auto_expand
        )
        self._dealing_saver[_uuid] = {
            'saver': _saver, 'last': datetime.datetime.now()
        }

        # 返回结果
        return {
            'id': _uuid, 'thread_num': _saver._thread_num
        }

    @RemoteCallFormater.format_service(with_request=False)
    def push_transfer_flush(self, id: str):
        """
        写入缓存

        @param {str} id - 要处理的saver的uuid
        """
        _saver_dict = self._dealing_saver.get(id, None)
        if _saver_dict is not None:
            _saver_dict['saver'].flush()
            _saver_dict['last'] = datetime.datetime.now()

    @RemoteCallFormater.format_service(with_request=False)
    def push_transfer_close(self, id: str):
        """
        关闭处理

        @param {str} id - 要处理的saver的uuid
        """
        self._dealing_saver[id]['saver'].close()

        # 将任务移除
        self._dealing_saver.pop(id)

    @RemoteCallFormater.format_service(with_request=True, native_request=True)
    def push_transfer_write_data(self, request: dict, id: str, index: int = 0) -> dict:
        """
        写入文件数据
        注: 采用双向流模式, 处理迭代对象

        @param {dict} request - 客户端流送入的请求信息字典
            {
                'request': request,  # 请求报文对象(如果是流模式也需获取对应的请求报文对象)
                'context': context,  # 请求服务端上下文, grpc.ServicerContext
                'call_mode': call_mode  # 调用模式
            }
        @param {str} id - 要处理的saver的uuid
        @param {int} index=0 - 指定写入数据的线程索引

        @returns {dict} - 返回下一个任务要获取的信息字典, 格式为:
            {
                'status': 0,  # 状态, 0-成功, 1-开始位置与线程缓存不一致, 2-全部下载完成, 3-文件md5校验失败
                'index': 0,  # 当前线程索引
                'start': -1,  # 开始位置, 如果传入-1代表该线程已无获取任务
                'size': 0,  # 要获取数据的大小
            }
        """
        _saver_dict = self._dealing_saver.get(id, None)
        if _saver_dict is not None:
            for _request in request['request']:
                _json = StringTool.json_loads_hive_net(_request.para_json)
                _data = _request.extend_bytes
                _saver_dict['last'] = datetime.datetime.now()
                yield _saver_dict['saver'].write_data(
                    index=_json['index'], start=_json['start'], size=_json['size'],
                    data=_data
                )
        else:
            yield {'status': 0, 'index': index, 'start': -1, 'size': 0}

    @RemoteCallFormater.format_service(with_request=False)
    def push_transfer_finished(self, id: str):
        """
        对于未知文件大小的情况, 由该函数指定文件写入完成

        @param {str} id - 要处理的saver的uuid
        """
        _saver_dict = self._dealing_saver.get(id, None)
        if _saver_dict is not None:
            _saver_dict['last'] = datetime.datetime.now()
            _saver_dict['saver'].finished()

    @RemoteCallFormater.format_service(with_request=False)
    def push_transfer_get_save_info(self, id: str) -> dict:
        """
        获取数据保存信息

        @param {str} id - 要处理的saver的uuid

        @returns {dict} - 数据保存的信息字典
            {
                'file_size': -1,  # 要接收的文件大小, -1 代表不确定文件实际大小
                'write_size': 0,  # 已写入的数据大小
                'md5': '',  # 文件的md5值
            }
        """
        self._dealing_saver[id]['last'] = datetime.datetime.now()
        return self._dealing_saver[id]['saver'].get_save_info()

    @RemoteCallFormater.format_service(with_request=False)
    def push_transfer_get_extend_info(self, id: str) -> dict:
        """
        获取保存的信息字典

        @param {str} id - 要处理的saver的uuid

        @returns {dict} - 返回保存的信息字典
        """
        self._dealing_saver[id]['last'] = datetime.datetime.now()
        return self._dealing_saver[id]['saver'].get_extend_info()

    #############################
    # 拉文件模式服务函数
    #############################
    @RemoteCallFormater.format_service(with_request=False)
    def pull_transfer_get_file_size(self, file: str) -> int:
        """
        获取文件的大小

        @param {str} file - 文件路径

        @returns {int} - 文件大小
        """
        _file = self._get_file_real_path(file)
        return os.path.getsize(_file)

    @RemoteCallFormater.format_service(with_request=False)
    def pull_transfer_get_file_md5(self, file: str) -> str:
        """
        获取文件的md5值

        @param {str} file - 文件路径

        @returns {str} - 文件md5值
        """
        _file = self._get_file_real_path(file)
        return NetTool.get_file_md5(_file)

    @RemoteCallFormater.format_service(with_request=False)
    def pull_transfer_open_file_handle(self, file: str) -> dict:
        """
        打开文件句柄

        @param {str} file - 文件路径

        @returns {dict} - {'id': 打开文件句柄的访问id}
        """
        _file = self._get_file_real_path(file)
        _file_dict = {
            'file_handle': open(_file, 'rb'),
            'last': datetime.datetime.now(),
            'lock': threading.RLock()
        }
        _id = str(uuid.uuid1())
        self._file_handles[_id] = _file_dict

        # 返回打开的结果
        return {'id': _id}

    @RemoteCallFormater.format_service(with_request=False)
    def pull_transfer_close_file_handle(self, id: str):
        """
        关闭已打开的文件句柄

        @param {str} id - 打开的文件句柄id
        """
        _file_dict = self._file_handles.pop(id, None)
        if _file_dict is not None:
            _file_dict['lock'].acquire()
            try:
                _file_dict['file_handle'].close()
                _file_dict['file_handle'] = None
            finally:
                _file_dict['lock'].release()

    @RemoteCallFormater.format_service(with_request=False)
    def pull_transfer_read_file_data(self, request: dict, id: str) -> dict:
        """
        获取文件数据
        注: 采用双向流模式

        @param {dict} request - 客户端流送入的请求信息字典
            {
                'request': request,  # 请求报文对象(如果是流模式也需获取对应的请求报文对象)
                'context': context,  # 请求服务端上下文, grpc.ServicerContext
                'call_mode': call_mode  # 调用模式
            }
        @param {str} id - 访问文件的id

        @returns {dict} -获取到的数据字典: {'data': 数据}
            注: 如果开始位置超过文件大小, 将返回b''; 如果要获取的数据大小超过文件, 则返回真实的数据大小
        """
        _file_dict = self._file_handles.get(id, None)
        if _file_dict is None:
            raise FileNotFoundError('file is not opened!')

        for _json in request['request']:
            # 获取文件数据并返回
            _file_dict['lock'].acquire()
            try:
                _file_dict['last'] = datetime.datetime.now()
                _file_dict['file_handle'].seek(_json['start'])
                _resp = RemoteCallFormater.service_resp_to_grpc_resp(
                    '', EnumCallMode.Simple, extend_bytes=_file_dict['file_handle'].read(_json['size'])
                )
                yield _resp
            finally:
                _file_dict['lock'].release()

    #############################
    # 内部函数
    #############################
    def _get_file_real_path(self, file: str) -> str:
        """
        获取文件真实路径

        @param {str} file - 传入的文件路径

        @returns {str} - 返回文件真实路径

        @throws {FileNotUnderWorkDirError} - 锁定工作目录的情况如果文件路径不在工作目录下, 抛出异常
        """
        # 进行参数控制和校验
        _work_dir = os.getcwd() if self.work_dir is None else self.work_dir
        _file = os.path.realpath(
            os.path.join(_work_dir, file)
        )
        if self.lock_in_work_dir and not FileTool.is_file_in_subdir(_file, _work_dir):
            # 控制文件必须在指定目录下
            raise FileNotUnderWorkDirError('file not under work dir')

        return _file

    def _overtime_thread_fun(self):
        """
        超时检查关闭保存对象
        """
        while self._overtime_thread_running:
            try:
                _now = datetime.datetime.now()

                # 检查客户端推送模式的超时对象
                _ids = list(self._dealing_saver.keys())
                for _id in _ids:
                    _dict = self._dealing_saver.get(_id, None)
                    if _dict is not None and (_now - _dict['last']).total_seconds() > self.push_overtime:
                        # 已超时, 移除该保存对象
                        self._dealing_saver.pop(_id, None)
                        _dict['saver'].close()

                # 检查客户端拉模式的超时对象
                _ids = list(self._file_handles.keys())
                for _id in _ids:
                    _dict = self._file_handles.get(_id, None)
                    if _dict is not None and (_now - _dict['last']).total_seconds() > self.pull_file_handle_overtime:
                        # 已超时, 移除该保存对象
                        self.pull_transfer_close_file_handle(_id)

                # 停止1秒再进行下一次循环
                time.sleep(1.0)
            except:
                print('GRpcProtocolServer overtime thread error: %s' % traceback.format_exc())


class GRpcPushProtocol(LocalProtocol):
    """
    本地文件通过gRpc传输至远端的传输协议
    """

    def __init__(self, src_file: Union[str, FileIO], dest_file: str, is_resume: bool = True, is_overwrite: bool = False,
                 thread_num: int = 1, block_size: int = 4096, cache_size: int = 1024, auto_expand: bool = True,
                 **kwargs):
        """
        初始化文件传输协议类

        @param {str|FileIO} src_file - 源文件路径或已打开的文件句柄
        @param {str} dest_file - 目标文件路径(指的是远端服务器上的路径, 是约定工作目录的相对路径)
        @param {bool} is_resume=True - 指定是否续传(自动查找已下载的信息), 如果不指定续传将自动删除原来已下载临时文件
        @param {bool} is_overwrite=False - 是否覆盖已有文件, 如果为否, 则目标文件已存在的情况下抛出异常
        @param {int} thread_num=1 - 写入处理线程数量
        @param {int} block_size=4096 - 每次传输块大小, 单位为byte
        @param {int} cache_size=1024 - 单线程缓存大小, 单位为kb(注意: 真实缓存大小还需要乘以处理线程数量)
        @param {bool} auto_expand=True - 是否自动扩展文件大小(否则在初始化时会自动创建指定大小的文件)
        @param {kwargs} - 扩展参数, 重载类自行扩展处理所需的参数
            conn_config {dict} - grpc的连接参数, 具体参数参考HiveNetGRpc.client.AIOGRpcClient的初始化函数
                注: use_sync_client参数无效, 将固定设置为True
        """
        # 自定义的参数
        self.conn_config = kwargs['conn_config']
        # 指定grpc客户端只能使用同步模式
        self.conn_config['use_sync_client'] = True

        # 创建连接线程池
        self._pool = AIOConnectionPool(
            AIOGRpcClient, GRpcPoolConnection, args=[self.conn_config], connect_method_name=None,
            max_size=max(thread_num, 10), min_size=0, connect_on_init=False,
            get_timeout=10, free_idle_time=10, ping_on_get=True,
            ping_on_back=False, ping_on_idle=True, ping_interval=5
        )

        # 执行父类的初始化函数
        super().__init__(
            src_file, dest_file, is_resume=is_resume, is_overwrite=is_overwrite,
            thread_num=thread_num, block_size=block_size, cache_size=cache_size,
            auto_expand=auto_expand, **kwargs
        )

    def __del__(self):
        """
        析构函数
        """
        # 关闭连接池
        AsyncTools.sync_run_coroutine(
            self._pool.close()
        )

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

        # 初始化远端的数据保存对象
        _ret = self._grpc_call(
            'push_transfer_init_saver', para_args=[self.dest_file], para_kwargs={
                'is_resume': self.is_resume, 'file_size': self._file_size, 'md5': self._file_md5,
                'is_overwrite': self.is_overwrite, 'extend_info': None, 'thread_num': self.thread_num,
                'block_size': self.block_size, 'cache_size': self.cache_size,
                'auto_expand': self.auto_expand
            }
        )

        # 修改本地参数
        self._saver = _ret['id']
        self.thread_num = _ret['thread_num']  # 线程数有可能被改变

    def destroy_saver(self):
        """
        销毁接收数据对象
        """
        self._grpc_call(
            'push_transfer_close', para_args=[self._saver]
        )

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
        self._writer_handles_lock.acquire()
        try:
            if index not in self._writer_handles.keys():
                # 新增写入对象属性(远程连接对象)
                self._writer_handles[index] = {
                    'handle': AsyncTools.sync_run_coroutine(self._pool.connection()),
                    'close_able': True, 'lock': threading.RLock(),
                    'req_queue': queue.Queue(),  # 用于向远端请求文件数据的队列
                    'ret_queue': queue.Queue(),  # 用于获取远端请求文件数据的队列
                }

                # 启动后台线程监控数据读取请求
                _write_data_thread = threading.Thread(
                    target=self._write_data_thread_fun,
                    args=(index, ),
                    name='Thread-gRpc-Write-Data'
                )
                _write_data_thread.setDaemon(True)
                _write_data_thread.start()

            # 返回打开的写入对象
            return self._writer_handles[index]

        finally:
            self._writer_handles_lock.release()

    def close_writer(self, index: int, is_force: bool = False):
        """
        关闭打开的写入对象

        @param {int} index - 要关闭的写入对象对应的处理线程索引
        @param {bool} is_force=False - 指示是否强制关闭
        """
        # 关闭远程连接
        self._writer_handles_lock.acquire()
        try:
            _writer_prop = self._writer_handles.pop(index, None)
            if _writer_prop is not None and _writer_prop['close_able']:
                _writer_prop['req_queue'].put(None)  # 通知文件获取不再请求
                if is_force:
                    # 强制删除即可
                    AsyncTools.sync_run_coroutine(
                        _writer_prop['handle'].close()
                    )
                else:
                    # 需要等待处理完成, 根据锁判断
                    if _writer_prop['lock'] is not None:
                        _writer_prop['lock'].acquire()
                    try:
                        AsyncTools.sync_run_coroutine(
                            _writer_prop['handle'].close()
                        )
                    finally:
                        if _writer_prop['lock'] is not None:
                            _writer_prop['lock'].release()
        finally:
            self._writer_handles_lock.release()

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
        lock.acquire()
        try:
            _writer_prop = self._writer_handles.get(index, None)
            if _writer_prop is None:
                raise RuntimeError('write_data error: index[%d] writer not opened!' % index)

            # 发送文件数据获取请求
            _writer_prop['req_queue'].put({
                'index': index, 'start': start, 'size': size, 'data': data
            })

            # 等待文件数据获取结果
            _info_dict = _writer_prop['ret_queue'].get()
            if not isinstance(_info_dict, dict):
                # 如果不是字典, 则为异常对象
                raise _info_dict

            # 返回处理结果
            return _info_dict
        finally:
            lock.release()

    def file_finished(self):
        """
        通知数据保存对象文件已结束
        """
        self._grpc_call(
            'push_transfer_finished', para_args=[self._saver]
        )

    def flush_cache(self):
        """
        强制将缓存数据写入实际文件
        """
        self._grpc_call(
            'push_transfer_flush', para_args=[self._saver]
        )

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
        return self._grpc_call(
            'push_transfer_get_save_info', para_args=[self._saver]
        )

    def get_extend_info(self) -> dict:
        """
        获取保存的扩展信息字典

        @returns {dict} - 返回保存的扩展信息字典
        """
        return self._grpc_call(
            'push_transfer_get_extend_info', para_args=[self._saver]
        )

    #############################
    # 内部函数
    #############################
    def _grpc_call(self, service_uri: str, para_args: list = None, para_kwargs: dict = None) -> dict:
        """
        通用的grpc远程函数调用

        @param {str} service_uri - 服务uri
        @param {list} para_args=None - 远程函数的入参
        @param {dict} para_kwargs=None - 远程函数的出参

        @returns {dict} - 返回结果字典
        """
        # 生成调用参数
        _request = RemoteCallFormater.paras_to_grpc_request(
            args=para_args, kwargs=para_kwargs,
        )

        # 获取连接
        _conn: AIOGRpcClient = AsyncTools.sync_run_coroutine(self._pool.connection())
        try:
            _result = AsyncTools.sync_run_coroutine(_conn.call(
                service_uri, _request
            ))
            _result = RemoteCallFormater.format_call_result(_result)
            if not _result.is_success():
                # 执行失败, 抛出异常
                raise RuntimeError('call %s error: %s' % (service_uri, str(_result)))

            # 返回json对象
            return _result.resp
        finally:
            # 释放连接
            AsyncTools.sync_run_coroutine(_conn.close())

    def _write_data_reqs_iter(self, index: int):
        """
        请求写入数据的迭代器

        @param {int} index - 文件索引

        @returns {Iterator} - grpc请求对象迭代器
        """
        _writer_prop = self._writer_handles.get(index, None)
        if _writer_prop is None:
            raise RuntimeError('_write_data_reqs_iter error: index[%d] writer not opened!' % index)

        # 循环获取请求数据
        _req_queue = _writer_prop['req_queue']
        _ret_queue = _writer_prop['ret_queue']
        while True:
            try:
                _req_info = _req_queue.get()
                if _req_info is None:
                    # 收到None代表结束处理
                    break

                # 生成grpc请求对象
                _req_obj = JsonRpcRequest(
                    para_json=StringTool.json_dumps_hive_net({
                        'index': index, 'start': _req_info['start'], 'size': _req_info['size']
                    }),
                    extend_bytes=_req_info['data']
                )

                # 返回迭代对象
                yield _req_obj
            except:
                # 执行出现异常, 将异常对象放入返回结果
                _ret_queue.put(sys.exc_info()[1])
                break

        return

    def _write_data_thread_fun(self, index: int):
        """
        监控并读取文件数据的后台线程函数

        @param {int} index - 要读取数据的线程索引
        """
        _writer_prop = self._writer_handles.get(index, None)
        if _writer_prop is None:
            raise RuntimeError(
                '_write_data_thread_fun error: index[%d] writer not opened!' % index)

        # 获取请求迭代器
        _iter_objs = self._write_data_reqs_iter(index)

        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            _iter_objs, args=[self._saver], kwargs={'index': index}
        )

        # 执行远程调用处理
        _result = AsyncTools.sync_run_coroutine(
            _writer_prop['handle'].call(
                'push_transfer_write_data', _request, call_mode=EnumCallMode.BidirectionalStream
            )
        )
        _result = RemoteCallFormater.format_call_result(_result)
        try:
            for _cresult in _result:
                if not _cresult.is_success():
                    # 执行失败, 抛出异常
                    _writer_prop['ret_queue'].put(
                        RuntimeError(
                            'call %s error: %s' %
                            ('push_transfer_write_data', str(_cresult))
                        ))
                    break

                # 放入处理结果
                _writer_prop['ret_queue'].put(_cresult.resp)
        except:
            # 异常停止, 返回异常后中止处理
            _writer_prop['ret_queue'].put({'status': 4, 'index': index, 'start': -1, 'size': 0})
            # _writer_prop['ret_queue'].put(sys.exc_info()[1])


class GRpcPullProtocol(LocalProtocol):
    """
    本地通过gRpc获取至远端文件的传输协议
    """

    def __init__(self, src_file: str, dest_file: str, is_resume: bool = True, is_overwrite: bool = False,
                 thread_num: int = 1, block_size: int = 4096, cache_size: int = 1024, auto_expand: bool = True,
                 **kwargs):
        """
        初始化文件传输协议类

        @param {str} src_file - 源文件路径(指的是远端服务器上的路径, 是约定工作目录的相对路径)
        @param {str} dest_file - 目标文件路径
        @param {bool} is_resume=True - 指定是否续传(自动查找已下载的信息), 如果不指定续传将自动删除原来已下载临时文件
        @param {bool} is_overwrite=False - 是否覆盖已有文件, 如果为否, 则目标文件已存在的情况下抛出异常
        @param {int} thread_num=1 - 写入处理线程数量
        @param {int} block_size=4096 - 每次传输块大小, 单位为byte
        @param {int} cache_size=1024 - 单线程缓存大小, 单位为kb(注意: 真实缓存大小还需要乘以处理线程数量)
        @param {bool} auto_expand=True - 是否自动扩展文件大小(否则在初始化时会自动创建指定大小的文件)
        @param {kwargs} - 扩展参数, 重载类自行扩展处理所需的参数
            conn_config {dict} - grpc的连接参数, 具体参数参考HiveNetGRpc.client.AIOGRpcClient的初始化函数
                注: use_sync_client参数无效, 将固定设置为True
        """
        # 自定义的参数
        self.conn_config = kwargs['conn_config']
        # 指定grpc客户端只能使用同步模式
        self.conn_config['use_sync_client'] = True

        # 创建连接线程池
        self._pool = AIOConnectionPool(
            AIOGRpcClient, GRpcPoolConnection, args=[self.conn_config], connect_method_name=None,
            max_size=max(thread_num, 10), min_size=0, connect_on_init=False,
            get_timeout=10, free_idle_time=10, ping_on_get=True,
            ping_on_back=False, ping_on_idle=True, ping_interval=5
        )

        # 执行父类的初始化函数
        super().__init__(
            src_file, dest_file, is_resume=is_resume, is_overwrite=is_overwrite,
            thread_num=thread_num, block_size=block_size, cache_size=cache_size,
            auto_expand=auto_expand, **kwargs
        )

    def __del__(self):
        """
        析构函数
        """
        # 关闭连接池
        AsyncTools.sync_run_coroutine(
            self._pool.close()
        )

    #############################
    # 文件读取的工具函数
    #############################

    def get_file_size(self) -> int:
        """
        获取文件的大小

        @returns {int} - 文件大小, 如果不支持获取文件大小返回 None
        """
        return self._grpc_call(
            'pull_transfer_get_file_size', para_args=[self.src_file]
        )

    def get_file_md5(self) -> str:
        """
        获取文件的md5值

        @returns {str} - 文件md5值, 如果获取不到md5值返回None
        """
        return self._grpc_call(
            'pull_transfer_get_file_md5', para_args=[self.src_file]
        )

    #############################
    # 文件读取的工具函数(需继承类实现)
    #############################
    def open_file(self, index: int = 0):
        """
        打开文件并返回文件对象

        @param {int} index=0 - 当前的数据处理线程索引

        @returns {dict} - 打开的文件对象属性字典
            {'handle': connection, 'close_able': 是否可关闭, lock: 锁对象, req_queue: 请求队列, ret_queue: 获取文件数据队列}
        """
        self._mutiple_read = True
        self._file_handles_lock.acquire()
        _file_dict = self._file_handles.get(index, None)
        self._file_handles_lock.release()

        if _file_dict is None:
            # 获取不到, 创建新文件访问对象
            _id = self._grpc_call(
                'pull_transfer_open_file_handle', para_args=[self.src_file]
            )['id']

            _lock = threading.RLock()
            _file_dict = {
                'handle': AsyncTools.sync_run_coroutine(self._pool.connection()),
                'close_able': True, 'lock': _lock,
                'file_id': _id,  # 已打开的文件访问id
                'req_queue': queue.Queue(),  # 用于向远端请求文件数据的队列
                'ret_queue': queue.Queue(),  # 用于获取远端请求文件数据的队列
            }
            self._file_handles_lock.acquire()
            self._file_handles[index] = _file_dict
            self._file_handles_lock.release()

            # 启动后台线程监控数据读取请求
            _read_file_data_thread = threading.Thread(
                target=self._read_file_data_thread_fun,
                args=(index, ),
                name='Thread-gRpc-Read-File-Data'
            )
            _read_file_data_thread.setDaemon(True)
            _read_file_data_thread.start()

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
                _file_dict['req_queue'].put(None)  # 通知文件获取不再请求
                self._file_handles.pop(index, None)
                AsyncTools.sync_run_coroutine(
                    _file_dict['handle'].close()
                )
        finally:
            self._file_handles_lock.release()

        # 关闭远程文件句柄
        if _file_dict is not None:
            self._grpc_call(
                'pull_transfer_close_file_handle', para_args=[_file_dict['file_id']]
            )

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
            _file_dict = self._file_handles.get(index, None)
            if _file_dict is None:
                raise RuntimeError('read_file_data error: index[%d] file not opened!' % index)

            # 发送文件数据获取请求
            _file_dict['req_queue'].put({
                'index': index, 'start': start, 'size': size
            })

            # 等待文件数据获取结果
            _bytes = _file_dict['ret_queue'].get()
            if type(_bytes) != bytes:
                # 非数据类型, 则为异常
                raise _bytes

            # 返回处理结果
            return _bytes
        finally:
            lock.release()

    #############################
    # 内部函数
    #############################
    def _grpc_call(self, service_uri: str, para_args: list = None, para_kwargs: dict = None) -> dict:
        """
        通用的grpc远程函数调用

        @param {str} service_uri - 服务uri
        @param {list} para_args=None - 远程函数的入参
        @param {dict} para_kwargs=None - 远程函数的出参

        @returns {dict} - 返回结果字典
        """
        # 生成调用参数
        _request = RemoteCallFormater.paras_to_grpc_request(
            args=para_args, kwargs=para_kwargs,
        )

        # 获取连接
        _conn: AIOGRpcClient = AsyncTools.sync_run_coroutine(self._pool.connection())
        try:
            _result = AsyncTools.sync_run_coroutine(_conn.call(
                service_uri, _request
            ))
            _result = RemoteCallFormater.format_call_result(_result)
            if not _result.is_success():
                # 执行失败, 抛出异常
                raise RuntimeError('call %s error: %s' % (service_uri, str(_result)))

            # 返回json对象
            return _result.resp
        finally:
            # 释放连接
            AsyncTools.sync_run_coroutine(_conn.close())

    def _read_file_data_reqs_iter(self, index: int):
        """
        请求文件数据的迭代器

        @param {int} index - 文件索引

        @returns {Iterator} - grpc请求对象迭代器
        """
        _file_dict = self._file_handles.get(index, None)
        if _file_dict is None:
            raise RuntimeError('read_file_data error: index[%d] file not opened!' % index)

        # 循环获取请求数据
        _req_queue = _file_dict['req_queue']
        _ret_queue = _file_dict['ret_queue']
        while True:
            try:
                _req_info = _req_queue.get()
                if _req_info is None:
                    # 收到None代表结束处理
                    break

                # 返回迭代对象
                yield {'start': _req_info['start'], 'size': _req_info['size']}
            except:
                # 执行出现异常, 将异常对象放入返回结果
                _ret_queue.put(sys.exc_info()[1])
                break

        return

    def _read_file_data_thread_fun(self, index: int):
        """
        监控并读取文件数据的后台线程函数

        @param {int} index - 要读取数据的线程索引
        """
        _file_dict = self._file_handles.get(index, None)
        if _file_dict is None:
            raise RuntimeError(
                '_read_file_data_thread_fun error: index[%d] file not opened!' % index)

        # 获取请求迭代器
        _req_objs = self._read_file_data_reqs_iter(index)
        _request = RemoteCallFormater.paras_to_grpc_request_iter(
            _req_objs, args=[_file_dict['file_id']]
        )

        # 执行双向流请求
        _result = AsyncTools.sync_run_coroutine(
            _file_dict['handle'].call(
                'pull_transfer_read_file_data', _request, call_mode=EnumCallMode.BidirectionalStream
            )
        )
        _result = RemoteCallFormater.format_call_result(_result)

        # 处理结果
        try:
            for _cresult in _result:
                if not _cresult.is_success():
                    # 执行失败, 抛出异常
                    _file_dict['ret_queue'].put(
                        RuntimeError(
                            'call %s error: %s' %
                            ('pull_transfer_read_file_data', str(_cresult))
                        ))
                    break

                # 放入处理结果
                _file_dict['ret_queue'].put(_cresult.extend_bytes)
        except:
            # 异常停止, 返回异常后中止处理
            _file_dict['ret_queue'].put(sys.exc_info()[1])


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
