# HiveNetNoSql总览

HiveNetNoSql是一个通用的NoSql数据访问驱动框架, 参考MongoDB的语法对NoSql的数据访问操作进行了抽象, 便于对各类数据库(包括关系型数据库和NoSql数据库)采用同一套NoSql操作进行数据访问, 在该包中实现了MongoDB和Sqlite的驱动适配, 可以根据自己的需要实现其他数据库的适配实现。


## 安装方法

### 源码方式安装

- HiveNetNoSql库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetNoSql


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetNoSql-0.1.0-py3-none-any.whl




## 库模块大纲

### base.driver_fw

base.driver_fw模块提供NoSQL数据库驱动基础框架类NosqlDriverFW, 定义了统一的NoSQL数据访问操作, 可以基于不同的数据库驱动继承该框架类实现对不同数据库的NoSQL数据访问支持。

要注意NosqlDriverFW的框架是需要实现连接池管理的, 如果要适配的数据库驱动本身无连接池管理功能, 你也可以直接集成NosqlDriverFW的扩展框架类NosqlAIOPoolDriver, 该框架类基于HiveNetCore.connection_pool.AIOConnectionPool来处理连接池管理功能, 这样在实现数据库驱动支持时无需自行实现连接池的管理。


### mongo

mongo模块基于motor异步IO驱动提供了MongoDB的NosqlDriver实现类MongoNosqlDriver, 可基于MongoDB来进行NoSQL数据访问处理。

### sqlite

sqlite模块基于aiosqlite异步IO驱动提供了SQLite的NosqlDriver实现类SQLiteNosqlDriver, 可基于SQLite数据库来进行NoSQL数据访问处理。



## HiveNetNoSql使用示例（sqlite）

当前示例代码使用SQLiteNosqlDriver作为展示（使用MongoNosqlDriver的方法类似，仅启动参数有所不同）：

```
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetNoSql.sqlite import SQLiteNosqlDriver


# 步骤1: 准备驱动启动的特定参数
_path = 'test_data/temp/sqlite_test.db'  # 数据库文件路径

# 启动驱动时要创建的数据库参数(可不设置)
_init_db = {
    'memory': {
        'index_only': False,
        'args': [':memory:']
    },
    'db_init_test': {
        'index_only': False,
        'args': [os.path.join(self._path, 'sqlite_db_init_test.db')]
    }
}

# 启动驱动时要创建的集合（表）(可不设置)
_init_collections = {
    # 在memory库创建表
    'memory': {
        'tb_init_on_memory': {
            'index_only': False,
            'indexs': {
                'idx_tb_init_on_memory_c_index_c_int': {
                    'keys': {
                        'c_index': {'asc': 1}, 'c_int': {'asc': -1}
                    },
                    'paras': {
                        'unique': True
                    }
                }
            },
            'fixed_col_define': {
                'c_index': {'type': 'str', 'len': 20},
                'c_str': {'type': 'str', 'len': 50},
                'c_bool': {'type': 'bool'},
                'c_int': {'type': 'int'},
                'c_float': {'type': 'float'},
                'c_json': {'type': 'json'}
            }
        }
    },
    # 在db_init_test上创建表
    'db_init_test': {
        'tb_init_on_db_init_test': {
            'index_only': False,
            'indexs': None,
            'fixed_col_define': {
                'c_index': {'type': 'str', 'len': 20},
                'c_str': {'type': 'str', 'len': 50},
                'c_bool': {'type': 'bool'},
                'c_int': {'type': 'int'},
                'c_float': {'type': 'float'},
                'c_json': {'type': 'json'}
            }
        }
    }
}

# 步骤2: 初始化驱动, 连接数据库
_driver = SQLiteNosqlDriver(
    connect_config={
        'host': _path,
        'check_same_thread': False
    },
    driver_config={
        'close_action': 'commit',
        'init_db': _init_db,
        'init_collections': _init_collections
    }
)

# 步骤3: 执行自己想要的操作(注意异步IO函数的执行要用await或使用AsyncTools工具)
# 创建数据库
AsyncTools.sync_run_coroutine(_driver.create_db('new_test_db', :memory:'))

# 列出所有数据库
_dbs = AsyncTools.sync_run_coroutine(_driver.list_dbs())
print(_dbs)

# 切换到要操作的数据库上
AsyncTools.sync_run_coroutine(_driver.switch_db('memory'))

# 执行JSON数据存储
_row = {
    'n_str': 'str', 'n_bool': True, 'n_int': 1, 'n_float': 0.1, 'n_dict': {'d1': 'v1', 'd2': 2},
    'n_list': ['a', 'b', 'c']
}
_id = AsyncTools.sync_run_coroutine(
    _driver.insert_one('tb_init_on_memory', _row)
)

# 查询数据
_ret = AsyncTools.sync_run_coroutine(_driver.query_list('tb_init_on_memory', filter={'_id': _id}))
print(_ret)

# 步骤4: 关闭连接
AsyncTools.sync_run_coroutine(_driver.destroy())
```



## 关键设计说明

### 关系型数据库适配NoSQL

当前框架是将所有数据库访问统一抽象为NoSQL操作，因此如果使用关系型数据库作为存储，建议按以下标准的数据表进行设计，以集合名t_demo为例:

 t_demo(_id varchar, ...其他固定索引字段, nosql_driver_extend_tags json)

其中:

- _id为唯一主键, 可通过bson库的objectid模块自动生成
- 固定字段, 可用于查询条件的字段, 注意对顺序并无要求
- nosql_driver_extend_tags, 存放其他扩展信息的字段(尽可能使用支持json的数据库类型, 以支持查询和更新等操作)



### NosqlAIOPoolDriver框架设计

NosqlAIOPoolDriver框架类直接提供了对DB-API规范的支持，因此如果你要适配的驱动是关系型数据库且满足DB-API规范，建议直接继承NosqlAIOPoolDriver来开发实现类，这样最主要的开发内容是实现相关操作的SQL脚本生成代码。



### NoSQL操作遵循MongoDB的标准

该驱动框架的所有NoSQL操作都是遵循MongoDB的标准，包括术语、操作、语法等，可以直接参考MongoDB的手册来使用。



