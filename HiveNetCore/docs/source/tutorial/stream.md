# stream使用说明

stream模块主要定义了python流处理的框架（按流顺序逐个对象进行处理），并基于该框架实现了字符串流的处理类StringStream。



## 使用StringStream

当需要对字符串进行逐个字符处理的情况（例如进行解析），可以使用StringStream简化实际业务处理逻辑，使用方法有两种：

### 使用实例对象的方法

1、定义处理函数

```
def dealer_fun1(deal_obj, position):
	# deal_obj 为流当前处理到的字符对象
	# position 为当前处理的字符对象在字符串中的位置
	# 以下为自定义对字符处理的具体逻辑
    _logger.info('dealer_fun1: position:%s : %s' % (str(position), deal_obj))
```

2、初始化并启动流处理

```
# 初始化流管理对象
_stream = StringStream(stop_by_excepiton=False, logger=None, dealer_exception_fun=None, stream_closed_fun=None)

# 在流管理对象中注册处理函数，同一个对象可以放置多个处理函数
_stream.add_dealer(dealer_fun1, dealer_fun2, ....)

# 启动流处理，要处理的字符串为str_obj
_stream.start_stream(stream_tag='default', is_sync=True, is_pause=False, seek_position=None, move_next_step=None, move_forward_step=None, str_obj='my test string')
```



### 使用修饰符的方法（更简单）

1、通过修饰符定义处理函数

```
@StringStream.stream_decorator(stop_by_excepiton=False, logger=_logger, dealer_exception_fun=dealer_exception_fun, stream_closed_fun=stream_closed_fun, stream_tag='stream_dealer', is_sync=True, seek_position=None, move_next_step=None, move_forward_step=None)
def string_stream_dealer_3(deal_obj=None, position=0, str_obj='', my_para1='', ...):
    # deal_obj 为流当前处理到的字符对象
	# position 为当前处理的字符对象在字符串中的位置
	# str_obj 为要处理的字符串对象（要转换为流的对象）- 注意命名一定是这个命名，不是按顺序就可以
	# my_para1为自定义传入的参数（例如传入全局变量配合内部处理）
	# 以下为自定义对字符处理的具体逻辑
    _logger.info('string_stream_dealer_3: my_para1 : %s\n str_obj : %s' % (my_para1, str_obj))
    _logger.info('string_stream_dealer_3: position:%s : %s' % (str(position), deal_obj))
```



2、通过执行处理函数启动流处理（str_obj为要处理的字符串对象）

```
string_stream_dealer_3(None, 0, str_obj=u'test my string 加上中文', my_para1='my_para3')
```



## 实现自定义流处理类

1、流处理类必须继承BaseStream类

```
class StringStream(BaseStream):
	...
```



2、需继承实现BaseStream类的内部处理函数

_init_stream(\*\*kwargs) ： 初始化流对象并返回，需注意：**kwargs参数是start_stream方法（或修饰器模式中的处理函数）的自定义参数部分传入，需要在自定义类时明确要求传入所需的必要参数来生成流对象**

\_next(stream_obj)：从流中获取下一个对象，并将流指针指向下一个位置

\_close_stream(stream_obj)：关闭流对象（与_init_stream对应），在中止流处理时调用

\_seek(stream_obj, position):  移动到流的指定位置

\_move_next(stream_obj, step=1): 流从当前位置向后移动指定步数

\_move_forward(stream_obj, step=1): 流从当前位置向前移动指定步数

\_current_position(stream_obj):  获取当前流的位置信息



3、完成以上步骤，就可以按实例方式或修饰符方式使用流对象了！



