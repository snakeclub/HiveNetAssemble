# cache模块说明

cache定义了一个通用的缓存处理框架类BaseCache，并基于该框架类实现了内存缓存的实现类MemoryCache。

## BaseCache框架原理

BaseCache框架封装了缓存基本排序和管理功能，包括缓存大小控制、缓存保留优先级控制（按命中时间优先排序、按命中次数优先排序）、缓存更新一致性控制（更新锁）。

同时定义了缓存数据清除、更新、存入、查询等公共方法和内部数据处理的抽象方法。

在BaseCache框架中并不实现实际的缓存数据存储（具体的缓存数据由实现类自行控制存储地点，例如内存存储或文件存储），只是通过内部字典变量self._cache_data中存储了外部唯一标识（Key）和数据存储索引（value）的关系，需要具体实现类按照数据存储索引（value）操作实际的缓存数据（data）。



## MemoryCache的使用

MemoryCache的使用较为简单，直接按照所继承的BaseCache的公共方法进行缓存数据的操作即可。



## 自定义缓存类

需要自定义自己的缓存类（将实际数据存储在所需的地方），只需继承BaseCache框架并实现其数据操作的抽象方法即可，相关方法的重要说明如下：

\_clear_cache_data(self)： 清除实际存储的所有缓存数据（data），外部唯一标识（Key）和数据存储索引（value）由框架自行清除，无需实现类处理

\_get_cache_data(self, key, value):  根据外部唯一标识（Key）和数据存储索引（value），取出实际存储的缓存数据对象（data）返回

\_update_cache_data(self, key, value, data): 根据外部唯一标识（Key）和数据存储索引（value），将缓存数据（data）替换为新的数据

\_del_cache_data(self, key, value): 根据外部唯一标识（Key）和数据存储索引（value），删除对应的实际缓存数据（data）