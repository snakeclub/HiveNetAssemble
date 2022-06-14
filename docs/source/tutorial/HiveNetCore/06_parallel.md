# parallel模块说明

模块名：HiveNetCore.parallel

parallel是并行任务（多线程、多进程）的处理框架和实现，包括并行任务处理，以及并行池（类似线程池或进程池）管理的封装，同时该框架可以支持扩展为分布式的并行任务处理（按框架定义实现对应的实现类即可）。

使用该框架的最主要优点为：

1、多线程、多进程接口统一，可直接实现多进程或多线程的直接切换（无需修改代码）；

2、简化多线程和多进程的代码实现，且实现了函数执行回调函数的支持；此外遵循HiveNet 日志规范（hivenet_log_standards）；

3、框架可支持实现分布式计算并行任务的自定义扩展。

**注意：本模块要使用内置的affinity，在windows平台需要同步安装pywin32；**



## ParallelLockFw（并行锁框架）

定义了并行任务所需的锁对象框架，该框架与Python自带的threading.RLock定义兼容，目前已直接利用Python原生类实现了该框架的线程锁实例（ThreadParallelLock）、进程锁实例（ProcessParallelLock），分别可以针对多线程、多进程的锁控制。后续也可根据需要基于框架（ParallelLockFw）实现分布计算锁，来支持分布式计算的锁控制需求。

使用ParallelLockFw具体实例的简单示例如下：

```

```



## ParallelShareDictFw(并行任务共享字典框架)

定义了并行任务所需的数据共享框架（特别是多进程、或后续可能的分布式任务的数据共享），目前已实现了线程共享字典实例（ThreadParallelShareDict，利用全局变量共享）、进程共享字典实例（ProcessParallelShareDict，利用multiprocessing的Manager对象共享）。后续也可以根据需要基于框架（ParallelShareDictFw）实现分布共享字典，来支持分布式计算的共享数据需求。

使用ParallelShareDictFw具体实例的简单示例如下：

```
# 创建进程共享字典
_tag = uuid.uuid1()  # 共享字典标签
_dict = ProcessParallelShareDict(_tag)

# 使用共享字典
_dict['key'] += 1
```



## ParallelFw(并行任务框架)

定义了并行任务处理的框架（例如多线程、多进程的任务发起），目前已实现了多线程任务实例（ThreadParallel）、多进程任务实例（ProcessParallel）。后续也可以根据需要基于框架（ParallelFw）实现分布式任务处理实例，来支持分布式计算的并行任务处理需求。

支持的方法包括：

start - 启动并行池任务处理

stop - 停止并行池任务处理

pause - 暂停并行池任务处理

resume - 恢复并行池任务处理



并行任务框架的应用的关键在于对象初始化，支持的参数如下：

```
        @param {fuction} deal_fun - 并发处理主函数，按顺序入参，可以有返回值
        @param {tuple} run_args=None - 并发处理主函数的入参列表
        @param {dict} run_kwargs=None - 并发处理主函数的动态入参列表
        @param {bool} auto_start=False - 是否创建时自动发起并发任务
        @param {string} pid='' - 并发对象的id
        @param {string} pname='' - 并发对象的标识名
        @param {ParallelLockFw} lock=None - 并发锁对象，控制多个并发对象根据该锁控制单一处理
        @param {fuction} callback_fun=None - 回调函数，在执行完函数后执行，定义如下
            fun(id, name, call_result, deal_fun_ret)
                id - 并发对象的id
                name - 并发对象的标识名
                call_result - 线程执行的结果，CResult对象，如果执行无异常返回'00000'；
                    如果发生异常，返回'21399'，并登记异常信息
                deal_fun_ret - deal_fun函数执行的返回值
        @param {bool} set_daemon=False - 是否设置守护，如果设置守护，则在主进程中使用join方法等待所有并发完成，
            否则主进程结束后并发执行的结果不可预知；如果不设置守护，主进程结束后并发任务仍会执行
        @param {Logger} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {int} log_level=logging.INFO - 打印日志的级别
        @param {bool} use_distributed_logger=False - 是否使用分布式logger，如果是，则每个分布任务自行创建独立logger记录日志
            注：对于多进程及分布式并发任务，应采取该日志模式
        @param {string} distributed_logger_module_name='' - 分布式日志类模块名
        @param {string} distributed_logger_class_name='' - 分布式日志类类名
        @param {tuple} distributed_logger_args=None - 分布式日志类创建参数
        @param {dict} distributed_logger_kwargs=None - 分布式日志类创建参数
        @param {dict} distributed_logger_replace_para=dict() - 分布式日志动态参数替换，在每创建一个并发任务通过该参数修改日志参数
            key - 如果是int类型，代表替换distributed_logger_args的第几个参数；如果是string，代表替换distributed_logger_kwargs的指定参数
            value - 替换参数字典，key为要替换正则表达式字符，value为要替换的动态值
                要替换的动态值，可选值有以下几种：
                    'pid' - 并发任务id
                    'pname' - 并发任务名
                    'pocess_id' - 进程ID
                    'thread_id' - 线程ID - 暂不支持
        @param {bool} is_logger_to_deal_fun=False - 是否传递并发任务logger到deal_fun中
            注意：传递通过kwargs，参数名为logger
```

该框架的几个特性说明如下：

1、并发任务处理函数（deal_fun）支持返回值，返回值（或执行过程的异常信息）可在处理函数执行完成后，通过回调函数（callback_fun）通知回调用方；

2、可在定义中直接传入并发任务锁（lock），框架会保证同一锁发起的并发任务基于该所控制并发；

3、并发任务的日志记录支持单一日志对象（多进程情况不支持）及分布式日志对象（每个任务自行初始化一个新的日志对象），可通过distributed_logger相关参数实现各种情况的日志输出支持；此外也可支持将日志对象传递到执行函数中（is_logger_to_deal_fun参数），执行函数可以复用该日志对象进行日志的输出；

使用ParallelFw具体实例的简单示例如下：

```
# 定义主进程使用的logger
_logger = HiveNetCore.logging_hivenet.Logger(conf_file_name=None, logger_name=HiveNetCore.logging_hivenet.EnumLoggerName.Console,
                 config_type=HiveNetCore.logging_hivenet.EnumLoggerConfigType.JSON_STR)


# 定义并发任务的logger创建参数
_logger_kwargs = {
    'conf_file_name': None,
    'logger_name': HiveNetCore.logging_hivenet.EnumLoggerName.Console,
    'config_type': HiveNetCore.logging_hivenet.EnumLoggerConfigType.JSON_STR
}

# 定义并发任务处理函数
def demo_deal_fun(a, b, c, p1='', p2=''):
    print('demo_deal_fun print: a=%s, b=%s, c=%s, p1=%s, p2=%s' % (
        str(a), str(b), str(c), str(p1), str(p2)
    ))
    time.sleep(0.1)
    _ret = ('demo_deal_fun:r1-%s' % (str(a)), 'demo_deal_fun:r2')
    print('demo_deal_fun print: return=%s' % (str(_ret)))
    return _ret

# 定义并发任务回调函数
def demo_callback(id, name, call_result, deal_fun_ret):
    print('demo_callback print: id=%s, name=%s, call_result=%s, deal_fun_ret=%s' % (
        str(id), str(name), str(call_result), str(deal_fun_ret)
    ))
    return

# 初始化并发任务对象
_t1 = ProcessParallel(
        deal_fun=demo_deal_fun, run_args=('demo2-a-1', 'demo2-b-1', 'demo2-c-1'),
        run_kwargs={'p1': 'demo2-p1-1', 'p2': 'demo2-p2-1'}, pid='demo2-t1', pname='demo2-t1-name',
        callback_fun=demo_callback, set_daemon=True, logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs
    )

# 执行并发任务
_t1.start()

# 等待任务完成
_t1.join()

# 如果过程中想强行中止并发任务
_t1.force_stop()
```



## ParallelPool（并行池管理类）

实现了统一的并行池（线程池、进程池的管理），实现池中任务的创建、销毁、启动、暂停等管理，同时直接支持队列方式的消费者任务处理。该类可以直接支持后续扩展其他并行任务的管理（如分布式并行任务，只要并行任务基于以上的框架实现）。

并行池的应用的关键在于对象初始化，支持的参数如下：

```
		@param {fuction} deal_fun - 并发任务处理主函数，按顺序入参，可以有返回值
            注：该函数内部需自行实现获取数据并处理的流程，但约定如果无处理数据，函数应返回None（用于并发池判断是否释放任务）
        @param {ParallelFw} parallel_class=None - 并行任务类定义对象，获取方法如下：
            getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ThreadParallel')
        @param {tuple} run_args=None - 并发任务处理主函数的入参列表
        @param {dict} run_kwargs=None - 并发任务处理主函数的动态入参列表
        @param {string} pname='' - 并发任务处理主函数的标识名
        @param {ParallelLockFw} lock=None - 并发锁对象，控制多个并发对象根据该锁控制单一处理
        @param {fuction} callback_fun=None - 回调函数，在执行完函数后执行，定义如下
            fun(id, name, call_result, deal_fun_ret)
                id - 并发对象的id
                name - 并发对象的标识名
                call_result - 线程执行的结果，CResult对象，如果执行无异常返回'00000'；
                    如果发生异常，返回'21399'，并登记异常信息
                deal_fun_ret - deal_fun函数执行的返回值

        @param {Logger} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:
            1、标准logging的logger对象
            2、自定义的日志类对象，但应实现info、warning、error等标准方法
        @param {bool} is_use_global_logger=True - 当logger=None时，是否使用全局logger对象
            注：通过RunTool.set_global_logger进行设置
        @param {int} log_level=logging.INFO - 打印日志的级别
        @param {bool} use_distributed_logger=False - 是否使用分布式logger，如果是，则每个分布任务自行创建独立logger记录日志
            注：对于多进程及分布式并发任务，应采取该日志模式
        @param {string} distributed_logger_module_name='' - 分布式日志类模块名
        @param {string} distributed_logger_class_name='' - 分布式日志类类名
        @param {tuple} distributed_logger_args=None - 分布式日志类创建参数
        @param {dict} distributed_logger_kwargs=None - 分布式日志类创建参数
        @param {dict} distributed_logger_replace_para=dict() - 分布式日志动态参数替换，在每创建一个并发任务通过该参数修改日志参数
            key - 如果是int类型，代表替换distributed_logger_args的第几个参数；如果是string，代表替换distributed_logger_kwargs的指定参数
            value - 替换参数字典，key为要替换正则表达式字符，value为要替换的动态值
                要替换的动态值，可选值有以下几种：
                    'pid' - 并发任务id
                    'pname' - 并发任务名
                    'pocess_id' - 进程ID
                    'thread_id' - 线程ID
        @param {bool} is_logger_to_deal_fun=False - 是否传递并发任务logger到deal_fun中
            注意：传递通过kwargs，参数名为logger
        @param {bool} auto_start=False - 是否自动启动并发池
        @param {bool} auto_stop=False - 是否自动关闭并发池（当任务都已全部完成处理）
        @param {QueueFw} task_queue=None - 并发池需要处理的任务队列
            注：如果有指定队列，get_task_num_fun参数无效，则自动根据队列长度检查待处理任务
        @param {function} get_task_num_fun=None - 获取待处理任务数量的函数
            注：如果task_queue和get_task_num_fun均为None，则直接创建最大数量的线程数，且不释放空闲任务
        @param {list} get_task_num_fun_args=None - 获取待处理任务数量的函数，的入参列表
        @param {int} maxsize=10 - 并发池最大并发对象数
        @param {int} minsize=0 - 并发池最小并发对象数
        @param {number} worker_release_time=10 - 空闲工作并发对象释放时间，单位为秒, 0代表不控制空闲释放
        @param {number} worker_overtime=0 - 正在执行的任务超时时间（秒），0代表不控制超时
            注：对于超时执行任务，将视为失效任务，可以选择直接忽略或强制中止
        @param {bool} force_kill_overtime_worker=False - 是否强制中止失效任务
        @param {bool} replace_overtime_worker=False - 是否创建新任务替代超时任务
            注：仅当force_kill_overtime_worker=False时才会进行替代
        @param {number} daemon_thread_time=0.01 - 守护线程的间隔时间
        @param {ParallelShareDictFw} sharedict_class=None - 进程间共享字典对象的类对象，获取方法如下：
            getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ThreadParallelShareDict')
        @param {ParallelLockFw} parallel_lock_class=None - 进程间锁对象的类对象，获取方法如下：
            getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ThreadParallelLock')
```

该框架的几个特性说明如下：

1、支持多种并行任务类型，可通过参数指定具体的并行任务类型（parallel_class，注意要取到的是该类型的定义对象，通过getattr获取，后续基于该对象动态创建并行任务，例如多线程还是多进程）；

2、支持指定队列发起并行任务（task_queue，队列对象应为Python原生队列对象，或基于HiveNetCore.queue_hivenet.QueueFw扩展的队列对象）；如果需要执行固定数量的任务，可以将任务放入队列后，指定自动结束参数（auto_stop），再启动并发池，并发池将在任务完成后自行结束；

3、支持自动释放空闲并发任务（worker_release_time），减少并发任务空跑导致的性能消耗；

4、支持处理超时任务（worker_overtime），可强制中止超时任务（force_kill_overtime_worker），或启动新任务替代某一超时任务（replace_overtime_worker），避免超时任务堵塞了任务队列的处理；



使用ParallelPool的简单示例如下：

```
# 定义并行池的处理函数，注意示例中q为支持进程共享访问的队列
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

def demo():
    # 定义要处理的队列
	_task_queue = multiprocessing.Queue()
    _i = 0
    while _i < 100:
        _task_queue.put(_i)
        _i = _i + 1

    # 定义进程池，注意大部分参数与ParallelFw一致
    _pool = ParallelPool(
        deal_fun=_deal_fun_demo5,
        parallel_class=getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ProcessParallel'),
        run_args=(_task_queue, 'demo5-a'), run_kwargs={'p1': 'demo5-p1'},
        pname='demo5', callback_fun=demo_callback,
        logger=_logger,
        use_distributed_logger=True, distributed_logger_module_name='HiveNetCore.logging_hivenet',
        distributed_logger_class_name='Logger',
        distributed_logger_args=None, distributed_logger_kwargs=_logger_kwargs,
        auto_start=False, auto_stop=True, task_queue=_task_queue, get_task_num_fun=None, get_task_num_fun_args=None,
        maxsize=10, minsize=0, worker_release_time=10, worker_overtime=0,
        force_kill_overtime_worker=False, replace_overtime_worker=False, daemon_thread_time=0.01,
        sharedict_class=getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ProcessParallelShareDict'),
        parallel_lock_class=getattr(ImportTool.import_module('HiveNetCore.parallel'), 'ProcessParallelLock')
    )

    # 启动并行池，该示例定义了自动结束
    _pool.start()
    while not _pool.is_stop:
        time.sleep(1)
```

