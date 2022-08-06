#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
nosql数据库驱动基础框架
注: 实现类可以通过bson库的objectid模块自动生成与mongodb匹配的ObjectID

@module driver_fw
@file driver_fw.py
"""
import os
import sys
import logging
import copy
import traceback
from bson.objectid import ObjectId
from typing import Union, Any
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.test_tool import TestTool
from HiveNetCore.connection_pool import AIOConnectionPool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


class NosqlDriverFW(object):
    """
    nosql数据库驱动框架
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, connect_config: dict = {}, pool_config: dict = {}, driver_config: dict = {}):
        """
        初始化驱动

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 连接数据库的ip或uri, 如果使用uri方式, 其他的连接参数不生效
            port {int} - 连接数据库的端口(可选)
            usedb {str} - 登录后默认切换到的数据库(可选), 如果不传使用登录后的默认数据库
            username {str} - 登录验证用户(可选)
            password {str} - 登录验证密码(可选)
            dbname {str} - 登录用户的数据库名(可选)
            connect_on_init {bool} - 是否启动时直接连接数据库, 默认为False(等待第一次操作再连接)
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            ...驱动实现类自定义支持的参数
        @param {dict} pool_config={} - 连接池配置
            max_size {int} - 连接池的最大大小, 默认为100
            min_size {int} - 连接池维持的最小连接数量, 默认为0
            max_idle_time {float} - 连接被移除前的最大空闲时间, 单位为秒, 默认为None
            wait_queue_timeout {float} - 在没有空闲连接的时候, 请求连接所等待的超时时间, 单位为秒, 默认为None(不超时)
            ...驱动实现类自定义支持的参数
        @param {dict} driver_config={} - 驱动配置
            init_db {dict} - 要在启动驱动时创建的数据库
                {
                    '数据库名': {
                        'index_only': False,  # 是否仅用于索引, 不创建
                        'comment': '',  # 数据库注释
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    },
                    ...
                }
            init_collections {dict} - 要在启动驱动时创建的集合(表)
                {
                    '数据库名': {
                        '集合名': {
                            'index_only': False,  # 是否仅用于索引, 不创建
                            'comment': '',  # 集合注释
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}
                        },
                        ...
                    },
                    ...
                }
            init_yaml_file {str} - 要在启动时创建的数据库和集合(表)配置yaml文件
                注1: 该参数用于将init_db和init_collections参数内容放置的配置文件中, 如果参数有值则忽略前面两个参数
                注2: 配置文件为init_db和init_collections两个字典, 内容与这两个参数一致
            logger {Logger} - 传入驱动的日志对象
        """
        raise NotImplementedError()

    def __del__(self):
        """
        注销对象, 应关闭数据库连接
        """
        AsyncTools.sync_run_coroutine(self.destroy())

    #############################
    # 主动销毁驱动
    #############################
    async def destroy(self):
        """
        主动销毁驱动(连接)
        """
        raise NotImplementedError()

    #############################
    # 通用属性
    #############################
    @property
    def db_name(self):
        """
        返回当前数据库名
        @property {str}
        """
        raise NotImplementedError()

    #############################
    # 数据库操作
    #############################
    async def create_db(self, name: str, *args, **kwargs):
        """
        创建数据库
        注: 创建后会自动切换到该数据库

        @param {str} name - 数据库名
        """
        raise NotImplementedError()

    async def switch_db(self, name: str, *args, **kwargs):
        """
        切换当前数据库到指定数据库

        @param {str} name - 数据库名
        """
        raise NotImplementedError()

    async def list_dbs(self, *args, **kwargs) -> list:
        """
        列出数据库清单

        @returns {list} - 数据库名清单
        """
        raise NotImplementedError()

    async def drop_db(self, name: str, *args, **kwargs):
        """
        删除数据库

        @param {str} name - 数据库名
        """
        raise NotImplementedError()

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
                        ...启动实现类自定义支持的参数
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
        """
        raise NotImplementedError()

    async def list_collections(self, filter: dict = None, **kwargs) -> list:
        r"""
        获取所有集合(表)清单

        @param {dict} filter=None - 查找条件
            例如查找所有非'system.'开头的集合: {"name": {"$regex": r"^(?!system\.)"}}

        @returns {list} - 集合(表)清单
        """
        raise NotImplementedError()

    async def drop_collection(self, collection: str, *args, **kwargs):
        """
        删除集合
        注: 集合不存在也正常返回

        @param {str} collection - 集合名(表名)
        """
        raise NotImplementedError()

    async def turncate_collection(self, collection: str, *args, **kwargs):
        """
        清空集合记录

        @param {str} collection - 集合名(表名)
        """
        raise NotImplementedError()

    async def collections_exists(self, collection: str, *args, **kwargs) -> bool:
        """
        判断集合(表)是否存在

        @param {str} collection - 集合名(表名)

        @returns {bool} - 是否存在
        """
        raise NotImplementedError()

    #############################
    # 事务支持
    #############################
    async def start_transaction(self, *args, **kwargs) -> Any:
        """
        启动事务
        注: 通过该方法处理事务, 必须显式通过commit_transaction或abort_transaction关闭事务

        @returns {Any} - 返回事务所在的连接(session)
        """
        raise NotImplementedError()

    async def commit_transaction(self, session, *args, **kwargs):
        """
        提交事务

        @param {Any} session=None - 启动事务的连接(session)
        """
        raise NotImplementedError()

    async def abort_transaction(self, session, *args, **kwargs):
        """
        回滚事务

        @param {Any} session=None - 启动事务的连接(session)
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

    async def insert_many(self, collection: str, rows: list, session: Any = None, **kwargs) -> int:
        """
        插入多条记录

        @param {str} collection - 集合(表)
        @param {list} rows - 行记录数组
            注: 每个记录可以通过'_id'字段指定该记录的唯一主键, 如果不送入, 将自动生成一个唯一主键
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 返回插入的记录数量
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

    async def delete(self, collection: str, filter: dict, multi: bool = True, hint: dict = None,
            session: Any = None, **kwargs) -> int:
        """
        删除指定记录

        @param {str} collection - 集合(表)
        @param {dict} filter - 查询条件字典, 与mongodb的查询条件设置参数一致
        @param {bool} multi=True - 是否更新全部找到的记录, 如果为Fasle只更新找到的第一条记录
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 删除记录数量
        """
        raise NotImplementedError()

    #############################
    # 数据查询
    #############################
    async def query_list(self, collection: str, filter: dict = None, projection: Union[dict, list] = None,
            sort: list = None, skip: int = None, limit: int = None, hint: dict = None, session: Any = None, **kwargs) -> list:
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
        raise NotImplementedError()

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

        @returns {list} - 返回的结果列表迭代器
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

    async def query_page_info(self, collection: str, page_size: int = 15, filter: dict = None,
            hint: dict = None, session: Any = None, **kwargs) -> dict:
        """
        查询分页信息字典

        @param {str} collection - 集合(表)
        @param {int} page_size=15 - 每页大小
        @param {dict} filter=None - 查询条件字典, 与mongodb的查询条件设置方法一样, 参考如下:
            {} : 查询全部记录
            {'id': 'info', 'ver': '0.0.1'} : where id = 'info' and 'ver' = '0.0.1'
            {'ver': {'$lt': '0.0.1'}} : where ver < '0.0.1'
                注: $lt - 小于, $lte - 小于或等于, $gt - 大于, $gte - 大于或等于, $ne - 不等于
            {'id': {'$gt':50}, '$or': [{'name': 'lhj'},{'title': 'book'}]} :
                where id > 50 and (name='lhj' or 'title' = 'book')
            {'name': {'$regex': 'likestr'}} : where name like '%likestr%', 正则表达式
        @param {dict} hint=None - 指定查询使用索引的名字清单
            例: {'index_name1': 1, 'index_name2': 1}
        @param {Any} session=None - 指定事务连接对象

        @returns {dict} - 返回的分页信息
            {
                'total': ?, # 记录总数
                'total_pages': ?, # 分页数
                'page_size': ? # 每页大小
            }
        """
        # 获取记录总数
        _count = await self.query_count(
            collection, filter=filter, hint=hint, session=session
        )

        # 组成返回字典
        return {
            'total': _count,
            'total_pages': int((_count + page_size - 1) / page_size),
            'page_size': page_size
        }

    async def query_page(self, collection: str, page_index: int = 1, page_size: int = 15, filter: dict = None,
            projection: Union[dict, list] = None,
            sort: list = None, hint: dict = None, session: Any = None, **kwargs) -> list:
        """
        查询分页记录(直接返回清单)

        @param {str} collection - 集合(表)
        @param {int} page_index=1 - 分页位置, 从1开始算
        @param {int} page_size=15 - 每页大小
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
        @param {dict} hint=None - 指定查询使用索引的名字清单
            例: {'index_name1': 1, 'index_name2': 1}
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 返回的分页的结果列表
        """
        return await self.query_list(
            collection, filter=filter, projection=projection, sort=sort,
            skip=(page_index - 1) * page_size, limit=page_size, hint=hint, session=session
        )

    #############################
    # 原生命令执行
    #############################
    async def run_native_cmd(self, *args, **kwargs):
        """
        执行原生命令(或SQL)并返回执行结果
        注: 该函数不支持驱动的兼容处理
        """
        raise NotImplementedError()

    #############################
    # 数据库及集合辅助索引
    #############################
    def init_index_extend_dbs(self, dbs: dict):
        """
        在初始化索引参数中扩展数据库索引信息

        @param {dict} dbs - 要扩展的数据库信息字典(注: 仅用于索引, 不创建实际数据库)
                {
                    '数据库名': {
                        'comment': '',  # 数据库注释
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    }
                }
        """
        pass

    def init_index_extend_collections(self, collections: dict):
        """
        在初始化索引参数中扩展集合索引信息

        @param {dict} collections - 要扩展的集合信息字典(注: 仅用于索引, 不创建实际数据库)
                {
                    '数据库名': {
                        '集合名': {
                            'comment': '',  # 集合注释
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}
                        }
                        ...
                    },
                    ...
                }
        """
        pass


class NosqlAIOPoolDriver(NosqlDriverFW):
    """
    nosql数据库驱动使用关系型数据库连接池AIOConnectionPool的基础类
    可以尝试整合的异步数据库驱动包括: asyncpg, aiopg, aiomysql, asyncmy, aiosqlite
    为兼容mongodb的数据存储, 数据表的设计统一为(以集合名t_demo为例):
    t_demo(_id varchar, ...其他固定索引字段, nosql_driver_extend_tags json)
        _id为唯一主键, 可通过bson库的objectid模块自动生成
        固定字段, 可用于查询条件的字段, 注意对顺序并无要求
        nosql_driver_extend_tags, 存放其他扩展信息的字段(尽可能使用支持json的数据库类型, 以支持查询和更新等操作)
    注: 对于原生数据库驱动没有连接池管理情况, 建议基于本基础类实现, 无需自行处理连接池的功能
    """

    #############################
    # 静态工具函数 - 通用查询结果比较函数
    #############################
    @classmethod
    def cmp_func_equal_value(cls, query_ret, cmp_val: Any) -> bool:
        """
        比较函数-与查询结果第1行第1个值与比较值相等

        @param {list} query_ret - 查询返回结果
        @param {Any} cmp_val - 比较值

        @returns {bool} - 比较结果(True代表通过)
        """
        if query_ret is None or len(query_ret) == 0:
            return False

        _type = type(cmp_val)
        _ret_val = list(query_ret[0].values())[0]
        if _type == dict:
            return TestTool.cmp_dict(_ret_val, cmp_val, print_if_diff=False)
        elif _type in (list, tuple):
            return TestTool.cmp_list(_ret_val, cmp_val, print_if_diff=False)
        else:
            return _ret_val == cmp_val

    @classmethod
    def cmp_func_equal_row(cls, query_ret, cmp_val: dict) -> bool:
        """
        比较函数-与查询结果第1行结果比较字典

        @param {list} query_ret - 查询返回结果
        @param {dict} cmp_val - 比较字典值

        @returns {bool} - 比较结果(True代表通过)
        """
        if query_ret is None:
            if cmp_val is None:
                return True
            else:
                return False
        else:
            return TestTool.cmp_dict(query_ret[0], cmp_val, print_if_diff=False)

    @classmethod
    def cmp_func_lt_value(cls, query_ret, cmp_val: Any) -> bool:
        """
        比较函数-查询结果第1行第1个值小于比较值

        @param {list} query_ret - 查询返回结果
        @param {Any} cmp_val - 比较值

        @returns {bool} - 比较结果(True代表通过)
        """
        if query_ret is None or len(query_ret) == 0:
            return False

        _ret_val = list(query_ret[0].values())[0]
        return _ret_val < cmp_val

    @classmethod
    def cmp_func_gt_value(cls, query_ret, cmp_val: Any) -> bool:
        """
        比较函数-查询结果第1行第1个值大于比较值

        @param {list} query_ret - 查询返回结果
        @param {Any} cmp_val - 比较值

        @returns {bool} - 比较结果(True代表通过)
        """
        if query_ret is None or len(query_ret) == 0:
            return False

        _ret_val = list(query_ret[0].values())[0]
        return _ret_val > cmp_val

    #############################
    # 构造函数
    #############################
    def __init__(self, connect_config: dict = {}, pool_config: dict = {}, driver_config: dict = {}):
        """
        初始化驱动

        @param {dict} connect_config={} - 数据库的连接参数
            host {str} - 连接数据库的ip或uri, 如果使用uri方式, 其他的连接参数不生效
            port {int} - 连接数据库的端口(可选)
            usedb {str} - 登录后默认切换到的数据库(可选), 如果不传使用登录后的默认数据库
            username {str} - 登录验证用户(可选)
            password {str} - 登录验证密码(可选)
            dbname {str} - 登录用户的数据库名(可选)
            connect_on_init {bool} - 是否启动时直接连接数据库, 默认为False(等待第一次操作再连接)
            connect_timeout {float} - 连接数据库的超时时间, 单位为秒, 默认为20
            default_str_len {int} - 默认的字符串类型长度, 默认为30
            ...驱动实现类自定义支持的参数
            transaction_share_cursor {bool} - 进行事务处理是否复用同一个游标对象, 默认为True
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
        """
        # 指定是否使用insert_many的单独生成语句, Fasle代表使用insert_one逐条插入替代(存在性能问题)
        self._use_insert_many_generate_sqls = False

        # 公共参数处理
        self._driver_config = copy.deepcopy(driver_config)
        self._default_str_len = connect_config.get('default_str_len', 30)
        self._transaction_share_cursor = connect_config.get('transaction_share_cursor', True)
        self._debug = self._driver_config.get('debug', False)
        self._ignore_index_error = self._driver_config.get('ignore_index_error', True)
        self._logger = driver_config.get('logger', None)
        if self._logger is None:
            logging.basicConfig()
            self._logger = logging.getLogger(__name__)
            if self._debug:
                self._logger.setLevel(logging.DEBUG)

        # 获取数据库连接驱动及参数
        _creator_infos = self._get_db_creator(connect_config, pool_config, driver_config)
        self._db_name = _creator_infos.get('current_db_name', None)

        # 连接池设置参数
        _pool_config = copy.deepcopy(pool_config)
        _pool_config.pop('wait_queue_timeout', None)
        _pool_config['get_timeout'] = pool_config.get('wait_queue_timeout', None)
        _pool_config.pop('max_idle_time', None)
        _pool_config['free_idle_time'] = pool_config.get('max_idle_time', None)
        _pool_config.update(_creator_infos.get('pool_update_config', {}))

        self._pool = AIOConnectionPool(
            _creator_infos['creator'], _creator_infos['pool_connection_class'],
            args=_creator_infos.get('args', []), kwargs=_creator_infos.get('kwargs', {}),
            connect_method_name=_creator_infos.get('connect_method_name', None),
            **_pool_config
        )

        # 是否启动时直接连接数据库
        if connect_config.get('connect_on_init', False):
            # 获取连接, 然后关闭, 相当于验证连接
            _conn = AsyncTools.sync_run_coroutine(self._get_connection())
            AsyncTools.sync_run_coroutine(_conn.close())

        # 获取正确的数据库名(利用db_name的属性获取)
        if self._db_name is None:
            self._db_name = self.db_name

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

        _temp_db_name = self._db_name
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

        # 启动连接池后驱动需要执行的后处理
        AsyncTools.sync_run_coroutine(self._driver_after_init_pool())

        # 数据表的字段信息字典, {'数据库名': {'表名': {'cols': [固定字段列表], 'define': {固定字段定义}}}}
        self._fixed_col_define = {}

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
        await AsyncTools.async_run_coroutine(self._pool.close())

    #############################
    # 通用属性
    #############################
    @property
    def db_name(self):
        """
        返回当前数据库名
        @property {str}
        """
        if self._db_name is None:
            return AsyncTools.sync_run_coroutine(self._get_current_db_name())
        else:
            return self._db_name

    #############################
    # 数据库操作
    #############################
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
        await self.switch_db(name)

    async def switch_db(self, name: str, *args, **kwargs):
        """
        切换当前数据库到指定数据库

        @param {str} name - 数据库名
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('switch_db', name)
        )
        await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )
        self._db_name = name

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
        # 需要将字典形式的列表转换为数据库名列表, 注意查询结果的字段名必须为name
        return [_db['name'] for _db in _ret]

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

        # 切换后判断是不是删除当前数据库
        if self._db_name == name:
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
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'create_collection', collection, indexs=indexs, fixed_col_define=fixed_col_define,
                comment=comment, **kwargs
            )
        )
        return await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )

    async def list_collections(self, filter: dict = None, **kwargs) -> list:
        r"""
        获取所有集合(表)清单

        @param {dict} filter=None - 查找条件
            例如查找所有非'system.'开头的集合: {"name": {"$regex": r"^(?!system\.)"}}

        @returns {list} - 集合(表)清单
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('list_collections', filter=filter)
        )
        _ret = await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )
        # 需要将字典形式的列表转换为数据库名列表, 注意查询结果的字段名必须为name
        return [_tab['name'] for _tab in _ret]

    async def drop_collection(self, collection: str, *args, **kwargs):
        """
        删除集合
        注: 集合不存在也正常返回

        @param {str} collection - 集合名(表名)
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('drop_collection', collection)
        )
        # 设置固定的参数
        _execute_paras.update({
            'is_query': False, 'commit_on_finished': True, 'rollback_on_exception': True
        })
        return await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )

    async def turncate_collection(self, collection: str, *args, **kwargs):
        """
        清空集合记录

        @param {str} collection - 集合名(表名)
        """
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls('turncate_collection', collection)
        )
        return await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, **_execute_paras
        )

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
    #############################
    async def start_transaction(self, *args, **kwargs) -> Any:
        """
        启动事务
        注: 通过该方法处理事务, 必须显式通过commit_transaction或abort_transaction关闭事务

        @returns {Any} - 返回事务所在的连接(session)
        """
        # 获取新连接和游标, 开始处理事务
        _conn = await self._get_connection()
        _cursor = None
        if self._transaction_share_cursor:
            # 复用相同的游标
            _cursor = await AsyncTools.async_run_coroutine(_conn.cursor())

        return (_conn, _cursor)

    async def commit_transaction(self, session, *args, **kwargs):
        """
        提交事务

        @param {Any} session=None - 启动事务的连接(session)
        """
        _conn = session[0]
        _cursor = session[1]
        if _cursor is not None:
            # 先关闭游标
            await AsyncTools.async_run_coroutine(_cursor.close())

        # 提交事务
        await AsyncTools.async_run_coroutine(_conn.commit())

        # 关闭连接
        await AsyncTools.async_run_coroutine(_conn.close())

    async def abort_transaction(self, session, *args, **kwargs):
        """
        回滚事务

        @param {Any} session=None - 启动事务的连接(session)
        """
        _conn = session[0]
        _cursor = session[1]
        if _cursor is not None:
            # 先关闭游标
            await AsyncTools.async_run_coroutine(_cursor.close())

        # 回滚事务
        await AsyncTools.async_run_coroutine(_conn.rollback())

        # 关闭连接
        await AsyncTools.async_run_coroutine(_conn.close())

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
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 处理_id
        _row = copy.copy(row)  # 浅复制即可
        _id = _row.get('_id', None)
        if _id is None:
            _id = str(ObjectId())
            _row['_id'] = _id

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)

        # 获取执行sql
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'insert_one', collection, _row, fixed_col_define=_fixed_col_define
            )
        )
        _execute_paras.update(_upd_execute_paras)
        _ret = await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
        )
        if _ret == 1:
            return _id

    async def insert_many(self, collection: str, rows: list, session: Any = None, **kwargs) -> int:
        """
        插入多条记录

        @param {str} collection - 集合(表)
        @param {list} rows - 行记录数组
            注: 每个记录可以通过'_id'字段指定该记录的唯一主键, 如果不送入, 将自动生成一个唯一主键
        @param {Any} session=None - 指定事务连接对象

        @returns {int} - 返回插入的记录数量
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)

        if self._use_insert_many_generate_sqls:
            # 生成插入多条数据的语句
            # 获取执行sql
            _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
                self._generate_sqls(
                    'insert_many', collection, rows, fixed_col_define=_fixed_col_define
                )
            )
            _execute_paras.update(_upd_execute_paras)
            await self._execute_sqls(
                _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
            )
        else:
            # 通过多次执行insert_one插入
            _msqls = []
            _msql_paras = []
            _mexecute_paras = {}
            _mchecks = None
            _mis_query = None
            for _s_row in rows:
                # 处理_id
                _row = copy.copy(_s_row)  # 浅复制即可
                if _row.get('_id', None) is None:
                    _row['_id'] = str(ObjectId())

                _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
                    self._generate_sqls(
                        'insert_one', collection, _row, fixed_col_define=_fixed_col_define
                    )
                )
                # 语句检查参数
                if _checks is not None:
                    if _mchecks is None:
                        _mchecks = [None for _temp in _msqls]  # 生成检查列表
                    _mchecks.extend(_checks)

                # 是否查询参数
                if _execute_paras.get('is_query', None) is not None:
                    _is_query = _execute_paras['is_query']
                    if type(_is_query) in (list, tuple):
                        # 是列表的情况, 需要扩充
                        if _mis_query is None:
                            _mis_query = [False for _temp in _msqls]  # 生成查询列表
                        _mis_query.extend(_is_query)
                    elif _is_query:
                        # 最后一个要查询
                        if _mis_query is not None:
                            _mis_query.extend([False for _temp in _sqls[: -1]])
                            _mis_query.append(True)
                    else:
                        # 最后一个非查询
                        if _mis_query is not None:
                            _mis_query.extend([False for _temp in _sqls])
                else:
                    # 没有指定, 对于列表情况需要扩充
                    if _mis_query is not None:
                        _mis_query.extend([False for _temp in _sqls])

                _msqls.extend(_sqls)
                _msql_paras.extend(_sql_paras)
                _mexecute_paras = _execute_paras

            _mexecute_paras.update(_upd_execute_paras)
            if _mis_query is not None:
                _mexecute_paras['is_query'] = _mis_query

            await self._execute_sqls(
                _msqls, paras=_msql_paras, checks=_mchecks, conn=_conn, cursor=_cursor, **_mexecute_paras
            )

        return len(rows)

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
            注: min和max当遇到字段不存在或为null时, 则直接设置为比较值
            {'$unset': {'job': 1}}: job=null, 删除指定字段
            {'$rename': {'old_name': 'new_name', ...}}: 将字段名修改为新字段名
        @param {bool} multi=True - 是否更新全部找到的记录, 如果为Fasle只更新找到的第一条记录
        @param {bool} upsert=False - 指定如果记录不存在是否插入
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {Any} session=None - 指定事务连接对象
        @param {list|str} partition=None - MySQL, PostgreSQL专有参数, 指定操作的分区
            注: MySQL支持送入分区列表名, 例如(p1, s3); PostgreSQL仅支持送入单个分区后缀名, 例如'p1'

        @returns {int} - 返回更新的数据条数
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)

        _filter = {} if filter is None else filter
        _no_match = False
        if not multi and '_id' not in _filter.keys():
            # 只更新一条记录, 但又没有送主键进来, 需要查询记录的主键再更新
            _ret = await self.query_list(
                collection, filter=_filter, projection={'_id': True}, limit=1, hint=hint,
                session=session
            )
            if len(_ret) == 0:
                # 没有找到记录
                _no_match = True
            else:
                # 变更更新的条件, 直接用_id就好
                _filter = {'_id': _ret[0]['_id']}

        if not _no_match:
            # 执行更新操作
            _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
                self._generate_sqls(
                    'update', collection, _filter, update, multi=multi, upsert=upsert, hint=hint,
                    fixed_col_define=_fixed_col_define, **kwargs
                )
            )
            _execute_paras.update(_upd_execute_paras)
            _ret = await self._execute_sqls(
                _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
            )
            if _ret > 0:
                # 更新成功
                return _ret

        if upsert:
            # 没有更新成功, 改为用insert_one插入
            _row = {}
            if _filter is not None:
                for _key, _val in _filter.items():
                    if _key[0] != '$' and type(_val) != dict:
                        _row[_key] = _val

            for _op, _para in update.items():
                if _op in ('$set', '$inc', '$min', '$max'):
                    _row.update(_para)
                elif _op == '$mul':
                    # 设置为0
                    for _key, _val in _para.items():
                        _row[_key] = 0

            await self.insert_one(collection, _row, session=session)
            return 0
        else:
            # 没有更新成功且无需插入
            return 0

    async def delete(self, collection: str, filter: dict, multi: bool = True, hint: dict = None,
            session: Any = None, **kwargs) -> int:
        """
        删除指定记录

        @param {str} collection - 集合(表)
        @param {dict} filter - 查询条件字典, 与mongodb的查询条件设置参数一致
        @param {bool} multi=True - 是否删除全部找到的记录, 如果为Fasle只删除找到的第一条记录
        @param {dict} hint=None - 指定查询使用索引的名字清单
        @param {Any} session=None - 指定事务连接对象
        @param {list|str} partition=None - MySQL, PostgreSQL专有参数, 指定操作的分区
            注: MySQL支持送入分区列表名, 例如(p1, s3); PostgreSQL仅支持送入单个分区后缀名, 例如'p1'

        @returns {int} - 删除记录数量
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)

        _filter = {} if filter is None else filter
        if not multi and '_id' not in _filter.keys():
            # 只删除一条记录, 但又没有送主键进来, 需要查询记录的主键再删除
            _ret = await self.query_list(
                collection, filter=_filter, projection={'_id': True}, limit=1, hint=hint,
                session=session
            )
            if len(_ret) == 0:
                # 没有找到记录
                return 0
            else:
                # 变更更新的条件, 直接用_id就好
                _filter = {'_id': _ret[0]['_id']}

        # 获取并执行删除语句
        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'delete', collection, _filter, multi=multi, hint=hint,
                fixed_col_define=_fixed_col_define, **kwargs
            )
        )

        _execute_paras.update(_upd_execute_paras)
        return await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
        )

    #############################
    # 数据查询
    #############################
    async def query_list(self, collection: str, filter: dict = None, projection: Union[dict, list] = None,
            sort: list = None, skip: int = None, limit: int = None, hint: dict = None, session: Any = None, **kwargs) -> list:
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
        @param {list|str} partition=None - MySQL, PostgreSQL专有参数, 指定操作的分区
            注: MySQL支持送入分区列表名, 例如(p1, s3); PostgreSQL仅支持送入单个分区后缀名, 例如'p1'

        @returns {list} - 返回的结果列表
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True,
            'is_query': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)
        _filter = {} if filter is None else filter

        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'query', collection, filter=_filter, projection=projection, sort=sort,
                skip=skip, limit=limit, hint=hint, fixed_col_define=_fixed_col_define,
                **kwargs
            )
        )
        # 更新执行sql的参数
        _execute_paras.update(_upd_execute_paras)
        return await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
        )

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
        @param {list|str} partition=None - MySQL, PostgreSQL专有参数, 指定操作的分区
            注: MySQL支持送入分区列表名, 例如(p1, s3); PostgreSQL仅支持送入单个分区后缀名, 例如'p1'

        @returns {list} - 返回的结果列表迭代器
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True,
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)
        _filter = {} if filter is None else filter

        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'query', collection, filter=_filter, projection=projection, sort=sort,
                skip=skip, limit=limit, hint=hint, fixed_col_define=_fixed_col_define,
                **kwargs
            )
        )
        _execute_is_query = _execute_paras.get('is_query', True)
        _execute_paras.update(_upd_execute_paras)

        if _cursor is None:
            _conn = await self._get_connection(conn=_conn)
            _cursor = await AsyncTools.async_run_coroutine(_conn.cursor())

        try:
            # 上一个语句执行结果和是否异常的标识
            _prev_return = None
            _prev_error = False

            # 遍历执行语句
            _index = 0
            _lask_index = len(_sqls) - 1
            for _sql in _sqls:
                # 参数准备
                _is_last = (_index >= _lask_index)
                _sql_paras = None if _sql_paras is None else _sql_paras[_index]
                _run_check = {}
                if _checks is not None and _checks[_index] is not None:
                    _run_check = _checks[_index]

                _is_query = False
                if type(_execute_is_query) in (list, tuple):
                    _is_query = _execute_is_query[_index]
                elif _is_last:
                    _is_query = True

                _index += 1  # 跳转下一个标识

                # 执行前判断
                if not self._execute_sql_pre_check(_run_check, _prev_return, _prev_error):
                    # 检查不通过, 跳过执行, 当作空执行成功
                    _prev_return = None
                    _prev_error = False
                    continue

                try:
                    if _is_last:
                        # 最后一个查询
                        _prev_return = self._execute_sql_query_iter(
                            _sql, paras=_sql_paras, fetch_each=fetch_each, conn=_conn, cursor=_cursor,
                            commit_on_finished=False, rollback_on_exception=False,
                            close_cursor=False, close_conn=False
                        )
                    else:
                        _prev_return = await self._execute_sql(
                            _sql, paras=_sql_paras, is_query=_is_query, conn=_conn, cursor=_cursor,
                            commit_on_finished=False, rollback_on_exception=False,
                            close_cursor=False, close_conn=False
                        )

                    _prev_error = False
                except:
                    _prev_error = True
                    _prev_return = None
                    if not _run_check.get('after_check', {}).get('ignore_current_error', False):
                        # 不忽略执行异常
                        raise

            # 最后一个语句为异步迭代器
            async for _rows in _prev_return:
                yield _rows

            # 判断是否需要自动提交
            if _execute_paras['commit_on_finished']:
                await AsyncTools.async_run_coroutine(_conn.commit())
        except:
            # 出现异常, 判断是否要回滚
            if _execute_paras['rollback_on_exception']:
                await AsyncTools.async_run_coroutine(_conn.rollback())
            raise
        finally:
            # 判断是否关闭游标和连接
            if _execute_paras['close_cursor']:
                await AsyncTools.async_run_coroutine(_cursor.close())
            if _execute_paras['close_conn']:
                await AsyncTools.async_run_coroutine(_conn.close())

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
        @param {list|str} partition=None - MySQL, PostgreSQL专有参数, 指定操作的分区
            注: MySQL支持送入分区列表名, 例如(p1, s3); PostgreSQL仅支持送入单个分区后缀名, 例如'p1'

        @returns {int} - 返回查询条件匹配的记录数
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True,
            'is_query': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)
        _filter = {} if filter is None else filter

        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'query_count', collection, filter=_filter, skip=skip, limit=limit, hint=hint,
                fixed_col_define=_fixed_col_define, **kwargs
            )
        )

        # 更新执行sql的参数
        _execute_paras.update(_upd_execute_paras)
        _ret = await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
        )

        # 返回第0行第0个记录
        return list(_ret[0].values())[0]

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
        @param {list|str} partition=None - MySQL, PostgreSQL专有参数, 指定操作的分区
            注: MySQL支持送入分区列表名, 例如(p1, s3); PostgreSQL仅支持送入单个分区后缀名, 例如'p1'

        @returns {list} - 返回结果列表
        """
        # 执行连接的固定参数
        _upd_execute_paras = {
            'commit_on_finished': True,
            'rollback_on_exception': True,
            'close_cursor': True,
            'close_conn': True,
            'is_query': True
        }

        # 获取session
        if session is not None:
            _conn = session[0]
            _cursor = session[1]
            _upd_execute_paras['commit_on_finished'] = False
            _upd_execute_paras['rollback_on_exception'] = False
            _upd_execute_paras['close_conn'] = False
            if _cursor is not None:
                _upd_execute_paras['close_cursor'] = False
        else:
            _conn = None
            _cursor = None

        # 获取固定字段信息
        _fixed_col_define = await self._get_fixed_col_define(collection, session=session)
        _filter = {} if filter is None else filter

        _sqls, _sql_paras, _execute_paras, _checks = await AsyncTools.async_run_coroutine(
            self._generate_sqls(
                'query_group_by', collection, group=group, filter=_filter, projection=projection,
                sort=sort, fixed_col_define=_fixed_col_define, **kwargs
            )
        )

        _execute_paras.update(_upd_execute_paras)
        return await self._execute_sqls(
            _sqls, paras=_sql_paras, checks=_checks, conn=_conn, cursor=_cursor, **_execute_paras
        )

    #############################
    # 原生命令执行
    #############################
    async def run_native_cmd(self, sql: str, paras: tuple = None, is_query: bool = True,
            conn: Any = None, cursor: Any = None,
            commit_on_finished: bool = True, rollback_on_exception: bool = True,
            close_cursor: bool = False, close_conn: bool = False, **kwargs):
        """
        执行原生命令(或SQL)并返回执行结果
        注: 该函数不支持驱动的兼容处理

        @param {str} sql - 要执行的SQL语句
        @param {tuple} paras=None - 传入的SQL参数字典(支持?占位)
        @param {bool} is_query=True - 指定语句是否查询
        @param {Any} conn=None - 传入的已打开连接, 如果传入代表纳入事务处理
        @param {Any} cursor=None - 传入的已有游标, 不传入将自动创建新游标, 如果传入该值必须也传入conn
        @param {bool} commit_on_finished=True - 完成处理时是否执行commit操作
        @param {bool} rollback_on_exception=True - 出现异常时是否执行rollback操作
        @param {bool} close_cursor=False - 是否关闭所传入的游标
        @param {bool} close_conn=False - 是否关闭所传入的连接

        @returns {int} - 返回结果, 不同情况返回如下:
            非查询语句: 返回当前语句影响的记录数量, 如果无记录情况返回None
            一次性获取的查询语句: 返回行记录转换为字典形式的list列表
        """
        return await self._execute_sql(
            sql, paras=paras, is_query=is_query, conn=conn, cursor=cursor,
            commit_on_finished=commit_on_finished, rollback_on_exception=rollback_on_exception,
            close_cursor=close_cursor, close_conn=close_conn
        )

    #############################
    # 数据库及集合辅助索引
    #############################
    def init_index_extend_dbs(self, dbs: dict):
        """
        在初始化索引参数中扩展数据库索引信息

        @param {dict} dbs - 要扩展的数据库信息字典(注: 仅用于索引, 不创建实际数据库)
                {
                    '数据库名': {
                        'comment': '',  # 数据库注释
                        'args': [], # 创建数据库的args参数
                        'kwargs': {}  #创建数据库的kwargs参数
                    }
                }
        """
        pass

    def init_index_extend_collections(self, collections: dict):
        """
        在初始化索引参数中扩展集合索引信息

        @param {dict} collections - 要扩展的集合信息字典(注: 仅用于索引, 不创建实际数据库)
                {
                    '数据库名': {
                        '集合名': {
                            'comment': '',  # 集合注释
                            'indexs': {索引字典}, 'fixed_col_define': {固定字段定义}, ...
                        }
                        ...
                    },
                    ...
                }
        """
        # 遍历数据库处理字段信息字典
        for _db_name, _collections in collections.items():
            # 构建数据表的字段信息字典缓存
            if _db_name not in self._fixed_col_define.keys():
                self._fixed_col_define[_db_name] = {}

            # 遍历表进行创建处理
            for _collection, _info in _collections.items():
                self._fixed_col_define[_db_name][_collection] = {
                    'cols': list(_info.get('fixed_col_define', {}).keys()),
                    'define': _info.get('fixed_col_define', {})
                }

    #############################
    # 内部函数
    #############################
    async def _get_fixed_col_define(self, collection: str, session: Any = None) -> dict:
        """
        获取制定集合(表)的固定字段定义信息

        @param {str} collection - 集合名(表)
        @param {Any} session=None - 指定事务连接对象

        @returns {dict} - 返回固定信息字典
        """
        _fixed_col_define = self._fixed_col_define.get(self._db_name, {}).get(collection, None)
        if _fixed_col_define is None:
            # 尝试查询数据库获取
            _cols_define = await AsyncTools.async_run_coroutine(
                self._get_cols_info(collection, session=session)
            )
            _fixed_col_define = {'cols': [], 'define': {}}
            for _info in _cols_define:
                if _info['name'] in ('_id', 'nosql_driver_extend_tags'):
                    continue

                _fixed_col_define['cols'].append(_info['name'])
                _fixed_col_define['define'][_info['name']] = _info['type']

            # 添加到数据表的字段信息字典缓存
            if len(_cols_define) > 0:
                if self._db_name not in self._fixed_col_define.keys():
                    self._fixed_col_define[self._db_name] = {}

                self._fixed_col_define[self._db_name][collection] = _fixed_col_define

        return _fixed_col_define

    async def _get_connection(self, conn: Any = None) -> Any:
        """
        从连接池获取数据库连接

        @param {Any} conn=None - 传入指定的连接对象
            注: 如果传入连接对象则不再从连接池获取

        @returns {Any} - 数据库连接对象
        """
        _conn = conn
        if _conn is None:
            _conn = await self._pool.connection()
            # 驱动初始化连接对象
            await AsyncTools.async_run_coroutine(
                self._driver_init_connection(_conn)
            )

        return _conn

    def _execute_sql_pre_check(self, pre_check: dict, prev_return: Any, prev_error: bool) -> bool:
        """
        执行SQL语句数组前检查函数

        @param {dict} pre_check - 检查字典
            {
                'skip_when_prev_error': False,  # 是否当上一条语句异常时跳过当前语句执行, 默认为False
                # # 默认为None忽略当前参数, 使用cmp_val与上一条执行语句的返回值比较
                # (如果传入func比较函数或lamba, 则使用比较函数来处理, 否则默认使用self.cmp_func_equal_first_value比较),
                # 比较结果为True则执行当前语句, 为False则跳过当前语句
                'cmp_prev_return': [cmp_val, func]
            }
        @param {Any} prev_return - 上一语句返回结果
        @param {bool} prev_error - 上一结果是否异常

        @returns {bool} - 检查结果, True为通过, False为跳过
        """
        if pre_check is None:
            # 没有检查参数
            return True

        # 是否当上一条语句异常时跳过当前语句执行
        if prev_error and pre_check.get('skip_when_prev_error', False):
            return False

        # 与上一返回值的比较
        if pre_check.get('cmp_prev_return', None) is not None:
            _cmp_val = pre_check['cmp_prev_return'][0]
            if len(pre_check['cmp_prev_return']) < 2 or pre_check['cmp_prev_return'][1] is None:
                _func = self.cmp_func_equal_first_value
            else:
                _func = pre_check['cmp_prev_return'][1]

            if not _func(prev_return, _cmp_val):
                return False

        return True

    async def _execute_sqls(self, sqls: list, paras: list = None, checks: list = None,
            is_query: bool = False, conn: Any = None, cursor: Any = None,
            commit_on_finished: bool = True, rollback_on_exception: bool = True,
            close_cursor: bool = False, close_conn: bool = False):
        """
        执行SQL语句

        @param {list} sqls - 要执行的SQL语句数组
        @param {list} paras=None - 传入的SQL参数数组(支持?占位)
        @param {list} checks=None - SQL语句的检查列表, 如果设置了必须于sqls对应, 每个sql的检查值为:
            {
                'pre_check': {
                    . # 执行前检查, 支持的参数见self._execute_sql_pre_check的定义
                },
                'after_check': {  # 执行后检查
                    'ignore_current_error': False,  # 是否忽略当前语句异常, 默认为False
                }
            }
        @param {bool|list} is_query=False - 指定语句是否查询(最后一个语句使用参数)
            注: 如果传入的是list, 则代表指定每个语句是否查询
        @param {Any} conn=None - 传入的已打开连接, 如果传入代表纳入事务处理
        @param {Any} cursor=None - 传入的已有游标, 不传入将自动创建新游标, 如果传入该值必须也传入conn
        @param {bool} commit_on_finished=True - 完成处理时是否执行commit操作
        @param {bool} rollback_on_exception=True - 出现异常时是否执行rollback操作
        @param {bool} close_cursor=False - 是否关闭所传入的游标
        @param {bool} close_conn=False - 是否关闭所传入的连接

        @returns {int} - 最后一个语句的返回结果, 不同情况返回如下:
            非查询语句: 返回当前语句影响的记录数量, 如果无记录情况返回None
            一次性获取的查询语句: 返回行记录转换为字典形式的list列表
        """
        # 判断是否关闭传入游标和连接
        _close_cursor = close_cursor
        if not _close_cursor and cursor is None:
            _close_cursor = True

        _close_conn = close_conn
        if _close_cursor:
            if not _close_conn and conn is None:
                _close_conn = True
        else:
            # 不关闭游标的情况下, 不能关闭连接
            _close_conn = False

        # 获取连接和游标对象
        _cursor = cursor
        _conn = conn
        if cursor is None:
            _conn = await self._get_connection(conn=conn)
            _cursor = await AsyncTools.async_run_coroutine(_conn.cursor())

        try:
            # 上一个语句执行结果和是否异常的标识
            _prev_return = None
            _prev_error = False

            # 遍历执行语句
            _index = 0
            _last_index = len(sqls) - 1
            for _sql in sqls:
                # 参数准备
                _sql_paras = None if paras is None else paras[_index]
                _run_check = {}
                if checks is not None and checks[_index] is not None:
                    _run_check = checks[_index]

                _is_query = False
                if type(is_query) in (list, tuple):
                    _is_query = is_query[_index]
                elif _index >= _last_index:
                    # 最后一个
                    _is_query = is_query

                _index += 1  # 跳转下一个标识

                # 执行前判断
                if not self._execute_sql_pre_check(_run_check.get('pre_check', None), _prev_return, _prev_error):
                    # 检查不通过, 跳过执行, 当作空执行成功
                    _prev_return = None
                    _prev_error = False
                    continue

                try:
                    _prev_return = await self._execute_sql(
                        _sql, paras=_sql_paras, is_query=_is_query,
                        conn=_conn, cursor=_cursor,
                        commit_on_finished=False, rollback_on_exception=False,
                        close_cursor=False, close_conn=False
                    )
                    _prev_error = False
                except:
                    _prev_return = None
                    _prev_error = True
                    if not _run_check.get('after_check', {}).get('ignore_current_error', False):
                        # 不忽略执行异常
                        raise

            # 判断是否需要自动提交
            if commit_on_finished:
                await AsyncTools.async_run_coroutine(_conn.commit())

            return _prev_return
        except:
            # 出现异常, 判断是否要回滚
            if rollback_on_exception:
                await AsyncTools.async_run_coroutine(_conn.rollback())
            raise
        finally:
            # 判断是否关闭游标和连接
            if _close_cursor:
                await AsyncTools.async_run_coroutine(_cursor.close())
            if _close_conn:
                await AsyncTools.async_run_coroutine(_conn.close())

    async def _rows_to_dict(self, col_index: list, rows: list) -> list:
        """
        将查询结果数组转换为字典数组

        @param {list} col_index - 列索引
        @param {list} rows - 要处理的数组

        @returns {list} - 返回处理后的字典数组
        """
        # 空结果的情况返回空列表
        if rows is None:
            return []

        _dict_list = []
        for _row in rows:
            # 遍历形成, 需要去掉None的key
            # _dict = dict(zip(col_index, self._format_row_value(_row)))
            _dict = {}
            _formated_row = await AsyncTools.async_run_coroutine(self._format_row_value(_row))
            for _i in range(len(col_index)):
                if _formated_row[_i] is not None:
                    _dict[col_index[_i]] = _formated_row[_i]

            if 'nosql_driver_extend_tags' in col_index:
                # 扩展字段放回字典的第一层
                _extend = _dict.pop('nosql_driver_extend_tags')
                _dict.update(_extend)

            _dict_list.append(_dict)

        return _dict_list

    async def _execute_sql(self, sql: str, paras: tuple = None, is_query: bool = False,
            conn: Any = None, cursor: Any = None,
            commit_on_finished: bool = True, rollback_on_exception: bool = True,
            close_cursor: bool = False, close_conn: bool = False):
        """
        执行SQL语句(正常返回模式)

        @param {str} sql - 要执行的SQL语句
        @param {tuple} paras=None - 传入的SQL参数字典(支持?占位)
        @param {bool} is_query=False - 指定语句是否查询
        @param {Any} conn=None - 传入的已打开连接, 如果传入代表纳入事务处理
        @param {Any} cursor=None - 传入的已有游标, 不传入将自动创建新游标, 如果传入该值必须也传入conn
        @param {bool} commit_on_finished=True - 完成处理时是否执行commit操作
        @param {bool} rollback_on_exception=True - 出现异常时是否执行rollback操作
        @param {bool} close_cursor=False - 是否关闭所传入的游标
        @param {bool} close_conn=False - 是否关闭所传入的连接

        @returns {int} - 返回结果, 不同情况返回如下:
            非查询语句: 返回当前语句影响的记录数量, 如果无记录情况返回None
            一次性获取的查询语句: 返回行记录转换为字典形式的list列表
        """
        # 判断是否关闭传入游标和连接
        _close_cursor = close_cursor
        if not _close_cursor and cursor is None:
            _close_cursor = True

        _close_conn = close_conn
        if _close_cursor:
            if not _close_conn and conn is None:
                _close_conn = True
        else:
            # 不关闭游标的情况下, 不能关闭连接
            _close_conn = False

        # 获取连接和游标对象
        _cursor = cursor
        _conn = conn
        if _cursor is None:
            _conn = await self._get_connection(conn=conn)
            _cursor = await AsyncTools.async_run_coroutine(_conn.cursor())

        try:
            # 返回结果对象
            _ret = None

            # 执行sql
            if self._debug:
                # debug模式, 打印sql
                self._logger.debug('run sql: %s, para: %s' % (sql, paras))

            if paras is None:
                await AsyncTools.async_run_coroutine(_cursor.execute(sql))
            else:
                await AsyncTools.async_run_coroutine(_cursor.execute(sql, paras))

            if is_query:
                # 查询语句, 一次性返回查询结果
                _col_index = [_tup[0] for _tup in _cursor.description]
                _rows = await AsyncTools.async_run_coroutine(_cursor.fetchall())
                # 转换为字典形式并返回
                _ret = await self._rows_to_dict(_col_index, _rows)
            else:
                # 非查询语句, 返回语句影响影响的记录行数
                _rowcount = _cursor.rowcount
                _ret = None if _rowcount == -1 else _rowcount

            # 判断是否需要自动提交
            if commit_on_finished:
                await AsyncTools.async_run_coroutine(_conn.commit())

            return _ret
        except:
            # 出现异常, 判断是否要回滚
            if rollback_on_exception:
                await AsyncTools.async_run_coroutine(_conn.rollback())

            # 异常输出日志
            self._logger.error(
                'execute sql error, sql=%s paras=%s error: %s' % (sql, str(paras), traceback.format_exc())
            )
            raise
        finally:
            # 判断是否关闭游标和连接
            if _close_cursor:
                await AsyncTools.async_run_coroutine(_cursor.close())
            if _close_conn:
                await AsyncTools.async_run_coroutine(_conn.close())

    async def _execute_sql_query_iter(self, sql: str, paras: tuple = None,
            fetch_each: int = 1, conn: Any = None, cursor: Any = None,
            commit_on_finished: bool = True, rollback_on_exception: bool = True,
            close_cursor: bool = False, close_conn: bool = False):
        """
        执行查询SQL语句(迭代获取模式)

        @param {str} sql - 要执行的SQL语句
        @param {tuple} paras=None - 传入的SQL参数字典(支持?占位)
        @param {int} fetch_each=1 - 查询的情况下, 每次获取的记录数量
        @param {Any} conn=None - 传入的已打开连接, 如果传入代表纳入事务处理
        @param {Any} cursor=None - 传入的已有游标, 不传入将自动创建新游标, 如果传入该值必须也传入conn
        @param {bool} commit_on_finished=True - 完成处理时是否执行commit操作
        @param {bool} rollback_on_exception=True - 出现异常时是否执行rollback操作
        @param {bool} close_cursor=False - 是否关闭所传入的游标
        @param {bool} close_conn=False - 是否关闭所传入的连接

        @returns {async_generator} - 返回可异步迭代获取的查询结果
            通过 async for 遍历返回的迭代结果列表, 或使用RunTool.AsyncTools工具遍历处理
        """
        # 判断是否关闭传入游标和连接
        _close_cursor = close_cursor
        if not _close_cursor and cursor is None:
            _close_cursor = True

        _close_conn = close_conn
        if _close_cursor:
            if not _close_conn and conn is None:
                _close_conn = True
        else:
            # 不关闭游标的情况下, 不能关闭连接
            _close_conn = False

        # 获取连接和游标对象
        _cursor = cursor
        _conn = conn
        if _cursor is None:
            _conn = await self._get_connection(conn=conn)
            _cursor = await AsyncTools.async_run_coroutine(_conn.cursor())

        try:
            # 执行sql
            if self._debug:
                # debug模式, 打印sql
                self._logger.debug('run sql: %s, para: %s' % (sql, paras))

            if paras is None:
                await AsyncTools.async_run_coroutine(_cursor.execute(sql))
            else:
                await AsyncTools.async_run_coroutine(_cursor.execute(sql, paras))

            # 查询语句, 分批次返回查询结果
            _col_index = [_tup[0] for _tup in _cursor.description]
            while True:
                _rows = await AsyncTools.async_run_coroutine(_cursor.fetchmany(fetch_each))
                if _rows is None or len(_rows) == 0:
                    # 已无记录获取
                    break

                # 返回转换后的处理结果
                _fetchs = await self._rows_to_dict(_col_index, _rows)
                yield _fetchs

            # 判断是否需要自动提交
            if commit_on_finished:
                await AsyncTools.async_run_coroutine(_conn.commit())

        except:
            # 出现异常, 判断是否要回滚
            if rollback_on_exception:
                await AsyncTools.async_run_coroutine(_conn.rollback())
            # 异常输出日志
            self._logger.error(
                'execute sql error, sql=%s paras=%s error: %s' % (sql, str(paras), traceback.format_exc())
            )
            raise
        finally:
            # 判断是否关闭游标和连接
            if _close_cursor:
                await AsyncTools.async_run_coroutine(_cursor.close())
            if _close_conn:
                await AsyncTools.async_run_coroutine(_conn.close())

    #############################
    # 初始化集合
    #############################
    async def _init_collections(self, init_configs: dict):
        """
        启动驱动时创建的集合(表)

        @param {dict} init_configs - 初始化参数, 在构造函数中传入
        """
        # 记录开始时的数据库名
        _temp_name = self._db_name

        # 遍历数据库创建
        for _db_name, _collections in init_configs.items():
            if self._db_name != _db_name:
                # 切换到指定数据库
                await self.switch_db(_db_name)

            # 构建数据表的字段信息字典缓存
            if _db_name not in self._fixed_col_define.keys():
                self._fixed_col_define[_db_name] = {}

            # 遍历表进行创建处理
            for _collection, _info in _collections.items():
                self._fixed_col_define[_db_name][_collection] = {
                    'cols': list(_info.get('fixed_col_define', {}).keys()),
                    'define': _info.get('fixed_col_define', {})
                }

                if _info.get('index_only', True):
                    # 只用于索引, 不创建
                    continue

                if await self.collections_exists(_collection):
                    # 表已存在
                    continue

                # 建表操作
                await self.create_collection(
                    _collection, **_info
                )

        # 切换回开始的数据库
        await self.switch_db(_temp_name)

    #############################
    # 需要继承类实现的内部函数
    #############################
    def _get_db_creator(self, connect_config: dict, pool_config: dict, driver_config: dict) -> dict:
        """
        获取数据库连接驱动及参数(同步函数)

        @param {dict} connect_config - 外部送入的连接参数
        @param {dict} pool_config - 连接池配置
        @param {dict} driver_config={} - 驱动配置

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
        raise NotImplementedError()

    async def _generate_sqls(self, op: str, *args, **kwargs) -> tuple:
        """
        生成对应操作要执行的sql语句数组(同步或异步函数)

        @param {str} op - 要执行的操作(传入函数名字符串)
        @param {args} - 要执行操作函数的固定位置入参
        @param {kwargs} - 要执行操作函数的kv入参

        @returns {tuple} - 返回要执行的sql信息(sqls, sql_paras, execute_paras, checks)
            sqls: list, 要顺序执行的sql语句数组; 注意, 仅最后一个语句支持为查询语句, 前面的语句都必须为非查询语句
            sql_paras: list, 传入的SQL参数字典(支持?占位), 注意必须与sqls数组一一对应(如果只有个别语句需要传参, 其他位置设置为None; 如果全部都无需传参, 该值直接传None)
            execute_paras: dict, 最后一个SQL语句的执行参数 {'is_query': ...}
            checks: list, 传入每个语句执行检查字典列表, 注意必须与sqls数组一一对应(如果只有个别语句需要传参, 其他位置设置为None; 如果全部都无需传参, 该值直接传None)
        """
        raise NotImplementedError()

    async def _format_row_value(self, row: list) -> list:
        """
        处理行记录的值(数据库存储类型转为Python类型)
        (同步函数)

        @param {list} row - 行记录

        @returns {list} - 转换后的行记录
        """
        raise NotImplementedError()

    async def _driver_after_init_pool(self):
        """
        初始化连接池以后驱动执行的处理(同步或异步函数)
        """
        pass

    async def _driver_init_connection(self, conn: Any):
        """
        驱动对获取到的连接的初始化处理(同步或异步函数)

        @param {Any} conn - 传入连接对象
        """
        pass

    async def _get_cols_info(self, collection: str, session: Any = None) -> list:
        """
        获取制定集合(表)的列信息(同步或异步函数)

        @param {str} collection - 集合名(表)
        @param {Any} session=None - 指定事务连接对象

        @returns {list} - 字典形式的列信息数组, 注意列名为name, 类型为type(类型应为标准类型: str, int, float, bool, json)
        """
        return []

    async def _get_current_db_name(self, session: Any = None) -> str:
        """
        获取当前数据库名

        @param {Any} session=None - 指定事务连接对象

        @returns {str} - 数据库名
        """
        return None
