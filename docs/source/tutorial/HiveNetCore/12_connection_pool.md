# connection_pool模块说明

connection_pool模块定义了一个通用的支持异步模式的网络连接池框架，支持通过对已有的连接模块快速实现对应的连接池管理能力，例如实现网络连接池和数据库连接池。




## 模块标准使用步骤（以sqlite为例）

1、开发PoolConnectionFW的实现类，继承PoolConnectionFW并且实现需要实现的函数：

```
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.connection_pool import PoolConnectionFW

class SQLitePoolConnection(PoolConnectionFW):
    """
    SQLite连接池连接对象
    """
    #############################
    # 需要继承类实现的函数
    #############################
    async def _real_ping(self, *args, **kwargs) -> bool:
        """
        实现类的真实检查连接对象是否有效的的函数

        @returns {bool} - 返回检查结果
        """
        # 不支持检测连接, 直接返回True就好
        return True

    async def _fade_close(self) -> Any:
        """
        实现类提供的虚假关闭函数
        注1: 不关闭连接, 只是清空上一个连接使用的上下文信息(例如数据库连接进行commit或rollback处理)
        注2: 如果必须关闭真实连接, 则可以关闭后创建一个新连接返回

        @returns {Any} - 返回原连接或新创建的连接
        """
        _close_action = self._pool._pool_extend_paras.get('close_action', None)
        if _close_action == 'commit':
            await AsyncTools.async_run_coroutine(self._conn.commit())
        elif _close_action == 'rollback':
            await AsyncTools.async_run_coroutine(self._conn.rollback())

        return self._conn

    async def _real_close(self):
        """
        实现类提供的真实关闭函数
        """
        await AsyncTools.async_run_coroutine(self._conn.close())
```



2、使用AIOConnectionPool创建连接池

```
import aiosqlite
import sqlite3
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.connection_pool import AIOConnectionPool

# 创建连接池, 注意会通过aiosqlite.connect函数创建连接对象；另外SQLitePoolConnection是上面实现的PoolConnectionFW继承类
_pool = AIOConnectionPool(
    aiosqlite, SQLitePoolConnection, args=['test.db'], kwargs={'timeout': 10.0},
    connect_method_name='connect', max_size=1, min_size=0, connect_on_init=True,
    get_timeout=1,
    free_idle_time=5, ping_on_get=True, ping_on_back=True, ping_on_idle=True,
    ping_interval=5
)

# 从连接池获取一个连接, 注意这里是一个异步io的函数调用
_conn = AsyncTools.sync_run_coroutine(_pool.connection())

# 使用连接对象进行操作
try:
  # 可以使用连接对象自身特有函数进行处理
  ...
finally:
   # 关闭连接对象, 把对象还回连接池, 注意这里是一个异步io的函数调用
   AsyncTools.sync_run_coroutine(_conn.close())
   
# 关闭连接池, 注意这里是一个异步io的函数调用
AsyncTools.sync_run_coroutine(_conn.close())
```







