#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir
)))
from HiveNetCore.utils.debug_tool import DebugTool
from HiveNetCore.utils.exception_tool import ExceptionTool
import HiveNetCore.logging_hivenet as simple_log
from debug_tool_demo_not_run import test_debugtools


__MOUDLE__ = 'debug_tool_demo'  # 模块名
__DESCRIPT__ = u'验证DebugTool跨模块打印功能'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


_TEMP_DIR = os.path.abspath(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)) + '/' +
    'test_data/temp/debug_tool/').replace('\\', '/')


def test_debugtools_1():
    # 测试DebugTools  -  跨模块的打印 - 增加日志类的干扰
    _logger = simple_log.Logger(conf_file_name=_TEMP_DIR + '/test_debugtools_1.json',
                                logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
                                config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
                                logfile_path=_TEMP_DIR + '/log/test_debugtools_1.log')
    _logger.log(simple_log.DEBUG,
                'test_debugtools_1:write_log:DEBUG:1:界面应显示本日志，文件不应显示本日志')
    _logger.log(simple_log.INFO,
                'test_debugtools_1:write_log:INFO:2:界面应显示本日志，文件应显示本日志')
    del _logger

    DebugTool.set_debug(True)
    DebugTool.debug_print("自己本模块的打印")
    test_debugtools()
    return


def test_excepitontools_1():
    # 测试异常工具的处理机制
    _logger2 = simple_log.Logger(
        conf_file_name=_TEMP_DIR + '/test_excepitontools_1.json',
        logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
        config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
        logfile_path=_TEMP_DIR + '/log/test_excepitontools_1.log',
        call_fun_level=1
    )
    _logger2.setLevel(simple_log.DEBUG)
    _logger2.log(simple_log.INFO, 'test log', extra={'callFunLevel': 0})

    with ExceptionTool.ignored_all(logger=_logger2, self_log_msg='测试异常处理：'):
        print("test_excepitontools_1 step 1")
        print("test_excepitontools_1 step 2")
        print("test_excepitontools_1 step 3")
        1 / 0
        print("test_excepitontools_1 step 4 - 不应打印")
        print("test_excepitontools_1 step 5 - 不应打印")

    print("test_excepitontools_1 step 6 - 退出后的打印信息")

    del _logger2


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

    test_debugtools_1()

    test_excepitontools_1()
