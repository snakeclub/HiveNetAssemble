#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetPromptPlus import ProgressRate


class Test(unittest.TestCase):

    def test_progress_rate(self):
        # 测试进度值控制
        _pr = ProgressRate()
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 0.0, '1-获取进度值失败: %s' % str(_rate)
        )

        _set_rate = 10.0
        _set_next_rate = 30.0
        _pr.set_rate(_set_rate, _set_next_rate, split_len=10)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == _set_rate, '2-设置进度值失败: %s' % str(_rate)
        )

        _pr.add_rate_by_step()
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == _set_rate + 2, '3-通过步长设置进度值失败: %s' % str(_rate)
        )

        # 进入第2层
        _pr.into_next_level(30.0, 40.0)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 30.0, '4-失败: %s' % str(_rate)
        )

        _pr.set_rate(20.0)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 32.0, '5-失败: %s' % str(_rate)
        )

        _pr.set_rate(30.0)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 33.0, '6-失败: %s' % str(_rate)
        )

        # 进入第3层
        _pr.into_next_level(40.0, 50.0)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 34.0, '7-失败: %s' % str(_rate)
        )

        _pr.set_rate(10.0)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 34.1, '8-失败: %s' % str(_rate)
        )

        # 退出第3层
        _pr.exit_current_level()
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 35.0, '9-失败: %s' % str(_rate)
        )

        # 第2层进度
        _pr.set_rate(60)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 36.0, '10-失败: %s' % str(_rate)
        )

        _pr.set_rate(200)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 40.0, '11-失败: %s' % str(_rate)
        )

        # 退出第2层
        _pr.exit_current_level()
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 40.0, '12-失败: %s' % str(_rate)
        )

        # 第1层进度
        _pr.set_rate(18)
        _rate = _pr.get_current_rate()
        self.assertTrue(
            _rate == 18.0, '12-失败: %s' % str(_rate)
        )


if __name__ == '__main__':
    unittest.main()
