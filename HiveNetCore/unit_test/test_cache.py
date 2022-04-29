#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试MemoryCache
@module test_cache
@file test_cache.py
"""

import time
import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.cache import EnumCacheSortedOrder, MemoryCache


__MOUDLE__ = 'test_cache'  # 模块名
__DESCRIPT__ = u'测试MemoryCache'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


class TestMemoryCache(unittest.TestCase):
    """
    测试MemoryCache类
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

    def test_memory_cache(self):
        """
        测试自动加载
        """
        # 有大小控制，按照访问时间优先规则处理
        cache_obj1 = MemoryCache(size=5, sorted_order=EnumCacheSortedOrder.HitTimeFirst)
        cache_obj1.update_cache('v1', 'value1')
        g1 = cache_obj1.get_cache('v1')
        self.assertTrue(g1 == 'value1', '查询缓存v1失败，查到:%s' % (g1))
        g1 = cache_obj1.get_cache('v2')
        self.assertTrue(g1 is None, '查询缓存v2不应存在，查到:%s' % (g1))
        time.sleep(0.01)
        cache_obj1.update_cache('v2', 'value2')
        time.sleep(0.01)
        cache_obj1.update_cache('v3', 'value3')
        time.sleep(0.01)
        cache_obj1.update_cache('v4', 'value4')
        time.sleep(0.01)
        cache_obj1.update_cache('v5', 'value5')
        time.sleep(0.01)
        g1 = cache_obj1.get_cache('v1')
        self.assertTrue(g1 == 'value1', '再次查询缓存v1失败，查到:%s' % (g1))
        time.sleep(0.01)
        cache_obj1.update_cache('v6', 'value6')
        g1 = cache_obj1.get_cache('v6')
        self.assertTrue(g1 == 'value6', '查询缓存v6失败，查到:%s' % (g1))
        g1 = cache_obj1.get_cache('v2')
        self.assertTrue(g1 is None, 'v2应按规则被删除，查到:%s' % (g1))

        # 有大小控制，按照访问次数优先规则处理
        cache_obj1 = MemoryCache(size=5, sorted_order=EnumCacheSortedOrder.HitCountFirst)
        cache_obj1.update_cache('b1', 'valueb1')
        g1 = cache_obj1.get_cache('b1')
        self.assertTrue(g1 == 'valueb1', '查询缓存b1失败，查到:%s' % (g1))
        time.sleep(0.01)
        cache_obj1.update_cache('b2', 'valueb2')
        g1 = cache_obj1.get_cache('b2')
        time.sleep(0.01)
        cache_obj1.update_cache('b3', 'valueb3')
        g1 = cache_obj1.get_cache('b3')
        time.sleep(0.01)
        cache_obj1.update_cache('b4', 'valueb4')
        g1 = cache_obj1.get_cache('b4')
        time.sleep(0.01)
        cache_obj1.update_cache('b5', 'valueb5')
        g1 = cache_obj1.get_cache('b5')
        time.sleep(0.01)
        g1 = cache_obj1.get_cache('b1')
        self.assertTrue(g1 == 'valueb1', '再次查询缓存b1失败，查到:%s' % (g1))
        time.sleep(0.01)
        cache_obj1.update_cache('b6', 'valueb6')
        g1 = cache_obj1.get_cache('b6')
        self.assertTrue(g1 == 'valueb6', '查询缓存b6失败，查到:%s' % (g1))
        g1 = cache_obj1.get_cache('b2')
        self.assertTrue(g1 is None, 'b2应按规则被删除，查到:%s' % (g1))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
