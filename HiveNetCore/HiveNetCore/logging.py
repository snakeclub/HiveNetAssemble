#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
简单日志模块

@module logging
@file logging.py
@see https://docs.python.org/zh-cn/3/howto/logging-cookbook.html
"""

import sys
import os
import os.path
import uuid
import datetime
import configparser
import shutil
import logging
import logging.config
import threading
import json
import traceback
from queue import Empty
from enum import Enum
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.generic import NullObj, CResult
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.string_tool import StringTool
from HiveNetCore.utils.exception_tool import ExceptionTool
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.queue import MemoryQueue


__MOUDLE__ = 'logging'  # 模块名
__DESCRIPT__ = u'简单日志模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


# 日志默认配置文件信息(INF格式)
_LOGGER_DEFAULT_CONF_STR = u'''###############################################
[loggers]
keys=root,Console,File,ConsoleAndFile

[logger_root]
level=DEBUG
handlers=

[logger_Console]
level=DEBUG
handlers=ConsoleHandler

[logger_File]
level=INFO
handlers=FileHandler
qualname=File
propagate=0

[logger_ConsoleAndFile]
level=DEBUG
handlers=ConsoleHandler,FileHandler
qualname=ConsoleAndFile
propagate=0

###############################################
[handlers]
keys=ConsoleHandler,FileHandler

[handler_ConsoleHandler]
class=StreamHandler
level=DEBUG
formatter=simpleFormatter
args=(sys.stdout,)

[handler_FileHandler]
class=handlers.RotatingFileHandler
level=INFO
formatter=simpleFormatter
args=('{$log_file_path$}', 'a', 10*1024*1024, 1000)

###############################################
[formatters]
keys=simpleFormatter
[formatter_simpleFormatter]
format=[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s
datefmt=%Y-%m-%d %H:%M:%S
'''

# 日志配置帮助信息
_LOGGER_HELP_CONF_STR = u'''###############################################
# 以下部分定义logger模块, root是父类, 必需存在的, 其它的是自定义的模块名(例子中的模块名是默认创建的, 使用者可以自行定义其他模块名)
# logging.getLogger(模块名称) 相当于向根据指定模块名的定义实例化一个日志操作对象
# 每个[logger_模块名称] 实际定义了一个模块名称和对应的处理句柄类
# level     日志输出级别, 有DEBUG、INFO、WARNING、ERROR、CRITICAL, 可设置不同级别进行日志的过滤
# handlers  处理句柄类, 一个日志模块可以引用多个处理句柄, 用逗号分开, 用来实现同一日志向多个地方输出
# qualname  logger名称, 应用程序通过 logging.getLogger获取。对于不能获取的名称, 则记录到root模块
# propagate 是否继承父类的log信息, 0:否 1:是
###############################################
[loggers]
keys=root,Console,File,ConsoleAndFile

[logger_root]
level=DEBUG
handlers=

[logger_Console]
level=DEBUG
handlers=ConsoleHandler

[logger_File]
handlers=FileHandler
qualname=File
propagate=0

[logger_ConsoleAndFile]
handlers=ConsoleHandler,FileHandler
qualname=ConsoleAndFile
propagate=0

###############################################
# 以下部分定义处理句柄及相关参数:
# [handlers] 指定配置里定义的句柄名清单
# [handler_句柄名] 定义了具体句柄的具体传入参数, 简要说明如下:
#     class - 句柄的类对象路径(按照python标准访问类的形式), 要求在代码中必须能通过该路径访问类
#     level - 句柄对应的日志级别, 可设置不同级别进行日志的过滤
#     formatter - 指定句柄对应的日志格式定义, 为[formatters]章节的格式名
#     args - 句柄类初始化的传入参数, 按照不同的句柄有不同的定义
#
# 可以使用python自带的句柄类、第三方库中的句柄类, 也可以自行开发自己的句柄类, 部分官方句柄类说明如下:
#     StreamHandler : 使用这个Handler可以向类似与sys.stdout或者sys.stderr的任何文件对象(file object)输出信息。它的构造函数是:
#         StreamHandler([strm])
#         其中strm参数是一个文件对象。默认是sys.stderr
#     FileHandler : 和StreamHandler类似, 用于向一个文件输出日志信息。不过FileHandler会帮你打开这个文件。它的构造函数是:
#         FileHandler(filename[,mode])
#         filename是文件名, 必须指定一个文件名。
#         mode是文件的打开方式。参见Python内置函数open()的用法。默认是’a', 即添加到文件末尾。
#     handlers.RotatingFileHandler : 这个Handler类似于上面的FileHandler, 但是它可以管理文件大小。当文件达到一定大小之后, 它会自动将当前日志文件改名, 然后创建一个新的同名日志文件继续输出。比如日志文件是chat.log。当chat.log达到指定的大小之后, RotatingFileHandler自动把文件改名为chat.log.1。不过, 如果chat.log.1已经存在, 会先把chat.log.1重命名为chat.log.2...;最后重新创建 chat.log, 继续输出日志信息。它的构造函数是:
#         RotatingFileHandler( filename[, mode[, maxBytes[, backupCount]]])
#         其中filename和mode两个参数和FileHandler一样。
#         maxBytes用于指定日志文件的最大文件大小。如果maxBytes为0, 意味着日志文件可以无限大, 这时上面描述的重命名过程就不会发生。
#         backupCount用于指定保留的备份文件的个数。比如, 如果指定为2, 当上面描述的重命名过程发生时, 原有的chat.log.2并不会被更名, 而是被删除。
###############################################
[handlers]
keys=ConsoleHandler,FileHandler

[handler_ConsoleHandler]
class=StreamHandler
level=DEBUG
formatter=simpleFormatter
args=(sys.stdout,)

[handler_FileHandler]
class=handlers.RotatingFileHandler
level=INFO
formatter=simpleFormatter
args=('myapp.log', 'a', 10*1024*1024, 1000)

###############################################
# 以下部分定义输出的格式和内容:
# [formatters] 指定配置里定义的格式名清单
# [formatter_格式名] 为具体格式名的配置, 里面有两个参数:
#     format - 定义输出日志的默认信息(前缀), 可选的信息项包括:
#        %(levelno)s: 打印日志级别的数值
#        %(levelname)s: 打印日志级别名称
#        %(pathname)s: 打印当前执行函数所在文件的路径
#        %(filename)s: 打印当前执行函数所在的文件名
#        %(funcName)s: 打印日志的当前函数名
#        %(lineno)d: 打印日志的当前行号
#        %(asctime)s: 打印日志的时间
#        %(millisecond)s: 打印日志的时间(毫秒, 不适用于官方的logging)
#        %(thread)d: 打印线程ID
#        %(threadName)s: 打印线程名称
#        %(process)d: 打印进程ID
#        %(message)s: 打印日志信息
#      datefmt - 定义日期时间(asctime)的输出格式, 默认为%Y-%m-%d %H:%M:%S,uuu
#         %y 两位数的年份表示(00-99)
#         %Y 四位数的年份表示(000-9999)
#         %m 月份(01-12)
#         %d 月内中的一天(0-31)
#         %H 24小时制小时数(0-23)
#         %I 12小时制小时数(01-12)
#         %M 分钟数(00=59)
#         %S 秒(00-59)
#         %a 本地简化星期名称
#         %A 本地完整星期名称
#         %b 本地简化的月份名称
#         %B 本地完整的月份名称
#         %c 本地相应的日期表示和时间表示
#         %j 年内的一天(001-366)
#         %p 本地A.M.或P.M.的等价符
#         %U 一年中的星期数(00-53)星期天为星期的开始
#         %w 星期(0-6), 星期天为星期的开始
#         %W 一年中的星期数(00-53)星期一为星期的开始
#         %x 本地相应的日期表示
#         %X 本地相应的时间表示
#         %Z 当前时区的名称
#         \%% %号本身(两个百分号)
#       注意: python并未给出毫秒的占位符, 因此如果datefmt为空输出格式才有毫秒, 如果要自己输出, 请采用%(millisecond)s占位符
###############################################
[formatters]
keys=simpleFormatter

[formatter_simpleFormatter]
format=[%(asctime)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s
datefmt=%Y-%m-%d %H:%M:%S.%f
'''


# JSON格式的日志配置文件默认字符串, 需注意disable_existing_loggers的设置, 如果为true会导致多个logger实例有被屏蔽的问题
_LOGGER_DEFAULT_JSON_STR = u'''{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "simpleFormatter": {
            "format": "[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },

    "handlers": {
        "ConsoleHandler": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simpleFormatter",
            "stream": "ext://sys.stdout"
        },

        "FileHandler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simpleFormatter",
            "filename": "{$log_file_path$}",
            "maxBytes": 10485760,
            "backupCount": 1000,
            "encoding": "utf8"
        }
    },

    "loggers": {
        "Console": {
            "level": "DEBUG",
            "handlers": ["ConsoleHandler"]
        },

        "File": {
            "level": "INFO",
            "handlers": ["FileHandler"],
            "propagate": "no"
        },

        "ConsoleAndFile": {
            "level": "DEBUG",
            "handlers": ["ConsoleHandler", "FileHandler"],
            "propagate": "no"
        }
    },

    "root": {
        "level": "DEBUG",
        "handlers": []
    }
}
'''

# JSON格式的日志终端输出默认字符串, 需注意disable_existing_loggers的设置, 如果为true会导致多个logger实例有被屏蔽的问题
_LOGGER_DEFAULT_JSON_CONSOLE_STR = u'''{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "simpleFormatter": {
            "format": "[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },

    "handlers": {
        "ConsoleHandler": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simpleFormatter",
            "stream": "ext://sys.stdout"
        }
    },

    "loggers": {
        "Console": {
            "level": "DEBUG",
            "handlers": ["ConsoleHandler"]
        }
    },

    "root": {
        "level": "DEBUG",
        "handlers": []
    }
}
'''

# 日志级别
DEBUG = logging.DEBUG  # 调试
INFO = logging.INFO  # 一般
WARNING = logging.WARNING  # 告警
ERROR = logging.ERROR  # 错误
CRITICAL = logging.CRITICAL  # 严重


class EnumLoggerName(Enum):
    """
    输出日志类型,用于编码时快捷获取输出日志类型字符内容

    @enum {string}

    """
    Console = 'Console'  # 输出到控制台
    File = 'File'  # 输出到文件
    ConsoleAndFile = 'ConsoleAndFile'  # 同时输出到屏幕和文件


class EnumLoggerConfigType(Enum):
    """
    日志配置方式

    @enum {string}

    """
    JSON_FILE = 'JSON_FILE'  # JSON格式配置文件
    INI_FILE = 'INI_FILE'  # INI格式配置文件
    JSON_STR = 'JSON_STR'  # JSON字符串
    XML_FILE = 'XML_FILE'  # XML格式配置文件


class SimpleLogFilter(logging.Filter):
    """
    增加Filter用于处理自定义的日志参数
    """

    def filter(self, record):
        """
        重载过滤器, 进行函数名和文件名的替换, 以及固定输入时间的替换
        """
        _bresult = logging.Filter.filter(self, record)
        if _bresult:
            if hasattr(record, 'callFunLevel'):
                # 增加变更日志真实触发函数的支持
                record.pathname = record.pathnameReal
                record.funcName = record.funcNameReal
                record.filename = record.filenameReal

            if hasattr(record, 'asctimeReal'):
                # 增加变更日志真实记录时间的支持
                record.asctime = record.asctimeReal

            if hasattr(record, 'millisecond'):
                # 增加时间中毫秒的支持
                record.millisecond = StringTool.fill_fix_string(str(round(record.msecs)), 3, '0')

            if hasattr(record, 'dealMsgFun'):
                # 增加自定义日志内容(msg)修改的支持
                if callable(record.dealMsgFun):
                    topic_name = ''
                    if hasattr(record, 'topicName'):
                        topic_name = record.topicName
                    record.msg = record.dealMsgFun(topic_name, record)

        # 返回结果
        return _bresult


class Logger(object):
    """
    日志输出类, 封装Python自带logging库的日志类, 简化日志类的配置和输出

    @example
        1、装载要使用的对象
        import HiveNetCore.logging as simple_log

        2、程序本地创建“logger.conf”文件, 修改配置文件为自己希望的内容
        注意: conf文件中请不要含中文内容, 原因是目前的程序对中文处理存在转码问题(问题待解决)
        主要修改的参数如下:
        (1)[handler_FileHandler]下的args参数:
            第1个参数是日志文件名(可以带路径), 日志程序会自动在扩展名前补充日期;
            第2个参数固定为追加模式;
            第3个参数为自动转存的文件大小, 单位为byte;
            第4个参数为自动转存时, 超过多少个文件后以覆盖方式记录(不会再新增)
        (2)[formatters]下的format参数, 该参数定义了日志的格式

        3、各个标签下的level级别, 修改为: DEBUG、INFO、WARNING、ERROR、CRITICAL中的一个

        4、使用方式
        # 实例化对象, 根据需要传入不同参数
        _logger = simple_log.Logger(...)

        # 写日志
        _logger.log(simple_log.INFO, '要写入的日志')
        # 其他写入方式
        _logger.info('要写入的INFO日志')
        _logger.debug('要写入的Debug日志')
    """

    #############################
    # 私有变量
    #############################
    __file_date = "20170101"  # 日志文件的日期
    __conf_file_name = "logger.conf"  # 日志配置文件的路径/或配置字符串
    __config_type = EnumLoggerConfigType.JSON_FILE
    __json_str = ''  # JSON_STR方式的字符集串
    __conf_tmp_file_name = "logger.conf.tmp20170101"  # 复制的日志文件临时路径
    __logger_name = "Console"  # 输出日志类型, Console - 输出屏幕 ,File - 输出到文件 , ConsoleAndFile - 同时输出到屏幕和文件
    __work_path = ""  # 工作路径
    __logfile_path = ""  # 日志文件的路径(含文件名)
    __logger = None  # 日志对象
    __logger_filter = None  # 日志的过滤器
    __thread_lock = None  # 保证多线程访问的锁
    __json_config = None  # json格式的配置信息
    __is_create_logfile_by_day = True  # 是否按天生成新的日志文件
    __call_fun_level = 0  # 调用log函数输出文件名和函数名的层级,0代表获取直接调用函数; 1代表获取直接调用函数的上一级

    #############################
    # 公共属性
    #############################
    @property
    def base_logger(self):
        """
        获取底层的logger对象, (logging.getLogger()对象)

        @property {logger}

        """
        return self.__logger

    #############################
    # 静态工具
    #############################
    @staticmethod
    def set_handler_log_level(handler, log_level):
        """
        设置指定handler的日志输出级别

        @param {object} handler - 要设置的handler对象, 可通过_logger.base_logger.handlers[i]获取
        @param {int} log_level - 日志级别(simple_log.DEBUG/INFO/WARNING/ERROR/CRITICAL)

        """
        handler.setLevel(log_level)

    @staticmethod
    def create_logger_by_dict(config_dict):
        """
        根据参数字典生成日志对象

        @param {dict} config_dict - 参数字典
            注: 通过 StringTool.xml_to_dict 函数解析xml配置产生的字典, 取logger节点内部的内容
            <logger>
                <conf_file_name></conf_file_name>
                <logger_name>Console</logger_name>
                <logfile_path></logfile_path>
                <config_type>JSON_STR</config_type>
                <json_str></json_str>
                <auto_create_conf>true</auto_create_conf>
                <is_create_logfile_by_day>true</is_create_logfile_by_day>
                <call_fun_level>0</call_fun_level>
            </logger>

        @return {simple_log.Logger} - 返回日志对象
        """
        # 根据字典生成日志参数
        _conf_file_name = None if config_dict['conf_file_name'] == '' else config_dict['conf_file_name']
        _logger_name = config_dict['logger_name']
        _logfile_path = config_dict['logfile_path']
        _config_type = eval('EnumLoggerConfigType.%s' % config_dict['config_type'])
        _json_str = config_dict['json_str']
        _auto_create_conf = (config_dict['auto_create_conf'] == 'true')
        _is_create_logfile_by_day = (config_dict['is_create_logfile_by_day'] == 'true')
        _call_fun_level = int(config_dict['call_fun_level'])
        # 返回日志对象
        return Logger(
            conf_file_name=_conf_file_name, logger_name=_logger_name, logfile_path=_logfile_path,
            config_type=_config_type, json_str=_json_str, auto_create_conf=_auto_create_conf,
            is_create_logfile_by_day=_is_create_logfile_by_day,
            call_fun_level=_call_fun_level
        )

    #############################
    # 构造函数
    #############################
    def __init__(self, conf_file_name=None, logger_name=EnumLoggerName.Console, logfile_path='',
                 config_type=EnumLoggerConfigType.JSON_STR, json_str=None, auto_create_conf=True,
                 is_create_logfile_by_day=True,
                 call_fun_level=0):
        """
        初始化日志类, 生成日志对象实例

        @param {string} conf_file_name=None - 日志配置文件路径和文件名:
            默认为'logger.conf', 如果找不到配置文件本函数会自动创带默认设置的配置文件
        @param {EnumLoggerName|string} logger_name=EnumLoggerName.Console - 输出日志类型,
            默认的3个类型如下: Console-输出到屏幕,File-输出到文件,ConsoleAndFile-同时输出到屏幕和文件;
            如果自己自定义了日志模块名, 可以直接使用字符串方式传值使用(例如'myLoggerName')
        @param {string} logfile_path='' - 日志输出文件的路径(含文件名), 如果已有配置文件的情况下该
            参数无效, 不传值时代表使用'log/程序名.log'来定义输出文件的路径
        @param {EnumLoggerConfigType} config_type=EnumLoggerConfigType.JSON_STR - 日志配置方式
        @param {string} json_str=None - 当日志配置方式为JSON_STR时使用, 配置的字符串,
            如果不串则默认使用_LOGGER_DEFAULT_JSON_CONSOLE_STR的值
        @param {bool} auto_create_conf=True - 是否自动创建配置文件(找不到指定的配置文件时), 默认为True
        @param {bool} is_create_logfile_by_day=True - 指定是否按天生成新的日志文件, 默认为True
        @param {int} call_fun_level=0 - 指定log函数输出文件名和函数名的层级, 当自己对日志函数再封装
            了几层的情况下, 无法打印到实际所需要登记的函数时, 可以指定从向上几级来获取真实调用函数;
            0代表获取直接调用函数; 1代表获取直接调用函数的上一级

        @example
            log = Logger(conf_file_name='/root/logger.conf', logger_name='ConsoleAndFile',
                        logfile_path="appname.log', auto_create_conf=True)
            log.log(simple_log.INFO, '输出日志内容'):

        """
        # 初始化变量
        self.__thread_lock = threading.Lock()  # 保证多线程访问的锁
        # 设置默认值
        self.__file_date = ''
        self.__conf_file_name = conf_file_name
        if self.__conf_file_name is None:
            if config_type == EnumLoggerConfigType.INI_FILE:
                self.__conf_file_name = 'logger.conf'
            elif config_type == EnumLoggerConfigType.XML_FILE:
                self.__conf_file_name = 'logger.xml'
            else:
                self.__conf_file_name = 'logger.json'
        self.__json_str = json_str
        if config_type == EnumLoggerConfigType.JSON_STR and json_str is None:
            self.__json_str = _LOGGER_DEFAULT_JSON_CONSOLE_STR
        self.__logger_name = logger_name
        if type(logger_name) == EnumLoggerName:
            self.__logger_name = logger_name.value
        self.__logfile_path = logfile_path
        self.__config_type = config_type
        self.__work_path = os.path.realpath(sys.path[0])
        if config_type in (EnumLoggerConfigType.INI_FILE, EnumLoggerConfigType.JSON_FILE):
            _path_dir, _path_file_name = os.path.split(os.path.realpath(self.__conf_file_name))
            self.__conf_tmp_file_name = (self.__work_path + os.sep + _path_file_name + '.tmp' +
                                         self.__file_date + str(uuid.uuid4()))
        self.__is_create_logfile_by_day = is_create_logfile_by_day
        self.__call_fun_level = call_fun_level
        self.__logger_filter = SimpleLogFilter()

        if auto_create_conf and config_type in (EnumLoggerConfigType.JSON_FILE, EnumLoggerConfigType.INI_FILE):
            # 判断文件是否存在, 如果不存在则按默认值创建文件
            self.__create_conf_file()
        elif self.__config_type == EnumLoggerConfigType.JSON_STR:
            # 不自动创建配置文件的情况下, 需要更新文件路径
            self.__json_str = self.__json_str.replace('{$log_file_path$}', logfile_path)

        # 如果是JSON格式, 先加载到对象
        if self.__config_type == EnumLoggerConfigType.JSON_STR:
            self.__json_config = json.loads(self.__json_str)
        elif self.__config_type == EnumLoggerConfigType.JSON_FILE:
            with open(self.__conf_file_name, 'rt', encoding='utf-8') as f:
                self.__json_config = json.load(f)
        elif self.__config_type == EnumLoggerConfigType.XML_FILE:
            with open(self.__conf_file_name, 'rt', encoding='utf-8') as f:
                self.__json_config = StringTool.object_to_json(
                    StringTool.xml_to_dict(f.read())['logger_conf']
                )

        # 如果要求按日记录日志, 则修改配置中的文件名, 加上日期
        if self.__is_create_logfile_by_day:
            self.__check_log_date()
        else:
            # 直接使用默认的配置
            if self.__config_type == EnumLoggerConfigType.INI_FILE:
                shutil.copyfile(self.__conf_file_name, self.__conf_tmp_file_name)
            # 生效配置
            self.__set_logger_config()

    def __del__(self):
        """
        当删除日志对象时, 删除对应的日志类实例

        """
        # 删除对象
        if self.__logger is not None:
            del self.__logger
            self.__logger = None

    #############################
    # 内部函数
    #############################
    @staticmethod
    def __get_date_str(dt):
        """
        获取yyyyMMdd格式的日期函数(内部函数), 将datetime转换为yyyyMMdd的字符串格式

        @param {datetime} dt - 要处理的日期变量

        @returns {string} - 转换后的日期字符串; 如果传入的不是datetime格式, 返回""

        """
        if isinstance(dt, datetime.datetime):
            return dt.strftime('%Y%m%d')
        else:
            return ""

    @staticmethod
    def __get_call_fun_frame(call_fun_level):
        """
        获取指定层级的调用函数框架(fake_frame), 从当前调用函数开始往逐级向上获取

        @param {int} call_fun_level - 要获取的函数名所属层级:
            -1 - 返回函数自身框架
            0 - 返回调用本函数的函数框架
            1 - 返回调用本函数的函数的上1级函数框架
            n - 返回调用本函数的函数的上n级函数框架

        @returns {fake_frame} - 返回指定层级函数的框架(fake_frame), 可以通过fake_frame.f_code获取代码相关信息

        """
        _ret_frame = sys._getframe()  # 要返回的函数框架
        if call_fun_level < 0:
            return _ret_frame
        _index = 0
        # 循环获取上一级函数的框架
        while _index <= call_fun_level:
            _ret_frame = _ret_frame.f_back
            _index = _index + 1
        return _ret_frame

    def __create_conf_file(self):
        """
        自动创建日志配置文件(内部函数), 检查类中指定的配置文件是否存在, 如果不存在则进行创建

        """
        _path_dir, _path_file_name = os.path.split(os.path.realpath(self.__conf_file_name))
        if not os.path.exists(_path_dir):
            # 路径不存在
            os.makedirs(_path_dir)

        if not os.path.exists(self.__conf_file_name):
            # 文件不存在, 如果日志文件路径为空, 则重新设置日志文件路径为工作目录下的log\发起模块名.log
            _temp_logfile_path = self.__logfile_path
            if self.__logfile_path == '':
                _temp_logfile_path = 'log/' + FileTool.get_exefile_name_no_ext() + '.log'

            # 文件不存在, 创建文件并写入特殊值
            with open(self.__conf_file_name, 'w+', encoding='utf-8') as f:
                if self.__config_type == EnumLoggerConfigType.INI_FILE:
                    f.write(_LOGGER_DEFAULT_CONF_STR.replace(
                        '{$log_file_path$}', _temp_logfile_path))
                elif self.__config_type == EnumLoggerConfigType.XML_FILE:
                    f.write(
                        StringTool.json_to_xml(
                            _LOGGER_DEFAULT_JSON_STR.replace(
                                '{$log_file_path$}', _temp_logfile_path),
                            root=True, custom_root='logger_conf', attr_type=True
                        )
                    )
                else:
                    f.write(_LOGGER_DEFAULT_JSON_STR.replace(
                        '{$log_file_path$}', _temp_logfile_path))

    def __create_log_dir(self):
        """
        遍历对应logger的配置并创建日志路径

        """
        if self.__config_type == EnumLoggerConfigType.INI_FILE:
            # conf配置文件
            _config = configparser.ConfigParser()
            try:
                _config.read(self.__conf_tmp_file_name)
                _loggers = _config.get('loggers', 'keys').split(',')
                for _logger_name in _loggers:
                    _handlers = _config.get('logger_%s' % _logger_name, 'handlers').split(',')
                    for _handler_name in _handlers:
                        if _config.get('handler_%s' % _handler_name, 'class').find('FileHandler') >= 0:
                            _file_args = _config.get('handler_%s' % _handler_name, 'args')
                            _dot_index = _file_args.find(',')
                            _temp_file_path = _file_args[2:_dot_index - 1].strip(' (,\'"')
                            _temp_path = os.path.split(os.path.realpath(_temp_file_path))[0]
                            if not os.path.exists(_temp_path):
                                FileTool.create_dir(_temp_path)
            finally:
                del _config
        else:
            # JSON, 要检索所有的handler进行处理
            for _handler_name in self.__json_config['handlers'].keys():
                if 'filename' in self.__json_config['handlers'][_handler_name].keys():
                    _temp_path = os.path.split(
                        os.path.realpath(self.__json_config['handlers'][_handler_name]['filename'])
                    )[0]
                    if not os.path.exists(_temp_path):
                        FileTool.create_dir(_temp_path)

    def __change_filepath_to_config(self, file_path='', handler_name=None, add_date_str=None):
        """
        修改日志配置中的文件路径(含文件名)
        遍历并修改日志配置中的文件路径, 如果是JSON, 只修改内存的对象即可:
        如果是INI文件, 则创建临时配置文件并进行修改

        @param {string} file_path='' - 要修改的文件路径(含文件名)
        @param {string} handler_name=None - 指定要修改的handler名称, 如果不传代表遍历所有并处理
        @param {string} add_date_str=None - 基于原配置增加日期字符串, 如果传入该值, file_path将不再生效

        """
        if self.__config_type == EnumLoggerConfigType.INI_FILE:
            # conf配置文件, 创建临时文件并修改临时文件的配置
            shutil.copyfile(self.__conf_file_name, self.__conf_tmp_file_name)
            _config = configparser.ConfigParser()
            try:
                _config.read(self.__conf_tmp_file_name)
                _handlers = _config.get('logger_%s' % self.__logger_name, 'handlers').split(',')
                for _handler_name in _handlers:
                    if _config.get('handler_%s' % _handler_name, 'class').find('FileHandler') >= 0:
                        if handler_name is None or handler_name == _handler_name:
                            _file_args = _config.get('handler_%s' % _handler_name, 'args')
                            _dot_index = _file_args.find(',')
                            if add_date_str is not None:
                                _temp_file_path = _file_args[2:_dot_index - 1].strip(' (,\'"')
                                _dot_index = _temp_file_path.rfind('.')
                                if _dot_index == -1:
                                    _temp_file_path = _temp_file_path + add_date_str
                                else:
                                    _temp_file_path = (_temp_file_path[0:_dot_index] + add_date_str +
                                                       _temp_file_path[_dot_index:])
                                # 修改配置
                                _file_args = "('%s'%s" % (_temp_file_path, _file_args[_dot_index:])
                            else:
                                _file_args = "('%s'%s" % (file_path, _file_args[_dot_index:])
                            _config.set('handler_%s' % _handler_name, 'args', _file_args)
                # 写回临时文件
                _file = open(self.__conf_tmp_file_name, 'w', encoding='utf-8')
                _config.write(_file)
                _file.close()
            finally:
                del _config
        else:
            # JSON, 根据遍历配置找到对应的handler进行修改
            _ori_json_config = None
            if add_date_str is not None:
                if self.__config_type == EnumLoggerConfigType.JSON_STR:
                    _ori_json_config = json.loads(self.__json_str)
                elif self.__config_type == EnumLoggerConfigType.JSON_FILE:
                    with open(self.__conf_file_name, 'rt', encoding='utf-8') as f:
                        _ori_json_config = json.load(f)
            _handlers = []
            _handlers = self.__json_config['loggers'][self.__logger_name]['handlers']

            # 修改文件路径
            for _handler_name in _handlers:
                if 'filename' in self.__json_config['handlers'][_handler_name].keys():
                    if handler_name is None or handler_name == _handler_name:
                        if add_date_str is not None:
                            _temp_file_path = _ori_json_config['handlers'][_handler_name]['filename']
                            _dot_index = _temp_file_path.rfind('.')
                            if _dot_index == -1:
                                _temp_file_path = _temp_file_path + add_date_str
                            else:
                                _temp_file_path = (_temp_file_path[0:_dot_index] + add_date_str
                                                   + _temp_file_path[_dot_index:])
                            # 修改配置
                            self.__json_config['handlers'][_handler_name]['filename'] = _temp_file_path
                        else:
                            self.__json_config['handlers'][_handler_name]['filename'] = file_path

    def __set_logger_config(self):
        """
        通过临时配置文件生成logging日志实例(内部函数)

        """
        # 根据新参数创建目录
        self.__create_log_dir()
        # 重新设置logger的参数
        if self.__logger is not None:
            del self.__logger
        if self.__config_type == EnumLoggerConfigType.INI_FILE:
            # INI配置文件方式
            try:
                logging.config.fileConfig(self.__conf_tmp_file_name)
            finally:
                os.remove(self.__conf_tmp_file_name)
        else:
            # JSON配置方式
            logging.config.dictConfig(self.__json_config)
        # 重新获取logger
        self.__logger = logging.getLogger(self.__logger_name)
        self.__logger.addFilter(self.__logger_filter)

    def __check_log_date(self):
        """
        检查并变更日志文件日期(内部函数)
        检查当前日期是否已发生变更, 如果已发生变更, 则修改临时配置文件并重新设置日志实例

        """
        # 检查当前日期是否与日志日期一致, 如果不是, 则重新装载文件配置
        if self.__is_create_logfile_by_day:
            try:
                self.__thread_lock.acquire()
                _now_date = self.__get_date_str(datetime.datetime.now())
                if _now_date != self.__file_date:
                    self.__file_date = _now_date
                    # 修改日志配置
                    self.__change_filepath_to_config(add_date_str=self.__file_date)
                    # 生效日志类
                    self.__set_logger_config()
            finally:
                self.__thread_lock.release()

    #############################
    # 公开方法
    #############################
    def log(self, level, msg, *args, **kwargs):
        """
        通过日志实例输出日志内容(兼容默认logging类的用法)

        @param {int} - 日志级别(simple_log.DEBUG/INFO/WARNING/ERROR/CRITICAL)
        @param {string} msg - 要输出的日志内容
        @param {*args} args - 通用日志类的args参数
        @param {**kwargs} args - 通用日子类的kwargs参数, 以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典, 可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}, 这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文:
                    callFunLevel {int} - 日志中输出的函数名(文件名)所属层级:
                        0 - 输出调用本函数的函数名(文件名)
                        1 - 输出调用本函数的函数的上1级函数的函数名(文件名)
                        n - 输出调用本函数的函数的上n级函数的函数名(文件名)
                    dealMsgFun {function} - 自定义日志内容修改函数, 可以在输出日志前动态修改日志内容(msg)
                        函数格式为funs(topic_name, record){return msg_string}, 返回生成后的日志msg内容
                    topicName {string} - 日志主题, 与dealMsgFun配套使用

        @example
            log = Logger(conf_file_name='/root/logger.conf',logger_name='ConsoleAndFile',
                logfile_path='appname.log',auto_create_conf=True)
            log.log(simple_log.ERROR, '输出日志内容')

        """
        self.__check_log_date()  # 检查日志文件是否要翻日
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # 增加毫秒的处理
        kwargs['extra']['millisecond'] = ''

        # 处理函数名等信息
        _frame = Logger.__get_call_fun_frame(kwargs['extra']['callFunLevel'] + 1)
        kwargs['extra']['pathnameReal'] = os.path.realpath(_frame.f_code.co_filename)
        _path_dir, kwargs['extra']['filenameReal'] = os.path.split(kwargs['extra']['pathnameReal'])
        kwargs['extra']['funcNameReal'] = _frame.f_code.co_name

        # 调用底层的日志类
        self.__logger.log(level, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """
        记录DEBUG级别的日志
        用于兼容logging的写日志模式提供的方法

        @param {string} msg - 要输出的日志内容
        @param {*args} args - 通用日志类的args参数
        @param {**kwargs} args - 通用日子类的kwargs参数, 以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典, 可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}, 这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文:
                    callFunLevel {int} - 日志中输出的函数名(文件名)所属层级:
                        0 - 输出调用本函数的函数名(文件名)
                        1 - 输出调用本函数的函数的上1级函数的函数名(文件名)
                        n - 输出调用本函数的函数的上n级函数的函数名(文件名)
                    dealMsgFun {function} - 自定义日志内容修改函数, 可以在输出日志前动态修改日志内容(msg)
                        函数格式为funs(topic_name, record){return msg_string}, 返回生成后的日志msg内容
                    topicName {string} - 日志主题, 与dealMsgFun配套使用

        """
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # callFunLevel + 1 保证函数的正确
        kwargs['extra']['callFunLevel'] += 1

        self.log(DEBUG, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        记录WARNING级别的日志
        用于兼容logging的写日志模式提供的方法

        @param {string} msg - 要输出的日志内容
        @param {*args} args - 通用日志类的args参数
        @param {**kwargs} args - 通用日子类的kwargs参数, 以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典, 可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}, 这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文:
                    callFunLevel {int} - 日志中输出的函数名(文件名)所属层级:
                        0 - 输出调用本函数的函数名(文件名)
                        1 - 输出调用本函数的函数的上1级函数的函数名(文件名)
                        n - 输出调用本函数的函数的上n级函数的函数名(文件名)
                    dealMsgFun {function} - 自定义日志内容修改函数, 可以在输出日志前动态修改日志内容(msg)
                        函数格式为funs(topic_name, record){return msg_string}, 返回生成后的日志msg内容
                    topicName {string} - 日志主题, 与dealMsgFun配套使用
        """
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # callFunLevel + 1 保证函数的正确
        kwargs['extra']['callFunLevel'] += 1

        self.log(WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """
        记录ERROR级别的日志
        用于兼容logging的写日志模式提供的方法

        @param {string} msg - 要输出的日志内容
        @param {*args} args - 通用日志类的args参数
        @param {**kwargs} args - 通用日子类的kwargs参数, 以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典, 可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}, 这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文:
                    callFunLevel {int} - 日志中输出的函数名(文件名)所属层级:
                        0 - 输出调用本函数的函数名(文件名)
                        1 - 输出调用本函数的函数的上1级函数的函数名(文件名)
                        n - 输出调用本函数的函数的上n级函数的函数名(文件名)
                    dealMsgFun {function} - 自定义日志内容修改函数, 可以在输出日志前动态修改日志内容(msg)
                        函数格式为funs(topic_name, record){return msg_string}, 返回生成后的日志msg内容
                    topicName {string} - 日志主题, 与dealMsgFun配套使用

        """
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # callFunLevel + 1 保证函数的正确
        kwargs['extra']['callFunLevel'] += 1

        self.log(ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        """
        记录ERROR级别的日志(处理异常信息)
        用于兼容logging的写日志模式提供的方法
        """
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # callFunLevel + 1 保证函数的正确
        kwargs['extra']['callFunLevel'] += 1

        self.log(ERROR, msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        记录CRITICAL级别的日志
        用于兼容logging的写日志模式提供的方法

        @param {string} msg - 要输出的日志内容
        @param {*args} args - 通用日志类的args参数
        @param {**kwargs} args - 通用日子类的kwargs参数, 以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典, 可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}, 这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文:
                    callFunLevel {int} - 日志中输出的函数名(文件名)所属层级:
                        0 - 输出调用本函数的函数名(文件名)
                        1 - 输出调用本函数的函数的上1级函数的函数名(文件名)
                        n - 输出调用本函数的函数的上n级函数的函数名(文件名)
                    dealMsgFun {function} - 自定义日志内容修改函数, 可以在输出日志前动态修改日志内容(msg)
                        函数格式为funs(topic_name, record){return msg_string}, 返回生成后的日志msg内容
                    topicName {string} - 日志主题, 与dealMsgFun配套使用

        """
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # callFunLevel + 1 保证函数的正确
        kwargs['extra']['callFunLevel'] += 1

        self.log(CRITICAL, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        记录INFO级别的日志
        用于兼容logging的写日志模式提供的方法

        @param {string} msg - 要输出的日志内容
        @param {*args} args - 通用日志类的args参数
        @param {**kwargs} args - 通用日子类的kwargs参数, 以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典, 可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}, 这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文:
                    callFunLevel {int} - 日志中输出的函数名(文件名)所属层级:
                        0 - 输出调用本函数的函数名(文件名)
                        1 - 输出调用本函数的函数的上1级函数的函数名(文件名)
                        n - 输出调用本函数的函数的上n级函数的函数名(文件名)
                    dealMsgFun {function} - 自定义日志内容修改函数, 可以在输出日志前动态修改日志内容(msg)
                        函数格式为funs(topic_name, record){return msg_string}, 返回生成后的日志msg内容
                    topicName {string} - 日志主题, 与dealMsgFun配套使用

        """
        # 获取参数并处理
        if 'extra' not in kwargs:
            kwargs['extra'] = dict()
        if 'callFunLevel' not in kwargs['extra'].keys():
            kwargs['extra']['callFunLevel'] = self.__call_fun_level

        # callFunLevel + 1 保证函数的正确
        kwargs['extra']['callFunLevel'] += 1

        self.log(INFO, msg, *args, **kwargs)

    def change_logger_name(self, logger_name):
        """
        修改输出日志类型配置

        @param {EnumLoggerName|string} logger_name - 输出日志类型, 默认为'Console':
            Console-输出到屏幕,File-输出到文件,ConsoleAndFile-同时输出到屏幕和文件
            如果没有自定义日志类型, 可以使用EnumLoggerName枚举值,用法为: EnumLoggerName.Console

        """
        self.__logger_name = logger_name
        if type(logger_name) == EnumLoggerName:
            self.__logger_name = logger_name.value
        if self.__is_create_logfile_by_day:
            self.__file_date = ''
            self.__check_log_date()
        else:
            try:
                self.__thread_lock.acquire()
                # 重新装载文件配置
                if self.__config_type == EnumLoggerConfigType.INI_FILE:
                    shutil.copyfile(self.__conf_file_name, self.__conf_tmp_file_name)
                # 生效配置
                self.__set_logger_config()
            finally:
                self.__thread_lock.release()

    def setLevelWithHandler(self, level):
        """
        设置日志对象的日志级别(同时修改loggername及handler的级别)

        @param {int} level - 日志级别(simple_log.DEBUG/INFO/WARNING/ERROR/CRITICAL)

        """
        self.__logger.setLevel(level)
        for _handler in self.__logger.handlers:
            _handler.setLevel(level)

    def setLevel(self, level):
        """
        动态设置日志logger的输出级别(只影响loggername的级别, 不影响handler的级别)

        @param {int} level - 日志级别(simple_log.DEBUG/INFO/WARNING/ERROR/CRITICAL)

        """
        self.__logger.setLevel(level)

    def set_logger_formater(self, format_str):
        """
        动态设置输出日志格式

        @param {string} format_str - 输出格式字符串, 参考conf文件中的format格式

        """
        _formater = logging.Formatter(format_str)
        for _handler in self.__logger.handlers:
            _handler.setFormatter(_formater)

    def get_logger_formater(self):
        """
        获取输出日志格式对象
        注意: 如果有多个handler则返回第一个handler的日志格式对象

        @return {logging.Formatter} - 日志对象的格式对象
        """
        for _handler in self.__logger.handlers:
            return _handler.formatter


class QueueHandler(logging.Handler):
    """
    内存队列日志处理Handler类
    将日志信息写入指定队列对象(通过handler.queue访问), 队列对象必须支持put(object)的方法, 每个传入的日志的对象信息如下:
        queue_obj.levelno {int} : 日志级别, 值说明参考logging.INFO这些值
        queue_obj.topic_name {string} : 日志主题标识(用于使用方区分日志来源),注意'default'为保留的标识名
        queue_obj.msg {string} : 已格式化后的日志内容, is_deal_msg为True时有效
        queue_obj.record {object} : 未格式化的日志相关信息, 其中record.msg为要写入的日志'%(message)s',
            is_deal_msg为False时有效
    如果使用自带的start_logging方法进行队列的处理, 当写日志出现异常时, 会将异常信息登记到handler.error_queue,
    注意该队列可以设置长度(避免内存占用过大), 当超过一定长度时会将前面的数据删除
        error_obj.topic_name - 日志主题标识
        error_obj.trace_str - 异常堆栈信息字符
    @example
        日志配置信息如下, 其中queue_var_name如果填""代表由handler对象自行生成队列, 为字符串时代表通过队列
        的变量名获取队列; topic_name为默认的日志主题名, 如果需要在写入时再定义主题名, 则通过extra参数的
        'topicName'参数传入; 最后一个参数为is_deal_msg, 代表是否处理日志格式, True代表直接生成完整的日志,
        将日志字符串写入队列, False代表不直接生成完整的日志消息, 而是将record对象放入队列(待后面的程序自动处理)
        [handler_queueHandler]
        class=HiveNetCore.logging.QueueHandler
        level=DEBUG
        formatter=logstashFormatter
        args=("queue_var_name", "topic_name", True)

    """
    #############################
    # 变量
    #############################

    queue = None  # 缓存日志的队列对象
    default_topic_name = ''  # 默认的日志主题
    error_queue = None  # 写日志出现异常时的异常记录
    _error_queue_size = 20  # 遇到异常时记录错误信息的队列大小
    _is_deal_msg = True

    # 队列中日志项处理的相关参数
    _loggers = None  # 要写入的日志logger对象列表, key为topic_name, value为对应的日志类Logger
    _thread_num = 1  # 处理队列对象的线程数
    _deal_msg_funs = None  # is_deal_msg为False时, 处理record的函数(形成msg部分内容)
    _formatters = None  # 如果is_deal_msg为False时, 原日志logger对象的formatter

    # 运行相关变量
    _logging_running = False  # 是否已启动日志处理
    _current_running_num = 0  # 当前正在执行的线程数
    _running_status_lock = None  # 处理线程执行状态锁
    _is_stop = False  # 标记是否结束处理线程

    #############################
    # 句柄的基础功能
    #############################
    def __init__(self, queue='', topic_name='', is_deal_msg=True, error_queue_size=20, ):
        """
        初始化队列日志Handler对象

        @param {string} queue='' - 要写入的队列对象, 可以传多种类型:
            '' or None - 代表由类自行生成FIFO队列, 可以通过handler.queue访问对象
            'queue_var_name' {string} - 传入外部生成的队列变量访问名称字符串
            queue_obj {object} - 直接传入队列对象
        @param {string} topic_name='' - 默认的日志主题, 当写日志的时候没有传topicName的扩展信息时使用
        @param {bool} is_deal_msg=True - 是否处理日志格式:
            True - 直接生成完整的日志, 将日志字符串写入队列
            False - 不直接生成完整的日志消息, 而是将record对象放入队列(待后面的程序自动处理)
        @param {int} error_queue_size=20 - 通过start_logging方法写日志时, 遇到异常时记录错误信息的队列大小,
            如果错误信息数量超过大小, 会自动删除前面的数据, 0代表不限制大小
        """
        # 初始化
        self._loggers = dict()  # 要写入的日志logger对象列表, key为topic_name, value为对应的日志类Logger
        self._deal_msg_funs = dict()  # is_deal_msg为False时, 处理record的函数(形成msg部分内容)
        self._formatters = dict()  # 如果is_deal_msg为False时, 原日志logger对象的formatter
        self._running_status_lock = threading.RLock()  # 处理线程执行状态锁

        # 处理入参
        self.default_topic_name = topic_name
        self._is_deal_msg = is_deal_msg

        # 获取队列对象
        if queue is None or queue == '':
            # 没有传值进来, 使用自己的队列
            self.queue = MemoryQueue()
        elif type(queue) == str:
            # 送入的是队列对象的变量名
            self.queue = eval(queue)
        else:
            # 直接送进来的是队列对象
            self.queue = queue

        # 异常队列信息
        self._error_queue_size = error_queue_size
        self.error_queue = MemoryQueue(maxsize=self._error_queue_size)

        # 调用handler默认方法
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            # 定义传入队列中的对象
            _queue_obj = NullObj()
            # 日志级别
            _queue_obj.levelno = record.levelno
            # topic_name
            if hasattr(record, 'topicName'):
                _queue_obj.topic_name = record.topicName
            else:
                _queue_obj.topic_name = self.default_topic_name
            # 日志内容
            if self._is_deal_msg:
                _queue_obj.msg = self.format(record)
            else:
                _queue_obj.record = record

            # 放入队列
            self.queue.put(_queue_obj)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def close(self):
        logging.Handler.close(self)

    #############################
    # 处理队列中日志内容的通用方法
    #############################
    def start_logging(self, loggers_or_funs, thread_num=1, deal_msg_funs={}, formatters=None):
        """
        启动线程处理日志队列的对象

        @param {dict} loggers_or_funs - 要写入的日志logger对象列表(或处理函数列表), key为topic_name, value为对应的
            处理日志类(HiveNetCore.logging.Logger)或处理函数, 其中'default'为默认日志处理类或处理函数,
            如果不传入则代表匹配不到的topic_name不进行处理, 规则如下: 遇到日志项的topic_name在列表中不存在, 先找'default'的日志对象进行处理,
            如果传入的日志对象清单中没有'default', 则不进行该日志项的处理
            如果传入的是处理函数, 格式为funs(levelno, topic_name, msg){...}
            注意: 如果为logger, 则所传入的日志对象的formatter将统一修改为'%(message)s', 因此该日志对象注意不要与其他日志处理共用
                 字典里可以支持logger和fun并存, 只是如果存在fun的情况, 应注意formatters的取值
        @param {int} thread_num=1 - 处理队列对象的线程数
        @param {dict} deal_msg_funs={} - 处理record的函数(形成msg部分内容), 当is_deal_msg为False时有效,
            key为topic_name, value为对应的日志内容生成函数,
            搜索函数的规则与loggers一样, 处理函数的定义应如下: func(topic_name, record) {return msg}
        @param {dict} formatters=None - is_deal_msg为False时, 用于格式化record的Formatter,
            key为topic_name, value为该topic_name的Formatter, 搜索格式对象的规则与loggers一样,
            如果formatters=None, 代表自动获取loggers的Formatter形成该字典

        @returns {CResult} - 启动结果, result.code: '00000'-成功, '21401'-服务不属于停止状态, 不能启动, 其他-异常
        """
        _result = CResult(code='00000')  # 成功
        self._running_status_lock.acquire()

        # 判断线程是否正在执行
        if self._logging_running:
            # 日志线程已启动
            _result = CResult(code='21401')  # 服务启动失败-服务已启动
        else:
            with ExceptionTool.ignored_cresult(_result, logger=None):
                # 参数处理
                self._loggers = loggers_or_funs
                self._thread_num = thread_num
                self._deal_msg_funs = deal_msg_funs
                self._formatters = formatters
                if formatters is None and not self._is_deal_msg:
                    self._formatters = dict()
                    # 获取loggers原来的Formatter对象
                    for _topic_name in loggers_or_funs.keys():
                        if not callable(loggers_or_funs[_topic_name]):
                            self._formatters[_topic_name] = loggers_or_funs[_topic_name].get_logger_formater(
                            )

                # 变更loggers的formater
                for _topic_name in self._loggers.keys():
                    if not callable(self._loggers[_topic_name]):
                        self._loggers[_topic_name].set_logger_formater('%(message)s')

                # 启动处理线程
                self._is_stop = False
                self._current_running_num = 0
                while self._current_running_num < self._thread_num:
                    _logging_thread = threading.Thread(
                        target=self.__logging_thread_fun,
                        args=(self._current_running_num,),
                        name='Thread-Logging-Queue'
                    )
                    _logging_thread.setDaemon(True)
                    _logging_thread.start()
                    self._current_running_num += 1

                # 更新运行状态
                self._logging_running = True

        # 处理完成
        self._running_status_lock.release()
        return _result

    def stop_logging(self):
        """
        停止处理日志队列的线程

        @returns {CResult} - 停止结果, result.code: '00000'-成功, '21402'-服务停止失败-服务已关闭,
            '29999'-其他系统失败
        """
        _result = CResult(code='00000')  # 成功
        self._running_status_lock.acquire()
        if not self._logging_running:
            _result = CResult(code='21402')  # 服务停止失败-服务已关闭
        else:
            with ExceptionTool.ignored_cresult(_result, logger=None):
                # 将标签设置为停止, 并等待结束
                self._is_stop = True
                while True:
                    if self._current_running_num <= 0:
                        break
                    RunTool.sleep(0.1)
                self._logging_running = False
        # 返回结果
        self._running_status_lock.release()
        return _result

    #############################
    # 内部方法
    #############################
    def __logging_thread_fun(self, tid):
        """
        处理日志线程函数

        @param {int} tid - 线程id

        """
        # 循环执行日志处理
        while True:
            # 判断是否要结束线程
            if self._is_stop:
                break

            # 执行处理, 尝试获取日志处理对象
            _log_obj = None
            try:
                _log_obj = self.queue.get(block=False)
                _logger = None
                if _log_obj.topic_name in self._loggers.keys():
                    _logger = self._loggers[_log_obj.topic_name]
                elif 'default' in self._loggers.keys():
                    _logger = self._loggers['default']
                else:
                    # 没有找到对应的logger, 不记录日志
                    RunTool.sleep(0.1)
                    continue

                # 处理日志内容
                _msg = ''
                if self._is_deal_msg:
                    # 直接写入即可
                    _msg = _log_obj.msg
                else:
                    # 要进行格式化再写入
                    _formatter = None
                    if _log_obj.topic_name in self._formatters.keys():
                        _formatter = self._formatters[_log_obj.topic_name]
                    elif 'default' in self._formatters.keys():
                        _formatter = self._formatters['default']
                    else:
                        # 找不到格式化的对象, 不记录日志
                        RunTool.sleep(0.1)
                        continue

                    # 内容处理函数
                    _deal_msg_fun = None
                    if _log_obj.topic_name in self._deal_msg_funs.keys():
                        _deal_msg_fun = self._deal_msg_funs[_log_obj.topic_name]
                    elif 'default' in self._deal_msg_funs.keys():
                        _deal_msg_fun = self._deal_msg_funs['default']
                    if _deal_msg_fun is not None:
                        _log_obj.record.msg = _deal_msg_fun(_log_obj.topic_name, _log_obj.record)

                    # 格式化日志信息
                    _msg = _formatter.format(_log_obj.record)

                # 记录日志或调用日志处理函数
                if callable(_logger):
                    # 调用处理函数
                    _logger(_log_obj.levelno, _log_obj.topic_name, _msg)
                else:
                    _logger.log(_log_obj.levelno, _msg)
            except Empty:
                # 获取不到数据继续循环
                RunTool.sleep(0.1)
            except:
                # 遇到异常情况, 将异常信息登记入堆栈
                _error_obj = NullObj()
                _error_obj.topic_name = _log_obj.topic_name
                _error_obj.trace_str = traceback.format_exc()
                # 放入队列, 如果队列满了则取出一个
                while True:
                    try:
                        self.error_queue.put(_error_obj, block=False)
                        break
                    except:
                        try:
                            self.error_queue.get(block=False)
                        except:
                            pass

        # 结束日志线程, 线程数减少
        self._current_running_num -= 1


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

    if len(sys.argv) > 1:
        _cmd = sys.argv[1].upper()
    else:
        _cmd = ''
        print('''帮助命令: python %s.py CONF/DEMO
    CONF - 配置文件说明
    DEMO - 演示代码执行''' % (__MOUDLE__))

    if _cmd == 'DEMO':
        # 执行实例代码
        def testfun(logger):
            logger.debug('testfun log 1')
            logger.log(logging.INFO, 'testfun log 2')

        _logroot = Logger(logger_name=EnumLoggerName.Console)
        _logroot.log(INFO, '仅输出界面信息 - INFO')
        _logroot.log(DEBUG, '仅输出界面信息 - DEBUG')
        _logroot.debug("haha")
        testfun(_logroot)

        _logroot.setLevel(INFO)
        _logroot.set_logger_formater('[%(asctime)s]%(message)s')
        _logroot.log(INFO, "修改日志级别及格式后输出 - INFO")
        _logroot.log(DEBUG, "修改日志级别及格式后输出 - DEBUG")

        # 停止日志服务
        del _logroot
    elif _cmd == 'CONF':
        # 展示配置文件说明
        print('\r\n 配置文件logger.conf的说明如下: ')
        print(_LOGGER_HELP_CONF_STR)
