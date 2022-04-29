#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir
)))
from HiveNetCore.utils.file_tool import FileTool
import HiveNetCore.logging as simple_log

__MOUDLE__ = 'simple_log_demo'  # 模块名
__DESCRIPT__ = u'simple示例代码'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


_TEMP_DIR = os.path.abspath(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)) + '/' +
    'test_data/temp/simple_log/').replace('\\', '/')


def test_case1():
    # 测试单日志最基本功能，日志输出，变更日志级别，修改日志格式
    # 删除临时日志
    try:
        FileTool.remove_file(_TEMP_DIR + '/test_case1.json')
        print('del %s%s' % (_TEMP_DIR, '/test_case1.json'))
    except:
        pass

    try:
        FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case1*')
    except:
        pass

    _logger = simple_log.Logger(conf_file_name=_TEMP_DIR + '/test_case1.json',
                                logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
                                config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
                                logfile_path=_TEMP_DIR + '/log/test_case1.log')
    # ConsoleAndFile 的配置level为DEBUG，但对应的ConsoleHandler的level为DEBUG，FileHandler的level为INFO
    # 日志是否显示会根据logger的level和handler的level，以级别比较高的匹配输出
    # 注意默认root的handler应该为空，否则无论如何都会执行root的输出，如果自己又另外指定了输出，那就会有2个相同输出日志
    _logger.log(simple_log.DEBUG,
                'test_case1:write_log:DEBUG:1:界面应显示本日志，文件不应显示本日志')
    _logger.debug('test_case1:write_log:DEBUG:1-1:界面应显示本日志，文件不应显示本日志')
    _logger.log(simple_log.INFO,
                'test_case1:write_log:INFO:2:界面应显示本日志，文件应显示本日志')
    _logger.info('test_case1:write_log:INFO:2-1:界面应显示本日志，文件应显示本日志')

    # 修改ConsoleAndFile的level为INFO，handler仍不变
    _logger.setLevel(simple_log.INFO)
    _logger.log(simple_log.DEBUG,
                'test_case1:write_log:DEBUG:3:界面不应显示本日志，文件不应显示本日志')
    _logger.log(simple_log.INFO,
                'test_case1:write_log:INFO:4:界面应显示本日志，文件应显示本日志')

    # 修改ConsoleAndFile的level为DEBUG, FileHandler的level为WARNING
    _logger.setLevel(simple_log.DEBUG)
    for _handler in _logger.base_logger.handlers:
        if _handler.name == 'FileHandler':
            _logger.set_handler_log_level(_handler, simple_log.WARNING)
    _logger.log(simple_log.DEBUG,
                'test_case1:write_log:DEBUG:5:界面应显示本日志，文件不应显示本日志')
    _logger.log(simple_log.WARNING,
                'test_case1:write_log:WARNING:6:界面应显示本日志，文件应显示本日志')

    #  修改整个日志级别为INFO
    _logger.setLevel(simple_log.INFO)
    _logger.log(simple_log.DEBUG,
                'test_case1:write_log:DEBUG:7:界面不应显示本日志，文件不应显示本日志')
    _logger.log(simple_log.INFO,
                'test_case1:write_log:INFO:8:界面应显示本日志，文件应显示本日志')

    # 修改日志类型为Console，日志级别应根据配置文件恢复原状态（DEBUG）
    _logger.change_logger_name(logger_name=simple_log.EnumLoggerName.Console)
    _logger.log(simple_log.DEBUG,
                'test_case1:write_log:DEBUG:9:界面应显示本日志，文件不应显示本日志')

    # 修改日志输出格式
    _logger.set_logger_formater(format_str='[%(asctime)s]%(message)s')
    _logger.log(simple_log.DEBUG,
                'test_case1:write_log:DEBUG:9:格式发生变化，界面应显示本日志，文件不应显示本日志')

    del _logger


def test_case2():
    # 测试多个日志类相互影响的情况
    try:
        FileTool.remove_file(_TEMP_DIR + '/test_case2.json')
    except:
        pass
    try:
        FileTool.remove_file(_TEMP_DIR + '/test_case2-1.json')
    except:
        pass

    try:
        FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case2*')
    except:
        pass
    try:
        FileTool.remove_files(path=_TEMP_DIR + '/log/', regex_str='test_case2-1*')
    except:
        pass

    _logger = simple_log.Logger(conf_file_name=_TEMP_DIR + '/test_case2.json',
                                logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
                                config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
                                logfile_path=_TEMP_DIR + '/log/test_case2.log')
    # ConsoleAndFile 的配置level为DEBUG，但对应的ConsoleHandler的level为DEBUG，FileHandler的level为INFO
    # 日志是否显示会根据logger的level和handler的level，以级别比较高的匹配输出
    # 注意默认root的handler应该为空，否则无论如何都会执行root的输出，如果自己又另外指定了输出，那就会有2个相同输出日志
    _logger.log(simple_log.DEBUG,
                'test_case2:write_log:DEBUG:1:界面应显示本日志，文件不应显示本日志')
    _logger.debug('test_case2:write_log:DEBUG:1-1:界面应显示本日志，文件不应显示本日志')
    _logger.log(simple_log.INFO,
                'test_case2:write_log:INFO:2:界面应显示本日志，文件应显示本日志')
    _logger.info('test_case2:write_log:INFO:2-1:界面应显示本日志，文件应显示本日志')

    # 新增logger，但与原logger的loggername一样，实际上会互相影响，同时如果handler一样，也会受影响
    _logger1 = simple_log.Logger(conf_file_name=_TEMP_DIR + '/test_case2-1.json',
                                 logger_name=simple_log.EnumLoggerName.ConsoleAndFile,
                                 config_type=simple_log.EnumLoggerConfigType.JSON_FILE,
                                 logfile_path=_TEMP_DIR + '/log/test_case2-1.log')
    _logger1.setLevel(simple_log.DEBUG)

    _logger.log(simple_log.DEBUG,
                'test_case2:write_log:DEBUG:3:界面应显示本日志，文件不应显示本日志,但实际受logger1影响，也记录了日志；本应记录在日志1中，但受影响记录在日志2中')
    _logger.log(simple_log.INFO,
                'test_case2:write_log:INFO:4:界面应显示本日志，文件应显示本日志；本应记录在日志1中，但受影响记录在日志2中')
    _logger1.log(simple_log.DEBUG,
                 'test_case2:write_log:DEBUG:5-1:界面应显示本日志，文件应显示本日志')
    _logger1.log(simple_log.INFO,
                 'test_case2:write_log:INFO:6-1:界面应显示本日志，文件应显示本日志')

    del _logger

    _logger1.log(simple_log.DEBUG,
                 'test_case2:write_log:DEBUG:6-1:界面应显示本日志，文件应显示本日志')
    _logger1.log(simple_log.INFO,
                 'test_case2:write_log:INFO:7-1:界面应显示本日志，文件应显示本日志')

    del _logger1


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

    #
    print("临时目录:" + _TEMP_DIR)

    # 测试单日志最基本功能，日志输出，变更日志级别，修改日志格式
    test_case1()

    # 测试多个日志类相互影响的情况
    test_case2()
