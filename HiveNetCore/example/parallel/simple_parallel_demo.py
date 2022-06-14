#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
并发任务示例
@module simple_parallel_demo
@file simple_parallel_demo.py
"""

import sys
import os
import time
import multiprocessing
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir
)))
from HiveNetCore.logging_hivenet import EnumLoggerName, Logger, EnumLoggerConfigType
from HiveNetCore.parallel import ThreadParallel, ProcessParallel, ProcessParallelShareDict, ProcessParallelLock, ParallelPool
from HiveNetCore.utils.import_tool import ImportTool


# 通用的logger
_logger = Logger(conf_file_name=None, logger_name=EnumLoggerName.Console,
                 config_type=EnumLoggerConfigType.JSON_STR)


# 通用的logger创建参数
_logger_kwargs = {
    'conf_file_name': None,
    'logger_name': EnumLoggerName.Console,
    'config_type': EnumLoggerConfigType.JSON_STR
}


# 通用的并发任务处理函数
def demo_deal_fun(a, b, c, p1='', p2=''):
    print('demo_deal_fun print: a=%s, b=%s, c=%s, p1=%s, p2=%s' % (
        str(a), str(b), str(c), str(p1), str(p2)
    ))
    time.sleep(0.1)
    _ret = ('demo_deal_fun:r1-%s' % (str(a)), 'demo_deal_fun:r2')
    print('demo_deal_fun print: return=%s' % (str(_ret)))
    return _ret


# 通用的并发任务回调函数
def demo_callback(id, name, call_result, deal_fun_ret):
    print('demo_callback print: id=%s, name=%s, call_result=%s, deal_fun_ret=%s' % (
        str(id), str(name), str(call_result), str(deal_fun_ret)
    ))
    return


# 示例1，多线程任务处理
def demo1():
    print('demo1 create Thread ...\n')
    _t1 = ThreadParallel(
        deal_fun=demo_deal_fun, run_args=('demo1-a-1', 'demo1-b-1', 'demo1-c-1'),
        run_kwargs={'p1': 'demo1-p1-1', 'p2': 'demo1-p2-1'}, pid='demo1-t1', pname='demo1-t1-name',
        callback_fun=demo_callback, set_daemon=True, logger=_logger
    )

    _t2 = ThreadParallel(
        deal_fun=demo_deal_fun, run_args=('demo1-a-2', 'demo1-b-2', 'demo1-c-2'),
        run_kwargs={'p1': 'demo1-p1-2', 'p2': 'demo1-p2-2'}, pid='demo1-t2', pname='demo1-t2-name',
        callback_fun=demo_callback, set_daemon=True, logger=_logger
    )

    print('\ndemo1 start Thread ...\n')
    _t1.start()
    _t2.start(run_args=('demo1-a-2-add', 'demo1-b-2', 'demo1-c-2'))

    print('\ndemo1 wait stop ...\n')

    _t1.join()
    _t2.join()

    print('\ndemo1 finished!\n')


# 示例2，多进程任务处理
def demo2():
    print('demo2 create process ...\n')

    _t1 = ProcessParallel(
        deal_fun=demo_deal_fun, run_args=('demo2-a-1', 'demo2-b-1', 'demo2-c-1'),
        run_kwargs={'p1': 'demo2-p1-1', 'p2': 'demo2-p2-1'}, pid='demo2-t1', pname='demo2-t1-name',
        callback_fun=demo_callback, set_daemon=True, logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs
    )

    _t2 = ProcessParallel(
        deal_fun=demo_deal_fun, run_args=('demo2-a-2', 'demo2-b-2', 'demo2-c-2'),
        run_kwargs={'p1': 'demo2-p1-2', 'p2': 'demo2-p2-2'}, pid='demo2-t2', pname='demo2-t2-name',
        callback_fun=demo_callback, set_daemon=True, logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs
    )

    print('\ndemo2 start process ...\n')
    _t1.start()
    _t2.start(run_args=('demo1-a-2-add', 'demo1-b-2', 'demo1-c-2'))

    print('\ndemo2 wait stop ...\n')

    _t1.join()
    _t2.join()

    print('\ndemo2 finished!\n')


# 示例3，进程锁
def _thread_fun(pid, share_dict, wait):
    share_dict['key'] += '-[%s:start]' % (str(pid))
    time.sleep(wait)
    share_dict['key'] += '-[%s:end]' % (str(pid))


def demo3():
    _share = ProcessParallelShareDict('demo3')
    _share['key'] = 'default'
    print('demo3 share dict is %s\n' % (str(_share['key'])))

    _lock = ProcessParallelLock()

    _t1 = ProcessParallel(
        deal_fun=_thread_fun, run_args=('demo3-t1', _share, 3),
        run_kwargs=None, pid='demo3-t1', pname='demo3-t1-name',
        lock=_lock,
        callback_fun=demo_callback, set_daemon=True, logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs
    )

    _t2 = ProcessParallel(
        deal_fun=_thread_fun, run_args=('demo3-t2', _share, 3),
        run_kwargs=None, pid='demo3-t2', pname='demo3-t2-name',
        lock=_lock,
        callback_fun=demo_callback, set_daemon=True, logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs
    )

    print('\ndemo3 start process ...\n')
    _t1.start()
    _t2.start()

    print('\ndemo3 wait stop ...\n')

    _t1.join()
    _t2.join()

    print('\ndemo3 finished! share dict is %s\n' % (str(_share['key'])))


# 示例4，强制中止任务
def _thread_fun_no_stop(pid):
    while True:
        print('_thread_fun_no_stop running [%s]' % (pid))
        time.sleep(1)


def demo4():
    print('demo4 start thread\n')
    _t1 = ThreadParallel(
        deal_fun=_thread_fun_no_stop, run_args=('demo4-1',),
        run_kwargs=None, pid='demo4-t1', pname='demo4-t1-name',
        auto_start=True,
        callback_fun=demo_callback, set_daemon=True, logger=_logger
    )
    time.sleep(4)
    print('demo4 try kill thread\n')
    _t1.force_stop()
    print('\ndemo4 wait thread stop ...\n')
    _t1.join()
    print('\ndemo4 thread finished!\n')

    print('demo4 start process\n')
    _t2 = ProcessParallel(
        deal_fun=_thread_fun_no_stop, run_args=('demo4-2',),
        run_kwargs=None, pid='demo4-t2', pname='demo4-t2-name',
        auto_start=True,
        callback_fun=demo_callback, set_daemon=True, logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs
    )
    time.sleep(4)
    print('demo4 try kill process\n')
    _t2.force_stop()
    print('\ndemo4 wait process stop ...\n')
    _t2.join()
    print('\ndemo4 thread finished!\n')

    time.sleep(4)
    print('\ndemo4 finished!\n')


# 示例5，并发池，自动处理队列任务，处理完自动停止
def _deal_fun_demo5(q, a, p1=''):
    try:
        obj = q.get(block=False)
        print('_deal_fun_demo5: a=%s, p1=%s, qobj=%s' % (str(a), str(p1), str(obj)))
        time.sleep(1)
        return True
    except Exception as e:
        print('_deal_fun_demo5 error: a=%s, p1=%s, error=%s' % (str(a), str(p1), str(type(e))))
        time.sleep(1)
        return None


def demo5():
    print('demo5 create process queue and put task\n')
    _task_queue = multiprocessing.Queue()
    _i = 0
    while _i < 100:
        _task_queue.put(_i)
        _i = _i + 1

    print('demo5 create parallel pool\n')
    _pool = ParallelPool(
        deal_fun=_deal_fun_demo5,
        parallel_class=getattr(ImportTool.import_module(
            'HiveNetCore.parallel'), 'ProcessParallel'),
        run_args=(_task_queue, 'demo5-a'), run_kwargs={'p1': 'demo5-p1'},
        pname='demo5', callback_fun=demo_callback,
        logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs,
        auto_start=False, auto_stop=True, task_queue=_task_queue, get_task_num_fun=None, get_task_num_fun_args=None,
        maxsize=10, minsize=0, worker_release_time=10, worker_overtime=0,
        force_kill_overtime_worker=False, replace_overtime_worker=False, daemon_thread_time=0.01,
        sharedict_class=getattr(ImportTool.import_module(
            'HiveNetCore.parallel'), 'ProcessParallelShareDict'),
        parallel_lock_class=getattr(ImportTool.import_module(
            'HiveNetCore.parallel'), 'ProcessParallelLock')
    )

    print('demo5 start parallel pool\n')
    _pool.start()

    print('demo5 wait parallel pool stop...\n')
    while not _pool.is_stop:
        time.sleep(1)

    print('demo5 parallel pool finished!\n')


# 示例6，空闲线程自动释放，释放后有新任务自动拉起
def demo6():
    print('demo6 create process queue and put some task\n')
    _task_queue = multiprocessing.Queue()

    _i = 0
    while _i < 10:
        _task_queue.put(_i)
        _i = _i + 1

    print('demo6 create parallel pool\n')
    _pool = ParallelPool(
        deal_fun=_deal_fun_demo5,
        parallel_class=getattr(ImportTool.import_module(
            'HiveNetCore.parallel'), 'ProcessParallel'),
        run_args=(_task_queue, 'demo6-a'), run_kwargs={'p1': 'demo6-p1'},
        pname='demo6', callback_fun=demo_callback,
        logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs,
        auto_start=False, auto_stop=False, task_queue=_task_queue, get_task_num_fun=None, get_task_num_fun_args=None,
        maxsize=10, minsize=5, worker_release_time=3, worker_overtime=0,
        force_kill_overtime_worker=False, replace_overtime_worker=False, daemon_thread_time=0.01,
        sharedict_class=getattr(ImportTool.import_module(
            'HiveNetCore.parallel'), 'ProcessParallelShareDict'),
        parallel_lock_class=getattr(ImportTool.import_module(
            'HiveNetCore.parallel'), 'ProcessParallelLock')
    )

    print('demo6 start parallel pool\n')
    _pool.start()

    print('demo6 start wait parallel free\n')
    time.sleep(30)

    print('demo6 add queue obj\n')
    _i = 0
    while _i < 50:
        _task_queue.put(_i)
        _i = _i + 1

    print('demo6 wait parallel done and stop pool\n')
    while _task_queue.qsize() > 0:
        time.sleep(1)
    _pool.stop()

    print('demo6 wait parallel pool stop...\n')
    while not _pool.is_stop:
        time.sleep(1)

    print('demo6 parallel pool finished!\n')


# 示例7，超时线程处理
def _deal_fun_demo7(a, p1=''):
    try:
        print('_deal_fun_demo7 start and overtime: a=%s, p1=%s' % (str(a), str(p1)))
        while True:
            time.sleep(1)
        return True
    except Exception as e:
        print('_deal_fun_demo7 error: a=%s, p1=%s, error=%s' % (str(a), str(p1), str(type(e))))
        time.sleep(1)
        return None


def demo7():
    print('demo7 create parallel pool\n')
    # 同步测试三种场景：
    # force_kill_overtime_worker=False
    # force_kill_overtime_worker=True
    # force_kill_overtime_worker=False, replace_overtime_worker=True
    _pool = ParallelPool(
        deal_fun=_deal_fun_demo7,
        parallel_class=ProcessParallel,
        run_args=('demo7-a', ), run_kwargs={'p1': 'demo7-p1'},
        pname='demo7', callback_fun=demo_callback,
        logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs,
        auto_start=True, auto_stop=False, task_queue=None, get_task_num_fun=None, get_task_num_fun_args=None,
        maxsize=10, minsize=5, worker_release_time=0, worker_overtime=10,
        force_kill_overtime_worker=False, replace_overtime_worker=True, daemon_thread_time=0.01,
        sharedict_class=ProcessParallelShareDict,
        parallel_lock_class=ProcessParallelLock
    )

    print('demo7 wait overtime\n')
    time.sleep(30)

    print('demo7 stop parallel pool no force\n')
    try:
        _pool.stop(overtime=3)
    except Exception as e:
        print('demo7 stop overtime, error:%s' % (str(type(e))))

    print('demo7 stop parallel pool force\n')
    _pool.stop(force=True)

    print('demo7 wait parallel pool stop...\n')
    while not _pool.is_stop:
        time.sleep(1)

    print('demo7 parallel pool finished!\n')


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    demo1()
    demo2()
    demo3()
    demo4()
    demo5()
    demo6()
    demo7()
