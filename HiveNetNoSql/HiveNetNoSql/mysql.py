#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
MySQL的HiveNetNoSql实现模块

@module mysql
@file mysql.py
"""
import os
import sys
import copy
import re
from typing import Any, Union
import json
import aiomysql
from bson.objectid import ObjectId
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.validate_tool import ValidateTool
from HiveNetCore.connection_pool import PoolConnectionFW
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
try:
    import aiomysql
except ImportError:
    PythonEnvTools.install_package('aiomysql')
    import aiomysql
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetNoSql.base.driver_fw import NosqlAIOPoolDriver


class MySQLPoolConnection(PoolConnectionFW):
    """
    MySQL连接池连接对象
    """
    #############################
    # 需要继承类实现的函数
    #############################
    async def _real_ping(self, *args, **kwargs) -> bool:
        """
        实现类的真实检查连接对象是否有效的的函数

        @returns {bool} - 返回检查结果
        """
        try:
            await AsyncTools.async_run_coroutine(self._conn.ping(reconnect=False))
            return True
        except:
            return False

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


class MySQLNosqlDriver(NosqlAIOPoolDriver):
    """
    nosql数据库MySQL驱动
    """

    #############################
    # 构造函数重载, 主要是注释
    #############################
    def __init__(self, connect_config: dict = {}, pool_config: dict = {}, driver_config: dict = {}):
        """
        初始化驱动

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 数据库主机地址, 默认为'localhost'
            port {int} - 连接数据库的端口, 默认为3306
            usedb {str} - 登录后默认切换到的数据库
            username {str} - 登录验证用户
            password {str} - 登录验证密码
            dbname {str} - 登录用户的数据库名(MySQL无效)
            connect_on_init {bool} - 是否启动时直接连接数据库
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            default_str_len {int} - 默认的字符串类型长度, 默认为30
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
            aiomysql.connect 支持的其他参数...
        @param {dict} pool_config={} - 连接池配置
            max_size {int} - 连接池的最大大小, 默认为100
            min_size {int} - 连接池维持的最小连接数量, 默认为0
            max_idle_time {float} - 连接被移除前的最大空闲时间, 单位为秒, 默认为None
            wait_queue_timeout {float} - 在没有空闲连接的时候, 请求连接所等待的超时时间, 单位为秒, 默认为None(不超时)
            ...驱动实现类自定义支持的参数
            注: 其他参数为AIOConnectionPool所支持的参数
        @param {dict} driver_config={} - 驱动配置
            init_db {dict} - 要在启动驱动时创建的数据库
                {
                    '数据库名': {
                        'index_only': False,  # 是否仅用于索引, 不创建
                        'comment': '',  # 数据库注释
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    }
                }
            init_collections {dict} - 要在启动驱动时创建的集合(表)
                {
                    '数据库名': {
                        '集合名': {
                            'index_only': False,  # 是否仅用于索引, 不创建
                            'comment': '',  # 集合注释
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}, 'partition': {表分区定义}
                        }
                        ...
                    },
                    ...
                }
            init_yaml_file {str} - 要在启动时创建的数据库和集合(表)配置yaml文件
                注1: 该参数用于将init_db和init_collections参数内容放置的配置文件中, 如果参数有值则忽略前面两个参数
                注2: 配置文件为init_db和init_collections两个字典, 内容与这两个参数一致
            logger {Logger} - 传入驱动的日志对象
            ignore_index_error {bool} - 是否忽略索引创建的异常, 默认为True
            debug {bool} - 指定是否debug模式, 默认为False
            close_action {str} - 关闭连接时自动处理动作, None-不处理, 'commit'-自动提交, 'rollback'-自动回滚
            support_desc_index {bool} - 是否支持降序索引, 默认为False, MySQL8.0后的版本支持
        """
        super().__init__(
            connect_config=connect_config, pool_config=pool_config, driver_config=driver_config
        )

        # 指定使用独立的insert_many语句, 性能更高
        self._use_insert_many_generate_sqls = True

    #############################
    # 特殊的重载函数
    #############################

    async def list_dbs(self, *args, **kwargs) -> list:
        """
        列出数据库清单

        @returns {list} - 数据库名清单
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('list_dbs')
        )
        _ret = await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )
        # 需要将字典形式的列表转换为数据库名列表, 查询结果无法转换为标准的name, 需要特殊实现
        return [_db['Database'] for _db in _ret]

    async def create_collection(self, collection: str, indexs: dict = None, fixed_col_define: dict = None,
            comment: str = None, **kwargs):
        """
        创建集合(相当于关系型数据库的表, 如果不存在则创建)
        注意: 所有集合都有必须有 '_id' 这个记录的唯一主键字段

        @param {str} collection - 集合名(表名)
        @param {dict} indexs=None - 要创建的索引字典, 格式为:
            {
                '索引名': {
                    --索引的字段清单
                    'keys': {
                        '字段名': { 'asc': 是否升序(1为升序, -1为降序) },
                        ...
                    }
                    --创建参数
                    'paras': {
                        'unique': 是否唯一索引(True/False),
                        ...驱动实现类自定义支持的参数
                    }
                },
            }
        @param {dict} fixed_col_define=None - 固定字段定义(只有固定字段才能进行索引), 格式如下:
            {
                '字段名': {
                    'type': '字段类型(str, int, float, bool, json)',
                    'len': 字段长度,
                    'nullable': True,  # 是否可空
                    'default': 默认值,
                    'comment': '字段注释'
                },
                ...
            }
        @param {str} comment=None - 集合注释
        @param {kwargs} - 实现驱动自定义支持的参数
            partition {dict} - 表分区设置, 仅支持固定字段的str, int, bool类型
                type : str, 指定创建分区的类型，可支持的分区类型如下：
                    range - int类型的范围分区, 分区字段必须为int类型, 或者可支持通过表达式转换为int结果的字段(同步需配置转换表达式);
                        对应的比较值需设置为int类型的值, 或者以字符串形式的函数表达式, 但函数表达式的结果必须为int类型, 例如"to_days('2021-10-11')"
                        注1: range类型分区字段仅支持设置单个字段
                        注2: 每个分区的范围设置只有一个比较值, 实际符合分区的取值范围为"上一分区比较值 <= 字段值 < 当前分区比较值"
                    range_columns - 多列范围分区, 与range类似, 但分区字段类型可支持各种类型, 不支持函数表达式; 对应的比较值需设置为与字段类型相同的值或函数表达式
                        注1: range_columns可以支持同时设置多个分区字段
                        注2: 当设置为多个分区字段时, 符合分区的取值范围为数组比较, 例如字段值(c1, c2)与范围值(v1, v2)的比较表达式为: (c1 < v1 or (c1 == v1 and c2 < v2))
                    list - int类型的列表分区, 分区字段必须为int类型, 或者可支持通过表达式转换为int结果的字段(同步需配置转换表达式);
                        对应的比较值需设置为数组, 且数组内的值必须为int类型, 或以字符串形式的函数表达式, 但函数表达式的结果必须为int类型
                        注1: 分区字段仅支持设置单个字段
                        注2: 符合分区的取值范围为在数组中能找到的字段值, 如果所有分区都无法匹配, 数据将无法正常插入数据库
                    list_columns - 全类型列表分区, 与list类似, 但分区字段类型可支持各种类型, 不支持函数表达式
                    hash - 哈希分区, 可以字段的哈希值均匀分布记录, 分区字段必须为int类型, 或者可支持通过表达式转换为int结果的字段(同步需配置转换表达式)
                        注1: 分区字段仅支持设置单个字段
                        注2: hash类型分区不支持分区范围的设置, 而是通过count参数指定要拆分的分区数量
                    linear_hash - 线性哈希分区, 与hash分区类似, 算法处理更快, 缺点是数据分布不够均匀
                    key - key分区, 与哈希分区类似, 区别是可以支持各种数据类型, 此外可以支持设置多个分区字段
                    linear_key - 线性key分区, 与key分区类似, 算法处理更快, 缺点是数据分布不够均匀
                count: int, 拆分的分区数量, 仅对hash, linear_hash, key, linear_key的分区类型有效
                columns : list, 分区字段设置, 列表每个值为对应的一个分区字段设置字典, 定义如下:
                    col_name : str, 分区字段名
                    func : str, 转换函数表达式, 可通过{col_name}进行字段名的替换, 例如to_days({col_name})
                    range_list : list, 分区条件列表, 设置每个分区名和分区条件比较值, 仅range, range_columns, list, list_columns使用
                        name : str, 分区名, 不设置或设置为None代表自动生成分区名, 如果不是第一个分区字段无需设置(统一使用第一个分区字段的对应分区名)
                        value : any, 分区条件比较值, 按不同分区类型应设置为不同的值
                            注1: 如果为range或range_columns, 该值设置为单一比较常量值, 例如 3, "'test'", "to_days('2021-10-11')", None(代表最大值MAXVALUE)
                            注2: 如果为list或list_columns, 该值应设置为list, 例如 [3, "'test'", 5, "to_days('2021-01-01')", None], None代表NULL
                            注3: 如果值为字符串, 应使用单引号进行包裹, 例如"'str_value'"
                sub_partition: dict, 子分区设置
                    type : str, 子分区类型, hash-哈希子分区, key-key类型子分区
                    columns: list, 分区字段设置, 列表每个值为对应的一个分区字段设置字典, 定义如下(注意hash子分区仅支持1个分区字段, key子分区可以支持多个分区字段):
                        col_name : str, 分区字段名
                        func : str, 转换函数表达式, 可通过{col_name}进行字段名的替换, 例如to_days({col_name})
                    count : int, 要划分的子分区数
                    sub_name : list[list], 指定子分区名, 一维数组长度与父分区数量一致, 二位数组长度与count一致
                        例如: [['sub_name1', 'sub_name2'], ['sub_name3', 'sub_name4'], ['sub_name5', 'sub_name6']]
                注: 使用表分区的限制:
                    1. 如果 _id 没有作为分区条件, 则仅创建普通索引而非唯一索引, _id 的唯一性数据库层面不控制, 需要由应用自行控制
                    2. 要创建唯一索引的字段必须作为分区条件之一, 否则将会作为普通索引而非唯一索引来创建
        """
        # 只是单纯解决注释问题
        await super().create_collection(
            collection, indexs=indexs, fixed_col_define=fixed_col_define, comment=comment,
            **kwargs
        )

    #############################
    # 需要继承类实现的内部函数
    #############################
    def _get_db_creator(self, connect_config: dict, pool_config: dict, driver_config: dict) -> tuple:
        """
        获取数据库连接驱动及参数

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 数据库主机地址, 默认为'localhost'
            port {int} - 连接数据库的端口, 默认为3306
            usedb {str} - 登录后默认切换到的数据库
            username {str} - 登录验证用户
            password {str} - 登录验证密码
            dbname {str} - 登录用户的数据库名(MySQL无效)
            connect_on_init {bool} - 是否启动时直接连接数据库
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
            aiomysql.connect 支持的其他参数...
        @param {dict} pool_config={} - 连接池配置
            max_size {int} - 连接池的最大大小, 默认为100
            min_size {int} - 连接池维持的最小连接数量, 默认为0
            max_idle_time {float} - 连接被移除前的最大空闲时间, 单位为秒, 默认为None
            wait_queue_timeout {float} - 在没有空闲连接的时候, 请求连接所等待的超时时间, 单位为秒, 默认为None(不超时)
            ...驱动实现类自定义支持的参数
            wait_connection_idle {float} - 没有空闲连接时, 等待获取连接的间隔时长, 单位为秒, 默认维护0.01
        @param {dict} driver_config={} - 驱动配置
            init_db {dict} - 要在启动驱动时创建的数据库
                {
                    '数据库名': {
                        'index_only': False,  # 是否仅用于索引, 不创建
                        'comment': '',  # 数据库注释
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    }
                }
            init_collections {dict} - 要在启动驱动时创建的集合(表)
                {
                    '数据库名': {
                        '集合名': {
                            'index_only': False,  # 是否仅用于索引, 不创建
                            'comment': '',  # 集合注释
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}
                        }
                        ...
                    },
                    ...
                }
            logger {Logger} - 传入驱动的日志对象
            debug {bool} - 指定是否debug模式, 默认为False
            close_action {str} - 关闭连接时自动处理动作, None-不处理, 'commit'-自动提交, 'rollback'-自动回滚
        @returns {dict} - 返回连接池的相关参数
            {
                'creator': class,  # 连接创建模块或对象
                'pool_connection_class': class,  # 连接池连接对象实现类(继承PoolConnectionFW的类对象)
                'args': [], # 进行连接创建的固定位置参数
                'kwargs': {}, # 进行连接创建的kv参数
                'connect_method_name': 'connect', # 连接创建模块要执行的连接方法, 传None代表直接使用creator创建连接
                'pool_update_config': {}, # 要指定AIOConnectionPool特定值的更新字典
                'current_db_name': '',  # 当前数据库名
            }
        """
        # 初始化处理函数的映射字典
        self._sqls_fun_mapping = {
            'create_db': self._sqls_fun_create_db,
            'switch_db': self._sqls_fun_not_support,
            'list_dbs': self._sqls_fun_list_dbs,
            'drop_db': self._sqls_fun_drop_db,
            'create_collection': self._sqls_fun_create_collection,
            'list_collections': self._sql_fun_list_collections,
            'drop_collection': self._sql_fun_drop_collection,
            'turncate_collection': self._sql_fun_turncate_collection,
            'insert_one': self._sql_fun_insert_one,
            'insert_many': self._sql_fun_insert_many,
            'update': self._sql_fun_update,
            'delete': self._sql_fun_delete,
            'query': self._sql_fun_query,
            'query_count': self._sql_fun_query_count,
            'query_group_by': self._sql_fun_query_group_by
        }

        # 初始化查询操作符对应的符号
        self._filter_symbol_mapping = {
            '$lt': '<',
            '$lte': '<=',
            '$gt': '>',
            '$gte': '>=',
            '$ne': '!='
        }

        # 生成aiomysql的连接配置
        _args = []
        _kwargs = {}

        # 要处理的参数
        _kwargs['db'] = connect_config.get('usedb', None)
        _kwargs['user'] = connect_config.get('username', None)
        _kwargs['connect_timeout'] = connect_config.get('connect_timeout', 20)

        # 移除不使用的参数
        _connect_config = copy.deepcopy(connect_config)
        for _pop_item in ('usedb', 'dbname', 'username', 'connect_on_init', 'connect_timeout', 'transaction_share_cursor'):
            _connect_config.pop(_pop_item, None)

        # 合并参数
        _kwargs.update(_connect_config)

        return {
            'creator': aiomysql, 'pool_connection_class': MySQLPoolConnection,
            'args': _args, 'kwargs': _kwargs, 'connect_method_name': 'connect',
            'pool_update_config': {
                'pool_extend_paras': {
                    'close_action': driver_config.get('close_action', None)
                }
            },
            'current_db_name': _kwargs['db']
        }

    def _generate_sqls(self, op: str, *args, **kwargs) -> tuple:
        """
        生成对应操作要执行的sql语句数组

        @param {str} op - 要执行的操作(传入函数名字符串)
        @param {args} - 要执行操作函数的固定位置入参
        @param {kwargs} - 要执行操作函数的kv入参

        @returns {tuple} - 返回要执行的sql信息(sqls, sql_paras, execute_paras)
            sqls: list, 要顺序执行的sql语句数组; 注意, 仅最后一个语句支持为查询语句, 前面的语句都必须为非查询语句
            sql_paras: list, 传入的SQL参数字典(支持?占位), 注意必须与sqls数组一一对应(如果只有个别语句需要传参, 其他位置设置为None; 如果全部都无需传参, 该值直接传None)
            execute_paras: dict, 最后一个SQL语句的执行参数 {'is_query': ...}
            checks: list, 传入每个语句执行检查字典列表, 注意必须与sqls数组一一对应(如果只有个别语句需要传参, 其他位置设置为None; 如果全部都无需传参, 该值直接传None)
        """
        _func = self._sqls_fun_mapping.get(op, None)
        if _func is None:
            raise aiomysql.NotSupportedError('driver not support this operation')

        _ret = _func(op, *args, **kwargs)
        if len(_ret) == 4:
            return _ret
        else:
            _new_ret = []
            _new_ret.extend(_ret)
            _new_ret.append(None)  # 补充最后一个参数
            return _new_ret

    def _format_row_value(self, row: list) -> list:
        """
        处理行记录的值(数据库存储类型转为Python类型)

        @param {list} row - 行记录

        @returns {list} - 转换后的行记录
        """
        _new_row = []
        for _item in row:
            _new_row.append(self._dbtype_to_python(_item))

        return _new_row

    def _driver_init_connection(self, conn: Any):
        """
        驱动对获取到的连接的初始化处理

        @param {Any} conn - 传入连接对象
        """
        pass

    async def _get_cols_info(self, collection: str, db_name: str = None, session: Any = None) -> list:
        """
        获取制定集合(表)的列信息

        @param {str} collection - 集合名(表)
        @param {str} db_name=None - 数据库名(不指定代表默认当前数据库)
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 字典形式的列信息数组, 注意列名为name, 类型为type(类型应为标准类型: str, int, float, bool, json)
        """
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
        else:
            _conn = None
            _cursor = None

        # 获取表结构
        _db_name = self._db_name if db_name is None else db_name
        _sql = "select column_name as name, data_type as type from information_schema.columns where table_schema='%s' and table_name='%s'" % (
            _db_name, collection
        )
        _ret = await self._execute_sql(
            _sql, paras=None, is_query=True, conn=_conn, cursor=_cursor
        )

        # 处理标准类型
        for _row in _ret:
            if _row['type'] == 'tinyint':
                _row['type'] = 'bool'
            elif _row['type'].startswith('varchar('):
                _row['type'] = 'str'

        return _ret

    async def _get_current_db_name(self, session: Any = None) -> str:
        """
        获取当前数据库名

        @param {Any} session=None - 指定事务连接对象

        @returns {str} - 数据库名
        """
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
        else:
            _conn = None
            _cursor = None

        # 获取当前数据库名称
        _sql = "SELECT DATABASE() as db_name"
        _ret = await self._execute_sql(
            _sql, paras=None, is_query=True, conn=_conn, cursor=_cursor
        )

        return _ret[0]['db_name']

    #############################
    # 需要单独重载的函数
    #############################
    async def switch_db(self, name: str):
        """
        切换当前数据库到指定数据库

        @param {str} name - 数据库名
        """
        self._db_name = name

    #############################
    # 支持SQL处理的通用函数
    #############################
    def _dbtype_mapping(self, std_type: str, len: int) -> str:
        """
        获取字段的数据库类型

        @param {str} std_type - 字段类型(str, int, float, bool, json)
        @param {int} len - 字段长度

        @returns {str} - 返回数据库类型
        """
        if std_type in ('int', 'float'):
            return std_type
        elif std_type == 'bool':
            return 'bool'
        elif std_type == 'json':
            return 'json'
        else:
            return 'varchar(%d)' % (self._default_str_len if len is None else len)

    def _python_to_dbtype(self, val: Any, dbtype: str = None, is_json: bool = False) -> tuple:
        """
        将Python对象转换为数据库存储类型

        @param {Any} val - 要转换的Python对象
        @param {str} dbtype=None - 强制指定数据库类型, 如果不指定则自动判断
        @param {str} is_json=False - 是否json数据(用于存入json的内容)

        @returns {tuple} - 返回转换后的结果(dbtype, dbvalue)
        """
        # 判断类型
        _dbtype = dbtype
        if _dbtype is None:
            _pytype = type(val)
            if _pytype == bool:
                _dbtype = 'bool'
            elif _pytype == int:
                _dbtype = 'int'
            elif _pytype == float:
                _dbtype = 'float'
            elif _pytype in (dict, tuple, list):
                _dbtype = 'json'
            else:
                _dbtype = 'str'

        # 进行转换处理
        _dbvalue = None
        if val is not None:
            if _dbtype == 'bool':
                if is_json:
                    _dbvalue = 'true' if val else 'false'
                else:
                    _dbvalue = 1 if val else 0
            elif _dbtype in ('int', 'float'):
                _dbvalue = val
            elif _dbtype == 'json':
                _dbvalue = json.dumps(val, ensure_ascii=False)
            else:
                _dbvalue = str(val)

        # 返回结果
        return (_dbtype, _dbvalue)

    def _dbtype_to_python(self, val: Any) -> Any:
        """
        数据库值转换为python类型

        @param {Any} val - 数据库值

        @returns {Any} - Python值
        """
        if type(val) == str:
            try:
                return json.loads(val)
            except:
                return val
        else:
            return val

    def _db_quotes_str(self, val: str) -> str:
        """
        数据库单引号转义处理

        @param {str} val - 要处理的字符串

        @returns {str} - 转义处理后的字符串, 注意不包含外面的引号
        """
        return re.sub(r"\'", "''", re.sub(r"\\", "\\\\", val))  # 单引号转义和反斜杠转义

    def _get_filter_unit_sql(self, key: str, val: Any, fixed_col_define: dict = None,
            sql_paras: list = [], left_join: list = None, session=None) -> str:
        """
        获取兼容mongodb过滤条件规则的单个规则对应的sql

        @param {str} key - 规则key
        @param {Any} val - 规则值
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {list} left_join=None - 左关联配置
        @param {Any} session=None - 数据库事务连接对象

        @returns {str} - 单个规则对应的sql
        """
        # 根据字段判断是主表还是关联表
        _key = key
        _fixed_cols = None
        if _key[0] != '#':
            # 主表的过滤条件
            _as_name = ''
            if fixed_col_define is not None:
                _fixed_cols = copy.deepcopy(fixed_col_define.get('cols', []))
        else:
            # 关联表的过滤条件
            _index = _key.find('.')
            _join_para = left_join[int(_key[1: _index])]
            _key = _key[_index+1:]

            _join_db_name = _join_para.get('db_name', self._db_name)
            _join_tab = _join_para['collection']
            _as_name = '`%s`.' % _join_para.get('as', _join_tab)

            _fixed_col_define = AsyncTools.sync_run_coroutine(self._get_fixed_col_define(
                _join_tab, db_name=_join_db_name, session=session
            ))
            if _fixed_col_define is not None:
                _fixed_cols = copy.deepcopy(_fixed_col_define.get('cols', []))

        # 判断是否处理json的值, 形成最后比较的 key 值
        _is_json = False
        if _fixed_cols is not None:
            if _key != '_id' and _key not in _fixed_cols:
                _is_json = True
                _path_cols = _key.split('.')
                if len(_path_cols) > 1 and _path_cols[0] in _fixed_cols:
                    # json固定字段
                    _path = self._convert_path_array(_path_cols[1:])
                    _key = "%s`%s`->'$.%s'" % (_as_name, _path_cols[0], _path)
                else:
                    _path = self._convert_path_array(_path_cols)
                    _key = "%s`nosql_driver_extend_tags`->'$.%s'" % (_as_name, _path)

        if type(val) == dict:
            # 有特殊规则
            _cds = []  # 每个规则的数组
            for _op, _para in val.items():
                if _op in self._filter_symbol_mapping.keys():
                    # 比较值转换为数据库的格式
                    _dbtype, _cmp_val = self._python_to_dbtype(_para)
                    _cds.append('%s %s %s' % (_key if _is_json else '%s`%s`' % (_as_name, _key), self._filter_symbol_mapping[_op], '%s'))
                    sql_paras.append(_cmp_val)
                elif _op in ('$in', '$nin'):
                    # in 和 not in
                    _cds.append('%s %s (%s)' % (
                        _key if _is_json else '%s`%s`' % (_as_name, _key), 'in' if _op == '$in' else 'not in',
                        ','.join(['%s' for _item in _para])
                    ))
                    for _item in _para:
                        _dbtype, _cmp_val = self._python_to_dbtype(_item)
                        sql_paras.append(_cmp_val)
                elif _op == '$regex':
                    if _is_json:
                        # json查出来的字段默认带双引号, 因此需要去掉双引号才能进行正则比对
                        _cds.append("trim(both '\"' from %s) REGEXP %s" % (_key if _is_json else '%s`%s`' % (_as_name, _key), '%s'))
                    else:
                        _cds.append("%s REGEXP %s" % (_key if _is_json else '%s`%s`' % (_as_name, _key), '%s'))
                    sql_paras.append(_para)
                else:
                    raise aiomysql.NotSupportedError('aiomysql not support this search operation [%s]' % _op)
            _sql = ' and '.join(_cds)
        else:
            # 直接相等的条件
            if val is None:
                _sql = '%s is NULL' % (_key if _is_json else '%s`%s`' % (_as_name, _key))
            else:
                _dbtype, _cmp_val = self._python_to_dbtype(val)
                _sql = '%s = %s' % (_key if _is_json else '%s`%s`' % (_as_name, _key), '%s')
                sql_paras.append(_cmp_val)

        return _sql

    def _get_filter_sql(self, filter: dict, fixed_col_define: dict = None,
            sql_paras: list = [], left_join: list = None, session=None) -> str:
        """
        获取兼容mongodb过滤条件规则的sql语句

        @param {dict} filter - 过滤规则字典
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {list} left_join=None - 左关联配置
        @param {Any} session=None - 数据库事务连接对象

        @returns {str} - 返回的sql语句, 如果没有条件则返回None
        """
        if filter is None or len(filter) == 0:
            return None

        # 遍历进行解析
        _condition_list = []
        for _col, _val in filter.items():
            if _col == '$or':
                # or的情况，处理的是字典数组
                _or_list = list()
                for _condition in _val:
                    # 逐个条件处理
                    _where = self._get_filter_sql(
                        _condition, fixed_col_define=fixed_col_define, sql_paras=sql_paras,
                        left_join=left_join, session=session
                    )
                    if len(_condition) > 1:
                        # 多条件的情况，需要增加括号进行集合处理
                        _where = '(%s)' % _where

                    if _where is not None:
                        _or_list.append(_where)

                # 组合放到全局列表中
                _condition_list.append(
                    '(%s)' % ' or '.join(_or_list)
                )
            else:
                # 正常的and条件
                _where = self._get_filter_unit_sql(
                    _col, _val, fixed_col_define=fixed_col_define, sql_paras=sql_paras,
                    left_join=left_join, session=session
                )
                # 添加条件
                _condition_list.append(_where)

        # 组合条件并返回
        return ' and '.join(_condition_list)

    def _get_update_sql(self, update: dict, fixed_col_define: dict = None,
            sql_paras: list = []) -> str:
        """
        获取兼容mongodb更新语句的sql语句

        @param {dict} update - 更新配置字典
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数

        @returns {str} - 返回更新部分语句sql
        """
        # 更新辅助字典, key为要更新的字段名, value为{'sql': '对应的sql语句, 比如%s', 'paras': [传入sql的参数列表]}
        _upd_dict = {}

        # 扩展字典, key为物理字段名, value为对应的扩展设置
        # 'set_dict': {'sqls': [], 'paras': []} , 扩展字段的set字典, 设置json指定key的值, 每处理一个字段在sqls增加一个语句, 对应在paras参数列表
        # 'remove_list': [] , 扩展字段的remove列表, 为要删除json的key的字段列表
        _extend = {}

        # 遍历处理
        for _op, _para in update.items():
            for _key, _val in _para.items():
                if fixed_col_define is None or _key == '_id' or _key in fixed_col_define.get('cols', []):
                    # 是固定字段
                    if _op == '$set':
                        _upd_dict[_key] = {'sql': '%s', 'paras': [self._python_to_dbtype(_val)[1]]}
                    elif _op == '$unset':
                        _upd_dict[_key] = {'sql': 'NULL', 'paras': []}
                    elif _op == '$inc':
                        _upd_dict[_key] = {'sql': 'ifnull(%s,0) + %s' % (_key, '%s'), 'paras': [_val]}
                    elif _op == '$mul':
                        _upd_dict[_key] = {'sql': 'ifnull(%s,0) * %s' % (_key, '%s'), 'paras': [_val]}
                    elif _op == '$min':
                        _upd_dict[_key] = {
                            'sql': 'case when ifnull({key}, {pos}) < {pos} then ifnull({key},0) else {pos} end'.format(key=_key, pos='%s'),
                            'paras': [_val, _val, _val]
                        }
                    elif _op == '$max':
                        _upd_dict[_key] = {
                            'sql': 'case when ifnull({key}, {pos}) > {pos} then ifnull({key},0) else {pos} end'.format(key=_key, pos='%s'),
                            'paras': [_val, _val, _val]
                        }
                    else:
                        raise aiomysql.NotSupportedError('aiomysql not support this update operation [%s]' % _op)
                else:
                    # 是扩展字段
                    _path_cols = _key.split('.')
                    if len(_path_cols) > 1 and _path_cols[0] in fixed_col_define.get('cols', []):
                        _col_name = _path_cols[0]
                        _path = self._convert_path_array(_path_cols[1:])
                    else:
                        _col_name = 'nosql_driver_extend_tags'
                        _path = self._convert_path_array(_path_cols)

                    # 初始化扩展字典
                    if _extend.get(_col_name, None) is None:
                        _extend[_col_name] = {
                            'set_dict': {'sqls': [], 'paras': []}, 'remove_list': []
                        }

                    if _op == '$set':
                        _dbtype, _dbval = self._python_to_dbtype(_val, is_json=True)
                        if _dbtype in ('int', 'float', 'bool'):
                            _sql = "'$.{key}', {val}"
                        elif _dbtype == 'json':
                            _sql = "'$.{key}', CONVERT({pos}, json)"
                            _extend[_col_name]['set_dict']['paras'].append(_dbval)
                        else:
                            _sql = "'$.{key}', {pos}"
                            _extend[_col_name]['set_dict']['paras'].append(_dbval)
                    elif _op == '$unset':
                        _extend[_col_name]['remove_list'].append("'$.%s'" % _key)
                        continue
                    elif _op in ('$inc', '$mul', '$min', '$max'):
                        _dbtype, _dbval = self._python_to_dbtype(_val, is_json=True)
                        # 需要取值出来, 添加查询字段
                        if _op == '$inc':
                            _sql = "'$.{key}', cast((ifnull(`{col_name}`->'$.{key}', 0) + {val}) as float)"
                            # _extend_set_dict['paras'].append(_dbval)
                        elif _op == '$mul':
                            _sql = "'$.{key}', cast((ifnull(`{col_name}`->'$.{key}', 0) * {val}) as float)"
                            # _extend_set_dict['paras'].append(_dbval)
                        elif _op == '$min':
                            _sql = "'$.{key}', cast(case when ifnull(`{col_name}`->'$.{key}', {val}) < {val} then ifnull(`{col_name}`->'$.{key}', 0) else {val} end as float)"
                            # _extend_set_dict['paras'].extend([_dbval, _dbval, _dbval])
                        elif _op == '$max':
                            _sql = "'$.{key}', cast(case when ifnull(`{col_name}`->'$.{key}', {val}) > {val} then ifnull(`{col_name}`->'$.{key}', 0) else {val} end as float)"
                            # _extend_set_dict['paras'].extend([_dbval, _dbval, _dbval])
                    else:
                        raise aiomysql.NotSupportedError('aiomysql not support this update operation [%s]' % _op)

                    # 处理格式化
                    _extend[_col_name]['set_dict']['sqls'].append(
                        _sql.format(key=_path, pos='%s', val=str(_dbval), col_name=_col_name)
                    )

        # 开始生成sql语句和返回参数
        _sqls = []
        for _key, _val in _upd_dict.items():
            _sqls.append('`%s`=%s' % (_key, _val['sql']))
            if _val['paras'] is not None:
                sql_paras.extend(_val['paras'])

        # 处理扩展字段
        for _col_name, _extend_para in _extend.items():
            _remove_sql = ''
            if len(_extend_para['remove_list']) > 0:
                _remove_sql = "JSON_REMOVE(`%s`, %s)" % (_col_name, ','.join(_extend_para['remove_list']))

            if len(_extend_para['set_dict']['sqls']) == 0:
                if _remove_sql != '':
                    _sqls.append('`%s`=%s' % (_col_name, _remove_sql))
            else:
                _sqls.append(
                    '`%s`=JSON_SET(%s, %s)' % (
                        _col_name,
                        _col_name if _remove_sql == '' else _remove_sql,
                        ','.join(_extend_para['set_dict']['sqls'])
                    )
                )
                sql_paras.extend(_extend_para['set_dict']['paras'])

        return ','.join(_sqls)

    def _get_projection_sql(self, projection: Union[dict, list], fixed_col_define: dict = None,
            sql_paras: list = [], is_group_by: bool = False, as_name: str = None,
            left_join: list = None, session=None) -> str:
        """
        获取兼容mongodb查询返回字段的sql语句

        @param {Union[dict, list]} projection - 指定结果返回的字段信息
            列表模式: ['col1','col2', ...]  注意: 该模式一定会返回 _id 这个主键
            字典模式: {'_id': False, 'col1': True, ...}  该方式可以通过设置False屏蔽 _id 的返回
                注: 字典模式的值也可以传入字符串, 如果是字符串, 则代表key为别名, value才是真正的字段
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {bool} is_group_by=False - 指定是否group by的处理, 如果是不会处理_id字段
        @param {str} as_name=None - 字段对应的表别名
        @param {list} left_join - 左关联配置
        @param {Any} session=None - 数据库事务连接对象

        @returns {str} - 返回更新部分语句sql
        """
        # 如果不指定, 返回所有字段
        if projection is None:
            _project_sql = '%s*' % ('' if as_name is None else ('`%s`.' % as_name))
            if left_join is not None:
                # 补充关联表的所有字段获取
                for _join_para in left_join:
                    _project_sql = '%s, `%s`.*' % (
                        _project_sql, _join_para.get('as', _join_para['collection'])
                    )

            return _project_sql

        # 定义的内部函数
        def _get_join_col_info(col: str, left_join: list, tab_as_name: str) -> tuple:
            # 获取关联表列信息
            if col[0] == '#':
                _index = col.find('.')
                _join_para = left_join[int(col[1: _index])]
                _col = col[_index+1:]
                _join_as_name = _join_para.get('as', _join_para['collection'])
                _join_as_name_sql = '`%s`.' % _join_as_name
            else:
                _col = col
                _join_as_name = '_main_tab' if tab_as_name is None else tab_as_name
                _join_as_name_sql = '' if tab_as_name is None else ('`%s`.' % tab_as_name)

            return _col, _join_as_name, _join_as_name_sql

        # 标准化要显示的字段清单
        _projection = {}
        if type(projection) == dict:
            for _key, _show in projection.items():
                if type(_show) == str and _show[0] == '$':
                    _col, _tab_as_name, _tab_as_name_sql = _get_join_col_info(
                        _show[1:], left_join, as_name
                    )
                    _projection[_key] = {
                        'col': _col, 'tab_as': _tab_as_name, 'tab_as_sql': _tab_as_name_sql,
                        'col_as': _key
                    }
                elif _show:
                    _col, _tab_as_name, _tab_as_name_sql = _get_join_col_info(
                        _key, left_join, as_name
                    )
                    _projection[_key] = {
                        'col': _col, 'tab_as': _tab_as_name, 'tab_as_sql': _tab_as_name_sql
                    }
        else:
            # 列表形式, _id是必须包含的
            if not is_group_by and '_id' not in projection:
                _projection['_id'] = {
                    'col': '_id', 'tab_as': '_main_tab' if as_name is None else as_name,
                    'tab_as_sql': '' if as_name is None else ('`%s`.' % as_name)
                }

            for _key in projection:
                _col, _tab_as_name, _tab_as_name_sql = _get_join_col_info(
                    _key, left_join, as_name
                )
                _projection[_key] = {
                    'col': _col, 'tab_as': _tab_as_name, 'tab_as_sql': _tab_as_name_sql
                }

        # 处理fixed_cols参数
        _fixed_cols_dict = {}
        if fixed_col_define is not None:
            # 主表的列参数
            _tab_as_name = '_main_tab' if as_name is None else as_name
            _fixed_cols_dict[_tab_as_name] = {
                'fixed_define': fixed_col_define,
                'fixed_cols': copy.deepcopy(fixed_col_define.get('cols', []))
            }
            _fixed_cols_dict[_tab_as_name]['fixed_cols'].append('_id')

        if left_join is not None:
            # 关联表的列参数
            for _join_para in left_join:
                _join_db_name = _join_para.get('db_name', self._db_name)
                _join_tab = _join_para['collection']
                _join_as_name = _join_para.get('as', _join_tab)
                _fixed_col_define = AsyncTools.sync_run_coroutine(self._get_fixed_col_define(
                    _join_tab, db_name=_join_db_name, session=session
                ))
                if _fixed_col_define is not None:
                    _fixed_cols_dict[_join_as_name] = {
                        'fixed_define': _fixed_col_define,
                        'fixed_cols': copy.deepcopy(_fixed_col_define.get('cols', []))
                    }
                    _fixed_cols_dict[_join_as_name]['fixed_cols'].append('_id')

        # 生成sql
        _real_cols = []
        for _key, _val in _projection.items():
            _fixed_col_define = _fixed_cols_dict.get(_val['tab_as'], {}).get('fixed_define', None)
            _fixed_cols = _fixed_cols_dict.get(_val['tab_as'], {}).get('fixed_cols', None)
            _col = _val['col']
            _as_name = _val['tab_as_sql']
            if _fixed_cols is None or _col in _fixed_cols:
                _real_cols.append(('%s`%s`' % (_as_name, _col)) if _val.get('col_as', None) is None else '%s`%s` as `%s`' % (_as_name, _col, _val['col_as']))
            else:
                # 其他非固定字段
                _path_cols = _col.split('.')
                if len(_path_cols) > 1 and _path_cols[0] in _fixed_cols:
                    _col_name = _path_cols[0]
                    _path = self._convert_path_array(_path_cols[1:])
                else:
                    _col_name = 'nosql_driver_extend_tags'
                    _path = self._convert_path_array(_path_cols)

                _col_as_name = _col if _val.get('col_as', None) is None else _val['col_as']
                _real_cols.append(
                    "{tab_as_name}`{col_name}`->'$.{path}' as `{as_name}`".format(
                        path=_path, col_name=_col_name, as_name=_col_as_name, tab_as_name=_as_name
                    )
                )

        # 返回sql
        return ','.join(_real_cols)

    def _get_sort_sql(self, sort: list, fixed_col_define: dict = None,
            sql_paras: list = [], left_join: list = None, session=None) -> str:
        """
        获取兼容mongodb查询排序的sql语句

        @param {list} sort - 查询结果的排序方式
            例: [('col1', 1), ...]  注: 参数的第2个值指定是否升序(1为升序, -1为降序)
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {list} left_join=None - 左关联配置
        @param {Any} session=None - 数据库事务连接对象

        @returns {str} - 返回更新部分语句sql
        """
        _sorts = []
        # 主表的字段定义参数
        _main_fixed_cols = None
        if fixed_col_define is not None:
            _main_fixed_cols = copy.deepcopy(fixed_col_define.get('cols', []))
            _main_fixed_cols.append('_id')

        # 关联表的字段定义列表
        _fixed_cols_dict = {}

        # 循环处理每个排序参数
        for _item in sort:
            # 处理临时参数
            _col: str = _item[0]
            if _col[0] != '#':
                # 属于主表字段
                _as_name = ''
                _fixed_cols = _main_fixed_cols
            else:
                # 属于关联表字段
                _index = _col.find('.')
                _join_para = left_join[int(_col[1: _index])]
                _col = _col[_index+1:]

                _join_db_name = _join_para.get('db_name', self._db_name)
                _join_tab = _join_para['collection']
                _as_name = '`%s`.' % _join_para.get('as', _join_tab)
                if _as_name in _fixed_cols_dict.keys():
                    _fixed_cols = _fixed_cols_dict.get(_as_name, None)
                else:
                    # 重新获取并放入缓存字典
                    _fixed_col_define = AsyncTools.sync_run_coroutine(self._get_fixed_col_define(
                        _join_tab, db_name=_join_db_name, session=session
                    ))
                    _fixed_cols = copy.deepcopy(_fixed_col_define.get('cols', []))
                    _fixed_cols.append('_id')
                    _fixed_cols_dict[_as_name] = _fixed_cols

            # 生成排序sql语句
            if _fixed_cols is None:
                # 所有字段认为是固定字段
                _sorts.append('%s`%s` %s' % (_as_name, _col, 'asc' if _item[1] == 1 else 'desc'))
            else:
                if _col in _fixed_cols:
                    _sorts.append('%s`%s` %s' % (_as_name, _col, 'asc' if _item[1] == 1 else 'desc'))
                else:
                    # 属于扩展字段
                    _path_cols = _col.split('.')
                    if len(_path_cols) > 1 and _path_cols[0] in _fixed_cols:
                        _col_name = _path_cols[0]
                        _path = self._convert_path_array(_path_cols[1:])
                    else:
                        _col_name = 'nosql_driver_extend_tags'
                        _path = self._convert_path_array(_path_cols)

                    _sorts.append(
                        "%s`%s`->'$.%s' %s" % (_as_name, _col_name, _path, 'asc' if _item[1] == 1 else 'desc')
                    )

        # 返回结果
        return ','.join(_sorts)

    def _get_group_sql(self, group: dict, fixed_col_define: dict = None,
            sql_paras: list = []) -> tuple:
        """
        生成分组sql语句

        @param {dict} group - 分组返回设置字典(注意与mongodb的_id要求有所区别)
            指定分组字段为col1、col2, 聚合字段为count、pay_amt, 其中pay_amt统计col_pay字段的合计数值
            {'id': '$col1', 'name': '$col2', 'count': {'$sum': 1}, 'pay_amt': {'$sum': '$col_pay'}}
            常见的聚合类型: $sum-计算总和, $avg-计算平均值, $min-取最小值, $max-取最大值, $first-取第一条, $last-取最后一条
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数

        @returns {tuple} - 返回sql, (select语句, group by语句)
        """
        # 固定字段定义
        if fixed_col_define is None:
            _fixed_cols = []
        else:
            _fixed_cols = copy.deepcopy(fixed_col_define.get('cols', []))
            _fixed_cols.append('_id')

        # 函数操作名映射
        _op_mapping = {
            '$sum': 'SUM',
            '$avg': 'AVG',
            '$min': 'MIN',
            '$max': 'MAX'
        }

        _select = []
        _groupby = []
        for _key, _val in group.items():
            _val_type = type(_val)
            if _val_type == dict:
                # 是聚合函数
                _op = list(_val.keys())[0]
                _col = _val[_op]
                if type(_col) == str and _col.startswith('$'):
                    # 是字段
                    _col = _col[1:]
                    if _col not in _fixed_cols:
                        # 非固定字段
                        _path_cols = _col.split('.')
                        if len(_path_cols) > 1 and _path_cols[0] in _fixed_cols:
                            _col_name = _path_cols[0]
                            _path = self._convert_path_array(_path_cols[1:])
                        else:
                            _col_name = 'nosql_driver_extend_tags'
                            _path = self._convert_path_array(_path_cols)

                        _col = "`%s`->'$.%s'" % (_col_name, _path)
                    else:
                        _col = "`%s`" % _col

                    _select.append('%s(%s) as `%s`' % (_op_mapping[_op], _col, _key))
                else:
                    # 是值
                    _select.append('%s(%s) as `%s`' % (_op_mapping[_op], '%s', _key))
                    sql_paras.append(_col)
            elif _val_type == str and _val.startswith('$'):
                # 是字段
                _col = _val[1:]
                if _col not in _fixed_cols:
                    # 非固定字段
                    _path_cols = _col.split('.')
                    if len(_path_cols) > 1 and _path_cols[0] in _fixed_cols:
                        _col_name = _path_cols[0]
                        _path = self._convert_path_array(_path_cols[1:])
                    else:
                        _col_name = 'nosql_driver_extend_tags'
                        _path = self._convert_path_array(_path_cols)

                    _col = "`%s`->'$.%s'" % (_col_name, _path)
                else:
                    _col = "`%s`" % _col

                _select.append('%s as `%s`' % (_col, _key))
                _groupby.append(_col)
            else:
                # 是固定值
                _select.append('%s as `%s`' % ('%s', _key))
                sql_paras.append(_val)

        return ','.join(_select), ','.join(_groupby)

    def _get_col_default_value(self, val: str, dbtype: str) -> str:
        """
        获取字段的默认值

        @param {str} val - 字符串形式的值
        @param {str} dbtype - 数据类型

        @returns {str} - 返回默认值的字符串
        """
        if dbtype in ('int', 'float'):
            return str(val)
        elif dbtype == 'bool':
            return '1' if str(val).lower() == 'true' else '0'
        elif dbtype == 'json':
            if type(val) != str:
                return "'%s'" % self._db_quotes_str(json.dumps(val, ensure_ascii=False))
            else:
                return "'%s'" % self._db_quotes_str(val)
        else:
            return "'%s'" % self._db_quotes_str(str(val))

    def _get_partition_sql(self, partition: dict) -> str:
        """
        生成分区创建sql

        @param {dict} partition - 分区创建配置字典

        @returns {str} - 分区创建sql
        """
        # 复制参数对象
        _partition = copy.deepcopy(partition)

        # 组装sql需要用到的sql关键字字典
        _type_sql_mapping = {
            'range': {
                'name_sql': 'RANGE', 'value_sql': 'VALUES LESS THAN',
                'support_func': True, 'support_range': True, 'is_columns': False
            },
            'range_columns': {
                'name_sql': 'RANGE COLUMNS', 'value_sql': 'VALUES LESS THAN',
                'support_func': False, 'support_range': True, 'is_columns': True
            },
            'list': {
                'name_sql': 'LIST', 'value_sql': 'VALUES IN',
                'support_func': True, 'support_range': True, 'is_columns': False
            },
            'list_columns': {
                'name_sql': 'LIST COLUMNS', 'value_sql': 'VALUES IN',
                'support_func': False, 'support_range': True, 'is_columns': False
            },
            'hash': {
                'name_sql': 'HASH',
                'support_func': True, 'support_range': False, 'is_columns': False
            },
            'linear_hash': {
                'name_sql': 'LINEAR HASH',
                'support_func': True, 'support_range': False, 'is_columns': False
            },
            'key': {
                'name_sql': 'KEY',
                'support_func': False, 'support_range': False, 'is_columns': True
            },
            'linear_key': {
                'name_sql': 'LINEAR KEY',
                'support_func': False, 'support_range': False, 'is_columns': True
            }
        }

        _type_sql_para = _type_sql_mapping[_partition['type']]

        # 非多列模式的分区条件清单只取第一个参数
        if _type_sql_para['is_columns']:
            _columns = _partition['columns']
        else:
            # 只支持单字段
            _columns = _partition['columns'][0: 1]

        _cols = []  # 分区字段清单
        _partition_configs = []  # 分区定义清单
        for _index in range(len(_columns)):
            _column = _columns[_index]

            # 分区字段清单处理
            if not _type_sql_para['support_func'] or _column.get('func', '') == '':
                # 不支持函数的情况
                _cols.append('`%s`' % _column['col_name'])
            else:
                _cols.append(_column['func'].format(col_name='`%s`' % _column['col_name']))

            if not _type_sql_para['support_range']:
                # 不支持分区条件的情况, 跳过分区清单
                continue

            for _range_index in range(len(_column['range_list'])):
                _range = _column['range_list'][_range_index]
                if _index == 0:
                    # 第一个字段
                    _partition_name = ('p%d' % _range_index) if _range.get('name', None) is None else _range['name']
                    _partition_configs.append({
                        'name': _partition_name, 'values': [_range['value']]
                    })
                else:
                    # 非第一个字段, 添加到对应分区的values数组即可
                    _partition_configs[_range_index]['values'].append(_range['value'])

        # 组装sql
        if not _type_sql_para['support_range']:
            # 不支持分区条件清单, 直接按分区数量处理
            _partition_sql = 'PARTITION BY %s (%s) PARTITIONS %d' % (
                _type_sql_para['name_sql'], ','.join(_cols), _partition['count']
            )
            return _partition_sql

        # 支持分区条件清单的情况
        _partition_sql = 'PARTITION BY %s (%s)' % (_type_sql_para['name_sql'], ','.join(_cols))
        _partition_value_sqls = []  # 分区值sql数组
        for _partition_config in _partition_configs:
            # 处理值清单, 将其修改为对应的sql字符串
            if _partition['type'] in ('list', 'list_columns'):
                # 列表形式, 只需处理第一个值
                _deal_value = _partition_config['values'][0]
                for _index in range(len(_deal_value)):
                    _val = _deal_value[_index]
                    if _val is None:
                        _deal_value[_index] = 'MAXVALUE' if _partition['type'] == 'list' else 'NULL'
                    else:
                        _deal_value[_index] = str(_val)

                _partition_config['values'] = ','.join(_deal_value)
            else:
                # 值形式, 需要每个值处理
                for _index in range(len(_partition_config['values'])):
                    _deal_value = _partition_config['values'][_index]
                    if _deal_value is None:
                        _partition_config['values'][_index] = 'MAXVALUE'
                    else:
                        _partition_config['values'][_index] = str(_deal_value)

                _partition_config['values'] = ','.join(_partition_config['values'])

            _sql = 'PARTITION `%s` %s (%s)' % (
                _partition_config['name'], _type_sql_para['value_sql'], _partition_config['values']
            )
            _partition_value_sqls.append(_sql)

        # 判断是否有子分区
        if _partition.get('sub_partition', None) is None:
            # 没有子分区, 直接组织并返回
            _partition_sql = '%s (%s)' % (
                _partition_sql, ', '.join(_partition_value_sqls)
            )
            return _partition_sql

        # 子分区处理
        _cols = []  # 字段处理清单
        if _partition['sub_partition']['type'] == 'hash':
            _columns = _partition['sub_partition']['columns'][0: 1]
        else:
            _columns = _partition['sub_partition']['columns']

        for _column in _columns:
            if _partition['sub_partition']['type'] == 'key' or _column.get('func', '') == '':
                _cols.append('`%s`' % _column['col_name'])
            else:
                _cols.append(_column['func'].format(col_name='`%s`' % _column['col_name']))

        _partition_sql = '%s SUBPARTITION BY %s (%s)' % (
            _partition_sql, _partition['sub_partition']['type'].upper(), ','.join(_cols)
        )

        if _partition['sub_partition'].get('sub_name', None) is None:
            # 子分区无需定义名字
            _partition_sql = '%s SUBPARTITIONS %d (%s)' % (
                _partition_sql, _partition['sub_partition']['count'], ', '.join(_partition_value_sqls)
            )
        else:
            # 处理子分区的名字
            _sub_name = _partition['sub_partition']['sub_name']
            for _index in range(len(_partition_value_sqls)):
                for _sub_index in range(len(_sub_name[_index])):
                    _sub_name[_index][_sub_index] = 'SUBPARTITION %s' % _sub_name[_index][_sub_index]

                _partition_value_sqls[_index] = '%s (%s)' % (
                    _partition_value_sqls[_index], ', '.join(_sub_name[_index])
                )

            # 组合
            _partition_sql = '%s (%s)' % (_partition_sql, ', '.join(_partition_value_sqls))

        return _partition_sql

    def _get_left_join_sqls(self, db_name: str, collection: str, left_join: list, sql_paras: list = [],
            session=None, fixed_col_define: dict = None) -> list:
        """
        获取左关联的关联表sql清单

        @param {str} db_name - 主表数据库名
        @param {str} collection - 主表名
        @param {list} left_join - 左关联配置
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {Any} session=None - 数据库事务连接对象
        @param {dict} fixed_col_define=None - 主表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }

        @returns {list} - 关联表sql清单
        """
        _sqls = []
        # 遍历生成每个表的关联sql
        for _join_para in left_join:
            _join_db_name = _join_para.get('db_name', db_name)
            _join_tab = _join_para['collection']
            _as_name = _join_para.get('as', _join_tab)

            # 表字段定义
            _fixed_col_define = {'cols': []} if fixed_col_define is None else fixed_col_define
            _join_fixed_col_define = AsyncTools.sync_run_coroutine(self._get_fixed_col_define(
                _join_tab, db_name=_join_db_name, session=session
            ))

            # on语句
            _on_fields = []
            for _on in _join_para['join_fields']:
                if _on[0] != '_id' and _on[0] not in _fixed_col_define['cols']:
                    # 扩展字段
                    _field0 = "`nosql_driver_extend_tags`->'$.%s'" % _on[0]
                else:
                    _field0 = '`%s`' % _on[0]

                if _on[1] != '_id' and _on[1] not in _join_fixed_col_define['cols']:
                    # 扩展字段
                    _field1 = "`nosql_driver_extend_tags`->'$.%s'" % _on[1]
                else:
                    _field1 = '`%s`' % _on[1]

                _on_fields.append('`%s`.%s = `%s`.%s' % (
                    collection, _field0, _as_name, _field1
                ))

            # 根据是否有过滤条件处理
            _filter = _join_para.get('filter', None)
            if _filter is None:
                _sqls.append('`%s`.`%s` `%s` on %s' % (
                    _join_db_name, _join_tab, _as_name, ' and '.join(_on_fields)
                ))
            else:
                # 有过滤条件, 按查询表的方式关联
                _filter_sql = self._get_filter_sql(
                    _filter, fixed_col_define=_join_fixed_col_define, sql_paras=sql_paras
                )
                _sqls.append('(select * from `%s`.`%s` where %s) `%s` on %s' % (
                    _join_db_name, _join_tab, _filter_sql, _as_name, ' and '.join(_on_fields)
                ))

        return _sqls

    #############################
    # 生成SQL转换的处理函数
    #############################
    def _sqls_fun_not_support(self, op: str, *args, **kwargs):
        """
        驱动不支持的情况
        """
        raise aiomysql.NotSupportedError('aiomysql not support this operation')

    def _sqls_fun_create_db(self, op: str, *args, **kwargs) -> tuple:
        """
        生成添加数据库的sql语句数组
        """
        # 获取参数
        _name = args[0]  # 数据库名
        _char_acter = args[1] if len(args) > 1 else kwargs.get('char_acter', None)  # 字符集, 例如utf8
        _collate = args[2] if len(args) > 2 else kwargs.get('collate', None)  # 校对规则, 例如utf8_chinese_ci

        # 组成sql
        _sql = "CREATE DATABASE if not exists `%s`" % _name
        if _char_acter is not None:
            _sql = '%s DEFAULT CHARACTER SET %s' % (_sql, _char_acter)
        if _collate is not None:
            _sql = "%s DEFAULT COLLATE %s" % (_sql, _collate)

        return ([_sql], None, {})

    def _sqls_fun_list_dbs(self, op: str, *args, **kwargs) -> tuple:
        """
        生成获取数据库清单的sql语句数组
        """
        _sql = "SHOW DATABASES"
        return ([_sql], None, {'is_query': True})

    def _sqls_fun_drop_db(self, op: str, *args, **kwargs) -> tuple:
        """
        生成分离数据库的sql语句数组
        """
        _name = args[0]  # 数据库名
        _sql = "DROP DATABASE `%s`" % _name

        return ([_sql], None, {})

    def _sqls_fun_create_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成建表的sql语句数组
        """
        _db_prefix = '`%s`.' % self._db_name
        _collection = args[0]
        _sqls = []
        _checks = []  # 语句检查数组

        # 生成表字段清单
        _cols = []
        if kwargs.get('fixed_col_define', None) is not None:
            for _col_name, _col_def in kwargs['fixed_col_define'].items():
                _cols.append(
                    '`%s` %s%s%s%s' % (
                        _col_name, self._dbtype_mapping(_col_def['type'], _col_def.get('len', None)),
                        '' if _col_def.get('nullable', True) else ' not null',
                        '' if _col_def.get('default', None) is None or _col_def['type'] == 'json' else ' default %s' % self._get_col_default_value(
                            _col_def['default'], _col_def['type']
                        ),
                        '' if _col_def.get('comment', None) is None else " comment '%s'" % self._db_quotes_str(_col_def['comment'])
                    )
                )

        # 主键清单(如果存在分区的情况, 分区字段必须为主键)
        _primary_keys = ['`_id`']

        # 生成分区sql
        _partition_sql = None
        _partition_cols = []  # 放入分区条件的字段列表
        if kwargs.get('partition', None) is not None:
            _partition_sql = self._get_partition_sql(kwargs['partition'])
            # 分区字段要添加为主键
            for _column in kwargs['partition']['columns']:
                _partition_cols.append(_column['col_name'])

            for _column in kwargs['partition'].get('sub_partition', {}).get('columns', []):
                _partition_cols.append(_column['col_name'])

            for _col in _partition_cols:
                _col_name = '`%s`' % _col
                if _col_name not in _primary_keys:
                    _primary_keys.append(_col_name)

        # 建表脚本, 需要带上数据库前缀
        _sql = 'create table if not exists %s`%s`(`_id` varchar(100), %s `nosql_driver_extend_tags` json, %s)%s%s' % (
            _db_prefix, _collection, (', '.join(_cols) + ',') if len(_cols) > 0 else '',
            'primary key(%s)' % ','.join(_primary_keys),  # 设置主键
            '' if kwargs.get('comment', None) is None else " comment='%s'" % self._db_quotes_str(kwargs['comment']),  # 表注释
            '' if _partition_sql is None else _partition_sql  # 分区语句
        )
        _sqls.append(_sql)
        _checks.append(None)

        # 如果_id不是唯一主键, 需要设置为唯一索引
        if len(_primary_keys) > 1:
            _sql = 'create %sindex `idx_%s_%s__id` on %s`%s`(`_id`)' % (
                'UNIQUE ' if '_id' in _partition_cols else '',
                self._db_name, _collection, _db_prefix, _collection
            )
            _sqls.append(_sql)
            if self._ignore_index_error:
                _checks.append({'after_check': {'ignore_current_error': True}})  # 忽略语句执行失败
            else:
                _checks.append(None)

        # 建索引脚本
        _support_desc_index = self._driver_config.get('support_desc_index', False)
        if kwargs.get('indexs', None) is not None:
            for _index_name, _index_def in kwargs['indexs'].items():
                _support_unique = True
                _cols = []
                for _col_name, _para in _index_def['keys'].items():
                    if _col_name not in _partition_cols:
                        # 索引中存在非分区条件的字段, 则不支持唯一索引
                        _support_unique = False

                    if _support_desc_index and _para.get('asc', 1) == -1:
                        # 降序索引
                        _cols.append('`%s` desc' % _col_name)
                    else:
                        _cols.append('`%s`' % _col_name)

                _sql = 'create %sindex `%s` on %s`%s`(%s)' % (
                    'UNIQUE ' if _index_def.get('paras', {}).get('unique', False) and _support_unique else '',
                    _index_name, _db_prefix, _collection, ','.join(_cols)
                )
                _sqls.append(_sql)
                if self._ignore_index_error:
                    _checks.append({'after_check': {'ignore_current_error': True}})  # 忽略语句执行失败
                else:
                    _checks.append(None)

        # 返回结果
        return (_sqls, None, {}, _checks)

    def _sql_fun_list_collections(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询表清单的sql语句数组
        """
        _filter = kwargs.get('filter', None)
        # 生成where语句
        _sql_paras = []
        _where = self._get_filter_sql(_filter, sql_paras=_sql_paras)

        _sql = "select `name` from (select table_name as `name` from information_schema.tables where table_schema='%s' and table_type='BASE TABLE') t%s order by `name`" % (
            self._db_name, '' if _where is None else ' where %s' % _where
        )

        # 返回结果
        return ([_sql], None if len(_sql_paras) == 0 else [_sql_paras], {'is_query': True})

    def _sql_fun_drop_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成删除表的sql语句数组
        """
        _collection = '`%s`.`%s`' % (
            self._db_name, args[0]
        )
        _sql = "drop table %s" % _collection
        return ([_sql], None, {})

    def _sql_fun_turncate_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成清空表的sql语句数组
        """
        _collection = args[0]
        _sqls = []
        _sqls.append(
            "truncate table `%s`.`%s`" % (self._db_name, _collection)
        )

        return (_sqls, None, {})

    def _sql_fun_insert_one(self, op: str, *args, **kwargs) -> tuple:
        """
        生成插入数据的sql语句数组
        """
        _collection = '`%s`.`%s`' % (self._db_name, args[0])
        _row = args[1]
        _fixed_col_define = args[2] if len(args) > 2 else kwargs.get('fixed_col_define', {})

        # 生成插入字段和值
        _cols = ['`_id`']
        _sql_paras = [_row.pop('_id')]
        for _col in _fixed_col_define.get('cols', []):
            _val = _row.pop(_col, None)
            if _val is not None:
                _cols.append('`%s`' % _col)
                _sql_paras.append(self._python_to_dbtype(_val)[1])

        # 剩余的内容放入扩展字段
        _cols.append('`nosql_driver_extend_tags`')
        _sql_paras.append(self._python_to_dbtype(_row, dbtype='json')[1])

        # 组成sql
        _sql = 'insert into %s(%s) values(%s)' % (
            _collection, ','.join(_cols), ','.join(['%s' for _tcol in _cols])
        )

        return ([_sql], [_sql_paras], {})

    def _sql_fun_insert_many(self, op: str, *args, **kwargs) -> tuple:
        """
        生成插入数据的sql语句数组
        """
        _collection = '`%s`.`%s`' % (self._db_name, args[0])
        _rows = args[1]
        _fixed_col_define = args[2] if len(args) > 2 else kwargs.get('fixed_col_define', {})

        # 生成插入字段列表
        _cols = ['`_id`']
        for _col in _fixed_col_define.get('cols', []):
            if _col == '_id':
                continue

            _cols.append('`%s`' % _col)

        _cols.append('`nosql_driver_extend_tags`')

        # 遍历生成插入数据和参数
        _para_array = []
        _value_array = []
        for _s_row in _rows:
            _row = copy.copy(_s_row)  # 浅复制即可
            _sql_paras = [_row.pop('_id', str(ObjectId()))]
            _col_values = ['%s']
            for _col in _fixed_col_define.get('cols', []):
                if _col == '_id':
                    continue

                _val = _row.pop(_col, None)
                if _val is None:
                    _col_values.append('null')
                else:
                    _col_values.append('%s')
                    _sql_paras.append(self._python_to_dbtype(_val)[1])

            # 剩余的内容放入扩展字段
            _col_values.append('%s')
            _sql_paras.append(self._python_to_dbtype(_row, dbtype='json')[1])

            # 添加到数组
            _para_array.extend(_sql_paras)
            _value_array.append('(%s)' % ','.join(_col_values))

        # 生成插入sql
        _sql = 'insert into %s(%s) values %s' % (
            _collection, ','.join(_cols), ','.join(_value_array)
        )

        return ([_sql], [_para_array], {})

    def _sql_fun_update(self, op: str, *args, **kwargs) -> tuple:
        """
        生成更新数据的sql语句数组
        """
        # 获取参数
        _collection = args[0]
        _filter = args[1]
        _update = args[2]
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _partition = kwargs.get('partition', None)  # 指定分区表
        if type(_partition) == str:
            _partition = [_partition]

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras
        )

        # 处理更新配置语句
        _update_sql_paras = []
        _update_sql = self._get_update_sql(
            _update, fixed_col_define=_fixed_col_define, sql_paras=_update_sql_paras
        )

        _sql_collection = '`%s`.`%s`%s' % (
            self._db_name, _collection, '' if _partition is None else ' partition(`%s`)' % '`.`'.join(_partition)
        )
        _sql = 'update %s set %s' % (_sql_collection, _update_sql)
        if _where_sql is not None:
            _sql = '%s where %s' % (_sql, _where_sql)
            _update_sql_paras.extend(_where_sql_paras)

        # 返回语句
        return ([_sql], [_update_sql_paras], {})

    def _sql_fun_delete(self, op: str, *args, **kwargs) -> tuple:
        """
        生成删除数据的sql语句数组
        """
        # 获取参数
        _collection = args[0]
        _filter = args[1]
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _partition = kwargs.get('partition', None)  # 指定分区表
        if type(_partition) == str:
            _partition = [_partition]

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras
        )

        _sql_paras = None
        _sql_collection = '`%s`.`%s`%s' % (
            self._db_name, _collection, '' if _partition is None else ' partition(`%s`)' % '`.`'.join(_partition)
        )
        _sql = 'delete from %s' % _sql_collection
        if _where_sql is not None:
            _sql = '%s where %s' % (_sql, _where_sql)
            _sql_paras = _where_sql_paras

        # 返回语句
        return ([_sql], [_sql_paras], {})

    def _sql_fun_query(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询数据的sql语句数组
        """
        # 获取参数
        _collection = args[0]
        _filter = kwargs.get('filter', {})
        _projection = kwargs.get('projection', None)
        _sort = kwargs.get('sort', None)
        _skip = kwargs.get('skip', None)
        _limit = kwargs.get('limit', None)
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _left_join = kwargs.get('left_join', None)  # 关联查询
        _session = kwargs.get('session', None)  # 数据库操作的session
        _partition = kwargs.get('partition', None)  # 指定分区表
        if type(_partition) == str:
            _partition = [_partition]

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            left_join=_left_join, session=_session
        )

        # 处理sort语句
        _sort_sql_paras = []
        _sort_sql = None
        if _sort is not None:
            _sort_sql = self._get_sort_sql(
                _sort, fixed_col_define=_fixed_col_define, sql_paras=_sort_sql_paras,
                left_join=_left_join, session=_session
            )

        # 处理projection语句
        _projection_sql_paras = []
        _projection_sql = self._get_projection_sql(
            _projection, fixed_col_define=_fixed_col_define, sql_paras=_projection_sql_paras,
            as_name=None if _left_join is None else _collection, left_join=_left_join, session=_session
        )

        # 查询表
        _tab = '`%s`.`%s`%s' % (
            self._db_name, _collection, '' if _partition is None else ' partition(`%s`)' % '`.`'.join(_partition)
        )

        # 处理关联表
        _left_join_sql_paras = []
        if _left_join is not None:
            _left_join_sqls = self._get_left_join_sqls(
                self._db_name, _collection, _left_join, sql_paras=_left_join_sql_paras,
                session=_session, fixed_col_define=_fixed_col_define
            )
            for _join_sql in _left_join_sqls:
                _tab = '%s left outer join %s' % (_tab, _join_sql)

        # 组装语句
        _sql_paras = []
        _sql = 'select %s from %s' % (_projection_sql, _tab)
        _sql_paras.extend(_projection_sql_paras)
        _sql_paras.extend(_left_join_sql_paras)

        if _where_sql is not None:
            _sql = '%s where %s' % (_sql, _where_sql)
            _sql_paras.extend(_where_sql_paras)

        if _sort_sql is not None:
            _sql = '%s order by %s' % (_sql, _sort_sql)
            _sql_paras.extend(_sort_sql_paras)

        # 增加skip和limit
        if _limit is not None:
            if _skip is not None:
                _sql = '%s %s' % (_sql, 'limit %d offset %d' % (_limit, _skip))
            else:
                _sql = '%s %s' % (_sql, 'limit %d' % _limit)
        else:
            if _skip is not None:
                _sql = '%s %s' % (_sql, 'limit 18446744073709551615 offset %d' % _skip)

        # 返回最终结果
        return ([_sql], [_sql_paras], {'is_query': True})

    def _sql_fun_query_count(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询数据count的sql语句数组
        """
        # 获取参数
        _collection = args[0]
        _filter = kwargs.get('filter', {})
        _skip = kwargs.get('skip', None)
        _limit = kwargs.get('limit', None)
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _left_join = kwargs.get('left_join', None)  # 关联查询
        _session = kwargs.get('session', None)  # 数据库操作的session
        _partition = kwargs.get('partition', None)  # 指定分区表
        if type(_partition) == str:
            _partition = [_partition]

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            left_join=_left_join, session=_session
        )

        # 查询表名
        _tab = '`%s`.`%s`%s' % (
            self._db_name, _collection, '' if _partition is None else ' partition(`%s`)' % '`.`'.join(_partition)
        )

        # 处理关联表
        _left_join_sql_paras = []
        if _left_join is not None:
            _left_join_sqls = self._get_left_join_sqls(
                self._db_name, _collection, _left_join, sql_paras=_left_join_sql_paras,
                session=_session, fixed_col_define=_fixed_col_define
            )
            for _join_sql in _left_join_sqls:
                _tab = '%s left outer join %s' % (_tab, _join_sql)

        # 组装语句
        if _limit is not None or _skip is not None:
            # 有获取数据区间, 只能采用性能差的子查询模式
            _sql_paras = []
            _sql = 'select 1 from %s' % _tab
            _sql_paras.extend(_left_join_sql_paras)
            if _where_sql is not None:
                _sql = '%s where %s' % (_sql, _where_sql)
                _sql_paras.extend(_where_sql_paras)

            # 增加skip和limit
            if _limit is not None:
                if _skip is not None:
                    _sql = '%s %s' % (_sql, 'limit %d offset %d' % (_limit, _skip))
                else:
                    _sql = '%s %s' % (_sql, 'limit %d' % _limit)
            else:
                if _skip is not None:
                    _sql = '%s %s' % (_sql, 'limit 18446744073709551615 offset %d' % _skip)

            # 外面封装一层查询
            _sql = 'select count(*) from (%s) t' % _sql
        else:
            _sql_paras = []
            _sql = 'select count(*) from %s' % _tab
            _sql_paras.extend(_left_join_sql_paras)

            if _where_sql is not None:
                _sql = '%s where %s' % (_sql, _where_sql)
                _sql_paras.extend(_where_sql_paras)

        # 返回最终结果
        return ([_sql], [_sql_paras], {'is_query': True})

    def _sql_fun_query_group_by(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询数据聚合的sql语句数组
        """
        # 获取参数
        _collection = args[0]
        _group = kwargs.get('group', None)
        _filter = kwargs.get('filter', {})
        _projection = kwargs.get('projection', None)
        _sort = kwargs.get('sort', None)
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _partition = kwargs.get('partition', None)  # 指定分区表
        if type(_partition) == str:
            _partition = [_partition]

        # 处理group by语句
        _select_sql_paras = []
        _select_sql, _group_by_sql = self._get_group_sql(
            _group, fixed_col_define=_fixed_col_define, sql_paras=_select_sql_paras
        )

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras
        )

        # 处理sort语句
        _sort_sql_paras = []
        _sort_sql = None
        if _sort is not None:
            _sort_sql = self._get_sort_sql(
                _sort, fixed_col_define=None, sql_paras=_sort_sql_paras
            )

        # 处理projection语句
        _projection_sql_paras = []
        _projection_sql = self._get_projection_sql(
            _projection, fixed_col_define=None, sql_paras=_projection_sql_paras,
            is_group_by=True
        )

        # 查询表名
        _tab = '`%s`.`%s`%s' % (
            self._db_name, _collection, '' if _partition is None else ' partition(`%s`)' % '`.`'.join(_partition)
        )

        # 组装查询语句
        _sql_paras = []
        _sql = 'select %s from %s' % (
            _select_sql, _tab
        )
        _sql_paras.extend(_select_sql_paras)

        if _where_sql is not None:
            _sql = '%s where %s' % (_sql, _where_sql)
            _sql_paras.extend(_where_sql_paras)

        _sql = '%s group by %s' % (_sql, _group_by_sql)

        if _sort_sql is not None:
            # 有排序, 需要包装多一层
            _sql = 'select %s from (%s) t' % (_projection_sql, _sql)
            _sql = '%s order by %s' % (_sql, _sort_sql)

        # 返回结果
        return ([_sql], None if len(_sql_paras) == 0 else [_sql_paras], {'is_query': True})

    #############################
    # 其他内部函数
    #############################
    def _convert_path_array(self, path_list: list) -> str:
        """
        将json查询路径数组转换为sqlite支持的json查询路径字符串

        @param {list} path_list - 路径数组

        @returns {str} - 转换后的查询路径字符串
        """
        _path = ''
        for _key in path_list:
            if ValidateTool.str_is_int(_key):
                # 是字符串
                _path = '%s[%s]' % (_path, _key)
            else:
                _path = '%s%s' % ('' if _path == '' else '%s.' % _path, _key)

        return _path
