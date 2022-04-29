#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
队列任务处理模块

@module queue
@file queue.py

"""

try:
    import threading
except ImportError:
    import dummy_threading as threading
from collections import deque
from heapq import heappush, heappop
from time import monotonic as time
import os
import sys
import operator
from enum import Enum
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
from queue import Full, Empty
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.utils.value_tool import ValueTool


__MOUDLE__ = 'queue'  # 模块名
__DESCRIPT__ = u'队列任务处理模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.30'  # 发布日期


class EnumQueueType(Enum):
    """
    队列类型

    @enum {int}

    """
    FIFO = 0  # 先进先出
    LIFO = 1  # 后进先出
    PRIORITY = 2  # 按优先级处理


class PriorityObject(object):
    """
    优先级对象类, 将一个对象封装为可按优先级排序的对象, 供MemoryQueue的PRIORITY类型队列使用

    """

    def __init__(self, obj, priority=0):
        """
        构造函数

        @param {object} obj - 需要构建的对象
        @param {int} priority=0 - 优先级, 数字越大优先级越高

        """
        self.priority = priority
        self.obj = obj
        return

    def __lt__(self, other):
        """
        比较函数
        """
        return self.priority > other.priority

    def __cmp__(self, other):
        """
        比较函数
        """
        return operator.lt(self.priority, other.priority)


class QueueFw(ABC):
    """
    基础队列处理框架, 用于定义队列的公共方法, 便于扩展不同的队列类型(例如支持各类MQ)
    框架基类重写了python基础库的Queue, 调用方法与Queue一致, 但增加了动态参数kwargs的扩展

    @param {**kwargs} kwargs - 队列初始化动态参数, 定义如下:
            maxsize=0 {int} - 队列深度, 如果为0代表不限制队列大小
            bucket_mode=False {bool} - 启动水桶模式, 队列大小达到上限后插入数据可自动丢弃老数据(get出来并丢弃)
            注: 其他定义参考具体的实例化类

    """

    #############################
    # 内部变量
    #############################
    _init_kwargs = {}  # 队列初始化参数

    #############################
    # 公共方法 - 无需实例对象实现
    #############################

    @property
    def init_kwargs(self):
        """
        获取初始化队列的参数

        @property {dict}

        """
        return self._init_kwargs

    def __init__(self, **kwargs):
        """
        构造函数

        @param {**kwargs} kwargs - 队列初始化动态参数, 定义如下:
            maxsize=0 {int} - 队列深度, 如果为0代表不限制队列大小
            bucket_mode=False {bool} - 启动水桶模式, 队列大小达到上限后插入数据可自动丢弃老数据(get出来并丢弃)
            注: 其他定义参考具体的实例化类

        """
        self._init_kwargs = kwargs
        _maxsize = ValueTool.get_dict_value('maxsize', kwargs, default_value=0)
        self.maxsize = _maxsize
        self.bucket_mode = ValueTool.get_dict_value('bucket_mode', kwargs, default_value=False)
        self._init(**kwargs)  # 改写部分, 增加动态参数支持

        # mutex must be held whenever the queue is mutating.  All methods
        # that acquire mutex must release it before returning.  mutex
        # is shared between the three conditions, so acquiring and
        # releasing the conditions also acquires and releases mutex.
        self.mutex = threading.Lock()

        # Notify not_empty whenever an item is added to the queue; a
        # thread waiting to get is notified then.
        self.not_empty = threading.Condition(self.mutex)

        # Notify not_full whenever an item is removed from the queue;
        # a thread waiting to put is notified then.
        self.not_full = threading.Condition(self.mutex)

        # Notify all_tasks_done whenever the number of unfinished tasks
        # drops to zero; thread waiting to join() is notified to resume
        self.all_tasks_done = threading.Condition(self.mutex)
        self.unfinished_tasks = 0

    def task_done(self, **kwargs):
        """
        任务完成通知, 用于支持生产者消费者模型处理
        由消费者线程每获取到一个队列对象, 完成处理后通过task_done通知队列任务完成
        队列机制是将队列待执行任务数-1, 以便于join函数判断队列任务是否已全部完成(已无待处理任务)

        @param {**kwargs} kwargs - 参数, 具体参数定义参考具体实现类

        """
        with self.all_tasks_done:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError('task_done() called too many times')
                self.all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished

    def join(self, **kwargs):
        """
        队列完成阻塞函数, 用于支持生产者消费者模型处理
        该函数必须与task_done通知配套使用, 当put一个任务到队列中, 待执行任务数+1；执行一次task_done, 待执行任务数-1
        当待执行任务数为0时, join执行退出

        @param {**kwargs} kwargs - 参数, 具体参数定义参考具体实现类

        """
        with self.all_tasks_done:
            while self.unfinished_tasks:
                self.all_tasks_done.wait()

    def qsize(self, **kwargs):
        """
        返回队列长度

        @param {**kwargs} kwargs - 参数, 具体参数定义参考具体实现类

        @returns {int} - 返回当前队列长度

        """
        with self.mutex:
            return self._qsize(**kwargs)

    def empty(self, **kwargs):
        """
        判断队列是否为空

        @param {**kwargs} kwargs - 其他判断参数, 具体参数定义参考具体实现类

        @returns {bool} - 如果队列为空, 返回True,反之返回False

        """
        with self.mutex:
            return not self._qsize(**kwargs)

    def full(self, **kwargs):
        """
        判断队列是否已满(无空闲空间)

        @param {**kwargs} kwargs - 其他判断参数, 具体参数定义参考具体实现类

        @returns {bool} - 如果队列为空, 返回True,反之返回False

        """
        with self.mutex:
            return 0 < self.maxsize <= self._qsize(**kwargs)

    def put(self, item, block=True, timeout=None, **kwargs):
        """
        将对象放入队列中

        @param {object} item - 要放进队列中的对象
            注意: 该对象建议是基础类型, 可序列化, 避免使用MQ等中间件传输后有问题
        @param {bool} block=True - 是否阻塞, 如果为True则待队列有空闲空间时放入成功才返回
        @param {number} timeout=None - 阻塞超时时间, 单位为秒
        @param {**kwargs} kwargs - 其他放置参数, 具体参数定义参考具体实现类

        @throws {queue.Full} - 遇到队列无空间放置时, 非阻塞模式直接抛出异常, 阻塞模式超时后抛出异常

        """
        with self.not_full:
            if self.maxsize > 0:
                if self.bucket_mode and self._qsize(**kwargs) >= self.maxsize:
                    # 水桶模式且已满, 直接抛弃掉可最先取出的对象
                    self._get(**kwargs)
                else:
                    if not block:
                        if self._qsize(**kwargs) >= self.maxsize:
                            raise Full
                    elif timeout is None:
                        while self._qsize(**kwargs) >= self.maxsize:
                            self.not_full.wait()
                    elif timeout < 0:
                        raise ValueError("'timeout' must be a non-negative number")
                    else:
                        endtime = time() + timeout
                        while self._qsize(**kwargs) >= self.maxsize:
                            remaining = endtime - time()
                            if remaining <= 0.0:
                                raise Full
                            self.not_full.wait(remaining)
            self._put(item, **kwargs)
            self.unfinished_tasks += 1
            self.not_empty.notify()

    def get(self, block=True, timeout=None, **kwargs):
        """
        从队列中获取对象

        @param {bool} block=True - 是否阻塞, 如果为True则待真正获取到数据才返回
        @param {number} timeout=None - 阻塞超时时间, 单位为秒
        @param {**kwargs} kwargs - 其他获取参数, 具体参数定义参考具体实现类

        @throws {queue.Empty} - 遇到队列为空时, 非阻塞模式直接抛出异常, 阻塞模式超时后抛出异常

        """
        with self.not_empty:
            if not block:
                if not self._qsize(**kwargs):
                    raise Empty
            elif timeout is None:
                while not self._qsize(**kwargs):
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = time() + timeout
                while not self._qsize(**kwargs):
                    remaining = endtime - time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self._get(**kwargs)
            self.not_full.notify()
            return item

    def put_nowait(self, item, **kwargs):
        """
        采取不阻塞的模式将对象放入队列

        @param {object} item - 要放进队列中的对象
            注意: 该对象建议是基础类型, 可序列化, 避免使用MQ等中间件传输后有问题
        @param {**kwargs} kwargs - 其他放置参数, 具体参数定义参考具体实现类

        @throws {queue.Full} - 遇到队列无空间放置时, 直接抛出异常

        """
        return self.put(item, block=False, **kwargs)

    def get_nowait(self, **kwargs):
        """
        采取不阻塞方式从队列中获取对象

        @param {**kwargs} kwargs - 其他获取参数, 具体参数定义参考具体实现类

        @throws {queue.Empty} - 遇到队列为空时, 直接抛出异常

        """
        return self.get(block=False, **kwargs)

    def clear(self, **kwargs):
        """
        清空队列

        @param {**kwargs} kwargs - 其他获取参数, 具体参数定义参考具体实现类
        """
        with self.not_empty:
            if not self._qsize(**kwargs):
                # 队列本身已为空
                return
            # 清空队列
            self._clear(**kwargs)

            # 通知队列未满
            self.not_full.notify()
            return

    #############################
    # 内部方法 - 抽象类
    #############################
    @abstractmethod
    def _init(self, **kwargs):
        """
        初始化队列

        @param {**kwargs} kwargs - 初始化参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError

    @abstractmethod
    def _qsize(self, **kwargs):
        """
        获取队列当前长度

        @param {**kwargs} kwargs - 获取长度参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError

    @abstractmethod
    def _put(self, item, **kwargs):
        """
        将对象放入队列

        @param {object} item - 要放进队列中的对象
        @param {**kwargs} kwargs - 放入参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError

    @abstractmethod
    def _get(self, **kwargs):
        """
        从队列中获取对象

        @param {**kwargs} kwargs - 获取参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError

    @abstractmethod
    def _clear(self, **kwargs):
        """
        清空队列

        @param {**kwargs} kwargs - 清空参数, 具体参数定义参考具体实现类

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        raise NotImplementedError


class MemoryQueue(QueueFw):
    """
    QueueFw的内存基础队列实现
    重新实现Python基础的Queue、LifoQueue和PriorityQueue
    注意: 该队列只能线程共享, 不能进程共享, 如果需进程共享, 可直接使用multiprocessing.Queue

    @param {**kwargs} kwargs - 初始化参数, 定义如下:
        queue_type {EnumQueueType} - 队列类型, 默认为EnumQueueType.FIFO
        maxsize=0 {int} - 队列深度, 如果为0代表不限制队列大小
        bucket_mode=False {bool} - 启动水桶模式, 队列大小达到上限后插入数据可自动丢弃老数据(get出来并丢弃)

    """

    #############################
    # 内部方法 - 继承实现
    #############################
    def _init(self, **kwargs):
        """
        初始化队列

        @param {**kwargs} kwargs - 初始化参数, 定义如下:
            queue_type {EnumQueueType} - 队列类型, 默认为EnumQueueType.FIFO
            maxsize=0 {int} - 队列深度, 如果为0代表不限制队列大小
            bucket_mode=False {bool} - 启动水桶模式, 队列大小达到上限后插入数据可自动丢弃老数据(get出来并丢弃)

        """
        self.queue_type = ValueTool.get_dict_value(
            'queue_type', kwargs, default_value=EnumQueueType.FIFO)
        if self.queue_type == EnumQueueType.FIFO:
            self.queue = deque()
        else:
            self.queue = []

    def _qsize(self, **kwargs):
        """
        获取队列当前长度

        @param {**kwargs} kwargs - 获取长度参数, 本实例无需传

        """
        return len(self.queue)

    def _put(self, item, **kwargs):
        """
        将对象放入队列

        @param {object} item - 要放进队列中的对象
        @param {**kwargs} kwargs - 放入参数
            priority {int} - 优先级, 默认为0, 数字越大优先级越高, 仅EnumQueueType.PRIORITY使用

        @throws {NotImplementedError} - 当实现类没有实现该方法时, 抛出该异常

        """
        if self.queue_type == EnumQueueType.FIFO:
            self.queue.append(item)
        elif self.queue_type == EnumQueueType.LIFO:
            self.queue.append(item)
        else:
            _item = PriorityObject(item, priority=ValueTool.get_dict_value(
                'priority', kwargs, default_value=0))
            heappush(self.queue, _item)

    def _get(self, **kwargs):
        """
        从队列中获取对象

        @param {**kwargs} kwargs - 获取参数, 具体参数定义参考具体实现类

        """
        if self.queue_type == EnumQueueType.FIFO:
            return self.queue.popleft()
        elif self.queue_type == EnumQueueType.LIFO:
            return self.queue.pop()
        else:
            return heappop(self.queue).obj

    def _clear(self, **kwargs):
        """
        清空队列

        @param {**kwargs} kwargs - 清空参数, 具体参数定义参考具体实现类

        """
        self.queue.clear()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
