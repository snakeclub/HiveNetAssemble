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
            left_join: list = None,
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
            {'name': {'$in': ['a', 'b', 'c']}} : where name in ('a', 'b', 'c')
            {'name': {'$nin': ['a', 'b', 'c']}} : where name not in ('a', 'b', 'c')
            {'col_json.sub_col': 'test'}: 查询json字段的指定字典key, 可以支持多级
            {'col_json.0': 'test'}: 查询json字段的指定数组索引, 可以支持多级
            注: 如果条件中涉及_id字段, 应传入ObjectId对象, 例如传入ObjectId('...')
            注: 可以在字段名前面加 "#序号." 用于与left_join参数配合使用, 指定当前排序字段所属的关联表索引(序号从0开始)
        @param {dict|list} projection=None - 指定结果返回的字段信息
            列表模式: ['col1','col2', ...]  注意: 该模式一定会返回 _id 这个主键
            字典模式: {'_id': False, 'col1': True, ...}  该方式可以通过设置False屏蔽 _id 的返回
                注1: 只有 _id 字段可以设置为False, 其他字段不可设置为False(如果要屏蔽可以不放入字典)
                注2: 可以通过字典模式的值设置为$开头的字段名或json检索路径的方式, 进行字段别名处理, 例如{'as_name': '$real_name'}或{'as_name': '$real_name.key.key'}
                注3: 可以在字段名前面加 "#序号." 用于与left_join参数配合使用, 指定当前排序字段所属的关联表索引(序号从0开始), 例如{'#0.col1': True, 'as_name': '$#0.col2'}
                注4: mongo的别名形式, 不支持数组索引
        @param {list} sort=None - 查询结果的排序方式
            例: [('col1', 1), ...]  注: 参数的第2个值指定是否升序(1为升序, -1为降序)
            注1: 参数的第1个值可以支持'col1.key1'的方式指定json值进行排序
            注2: 参数的第2个值指定是否升序(1为升序, -1为降序)
            注3: 可以在字段名前面加 "#序号." 用于与left_join参数配合使用, 指定当前排序字段所属的关联表索引(序号从0开始)
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
            例: {'index_name1': 1, 'index_name2': 1}
        @param {list} left_join=None - 指定左关联(left outer join)集合信息, 每个数组为一个关联表, 格式如下:
            [
                {
                    'db_name': '指定集合的db',  # 如果不设置则代表和主表是同一个数据库
                    'collection': '要关联的集合(表)名',
                    'as': '关联后的别名',  # 如果不设置默认为集合名
                    'join_fields': [(主表字段名, 关联表字段名), ...],  # 要关联的字段列表, 仅支持完全相等的关联条件
                    'filter': ..., # 关联表数据的过滤条件(仅用于内部过滤需要关联的数据), 注意字段无需添加集合的别名
                },
                ...
            ]
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 返回的结果列表
        """
        if left_join is None:
            # 单集合查询, 使用find函数处理
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
        else:
            # 联合查询, 使用聚合管道aggregate方式执行
            _kwargs = {
                'allowDiskUse': True
            }  # 聚合管道运行参数
            if hint is not None:
                _kwargs['hint'] = hint

            _pipeline = self._get_left_join_aggregate(
                filter=filter, projection=projection, sort=sort, skip=skip, limit=limit,
                hint=hint, left_join=left_join
            )

            # 执行管道
            _cursor = self._db.get_collection(collection).aggregate(
                _pipeline, session=session, **_kwargs
            )
            _ret = await _cursor.to_list(None)
            return self._std_left_join_result(_ret, left_join=left_join)

    async def query_iter(self, collection: str, filter: dict = None, projection: Union[dict, list] = None,
            sort: list = None, skip: int = None, limit: int = None, hint: dict = None,
            left_join: list = None, fetch_each: int = 1,
            session: Any = None, **kwargs):
        """
        查询记录(通过迭代对象依次返回)

        @param {str} collection - 集合(表)
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样, 参考如下:
            {} : 查询全部记录
            {'id': 'info', 'ver': '0.0.1'} : where id = 'info' and 'ver' = '0.0.1'
            {'ver': {'$lt': '0.0.1'}} : where ver < '0.0.1'
                注: $lt - 小于, $lte - 小于或等于, $gt - 大于, $gte - 大于或等于, $ne - 不等于
            {'id': {'$gt':50}, '$or': [{'name': 'lhj'},{'title': 'book'}]} :
                where id > 50 and (name='lhj' or 'title' = 'book')
            {'name': {'$regex': 'likestr'}} : where name like '%likestr%', 正则表达式
            {'name': {'$in': ['a', 'b', 'c']}} : where name in ('a', 'b', 'c')
            {'name': {'$nin': ['a', 'b', 'c']}} : where name not in ('a', 'b', 'c')
            {'col_json.sub_col': 'test'}: 查询json字段的指定字典key, 可以支持多级
            {'col_json.0': 'test'}: 查询json字段的指定数组索引, 可以支持多级
            注: 如果条件中涉及_id字段, 应传入ObjectId对象, 例如传入ObjectId('...')
            注: 可以在字段名前面加 "#序号." 用于与left_join参数配合使用, 指定当前排序字段所属的关联表索引(序号从0开始)
        @param {dict|list} projection=None - 指定结果返回的字段信息
            列表模式: ['col1','col2', ...]  注意: 该模式一定会返回 _id 这个主键
            字典模式: {'_id': False, 'col1': True, ...}  该方式可以通过设置False屏蔽 _id 的返回
                注1: 只有 _id 字段可以设置为False, 其他字段不可设置为False(如果要屏蔽可以不放入字典)
                注2: 可以通过字典模式的值设置为$开头的字段名或json检索路径的方式, 进行字段别名处理, 例如{'as_name': '$real_name'}或{'as_name': '$real_name.key.key'}
                注3: 可以在字段名前面加 "#序号." 用于与left_join参数配合使用, 指定当前排序字段所属的关联表索引(序号从0开始), 例如{'#0.col1': True, 'as_name': '$#0.col2'}
                注4: mongo的别名形式, 不支持数组索引
        @param {list} sort=None - 查询结果的排序方式
            例: [('col1', 1), ...]  注: 参数的第2个值指定是否升序(1为升序, -1为降序)
            注1: 参数的第1个值可以支持'col1.key1'的方式指定json值进行排序
            注2: 参数的第2个值指定是否升序(1为升序, -1为降序)
            注3: 可以在字段名前面加 "#序号." 用于与left_join参数配合使用, 指定当前排序字段所属的关联表索引(序号从0开始)
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
            例: {'index_name1': 1, 'index_name2': 1}
        @param {list} left_join=None - 指定左关联(left outer join)集合信息, 每个数组为一个关联表, 格式如下:
            [
                {
                    'db_name': '指定集合的db',  # 如果不设置则代表和主表是同一个数据库
                    'collection': '要关联的集合(表)名',
                    'as': '关联后的别名',  # 如果不设置默认为集合名
                    'join_fields': [(主表字段名, 关联表字段名), ...],  # 要关联的字段列表, 仅支持完全相等的关联条件
                    'filter': ..., # 关联表数据的过滤条件(仅用于内部过滤需要关联的数据), 注意字段无需添加集合的别名
                },
                ...
            ]
        @param {int} fetch_each=1 - 每次获取返回的记录数量
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 返回的结果列表
        """
        if left_join is None:
            # 单集合查询, 使用find函数处理
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
        else:
            # 联合查询, 使用聚合管道aggregate方式执行
            _kwargs = {
                'allowDiskUse': True
            }  # 聚合管道运行参数
            if hint is not None:
                _kwargs['hint'] = hint

            _pipeline = self._get_left_join_aggregate(
                filter=filter, projection=projection, sort=sort, skip=skip, limit=limit,
                hint=hint, left_join=left_join
            )

            # 执行管道
            _cursor = self._db.get_collection(collection).aggregate(
                _pipeline, session=session, **_kwargs
            )

            _fetchs = await _cursor.to_list(fetch_each)
            while _fetchs:
                # 返回当次结果
                yield self._std_left_join_result(_fetchs, left_join=left_join)

                # 返回下一次结果
                _fetchs = await _cursor.to_list(fetch_each)

    async def query_count(self, collection: str, filter: dict = None,
            skip: int = None, limit: int = None, hint: dict = None, left_join: list = None,
            overtime: float = None,
            session: Any = None, **kwargs) -> int:
        """
        获取匹配查询条件的结果数量

        @param {str} collection - 集合(表)
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样,
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {list} left_join=None - 指定左关联(left outer join)集合信息, 每个数组为一个关联表, 格式如下:
            [
                {
                    'db_name': '指定集合的db',  # 如果不设置则代表和主表是同一个数据库
                    'collection': '要关联的集合(表)名',
                    'as': '关联后的别名',  # 如果不设置默认为集合名
                    'join_fields': [(主表字段名, 关联表字段名), ...],  # 要关联的字段列表, 仅支持完全相等的关联条件
                    'filter': ..., # 关联表数据的过滤条件(仅用于内部过滤需要关联的数据), 注意字段无需添加集合的别名
                },
                ...
            ]
        @param {float} overtime=None - 指定操作的超时时间, 单位为秒
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 返回查询条件匹配的记录数
        """
        if left_join is None:
            # 单集合查询, 使用count_documents函数处理
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
        else:
            # 联合查询, 使用聚合管道aggregate方式执行
            _kwargs = {
                'allowDiskUse': True
            }  # 聚合管道运行参数
            if overtime is not None:
                _kwargs['maxTimeMS'] = overtime * 1000
            if hint is not None:
                _kwargs['hint'] = hint

            _pipeline = self._get_left_join_aggregate(
                filter=filter, projection=None, sort=None, skip=skip, limit=limit,
                hint=hint, left_join=left_join
            )

            # 统计文档数量
            _pipeline.append({'$count': 'docs_count'})

            # 执行管道
            _cursor = self._db.get_collection(collection).aggregate(
                _pipeline, session=session, **_kwargs
            )
            _ret = await _cursor.to_list(None)
            return _ret[0]['docs_count']

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
            if not isinstance(projection, dict):
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
            if _deal_group and isinstance(_doc['_id'], dict):
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
            return filter

        _id = filter.get('_id', None)
        if _id is not None:
            _type = type(_id)
            if _type == str:
                # 需要转换为ObjectId
                filter['_id'] = ObjectId(_id)
            elif isinstance(_id, dict):
                if filter['_id'].get('$in', None) is not None:
                    filter['_id']['$in'] = [ObjectId(_temp_id) for _temp_id in filter['_id']['$in']]

                if filter['_id'].get('$nin', None) is not None:
                    filter['_id']['$nin'] = [ObjectId(_temp_id) for _temp_id in filter['_id']['$nin']]

        return filter

    def _split_filter(self, filter: dict, left_join: list) -> tuple:
        """
        分离主表和关联表的过滤条件

        @param {dict} filter - 过滤条件
        @param {list} left_join - 指定左关联(left outer join)集合信息

        @returns {tuple} - (主表过滤条件, 关联表过滤条件)
        """
        if filter is None:
            return {}, {}

        _main_filter = {}
        _join_filter = {}
        for _key, _val in filter.items():
            _is_join, _std_key, _std_val = self._check_and_std_filter(_key, _val, left_join)
            if _is_join:
                # 是关联表
                _join_filter[_std_key] = _std_val
            else:
                _main_filter[_std_key] = _std_val

        return _main_filter, _join_filter

    def _check_and_std_filter(self, filter_key: str, filter_val, left_join: list,
            upper_ret: bool = False) -> tuple:
        """
        检查过滤条件是否关联表条件, 以及进行过滤条件的标准化处理

        @param {str} filter_key - 过滤条件的key
        @param {Any} filter_val - 过滤条件的值
        @param {list} left_join - 指定左关联(left outer join)集合信息
        @param {bool} upper_ret=False - 上级的检查结果

        @returns {tuple} - (是否关联表条件, 标准化后的key, 标准化后的值)
        """
        _upper_ret = upper_ret  # 以传入结果的为准
        _std_key = filter_key  # 标准化后的key
        _std_val = filter_val  # 标准化后的val

        # 解析真正的值
        if filter_key[0] == '#':
            _upper_ret = True
            _index = filter_key.find('.')
            _join_para = left_join[int(filter_key[1: _index])]
            _col = filter_key[_index+1:]
            _std_key = '%s.%s' % (_join_para.get('as', _join_para['collection']), _col)
        else:
            _col = filter_key

        # _id字段的处理
        if _col == '_id':
            _type = type(_std_val)
            if _type == str:
                _std_val = ObjectId(_std_val)
            elif isinstance(_std_val, dict):
                if _std_val.get('$in', None) is not None:
                    _std_val['$in'] = [ObjectId(_temp_id) for _temp_id in _std_val['$in']]

                if _std_val.get('$nin', None) is not None:
                    _std_val['$nin'] = [ObjectId(_temp_id) for _temp_id in _std_val['$nin']]

            return _upper_ret, _std_key, _std_val

        # 判断其他情况
        if _col == '$or':
            # 只有or的情况才会有子查询
            _temp_std_val = []
            for _or_filter in _std_val:
                _temp_filter = {}
                for _key, _val in _or_filter.items():
                    _temp_upper_ret, _temp_key, _temp_val = self._check_and_std_filter(
                        _key, _val, left_join, upper_ret=_upper_ret
                    )
                    _upper_ret = _temp_upper_ret
                    _temp_filter[_temp_key] = _temp_val

                _temp_std_val.append(_temp_filter)

            _std_val = _temp_std_val

        # 返回结果
        return _upper_ret, _std_key, _std_val

    def _std_sort(self, sort: list, left_join: list) -> dict:
        """
        标准化排序参数

        @param {list} sort - 查询结果的排序方式
        @param {list} left_join - 指定左关联(left outer join)集合信息

        @returns {dict} - 标准化后的排序参数
        """
        _sort = {}
        for _para in sort:
            if _para[0][0] == '#':
                _index = _para[0].find('.')
                _join_para = left_join[int(_para[0][1: _index])]
                _col = _para[0][_index+1:]
                _sort['%s.%s' % (_join_para.get('as', _join_para['collection']), _col)] = _para[1]
            else:
                _sort[_para[0]] = _para[1]

        return _sort

    def _std_project(self, project: Union[dict, list], left_join: list):
        """
        标准化返回字段参数

        @param {dict|list} project - 指定结果返回的字段信息
        @param {list} left_join - 指定左关联(left outer join)集合信息, 每个数组为一个关联表

        @returns {dict|list} - 标准化后的返回字段参数
        """
        # 无返回配置，全部字段返回
        if project is None:
            return None

        # 处理联表字段的函数
        def _get_col_info(col: str, left_join) -> tuple:
            if col[0] == '#':
                _index = col.find('.')
                _join_para = left_join[int(col[1: _index])]
                _col = col[_index+1:]
                _tab_as_name = '%s.' % _join_para.get('as', _join_para['collection'])
            else:
                _col = col
                _tab_as_name = ''

            return _col, _tab_as_name

        _project = {}
        if isinstance(project, dict):
            # 字典形式
            for _key, _show in project.items():
                if type(_show) == str and _show[0] == '$':
                    # as模式
                    _real_col, _tab_as_name = _get_col_info(_show[1:], left_join)
                    _project['%s%s' % (_tab_as_name, _key)] = '$%s%s' % (_tab_as_name, _real_col)
                elif _key == '_id':
                    _project['_id'] = _show
                elif _show:
                    # 除主表_id外不能为False
                    _real_col, _tab_as_name = _get_col_info(_key, left_join)
                    _project['%s%s' % (_tab_as_name, _real_col)] = _show
        else:
            # 列表形式
            for _item in project:
                _real_col, _tab_as_name = _get_col_info(_item, left_join)
                _project['%s%s' % (_tab_as_name, _real_col)] = True

        return _project

    def _get_left_join_aggregate(self, filter: dict = None, projection: Union[dict, list] = None,
            sort: list = None, skip: int = None, limit: int = None, hint: dict = None,
            left_join: list = None) -> list:
        """
        生成关联表模式的聚合管道运行参数

        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样
        @param {dict|list} projection=None - 指定结果返回的字段信息
        @param {list} sort=None - 查询结果的排序方式
        @param {int} skip=None - 指定跳过返回结果的前面记录的数量
        @param {int} limit=None - 指定限定返回结果记录的数量
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {list} left_join=None - 指定左关联(left outer join)集合信息, 每个数组为一个关联表

        @returns {list} - 聚合管道参数
        """
        _pipeline = []  # 组装执行的管道

        # 分离和标准化过滤条件, 将主表和关联表的过滤条件拆成两个, 分别放在最开始和最后进行过滤
        _main_filter, _join_filter = self._split_filter(filter, left_join)

        # 主表的过滤条件
        if len(_main_filter) > 0:
            _pipeline.append({'$match': _main_filter})

        # 处理关联
        if left_join is not None:
            for _join_para in left_join:
                _as_name = _join_para['collection'] if _join_para.get('as', None) is None else _join_para['as']
                _sub_pipeline = []  # 子聚合管道

                # 关联表过滤条件
                if _join_para.get('filter', None) is not None:
                    _sub_pipeline.append({
                        '$match': self._std_filter(_join_para['filter'])
                    })

                # 关联字段处理
                _let = {}
                _match = []
                for _join_field in _join_para['join_fields']:
                    _let['main_tab_%s' % _join_field[0]] = '$%s' % _join_field[0]
                    _match.append({
                        '$eq': ['$%s' % _join_field[1], '$$main_tab_%s' % _join_field[0]]
                    })

                # 通过匹配关联多字段
                _sub_pipeline.append({
                    '$match': {'$expr': {'$and': _match}}
                })

                # 指定集合
                if _join_para.get('db_name', None) is None:
                    _from = _join_para['collection']
                else:
                    _from = {'db': _join_para['db_name'], 'coll': _join_para['collection']}

                _step = {
                    '$lookup': {
                        # 指定集合
                        'from': _from,
                        # 设置主表关联字段为变量
                        'let': _let,
                        'pipeline': _sub_pipeline,
                        'as': _as_name
                    }
                }

                # 添加到主管道
                _pipeline.append(_step)

                # 展开关联到的关联表数组, 空数组的情况保留主表值
                _pipeline.append({'$unwind': {'path': '$%s' % _as_name, 'preserveNullAndEmptyArrays': True}})

        # 带关联表的过滤条件
        if len(_join_filter) > 0:
            _pipeline.append({'$match': _join_filter})

        # 排序处理
        if sort is not None:
            _pipeline.append({
                '$sort': self._std_sort(sort, left_join)
            })

        # 返回字段处理: {'id': 0} - 显示所有字段, 排除id; {'id': True} - 只显示id字段，排除其他所有字段
        _project = self._std_project(projection, left_join)
        if _project is not None:
            _pipeline.append({'$project': _project})

        # 其他处理
        if skip is not None:
            _pipeline.append({'$skip': skip})

        if limit is not None:
            _pipeline.append({'$limit': limit})

        # 返回结果
        return _pipeline

    def _std_left_join_result(self, result: list, left_join: list = None) -> list:
        """
        标准化关联表返回的结果

        @param {list} result - 返回的结果列表
        @param {list} left_join - 指定左关联(left outer join)集合信息, 每个数组为一个关联表

        @returns {list} - 标准化后的结果
        """
        if left_join is None:
            return result

        # 获取联表as_name的清单
        _as_names = []
        for _join_para in left_join:
            _as_names.append(_join_para.get('as', _join_para['collection']))

        # 逐个处理结果
        for _i in range(len(result)):
            for _as_name in _as_names:
                _join_ret = result[_i].pop(_as_name, None)
                if _join_ret is None:
                    continue

                # 逐个字段放到顶层
                for _key, _val in _join_ret.items():
                    if result[_i].get(_key, None) is None:
                        result[_i][_key] = _val
                    else:
                        _copy_index = 0
                        while True:
                            _copy_index += 1
                            _copy_name = '%s_%d' % (_key, _copy_index)
                            if result[_i].get(_copy_name, None) is None:
                                result[_i][_copy_name] = _val
                                break
                            else:
                                continue

        # 返回结果
        return result
