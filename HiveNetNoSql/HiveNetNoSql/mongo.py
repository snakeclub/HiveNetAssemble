#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
MongoDB的HiveNetNoSql实现模块

@module mongo
@file mongo.py
"""
import os
import sys
import copy
import logging
from bson import ObjectId
from typing import Any, Union
from urllib.parse import quote_plus
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.run_tool import AsyncTools
# 自动安装依赖库
from HiveNetCore.utils.pyenv_tool import PythonEnvTools
process_install_motor = False
while True:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from pymongo import IndexModel, ASCENDING, DESCENDING
        break
    except ImportError:
        if process_install_motor:
            break
        else:
            PythonEnvTools.install_package('motor')
            process_install_motor = True
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetNoSql.base.driver_fw import NosqlDriverFW


class MongoNosqlDriver(NosqlDriverFW):
    """
    nosql数据库Mongodb驱动
    注: MongoDB 4.0+ 才能支持事务, 并且单个mongodb server 不支持事务
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, connect_config: dict = {}, pool_config: dict = {}, driver_config: dict = {}):
        """
        初始化驱动

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 连接数据库的ip或uri, 如果使用uri方式, 其他的连接参数不生效
                推荐使用uri的方式, uri的参考示例如下:
                无验证连接: mongodb://localhost:27017/dbname
                验证用户密码: mongodb://name:pass@localhost:27017/dbname
                注意: 如果用户名密码包含“:”或“@”需要通过urllib.parse.quote_plus函数进行编码后传入
            port {int} - 连接数据库的端口(可选)
            usedb {str} - 登录后默认切换到的数据库(可选), 如果不传使用登录后的默认数据库
            username {str} - 登录验证用户(可选)
            password {str} - 登录验证密码(可选)
            dbname {str} - 登录用户的数据库名(可选)
                注意: mongodb每个用户都归属指定的数据库, 因此必须与登录的用户名密码匹配, 否则会出现权限错误
            connect_on_init {bool} - 是否启动时直接连接数据库, 默认为False(等待第一次操作再连接)
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            pymongo.MongoClient 支持的其他参数...
        @param {dict} pool_config={} - 连接池配置
            max_size {int} - 连接池的最大大小, 默认为100
            min_size {int} - 连接池维持的最小连接数量, 默认为0
            max_idle_time {float} - 连接被移除前的最大空闲时间, 单位为秒, 默认为None
            wait_queue_timeout {float} - 在没有空闲连接的时候, 请求连接所等待的超时时间, 单位为秒, 默认为None(不超时)
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
        """
        # 参数处理
        self._driver_config = copy.deepcopy(driver_config)
        self._logger = driver_config.get('logger', None)
        if self._logger is None:
            logging.basicConfig()
            self._logger = logging.getLogger(__name__)

        # 生成连接uri
        self._db_uri = connect_config.get('host', 'localhost')
        if not self._db_uri.startswith('mongodb://'):
            # 需要程序生成uri
            if connect_config.get('username', None) is None:
                self._db_uri = 'mongodb://%s:%d/%s' % (
                    connect_config.get('host', 'localhost'),
                    connect_config.get('port', 27017),
                    connect_config.get('dbname', 'local'),
                )
            else:
                # 带密码模式
                self._db_uri = 'mongodb://%s:%s@%s:%d/%s' % (
                    quote_plus(connect_config['username']), quote_plus(connect_config['password']),
                    connect_config.get('host', 'localhost'),
                    connect_config.get('port', 27017),
                    connect_config.get('dbname', 'local'),
                )

        # 处理MongoClient的其他入参
        _client_paras = copy.deepcopy(connect_config)
        _client_paras['host'] = self._db_uri
        _client_paras['connect'] = connect_config.get('connect_on_init', False)
        if connect_config.get('connect_timeout', None) is not None:
            _client_paras['connectTimeoutMS'] = connect_config['connect_timeout'] * 1000
        # 移除不使用的参数
        for _pop_item in ('port', 'usedb', 'dbname', 'username', 'password', 'connect_on_init', 'connect_timeout'):
            _client_paras.pop(_pop_item, None)

        # 添加连接池的配置
        _client_paras['maxPoolSize'] = pool_config.get('max_size', 100)
        _client_paras['minPoolSize'] = pool_config.get('min_size', 0)
        if pool_config.get('max_idle_time', None) is None:
            _client_paras['maxIdleTimeMS'] = None
        else:
            _client_paras['maxIdleTimeMS'] = pool_config['max_idle_time'] * 1000

        if pool_config.get('wait_queue_timeout', None) is None:
            _client_paras['waitQueueTimeoutMS'] = None
        else:
            _client_paras['waitQueueTimeoutMS'] = pool_config['wait_queue_timeout'] * 1000

        # 创建数据库连接
        self._client = AsyncIOMotorClient(**_client_paras)

        # 切换当前数据库
        if connect_config.get('usedb', None) is None:
            self._db = self._client.get_default_database()
        else:
            self._db = self._client.get_database(name=connect_config['usedb'])

        # 启动后创建数据库
        if self._driver_config.get('init_yaml_file', None) is None:
            _init_db = self._driver_config.get('init_db', {})
            _init_collections = self._driver_config.get('init_collections', {})
        else:
            _init_yaml = SimpleYaml(
                self._driver_config['init_yaml_file'], obj_type=EnumYamlObjType.File,
                encoding='utf-8'
            )
            _init_db = _init_yaml.get_value('init_db', default={})
            if _init_db is None:
                _init_db = {}
            _init_collections = _init_yaml.get_value('init_collections', default={})
            if _init_collections is None:
                _init_collections = {}

        _temp_db_name = self._db.name
        for _name, _db_info in _init_db.items():
            if _db_info.get('index_only', False):
                # 只索引不创建
                continue

            # 创建数据库
            AsyncTools.sync_run_coroutine(
                self.create_db(_name, *_db_info.get('args', []), **_db_info.get('kwargs', {}))
            )

        # 切换回默认数据库
        AsyncTools.sync_run_coroutine(self.switch_db(_temp_db_name))

        # 启动驱动时创建集合(表)
        AsyncTools.sync_run_coroutine(
            self._init_collections(_init_collections)
        )

    #############################
    # 主动销毁驱动
    #############################
    async def destroy(self):
        """
        主动销毁驱动(连接)
        """
        self._client.close()

    #############################
    # 通用属性
    #############################
    @property
    def db_name(self):
        """
        返回当前数据库名
        @property {str}
        """
        return self._db.name

    #############################
    # 数据库操作
    #############################
    async def create_db(self, name: str, *args, **kwargs):
        """
        创建数据库
        注: 创建后会自动切换到该数据库

        @param {str} name - 数据库名
        """
        await self.switch_db(name)

    async def switch_db(self, name: str, *args, **kwargs):
        """
        切换当前数据库到指定数据库

        @param {str} name - 数据库名
        """
        self._db = self._client.get_database(name=name)

    async def list_dbs(self, *args, **kwargs) -> list:
        """
        列出数据库清单

        @returns {list} - 数据库名清单
        """
        _result = await self._client.list_database_names()
        return _result

    async def drop_db(self, name: str, *args, **kwargs):
        """
        删除数据库

        @param {str} name - 数据库名
        """
        _current_db = self._db.name
        await self._client.drop_database(name)

        # 切换后判断是不是删除当前数据库
        if _current_db == name:
            _dbs = await self.list_dbs()
            if len(_dbs) > 0:
                await self.switch_db(_dbs[0])

    #############################
    # 集合操作
    #############################
    async def create_collection(self, collection: str, indexs: dict = None, fixed_col_define: dict = None,
            comment: str = None, **kwargs):
        """
        创建集合(相当于关系型数据库的表, 如果不存在则创建)
        注意: 所有集合都有必须有 '_id' 这个记录的唯一主键字段

        @param {str} collection - 集合名(表名)
        @param {dict} indexs=None - 要创建的索引字典, 格式为:
            {
                '索引名': {
                    # 索引的字段清单
                    'keys': {
                        '字段名': { 'asc': 是否升序(1为升序, -1为降序) },
                        ...
                    }
                    # 创建参数
                    'paras': {
                        'unique': 是否唯一索引(True/False),
                        ...MongoDB支持的其他索引参数
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

        @throws {CollectionInvalid} - 当集合已存在将抛出该异常
        """
        # 创建集合
        _collection = await self._db.create_collection(collection)

        # 创建索引
        if indexs is not None:
            _indexs = []
            for _name, _config in indexs.items():
                # 组装索引字段
                _keys = []
                for _key_name, _key_para in _config['keys'].items():
                    _keys.append((
                        _key_name, ASCENDING if _key_para.get('asc', 1) == 1 else DESCENDING
                    ))

                # 组装命令
                _kwargs = {'name': _name}
                _kwargs.update(_config.get('paras', {}))

                # 放入清单
                _indexs.append(IndexModel(_keys, **_kwargs))

            # 创建索引
            if len(_indexs) > 0:
                await _collection.create_indexes(_indexs)

    async def list_collections(self, filter: dict = None, **kwargs) -> list:
        r"""
        获取所有集合(表)清单

        @param {dict} filter=None - 查找条件
            例如查找所有非'system.'开头的集合: {"name": {"$regex": r"^(?!system\.)"}}

        @returns {list} - 集合(表)清单
        """
        return await self._db.list_collection_names(filter=filter)

    async def drop_collection(self, collection: str, *args, **kwargs):
        """
        删除集合
        注: 集合不存在也正常返回

        @param {str} collection - 集合名(表名)
        """
        await self._db.drop_collection(collection)

    async def turncate_collection(self, collection: str, *args, **kwargs):
        """
        清空集合记录

        @param {str} collection - 集合名(表名)
        """
        await self._db.get_collection(collection).delete_many({})

    async def collections_exists(self, collection: str, *args, **kwargs) -> bool:
        """
        判断集合(表)是否存在

        @param {str} collection - 集合名(表名)

        @returns {bool} - 是否存在
        """
        _list = await self.list_collections(filter={'name': collection})
        return len(_list) > 0

    #############################
    # 事务支持
    # 注: MongoDB 4.0+ 才能支持事务, 并且单个mongodb server 不支持事务
    #############################
    async def start_transaction(self, *args, **kwargs) -> Any:
        """
        启动事务
        注: 通过该方法处理事务, 必须显式通过commit_transaction或abort_transaction关闭事务

        @returns {Any} - 返回事务所在的连接(session)
        """
        _session = await self._client.start_session()
        _session.start_transaction()
        return _session

    async def commit_transaction(self, session, *args, **kwargs):
        """
        提交事务

        @param {Any} session=None - 启动事务的连接(session)
        """
        # 提交事务
        await session.commit_transaction()
        # 关闭session
        await session.end_session()

    async def abort_transaction(self, session, *args, **kwargs):
        """
        回滚事务

        @param {Any} session=None - 启动事务的连接(session)
        """
        # 回滚事务
        await session.abort_transaction()
        # 关闭session
        await session.end_session()

    #############################
    # 数据操作
    #############################
    async def insert_one(self, collection: str, row: dict, session: Any = None, **kwargs) -> str:
        """
        插入一条记录

        @param {str} collection - 集合(表)
        @param {dict} row - 行记录字典
            注: 每个记录可以通过'_id'字段指定该记录的唯一主键, 如果不送入, 将自动生成一个唯一主键
        @param {Any} session=None - 指定事务连接对象

        @returns {str} - 返回所插入记录的 _id 字段值
        """
        _result = await self._db.get_collection(collection).insert_one(row, session=session)
        return str(_result.inserted_id)

    async def insert_many(self, collection: str, rows: list, session: Any = None, **kwargs) -> int:
        """
        插入多条记录

        @param {str} collection - 集合(表)
        @param {list} rows - 行记录数组
            注: 每个记录可以通过'_id'字段指定该记录的唯一主键, 如果不送入, 将自动生成一个唯一主键
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 返回插入的记录数量
        """
        _result = await self._db.get_collection(collection).insert_many(rows, session=session)
        return len(_result.inserted_ids)

    async def update(self, collection: str, filter: dict, update: dict, multi: bool = True,
             upsert: bool = False, hint: dict = None, session: Any = None, **kwargs) -> int:
        """
        更新找到的记录

        @param {str} collection - 集合(表)
        @param {dict} filter - 查询条件字典, 与mongodb的查询条件设置参数一致
        @param {dict} update - 更新信息字典, 与mongodb的更新设置参数一致, 参考如下:
            {'$set': {'name': 'myname', ...}}: name='myname', 设置某个字段的值
            {'$inc': {'age': 3, ...}} : age = age + 3, 对数字类型字段, 在现有值上增加指定数值
            {'$mul': {'age': 2, ...}} : age = age * 2, 对数字类型字段, 在现有值上乘以指定数值
            {'$min': {'age': 10, ...}} : age = min(age, 10), 将现有值和给出值比较, 设置为小的值
            {'$max': {'age': 10, ...}} : age = max(age, 10), 将现有值和给出值比较, 设置为大的值
            {'$unset': {'job': 1}}: job=null, 删除指定字段
            {'$rename': {'old_name': 'new_name', ...}}: 将字段名修改为新字段名
        @param {bool} multi=True - 是否更新全部找到的记录, 如果为Fasle只更新找到的第一条记录
        @param {bool} upsert=False - 指定如果记录不存在是否插入
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 返回更新的数据条数
        """
        _filter = filter
        self._std_filter(_filter)  # 标准化filter字典
        if _filter is None:
            _filter = {}

        if multi:
            # 更新全部记录
            _result = await self._db.get_collection(collection).update_many(
                _filter, update, upsert=upsert, hint=hint, session=session
            )
        else:
            # 更新单个记录
            _result = await self._db.get_collection(collection).update_one(
                _filter, update, upsert=upsert, hint=hint, session=session
            )

        return _result.modified_count

    async def delete(self, collection: str, filter: dict, multi: bool = True,
            hint: dict = None, session: Any = None, **kwargs) -> int:
        """
        删除指定记录

        @param {str} collection - 集合(表)
        @param {dict} filter - 查询条件字典, 与mongodb的查询条件设置参数一致
        @param {bool} multi=True - 是否更新全部找到的记录, 如果为Fasle只更新找到的第一条记录
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 删除记录数量
        """
        self._std_filter(filter)  # 标准化filter字典
        if multi:
            # 删除全部记录
            _result = await self._db.get_collection(collection).delete_many(
                filter, hint=hint, session=session
            )
        else:
            # 仅删除第一个记录
            _result = await self._db.get_collection(collection).delete_one(
                filter, hint=hint, session=session
            )

        return _result.deleted_count

    #############################
    # 数据查询
    #############################
    async def query_list(self, collection: str, filter: dict = None, projection: Union[dict, list] = None,
            sort: list = None, skip: int = None, limit: int = None, hint: dict = None,
            session: Any = None, **kwargs) -> list:
        """
        查询记录(直接返回清单)

        @param {str} collection - 集合(表)
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样, 参考如下:
            {} : 查询全部记录
            {'id': 'info', 'ver': '0.0.1'} : where id = 'info' and 'ver' = '0.0.1'
            {'ver': {'$lt': '0.0.1'}} : where ver < '0.0.1'
                注: $lt - 小于, $lte - 小于或等于, $gt - 大于, $gte - 大于或等于, $ne - 不等于
            {'id': {'$gt':50}, '$or': [{'name': 'lhj'},{'title': 'book'}]} :
                where id > 50 and (name='lhj' or 'title' = 'book')
            {'name': {'$regex': 'likestr'}} : where name like '%likestr%', 正则表达式
        @param {dict|list} projection=None - 指定结果返回的字段信息
            列表模式: ['col1','col2', ...]  注意: 该模式一定会返回 _id 这个主键
            字典模式: {'_id': False, 'col1': True, ...}  该方式可以通过设置False屏蔽 _id 的返回
                注意: 只有 _id 字段可以设置为False, 其他字段不可设置为False(如果要屏蔽可以不放入字典)
        @param {list} sort=None - 查询结果的排序方式
            例: [('col1', 1), ...]  注: 参数的第2个值指定是否升序(1为升序, -1为降序)
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
            例: {'index_name1': 1, 'index_name2': 1}
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 返回的结果列表
        """
        self._std_filter(filter)  # 标准化filter字典
        _kwargs = {}
        if skip is not None:
            _kwargs['skip'] = skip
        if limit is not None:
            _kwargs['limit'] = limit
        if hint is not None:
            _kwargs['hint'] = hint

        _cursor = self._db.get_collection(collection).find(
            filter=filter, projection=projection, sort=sort, session=session, **_kwargs
        )
        return await _cursor.to_list(None)

    async def query_iter(self, collection: str, filter: dict = None, projection: Union[dict, list] = None,
            sort: list = None, skip: int = None, limit: int = None, hint: dict = None, fetch_each: int = 1,
            session: Any = None, **kwargs):
        """
        查询记录(通过迭代对象依次返回)

        @param {str} collection - 集合(表)
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样, 参考如下:
            {} : 查询全部记录
            {'id': 'info', 'ver': '0.0.1'} : where id = 'info' and 'ver' = '0.0.1'
            {'ver': {$lt: '0.0.1'}} : where ver < '0.0.1'
                注: $lt - 小于, $lte - 小于或等于, $gt - 大于, $gte - 大于或等于, $ne - 不等于
            {'id': {$gt:50}, $or: [{'name': 'lhj'},{'title': 'book'}]} :
                where id > 50 and (name='lhj' or 'title' = 'book')
            {'name': {'$regex': 'likestr'}} : where name like '%likestr%', 正则表达式
        @param {dict|list} projection=None - 指定结果返回的字段信息
            列表模式: ['col1','col2', ...]  注意: 该模式一定会返回 _id 这个主键
            字典模式: {'_id': False, 'col1': True, ...}  该方式可以通过设置False屏蔽 _id 的返回
        @param {list} sort=None - 查询结果的排序方式
            例: [('col1', 1), ...]  注: 参数的第2个值指定是否升序(1为升序, -1为降序)
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
            例: {'index_name1': 1, 'index_name2': 1}
        @param {int} fetch_each=1 - 每次获取返回的记录数量
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 返回的结果列表
        """
        self._std_filter(filter)  # 标准化filter字典
        _kwargs = {}
        if skip is not None:
            _kwargs['skip'] = skip
        if limit is not None:
            _kwargs['limit'] = limit
        if hint is not None:
            _kwargs['hint'] = hint

        _cursor = self._db.get_collection(collection).find(
            filter=filter, projection=projection, sort=sort, session=session, **_kwargs
        )
        _fetchs = await _cursor.to_list(fetch_each)
        while _fetchs:
            # 返回当次结果
            yield _fetchs

            # 返回下一次结果
            _fetchs = await _cursor.to_list(fetch_each)

    async def query_count(self, collection: str, filter: dict = None,
            skip: int = None, limit: int = None, hint: dict = None, overtime: float = None,
            session: Any = None, **kwargs) -> int:
        """
        获取匹配查询条件的结果数量

        @param {str} collection - 集合(表)
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样,
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {float} overtime=None - 指定操作的超时时间, 单位为秒
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 返回查询条件匹配的记录数
        """
        self._std_filter(filter)  # 标准化filter字典
        _kwargs = {}
        if skip is not None:
            _kwargs['skip'] = skip
        if limit is not None:
            _kwargs['limit'] = limit
        if hint is not None:
            _kwargs['hint'] = hint
        if overtime is not None:
            _kwargs['maxTimeMS'] = overtime * 1000

        return await self._db.get_collection(collection).count_documents(
            {} if filter is None else filter, session=session, **_kwargs
        )

    async def query_group_by(self, collection: str, group: dict = None, filter: dict = None,
            projection: Union[dict, list] = None, sort: list = None,
            overtime: float = None, session: Any = None, **kwargs) -> list:
        """
        获取记录聚合统计的结果

        @param {str} collection - 集合(表)
        @param {dict} group=None - 分组返回设置字典(注意与mongodb的_id要求有所区别)
            指定分组字段为col1、col2, 聚合字段为count、pay_amt, 其中pay_amt统计col_pay字段的合计数值
            {'id': '$col1', 'name': '$col2', 'count': {'$sum': 1}, 'pay_amt': {'$sum': '$col_pay'}}
            常见的聚合类型: $sum-计算总和, $avg-计算平均值, $min-取最小值, $max-取最大值, $first-取第一条, $last-取最后一条
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样
        @param {dict|list} projection=None - 指定结果返回的字段信息(指统计后的结果)
        @param {list} sort=None - 查询结果的排序方式(注意排序字段为返回结果的分组字段, 而不是表的原始字段)
        @param {float} overtime=None - 指定操作的超时时间, 单位为秒
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 返回结果列表
        """
        self._std_filter(filter)  # 标准化filter字典

        # 处理group的值, 适配mongodb聚合分组必须为_id字段的要求
        _group = copy.deepcopy(group)
        _deal_group = False
        if '_id' not in _group.keys():
            _deal_group = True
            _group['_id'] = {}
            for _key, _item in group.items():
                if type(_item) == str:
                    # 是分组条件
                    _group.pop(_key, None)
                    _group['_id'][_key] = _item

        # 处理完整的字段清单
        _full_projection = {}
        for _key, _val in group.items():
            if type(_val) == str:
                # 是分组条件
                _full_projection[_key] = '$_id.%s' % _key
            else:
                _full_projection[_key] = True

        # 处理排序
        _sort = {}
        if sort is not None:
            for _item in sort:
                _sort[_item[0]] = _item[1]

        _pipeline = []  # 组装执行的管道
        # 过滤条件
        if filter is not None:
            _pipeline.append({'$match': filter})

        # group
        _pipeline.append({'$group': _group})

        # 指定完整的返回字段
        _pipeline.append({'$project': _full_projection})

        # 对结果排序
        if len(_sort) > 0:
            _pipeline.append({'$sort': _sort})

        # 指定返回字段
        if projection is not None:
            # 标准化
            _projection = projection
            if type(projection) != dict:
                _projection = {}
                for _item in projection:
                    _projection[_item] = True
            _pipeline.append({'$project': _projection})

        # 其他运行参数
        _kwargs = {}
        if overtime is not None:
            _kwargs['maxTimeMS'] = overtime * 1000

        # 执行聚合操作
        _ret_list = []
        _cursor = self._db.get_collection(collection).aggregate(
            _pipeline, session=session, **_kwargs
        )
        # 逐个返回值处理 _id 的分组字典
        async for _doc in _cursor:
            if _deal_group and type(_doc['_id']) == dict:
                _doc.pop('_id', {})
            _ret_list.append(_doc)

        return _ret_list

    #############################
    # 原生命令执行
    #############################
    async def run_native_cmd(self, *args, **kwargs):
        """
        执行原生命令(或SQL)并返回执行结果
        注: 该函数不支持驱动的兼容处理, 当前函数直接执行执行的是motor的db.command函数
        """
        return await self._db.command(*args, **kwargs)

    #############################
    # 初始化集合
    #############################
    async def _init_collections(self, init_configs: dict):
        """
        启动驱动时创建的集合(表)

        @param {dict} init_configs - 初始化参数, 在构造函数中传入
        """
        # 记录开始时的数据库名
        _temp_name = self._db.name

        # 遍历数据库创建
        for _db_name, _collections in init_configs.items():
            if self._db.name != _db_name:
                # 切换到指定数据库
                await self.switch_db(_db_name)

            # 遍历表进行创建处理
            for _collection, _info in _collections.items():
                if _info.get('index_only', True):
                    # 只用于索引, 不创建
                    continue

                if await self.collections_exists(_collection):
                    # 表已存在
                    continue

                # 建表操作
                await self.create_collection(
                    _collection, indexs=_info.get('indexs', None),
                    fixed_col_define=_info.get('fixed_col_define', None),
                    comment=_info.get('comment', None)
                )

        # 切换回开始的数据库
        await self.switch_db(_temp_name)

    def _std_filter(self, filter: dict):
        """
        标准化查询条件

        @param {dict} filter - 查询条件字典
        """
        if filter is None:
            return

        _id = filter.get('_id', None)
        if _id is not None and type(_id) == str:
            # 需要转换为ObjectId
            filter['_id'] = ObjectId(_id)
