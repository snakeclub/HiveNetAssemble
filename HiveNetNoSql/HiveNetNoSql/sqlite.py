#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
sqlite的HiveNetNoSql实现模块

@module sqlite
@file sqlite.py
"""
import os
import sys
import copy
import re
from typing import Any, Union
import sqlite3
import json
from bson.objectid import ObjectId
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.string_tool import StringTool
from HiveNetCore.utils.validate_tool import ValidateTool
from HiveNetCore.connection_pool import PoolConnectionFW
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
try:
    import aiosqlite
except ImportError:
    PythonEnvTools.install_package('aiosqlite')
    import aiosqlite
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetNoSql.base.driver_fw import NosqlAIOPoolDriver


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


class SQLiteNosqlDriver(NosqlAIOPoolDriver):
    """
    nosql数据库SQLite驱动
    """

    #############################
    # 构造函数重载, 主要是注释
    #############################
    def __init__(self, connect_config: dict = {}, pool_config: dict = {}, driver_config: dict = {}):
        """
        初始化驱动

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 数据库文件路径, 或使用":memory:"在内存上创建数据库
            port {int} - 连接数据库的端口(SQLite无效)
            usedb {str} - 登录后默认切换到的数据库(SQLite无效)
            username {str} - 登录验证用户(SQLite无效)
            password {str} - 登录验证密码(SQLite无效)
            dbname {str} - 登录用户的数据库名(SQLite无效)
            connect_on_init {bool} - 是否启动时直接连接数据库
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            default_str_len {int} - 默认的字符串类型长度, 默认为30
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
            sqlite3.connect 支持的其他参数...
            check_same_thread: 是否控制检查与创建连接的是一个线程
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
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}
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
        """
        # 记录数据库所在路径, 创建无文件参数的数据库时默认使用该路径
        _host = connect_config.get('host', ':memory:')
        if _host == ':memory:':
            self._db_path = os.getcwd()
        else:
            self._db_path = os.path.dirname(_host)

        # 登记当前已经加载的数据库
        self._init_dbs = ['main']

        super().__init__(
            connect_config=connect_config, pool_config=pool_config, driver_config=driver_config
        )

        # 指定使用独立的insert_many语句, 性能更高
        self._use_insert_many_generate_sqls = True

    #############################
    # 需要继承类实现的内部函数
    #############################
    def _get_db_creator(self, connect_config: dict, pool_config: dict, driver_config: dict) -> tuple:
        """
        获取数据库连接驱动及参数

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 数据库文件路径, 或使用":memory:"在内存上创建数据库
            port {int} - 连接数据库的端口(SQLite无效)
            usedb {str} - 登录后默认切换到的数据库(SQLite无效)
            username {str} - 登录验证用户(SQLite无效)
            password {str} - 登录验证密码(SQLite无效)
            dbname {str} - 登录用户的数据库名(SQLite无效)
            connect_on_init {bool} - 是否启动时直接连接数据库
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
            sqlite3.connect 支持的其他参数...
            check_same_thread: 是否控制检查与创建连接的是一个线程
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
        # 需要sqlite 3.9.0 以上的版本支持
        if (StringTool.version_cmp(sqlite3.sqlite_version, '3.9.0') == '<'):
            raise aiosqlite.NotSupportedError('only support sqlite 3.9.0 or higher version')

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

        # 生成SQLite的连接配置
        _args = [connect_config['host']]
        _kwargs = {}
        if connect_config.get('connect_timeout', None) is not None:
            _kwargs['timeout'] = connect_config['connect_timeout']

        # 移除不使用的参数
        _connect_config = copy.deepcopy(connect_config)
        for _pop_item in ('host', 'port', 'usedb', 'dbname', 'username', 'password', 'connect_on_init', 'connect_timeout', 'transaction_share_cursor'):
            _connect_config.pop(_pop_item, None)
        # 合并参数
        _kwargs.update(_connect_config)

        return {
            'creator': aiosqlite, 'pool_connection_class': SQLitePoolConnection,
            'args': _args, 'kwargs': _kwargs, 'connect_method_name': 'connect',
            'pool_update_config': {
                # sqlite的限制: 不支持多线程, 连接池设置最大为1; 不检查空闲连接有效性, 也不释放连接
                'max_size': 1,
                'ping_on_idle': False,
                'free_idle_time': 0,
                'pool_extend_paras': {
                    'close_action': driver_config.get('close_action', None)
                }
            },
            'current_db_name': 'main'
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
            raise aiosqlite.NotSupportedError('driver not support this operation')

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
        # 注入正则表达式的支持函数
        AsyncTools.sync_run_coroutine(conn.create_function("REGEXP", 2, self._regexp))

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
        _db_prefix = '' if _db_name == 'main' else ('%s.' % _db_name)
        _sql = "PRAGMA %stable_info('%s')" % (_db_prefix, collection)
        _ret = await self._execute_sql(
            _sql, paras=None, is_query=True, conn=_conn, cursor=_cursor
        )

        # 处理标准类型
        for _row in _ret:
            if _row['type'] == 'JSON':
                _row['type'] = 'json'
            if _row['type'] == 'text':
                _row['type'] = 'str'
            elif _row['type'].startswith('varchar('):
                _row['type'] = 'str'

        return _ret

    #############################
    # 需要单独重载的函数
    #############################
    async def switch_db(self, name: str, *args, **kwargs):
        """
        切换当前数据库到指定数据库

        @param {str} name - 数据库名
        """
        if name in self._init_dbs:
            self._db_name = name
        else:
            await self.create_db(name)

    async def create_db(self, name: str, *args, **kwargs):
        """
        创建数据库
        注: 创建后会自动切换到该数据库

        @param {str} name - 数据库名
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('create_db', name, *args, **kwargs)
        )
        await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )

        # 登记已加载的数据库
        self._init_dbs.append(name)

        # 切换数据库
        await self.switch_db(name)

    async def drop_db(self, name: str, *args, **kwargs):
        """
        删除数据库

        @param {str} name - 数据库名
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('drop_db', name)
        )
        await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )

        # 从清单中删除
        self._init_dbs.pop(self._init_dbs.index(name))

        # 切换后判断是不是删除当前数据库
        if self._db_name == name:
            _dbs = await self.list_dbs()
            if len(_dbs) > 0:
                await self.switch_db(_dbs[0])

    #############################
    # sqlite3支持正则表达式的处理
    #############################

    def _regexp(self, expr, item):
        """
        正则表达式的函数

        @param {str} expr - 表达式文本
        @param {str} item - 匹配对象

        @returns {Any} - 返回匹配结果
        """
        reg = re.compile(expr)
        return reg.search(item) is not None

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
            return 'JSON'
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
        return re.sub(r"\'", "''", val)

    def _get_filter_unit_sql(self, key: str, val: Any, fixed_col_define: dict = None,
            sql_paras: list = [], json_query_cols_dict: dict = {},
            left_join: list = None, session=None, as_name: str = None, unuse_as_name: bool = False) -> str:
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
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典
            字典的key为别名, value为该别名下的配置字典, 字典的格式如下:
            key为查询名(json_query_别名_字段名_字段路径.value), value为配置字典{'col': 物理字段名, 'path': '真实查询路径', 'as': '字段别名'}
            注1: 真实查询路径 'key1.key2[10].key3' 对应的字段路径为 'key1_key2_10_key3'
            注2: nosql_driver_extend_tags字段名不填入查询名中
        @param {list} left_join=None - 左关联配置
        @param {Any} session=None - 数据库事务连接对象
        @param {str} as_name=None - 指定主表的别名
        @param {bool} unuse_as_name=False - 指定不使用as_name

        @returns {str} - 单个规则对应的sql
        """
        # 根据字段判断是主表还是关联表
        _key = key
        _fixed_cols = None
        if _key[0] != '#':
            # 主表的过滤条件
            _as_name = '_main_table' if as_name is None else as_name
            _col_as_name = '' if unuse_as_name else '%s.' % _as_name
            if fixed_col_define is not None:
                _fixed_cols = copy.deepcopy(fixed_col_define.get('cols', []))
        else:
            # 关联表的过滤条件
            _index = _key.find('.')
            _join_para = left_join[int(_key[1: _index])]
            _key = _key[_index+1:]

            _join_db_name = _join_para.get('db_name', self._db_name)
            _join_tab = _join_para['collection']
            _as_name = '%s' % _join_para.get('as', _join_tab)
            _col_as_name = '%s.' % _as_name

            _fixed_col_define = AsyncTools.sync_run_coroutine(self._get_fixed_col_define(
                _join_tab, db_name=_join_db_name, session=session
            ))
            if _fixed_col_define is not None:
                _fixed_cols = copy.deepcopy(_fixed_col_define.get('cols', []))

        # 判断是否处理json的值, 形成最后比较的 key 值
        _is_json = False
        if _fixed_cols is not None:
            _fixed_cols.append('_id')
            if _key not in _fixed_cols:
                # 非固定字段或json字段的处理
                _is_json = True
                if _as_name in ('_main_table', '_inner_temp_as_name'):
                    _key = self._add_to_json_query_cols(
                        _key, json_query_cols_dict=json_query_cols_dict, fixed_cols=_fixed_cols,
                        as_name=_as_name, unuse_as_name=(_col_as_name == '')
                    )
                    _key = '%s.value' % json_query_cols_dict[_as_name][_key]['as']
                else:
                    # 关联表不使用json_tree形式
                    _key = self._get_json_extract_sql(
                        _key, fixed_cols=_fixed_cols, as_name=_as_name, unuse_as_name=(_col_as_name == '')
                    )

        if isinstance(val, dict):
            # 有特殊规则
            _cds = []  # 每个规则的数组
            for _op, _para in val.items():
                if _op in self._filter_symbol_mapping.keys():
                    # 比较值转换为数据库的格式
                    _dbtype, _cmp_val = self._python_to_dbtype(_para)
                    _cds.append('%s %s ?' % (
                        _key if _is_json else '%s%s' % (_col_as_name, _key), self._filter_symbol_mapping[_op]
                    ))
                    sql_paras.append(_cmp_val)
                elif _op in ('$in', '$nin'):
                    # in 和 not in
                    _cds.append('%s %s (%s)' % (
                        _key if _is_json else '%s%s' % (_col_as_name, _key), 'in' if _op == '$in' else 'not in',
                        ','.join(['?' for _item in _para])
                    ))
                    for _item in _para:
                        _dbtype, _cmp_val = self._python_to_dbtype(_item)
                        sql_paras.append(_cmp_val)
                elif _op == '$regex':
                    _cds.append("%s REGEXP ?" % (_key if _is_json else '%s%s' % (_col_as_name, _key)))
                    sql_paras.append(_para)
                else:
                    raise aiosqlite.NotSupportedError('sqlite3 not support this search operation [%s]' % _op)
            _sql = ' and '.join(_cds)
        else:
            # 直接相等的条件
            if val is None:
                _sql = '%s is NULL' % (_key if _is_json else '%s%s' % (_col_as_name, _key))
            else:
                _dbtype, _cmp_val = self._python_to_dbtype(val)
                _sql = '%s = ?' % (_key if _is_json else '%s%s' % (_col_as_name, _key))
                sql_paras.append(_cmp_val)

        return _sql

    def _get_filter_sql(self, filter: dict, fixed_col_define: dict = None,
            sql_paras: list = [], json_query_cols_dict: dict = {},
            left_join: list = None, session=None, as_name: str = None,
            unuse_as_name: bool = False) -> str:
        """
        获取兼容mongodb过滤条件规则的sql语句

        @param {dict} filter - 过滤规则字典
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典
        @param {list} left_join=None - 左关联配置
        @param {Any} session=None - 数据库事务连接对象
        @param {str} as_name=None - 指定主表的别名
        @param {bool} unuse_as_name=False - 指定不使用as_name

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
                        json_query_cols_dict=json_query_cols_dict, left_join=left_join,
                        session=session, as_name=as_name, unuse_as_name=unuse_as_name
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
                    json_query_cols_dict=json_query_cols_dict, left_join=left_join,
                    session=session, as_name=as_name, unuse_as_name=unuse_as_name
                )
                # 添加条件
                _condition_list.append(_where)

        # 组合条件并返回
        return ' and '.join(_condition_list)

    def _get_update_sql(self, update: dict, fixed_col_define: dict = None,
            sql_paras: list = [], json_query_cols_dict: dict = {}) -> str:
        """
        获取兼容mongodb更新语句的sql语句

        @param {dict} update - 更新配置字典
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典

        @returns {str} - 返回更新部分语句sql
        """
        # 更新辅助字典, key为要更新的字段名, value为{'sql': '对应的sql语句, 比如?', 'paras': [传入sql的参数列表]}
        _upd_dict = {}

        # 扩展字段字典, key要更新的扩展字段名, value为字典: {'sql': None, 'paras': []}
        _extend_dict = {}

        # 遍历处理
        for _op, _para in update.items():
            for _key, _val in _para.items():
                if fixed_col_define is None or _key == '_id' or _key in fixed_col_define.get('cols', []):
                    # 是固定字段
                    if _op == '$set':
                        _upd_dict[_key] = {'sql': '?', 'paras': [self._python_to_dbtype(_val)[1]]}
                    elif _op == '$unset':
                        _upd_dict[_key] = {'sql': 'NULL', 'paras': []}
                    elif _op == '$inc':
                        _upd_dict[_key] = {'sql': 'ifnull(%s,0) + ?' % _key, 'paras': [_val]}
                    elif _op == '$mul':
                        _upd_dict[_key] = {'sql': 'ifnull(%s,0) * ?' % _key, 'paras': [_val]}
                    elif _op == '$min':
                        _upd_dict[_key] = {
                            'sql': 'case when ifnull({key}, ?) < ? then ifnull({key},0) else ? end'.format(key=_key),
                            'paras': [_val, _val, _val]
                        }
                    elif _op == '$max':
                        _upd_dict[_key] = {
                            'sql': 'case when ifnull({key}, ?) > ? then ifnull({key},0) else ? end'.format(key=_key),
                            'paras': [_val, _val, _val]
                        }
                    else:
                        raise aiosqlite.NotSupportedError('sqlite3 not support this update operation [%s]' % _op)
                else:
                    # 是扩展字段或json字段
                    _path_cols = _key.split('.')
                    if len(_path_cols) > 1 and _path_cols[0] in fixed_col_define.get('cols', []):
                        # 是固定的json字段
                        _col_name = _path_cols[0]
                        _set_key = self._convert_path_array(_path_cols[1:])
                    else:
                        # 是扩展字段
                        _col_name = 'nosql_driver_extend_tags'
                        _set_key = self._convert_path_array(_path_cols)

                    if _extend_dict.get(_col_name, None) is None:
                        _extend_dict[_col_name] = {'sql': None, 'paras': []}

                    if _op == '$set':
                        _dbtype, _dbval = self._python_to_dbtype(_val, is_json=True)
                        if _dbtype in ('bool', 'json'):
                            _sql = 'json_set({sql}, "$.{key}", json(?))'
                        else:
                            _sql = 'json_set({sql}, "$.{key}", ?)'

                        _extend_dict[_col_name]['paras'].append(_dbval)
                    elif _op == '$unset':
                        _sql = 'json_remove({sql}, "$.{key}")'
                    elif _op in ('$inc', '$mul', '$min', '$max'):
                        _dbtype, _dbval = self._python_to_dbtype(_val, is_json=True)
                        # 需要取值出来, 添加查询字段
                        if _op == '$inc':
                            _sql = 'json_set({sql}, "$.{key}", ifnull(json_extract({col_name}, "$.{key}"), 0) + ?)'
                            _extend_dict[_col_name]['paras'].append(_dbval)
                        elif _op == '$mul':
                            _sql = 'json_set({sql}, "$.{key}", ifnull(json_extract({col_name}, "$.{key}"), 0) * ?)'
                            _extend_dict[_col_name]['paras'].append(_dbval)
                        elif _op == '$min':
                            _sql = 'json_set({sql}, "$.{key}", case when ifnull(json_extract({col_name}, "$.{key}"), ?) < ? then ifnull(json_extract({col_name}, "$.{key}"), 0) else ? end)'
                            _extend_dict[_col_name]['paras'].extend([_dbval, _dbval, _dbval])
                        elif _op == '$max':
                            _sql = 'json_set({sql}, "$.{key}", case when ifnull(json_extract({col_name}, "$.{key}"), ?) > ? then ifnull(json_extract({col_name}, "$.{key}"), 0) else ? end)'
                            _extend_dict[_col_name]['paras'].extend([_dbval, _dbval, _dbval])
                    else:
                        raise aiosqlite.NotSupportedError('sqlite3 not support this update operation [%s]' % _op)

                    # 处理格式化
                    _extend_dict[_col_name]['sql'] = _sql.format(
                        sql=_col_name if _extend_dict[_col_name]['sql'] is None else _extend_dict[_col_name]['sql'],
                        key=_set_key, col_name=_col_name
                    )

        # 开始生成sql语句和返回参数
        _sqls = []
        for _key, _val in _upd_dict.items():
            _sqls.append('%s=%s' % (_key, _val['sql']))
            if _val['paras'] is not None:
                sql_paras.extend(_val['paras'])

        # 处理扩展字段
        for _col_name, _extend_para in _extend_dict.items():
            _sqls.append('%s=%s' % (_col_name, _extend_para['sql']))
            sql_paras.extend(_extend_para['paras'])

        return ','.join(_sqls)

    def _get_projection_sql(self, projection: Union[dict, list], fixed_col_define: dict = None,
            sql_paras: list = [], json_query_cols_dict: dict = {}, is_group_by: bool = False,
            as_name: str = None, unuse_as_name: bool = False,
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
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典
        @param {bool} is_group_by=False - 指定是否group by的处理, 如果是不会处理_id字段
        @param {str} as_name=None - 字段对应的表别名
        @param {bool} unuse_as_name=False - 指定不使用as_name
        @param {list} left_join - 左关联配置
        @param {Any} session=None - 数据库事务连接对象

        @returns {str} - 返回更新部分语句sql
        """
        # 如果不指定, 返回所有字段
        if projection is None:
            _base_as_name = '_main_table' if as_name is None else as_name
            _as_name = '' if unuse_as_name else ('%s.' % _base_as_name)
            _project_sql = '%s*' % _as_name
            if left_join is not None:
                # 补充关联表的所有字段获取
                for _join_para in left_join:
                    _project_sql = '%s, %s.*' % (
                        _project_sql, _join_para.get('as', _join_para['collection'])
                    )

            return _project_sql

        # 定义的内部函数
        def _get_join_col_info(col: str, left_join: list, tab_as_name: str, unuse_as_name: bool) -> tuple:
            # 获取关联表列信息
            if col[0] == '#':
                _index = col.find('.')
                _join_para = left_join[int(col[1: _index])]
                _col = col[_index+1:]
                _join_as_name = _join_para.get('as', _join_para['collection'])
                _join_as_name_sql = '%s.' % _join_as_name
            else:
                _col = col
                _join_as_name = '_main_table' if tab_as_name is None else tab_as_name
                _join_as_name_sql = '' if unuse_as_name else ('%s.' % _join_as_name)

            return _col, _join_as_name, _join_as_name_sql

        # 标准化要显示的字段清单
        _projection = {}
        if isinstance(projection, dict):
            for _key, _show in projection.items():
                if type(_show) == str and _show[0] == '$':
                    _col, _tab_as_name, _tab_as_name_sql = _get_join_col_info(
                        _show[1:], left_join, as_name, unuse_as_name
                    )
                    _projection[_key] = {
                        'col': _col, 'tab_as': _tab_as_name, 'tab_as_sql': _tab_as_name_sql,
                        'col_as': _key
                    }
                elif _show:
                    _col, _tab_as_name, _tab_as_name_sql = _get_join_col_info(
                        _key, left_join, as_name, unuse_as_name
                    )
                    _projection[_key] = {
                        'col': _col, 'tab_as': _tab_as_name, 'tab_as_sql': _tab_as_name_sql
                    }
        else:
            # 列表形式, _id是必须包含的
            if not is_group_by and '_id' not in projection:
                _projection['_id'] = {
                    'col': '_id', 'tab_as': '_main_table' if as_name is None else as_name
                }
                _projection['_id']['tab_as_sql'] = '' if unuse_as_name else ('%s.' % _projection['_id']['tab_as'])

            for _key in projection:
                _col, _tab_as_name, _tab_as_name_sql = _get_join_col_info(
                    _key, left_join, as_name, unuse_as_name
                )
                _projection[_key] = {
                    'col': _col, 'tab_as': _tab_as_name, 'tab_as_sql': _tab_as_name_sql
                }

        # 处理fixed_cols参数
        _fixed_cols_dict = {}
        if fixed_col_define is not None:
            # 主表的列参数
            _tab_as_name = '_main_table' if as_name is None else as_name
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
            _base_as_name = _val['tab_as']
            if _fixed_cols is None or _col in _fixed_cols:
                _real_cols.append(('%s%s' % (_as_name, _col)) if _val.get('col_as', None) is None else '%s%s as %s' % (_as_name, _col, _val['col_as']))
            else:
                if _base_as_name in ('_main_table', '_inner_temp_as_name'):
                    _json_key = self._add_to_json_query_cols(
                        _col, json_query_cols_dict=json_query_cols_dict, fixed_cols=_fixed_cols,
                        as_name=_base_as_name, unuse_as_name=(_as_name == '')
                    )
                    _json_as = json_query_cols_dict[_base_as_name][_json_key]['as']
                    _json_col = json_query_cols_dict[_base_as_name][_json_key]['real_col']
                    _real_cols.append(
                        '%s.value as %s' % (
                            _json_as, _json_col if _val.get('col_as', None) is None else _val['col_as']
                        )
                    )
                else:
                    # 关联表不使用json_tree形式
                    _real_cols.append(
                        '%s as %s' % (
                            self._get_json_extract_sql(
                                _col, fixed_cols=_fixed_cols, as_name=_base_as_name, unuse_as_name=(_as_name == '')
                            ), _col if _val.get('col_as', None) is None else _val['col_as']
                        )
                    )

        # 返回sql
        return ','.join(_real_cols)

    def _get_sort_sql(self, sort: list, fixed_col_define: dict = None,
            sql_paras: list = [], json_query_cols_dict: dict = {},
            left_join: list = None, session=None, unuse_as_name: bool = False) -> str:
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
        @param {dict} json_query_cols={} - 返回sql中json查询所需的json_tree处理的字段字典
        @param {list} left_join=None - 左关联配置
        @param {Any} session=None - 数据库事务连接对象
        @param {bool} unuse_as_name=False - 指定不使用as_name

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
                _as_name = '_main_table'
                _col_as_name = '' if unuse_as_name else ('%s.' % _as_name)
                _fixed_cols = _main_fixed_cols
            else:
                # 属于关联表字段
                _index = _col.find('.')
                _join_para = left_join[int(_col[1: _index])]
                _col = _col[_index+1:]

                _join_db_name = _join_para.get('db_name', self._db_name)
                _join_tab = _join_para['collection']
                _as_name = '%s' % _join_para.get('as', _join_tab)
                _col_as_name = '%s.' % _as_name
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
                _sorts.append('%s%s %s' % (_col_as_name, _col, 'asc' if _item[1] == 1 else 'desc'))
            else:
                if _col in _fixed_cols:
                    _sorts.append('%s%s %s' % (_col_as_name, _col, 'asc' if _item[1] == 1 else 'desc'))
                else:
                    # 属于扩展字段
                    if _as_name in ('_main_table', '_inner_temp_as_name'):
                        _key = self._add_to_json_query_cols(
                            _col, json_query_cols_dict=json_query_cols_dict, fixed_cols=_fixed_cols,
                            as_name=_as_name, unuse_as_name=(_col_as_name == '')
                        )
                        _sorts.append('%s.value %s' % (
                            json_query_cols_dict[_as_name][_key]['as'], 'asc' if _item[1] == 1 else 'desc'
                        ))
                    else:
                        # 关联表不使用json_tree形式
                        _sorts.append('%s %s' % (
                            self._get_json_extract_sql(
                                _col, fixed_cols=_fixed_cols, as_name=_as_name, unuse_as_name=(_col_as_name == '')
                            ), 'asc' if _item[1] == 1 else 'desc'
                        ))

        # 返回结果
        return ','.join(_sorts)

    def _get_group_sql(self, group: dict, fixed_col_define: dict = None,
            sql_paras: list = [], json_query_cols_dict: dict = {}, unuse_as_name: bool = False) -> tuple:
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
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典
        @param {bool} unuse_as_name=False - 指定不使用as_name

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
            if isinstance(_val, dict):
                # 是聚合函数
                _op = list(_val.keys())[0]
                _col = _val[_op]
                if type(_col) == str and _col.startswith('$'):
                    # 是字段
                    _col = _col[1:]
                    if _col not in _fixed_cols:
                        # 非固定字段
                        _col = self._add_to_json_query_cols(
                            _col, json_query_cols_dict=json_query_cols_dict, fixed_cols=_fixed_cols,
                            unuse_as_name=unuse_as_name
                        )
                        _col = json_query_cols_dict['_main_table'][_col]['as']
                        _select.append('%s(%s.value) as %s' % (_op_mapping[_op], _col, _key))
                    else:
                        _select.append('%s(%s) as %s' % (_op_mapping[_op], _col, _key))
                else:
                    # 是值
                    _select.append('%s(?) as %s' % (_op_mapping[_op], _key))
                    sql_paras.append(_col)
            elif _val_type == str and _val.startswith('$'):
                # 是字段
                _col = _val[1:]
                if _col not in _fixed_cols:
                    # 非固定字段
                    _col = self._add_to_json_query_cols(
                        _col, json_query_cols_dict=json_query_cols_dict, fixed_cols=_fixed_cols,
                        unuse_as_name=unuse_as_name
                    )
                    _col = json_query_cols_dict['_main_table'][_col]['as']
                    _select.append('%s.value as %s' % (_col, _key))
                    _groupby.append('%s.value' % _col)
                else:
                    _select.append('%s as %s' % (_col, _key))
                    _groupby.append('%s' % _col)
            else:
                # 是固定值
                _select.append('? as %s' % _key)
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

    def _get_left_join_sqls(self, db_name: str, collection: str, left_join: list, sql_paras: list = [],
            json_query_cols_dict: dict = {}, session=None, fixed_col_define: dict = None) -> list:
        """
        获取左关联的关联表sql清单

        @param {str} db_name - 主表数据库名
        @param {str} collection - 主表名
        @param {list} left_join - 左关联配置
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典
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

            if _as_name not in json_query_cols_dict.keys():
                # 初始化json列字典表
                json_query_cols_dict[_as_name] = {}

            # 表字段定义
            _fixed_col_define = {'cols': []} if fixed_col_define is None else fixed_col_define
            _fixed_cols = _fixed_col_define['cols']
            _join_fixed_col_define = AsyncTools.sync_run_coroutine(self._get_fixed_col_define(
                _join_tab, db_name=_join_db_name, session=session
            ))
            _join_fixed_cols = _join_fixed_col_define['cols']

            # on语句
            _on_fields = []
            for _on in _join_para['join_fields']:
                if _on[0] != '_id' and _on[0] not in _fixed_col_define['cols']:
                    # 扩展字段
                    # _key = self._add_to_json_query_cols(
                    #     _on[0], json_query_cols_dict=json_query_cols_dict, fixed_cols=_fixed_cols
                    # )
                    # _field0 = "%s.value" % json_query_cols_dict['_main_table'][_key]['as']
                    _field0 = self._get_json_extract_sql(
                        _on[0], fixed_cols=_fixed_cols
                    )
                else:
                    _field0 = '_main_table.%s' % _on[0]

                if _on[1] != '_id' and _on[1] not in _join_fixed_col_define['cols']:
                    # 扩展字段
                    # _key = self._add_to_json_query_cols(
                    #     _on[1], json_query_cols_dict=json_query_cols_dict, fixed_cols=_join_fixed_cols,
                    #     as_name=_as_name
                    # )
                    # _field1 = "%s.value" % json_query_cols_dict[_as_name][_key]['as']
                    _field1 = self._get_json_extract_sql(
                        _on[1], fixed_cols=_join_fixed_cols, as_name=_as_name
                    )
                else:
                    _field1 = '%s.%s' % (_as_name, _on[1])

                _on_fields.append('%s = %s' % (_field0, _field1))

            # 根据是否有过滤条件处理
            _filter = _join_para.get('filter', None)
            if _filter is None:
                _sqls.append({
                    'as': _as_name, 'tab': '%s.%s' % (_join_db_name, _join_tab), 'on': _on_fields
                })
            else:
                # 有过滤条件, 按查询表的方式关联
                _self_json_query_cols_dict = {'_inner_temp_as_name': {}}
                _self_sql_paras = []
                _filter_sql = self._get_filter_sql(
                    _filter, fixed_col_define=_join_fixed_col_define, sql_paras=_self_sql_paras,
                    json_query_cols_dict=_self_json_query_cols_dict, as_name='_inner_temp_as_name',
                    unuse_as_name=True
                )
                _self_tabs = ['%s.%s' % (_join_db_name, _join_tab)]
                for _key, _key_para in _self_json_query_cols_dict['_inner_temp_as_name'].items():
                    _self_tabs.append(
                        'json_tree(%s, "$.%s") as %s' % (
                            _key_para['col'], _key_para['path'], _key_para['as']
                        )
                    )

                _sqls.append({
                    'as': _as_name, 'on': _on_fields, 'sql_paras': _self_sql_paras,
                    'tab': '(select * from %s where %s)' % (
                        ','.join(_self_tabs), _filter_sql
                    )
                })

        return _sqls

    #############################
    # 生成SQL转换的处理函数
    #############################
    def _sqls_fun_not_support(self, op: str, *args, **kwargs):
        """
        驱动不支持的情况
        """
        raise aiosqlite.NotSupportedError('sqlite3 not support this operation')

    def _sqls_fun_create_db(self, op: str, *args, **kwargs) -> tuple:
        """
        生成添加数据库的sql语句数组
        """
        _name = args[0]  # 数据库名
        _file = args[1] if len(args) > 1 else os.path.join(self._db_path, _name + '.db')  # 数据库文件
        _sql = "ATTACH DATABASE ? AS ?"

        return ([_sql], [(_file, _name)], {})

    def _sqls_fun_list_dbs(self, op: str, *args, **kwargs) -> tuple:
        """
        生成获取数据库清单的sql语句数组
        """
        _sql = "PRAGMA database_list"
        return ([_sql], None, {'is_query': True})

    def _sqls_fun_drop_db(self, op: str, *args, **kwargs) -> tuple:
        """
        生成分离数据库的sql语句数组
        """
        _name = args[0]  # 数据库名
        _sql = "DETACH DATABASE ?"

        return ([_sql], [(_name, )], {})

    def _sqls_fun_create_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成建表的sql语句数组
        """
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _sqls = []

        # 生成表字段清单
        _cols = []
        if kwargs.get('fixed_col_define', None) is not None:
            for _col_name, _col_def in kwargs['fixed_col_define'].items():
                _cols.append(
                    '%s %s%s%s' % (
                        _col_name, self._dbtype_mapping(_col_def['type'], _col_def.get('len', None)),
                        '' if _col_def.get('nullable', True) else ' not null',
                        '' if _col_def.get('default', None) is None else ' default %s' % self._get_col_default_value(
                            _col_def['default'], _col_def['type']
                        )
                    )
                )

        # 建表脚本, 需要带上数据库前缀
        _sql = 'create table if not exists %s%s(_id varchar(100) primary key, %s nosql_driver_extend_tags JSON)' % (
            _db_prefix, _collection, (', '.join(_cols) + ',') if len(_cols) > 0 else '',
        )
        _sqls.append(_sql)

        # 建索引脚本, 创建索引时, 索引名带数据库前缀, 表名无需带前缀
        if kwargs.get('indexs', None) is not None:
            for _index_name, _index_def in kwargs['indexs'].items():
                _cols = []
                for _col_name, _para in _index_def['keys'].items():
                    _cols.append(_col_name)
                _sql = 'create %sindex if not exists %s%s on %s(%s)' % (
                    'UNIQUE ' if _index_def.get('paras', {}).get('unique', False) else '',
                    _db_prefix, _index_name, _collection, ','.join(_cols)
                )
                _sqls.append(_sql)

        # 返回结果
        return (_sqls, None, {})

    def _sql_fun_list_collections(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询表清单的sql语句数组
        """
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _filter = kwargs.get('filter', None)
        # 生成where语句
        _sql_paras = []
        _where = self._get_filter_sql(_filter, sql_paras=_sql_paras, unuse_as_name=True)

        _sql = "SELECT name FROM %ssqlite_master where type='table'%s order by name" % (
            _db_prefix, '' if _where is None else ' and %s' % _where
        )

        # 返回结果
        return ([_sql], None if len(_sql_paras) == 0 else [_sql_paras], {'is_query': True})

    def _sql_fun_drop_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成删除表的sql语句数组
        """
        _collection = '%s%s' % (
            '' if self._db_name == 'main' else ('%s.' % self._db_name), args[0]
        )
        _sql = "drop table %s" % _collection
        return ([_sql], None, {})

    def _sql_fun_turncate_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成清空表的sql语句数组
        """
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _sqls = []
        _sqls.append(
            'delete from %s%s' % (_db_prefix, _collection)
        )
        # 自增长ID设置为0, 语句执行会报错
        # _sqls.append(
        #     "update %ssqlite_sequence SET seq = 0 where name ='%s'" % (_db_prefix, _collection)
        # )
        return (_sqls, None, {})

    def _sql_fun_insert_one(self, op: str, *args, **kwargs) -> tuple:
        """
        生成插入数据的sql语句数组
        """
        _collection = '%s%s' % (
            '' if self._db_name == 'main' else ('%s.' % self._db_name), args[0]
        )
        _row = args[1]
        _fixed_col_define = args[2] if len(args) > 2 else kwargs.get('fixed_col_define', {})

        # 生成插入字段和值
        _cols = ['_id']
        _sql_paras = [_row.pop('_id')]
        for _col in _fixed_col_define.get('cols', []):
            _val = _row.pop(_col, None)
            if _val is not None:
                _cols.append(_col)
                _sql_paras.append(self._python_to_dbtype(_val)[1])

        # 剩余的内容放入扩展字段
        _cols.append('nosql_driver_extend_tags')
        _sql_paras.append(self._python_to_dbtype(_row, dbtype='json')[1])

        # 组成sql
        _sql = 'insert into %s(%s) values(%s)' % (
            _collection, ','.join(_cols), ','.join(['?' for _tcol in _cols])
        )

        return ([_sql], [_sql_paras], {})

    def _sql_fun_insert_many(self, op: str, *args, **kwargs) -> tuple:
        """
        生成插入数据的sql语句数组
        """
        _collection = '%s%s' % (
            '' if self._db_name == 'main' else ('%s.' % self._db_name), args[0]
        )
        _rows = args[1]
        _fixed_col_define = args[2] if len(args) > 2 else kwargs.get('fixed_col_define', {})

        # 生成插入字段列表
        _cols = ['_id']
        for _col in _fixed_col_define.get('cols', []):
            if _col == '_id':
                continue
            _cols.append(_col)

        _cols.append('nosql_driver_extend_tags')

        # 遍历生成插入数据和参数
        _para_array = []
        _value_array = []
        for _s_row in _rows:
            _row = copy.copy(_s_row)  # 浅复制即可
            _sql_paras = [_row.pop('_id', str(ObjectId()))]
            _col_values = ['?']
            for _col in _fixed_col_define.get('cols', []):
                if _col == '_id':
                    continue

                _val = _row.pop(_col, None)
                if _val is None:
                    _col_values.append('null')
                else:
                    _col_values.append('?')
                    _sql_paras.append(self._python_to_dbtype(_val)[1])

            # 剩余的内容放入扩展字段
            _col_values.append('?')
            _sql_paras.append(self._python_to_dbtype(_row, dbtype='json')[1])

            # 添加到数组
            _para_array.extend(_sql_paras)
            _value_array.append('select %s' % ','.join(_col_values))

        # 生成插入sql
        _sql = 'insert into %s(%s) %s' % (
            _collection, ','.join(_cols), ' union '.join(_value_array)
        )

        return ([_sql], [_para_array], {})

    def _sql_fun_update(self, op: str, *args, **kwargs) -> tuple:
        """
        生成更新数据的sql语句数组
        """
        # 获取参数
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _filter = args[1]
        _update = args[2]
        _fixed_col_define = kwargs.get('fixed_col_define', None)

        # 处理where条件语句
        _where_sql_paras = []
        _json_query_cols_dict = {'_main_table': {}}
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, unuse_as_name=True
        )

        # 处理更新配置语句
        _update_sql_paras = []
        _update_sql = self._get_update_sql(
            _update, fixed_col_define=_fixed_col_define, sql_paras=_update_sql_paras,
            json_query_cols_dict=_json_query_cols_dict
        )

        _sql_collection = '%s%s' % (_db_prefix, _collection)
        if len(_json_query_cols_dict['_main_table']) == 0:
            # 没有以json对象做条件的情况
            _sql = 'update %s set %s' % (_sql_collection, _update_sql)
            if _where_sql is not None:
                _sql = '%s where %s' % (_sql, _where_sql)
                _update_sql_paras.extend(_where_sql_paras)
        else:
            # 有使用json对象做条件, 由于update语句不支持json_tree, 要使用子查询的方式处理
            _tabs = [_sql_collection]
            for _key, _key_para in _json_query_cols_dict['_main_table'].items():
                _tabs.append(
                    'json_tree(%s, "$.%s") as %s' % (
                        _key_para['col'], _key_para['path'], _key_para['as']
                    )
                )

            _sql = 'update %s set %s where _id in (select _id from %s%s)' % (
                _sql_collection, _update_sql, ','.join(_tabs),
                '' if _where_sql is None else ' where %s' % _where_sql
            )
            if _where_sql is not None:
                _update_sql_paras.extend(_where_sql_paras)

        # 返回语句
        return ([_sql], [_update_sql_paras], {})

    def _sql_fun_delete(self, op: str, *args, **kwargs) -> tuple:
        """
        生成删除数据的sql语句数组
        """
        # 获取参数
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _filter = args[1]
        _fixed_col_define = kwargs.get('fixed_col_define', None)

        # 处理where条件语句
        _where_sql_paras = []
        _json_query_cols_dict = {'_main_table': {}}
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, unuse_as_name=True
        )

        _sql_paras = None
        _sql_collection = '%s%s' % (_db_prefix, _collection)
        if len(_json_query_cols_dict['_main_table']) == 0:
            # 没有以json对象做条件的情况
            _sql = 'delete from %s' % _sql_collection
            if _where_sql is not None:
                _sql = '%s where %s' % (_sql, _where_sql)
                _sql_paras = _where_sql_paras
        else:
            # 有使用json对象做条件, 由于delete语句不支持json_tree, 要使用子查询的方式处理
            _tabs = [_sql_collection]
            for _key, _key_para in _json_query_cols_dict['_main_table'].items():
                _tabs.append(
                    'json_tree(%s, "$.%s") as %s' % (
                        _key_para['col'], _key_para['path'], _key_para['as']
                    )
                )

            _sql = 'delete from %s where _id in (select _id from %s%s)' % (
                _sql_collection, ','.join(_tabs),
                '' if _where_sql is None else ' where %s' % _where_sql
            )
            if _where_sql is not None:
                _sql_paras = _where_sql_paras

        # 返回语句
        return ([_sql], [_sql_paras], {})

    def _sql_fun_query(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询数据的sql语句数组
        """
        # 获取参数
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _filter = kwargs.get('filter', {})
        _projection = kwargs.get('projection', None)
        _sort = kwargs.get('sort', None)
        _skip = kwargs.get('skip', None)
        _limit = kwargs.get('limit', None)
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _left_join = kwargs.get('left_join', None)  # 关联查询
        _session = kwargs.get('session', None)  # 数据库操作的session

        # 存储不同表的json查询列信息的字典
        _json_query_cols_dict = {
            '_main_table': {}  # 主表
        }

        # 处理关联表
        _left_join_sql_paras = []
        _left_join_sqls = None
        if _left_join is not None:
            _left_join_sqls = self._get_left_join_sqls(
                self._db_name, _collection, _left_join, sql_paras=_left_join_sql_paras,
                json_query_cols_dict=_json_query_cols_dict,
                session=_session, fixed_col_define=_fixed_col_define
            )

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, left_join=_left_join, session=_session
        )

        # 处理sort语句
        _sort_sql_paras = []
        _sort_sql = None
        if _sort is not None:
            _sort_sql = self._get_sort_sql(
                _sort, fixed_col_define=_fixed_col_define, sql_paras=_sort_sql_paras,
                json_query_cols_dict=_json_query_cols_dict, left_join=_left_join, session=_session
            )

        # 处理projection语句
        _projection_sql_paras = []
        _projection_sql = self._get_projection_sql(
            _projection, fixed_col_define=_fixed_col_define, sql_paras=_projection_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, left_join=_left_join, session=_session
        )

        # 形成查询json的表别名
        _tabs = ['%s%s as _main_table' % (_db_prefix, _collection)]
        for _key, _key_para in _json_query_cols_dict['_main_table'].items():
            _tabs.append(
                'json_tree(%s, "$.%s") as %s' % (
                    _key_para['col'], _key_para['path'], _key_para['as']
                )
            )

        # 组装语句
        _sql_paras = []
        _sql = 'select %s from %s' % (_projection_sql, ','.join(_tabs))
        _sql_paras.extend(_projection_sql_paras)

        # 组装关联表
        if _left_join_sqls is not None:
            for _left_join_para in _left_join_sqls:
                _as_name = _left_join_para['as']
                _join_tabs = ['%s as %s' % (_left_join_para['tab'], _as_name)]
                # for _key, _key_para in _json_query_cols_dict[_as_name].items():
                #     _join_tabs.append(
                #         'json_tree(%s, "$.%s") as %s' % (
                #             _key_para['col'], _key_para['path'], _key_para['as']
                #         )
                #     )

                _sql = '%s left outer join %s' % (
                    _sql, '%s on %s' % (
                        ','.join(_join_tabs), ' and '.join(_left_join_para['on'])
                    )
                )
                if _left_join_para.get('sql_paras', None) is not None:
                    _sql_paras.extend(_left_join_para['sql_paras'])

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
                _sql = '%s %s' % (_sql, 'limit %d offset %d' % (-1, _skip))

        # 返回最终结果
        return ([_sql], [_sql_paras], {'is_query': True})

    def _sql_fun_query_count(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询数据count的sql语句数组
        """
        # 获取参数
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _filter = kwargs.get('filter', {})
        _skip = kwargs.get('skip', None)
        _limit = kwargs.get('limit', None)
        _fixed_col_define = kwargs.get('fixed_col_define', None)
        _left_join = kwargs.get('left_join', None)  # 关联查询
        _session = kwargs.get('session', None)  # 数据库操作的session

        # 存储不同表的json查询列信息的字典
        _json_query_cols_dict = {
            '_main_table': {}  # 主表
        }

        # 处理关联表
        _left_join_sql_paras = []
        _left_join_sqls = None
        if _left_join is not None:
            _left_join_sqls = self._get_left_join_sqls(
                self._db_name, _collection, _left_join, sql_paras=_left_join_sql_paras,
                json_query_cols_dict=_json_query_cols_dict,
                session=_session, fixed_col_define=_fixed_col_define
            )

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, left_join=_left_join, session=_session
        )

        # 形成查询json的表别名
        _tabs = ['%s%s as _main_table' % (_db_prefix, _collection)]
        for _key, _key_para in _json_query_cols_dict['_main_table'].items():
            _tabs.append(
                'json_tree(%s, "$.%s") as %s' % (
                    _key_para['col'], _key_para['path'], _key_para['as']
                )
            )

        # 组装语句
        if _limit is not None or _skip is not None:
            # 有获取数据区间, 只能采用性能差的子查询模式
            _sql_paras = []
            _sub_sql = 'select * from %s' % (','.join(_tabs))

            # 组装关联表
            if _left_join_sqls is not None:
                for _left_join_para in _left_join_sqls:
                    _sub_sql = '%s left outer join %s' % (
                        _sub_sql, '%s as %s on %s' % (
                            _left_join_para['tab'], _left_join_para['as'], ' and '.join(_left_join_para['on'])
                        )
                    )
                    if _left_join_para.get('sql_paras', None) is not None:
                        _sql_paras.extend(_left_join_para['sql_paras'])

            if _where_sql is not None:
                _sub_sql = '%s where %s' % (_sub_sql, _where_sql)
                _sql_paras.extend(_where_sql_paras)

            # 增加skip和limit
            if _limit is not None:
                if _skip is not None:
                    _sub_sql = '%s %s' % (_sub_sql, 'limit %d offset %d' % (_limit, _skip))
                else:
                    _sub_sql = '%s %s' % (_sub_sql, 'limit %d' % _limit)
            else:
                if _skip is not None:
                    _sub_sql = '%s %s' % (_sub_sql, 'limit %d offset %d' % (-1, _skip))

            _sql = 'select count(*) from (%s)' % _sub_sql
        else:
            _sql_paras = []
            _sql = 'select count(*) from %s' % (','.join(_tabs))

            # 组装关联表
            if _left_join_sqls is not None:
                for _left_join_para in _left_join_sqls:
                    _sql = '%s left outer join %s' % (
                        _sql, '%s as %s on %s' % (
                            _left_join_para['tab'], _left_join_para['as'], ' and '.join(_left_join_para['on'])
                        )
                    )
                    if _left_join_para.get('sql_paras', None) is not None:
                        _sql_paras.extend(_left_join_para['sql_paras'])

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
        _db_prefix = '' if self._db_name == 'main' else ('%s.' % self._db_name)
        _collection = args[0]
        _group = kwargs.get('group', None)
        _filter = kwargs.get('filter', {})
        _projection = kwargs.get('projection', None)
        _sort = kwargs.get('sort', None)
        _fixed_col_define = kwargs.get('fixed_col_define', None)

        # 处理group by语句
        _select_sql_paras = []
        _json_query_cols_dict = {'_main_table': {}}
        _select_sql, _group_by_sql = self._get_group_sql(
            _group, fixed_col_define=_fixed_col_define, sql_paras=_select_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, unuse_as_name=True
        )

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, unuse_as_name=True
        )

        # 处理sort语句
        _sort_sql_paras = []
        _sort_sql = None
        if _sort is not None:
            _sort_sql = self._get_sort_sql(
                _sort, fixed_col_define=None, sql_paras=_sort_sql_paras,
                json_query_cols_dict=_json_query_cols_dict, unuse_as_name=True
            )

        # 处理projection语句
        _projection_sql_paras = []
        _projection_sql = self._get_projection_sql(
            _projection, fixed_col_define=None, sql_paras=_projection_sql_paras,
            json_query_cols_dict=_json_query_cols_dict, is_group_by=True, unuse_as_name=True
        )

        # 形成查询json的表别名
        _tabs = ['%s%s' % (_db_prefix, _collection)]
        for _key, _key_para in _json_query_cols_dict['_main_table'].items():
            _tabs.append(
                'json_tree(%s, "$.%s") as %s' % (
                    _key_para['col'], _key_para['path'], _key_para['as']
                )
            )

        # 组装查询语句
        _sql_paras = []
        _sql = 'select %s from %s' % (
            _select_sql, ','.join(_tabs)
        )
        _sql_paras.extend(_select_sql_paras)

        if _where_sql is not None:
            _sql = '%s where %s' % (_sql, _where_sql)
            _sql_paras.extend(_where_sql_paras)

        _sql = '%s group by %s' % (_sql, _group_by_sql)

        if _sort_sql is not None or _projection_sql != '*':
            # 有排序或指定返回字段的情况, 需要包装多一层
            _sql = 'select %s from (%s)' % (_projection_sql, _sql)
            if _sort_sql is not None:
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

    def _add_to_json_query_cols(self, col_name: str, json_query_cols_dict: dict = {}, fixed_cols: list = [],
            as_name: str = '_main_table', unuse_as_name: bool = False) -> str:
        """
        将字段查询信息添加到json_query_cols_dict字典

        @param {str} col_name - 查询字段名(x.x.x形式)
        @param {dict} json_query_cols_dict={} - 返回sql中json查询所需的json_tree处理的字段字典
            key为查询名(json_query_[as_name]_字段名_字段路径.value), value为配置字典{'col': 物理字段名, 'path': '真实查询路径', 'as': '字段别名'}
            注1: 真实查询路径 'key1.key2[10].key3' 对应的字段路径为 'key1_key2_10_key3'
            注2: nosql_driver_extend_tags字段名不填入查询名中
        @param {list} fixed_cols=[] - 固定字段定义清单
        @param {str} as_name='_main_table' - 字典对应表的别名
        @param {bool} unuse_as_name=False - 指定不使用as_name

        @returns {str} - 返回json_query_cols_dict字典对应的key
        """
        _path_cols = col_name.split('.')
        _as = '%s%s' % ('' if unuse_as_name else ('%s_' % as_name), '_'.join(_path_cols))
        _key = 'json_query_%s.value' % _as
        _key_para = json_query_cols_dict[as_name].get(_key, None)
        if _key_para is None:
            # 不在查询字段中, 需要添加到查询字段
            if len(_path_cols) > 1 and _path_cols[0] in fixed_cols:
                # 是json类型的固定字段
                _col_name = _path_cols[0]
                _path = self._convert_path_array(_path_cols[1:])
            else:
                _col_name = 'nosql_driver_extend_tags'
                _path = self._convert_path_array(_path_cols)

            json_query_cols_dict[as_name][_key] = {
                'col': '%s%s' % ('' if unuse_as_name else ('%s.' % as_name), _col_name), 'path': _path, 'as': _as, 'real_col': col_name
            }

        return _key

    def _get_json_extract_sql(self, col_name: str, fixed_cols: list = [], as_name: str = '_main_table',
            unuse_as_name: bool = False) -> str:
        """
        获取指定字段的json_extract函数字符串

        @param {str} col_name - 查询字段名(x.x.x形式)
        @param {list} fixed_cols=[] - 固定字段定义清单
        @param {str} as_name='_main_table' - 字典对应表的别名
        @param {bool} unuse_as_name=False - 指定不使用as_name

        @returns {str} - 返回的sql语句
        """
        _as = '' if unuse_as_name else ('%s.' % as_name)
        _path_cols = col_name.split('.')
        if len(_path_cols) > 1 and _path_cols[0] in fixed_cols:
            # 是json类型的固定字段
            _col_name = _path_cols[0]
            _path = self._convert_path_array(_path_cols[1:])
        else:
            _col_name = 'nosql_driver_extend_tags'
            _path = self._convert_path_array(_path_cols)

        return 'json_extract(%s%s, "$.%s")' % (_as, _col_name, _path)
