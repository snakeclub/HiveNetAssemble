# logging_hivenet模块说明

logging_hivenet模块重新封装了python的logging模块，提供一个更便于使用的日志处理类。



## logging_hivenet的简单使用

**1、装载要使用的对象**

```
import HiveNetCore.logging_hivenet as simple_log
```

**2、程序本地创建“logger.conf”文件，修改配置文件为自己希望的内容**

注意：conf文件中请不要含中文内容，原因是目前的程序对中文处理存在转码问题（问题待解决）

主要修改的参数如下：

​        （1）[handler_FileHandler]下的args参数：

​            第1个参数是日志文件名（可以带路径），日志程序会自动在扩展名前补充日期；

​            第2个参数固定为追加模式；

​            第3个参数为自动转存的文件大小，单位为byte；

​            第4个参数为自动转存时，超过多少个文件后以覆盖方式记录（不会再新增）

​        （2）[formatters]下的format参数，该参数定义了日志的格式

补充说明：也可以是json或xml文件，内容都一样，只是格式不同，配置说明在后面介绍

**3、实例化Logger对象并使用**

```
# 实例化对象，根据需要传入不同参数
_logger = simple_log.Logger(...)

# 写日志
_logger.log(simple_log.INFO, '要写入的日志')
# 其他写入方式
_logger.info('要写入的INFO日志')
_logger.debug('要写入的Debug日志')
```

**4、使用注意问题**

- logger类是全局共享的，即如果loggername、handler的配置名一样，建立多个logger类且进行调整的情况下会互相干扰，因此如果需要实例化多个logger，则建议配置名和handler名有所区分
- Python默认的FileHandler是线程安全的（支持多线程），但不是进程安全（不支持启动多进程记录同一日志），如果需要支持多进程，需要使用第三方的FileHandler，使用方式如下：

​        （1）pip install ConcurrentLogHandler

​        （2）修改日志配置文件的class=handlers.RotatingFileHandler为class=handlers.ConcurrentRotatingFileHandler



## 日志调用特殊参数说明

**Logger初始化参数**

```
@param {EnumLoggerName|string} logger_name=EnumLoggerName.Console - 输出日志类型，默认的3个类型如下：Console-输出到屏幕,File-输出到文件,ConsoleAndFile-同时输出到屏幕和文件；如果自己自定义了日志模块名，可以直接使用字符串方式传值使用（例如'myLoggerName'）
@param {string} json_str=None - 当日志配置方式为JSON_STR时使用，配置的字符串,如果不串则默认使用_LOGGER_DEFAULT_JSON_CONSOLE_STR的值
@param {bool} auto_create_conf=True - 如果配置方式是文件的情况，指定是否利用默认的参数自动创建配置文件（找不到指定的配置文件时），默认为True
@param {bool} is_create_logfile_by_day=True - 指定是否按天生成新的日志文件，默认为True
@param {int} call_fun_level=0 - 指定log函数输出文件名和函数名的层级，当自己对日志函数再封装了几层的情况下，无法打印到实际所需要登记的函数时，可以指定从向上几级来获取真实调用函数；0代表获取直接调用函数；1代表获取直接调用函数的上一级
@param {string} logfile_path='' - 日志输出文件的路径（含文件名），如果已有配置文件的情况下该参数无效，不传值时代表使用'log/程序名.log'来定义输出文件的路径
```

**log写日志**

```
@param {int} - 输出日志的级别，可以使用simple_log.INFO这类值，也可以直接使用标准logging.INFO这样的传值
@param {**kwargs} args - 通用日子类的kwargs参数，以下为特殊参数的说明
            extra {dict} - 用于传递日志上下文的字典，可用于额外添加一些上下文内容
                例如可传入{'ip': '113.208.78.29', 'username': 'Petter'}，这样当Formatter为
                '%(asctime)s - %(name)s - %(ip)s - %(username)s - %(message)s'时可以正常输出日志值
                以下是simple_log定义的一些特殊上下文：
                    callFunLevel {int} - 日志中输出的函数名（文件名）所属层级：
                        0 - 输出调用本函数的函数名（文件名）
                        1 - 输出调用本函数的函数的上1级函数的函数名（文件名）
                        n - 输出调用本函数的函数的上n级函数的函数名（文件名）
                    dealMsgFun {function} - 自定义日志内容修改函数，可以在输出日志前动态修改日志内容（msg）
                        函数格式为funs(topic_name, record){return msg_string}，返回生成后的日志msg内容
                    topicName {string} - 日志主题，与dealMsgFun配套使用
```



## 日志配置文件详解

以下以INI文件的格式说明配置项的内容，其他格式的是同样道理：

```
###############################################
# 以下部分定义logger模块，root是父类，必需存在的，其它的是自定义的模块名（例子中的模块名是默认创建的，使用者可以自行定义其他模块名）
# logging.getLogger(模块名称) 相当于向根据指定模块名的定义实例化一个日志操作对象
# 每个[logger_模块名称] 实际定义了一个模块名称和对应的处理句柄类
# level     日志输出级别，有DEBUG、INFO、WARNING、ERROR、CRITICAL，可设置不同级别进行日志的过滤
# handlers  处理句柄类，一个日志模块可以引用多个处理句柄，用逗号分开，用来实现同一日志向多个地方输出
# qualname  logger名称，应用程序通过 logging.getLogger获取。对于不能获取的名称，则记录到root模块
# propagate 是否继承父类的log信息，0:否 1:是
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
# 以下部分定义处理句柄及相关参数：
# [handlers] 指定配置里定义的句柄名清单
# [handler_句柄名] 定义了具体句柄的具体传入参数，简要说明如下：
#     class - 句柄的类对象路径（按照python标准访问类的形式），要求在代码中必须能通过该路径访问类
#     level - 句柄对应的日志级别，可设置不同级别进行日志的过滤
#     formatter - 指定句柄对应的日志格式定义，为[formatters]章节的格式名
#     args - 句柄类初始化的传入参数，按照不同的句柄有不同的定义
#
# 可以使用python自带的句柄类、第三方库中的句柄类，也可以自行开发自己的句柄类，部分官方句柄类说明如下：
#     StreamHandler : 使用这个Handler可以向类似与sys.stdout或者sys.stderr的任何文件对象(file object)输出信息。它的构造函数是：
#         StreamHandler([strm])
#         其中strm参数是一个文件对象。默认是sys.stderr
#     FileHandler : 和StreamHandler类似，用于向一个文件输出日志信息。不过FileHandler会帮你打开这个文件。它的构造函数是：
#         FileHandler(filename[,mode])
#         filename是文件名，必须指定一个文件名。
#         mode是文件的打开方式。参见Python内置函数open()的用法。默认是’a'，即添加到文件末尾。
#     handlers.RotatingFileHandler : 这个Handler类似于上面的FileHandler，但是它可以管理文件大小。当文件达到一定大小之后，它会自动将当前日志文件改名，然后创建一个新的同名日志文件继续输出。比如日志文件是chat.log。当chat.log达到指定的大小之后，RotatingFileHandler自动把文件改名为chat.log.1。不过，如果chat.log.1已经存在，会先把chat.log.1重命名为chat.log.2...;最后重新创建 chat.log，继续输出日志信息。它的构造函数是：
#         RotatingFileHandler( filename[, mode[, maxBytes[, backupCount]]])
#         其中filename和mode两个参数和FileHandler一样。
#         maxBytes用于指定日志文件的最大文件大小。如果maxBytes为0，意味着日志文件可以无限大，这时上面描述的重命名过程就不会发生。
#         backupCount用于指定保留的备份文件的个数。比如，如果指定为2，当上面描述的重命名过程发生时，原有的chat.log.2并不会被更名，而是被删除。
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
# [formatter_格式名] 为具体格式名的配置，里面有两个参数：
#     format - 定义输出日志的默认信息（前缀），可选的信息项包括：
#        %(levelno)s: 打印日志级别的数值
#        %(levelname)s: 打印日志级别名称
#        %(pathname)s: 打印当前执行函数所在文件的路径
#        %(filename)s: 打印当前执行函数所在的文件名
#        %(funcName)s: 打印日志的当前函数名
#        %(lineno)d: 打印日志的当前行号
#        %(asctime)s: 打印日志的时间
#        %(millisecond)s: 打印日志的时间(毫秒，不适用于官方的logging)
#        %(thread)d: 打印线程ID
#        %(threadName)s: 打印线程名称
#        %(process)d: 打印进程ID
#        %(message)s: 打印日志信息
#      datefmt - 定义日期时间（asctime）的输出格式，默认为%Y-%m-%d %H:%M:%S,uuu
#         %y 两位数的年份表示（00-99）
#         %Y 四位数的年份表示（000-9999）
#         %m 月份（01-12）
#         %d 月内中的一天（0-31）
#         %H 24小时制小时数（0-23）
#         %I 12小时制小时数（01-12）
#         %M 分钟数（00=59）
#         %S 秒（00-59）
#         %a 本地简化星期名称
#         %A 本地完整星期名称
#         %b 本地简化的月份名称
#         %B 本地完整的月份名称
#         %c 本地相应的日期表示和时间表示
#         %j 年内的一天（001-366）
#         %p 本地A.M.或P.M.的等价符
#         %U 一年中的星期数（00-53）星期天为星期的开始
#         %w 星期（0-6），星期天为星期的开始
#         %W 一年中的星期数（00-53）星期一为星期的开始
#         %x 本地相应的日期表示
#         %X 本地相应的时间表示
#         %Z 当前时区的名称
#         %% %号本身
#       注意：python并未给出毫秒的占位符，因此如果datefmt为空输出格式才有毫秒，如果要自己输出，请采用%(millisecond)s占位符
###############################################
[formatters]
keys=simpleFormatter

[formatter_simpleFormatter]
format=[%(asctime)s.%(millisecond)s][%(levelname)s][PID:%(process)d][TID:%(thread)d][FILE:%(filename)s][FUN:%(funcName)s]%(message)s
datefmt=%Y-%m-%d %H:%M:%S
```



## 通过队列日志句柄实现异步日志处理

可以通过simple_log.QueueHandler来实现异步日志处理，QueueHandler可将日志信息写入内存队列中，然后通过对内存队列的日志项进行处理来实现异步记录日志。

使用步骤如下：

### 1、配置Logger句柄，让日志写入队列中

传入的4个参数说明如下：

- queue - 要写入的队列对象，如果不传值，代表由handler自行生成一个内存队列；如果传入的是字符串，则代表该字符串为可获取到队列对象的变量名字符串，handler将自动根据该字符串获取队列对象
- topic_name - 默认的日志主题，当写日志的时候没有传topicName的扩展信息时使用
- is_deal_msg - 是否处理日志格式，true代表直接生成完整的日志，将日志字符串写入队列；false代表不直接生成完整的日志消息，而是将record对象放入队列（待后面的程序自动处理）
- error_queue_size -  通过start_logging方法写日志时，遇到异常时记录错误信息的队列大小, 如果错误信息数量超过大小，会自动删除前面的数据，0代表不限制大小

```
# 对于json格式的日志配置，句柄配置参考如下
# 第1个配置会在写日志的时候直接将格式化后的日志字符串写入队列
# 第2个配置不直接格式化日志字符串，而是将包含日志所有信息的record对象送入队列，可在处理时再格式化
	"handlers": {
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
    }

# 对于ini格式的日志配置，句柄配置参考如下
[QueueMsgHandler]
class=HiveNetCore.logging_hivenet.handler_queueHandler
level=DEBUG
formatter=logstashFormatter
args=("queue_var_name", "topic_name", true, 20)

[QueueRecordHandler]
class=HiveNetCore.logging_hivenet.handler_queueHandler
level=DEBUG
formatter=logstashFormatter
args=("queue_var_name", "topic_name", false, 20)
```

### 2、使用配置生成simple_log.Logger对象

```
# 配置中的QueueMsg指定使用QueueMsgHandler
queue_logger = simple_log.Logger(logger_name='QueueMsg',
                                 json_str=_LOGGER_QUEUE_MSG_JSON_STR)
```

或

```
# 配置中的QueueRecord指定使用QueueRecordHandler
queue_logger = simple_log.Logger(logger_name='QueueRecord',
                                 json_str=_LOGGER_QUEUE_MSG_JSON_STR)
```

### 3、按正常情况使用Logger记录日志

```
# 记录日志，简单模式
queue_logger.log(simple_log.INFO, 'INFO msg')

# 记录日志，通过extra传入特殊信息，示例中的topicName用于指定日志的topic_name；name2Obj为自定义传入对象，对于QueueRecordHandler的情况，可以自定义日志内容处理函数，通过record.name2Obj访问并使用对象生成日志内容
queue_logger.log(
        simple_log.ERROR, 'ERROR msg',
        extra={
            'topicName': 'name3',
            'name2Obj': ['a', 'b', 'c', 'd']
        }
    )
```

### 4、处理队列的日志信息

可以通过Logger.base_logger.handlers[0]获取handler对象，然后通过handler.queue访问队列，取到消息项进行相应的处理，消息项的格式如下：

- queue_obj.levelno {int} : 日志级别，值说明参考logging.INFO这些值
- queue_obj.topic_name {string} : 日志主题标识（用于使用方区分日志来源）,注意'default'为保留的标识名
- queue_obj.msg {string} : 已格式化后的日志内容, is_deal_msg为True时有效
- queue_obj.record {object} : 未格式化的日志相关信息，其中record.msg为要写入的日志'%(message)s', is_deal_msg为False时有效

logging.QueueHandler也提供了对队列日志自动处理的方法，通过handler.start_logging启动后端线程自动处理队列中的日志数据，相关参数的定义如下：

```
@param {dict} loggers_or_funs - 要写入的日志logger对象列表(或处理函数列表), key为topic_name, value为对应的处理日志类(HiveNetCore.logging_hivenet.Logger)或处理函数
	其中'default'为默认日志处理类或处理函数，如果不传入则代表匹配不到的topic_name不进行处理，规则如下：遇到日志项的topic_name在列表中不存在，先找'default'的日志对象进行处理，如果传入的日志对象清单中没有'default'，则不进行该日志项的处理
	如果传入的是处理函数，格式为funs(levelno, topic_name, msg){...}
	注意：如果为logger，则所传入的日志对象的formatter将统一修改为'%(message)s'，因此该日志对象注意不要与其他日志处理共用；字典里可以支持logger和fun并存，只是如果存在fun的情况，应注意formatters的取值
@param {int} thread_num=1 - 处理队列对象的线程数
@param {dict} deal_msg_funs={} - 处理record的函数(形成msg部分内容), 当is_deal_msg为False时有效, key为topic_name, value为对应的日志内容生成函数，搜索函数的规则与loggers一样，处理函数的定义应如下：func(topic_name, record) {return msg}
@param {dict} formatters=None - is_deal_msg为False时，用于格式化record的Formatter，key为topic_name，value为该topic_name的Formatter，搜索格式对象的规则与loggers一样，如果formatters=None，代表自动获取loggers的Formatter形成该字典
```

提醒：如果loggers_or_funs对应的处理对象为Logger，则会根据Logger的配置进行日志的实际输出处理；如果处理对象为函数，则执行函数进行自定义的日志处理（例如发送到远程服务器）











