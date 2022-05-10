#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
连接池处理框架
@module connection_pool
@file connection_pool.py
"""

import os
import sys
import threading
import time
import asyncio
from logging import Logger
import traceback
from typing import Any
from HiveNetCore.utils.run_tool import AsyncTools
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


__MOUDLE__ = 'connection_pool'  # 模块名
__DESCRIPT__ = u'连接池处理框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2022.04.22'  # 发布日期


class TooManyConnections(Exception):
    """
    连接数已太多抛出的异常
    """
    pass


class AIOConnectionPool(object):
    """
    支持异步模式的连接池处理框架
    抽象连接池的公共方法形成框架, 并提供基本的处理功能, 简化连接池编程的难度
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, creator: Any, pool_connection_class: Any, args: list = [], kwargs: dict = {}, connect_method_name: str = 'connect',
            max_size: int = 100, min_size: int = 0, connect_on_init: bool = False,
            blocking: bool = True, blocking_interval: float = 0.1, get_timeout: float = 10, free_idle_time: float = 30,
            ping_on_get: bool = False, ping_on_back: bool = False, ping_on_idle: bool = True,
            ping_interval: float = 20, ping_args: list = [], ping_kwargs: dict = {},
            daemon_interval: float = 0.1, pool_extend_paras: dict = {}, logger: Logger = None):
        """
        初始化连接池

        @param {Any} creator - 连接创建模块或对象, 结合connect_method_name、args、kwargs创建连接
            如果connect_method_name不为None: conn = creator.connect_method_name(*args, **kwargs)
            如果connect_method_name为None: conn = creator(*args, **kwargs)
        @param {Any} pool_connection_class - 连接池连接对象实现类(继承PoolConnectionFW的类对象)
        @param {list} args=[] - 进行连接创建的固定位置参数
        @param {dict} kwargs={} - 进行连接创建的kv参数
        @param {str} connect_method_name='connect' - 连接创建模块要执行的连接方法, 传None代表直接使用creator创建连接
        @param {int} max_size=100 - 连接池的最大连接数
        @param {int} min_size=0 - 连接池中最少保持的连接数(空闲也不删除)
        @param {bool} connect_on_init=False - 是否在初始化时创建一个连接
        @param {bool} blocking=True - 当获取不到连接时是否阻塞等待, 如果为False则代表直接抛出异常
        @param {float} blocking_interval=0.1 - 获取连接阻塞时的循环间隔时长, 单位为秒
        @param {float} get_timeout=10 - 等待连接获取的超时时间, 单位为秒, 0或None代表永不超时
        @param {float} free_idle_time=30 - 释放空闲连接的时间, 单位为秒, 0或None代表永不释放
        @param {bool} ping_on_get=False - 是否在外部获取连接时先检查连接是否有效(注: 在ping_interval时间内不会检查)
        @param {bool} ping_on_back=False - 是否在外部发挥连接时检查连接是否有效(注: 在ping_interval时间内不会检查)
        @param {bool} ping_on_idle=True - 是否对空闲连接进行是否有效的检查
        @param {float} ping_interval=20 - 空闲连接有效检查的间隔时长, 单位为秒
        @param {list} ping_args=[] - 检查连接有效性的函数固定位置参数
        @param {dict} ping_kwargs={} - 检查连接有效性的函数kv参数
        @param {float} daemon_interval=1 - 守护程序的循环间隔时长, 单位为秒
        @param {dict} pool_extend_paras={} - 连接池的扩展参数, 可传递到连接对象使用的个性参数
        @param {Logger} logger=None - 日志对象
        """
        # 进行参数处理
        self._creator = creator  # 该变量直接就是连接方法
        self._pool_connection_class = pool_connection_class
        self._args = args
        self._kwargs = kwargs
        self._connect_method_name = connect_method_name
        if self._connect_method_name is not None:
            self._creator = getattr(creator, self._connect_method_name)
        self._min_size = max(1, min_size)
        self._max_size = max(1, min_size, max_size)
        self._blocking = blocking
        self._blocking_interval = blocking_interval
        self._get_timeout = 0 if get_timeout is None else max(0, get_timeout)
        self._free_idle_time = 0 if free_idle_time is None else max(0, free_idle_time)
        self._ping_on_get = ping_on_get
        self._ping_on_back = ping_on_back
        self._ping_on_idle = ping_on_idle
        self._ping_interval = 0 if ping_interval is None else max(0, ping_interval)
        self._ping_args = ping_args
        self._ping_kwargs = ping_kwargs
        self._daemon_interval = daemon_interval
        self._pool_extend_paras = pool_extend_paras
        self._logger = logger

        # 内部的控制变量
        self._is_closed = False  # 指示连接池被关闭的标识
        self._lock = threading.RLock()  # 控制连接对象获取的多线程锁
        self._size = 0  # 当前线程池的总线程数
        self._conn_cached = []  # 空闲连接缓存数组

        # 线程池的守护线程, 处理线程检查、释放等处理
        if self._free_idle_time > 0 or self._ping_on_idle:
            self._daemon_thread = threading.Thread(
                target=self.__start_daemon_thread_fun,
                args=(1,),
                name='DaemonThread-ConnectionPool'
            )
            self._daemon_thread.setDaemon(True)
            self._daemon_running = True
            self._daemon_thread.start()

        # 初始化连接
        if connect_on_init:
            self._lock.acquire()
            try:
                _conn = AsyncTools.sync_run_coroutine(self._create_connection())
                self._conn_cached.append(_conn)
                self._size += 1
            finally:
                self._lock.release()

    #############################
    # 属性
    #############################
    @property
    def current_size(self):
        """
        获取连接池当前大小

        @property {int} - 连接池当前大小
        """
        return self._size

    #############################
    # 公共函数
    #############################
    async def close(self):
        """
        关闭连接池
        """
        self._is_closed = True
        # 释放所有连接
        while self._size > 0:
            self._lock.acquire()
            try:
                _conn = self._conn_cached.pop()
                self._size -= 1
                # 关闭连接
                try:
                    await _conn._final_close()
                except:
                    pass
            except IndexError:
                # 没有空闲的连接, 等待下一次获取
                await asyncio.sleep(0.1)
            finally:
                self._lock.release()

    async def connection(self):
        """
        获取一个有效连接
        """
        _start_time = time.time()
        while True:
            # 尝试获取连接
            self._lock.acquire()
            try:
                try:
                    _conn = self._conn_cached.pop()
                except IndexError:
                    # 没有空闲的连接, 尝试创建新连接然后重新获取
                    _conn = None
                else:
                    # 获取到连接, 进行检查
                    if self._ping_on_get and self._ping_interval > 0 and (time.time() - _conn.last_ping) >= self._ping_interval:
                        if not await _conn.ping(*self._ping_args, **self._ping_kwargs):
                            # 连接已失效, 直接丢弃连接
                            _conn = None
                            self._size -= 1

                if _conn is not None:
                    # 返回连接
                    return _conn

                # 判断是否允许创建新连接
                if self._size >= self._max_size:
                    if self._blocking:
                        if self._get_timeout == 0 or (time.time() - _start_time) < self._get_timeout:
                            # 等待连接释放
                            await asyncio.sleep(self._blocking_interval)
                            continue
                        else:
                            raise TooManyConnections('Too many connetions')
                    else:
                        # 不阻塞, 直接抛出异常
                        raise TooManyConnections('Too many connetions')
                else:
                    # 创建一个新连接, 并直接返回
                    _conn = await self._create_connection()
                    self._size += 1
                    return _conn
            finally:
                self._lock.release()

    #############################
    # 内部函数
    #############################
    async def _create_connection(self) -> Any:
        """
        创建一个新连接

        @returns {Any} - 返回创建的PoolConnectionFW实现类对象
        """
        return self._pool_connection_class(
            self, self._creator, self._args, self._kwargs
        )

    async def back_to_pool(self, conn: Any):
        """
        将完成使用的连接归还到连接池

        @param {Any} conn - PoolConnectionFW实现对象
        """
        self._lock.acquire()
        try:
            # 是否检查连接有效性
            if self._ping_on_back and self._ping_interval > 0 and (time.time() - conn.last_ping) >= self._ping_interval:
                if not await conn.ping(*self._ping_args, **self._ping_kwargs):
                    # 连接已无效
                    self._size -= 1
                    return

            # 重新放回连接池
            self._conn_cached.append(conn)
        finally:
            self._lock.release()

    #############################
    # 守护线程
    #############################
    def __start_daemon_thread_fun(self, tid):
        """
        守护线程, 负责检查连接有效性和释放连接

        @param {int} tid - 线程id
        """
        while True:
            if self._is_closed:
                # 出现关闭标记，退出守护
                break

            # 检查需要释放的空闲连接
            self._lock.acquire()
            try:
                _cache_size = len(self._conn_cached)
                _remove_count = self._min_size - _cache_size
                if self._free_idle_time > 0 and _remove_count > 0:
                    while _remove_count > 0:
                        if (time.time() - self._conn_cached[0].last_back) > self._free_idle_time:
                            # 达到空闲释放时间
                            _conn = self._conn_cached.pop(0)
                            self._size -= 1
                            _remove_count -= 1
                            # 关闭连接
                            try:
                                AsyncTools.sync_run_coroutine(_conn._final_close())
                            except:
                                # 记录日志
                                if self._logger is not None:
                                    self._logger.warning(
                                        'close connection error: %s' % traceback.format_exc()
                                    )
                            # 继续检查下一个
                            continue
                        else:
                            # 第一个达不到时间, 其他返回的时间肯定更短, 无需再判断
                            break
            except:
                pass
            finally:
                self._lock.release()

            # 检查连接的有效性, 从后往前检查, 此外为了避免检查导致获取连接的阻塞, 采用逐个检查的方式
            if self._ping_on_idle:
                _index = len(self._conn_cached)
                while _index > 0:
                    self._lock.acquire()
                    try:
                        if len(self._conn_cached) < _index:
                            # 当前长度小于要获取的序号, 有可能检查对象被取出了, 继续检查前一个
                            _index -= 1
                            continue

                        _conn = self._conn_cached[_index - 1]
                        if (time.time() - _conn.last_ping) >= self._ping_interval:
                            # 需要进行检查
                            if not AsyncTools.sync_run_coroutine(_conn.ping(*self._ping_args, **self._ping_kwargs)):
                                # 连接已失效, 直接从连接池取出
                                self._conn_cached.pop(_index - 1)
                                self._size -= 1
                    except:
                        # 记录日志
                        if self._logger is not None:
                            self._logger.warning(
                                'connection ping error: %s' % traceback.format_exc()
                            )
                    finally:
                        self._lock.release()

                    # 继续检查下一个
                    _index -= 1

            # 等待下一次处理
            AsyncTools.sync_run_coroutine(asyncio.sleep(self._daemon_interval))


class PoolConnectionFW(object):
    """
    连接池的通用连接对象框架(封装实际的连接对象)
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, pool: AIOConnectionPool, creator: Any, args: list = [], kwargs: dict = {},
            logger: Logger = None):
        """
        构造函数

        @param {AIOConnectionPool} pool - 创建该连接的连接池对象
        @param {Any} creator - 连接创建模块或对象, 结合connect_method_name、args、kwargs创建连接
            如果connect_method_name不为None: conn = creator.connect_method_name(*args, **kwargs)
            如果connect_method_name为None: conn = creator(*args, **kwargs)
        @param {list} args=[] - 进行连接创建的固定位置参数
        @param {dict} kwargs={} - 进行连接创建的kv参数
        @param {Logger} logger=None - 日志对象
        """
        self._pool = pool
        self._logger = logger
        # 创建连接
        self._conn = AsyncTools.sync_run_coroutine(
            creator(*args, **kwargs)
        )
        self.last_ping = time.time()  # 记录上次检查的时间
        self.last_back = time.time()  # 记录上次返回连接池的时间

    #############################
    # 通过重写__getattr__把真实连接对象的属性和函数绑定在当前类
    #############################
    def __getattr__(self, name):
        """
        获取函数的属性和函数

        @param {str} name - 属性名
        """
        return getattr(self._conn, name)

    #############################
    # 通用函数
    #############################
    async def ping(self, *args, **kwargs) -> bool:
        """
        连接有效性的检查函数

        @returns {bool} - 返回检查结果
        """
        try:
            _ping_result = await AsyncTools.async_run_coroutine(self._real_ping(*args, **kwargs))
            if _ping_result:
                self.last_ping = time.time()

            return _ping_result
        except:
            # 出现异常视为失败
            if self._logger is not None:
                self._logger.warning(
                    'pool_connection ping error: %s' % traceback.format_exc()
                )
            return False

    async def close(self):
        """
        关闭连接
        """
        # 不是真实关闭, 而是返回连接池
        self._conn = await AsyncTools.async_run_coroutine(self._fade_close())
        await self._pool.back_to_pool(self)

    #############################
    # 内部函数
    #############################
    async def _final_close(self):
        """
        真正进行连接的关闭
        """
        await AsyncTools.async_run_coroutine(
            self._real_close()
        )

    #############################
    # 需要继承类实现的函数
    #############################
    async def _real_ping(self, *args, **kwargs) -> bool:
        """
        实现类的真实检查连接对象是否有效的的函数

        @returns {bool} - 返回检查结果
        """
        raise NotImplementedError()

    async def _fade_close(self) -> Any:
        """
        实现类提供的虚假关闭函数
        注1: 不关闭连接, 只是清空上一个连接使用的上下文信息(例如数据库连接进行commit或rollback处理)
        注2: 如果必须关闭真实连接, 则可以关闭后创建一个新连接返回

        @returns {Any} - 返回原连接或新创建的连接
        """
        raise NotImplementedError()

    async def _real_close(self):
        """
        实现类提供的真实关闭函数
        """
        raise NotImplementedError()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
