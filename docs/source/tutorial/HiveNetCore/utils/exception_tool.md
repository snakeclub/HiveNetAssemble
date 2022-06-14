# utils.exception_tool模块说明

exception_tool异常处理工具，提供便捷的异常处理模式，用于简化代码中的异常匹配错误码（基于CResult类）、异常忽略、异常日志登记的处理。



## ExceptionTool工具类

### ignored

忽略指定异常，简化异常捕获代码，利用该函数忽略指定的异常，详细说明如下：

1、对于指定忽略的异常，忽略不处理（如果指定logger则会进行日志输出，使用WARNING级别）

2、对于非指定的异常，仍抛出异常（如果指定logger则会进行日志输出，使用ERROR级别）

3、输出的日志为self_log_msg+'\n'+trace_str

重要参数定义：

(expect=(), logger=None, self_log_msg='', force_log_level=None)

@param {tuple} expect=() - 需要忽略的异常列表，例如(ZeroDivisionError, ValueError)

@param {object} logger=None - 日志对象，如果为None代表不需要输出日志，传入对象需满足:

​	1、标准logging的logger对象

​	2、自定义的日志类对象，但应实现warning、error的标准方法

使用示例：

```
# 以下代码将忽略ZeroDivisionError、ValueError这两类异常，程序正常往下执行
with ignored((ZeroDivisionError, ValueError), logger, '执行XX出现异常'):
	count = 1 / 0
	count = count + 10000
```



### ignored_all

忽略除指定以外的所有异常,简化异常捕获代码，利用该函数忽略指定以外的所有异常，详细说明如下：

​	1、对于指定以外的异常，忽略不处理（如果指定logger则会进行日志输出，使用WARNING级别）

​	2、对于指定的异常，仍抛出异常（如果指定logger则会进行日志输出，使用ERROR级别）

​	3、输出的日志为self_log_msg+'\n'+trace_str

重要参数定义：

(unexpect=(), logger=None, self_log_msg='', force_log_level=None)

@param {tuple} unexpect=() - 指定不能忽略的异常列表，例如(ZeroDivisionError, ValueError)

使用示例：

```
# 以下代码将抛出ZeroDivisionError异常，程序中断
with ignored_all((ZeroDivisionError, ValueError), logger, '执行XX出现异常'):
	count = 1 / 0
	count = count + 10000
```



### ignored_cresult

**特别注意：在 with 内部避免使用 result_obj 对应的变量处理其他函数的返回值（整个对象会被重新构建），这样可能会导致捕获一场后无法正常处理 result_obj 对象而出现异常被直接忽略的情况。**

忽略异常并设置CResult对象,简化异常捕获代码，利用该函数忽略指定的异常，并设置传入的通用结果对象，详细说明如下：

​	1、对于指定忽略的异常，忽略不处理，结果为成功（如果指定logger则会进行日志输出，使用WARNING级别）

​	2、对于非指定的异常，不抛出异常，结果为失败（如果指定logger则会进行日志输出，使用ERROR级别）

​	3、输出的日志为self_log_msg+'\n'+trace_str

​	4、根据error_map的映射关系设置错误码和错误信息

重要参数定义：

(result_obj=None, error_map={}, expect=(), expect_no_log=False, expect_use_error_map=True, logger=None, self_log_msg='', force_log_level=None, i18n_obj=None, i18n_msg_paras=())

​	    @param {CResult} result_obj=None - 需要设置的错误类对象(对象值会被修改)

​        @param {dict} error_map={} - 用来设置错误类对象的映射表，具体说明如下：

​            1、key为异常类，value为(code, msg)的错误码、错误描述二元组，如果msg=None代表使用标准错误码

​            2、应有一个'DEFAULT'的key，代表没有匹配上的异常映射，默认value为('29999', None)

​            3、应有一个'SUCESS'的key，代表成功的映射，默认value为('00000', None)

​			注：value也可以为(code, msg, i18n_msg_paras)的错误码、错误描述、国际化替换参数三元组,

​        		i18n_msg_paras为tuple类型, 使用该模式支持CResult的国际化处理

​        @param {tuple} expect=() - 需要忽略的异常列表，例如(ZeroDivisionError, ValueError)

​        @param {bool} expect_no_log=False - 忽略异常列表是否不打印日志

​        @param {bool} expect_use_error_map=True - 忽略异常列表所匹配到的异常，所返回错误码是否使用错误码映射表:

​            如果在映射表中匹配上则返回映射表的错误码；匹配不上则返回成功

​        @param {object} i18n_obj=None - 国际化类的实例对象，该对象需实现translate方法

​		@param {tuple} i18n_msg_paras=() - 与self_log_msg配套使用，当使用国际化时，可以传入变量，用于替换self_log_msg中的$1占位符

使用示例：

```
# 以下代码封装所有异常的获取（不会抛出新异常）
# 遇到expect中的ValueError异常时，尝试从error_map匹配错误码，因为匹配不到会将result修改为'00000'的成功状态
# 遇到非expect的异常，尝试从error_map匹配错误码，因为匹配不到会将result修改为'29999'的失败状态
# 遇到非expect的ZeroDivisionError异常，由于从error_map中匹配到错误码，则将result修改为'10001'的状态
result = CResult()
with ExceptionTools.ignored_CResult(result_obj=result, error_map={ZeroDivisionError: ('10001', 'zero division error')},expect=(ValueError),logger=None,self_log_msg=''):
	i = 1/0
	i = i + 1000
```

