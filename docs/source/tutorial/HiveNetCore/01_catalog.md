# HiveNetCore总览

HiveNetCore是HiveNetAssemble的核心组件, 提供了最常用的基础对象和基础工具类。

## 安装方法

### 源码方式安装

- HiveNetCore库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetCore


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetCore-0.1.0-py3-none-any.whl


## 库模块大纲

### 基础模块

#### generic

[generic](02_generic.md)模块主要实现一些公共的基础通用类，包括关键的NullObj（空对象定义类）和CResult(通用错误类)。


#### utils

实现一系列基础的基本工具，包括：

- value_tool :   值处理通用工具模块，提供从字典对象取值的方法实现，后续会按需持续扩展
- string_tool : 字符串处理模块, 提供字符串/字节/json/xml/dict/object相互转换、产生固定长度字符、字符查找等方法实现
- run_tool : 运行参数处理通用工具模块，提供全局变量处理、命令行入参、单进程运行控制、函数对象相关信息获取等方法实现
- net_tool : 网络处理相关工具模块，提供int/网络字节相互转换的方法实现，后续会按需持续扩展
- import_tool : 库导入工具模块，提供动态导入库及模块的方法实现
- file_tool : 文件处理工具模块, 提供文件及目录、zip压缩文件的相关方法实现
- test_tool : 测试相关工具模块，提供测试所需的对象比较相关方法实现，后续会按需持续扩展
- debug_tool : 通用调试工具模块，提供调式所需的打印相关方法
- [exception_tool](utils/exception_tool.md) : 异常处理工具模块，提供异常信息捕获、打印、错误对象转换等简化异常处理的方法实现
- [validate_tool](utils/validate_tool.md) : 通用验证工具，提供便捷的数据验证方法，可以支持单值验证、列表值验证、字典验证等。

### simple系列模块

#### cache

[cache](03_cache.md)定义了一个通用的缓存处理框架类BaseCache，并基于该框架类实现了内存缓存的实现类MemoryCache。

#### i18n

[i18n](04_i18n.md)是一个简单用于python的多国语言支持的模块，可以根据多国语言信息的配置实现语言的翻译转换。

#### logging

[logging](05_logging_hivenet.md)模块重新封装了python的logging模块，提供一个更便于使用的日志处理类。

#### parallel

[parallel](06_parallel.md)是并行任务（多线程、多进程）的处理框架和实现，包括并行任务处理，以及并行池（类似线程池或进程池）管理的封装，同时该框架可以支持扩展为分布式的并行任务处理（按框架定义实现对应的实现类即可）。

#### queue

[queue](07_queue_hivenet.md)框架基于Python原生的队列库（queue）的模式定义了队列处理的基本框架类（QueueFw），并基于该框架类，重构了普通队列（MemoryQueue，该对象合并了queue中的Queue、LifoQueue和PriorityQueue），同时考虑对分布式应用所需的网络队列（如各类MQ）提供框架层级的扩展开发支持。

本队列框架支持的方法与Python原生队列的支持的方法完全一致，因此可以直接使用原生队列替代实现队列处理，例如支持多进程访问的multiprocessing.Queue。

此外，框架也进行改造支持了水桶模式（bucket_mode），即可以往队列一直放对象，但当队列已满的情况下自动通过get丢弃前面的对象。

#### stream

[stream](08_stream.md)模块主要定义了python流处理的框架（按流顺序逐个对象进行处理），并基于该框架实现了字符串流的处理类StringStream。


#### xml
[xml](09_xml_hivenet.md)模块主要实现了xml文件的简单处理处理，模块使用lxml.etree进行底层处理。

### 其他模块

#### formula

[formula](10_formula.md)模块可用于对一段文本进行关键字解析，以及进行公式（表达式）匹配和公式值计算。主要应用场景包括代码解析结构化处理（例如将html代码按标签解析为字典形式进行处理）、对一段文本进行自定义公式识别和计算处理。

#### redirect_stdout

[redirect_stdout](11_redirect_stdout.md)模块由于重定向标准输出的处理，支持将界面的标准输出（print）重定向到其他多个输出对象，例如控制台、字符串、字符数组、日志、文件等，同时该框架也支持进行重定向对象的扩展，以实现更多的标准输出处理功能。

#### connection_pool

[connection_pool](12_connection_pool.md)模块定义了一个通用的支持异步模式的网络连接池框架，支持通过对已有的连接模块快速实现对应的连接池管理能力，例如实现网络连接池和数据库连接池。