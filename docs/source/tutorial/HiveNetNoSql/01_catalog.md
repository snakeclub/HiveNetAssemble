# HiveNetNoSql总览

HiveNetNoSql是一个通用的NoSql数据访问驱动框架, 参考MongoDB的语法对NoSql的数据访问操作进行了抽象, 便于对各类数据库(包括关系型数据库和NoSql数据库)采用同一套NoSql操作进行数据访问, 在该包中实现了MongoDB、Sqlite、MySQL、Postgresql的驱动适配, 可以根据自己的需要实现其他数据库的适配实现。


## 安装方法

### 源码方式安装

- HiveNetNoSql库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetNoSql

注意: 包依赖并未安装相应的驱动, 因此如果需要使用包中封装的驱动, 需在安装包时同步安装对应的驱动, 例如：

```
# 同时安装mongodb驱动
pip install HiveNetNoSql motor

# 同时安装sqlite驱动
pip install HiveNetNoSql aiosqlite

# 同时安装mysql驱动
pip install HiveNetNoSql aiomysql

# 同时安装postgresql驱动, 注意该驱动暂时不支持M1版本的mac, 如果是M1版本改为安装同步的psycopg2-binary驱动
pip install HiveNetNoSql psycopg
```



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

### mysql

mysql模块基于aiomysql异步IO驱动提供了MySQL的NosqlDriver实现类MySQLNosqlDriver, 可基于MySQL数据库来进行NoSQL数据访问处理。

### pgsql

pgsql模块基于psycopg 3异步IO驱动提供了Postgresql的NosqlDriver实现类MySQLNosqlDriver, 可基于Postgresql数据库来进行NoSQL数据访问处理。
注：psycopg 3暂时未发布M1版本的MacOS的版本, 因此实现的是psycopg2的同步IO驱动。



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



## MySQL和PostgreSQL的分区表功能支持

mongo自身可以通过集群部署的方式直接支持表数据分区，因此驱动并不包含分区表的支持；而MySQL和PostgreSQL的驱动，在建表和查询相关接口上扩展增加了分区表的支持，不过使用上有以下限制需要注意：

1. MySQL和PostgreSQL的驱动对分区表的支持参数有所差异，因此同样的参数在两个驱动并不一定兼容，使用上需要区分出来；
2. 非分区表的创建，统一使用 “\_id” 字段作为主键；而由于分区表的限制，会将  “\_id” 字段和其他分区字段共同作为联合主键，也就是  “\_id” 并不是唯一主键；
3. 如果 “\_id” 字段没有作为分区条件, 则只创建普通索引而非唯一索引, 此时 “\_id“ 字段的唯一性在数据库层面无法控制, 需要由应用自行控制该字段的唯一性；
4. 要创建唯一索引的字段必须作为分区条件字段之一, 否则将会忽略索引重的唯一索引标识，直接作为普通索引而非唯一索引来创建；



### MySQL分区表功能使用说明

#### partition参数说明

创建表的create_collection函数支持传入partition参数指定表创建为分区表，该参数的说明如下：

- type : str, 指定创建分区的类型，可支持的分区类型如下：

  - range - int类型的范围分区, 分区字段必须为int类型, 或者可支持通过表达式转换为int结果的字段(同步需配置转换表达式); 对应的比较值需设置为int类型的值, 或者以字符串形式的函数表达式, 但函数表达式的结果必须为int类型, 例如"to_days('2021-10-11')"

    注1: range类型分区字段仅支持设置单个字段

    注2: 每个分区的范围设置只有一个比较值, 实际符合分区的取值范围为"上一分区比较值 <= 字段值 < 当前分区比较值"

  - range_columns - 多列范围分区, 与range类似, 但分区字段类型可支持各种类型, 不支持函数表达式; 对应的比较值需设置为与字段类型相同的值或函数表达式

    注1: range_columns可以支持同时设置多个分区字段

    注2: 当设置为多个分区字段时, 符合分区的取值范围为数组比较, 例如字段值(c1, c2)与范围值(v1, v2)的比较表达式为: (c1 < v1 or (c1 == v1 and c2 < v2))

  - list - int类型的列表分区, 分区字段必须为int类型, 或者可支持通过表达式转换为int结果的字段(同步需配置转换表达式); 对应的比较值需设置为数组, 且数组内的值必须为int类型, 或以字符串形式的函数表达式, 但函数表达式的结果必须为int类型

    注1: 分区字段仅支持设置单个字段

    注2: 符合分区的取值范围为在数组中能找到的字段值, 如果所有分区都无法匹配, 数据将无法正常插入数据库

  - list_columns - 全类型列表分区, 与list类似, 但分区字段类型可支持各种类型, 不支持函数表达式

  - hash - 哈希分区, 可以字段的哈希值均匀分布记录, 分区字段必须为int类型, 或者可支持通过表达式转换为int结果的字段(同步需配置转换表达式)

    注1: 分区字段仅支持设置单个字段

    注2: hash类型分区不支持分区范围的设置, 而是通过count参数指定要拆分的分区数量

  - linear_hash - 线性哈希分区, 与hash分区类似, 算法处理更快, 缺点是数据分布不够均匀

  - key - key分区, 与哈希分区类似, 区别是可以支持各种数据类型, 此外可以支持设置多个分区字段

  - linear_key - 线性key分区, 与key分区类似, 算法处理更快, 缺点是数据分布不够均匀

- count: int, 拆分的分区数量, 仅对hash, linear_hash, key, linear_key的分区类型有效

- columns : list, 分区字段设置, 列表每个值为对应的一个分区字段设置字典, 定义如下:

  - col_name : str, 分区字段名

  - func : str, 转换函数表达式, 可通过{col_name}进行字段名的替换, 例如to_days({col_name})

  - range_list : list, 分区条件列表, 设置每个分区名和分区条件比较值, 仅range, range_columns, list, list_columns使用

    - name : str, 分区名, 不设置或设置为None代表自动生成分区名, 如果不是第一个分区字段无需设置(统一使用第一个分区字段的对应分区名)

    - value : any, 分区条件比较值, 按不同分区类型应设置为不同的值

      注1: 如果为range或range_columns, 该值设置为单一比较常量值, 例如 3, "'test'", "to_days('2021-10-11')", None(代表最大值MAXVALUE)

      注2: 如果为list或list_columns, 该值应设置为list, 例如 [3, "'test'", 5, "to_days('2021-01-01')", None], None代表NULL

      注3: 如果值为字符串, 应使用单引号进行包裹, 例如"'str_value'"

- sub_partition: dict, 子分区设置

  - type : str, 子分区类型, hash-哈希子分区, key-key类型子分区

  - columns: list, 分区字段设置, 列表每个值为对应的一个分区字段设置字典, 定义如下(注意hash子分区仅支持1个分区字段, key子分区可以支持多个分区字段):

    - col_name : str, 分区字段名
    - func : str, 转换函数表达式, 可通过{col_name}进行字段名的替换, 例如to_days({col_name})

  - count : int, 要划分的子分区数

  - sub_name : list[list], 指定子分区名, 一维数组长度与父分区数量一致, 二位数组长度与count一致

    ​	例如: [['sub_name1', 'sub_name2'], ['sub_name3', 'sub_name4'], ['sub_name5', 'sub_name6']]

#### partition参数示例

**1、range和hash组合的两级分区表，形成的分区如下：**

分区p1:  匹配条件 to_days(STR_TO_DATE(col_date_str, ’%Y-%m-%d’)) < 10

​        子分区s1：mod(col_sub_int) == 0

​        子分区s2：mod(col_sub_int) == 1

分区p2：匹配条件 10 <= to_days(STR_TO_DATE(col_date_str, ’%Y-%m-%d’)) < 20

​        子分区s3：mod(col_sub_int) == 0

​        子分区s4：mod(col_sub_int) == 1

分区p3：匹配条件 to_days(STR_TO_DATE(col_date_str, ’%Y-%m-%d’)) >= 20

​        子分区s5：mod(col_sub_int) == 0

​        子分区s6：mod(col_sub_int) == 1

```
{
	'type': 'range',
	'columns': [
		{
			'col_name': 'col_date_str',
			'func': 'to_days(STR_TO_DATE({col_name},’%Y-%m-%d’))',
			'range_list': [
				{'name': 'p1', 'value': 10},
				{'name': 'p2', 'value': 20},
				{'name': 'p3', 'value': None}
			]
		}
	],
	'sub_partition': {
		'type': 'hash',
		'columns': [{'col_name': 'col_sub_int'}],
		'count': 2,
		'sub_name': [['s1', 's2'], ['s3', 's4'], ['s5', 's6']]
	}
}
```

**2、list_columns的列表分区，形成的分区如下：**

分区p1:  匹配条件 col_str in ['test1', 'test2']

分区p2：匹配条件 col_str in ['test3']

分区p3：匹配条件 col_str in ['test4', 'test5', NULL]

```
{
	'type': 'list_columns',
	'columns': [
		{
			'col_name': 'col_str',
			'range_list': [
				{'name': 'p1', 'value': ["'test1'", "'test2'"]},
				{'name': 'p2', 'value': ["'test3'"]},
				{'name': 'p3', 'value': ["'test4'", "'test5'", None]}
			]
		}
	]
}
```

**3、key分区，形成的分区如下（分区名为数据库自动生成默认名）：**

分区p1:  匹配条件 mod(hash(col_str)) == 0

分区p2：匹配条件 mod(hash(col_str)) == 1

分区p3：匹配条件 mod(hash(col_str)) == 2

```
{
	'type': 'key',
	'count': 3,
	'columns': [
		{
			'col_name': 'col_str',
		}
	]
}
```

#### 在操作数据时指定分区

驱动的update、delete、query_list、query_iter、query_count、query_group_by函数均可支持对指定分区进行处理，可在函数调用时传入partition参数指定当次操作涉及的分区表，该参数的特殊说明如下：

1、该参数可以支持传入str或list，如果传入list代表指定多个分区，例如 partition='p1' 或 partition=['p1', 'p2', 'p3']

2、除指定一级分区外，该参数也可以直接传入二级分区，例如 ['p1', 's3']



### PostgreSQL分区表功能使用说明

#### partition参数说明

创建表的create_collection函数支持传入partition参数指定表创建为分区表，该参数的说明如下：

- type : str, 指定创建分区的类型，可支持的分区类型如下：

  - range - 范围分区, 支持通过表达式对分区字段进行格式转换(同步需配置转换表达式)

    ​	注1: 支持设置多个分区字段

    ​	注2: 每个分区的范围设置只有一个比较值, 实际符合分区的取值范围为"上一分区比较值 <= 字段值 < 当前分区比较值"

    ​	注3: 将自动创建一个默认分区, 当分区字段值无法匹配设置的分区时, 将存入默认分区中

  - list - 列表分区, 支持通过表达式对分区字段进行格式转换(同步需配置转换表达式)

    ​	注1: 分区字段仅支持设置单个字段

    ​	注2: 符合分区的取值范围为在数组中能找到的字段值

    ​	注3: 将自动创建一个默认分区, 当分区字段值无法匹配设置的分区时, 将存入默认分区中

  - hash - 哈希分区

    ​	注1: 支持设置多个分区字段

    ​	注2: hash类型分区不支持分区范围的设置, 而是通过count参数指定要拆分的分区数量

- count: int, 拆分的分区数量, 仅hash的分区类型有效

- columns : list, 分区字段设置, 列表每个值为对应的一个分区字段设置字典, 定义如下:

  - col_name : str, 分区字段名

  - func : str, 转换函数表达式, 可通过{col_name}进行字段名的替换, 例如to_days({col_name})

  - range_list : list, 分区条件列表, 设置每个分区名和分区条件比较值, 仅range, list使用

    - name : str, 分区名, 不设置或设置为None代表自动生成分区名, 如果不是第一个分区字段无需设置(统一使用第一个分区字段的对应分区名)

    - value : any, 分区条件比较值, 按不同分区类型应设置为不同的值

      ​	注1: 如果为range, 该值设置为单一比较常量值, 例如 3, "'test'", "to_days('2021-10-11')", None(代表最大值MAXVALUE)

      ​	注2: 如果为list, 该值应设置为list, 例如 [3, "'test'", 5, "to_days('2021-01-01')", None], None代表NULL

      ​	注3: 如果值为字符串, 应使用单引号进行包裹, 例如"'str_value'"

- sub_partition: dict, 子分区设置, 定义与主分区一致, 可以嵌套形成多级子分区

  ​	注意: 每个主分区下都会嵌套创建一套相同的子分区

#### 在操作数据时指定分区

驱动的update、delete、query_list、query_iter、query_count、query_group_by函数均可支持对指定分区进行处理，可在函数调用时传入partition参数指定当次操作涉及的分区表，该参数的特殊说明如下：

1、该参数仅支持传入str，也就是只能支持指定单分区，例如 partition='p1'

2、除指定一级分区外，该参数也可以直接传入二级分区，例如 partition='s1'

3、参数实际上传入的是分区表名的后缀，在sql上会自动拼接为完成的分区表名；
