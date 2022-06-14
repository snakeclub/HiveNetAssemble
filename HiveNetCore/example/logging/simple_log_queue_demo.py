#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import datetime
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir
)))
import HiveNetCore.logging_hivenet as simple_log

__MOUDLE__ = 'simple_log_queue_demo'  # 模块名
__DESCRIPT__ = u'simple的队列方式示例代码'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.09.01'  # 发布日期


_TEMP_DIR = os.path.abspath(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)) + '/' +
    'test_data/temp/simple_log/').replace('\\', '/')


_LOGGER_QUEUE_MSG_JSON_STR = u'''{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "simpleFormatter": {
            "format": "heihei[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s",
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
        },

        "QueueMsgHandler": {
            "class": "HiveNetCore.logging_hivenet.QueueHandler",
            "level": "DEBUG",
            "formatter": "simpleFormatter",
            "queue": "",
            "topic_name": "",
            "is_deal_msg": true,
            "error_queue_size": 20
        },

        "QueueRecordHandler": {
            "class": "HiveNetCore.logging_hivenet.QueueHandler",
            "level": "DEBUG",
            "formatter": "simpleFormatter",
            "queue": "",
            "topic_name": "",
            "is_deal_msg": false,
            "error_queue_size": 20
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
        },

        "QueueMsg": {
            "level": "DEBUG",
            "handlers": ["QueueMsgHandler"],
            "propagate": "no"
        },

        "QueueRecord": {
            "level": "DEBUG",
            "handlers": ["QueueRecordHandler"],
            "propagate": "no"
        }
    },

    "root": {
        "level": "DEBUG",
        "handlers": []
    }
}
'''


write_logger = simple_log.Logger(logger_name='Console', logfile_path=os.path.join(_TEMP_DIR, 'demo.log'),
                                 json_str=_LOGGER_QUEUE_MSG_JSON_STR)


def deal_msg_fun1(topic_name, record):
    """
    消息对象处理函数1
    """
    msg = record.msg + str(record.name1Obj[0]) + str(record.name1Obj[1])
    return msg


def deal_msg_fun2(topic_name, record):
    """
    消息对象处理函数2
    """
    msg = record.msg + str(record.name2Obj[2]) + str(record.name2Obj[3])
    return msg


def log_fun(levelno, topic_name, msg):
    """
    日志处理函数
    """
    print('log_fun: %s, %s, %s' % (str(levelno), topic_name, msg))


def test_case1():
    """
    测试日志项record写入队列的模式
    """
    print('测试队列日志模式-对象处理')
    queue_logger = simple_log.Logger(logger_name='QueueRecord', logfile_path=os.path.join(_TEMP_DIR, 'demo.log'),
                                     json_str=_LOGGER_QUEUE_MSG_JSON_STR)

    # 将要处理消息的对象通过extra传入
    queue_logger.log(
        simple_log.INFO, 'INFO msg',
        extra={
            'topicName': 'name1',
            'name1Obj': ['1', '2', '3', '4']
        }
    )

    queue_logger.log(
        simple_log.DEBUG, 'DEBUG msg',
        extra={
            'topicName': 'name1',
            'name1Obj': ['5', '6', '7', '8']
        }
    )

    queue_logger.log(
        simple_log.CRITICAL, 'CRITICAL msg',
        extra={
            'topicName': 'name1',
            'name1Obj': ['9', '10', '11', '12']
        }
    )

    queue_logger.log(
        simple_log.WARNING, 'WARNING msg',
        extra={
            'topicName': 'name2',
            'name2Obj': ['9', '10', '11', '12']
        }
    )

    queue_logger.log(
        simple_log.ERROR, 'ERROR msg',
        extra={
            'topicName': 'name3',
            'name2Obj': ['a', 'b', 'c', 'd']
        }
    )

    # 异常的情况
    queue_logger.log(
        simple_log.ERROR, 'ERROR msg',
        extra={
            'topicName': 'name2',
            'name2Obj': ['a', 'b']
        }
    )

    # 获取handler
    queue_handler = queue_logger.base_logger.handlers[0]
    print('当前队列数 %s' % (str(queue_handler.queue.qsize())))

    print('等待5s再处理')
    time.sleep(5)
    print("当前时间：%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    # 处理队列信息
    queue_handler.start_logging(
        loggers_or_funs={
            "default": write_logger,
            'name3': log_fun
        },
        deal_msg_funs={
            "default": deal_msg_fun2,
            'name1': deal_msg_fun1,
            'name2': deal_msg_fun2
        }
    )

    print('等待5s后结束')
    time.sleep(5)

    # 打印错误信息
    error_obj = queue_handler.error_queue.get()
    print('error: %s, %s' % (error_obj.topic_name, error_obj.trace_str))

    # 结束日志队列处理
    queue_handler.stop_logging()
    print('测试队列日志模式-对象处理 -- 完成')


def test_case2():
    """
    测试日志完整信息写入队列的模式
    """
    print('测试队列日志模式-完整日志信息')
    queue_logger = simple_log.Logger(logger_name='QueueMsg', logfile_path=os.path.join(_TEMP_DIR, 'demo.log'),
                                     json_str=_LOGGER_QUEUE_MSG_JSON_STR)
    queue_logger.log(simple_log.INFO, 'INFO msg')
    queue_logger.log(simple_log.DEBUG, 'DEBUG msg')
    queue_logger.log(simple_log.CRITICAL, 'CRITICAL msg')
    queue_logger.log(simple_log.WARNING, 'WARNING msg')
    queue_logger.log(simple_log.ERROR, 'ERROR msg')

    # 获取handler
    queue_handler = queue_logger.base_logger.handlers[0]
    print('当前队列数 %s' % (str(queue_handler.queue.qsize())))

    print('等待5s再处理')
    time.sleep(5)
    print("当前时间：%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    # 处理队列信息
    queue_handler.start_logging(
        loggers_or_funs={
            "default": write_logger
        }
    )

    print('等待5s后结束')
    time.sleep(5)

    # 结束日志队列处理
    queue_handler.stop_logging()
    print('测试队列日志模式-完整日志信息 -- 完成')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))

    print("临时目录:" + _TEMP_DIR)

    # 执行
    test_case1()
    print('')
    test_case2()
