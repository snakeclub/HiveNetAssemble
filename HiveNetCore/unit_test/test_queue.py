#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试queue
@module test_queue
@file test_queue.py
"""

import os
import sys
import unittest
from queue import Full, Empty
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.queue_hivenet import MemoryQueue, EnumQueueType


__MOUDLE__ = 'test_queue'  # 模块名
__DESCRIPT__ = u'测试test_queue'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.08.02'  # 发布日期


class TestMemoryQueue(unittest.TestCase):
    """
    测试MemoryQueue类
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        pass

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_fifo(self):
        """
        测试先进先出
        """
        print('测试先进先出 - 非水桶模式')
        queue = MemoryQueue(queue_type=EnumQueueType.FIFO, maxsize=3)
        queue.put(1)
        queue.put(2)
        queue.put(3)

        # 插入失败 - 抛出异常
        try:
            print('队列已满, 插入等待2秒后超时')
            queue.put(4, timeout=2)
        except Full:
            print('正常超时返回')
        except:
            self.assertTrue(False, '测试先进先出 - 非水桶模式 - 放入对象超时失败-出现其他异常')

        # 插入失败, 直接返回
        try:
            print('队列已满, 插入不等待异常')
            queue.put(4, block=False)
        except Full:
            print('正常异常返回')
        except:
            self.assertTrue(False, '测试先进先出 - 非水桶模式 - 放入对象异常失败-出现其他异常')

        # 取数据
        _get_str = ('%d%d%d' % (queue.get(), queue.get(), queue.get()))
        self.assertTrue(
            '123' == _get_str,
            '测试先进先出 - 非水桶模式 - 获取数据失败 %s' % _get_str
        )

        # 空的情况取数据超时
        try:
            print('队列已空, 获取等待2秒后超时')
            queue.get(timeout=2)
        except Empty:
            print('正常超时返回')
        except:
            self.assertTrue(False, '测试先进先出 - 非水桶模式 - 获取对象超时失败-出现其他异常')

        # 获取失败, 直接返回
        try:
            print('队列已空, 获取不等待异常')
            queue.get(block=False)
        except Empty:
            print('正常异常返回')
        except:
            self.assertTrue(False, '测试先进先出 - 非水桶模式 - 获取对象异常失败-出现其他异常')

        print('测试先进先出 - 水桶模式')
        queue = MemoryQueue(queue_type=EnumQueueType.FIFO, maxsize=3, bucket_mode=True)
        queue.put(1)
        queue.put(2)
        queue.put(3)
        queue.put(4)
        # 取数据
        _get_str = ('%d%d%d' % (queue.get(), queue.get(), queue.get()))
        self.assertTrue(
            '234' == _get_str,
            '测试先进先出 - 水桶模式 - 获取数据失败 %s' % _get_str
        )

    def test_lifo(self):
        """
        测试后进先出
        """
        print('测试后进先出 - 非水桶模式')
        queue = MemoryQueue(queue_type=EnumQueueType.LIFO, maxsize=3)
        queue.put(1)
        queue.put(2)
        queue.put(3)
        # 取数据
        _get_str = ('%d%d%d' % (queue.get(), queue.get(), queue.get()))
        self.assertTrue(
            '321' == _get_str,
            '测试后进先出 - 非水桶模式 - 获取数据失败 %s' % _get_str
        )

        print('测试后进先出 - 水桶模式')
        queue = MemoryQueue(queue_type=EnumQueueType.LIFO, maxsize=3, bucket_mode=True)
        queue.put(1)
        queue.put(2)
        queue.put(3)
        queue.put(4)
        # 取数据
        _get_str = ('%d%d%d' % (queue.get(), queue.get(), queue.get()))
        self.assertTrue(
            '421' == _get_str,
            '测试后进先出 - 水桶模式 - 获取数据失败 %s' % _get_str
        )

    def test_priority(self):
        """
        测试优先级队列
        """
        print('测试优先级队列 - 非水桶模式')
        queue = MemoryQueue(queue_type=EnumQueueType.PRIORITY, maxsize=3)
        queue.put(1, priority=2)
        queue.put(2, priority=3)
        queue.put(3, priority=1)
        # 取数据
        _get_str = ('%d%d%d' % (queue.get(), queue.get(), queue.get()))
        self.assertTrue(
            '213' == _get_str,
            '测试优先级队列 - 非水桶模式 - 获取数据失败 %s' % _get_str
        )

        print('测试优先级队列 - 水桶模式')
        queue = MemoryQueue(queue_type=EnumQueueType.PRIORITY, maxsize=3, bucket_mode=True)
        queue.put(1, priority=2)
        queue.put(2, priority=3)
        queue.put(3, priority=1)
        queue.put(4, priority=1)
        # 取数据
        _get_str = ('%d%d%d' % (queue.get(), queue.get(), queue.get()))
        self.assertTrue(
            '134' == _get_str,
            '测试优先级队列 - 水桶模式 - 获取数据失败 %s' % _get_str
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
