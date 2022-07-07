#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
PostgreSQL的HiveNetNoSql实现模块

@module pgsql
@file pgsql.py
"""
import os
import sys
import copy
import json
from typing import Any, Union
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.connection_pool import PoolConnectionFW
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
process_install_psycopg = False
while True:
    try:
        # psycopg3 暂时不支持mac M1的版本
        if sys.platform == 'darwin':
            import psycopg2 as pgadapter
        else:
            from psycopg import AsyncConnection as pgadapter
        break
    except ImportError:
        if process_install_psycopg:
            break
        else:
            if sys.platform == 'darwin':
                PythonEnvTools.install_package('psycopg2-binary')
            else:
                PythonEnvTools.install_package('psycopg')
            process_install_psycopg = True
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetNoSql.base.driver_fw import NosqlAIOPoolDriver


class PgSQLPoolConnection(PoolConnectionFW):
    """
    PostgreSQL连接池连接对象
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
            self._conn.isolation_level
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


class PgSQLNosqlDriver(NosqlAIOPoolDriver):
    """
    PostgreSQL数据库MySQL驱动
    """

    #############################
    # 构造函数重载, 主要是注释
    #############################
    def __init__(self, connect_config: dict = {}, pool_config: dict = {}, driver_config: dict = {}):
        """
        初始化驱动

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 数据库主机地址, 默认为'localhost'
            port {int} - 连接数据库的端口, 默认为5432
            usedb {str} - 登录后使用的数据库(其实是schema), 默认为'public'
                注: postgresql的连接对象不支持切换真实数据库, 因此驱动所指的数据库其实是schema
            username {str} - 登录验证用户
            password {str} - 登录验证密码
            dbname {str} - 登录的真实数据库, 默认为'postgres'
                注: 过程中无法切换真实数据库, 如果需要切换要重新创建驱动对象
            connect_on_init {bool} - 是否启动时直接连接数据库
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            default_str_len {int} - 默认的字符串类型长度, 默认为30
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
            psycopg2.connect 支持的其他参数...
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
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    }
                }
            init_collections {dict} - 要在启动驱动时创建的集合(表)
                {
                    '数据库名': {
                        '集合名': {
                            'index_only': False,  # 是否仅用于索引, 不创建
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}
                        }
                        ...
                    },
                    ...
                }
            logger {Logger} - 传入驱动的日志对象
            close_action {str} - 关闭连接时自动处理动作, None-不处理, 'commit'-自动提交, 'rollback'-自动回滚
            regexp_ignore_case {bool} - 正则表达式是否忽略大小写, 默认为False
        """
        super().__init__(
            connect_config=connect_config, pool_config=pool_config, driver_config=driver_config
        )

    #############################
    # 需要继承类实现的内部函数
    #############################
    def _get_db_creator(self, connect_config: dict, pool_config: dict, driver_config: dict) -> tuple:
        """
        获取数据库连接驱动及参数

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 数据库主机地址, 默认为'localhost'
            port {int} - 连接数据库的端口, 默认为5432
            usedb {str} - 登录后使用的数据库(其实是schema), 默认为'public'
                注: postgresql的连接对象不支持切换真实数据库, 因此驱动所指的数据库其实是schema
            username {str} - 登录验证用户
            password {str} - 登录验证密码
            dbname {str} - 登录的真实数据库, 默认为'postgres'
                注: 过程中无法切换真实数据库, 如果需要切换要重新创建驱动对象
            connect_on_init {bool} - 是否启动时直接连接数据库
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            default_str_len {int} - 默认的字符串类型长度, 默认为30
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
            psycopg2.connect 支持的其他参数...
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
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    }
                }
            init_collections {dict} - 要在启动驱动时创建的集合(表)
                {
                    '数据库名': {
                        '集合名': {
                            'index_only': False,  # 是否仅用于索引, 不创建
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}
                        }
                        ...
                    },
                    ...
                }
            logger {Logger} - 传入驱动的日志对象
            close_action {str} - 关闭连接时自动处理动作, None-不处理, 'commit'-自动提交, 'rollback'-自动回滚
            regexp_ignore_case {bool} - 正则表达式是否忽略大小写, 默认为False
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
        # 标准类型和数据库类型的映射关系字典
        self._dbtype_cast_mapping = {
            'str': 'varchar',
            'int': 'int',
            'float': 'float',
            'bool': 'boolean',
            'json': 'json'
        }
        self._regexp_op = '~*' if self._driver_config.get('regexp_ignore_case', False) else '~'

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
        _kwargs['dbname'] = connect_config.get('dbname', 'postgres')
        _kwargs['user'] = connect_config.get('username', None)
        _kwargs['connect_timeout'] = connect_config.get('connect_timeout', 20)

        # 移除不使用的参数
        _connect_config = copy.deepcopy(connect_config)
        for _pop_item in ('usedb', 'dbname', 'username', 'connect_on_init', 'connect_timeout', 'transaction_share_cursor'):
            _connect_config.pop(_pop_item, None)

        # 合并参数
        _kwargs.update(_connect_config)

        return {
            'creator': pgadapter, 'pool_connection_class': PgSQLPoolConnection,
            'args': _args, 'kwargs': _kwargs, 'connect_method_name': 'connect',
            'pool_update_config': {
                'pool_extend_paras': {
                    'close_action': driver_config.get('close_action', None)
                }
            },
            'current_db_name': connect_config.get('usedb', 'public')
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
            raise pgadapter.NotSupportedError('driver not support this operation')

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

    async def _get_cols_info(self, collection: str, session: Any = None) -> list:
        """
        获取制定集合(表)的列信息

        @param {str} collection - 集合名(表)
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
        _sql = "select column_name as name, data_type as type from information_schema.columns where table_schema='%s' and table_name='%s' order by ordinal_position" % (
            self._db_name, collection
        )
        _ret = await self._execute_sql(
            _sql, paras=None, is_query=True, conn=_conn, cursor=_cursor
        )

        # 处理标准类型
        for _row in _ret:
            if _row['type'] == 'boolean':
                _row['type'] = 'bool'
            elif _row['type'] == 'integer':
                _row['type'] = 'int'
            elif _row['type'] == 'double precision':
                _row['type'] = 'float'
            elif _row['type'] == 'jsonb':
                _row['type'] = 'json'
            else:
                _row['type'] = 'str'

        return _ret

    async def _get_current_db_name(self, session: Any = None) -> str:
        """
        获取当前数据库名

        @param {Any} session=None - 指定事务连接对象

        @returns {str} - 数据库名
        """
        if self._db_name is not None:
            return self._db_name
        else:
            return 'public'

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
            return 'boolean'
        elif std_type == 'json':
            return 'JSONB'
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
                _dbvalue = True if val else False
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
        return val.replace('\\', '\\\\').replace('\r', '\\r').replace(
            '\n', '\\n').replace('\t', '\\t').replace("'", "''").replace('"', '\\"')

    def _get_filter_unit_sql(self, key: str, val: Any, fixed_col_define: dict = None,
            sql_paras: list = []) -> str:
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

        @returns {str} - 单个规则对应的sql
        """
        # 判断是否处理json的值, 形成最后比较的 key 值
        _key = key
        _col_type = None
        _is_json = False
        _cast_by_val = False  # 是否需要根据比较值判断类型
        if fixed_col_define is not None:
            _fixed_cols = fixed_col_define.get('cols', [])
            if key != '_id' and key not in _fixed_cols:
                _is_json = True
                _col_type = fixed_col_define.get('define', {}).get(_key, {}).get('type', None)
                if _col_type is None:
                    _key = "nosql_driver_extend_tags->'%s'" % key
                    _cast_by_val = True
                elif _col_type == 'str':
                    # 字符串返回, 否则会带双引号
                    _key = "nosql_driver_extend_tags->>'%s'" % key
                else:
                    _key = "cast(nosql_driver_extend_tags->'%s' as %s)" % (
                        key, self._dbtype_cast_mapping[_col_type]
                    )

        if type(val) == dict:
            # 有特殊规则
            _cds = []  # 每个规则的数组
            for _op, _para in val.items():
                if _op in self._filter_symbol_mapping.keys():
                    # 比较值转换为数据库的格式
                    _dbtype, _cmp_val = self._python_to_dbtype(_para)
                    if _is_json and _cast_by_val:
                        if _dbtype == 'str':
                            _key = "nosql_driver_extend_tags->>'%s'" % key
                        else:
                            _key = 'cast(%s as %s)' % (_key, self._dbtype_cast_mapping[_dbtype])

                    _cds.append('%s %s %s' % (_key, self._filter_symbol_mapping[_op], '%s'))
                    sql_paras.append(_cmp_val)
                elif _op == '$regex':
                    if _is_json and _cast_by_val:
                        _key = "nosql_driver_extend_tags->>'%s'" % key

                    _cds.append("%s %s %s" % (_key, self._regexp_op, '%s'))
                    sql_paras.append(_para)
                else:
                    raise pgadapter.NotSupportedError('psycopg not support this search operation [%s]' % _op)
            _sql = ' and '.join(_cds)
        else:
            # 直接相等的条件
            _dbtype, _cmp_val = self._python_to_dbtype(val)
            if _is_json and _cast_by_val:
                if _dbtype == 'str':
                    _key = "nosql_driver_extend_tags->>'%s'" % key
                else:
                    _key = 'cast(%s as %s)' % (_key, self._dbtype_cast_mapping[_dbtype])

            _sql = '%s = %s' % (_key, '%s')
            sql_paras.append(_cmp_val)

        return _sql

    def _get_filter_sql(self, filter: dict, fixed_col_define: dict = None,
            sql_paras: list = []) -> str:
        """
        获取兼容mongodb过滤条件规则的sql语句

        @param {dict} filter - 过滤规则字典
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数

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
                        _condition, fixed_col_define=fixed_col_define, sql_paras=sql_paras
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
                    _col, _val, fixed_col_define=fixed_col_define, sql_paras=sql_paras
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

        # 扩展字段的set字典, 设置json指定key的值, 每处理一个字段在sqls增加一个语句, 对应在paras参数列表
        _extend_set_dict = {'sqls': [], 'paras': []}

        # 扩展字段的remove列表, 设置要删除json的key的字段
        _extend_remove_list = []

        # 遍历处理
        for _op, _para in update.items():
            for _key, _val in _para.items():
                if fixed_col_define is None or _key == '_id' or _key in fixed_col_define.get('cols', []):
                    # 是固定字段
                    if _op == '$set':
                        _upd_dict[_key] = {'sql': '%s', 'paras': [self._python_to_dbtype(_val)[1]]}
                    elif _op == '$unset':
                        _upd_dict[_key] = {'sql': 'null', 'paras': []}
                    elif _op == '$inc':
                        _upd_dict[_key] = {'sql': 'COALESCE(%s,0) + %s' % (_key, '%s'), 'paras': [_val]}
                    elif _op == '$mul':
                        _upd_dict[_key] = {'sql': 'COALESCE(%s,0) * %s' % (_key, '%s'), 'paras': [_val]}
                    elif _op == '$min':
                        _upd_dict[_key] = {
                            'sql': 'case when COALESCE({key}, {pos}) < {pos} then COALESCE({key},0) else {pos} end'.format(key=_key, pos='%s'),
                            'paras': [_val, _val, _val]
                        }
                    elif _op == '$max':
                        _upd_dict[_key] = {
                            'sql': 'case when COALESCE({key}, {pos}) > {pos} then COALESCE({key},0) else {pos} end'.format(key=_key, pos='%s'),
                            'paras': [_val, _val, _val]
                        }
                    else:
                        raise pgadapter.NotSupportedError('psycopg not support this update operation [%s]' % _op)
                else:
                    # 是扩展字段
                    if _op == '$set':
                        _dbtype, _dbval = self._python_to_dbtype(_val, is_json=True)
                        if _dbtype in ('int', 'float', 'bool'):
                            _sql = "'{{{key}}}', '{val}'"
                        elif _dbtype == 'json':
                            _sql = "'{%s}', '%s'" % (_key, str(_dbval).replace("'", "''"))
                            _extend_set_dict['sqls'].append(_sql)
                            continue
                        else:
                            _sql = "'{%s}', '\"%s\"'" % (_key, self._db_quotes_str(str(_dbval)))
                            _extend_set_dict['sqls'].append(_sql)
                            continue
                    elif _op == '$unset':
                        _extend_remove_list.append(" - '%s'" % _key)
                        continue
                    elif _op in ('$inc', '$mul', '$min', '$max'):
                        _dbtype, _dbval = self._python_to_dbtype(_val, is_json=True)
                        # 需要取值出来, 添加查询字段
                        if _op == '$inc':
                            _sql = "'{{{key}}}', to_jsonb(COALESCE(cast(nosql_driver_extend_tags->'{key}' as float), 0) + {val})"
                            # _extend_set_dict['paras'].append(_dbval)
                        elif _op == '$mul':
                            _sql = "'{{{key}}}', to_jsonb(COALESCE(cast(nosql_driver_extend_tags->'{key}' as float), 0) * {val})"
                            # _extend_set_dict['paras'].append(_dbval)
                        elif _op == '$min':
                            _sql = "'{{{key}}}', case when COALESCE(cast(nosql_driver_extend_tags->'{key}' as float), {val}) < {val} then to_jsonb(COALESCE(cast(nosql_driver_extend_tags->'{key}' as float), 0)) else '{val}' end"
                            # _extend_set_dict['paras'].extend([_dbval, _dbval, _dbval])
                        elif _op == '$max':
                            _sql = "'{{{key}}}', case when COALESCE(cast(nosql_driver_extend_tags->'{key}' as float), {val}) > {val} then to_jsonb(COALESCE(cast(nosql_driver_extend_tags->'{key}' as float), 0)) else '{val}' end"
                            # _extend_set_dict['paras'].extend([_dbval, _dbval, _dbval])
                    else:
                        raise pgadapter.NotSupportedError('psycopg not support this update operation [%s]' % _op)

                    # 处理格式化
                    _extend_set_dict['sqls'].append(
                        _sql.format(key=_key, pos='%s', val=str(_dbval))
                    )

        # 开始生成sql语句和返回参数
        _sqls = []
        for _key, _val in _upd_dict.items():
            _sqls.append('%s=%s' % (_key, _val['sql']))
            if _val['paras'] is not None:
                sql_paras.extend(_val['paras'])

        # 处理扩展字段
        _remove_sql = ''
        if len(_extend_remove_list) > 0:
            _remove_sql = ''.join(_extend_remove_list)

        if len(_extend_set_dict['sqls']) == 0:
            if _remove_sql != '':
                _sqls.append('nosql_driver_extend_tags=nosql_driver_extend_tags%s' % _remove_sql)
        else:
            # 嵌套更新值
            _set_sql = 'nosql_driver_extend_tags'
            for _sql in _extend_set_dict['sqls']:
                _set_sql = 'jsonb_set(%s, %s, true)' % (_set_sql, _sql)

            _sqls.append(
                'nosql_driver_extend_tags=%s%s' % (
                    _set_sql, _remove_sql
                )
            )
            sql_paras.extend(_extend_set_dict['paras'])

        return ','.join(_sqls)

    def _get_projection_sql(self, projection: Union[dict, list], fixed_col_define: dict = None,
            sql_paras: list = [], is_group_by: bool = False) -> str:
        """
        获取兼容mongodb查询返回字段的sql语句

        @param {Union[dict, list]} projection - 指定结果返回的字段信息
            列表模式: ['col1','col2', ...]  注意: 该模式一定会返回 _id 这个主键
            字典模式: {'_id': False, 'col1': True, ...}  该方式可以通过设置False屏蔽 _id 的返回
        @param {dict} fixed_col_define=None - 表的固定字段配置信息字典
            {
                'cols': [],  # 表固定字段名清单
                'define': {'字段名': {'type': 'str|bool|int|...'}}
            }
        @param {list} sql_paras=[] - 返回sql对应的占位参数
        @param {bool} is_group_by=False - 指定是否group by的处理, 如果是不会处理_id字段

        @returns {str} - 返回更新部分语句sql
        """
        # 如果不指定, 返回所有字段
        if projection is None:
            return '*'

        # 标准化要显示的字段清单
        if type(projection) == dict:
            _projection = []
            for _col, _show in projection.items():
                if _show:
                    _projection.append(_col)
        else:
            # 列表形式, _id是必须包含的
            _projection = list(projection)
            if not is_group_by and '_id' not in _projection:
                _projection.insert(0, '_id')

        # 生成sql
        if fixed_col_define is None:
            # 全部认为是固定字段
            return ','.join(_projection)

        _fixed_cols = fixed_col_define.get('cols', [])
        _fixed_cols.append('_id')
        _real_cols = []
        for _col in _projection:
            if _col in _fixed_cols:
                _real_cols.append('%s' % _col)
                continue
            else:
                # 其他非固定字段
                _col_type = fixed_col_define.get('define', {}).get(_col, {}).get('type', 'str')
                if _col_type == 'str':
                    # 字符串返回, 否则会带双引号
                    _real_cols.append("nosql_driver_extend_tags->>'%s' as %s" % (_col, _col))
                else:
                    _real_cols.append(
                        "cast(nosql_driver_extend_tags->'%s' as %s) as %s" % (
                            _col, self._dbtype_cast_mapping[_col_type], _col
                        )
                    )

        # 返回sql
        return ','.join(_real_cols)

    def _get_sort_sql(self, sort: list, fixed_col_define: dict = None,
            sql_paras: list = []) -> str:
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

        @returns {str} - 返回更新部分语句sql
        """
        if fixed_col_define is None:
            # 全部认为是固定字段
            _sorts = ['%s %s' % (_item[0], 'asc' if _item[1] == 1 else 'desc') for _item in sort]
        else:
            _fixed_cols = fixed_col_define.get('cols', [])
            _fixed_cols.append('_id')
            _sorts = []
            for _item in sort:
                _col = _item[0]
                if _col in _fixed_cols:
                    _sorts.append('%s %s' % (_col, 'asc' if _item[1] == 1 else 'desc'))
                else:
                    # 属于扩展字段
                    _sorts.append("nosql_driver_extend_tags->'%s' %s" % (_col, 'asc' if _item[1] == 1 else 'desc'))

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
        @param {list} json_query_cols=[] - 返回sql中json查询所需的json_tree处理的字段名

        @returns {tuple} - 返回sql, (select语句, group by语句)
        """
        # 固定字段定义
        if fixed_col_define is None:
            _fixed_cols = []
        else:
            _fixed_cols = fixed_col_define.get('cols', [])
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
                        _col_type = fixed_col_define.get('define', {}).get(_col, {}).get('type', None)
                        if _col_type is None:
                            # _col = "case when {typeof} = 'number' then cast({tag_val} as number) else {tag_text} end".format(
                            #     typeof="jsonb_typeof(nosql_driver_extend_tags->'%s')" % _col,
                            #     tag_val="nosql_driver_extend_tags->'%s'" % _col,
                            #     tag_text="nosql_driver_extend_tags->>'%s'" % _col
                            # )
                            # 聚合函数只支持数字类型
                            _col = "cast(nosql_driver_extend_tags->'%s' as float)" % _col
                        elif _col_type == 'str':
                            _col = "nosql_driver_extend_tags->>'%s'" % _col
                        else:
                            _col = "nosql_driver_extend_tags->'%s'" % _col
                    else:
                        _col = "%s" % _col

                    _select.append('%s(%s) as %s' % (_op_mapping[_op], _col, _key))
                else:
                    # 是值
                    _select.append('%s(%s) as %s' % (_op_mapping[_op], '%s', _key))
                    sql_paras.append(_col)
            elif _val_type == str and _val.startswith('$'):
                # 是字段
                _col = _val[1:]
                if _col not in _fixed_cols:
                    # 非固定字段
                    _col_type = fixed_col_define.get('define', {}).get(_col, {}).get('type', 'str')
                    if _col_type == 'str':
                        _col = "nosql_driver_extend_tags->>'%s'" % _col
                    else:
                        _col = "nosql_driver_extend_tags->'%s'" % _col
                else:
                    _col = "%s" % _col

                _select.append('%s as %s' % (_col, _key))
                _groupby.append(_col)
            else:
                # 是固定值
                _select.append('%s as %s' % ('%s', _key))
                sql_paras.append(_val)

        return ','.join(_select), ','.join(_groupby)

    #############################
    # 生成SQL转换的处理函数
    #############################
    def _sqls_fun_not_support(self, op: str, *args, **kwargs):
        """
        驱动不支持的情况
        """
        raise pgadapter.NotSupportedError('psycopg not support this operation')

    def _sqls_fun_create_db(self, op: str, *args, **kwargs) -> tuple:
        """
        生成添加数据库的sql语句数组
        """
        # 获取参数
        _name = args[0]  # 数据库名
        _authorization = args[1] if len(args) > 1 else kwargs.get('authorization', None)  # schema所属用户

        _sqls = []
        _checks = []
        _sqls.append("select count(*) as db_count from information_schema.schemata where schema_name='%s'" % _name)
        _checks.append(None)

        # 组成sql
        _sql = "CREATE SCHEMA %s" % _name
        if _authorization is not None:
            _sql = "%s AUTHORIZATION %s" % (_sql, _authorization)

        _sqls.append(_sql)
        _checks.append({'pre_check': {
            'cmp_prev_return': [1, self.cmp_func_lt_value]
        }})  # 上一个语句小于1才执行

        return (_sqls, None, {'is_query': [True, False]}, _checks)

    def _sqls_fun_list_dbs(self, op: str, *args, **kwargs) -> tuple:
        """
        生成获取数据库清单的sql语句数组
        """
        _sql = "SELECT schema_name as name FROM information_schema.schemata where schema_name not like 'pg\\_%' and schema_name not like 'information\\_%' order by schema_name"
        return ([_sql], None, {'is_query': True})

    def _sqls_fun_drop_db(self, op: str, *args, **kwargs) -> tuple:
        """
        生成删除数据库的sql语句数组
        """
        _name = args[0]  # 数据库名
        _sql = "DROP SCHEMA %s CASCADE" % _name

        return ([_sql], None, {})

    def _sqls_fun_create_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成建表的sql语句数组
        """
        # 参数处理
        _collection = args[0]
        _temporary = kwargs.get('temporary', False)  # 是否临时表
        _on_commit = kwargs.get('on_commit', None)  # 指定临时表事务提交时执行的操作, None-不采取任何操作, delete-删除所有数据, drop-删除表
        _tablespace = kwargs.get('tablespace', None)  # 指定表所在的表空间

        # 创建索引的参数
        _index_concurrently = kwargs.get('index_concurrently', False)  # 启用选项后创建索引的过程中不在表上持有任何防止插入、更改、删除的写入锁
        _index_method = kwargs.get('index_method', None)  # 要使用的索引方法的名字。可选的名字是 btree(缺省), hash, gist, gin
        _index_tablespace = kwargs.get('index_tablespace', None)  # 指定索引所在的表空间

        _sqls = []

        # 生成表字段清单
        _cols = []
        if kwargs.get('fixed_col_define', None) is not None:
            for _col_name, _col_def in kwargs['fixed_col_define'].items():
                _cols.append(
                    '%s %s' % (_col_name, self._dbtype_mapping(_col_def['type'], _col_def.get('len', None)))
                )

        # 建表脚本, 需要带上数据库前缀
        _sql = 'create%s table if not exists %s.%s(_id varchar(100) PRIMARY KEY, %s nosql_driver_extend_tags JSONB)' % (
            'TEMPORARY' if _temporary else '',
            self._db_name, _collection, (', '.join(_cols) + ',') if len(_cols) > 0 else '',
        )

        # 额外参数
        if _on_commit is not None:
            _sql = '%s ON COMMIT %s' % (
                _sql, 'DROP' if _on_commit == 'drop' else ('DELETE ROWS' if _on_commit == 'delete' else 'PRESERVE ROWS')
            )
        if _tablespace is not None:
            _sql = '%s TABLESPACE %s' % (_sql, _tablespace)

        _sqls.append(_sql)

        # 建索引脚本
        if kwargs.get('indexs', None) is not None:
            for _index_name, _index_def in kwargs['indexs'].items():
                _cols = []
                for _col_name, _para in _index_def['keys'].items():
                    _cols.append('%s' % _col_name)
                _sql = 'create %sindex%s if not exists %s on %s.%s %s(%s)%s' % (
                    'UNIQUE ' if _index_def.get('paras', {}).get('unique', False) else '',
                    ' CONCURRENTLY' if _index_concurrently else '',
                    _index_name, self._db_name, _collection,
                    '' if _index_method is None else 'USING %s ' % _index_method,
                    ','.join(_cols),
                    '' if _index_tablespace is None else ' TABLESPACE %s' % _index_tablespace
                )
                _sqls.append(_sql)

        # 返回结果
        return (_sqls, None, {})

    def _sql_fun_list_collections(self, op: str, *args, **kwargs) -> tuple:
        """
        生成查询表清单的sql语句数组
        """
        _filter = kwargs.get('filter', None)
        # 生成where语句
        _sql_paras = []
        _where = self._get_filter_sql(_filter, sql_paras=_sql_paras)
        if _where is not None:
            _where = _where.replace('name ', 'tablename ', 1)

        _sql = "select tablename as name from pg_tables where schemaname = '%s'%s order by tablename" % (
            self._db_name, '' if _where is None else ' and %s' % _where
        )

        # 返回结果
        return ([_sql], None if len(_sql_paras) == 0 else [_sql_paras], {'is_query': True})

    def _sql_fun_drop_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成删除表的sql语句数组
        """
        _collection = args[0]
        _sql = "DROP TABLE IF EXISTS %s.%s CASCADE" % (self._db_name, _collection)
        return ([_sql], None, {})

    def _sql_fun_turncate_collection(self, op: str, *args, **kwargs) -> tuple:
        """
        生成清空表的sql语句数组
        """
        _collection = args[0]
        _sqls = []
        _sqls.append(
            "TRUNCATE TABLE %s.%s" % (self._db_name, _collection)
        )

        return (_sqls, None, {})

    def _sql_fun_insert_one(self, op: str, *args, **kwargs) -> tuple:
        """
        生成插入数据的sql语句数组
        """
        _collection = args[0]
        _row = args[1]
        _fixed_col_define = args[2] if len(args) > 2 else kwargs.get('fixed_col_define', {})

        # 生成插入字段和值
        _cols = ['_id']
        _sql_paras = [_row.pop('_id')]
        for _col in _fixed_col_define.get('cols', []):
            _val = _row.pop(_col, None)
            if _val is not None:
                _cols.append('%s' % _col)
                _sql_paras.append(self._python_to_dbtype(_val)[1])

        # 剩余的内容放入扩展字段
        _cols.append('nosql_driver_extend_tags')
        _sql_paras.append(self._python_to_dbtype(_row)[1])

        # 组成sql
        _sql = 'insert into %s.%s(%s) values(%s)' % (
            self._db_name, _collection, ','.join(_cols), ','.join(['%s' for _tcol in _cols])
        )

        return ([_sql], [_sql_paras], {})

    def _sql_fun_update(self, op: str, *args, **kwargs) -> tuple:
        """
        生成更新数据的sql语句数组
        """
        # 获取参数
        _collection = args[0]
        _filter = args[1]
        _update = args[2]
        _fixed_col_define = kwargs.get('fixed_col_define', None)

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

        _sql_collection = '%s.%s' % (self._db_name, _collection)
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

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras
        )

        _sql_paras = None
        _sql_collection = '%s.%s' % (self._db_name, _collection)
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
                _sort, fixed_col_define=_fixed_col_define, sql_paras=_sort_sql_paras
            )

        # 处理projection语句
        _projection_sql_paras = []
        _projection_sql = self._get_projection_sql(
            _projection, fixed_col_define=_fixed_col_define, sql_paras=_projection_sql_paras
        )

        # 查询表
        _tab = '%s.%s' % (self._db_name, _collection)

        # 组装语句
        _sql_paras = []
        _sql = 'select %s from %s' % (_projection_sql, _tab)
        _sql_paras.extend(_projection_sql_paras)

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
                _sql = '%s %s' % (_sql, 'offset %d' % _skip)

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

        # 处理where条件语句
        _where_sql_paras = []
        _where_sql = self._get_filter_sql(
            _filter, fixed_col_define=_fixed_col_define, sql_paras=_where_sql_paras
        )

        # 查询表名
        _tab = '%s.%s' % (self._db_name, _collection)

        # 组装语句
        if _limit is not None or _skip is not None:
            # 有获取数据区间, 只能采用性能差的子查询模式
            _sql_paras = []
            _sql = 'select 1 from %s' % _tab
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
                    _sql = '%s %s' % (_sql, 'offset %d' % _skip)

            # 外面封装一层查询
            _sql = 'select count(*) from (%s) t' % _sql
        else:
            _sql_paras = []
            _sql = 'select count(*) from %s' % _tab

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

        # 查询表名
        _tab = '%s.%s' % (self._db_name, _collection)

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

        if _sort_sql is not None:
            # 有排序, 需要包装多一层
            _sql = 'select %s from (%s) t' % (_projection_sql, _sql)
            _sql = '%s order by %s' % (_sql, _sort_sql)

        # 返回结果
        return ([_sql], None if len(_sql_paras) == 0 else [_sql_paras], {'is_query': True})


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # "test \'单引号\' \\"双引号\\", 反斜杠\\\\, 回车:\\r, 换行:\\n, tab:\\t new"
    _str = 'test \'单引号\' "双引号", 反斜杠\\, 回车:\r, 换行:\n, tab:\t'
    _str = _str.replace('\\', '\\\\').replace('\r', '\\r').replace('\n', '\\n').replace("'", "\\'").replace('"', '\\"')
    print(_str)
