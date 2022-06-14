# queue_hivenet模块说明

该框架基于Python原生的队列库（queue）的模式定义了队列处理的基本框架类（QueueFw），并基于该框架类，重构了普通队列（MemoryQueue，该对象合并了queue中的Queue、LifoQueue和PriorityQueue），同时考虑对分布式应用所需的网络队列（如各类MQ）提供框架层级的扩展开发支持。

本队列框架支持的方法与Python原生队列的支持的方法完全一致，因此可以直接使用原生队列替代实现队列处理，例如支持多进程访问的multiprocessing.Queue。

此外，框架也进行改造支持了水桶模式（bucket_mode），即可以往队列一直放对象，但当队列已满的情况下自动通过get丢弃前面的对象

队列支持方法包括：

## 构造函数

```
@param {**kwargs} kwargs - 队列初始化动态参数，定义如下：
	maxsize=0 {int} - 队列深度，如果为0代表不限制队列大小
	bucket_mode=False {bool} - 启动水桶模式，队列大小达到上限后插入数据可自动丢弃老数据(get出来并丢弃)
```

## task_done

	任务完成通知，用于支持生产者消费者模型处理

	由消费者线程每获取到一个队列对象，完成处理后通过task_done通知队列任务完成

	队列机制是将队列待执行任务数-1，以便于join函数判断队列任务是否已全部完成（已无待处理任务）

## join

	队列完成阻塞函数，用于支持生产者消费者模型处理

	该函数必须与task_done通知配套使用，当put一个任务到队列中，待执行任务数+1；执行一次task_done，待执行任务数-1

	当待执行任务数为0时，join执行退出

## qsize

	返回队列长度

## empty

	判断队列是否为空

## full

	判断队列是否已满（无空闲空间）

## put(self, item, block=True, timeout=None, ****kwargs)

	将对象放入队列中

## get(self, block=True, timeout=None, ****kwargs

	从队列中获取对象

## put_nowait(self, item, ****kwargs)

	采取不阻塞的模式将对象放入队列

## get_nowait(self, ****kwargs)

	采取不阻塞方式从队列中获取对象



# 内存队列实例（MemoryQueue）

重构了Python原生的queue的三种队列（Queue、LifoQueue和PriorityQueue），并合并在一个队列类中支持。

**注意：该队列只能线程共享，不能进程共享，如果需进程共享，可直接使用multiprocessing.Queue**



1、初始化参数可指定内存队列类型：queue_type=EnumQueueType.FIFO，取值包括：

FIFO = 0  # 先进先出

LIFO = 1  # 后进先出

PRIORITY = 2  # 按优先级处理

2、对于PRIORITY 类型的队列，可以直接在put时指定优先级：

 priority {int} - 优先级，默认为0，数字越大优先级越高，仅EnumQueueType.PRIORITY使用

