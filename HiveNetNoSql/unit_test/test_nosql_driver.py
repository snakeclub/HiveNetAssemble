#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import sys
import unittest
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.test_tool import TestTool
from HiveNetCore.utils.file_tool import FileTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetNoSql.base.driver_fw import NosqlDriverFW
from HiveNetNoSql.sqlite import SQLiteNosqlDriver
from HiveNetNoSql.mongo import MongoNosqlDriver
from HiveNetNoSql.mysql import MySQLNosqlDriver
from HiveNetNoSql.pgsql import PgSQLNosqlDriver


class DriverTestCaseFW(object):
    """
    通用的驱动测试基础类
    """
    #############################
    # 不同驱动自有的测试方法
    #############################

    def __init__(self) -> None:
        """
        构造函数
        注: 需要把驱动对象设置到 self.driver 变量上, 驱动标识设置到 self.driver_id
        """
        self.driver = NosqlDriverFW()
        self.driver_id = ''

    @property
    def self_test_order(self) -> list:
        """
        当前驱动自有的测试清单
        """
        return []

    def destroy(self):
        """
        销毁连接
        """
        # 删除测试的库
        for _db_name in ['memory', 'db_init_test', 'db_test1', 'db_test2', 'db_del_test1', 'db_del_test2']:
            try:
                # AsyncTools.sync_run_coroutine(self.driver.drop_db(_db_name))
                pass
            except:
                pass
        AsyncTools.sync_run_coroutine(self.driver.destroy())

    #############################
    # 可能有个性的测试数据
    #############################
    @property
    def init_db(self) -> dict:
        """
        启动时创建数据库的参数
        """
        return {
            'memory': {
                'index_only': False,
                'comment': '内存数据库'
            },
            'db_init_test': {
                'index_only': False,
                'comment': '初始化测试库'
            }
        }

    @property
    def test_db_info(self) -> list:
        """
        测试数据库信息
        返回[(数据库名, 固定创建参数, kv创建参数), ...]
        """
        return [('db_test1', [], {}), ('db_test2', [], {})]

    @property
    def delete_db_info(self):
        """
        删除数据库信息
        返回[(数据库名, 固定创建参数, kv创建参数), ...]
        """
        return [('db_del_test1', [], {}), ('db_del_test2', [], {})]

    #############################
    # 自有的测试函数
    #############################
    def self_test_attach_dbs_1(self) -> tuple:
        _tips = '测试启动创建数据库1'
        _dbs = AsyncTools.sync_run_coroutine(self.driver.list_dbs())
        return (
            TestTool.cmp_list(_dbs, ['main', 'memory', 'db_init_test']),
            _tips,
            _dbs
        )

    #############################
    # 通用的配置属性
    #############################

    @property
    def common_test_order(self) -> list:
        """
        通用测试清单
        """
        return [
            'test_init_collections_1',
            'test_create_db_2',
            'test_drop_db_3',
            'test_create_collection_1',
            'test_drop_collection_2',
            'test_list_collections_3',
            'test_turncate_collection_4',
            'test_insert_one_1',
            'test_insert_many_2',
            'test_update_3',
            'test_update_4',
            'test_delete_5',
            'test_query_list_1',
            'test_query_list_2',
            'test_query_aggregate_3',
            'test_query_aggregate_4',
            'test_page_1',
            'test_data_type_1',
            'test_special_char2',
            'test_null_data_3',
            'test_json_path_1',
            'test_left_join_1',
            'test_transaction_1'
        ]

    @property
    def init_collections(self) -> dict:
        """
        驱动启动时要创建的集合
        """
        return {
            # 在memory库创建表
            'memory': {
                'tb_init_on_memory': {
                    'index_only': False,
                    'comment': '初始化在内存库的表"\',\\"',
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
                        'c_index': {'type': 'str', 'len': 20, 'comment': '索引, 字符类型字段, 特殊字符"\',\\"', 'nullable': True},
                        'c_str': {'type': 'str', 'len': 50, 'comment': '字符类型字段', 'nullable': False, 'default': '"\''},
                        'c_bool': {'type': 'bool', 'comment': '布尔类型字段', 'nullable': False, 'default': True},
                        'c_int': {'type': 'int', 'comment': 'int类型字段', 'nullable': False, 'default': 10},
                        'c_float': {'type': 'float', 'comment': 'float类型字段'},
                        'c_json': {'type': 'json', 'comment': 'json类型字段', 'nullable': False, 'default': {"a": "b"}}
                    }
                }
            },
            # 在db_init_test上创建表
            'db_init_test': {
                'tb_init_on_db_init_test': {
                    'index_only': False,
                    'comment': '初始化在测试库的表',
                    'indexs': None,
                    'fixed_col_define': {
                        'c_index': {'type': 'str', 'len': 20, 'comment': '索引, 字符类型字段'},
                        'c_str': {'type': 'str', 'len': 50, 'comment': '字符类型字段'},
                        'c_bool': {'type': 'bool', 'comment': '布尔类型字段'},
                        'c_int': {'type': 'int', 'comment': 'int类型字段'},
                        'c_float': {'type': 'float', 'comment': 'float类型字段'},
                        'c_json': {'type': 'json', 'comment': 'json类型字段'}
                    }
                }
            }
        }

    #############################
    # 测试数据库操作相关
    #############################

    def test_init_collections_1(self):
        _tips = '测试1: 启动创建表'
        AsyncTools.sync_run_coroutine(self.driver.switch_db('memory'))
        _m_tabs = AsyncTools.sync_run_coroutine(self.driver.list_collections())
        AsyncTools.sync_run_coroutine(self.driver.switch_db('db_init_test'))
        _ts_tabs = AsyncTools.sync_run_coroutine(self.driver.list_collections())
        return (
            TestTool.cmp_list(_m_tabs, ['tb_init_on_memory']) and TestTool.cmp_list(_ts_tabs, ['tb_init_on_db_init_test']),
            _tips, 'memory: %s, db_init_test: %s' % (str(_m_tabs), str(_ts_tabs))
        )

    def test_create_db_2(self):
        _tips = '测试2: 创建数据库及空表'
        _db_names = []
        for _db_info in self.test_db_info:
            # 创建数据库
            _db_names.append(_db_info[0])
            AsyncTools.sync_run_coroutine(self.driver.create_db(_db_info[0], *_db_info[1], **_db_info[2]))
            # 应自动切换到了新数据库, 创建空表
            AsyncTools.sync_run_coroutine(self.driver.create_collection('tb_null'))

        # 验证数据库是否创建成功
        _dbs = AsyncTools.sync_run_coroutine(self.driver.list_dbs())
        for _name in _db_names:
            if _name not in _dbs:
                return (False, _tips, 'db not exists: %s' % _name)

            # 验证空表是否存在
            AsyncTools.sync_run_coroutine(self.driver.switch_db(_name))
            if not AsyncTools.sync_run_coroutine(self.driver.collections_exists('tb_null')):
                return (False, _tips, 'table [tb_null] not exists on [%s]' % _name)

        # 返回成功
        return (True, _tips, '')

    def test_drop_db_3(self):
        _tips = '测试3: 删除数据库'
        _db_names = []
        for _db_info in self.delete_db_info:
            # 创建数据库
            _db_names.append(_db_info[0])
            AsyncTools.sync_run_coroutine(self.driver.create_db(_db_info[0], *_db_info[1], **_db_info[2]))

            # 应自动切换到了新数据库, 创建空表
            AsyncTools.sync_run_coroutine(self.driver.create_collection('tb_null_del'))

        for _name in _db_names:
            # 检查数据库是否创建成功
            _dbs = AsyncTools.sync_run_coroutine(self.driver.list_dbs())
            if _name not in _dbs:
                return (False, _tips, 'create del db error: %s' % _name)

            # 切换到要删除的数据库, 然后删除数据库
            AsyncTools.sync_run_coroutine(self.driver.switch_db(_name))
            AsyncTools.sync_run_coroutine(self.driver.drop_db(_name))

            # 检查数据库是否已被删除
            _dbs = AsyncTools.sync_run_coroutine(self.driver.list_dbs())
            if _name in _dbs:
                return (False, _tips, 'del db drop error: %s' % _name)

            if self.driver.db_name != _dbs[0]:
                return (False, _tips, 'current db error after drop db: %s' % _name)

        # 返回成功
        return (True, _tips, '')

    #############################
    # 测试集合操作相关
    #############################

    def test_create_collection_1(self):
        _tips = '集合测试1: 创建集合'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]

        # 两个库创建一摸一样的表
        for _db in _test_dbs:
            AsyncTools.sync_run_coroutine(self.driver.switch_db(_db))

            # 先删除表
            try:
                AsyncTools.sync_run_coroutine(self.driver.drop_collection('tb_full_type'))
            except:
                pass

            # tb_full_type
            AsyncTools.sync_run_coroutine(
                self.driver.create_collection(
                    'tb_full_type', indexs={
                        '%s_idx_tb_full_type_c_index' % _db: {
                            'keys': {
                                'c_index': {'asc': 1}
                            },
                            'paras': {
                                'unique': False
                            }
                        }
                    },
                    fixed_col_define={
                        'c_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
                        'c_str': {'type': 'str', 'len': 50, 'comment': '注释2'},
                        'c_str_no_len': {'type': 'str', 'comment': '注释3'},
                        'c_bool': {'type': 'bool'},
                        'c_int': {'type': 'int'},
                        'c_float': {'type': 'float'},
                        'c_json': {'type': 'json', 'comment': '注释4'}
                    },
                    comment='空类型表'
                )
            )

            # 检查表是否创建成功
            if not AsyncTools.sync_run_coroutine(self.driver.collections_exists('tb_full_type')):
                return (False, _tips, 'table [%s] not exists on db [%s]' % ('tb_full_type', _db))

        # 返回成功
        return (True, _tips, '')

    def test_drop_collection_2(self):
        _tips = '集合测试2: 删除集合'
        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        for _db in _test_dbs:
            AsyncTools.sync_run_coroutine(self.driver.switch_db(_db))

            # tb_drop_table
            AsyncTools.sync_run_coroutine(
                self.driver.create_collection(
                    'tb_drop_table', indexs={
                        'idx_tb_drop_table_c_index': {
                            'keys': {
                                'c_index': {'asc': 1}
                            }
                        }
                    },
                    fixed_col_define={
                        'c_index': {'type': 'str', 'len': 20}
                    }
                )
            )

            # 检查表是否创建成功
            if not AsyncTools.sync_run_coroutine(self.driver.collections_exists('tb_drop_table')):
                return (False, _tips, 'table [%s] create error on db [%s]' % ('tb_drop_table', _db))

            # 删除表
            AsyncTools.sync_run_coroutine(self.driver.drop_collection('tb_drop_table'))
            if AsyncTools.sync_run_coroutine(self.driver.collections_exists('tb_drop_table')):
                return (False, _tips, 'table [%s] drop error on db [%s]' % ('tb_drop_table', _db))

        # 返回成功
        return (True, _tips, '')

    def test_list_collections_3(self):
        _tips = '集合测试3: 获取集合清单'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]

        # 添加一个表
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))
        AsyncTools.sync_run_coroutine(self.driver.create_collection('tb_test_list'))

        # 删除历史测试表
        _tab_list = ['tb_left_join_main', 'tb_left_join_sub1', 'tb_left_join_sub2']
        for _tab in _tab_list:
            try:
                AsyncTools.sync_run_coroutine(self.driver.drop_collection(_tab))
            except:
                pass

        # 查询所有表
        _list = AsyncTools.sync_run_coroutine(self.driver.list_collections())
        if not TestTool.cmp_list(_list, ['tb_full_type', 'tb_null', 'tb_test_list'], sorted=True):
            return (False, _tips, 'list all collection error')

        _list = AsyncTools.sync_run_coroutine(self.driver.list_collections(filter={}))
        if not TestTool.cmp_list(_list, ['tb_full_type', 'tb_null', 'tb_test_list'], sorted=True):
            return (False, _tips, 'list all collection by null dict error')

        # 通过表名获取表
        _list = AsyncTools.sync_run_coroutine(self.driver.list_collections(
            filter={'name': 'tb_test_list'}
        ))
        if _list[0] != 'tb_test_list':
            return (False, _tips, 'list collection by name error')

        # 通过正则表达式获取表
        _list = AsyncTools.sync_run_coroutine(self.driver.list_collections(
            filter={'name': {'$regex': 'll'}}
        ))
        if not TestTool.cmp_list(_list, ['tb_full_type', 'tb_null'], sorted=True):
            return (False, _tips, 'list all collection by regex error')

        # 切换第2个库
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[1]))
        # 查询所有表
        _list = AsyncTools.sync_run_coroutine(self.driver.list_collections())
        if not TestTool.cmp_list(_list, ['tb_full_type', 'tb_null'], sorted=True):
            return (False, _tips, 'list all collection error on db: %s' % _test_dbs[1])

        # 返回成功
        return (True, _tips, '')

    def test_turncate_collection_4(self):
        _tips = '集合测试4: 清空集合'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]

        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type')
        )
        if _ret != 0:
            return (False, _tips, 'turncate collection error: %s' % str(_ret))

        # 插入数据
        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            'tb_full_type', rows=[
                {'c_index': 'i1', 'c_int': 1, 'n_str': 'ext_str1', 'n_bool': True},
                {'c_index': 'i2', 'c_int': 2, 'n_str': 'ext_str2', 'n_bool': True},
                {'c_index': 'i3', 'c_int': 3, 'n_str': 'ext_str3', 'n_bool': False},
                {'c_index': 'i4', 'c_int': 4, 'n_str': 'ext_str4', 'n_bool': True},
            ]
        ))
        if _ret != 4:
            return (False, _tips, 'insert test data error, insert count: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type')
        )
        if _ret != 4:
            return (False, _tips, 'count insert data error: %s' % str(_ret))

        # 清空表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type')
        )
        if _ret != 0:
            return (False, _tips, 'turncate collection error: %s' % str(_ret))

        # 返回成功
        return (True, _tips, '')

    #############################
    # 测试数据操作相关
    #############################

    def test_insert_one_1(self):
        _tips = '集合数据操作1: 插入单条记录'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_null'))
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))

        # 插入记录, 注意插入函数有可能会改变传入的字典值
        _row = {
            'n_str': 'str', 'n_bool': True, 'n_int': 1, 'n_float': 0.1, 'n_dict': {'d1': 'v1', 'd2': 2},
            'n_list': ['a', 'b', 'c']
        }
        _id = AsyncTools.sync_run_coroutine(
            self.driver.insert_one(
                'tb_null', _row
            )
        )
        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list('tb_null', filter={'_id': _id}))
        if len(_ret) > 0:
            _ret[0].pop('_id', None)
            _row.pop('_id', None)

        if len(_ret) != 1 or not TestTool.cmp_dict(_row, _ret[0]):
            return (False, _tips, 'insert one 1 error: %s' % str(_ret))

        # 插入全类型表, 注意固定字段里的bool类型，sqlite里返回的是0, 1, 而不是True/False
        _row = {
            'c_index': 'i1', 'c_str': 's1', 'c_str_no_len': 's2', 'c_bool': False, 'c_int': 1,
            'c_float': 1.3, 'c_json': {'jbool': True}, 'n_bool': False, 'n_str': 'nstr1'
        }
        _id = AsyncTools.sync_run_coroutine(
            self.driver.insert_one('tb_full_type', _row)
        )
        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list('tb_full_type', filter={'_id': _id}))

        if len(_ret) > 0:
            _ret[0].pop('_id', None)
            _row.pop('_id', None)

        if len(_ret) != 1 or not TestTool.cmp_dict(_row, _ret[0]):
            return (False, _tips, 'insert one 2 error: %s' % str(_ret))

        # 插入全类型表, 字段不完整
        _row = {
            'c_index': 'i2', 'c_str': 's2'
        }
        _id = AsyncTools.sync_run_coroutine(
            self.driver.insert_one('tb_full_type', _row)
        )
        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list('tb_full_type', filter={'_id': _id}))

        if len(_ret) > 0:
            _ret[0].pop('_id', None)
            _row.pop('_id', None)

        if len(_ret) != 1 or not TestTool.cmp_dict(_row, _ret[0]):
            return (False, _tips, 'insert one 3 error: %s' % str(_ret))

        return (True, _tips, '')

    def test_insert_many_2(self):
        _tips = '集合数据操作2: 插入多条记录'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_null'))
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                'tb_null', [
                    {'a1': 'a1v', 'a2': 'a2v', 'a3': 3, 'a4': True},
                    {'b1': 'b1v', 'b2': 'b2v', 'b3': 4, 'b4': False, 'fullkey': 'test'},
                    {'c1': 'c1v', 'c2': 'c2v', 'c3': 5, 'c4': False},
                ]
            )
        )
        if _ret != 3:
            return (False, _tips, 'insert num 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list('tb_null', filter={'b1': 'b1v'}))
        _ret[0].pop('_id', None)
        if not TestTool.cmp_dict(_ret[0], {'b1': 'b1v', 'b2': 'b2v', 'b3': 4, 'b4': False, 'fullkey': 'test'}):
            return (False, _tips, 'insert data 2 error: %s' % str(_ret))

        # 插入第二个表
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                'tb_full_type', [
                    {'a1': 'a1v', 'a2': 'a2v', 'a3': 3, 'a4': True},
                    {'c_index': 'i1', 'b1': 'b1v', 'b2': 'b2v', 'b3': 4, 'b4': False, 'fullkey': 'test'},
                    {'c1': 'c1v', 'c2': 'c2v', 'c3': 5, 'c4': False},
                ]
            )
        )
        if _ret != 3:
            return (False, _tips, 'insert num 3 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list('tb_full_type', filter={'b1': 'b1v'}))
        _ret[0].pop('_id', None)
        if not TestTool.cmp_dict(_ret[0], {'c_index': 'i1', 'b1': 'b1v', 'b2': 'b2v', 'b3': 4, 'b4': False, 'fullkey': 'test'}):
            return (False, _tips, 'insert data 4 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_count('tb_full_type'))
        if _ret != 3:
            return (False, _tips, 'insert num 5 error: %s' % str(_ret))

        # 切换到另外一个库, 数据查不到
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[1]))
        _ret = AsyncTools.sync_run_coroutine(self.driver.query_count('tb_full_type'))
        if _ret > 0:
            return (False, _tips, 'insert to wrong db: %s' % str(_ret))

        return (True, _tips, '')

    def test_update_3(self):
        _tips = '集合数据操作3: 更新记录(全部为扩展字段)'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_null'))

        # 测试更新
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                'tb_null', [
                    {'a1': 'a1v', 'a2': 'a2v', 'a3': 3, 'a4': True, 'inc': 2, 'mul': 3, 'min': 2, 'max': 3},
                    {'a1': 'a1v', 'b2': 'b2v', 'b3': 4, 'b4': False, 'fullkey': 'test'},
                    {'a1': 'c1v', 'c2': 'c2v', 'c3': 5, 'c4': False},
                ]
            )
        )
        if _ret != 3:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # 更新一条记录
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_null', filter={'a1': 'a1v'}, update={
                '$set': {'a2': 'a2u', 'b2': 'b2u', 'a4': False},
                '$inc': {'inc': 6, 'no_inc': 6}, '$mul': {'mul': 4, 'no_mul': 4},
                '$min': {'min': 1, 'no_min': 1}, '$max': {'max': 4, 'no_max': 4}
            }, multi=False
        ))
        if _ret != 1:
            return (False, _tips, 'update no multi 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_null', filter={'a1': 'a1v', 'a2': 'a2u'},
                projection=['a2', 'b2', 'a4', 'inc', 'no_inc', 'mul', 'no_mul', 'min', 'no_min', 'max', 'no_max'],
                limit=1
            )
        )
        _ret[0].pop('_id', None)
        if not TestTool.cmp_dict(_ret[0], {
            'a2': 'a2u', 'b2': 'b2u', 'a4': False, 'inc': 8, 'no_inc': 6,
            'mul': 12, 'no_mul': 0, 'min': 1, 'no_min': 1, 'max': 4, 'no_max': 4
        }):
            return (False, _tips, 'update no multi 2 error: %s' % str(_ret))

        # 更新多条记录
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_null', filter={'a1': 'a1v'}, update={
                '$set': {'a2': 'a2uu'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, multi=True
        ))
        if _ret != 2:
            return (False, _tips, 'update no multi 3 error: %s' % str(_ret))

        # 找不到记录更新
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_null', filter={'a1': 'no_exists'}, update={
                '$set': {'a2': 'a2uu'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, multi=True, upsert=False
        ))
        if _ret != 0:
            return (False, _tips, 'update no exists 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_null', filter={'a1': 'no_exists'}, update={
                '$set': {'a2': 'a2uu'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, upsert=True
        ))
        if _ret != 0:
            return (False, _tips, 'update no exists upsert 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_null', filter={'a1': 'no_exists'}
            )
        )

        _ret[0].pop('_id', None)
        if not TestTool.cmp_dict(_ret[0], {
            'a1': 'no_exists', 'a2': 'a2uu', 'inc': -3, 'no_inc': 3
        }):
            return (False, _tips, 'update no exists upsert 2 error: %s' % str(_ret))

        # 插入条件特殊的情况
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_null', filter={'a1': 'no_exists', 'ver': {'$lt': '0.0.1'}}, update={
                '$set': {'a2': 'a2uu'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, upsert=True
        ))
        if _ret != 0:
            return (False, _tips, 'update no exists upsert 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                'tb_null', filter={'a1': 'no_exists'}
            )
        )
        if _ret != 2:
            return (False, _tips, 'update no exists upsert 2 error: %s' % str(_ret))

        return (True, _tips, '')

    def test_update_4(self):
        _tips = '集合数据操作4: 更新记录(有固定字段)'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                'tb_full_type', [
                    {'c_index': 'i1', 'c_str': 'str1', 'c_bool': True, 'c_int': 2, 'c_float': 3.1, 'j_int': 4, 'j_float': 5.1},
                    {'c_index': 'i2', 'c_str': 'str2', 'c_bool': False, 'j_int': 4, 'j_float': 5.1},
                    {'c_index': 'i3', 'c_str': 'str1', 'c_bool': False, 'j_float': 10.1, 'j_int': 11}
                ]
            )
        )
        if _ret != 3:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # 更新一条记录
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_full_type', filter={'c_str': 'str1'}, update={
                '$set': {'c_bool': False, 'b2': 'b2u'},
                '$inc': {'c_int': 6, 'no_inc': 6}, '$mul': {'j_int': 4, 'no_mul': 4},
                '$min': {'c_float': 1, 'no_min': 1}, '$max': {'j_float': 4, 'no_max': 4}
            }, multi=False
        ))
        if _ret != 1:
            return (False, _tips, 'update no multi 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_full_type', filter={'c_str': 'str1', 'b2': 'b2u'},
                projection=['c_bool', 'b2', 'c_int', 'no_inc', 'j_int', 'no_mul', 'c_float', 'no_min', 'j_float', 'no_max'],
                limit=1
            )
        )
        _ret[0].pop('_id', None)
        if not TestTool.cmp_dict(_ret[0], {
            'c_bool': False, 'b2': 'b2u', 'c_int': 8, 'no_inc': 6,
            'j_int': 16, 'no_mul': 0, 'c_float': 1.0, 'no_min': 1, 'j_float': 5.1, 'no_max': 4
        }):
            return (False, _tips, 'update no multi 2 error: %s' % str(_ret))

        # 更新多条记录
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_full_type', filter={'c_str': 'str1'}, update={
                '$set': {'a2': 'a2uu'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, multi=True
        ))
        if _ret != 2:
            return (False, _tips, 'update no multi 3 error: %s' % str(_ret))

        # 找不到记录更新
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_full_type', filter={'c_index': 'no_exists'}, update={
                '$set': {'a2': 'a2uu', 'c_str': 'str1upd'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, multi=True, upsert=False
        ))
        if _ret != 0:
            return (False, _tips, 'update no exists 1 error: %s' % str(_ret))

        # 找不到记录, 插入新的
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_full_type', filter={'c_index': 'no_exists'}, update={
                '$set': {'a2': 'a2uu', 'c_str': 'str1upd'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, multi=True, upsert=True
        ))
        if _ret != 0:
            return (False, _tips, 'update no exists 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_full_type', filter={'c_index': 'no_exists'}
            )
        )

        _ret[0].pop('_id', None)
        if not TestTool.cmp_dict(_ret[0], {
            'c_index': 'no_exists', 'a2': 'a2uu', 'c_str': 'str1upd', 'inc': -3, 'no_inc': 3
        }):
            return (False, _tips, 'uupdate no exists upsert 2 error: %s' % str(_ret))

        # 插入特殊值
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            'tb_full_type', filter={'c_index': 'no_exists', 'c_int': {'$gt': 10}}, update={
                '$set': {'a2': 'a2uu', 'c_str': 'str1upd'},
                '$inc': {'inc': -3, 'no_inc': 3}
            }, multi=True, upsert=True
        ))
        if _ret != 0:
            return (False, _tips, 'update no exists 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                'tb_full_type', filter={'c_index': 'no_exists'}
            )
        )
        if _ret != 2:
            return (False, _tips, 'update no exists upsert 2 error: %s' % str(_ret))

        return (True, _tips, '')

    def test_delete_5(self):
        _tips = '集合数据操作5: 删除记录'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_null'))
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))

        # 无固定字段表的删除处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                'tb_null', [
                    {'a1': 'a1v', 'a2': 'a2v', 'a3': 3, 'a4': True, 'inc': 2, 'mul': 3, 'min': 2, 'max': 3},
                    {'a1': 'a1v', 'b2': 'b2v', 'b3': 4, 'b4': False, 'fullkey': 'test'},
                    {'a1': 'a1v', 'b2': 'b2v3', 'b3': 6, 'b4': True, 'fullkey': 'test1'},
                    {'a1': 'c1v', 'c2': 'c2v', 'c3': 5, 'c4': False},
                ]
            )
        )
        if _ret != 4:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.delete('tb_null', filter={'a1': 'a1v'}, multi=False)
        )
        if _ret != 1:
            return (False, _tips, 'delete no multi 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.delete('tb_null', filter={'a1': 'a1v'}, multi=True)
        )
        if _ret != 2:
            return (False, _tips, 'delete multi 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                'tb_null', filter={'a1': 'a1v'}
            )
        )
        if _ret != 0:
            return (False, _tips, 'delete multi 2 error: %s' % str(_ret))

        # 有固定字段的删除处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                'tb_full_type', [
                    {'c_index': 'i1', 'c_str': 'str1', 'c_bool': True, 'c_int': 2, 'c_float': 3.1, 'j_int': 4, 'j_float': 5.1, 'n_index': 10},
                    {'c_index': 'i2', 'c_str': 'str2', 'c_bool': False, 'j_int': 4, 'j_float': 5.1, 'n_index': 11},
                    {'c_index': 'i3', 'c_str': 'str1', 'c_bool': False, 'j_float': 10.1, 'j_int': 11, 'n_index': 10},
                    {'c_index': 'i4', 'c_str': 'str1', 'c_bool': False, 'j_float': 10.1, 'j_int': 11, 'n_index': 10}
                ]
            )
        )
        if _ret != 4:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.delete('tb_full_type', filter={'c_str': 'str1', 'n_index': 10}, multi=False)
        )
        if _ret != 1:
            return (False, _tips, 'delete full type no multi 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.delete('tb_full_type', filter={'c_str': 'str1', 'n_index': 10}, multi=True)
        )
        if _ret != 2:
            return (False, _tips, 'delete full type multi 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                'tb_full_type', filter={'c_str': 'str1'}
            )
        )
        if _ret != 0:
            return (False, _tips, 'delete full type multi 2 error: %s' % str(_ret))

        return (True, _tips, '')

    #############################
    # 查询相关
    #############################

    def test_query_list_1(self):
        _tips = '集合数据查询1: 列表查询(无固定字段)'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_null'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 无固定字段表的查询处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1', 'c_str': 'str1', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True
                    },
                    {
                        'c_index': 'i2', 'c_str': 'str2', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 2,
                        'c_float': 0.2, 'c_json': {'cj_1': 'cj_str_2', 'cj_2': False},
                        'n_str': 'nstr2', 'n_int': 20, 'n_bool': True
                    },
                    {
                        'c_index': 'i3', 'c_str': 'str1', 'c_str_no_len': 'nostr3', 'c_bool': True, 'c_int': 3,
                        'c_float': 0.3, 'c_json': {'cj_1': 'cj_str_3', 'cj_2': False},
                        'n_str': 'nstr3', 'n_int': 30, 'n_bool': True
                    },
                    {
                        'c_index': 'i4', 'c_str': 'str1', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 4,
                        'c_float': 0.4, 'c_json': {'cj_1': 'cj_str_4', 'cj_2': False},
                        'n_str': 'nstr4', 'n_int': 40, 'n_bool': True
                    },
                    {
                        'c_index': 'i5', 'c_str': 'str5', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 5,
                        'c_float': 0.5, 'c_json': {'cj_1': 'cj_str_5', 'cj_2': False},
                        'n_str': 'nstr5', 'n_int': 50, 'n_bool': True
                    },
                    {
                        'c_index': 'i6', 'c_str': 'str6', 'c_str_no_len': 'nostr6', 'c_bool': True, 'c_int': 6,
                        'c_float': 0.6, 'c_json': {'cj_1': 'cj_str_6', 'cj_2': False},
                        'n_str': 'nstr6', 'n_int': 60, 'n_bool': True
                    }
                ]
            )
        )
        if _ret != 6:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={}, projection={'_id': False, 'c_index': True},
                sort=[('c_index', -1)]
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i6', 'i5', 'i4', 'i3', 'i2', 'i1']):
            return (False, _tips, 'query list sorted 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_iter(
            _table_name, filter={}, projection={'_id': False, 'c_index': True},
            sort=[('c_index', -1)]
        ))
        _ret_list = []

        def test_query_iter1(query_list, upd_list):
            for _item in query_list:
                upd_list.append(_item['c_index'])

        AsyncTools.sync_run_coroutine(AsyncTools.async_for_iter(
            _ret, test_query_iter1, _ret_list
        ))

        if not TestTool.cmp_list(_ret_list, ['i6', 'i5', 'i4', 'i3', 'i2', 'i1']):
            return (False, _tips, 'query list sorted 2 error: %s' % str(_ret))

        # 通过两个字段排序
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={}, projection={'_id': False, 'c_index': True},
                sort=[('c_str', 1), ('c_index', -1)]
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i4', 'i3', 'i1', 'i2', 'i5', 'i6']):
            return (False, _tips, 'query list sorted 1 error: %s' % str(_ret))

        # 各种条件查询$or
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={
                    'n_int': {'$lte': 30}, '$or': [{'c_str_no_len': 'nostr2'}, {'c_str_no_len': 'nostr3'}]
                },
                projection={'_id': False, 'c_index': True},
                sort=[('c_index', -1)]
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i3', 'i2']):
            return (False, _tips, 'query list sorted 2 error: %s' % str(_ret))

        # 各种条件查询$lt $gt
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'n_int': {'$lt': 30, '$gt': 10}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i2']):
            return (False, _tips, 'query list sorted 3 error: %s' % str(_ret))

        # 各种条件查询$ne
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_str': {'$ne': 'str1'}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i2', 'i5', 'i6']):
            return (False, _tips, 'query list sorted 4 error: %s' % str(_ret))

        # 各种条件查询$regex 不以2结尾
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_str_no_len': {"$regex": r"^((?!2$).)*$"}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i1', 'i3', 'i5', 'i6']):
            return (False, _tips, 'query list sorted 5 error: %s' % str(_ret))

        # skip和limit
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={}, projection={'_id': False, 'c_index': True},
                sort=[('c_str', 1), ('c_index', -1)],
                skip=2, limit=3
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i1', 'i2', 'i5']):
            return (False, _tips, 'query list skip 1 error: %s' % str(_ret))

        return (True, _tips, '')

    def test_query_list_2(self):
        _tips = '集合数据查询2: 列表查询(固定字段)'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_full_type'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 无固定字段表的查询处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1', 'c_str': 'str1', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True
                    },
                    {
                        'c_index': 'i2', 'c_str': 'str2', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 2,
                        'c_float': 0.2, 'c_json': {'cj_1': 'cj_str_2', 'cj_2': False},
                        'n_str': 'nstr2', 'n_int': 20, 'n_bool': True
                    },
                    {
                        'c_index': 'i3', 'c_str': 'str1', 'c_str_no_len': 'nostr3', 'c_bool': True, 'c_int': 3,
                        'c_float': 0.3, 'c_json': {'cj_1': 'cj_str_3', 'cj_2': False},
                        'n_str': 'nstr3', 'n_int': 30, 'n_bool': True
                    },
                    {
                        'c_index': 'i4', 'c_str': 'str1', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 4,
                        'c_float': 0.4, 'c_json': {'cj_1': 'cj_str_4', 'cj_2': False},
                        'n_str': 'nstr4', 'n_int': 40, 'n_bool': True
                    },
                    {
                        'c_index': 'i5', 'c_str': 'str5', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 5,
                        'c_float': 0.5, 'c_json': {'cj_1': 'cj_str_5', 'cj_2': False},
                        'n_str': 'nstr5', 'n_int': 50, 'n_bool': True
                    },
                    {
                        'c_index': 'i6', 'c_str': 'str6', 'c_str_no_len': 'nostr6', 'c_bool': True, 'c_int': 6,
                        'c_float': 0.6, 'c_json': {'cj_1': 'cj_str_6', 'cj_2': False},
                        'n_str': 'nstr6', 'n_int': 60, 'n_bool': True
                    }
                ]
            )
        )
        if _ret != 6:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={}, projection={'_id': False, 'c_index': True},
                sort=[('c_index', -1)]
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i6', 'i5', 'i4', 'i3', 'i2', 'i1']):
            return (False, _tips, 'query list sorted 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_iter(
            _table_name, filter={}, projection={'_id': False, 'c_index': True},
            sort=[('c_index', -1)]
        ))
        _ret_list = []

        def test_query_iter1(query_list, upd_list):
            for _item in query_list:
                upd_list.append(_item['c_index'])

        AsyncTools.sync_run_coroutine(AsyncTools.async_for_iter(
            _ret, test_query_iter1, _ret_list
        ))

        if not TestTool.cmp_list(_ret_list, ['i6', 'i5', 'i4', 'i3', 'i2', 'i1']):
            return (False, _tips, 'query list sorted 2 error: %s' % str(_ret))

        # 通过两个字段排序
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={}, projection={'_id': False, 'c_index': True},
                sort=[('c_str', 1), ('c_index', -1)]
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i4', 'i3', 'i1', 'i2', 'i5', 'i6']):
            return (False, _tips, 'query list sorted 1 error: %s' % str(_ret))

        # 各种条件查询$or
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={
                    'n_int': {'$lte': 30}, '$or': [{'c_str_no_len': 'nostr2'}, {'c_str_no_len': 'nostr3'}]
                },
                projection={'_id': False, 'c_index': True},
                sort=[('c_index', -1)]
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i3', 'i2']):
            return (False, _tips, 'query list sorted 2 error: %s' % str(_ret))

        # 各种条件查询$lt $gt
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'n_int': {'$lt': 30, '$gt': 10}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i2']):
            return (False, _tips, 'query list sorted 3 error: %s' % str(_ret))

        # 各种条件查询$ne
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_str': {'$ne': 'str1'}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i2', 'i5', 'i6']):
            return (False, _tips, 'query list sorted 4 error: %s' % str(_ret))

        # 各种条件查询$in
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_str': {'$in': ['str1', 'str2']}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i1', 'i2', 'i3', 'i4']):
            return (False, _tips, 'query list in 4 - 1 error: %s' % str(_ret))

        # 各种条件查询$in
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_str': {'$nin': ['str1', 'str2']}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i5', 'i6']):
            return (False, _tips, 'query list in 4 - 2 error: %s' % str(_ret))

        # 各种条件查询$regex 不以2结尾
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_str_no_len': {"$regex": r"^((?!2$).)*$"}},
                projection={'_id': False, 'c_index': True},
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i1', 'i3', 'i5', 'i6']):
            return (False, _tips, 'query list sorted 5 error: %s' % str(_ret))

        # skip和limit
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={}, projection={'_id': False, 'c_index': True},
                sort=[('c_str', 1), ('c_index', -1)],
                skip=2, limit=3
            )
        )
        _ret_list = [_item['c_index'] for _item in _ret]
        if not TestTool.cmp_list(_ret_list, ['i1', 'i2', 'i5']):
            return (False, _tips, 'query list skip 1 error: %s' % str(_ret))

        return (True, _tips, '')

    def test_query_aggregate_3(self):
        _tips = '集合数据查询3: 聚合查询(无固定字段)'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_null'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 无固定字段表的查询处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1', 'c_str': 'str1', 'c_str_no_len': 'nostr1', 'c_bool': False, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True
                    },
                    {
                        'c_index': 'i2', 'c_str': 'str2', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 2,
                        'c_float': 0.2, 'c_json': {'cj_1': 'cj_str_2', 'cj_2': False},
                        'n_str': 'nstr2', 'n_int': 20, 'n_bool': True
                    },
                    {
                        'c_index': 'i3', 'c_str': 'str1', 'c_str_no_len': 'nostr3', 'c_bool': True, 'c_int': 3,
                        'c_float': 0.3, 'c_json': {'cj_1': 'cj_str_3', 'cj_2': False},
                        'n_str': 'nstr3', 'n_int': 30, 'n_bool': True
                    },
                    {
                        'c_index': 'i4', 'c_str': 'str1', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 4,
                        'c_float': 0.4, 'c_json': {'cj_1': 'cj_str_4', 'cj_2': False},
                        'n_str': 'nstr4', 'n_int': 40, 'n_bool': True
                    },
                    {
                        'c_index': 'i5', 'c_str': 'str5', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 5,
                        'c_float': 0.5, 'c_json': {'cj_1': 'cj_str_5', 'cj_2': False},
                        'n_str': 'nstr5', 'n_int': 50, 'n_bool': True
                    },
                    {
                        'c_index': 'i6', 'c_str': 'str6', 'c_str_no_len': 'nostr6', 'c_bool': True, 'c_int': 6,
                        'c_float': 0.6, 'c_json': {'cj_1': 'cj_str_6', 'cj_2': False},
                        'n_str': 'nstr6', 'n_int': 60, 'n_bool': True
                    }
                ]
            )
        )
        if _ret != 6:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # count
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(_table_name)
        )
        if _ret != 6:
            return (False, _tips, 'count 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                _table_name, filter={
                    'n_int': {'$lte': 30}, '$or': [{'c_str_no_len': 'nostr2'}, {'c_str_no_len': 'nostr3'}]
                }
            )
        )
        if _ret != 2:
            return (False, _tips, 'count 2 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                _table_name, filter={'c_str_no_len': {"$regex": r"^((?!2$).)*$"}},
                skip=1
            )
        )
        if _ret != 3:
            return (False, _tips, 'count 2 error: %s' % str(_ret))

        # group by
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'},
                    'avg': {'$avg': '$n_int'}, 'min': {'$min': '$c_int'}, 'max': {'$max': '$c_int'}
                }
            )
        )  # 不报错即可

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'},
                    'avg': {'$avg': '$n_int'}, 'min': {'$min': '$c_int'}, 'max': {'$max': '$c_int'}
                }, sort=[('count', 1), ('c_str', -1)]
            )
        )

        _cmp_list = [
            {'count': 1, 'sum': 60, 'avg': 60.0, 'min': 6, 'max': 6, 'c_str': 'str6'},
            {'count': 1, 'sum': 50, 'avg': 50.0, 'min': 5, 'max': 5, 'c_str': 'str5'},
            {'count': 1, 'sum': 20, 'avg': 20.0, 'min': 2, 'max': 2, 'c_str': 'str2'},
            {'count': 3, 'sum': 80, 'avg': 26.666666666666668, 'min': 1, 'max': 4, 'c_str': 'str1'}
        ]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'group by 1 error: [%d]%s' % (_i, str(_ret[_i])))

        # 多个字段分组
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'c_bool': '$c_bool', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'}
                }, sort=[('count', 1), ('c_str', -1), ('c_bool', 1)]
            )
        )
        _cmp_list = [
            {'count': 1, 'sum': 60, 'c_str': 'str6', 'c_bool': True},
            {'count': 1, 'sum': 50, 'c_str': 'str5', 'c_bool': True},
            {'count': 1, 'sum': 20, 'c_str': 'str2', 'c_bool': True},
            {'count': 1, 'sum': 10, 'c_str': 'str1', 'c_bool': False},
            {'count': 2, 'sum': 70, 'c_str': 'str1', 'c_bool': True}
        ]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'group by 2 error: [%d]%s' % (_i, str(_ret[_i])))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'c_bool': '$c_bool', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'}
                }, projection=['c_str', 'count'],
                sort=[('count', 1), ('c_str', -1), ('c_bool', 1)]
            )
        )
        _cmp_list = [
            {'count': 1, 'c_str': 'str6'},
            {'count': 1, 'c_str': 'str5'},
            {'count': 1, 'c_str': 'str2'},
            {'count': 1, 'c_str': 'str1'},
            {'count': 2, 'c_str': 'str1'}
        ]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'group by 3 error: [%d]%s' % (_i, str(_ret[_i])))

        return (True, _tips, '')

    def test_query_aggregate_4(self):
        _tips = '集合数据查询3: 聚合查询(固定字段)'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_full_type'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 无固定字段表的查询处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1', 'c_str': 'str1', 'c_str_no_len': 'nostr1', 'c_bool': False, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True
                    },
                    {
                        'c_index': 'i2', 'c_str': 'str2', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 2,
                        'c_float': 0.2, 'c_json': {'cj_1': 'cj_str_2', 'cj_2': False},
                        'n_str': 'nstr2', 'n_int': 20, 'n_bool': True
                    },
                    {
                        'c_index': 'i3', 'c_str': 'str1', 'c_str_no_len': 'nostr3', 'c_bool': True, 'c_int': 3,
                        'c_float': 0.3, 'c_json': {'cj_1': 'cj_str_3', 'cj_2': False},
                        'n_str': 'nstr3', 'n_int': 30, 'n_bool': True
                    },
                    {
                        'c_index': 'i4', 'c_str': 'str1', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 4,
                        'c_float': 0.4, 'c_json': {'cj_1': 'cj_str_4', 'cj_2': False},
                        'n_str': 'nstr4', 'n_int': 40, 'n_bool': True
                    },
                    {
                        'c_index': 'i5', 'c_str': 'str5', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 5,
                        'c_float': 0.5, 'c_json': {'cj_1': 'cj_str_5', 'cj_2': False},
                        'n_str': 'nstr5', 'n_int': 50, 'n_bool': True
                    },
                    {
                        'c_index': 'i6', 'c_str': 'str6', 'c_str_no_len': 'nostr6', 'c_bool': True, 'c_int': 6,
                        'c_float': 0.6, 'c_json': {'cj_1': 'cj_str_6', 'cj_2': False},
                        'n_str': 'nstr6', 'n_int': 60, 'n_bool': True
                    }
                ]
            )
        )
        if _ret != 6:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # count
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(_table_name)
        )
        if _ret != 6:
            return (False, _tips, 'count 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                _table_name, filter={
                    'n_int': {'$lte': 30}, '$or': [{'c_str_no_len': 'nostr2'}, {'c_str_no_len': 'nostr3'}]
                }
            )
        )
        if _ret != 2:
            return (False, _tips, 'count 2 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                _table_name, filter={'c_str_no_len': {"$regex": r"^((?!2$).)*$"}},
                skip=1
            )
        )
        if _ret != 3:
            return (False, _tips, 'count 2 error: %s' % str(_ret))

        # group by
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'},
                    'avg': {'$avg': '$n_int'}, 'min': {'$min': '$c_int'}, 'max': {'$max': '$c_int'}
                }
            )
        )  # 不报错即可

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'},
                    'avg': {'$avg': '$n_int'}, 'min': {'$min': '$c_int'}, 'max': {'$max': '$c_int'}
                }, sort=[('count', 1), ('c_str', -1)]
            )
        )

        _cmp_list = [
            {'count': 1, 'sum': 60, 'avg': 60.0, 'min': 6, 'max': 6, 'c_str': 'str6'},
            {'count': 1, 'sum': 50, 'avg': 50.0, 'min': 5, 'max': 5, 'c_str': 'str5'},
            {'count': 1, 'sum': 20, 'avg': 20.0, 'min': 2, 'max': 2, 'c_str': 'str2'},
            {'count': 3, 'sum': 80, 'avg': 26.666666666666668, 'min': 1, 'max': 4, 'c_str': 'str1'}
        ]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'group by 1 error: [%d]%s' % (_i, str(_ret[_i])))

        # 多个字段分组
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'c_bool': '$c_bool', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'}
                }, sort=[('count', 1), ('c_str', -1), ('c_bool', 1)]
            )
        )
        _cmp_list = [
            {'count': 1, 'sum': 60, 'c_str': 'str6', 'c_bool': True},
            {'count': 1, 'sum': 50, 'c_str': 'str5', 'c_bool': True},
            {'count': 1, 'sum': 20, 'c_str': 'str2', 'c_bool': True},
            {'count': 1, 'sum': 10, 'c_str': 'str1', 'c_bool': False},
            {'count': 2, 'sum': 70, 'c_str': 'str1', 'c_bool': True}
        ]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'group by 2 error: [%d]%s' % (_i, str(_ret[_i])))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_group_by(
                _table_name, group={
                    'c_str': '$c_str', 'c_bool': '$c_bool', 'count': {'$sum': 1}, 'sum': {'$sum': '$n_int'}
                }, projection=['c_str', 'count'],
                sort=[('count', 1), ('c_str', -1), ('c_bool', 1)]
            )
        )
        _cmp_list = [
            {'count': 1, 'c_str': 'str6'},
            {'count': 1, 'c_str': 'str5'},
            {'count': 1, 'c_str': 'str2'},
            {'count': 1, 'c_str': 'str1'},
            {'count': 2, 'c_str': 'str1'}
        ]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'group by 3 error: [%d]%s' % (_i, str(_ret[_i])))

        return (True, _tips, '')

    #############################
    # 数据类型及特殊字符相关
    #############################
    def test_data_type_1(self):
        _tips = '数据类型1: 类型存入及获取'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_full_type'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 插入不同类型的信息
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1', 'c_str': 'str1', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True, 'n_float': 3.4,
                        'n_json': {'nj_col_1': 'nj_val_1', 'nj_col_2': 3}
                    },
                ]
            )
        )
        if _ret != 1:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # 检查插入的值和类型
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, projection=[
                    'c_str', 'c_bool', 'c_int', 'c_float', 'c_json',
                    'n_str', 'n_bool', 'n_int', 'n_float', 'n_json'
                ]
            )
        )
        # 固定字段的检查
        if not (type(_ret[0]['c_str']) == str and _ret[0]['c_str'] == 'str1'):
            return (False, _tips, 'check insert test data c_str error: %s' % str(_ret[0]['c_str']))
        if not _ret[0]['c_bool']:
            return (False, _tips, 'check insert test data c_bool error: %s' % str(_ret[0]['c_bool']))
        if not (type(_ret[0]['c_int']) == int and _ret[0]['c_int'] == 1):
            return (False, _tips, 'check insert test data c_int error: %s' % str(_ret[0]['c_int']))
        if not (type(_ret[0]['c_float']) == float and _ret[0]['c_float'] == 0.1):
            return (False, _tips, 'check insert test data c_float error: %s' % str(_ret[0]['c_float']))
        if not (type(_ret[0]['c_json']) == dict and TestTool.cmp_dict(_ret[0]['c_json'], {'cj_1': 'cj_str_1', 'cj_2': False})):
            return (False, _tips, 'check insert test data c_json error: %s' % str(_ret[0]['c_json']))

        # json字段的检查
        if not (type(_ret[0]['n_str']) == str and _ret[0]['n_str'] == 'nstr1'):
            return (False, _tips, 'check insert test data n_str error: %s' % str(_ret[0]['n_str']))
        if not _ret[0]['n_bool']:
            return (False, _tips, 'check insert test data n_bool error: %s' % str(_ret[0]['n_bool']))
        if not (type(_ret[0]['n_int']) == int and _ret[0]['n_int'] == 10):
            return (False, _tips, 'check insert test data n_int error: %s' % str(_ret[0]['n_int']))
        if not (type(_ret[0]['n_float']) == float and _ret[0]['n_float'] == 3.4):
            return (False, _tips, 'check insert test data n_float error: %s' % str(_ret[0]['n_float']))
        if not (type(_ret[0]['n_json']) == dict and TestTool.cmp_dict(_ret[0]['n_json'], {'nj_col_1': 'nj_val_1', 'nj_col_2': 3})):
            return (False, _tips, 'check insert test data n_json error: %s' % str(_ret[0]['n_json']))

        # 更新不同类型的值
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            _table_name, filter=None, update={
                '$set': {
                    'c_str': 'str1_upd', 'c_bool': False, 'c_int': 2, 'c_float': 0.2,
                    'c_json': {'cj_1_u': 'cj_str_1', 'cj_2_u': False},
                    'n_str': 'nstr1_upd', 'n_bool': False, 'n_int': 11, 'n_float': 3.5,
                    'n_json': {'nj_col_1_u': 'nj_val_1', 'nj_col_2_u': 3}
                }
            }
        ))
        if _ret != 1:
            return (False, _tips, 'update 1 error: %s' % str(_ret))

        # 检查插入的值和类型
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, projection=[
                    'c_str', 'c_bool', 'c_int', 'c_float', 'c_json',
                    'n_str', 'n_bool', 'n_int', 'n_float', 'n_json'
                ]
            )
        )
        # 固定字段的检查
        if not (type(_ret[0]['c_str']) == str and _ret[0]['c_str'] == 'str1_upd'):
            return (False, _tips, 'check update test data c_str error: %s' % str(_ret[0]['c_str']))
        if _ret[0]['c_bool']:
            return (False, _tips, 'check update test data c_bool error: %s' % str(_ret[0]['c_bool']))
        if not (type(_ret[0]['c_int']) == int and _ret[0]['c_int'] == 2):
            return (False, _tips, 'check update test data c_int error: %s' % str(_ret[0]['c_int']))
        if not (type(_ret[0]['c_float']) == float and _ret[0]['c_float'] == 0.2):
            return (False, _tips, 'check update test data c_float error: %s' % str(_ret[0]['c_float']))
        if not (type(_ret[0]['c_json']) == dict and TestTool.cmp_dict(_ret[0]['c_json'], {'cj_1_u': 'cj_str_1', 'cj_2_u': False})):
            return (False, _tips, 'check update test data c_json error: %s' % str(_ret[0]['c_json']))

        # json字段的检查
        if not (type(_ret[0]['n_str']) == str and _ret[0]['n_str'] == 'nstr1_upd'):
            return (False, _tips, 'check update test data n_str error: %s' % str(_ret[0]['n_str']))
        if _ret[0]['n_bool']:
            return (False, _tips, 'check update test data n_bool error: %s' % str(_ret[0]['n_bool']))
        if not (type(_ret[0]['n_int']) == int and _ret[0]['n_int'] == 11):
            return (False, _tips, 'check update test data n_int error: %s' % str(_ret[0]['n_int']))
        if not (type(_ret[0]['n_float']) == float and _ret[0]['n_float'] == 3.5):
            return (False, _tips, 'check update test data n_float error: %s' % str(_ret[0]['n_float']))
        if not (type(_ret[0]['n_json']) == dict and TestTool.cmp_dict(_ret[0]['n_json'], {'nj_col_1_u': 'nj_val_1', 'nj_col_2_u': 3})):
            return (False, _tips, 'check update test data n_json error: %s' % str(_ret[0]['n_json']))

        return (True, _tips, '')

    def test_special_char2(self):
        _tips = '特殊字符: 转义相关字符'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_full_type'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 单双引号, 反斜杠, 回车换行, 制表符, 中文
        _str = 'test \'单引号\' "双引号", 反斜杠\\, 回车:\r, 换行:\n, tab:\t'
        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_one(
            _table_name, {
                'c_str': _str, 'c_json': {'j_val': _str},
                'n_str': _str, 'n_json': {'j_val': _str}
            }
        ))

        # 检查插入的值
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, projection=[
                    'c_str', 'c_json', 'n_str', 'n_json'
                ]
            )
        )
        # 固定字段的检查
        if not (type(_ret[0]['c_str']) == str and _ret[0]['c_str'] == _str):
            return (False, _tips, 'check insert test data c_str error: %s' % str(_ret[0]['c_str']))
        if not (type(_ret[0]['c_json']) == dict and TestTool.cmp_dict(_ret[0]['c_json'], {'j_val': _str})):
            return (False, _tips, 'check insert test data c_json error: %s' % str(_ret[0]['c_json']))

        # json字段的检查
        if not (type(_ret[0]['n_str']) == str and _ret[0]['n_str'] == _str):
            return (False, _tips, 'check insert test data n_str error: %s' % str(_ret[0]['n_str']))
        if not (type(_ret[0]['n_json']) == dict and TestTool.cmp_dict(_ret[0]['n_json'], {'j_val': _str})):
            return (False, _tips, 'check insert test data n_json error: %s' % str(_ret[0]['n_json']))

        # 更新值
        _str = '%s new' % _str
        _ret = AsyncTools.sync_run_coroutine(self.driver.update(
            _table_name, filter=None, update={
                '$set': {
                    'c_str': _str, 'c_json': {'j_val': _str},
                    'n_str': _str, 'n_json': {'j_val': _str}
                }
            }
        ))
        if _ret != 1:
            return (False, _tips, 'update 1 error: %s' % str(_ret))

        # 检查更新的值
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, projection=[
                    'c_str', 'c_json', 'n_str', 'n_json'
                ]
            )
        )
        # 固定字段的检查
        if not (type(_ret[0]['c_str']) == str and _ret[0]['c_str'] == _str):
            return (False, _tips, 'check update test data c_str error: %s' % str(_ret[0]['c_str']))
        if not (type(_ret[0]['c_json']) == dict and TestTool.cmp_dict(_ret[0]['c_json'], {'j_val': _str})):
            return (False, _tips, 'check update test data c_json error: %s' % str(_ret[0]['c_json']))

        # json字段的检查
        if not (type(_ret[0]['n_str']) == str and _ret[0]['n_str'] == _str):
            return (False, _tips, 'check update test data n_str error: %s' % str(_ret[0]['n_str']))
        if not (type(_ret[0]['n_json']) == dict and TestTool.cmp_dict(_ret[0]['n_json'], {'j_val': _str})):
            return (False, _tips, 'check update test data n_json error: %s' % str(_ret[0]['n_json']))

        return (True, _tips, '')

    def test_null_data_3(self):
        _tips = '数据类型3: 空值存入和比较'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_full_type'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 插入不同类型的信息
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1',
                        'c_str': None,
                        # 'c_str_no_len': 'nostr1',
                        'c_bool': True, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True, 'n_float': 3.4,
                        'n_json': {'nj_col_1': 'nj_val_1', 'nj_col_2': 3}
                    },
                ]
            )
        )
        if _ret != 1:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # 通过空值查询数据
        # TODO({lhj}): 如果返回结果带上n_json字段, sqlite将会把一个结果变成3个结果返回, 暂时无解决方案
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_index': 'i1', 'c_str': None, 'c_str_no_len': None},
                projection=[
                    'c_str', 'c_bool', 'c_int', 'c_float', 'c_json',
                    'n_str', 'n_bool', 'n_int', 'n_float', # 'n_json'
                ]
            )
        )

        if len(_ret) != 1:
            return (False, _tips, 'query test data 1 error: %s' % str(_ret))

        return (True, _tips, '')

    #############################
    # 分页
    #############################

    def test_page_1(self):
        _tips = '集合数据分页查询1: 分页'
        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_null'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 无固定字段表的查询处理
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1', 'c_str': 'str1', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 1,
                        'c_float': 0.1, 'c_json': {'cj_1': 'cj_str_1', 'cj_2': False},
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True
                    },
                    {
                        'c_index': 'i2', 'c_str': 'str2', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 2,
                        'c_float': 0.2, 'c_json': {'cj_1': 'cj_str_2', 'cj_2': False},
                        'n_str': 'nstr2', 'n_int': 20, 'n_bool': True
                    },
                    {
                        'c_index': 'i3', 'c_str': 'str1', 'c_str_no_len': 'nostr3', 'c_bool': True, 'c_int': 3,
                        'c_float': 0.3, 'c_json': {'cj_1': 'cj_str_3', 'cj_2': False},
                        'n_str': 'nstr3', 'n_int': 30, 'n_bool': True
                    },
                    {
                        'c_index': 'i4', 'c_str': 'str1', 'c_str_no_len': 'nostr2', 'c_bool': True, 'c_int': 4,
                        'c_float': 0.4, 'c_json': {'cj_1': 'cj_str_4', 'cj_2': False},
                        'n_str': 'nstr4', 'n_int': 40, 'n_bool': True
                    },
                    {
                        'c_index': 'i5', 'c_str': 'str5', 'c_str_no_len': 'nostr1', 'c_bool': True, 'c_int': 5,
                        'c_float': 0.5, 'c_json': {'cj_1': 'cj_str_5', 'cj_2': False},
                        'n_str': 'nstr5', 'n_int': 50, 'n_bool': True
                    },
                    {
                        'c_index': 'i6', 'c_str': 'str6', 'c_str_no_len': 'nostr6', 'c_bool': True, 'c_int': 6,
                        'c_float': 0.6, 'c_json': {'cj_1': 'cj_str_6', 'cj_2': False},
                        'n_str': 'nstr6', 'n_int': 60, 'n_bool': True
                    }
                ]
            )
        )
        if _ret != 6:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page_info(_table_name, page_size=2)
        )
        if not TestTool.cmp_dict(_ret, {'total': 6, 'total_pages': 3, 'page_size': 2}):
            return (False, _tips, 'query page info 1 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page_info(_table_name, page_size=5)
        )
        if not TestTool.cmp_dict(_ret, {'total': 6, 'total_pages': 2, 'page_size': 5}):
            return (False, _tips, 'query page info 2 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page_info(_table_name, page_size=6)
        )
        if not TestTool.cmp_dict(_ret, {'total': 6, 'total_pages': 1, 'page_size': 6}):
            return (False, _tips, 'query page info 3 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page_info(_table_name, filter={'a_no_exist': 0}, page_size=6)
        )
        if not TestTool.cmp_dict(_ret, {'total': 0, 'total_pages': 0, 'page_size': 6}):
            return (False, _tips, 'query page info 4 error: %s' % str(_ret))

        # 排序后返回
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page(
                _table_name, page_size=2, projection={'_id': False, 'c_index': True},
                sort=[('n_int', -1)]
            )
        )
        _cmp_list = [{'c_index': 'i6'}, {'c_index': 'i5'}]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'query page 1 error: [%d]%s' % (_i, str(_ret[_i])))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page(
                _table_name, page_index=3, page_size=2, projection={'_id': False, 'c_index': True},
                sort=[('n_int', -1)]
            )
        )
        _cmp_list = [{'c_index': 'i2'}, {'c_index': 'i1'}]
        for _i in range(len(_cmp_list)):
            if not TestTool.cmp_dict(_cmp_list[_i], _ret[_i]):
                return (False, _tips, 'query page 2 error: [%d]%s' % (_i, str(_ret[_i])))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_page(
                _table_name, page_index=4, page_size=2, projection={'_id': False, 'c_index': True},
                sort=[('n_int', -1)]
            )
        )
        if len(_ret) > 0:
            return (False, _tips, 'query page 3 error: [%d]%s' % (_i, str(_ret[_i])))

        return (True, _tips, '')

    #############################
    # 多级json路径操作
    #############################
    def test_json_path_1(self):
        _tips = '多级json路径操作1: 多级路径'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        _table_name = 'tb_full_type'
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection(_table_name))

        # 插入不同类型的信息
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many(
                _table_name, [
                    {
                        'c_index': 'i1',
                        'c_str': None,
                        'c_str_no_len': 'nostr1',
                        'c_bool': True, 'c_int': 1,
                        'c_float': 0.1,
                        'c_json': {
                            'cj_1': 'cj_str_1', 'cj_2': False,
                            'cj_3': ['a1', 'b1', {'c1': {'name': 'cj_val1'}}],
                            'cj_4': ['e1', 'f1', {'j1': 'cj_val_j1'}]
                        },
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True, 'n_float': 3.4,
                        'n_json': {
                            'nj_col_1': 'nj_val_1', 'nj_col_2': 3,
                            'nj_col_3': ['1', '2', {'3': {'name': 'nj_val1'}}],
                            'nj_col_4': ['4', '5', {'6': 'nj_val_61'}]
                        }
                    },
                    {
                        'c_index': 'i2',
                        'c_str': None,
                        'c_str_no_len': 'nostr2',
                        'c_bool': True, 'c_int': 2,
                        'c_float': 0.2,
                        'c_json': {
                            'cj_1': 'cj_str_2', 'cj_2': False,
                            'cj_3': ['a2', 'b2', {'c2': {'name': 'cj_val2'}}],
                            'cj_4': ['e2', 'f2', {'j2': 'cj_val_j2'}]
                        },
                        'n_str': 'nstr1', 'n_int': 10, 'n_bool': True, 'n_float': 3.4,
                        'n_json': {
                            'nj_col_1': 'nj_val_2', 'nj_col_2': 3,
                            'nj_col_3': ['1', '2', {'3': {'name': 'nj_val2'}}],
                            'nj_col_4': ['4', '5', {'6': 'nj_val_62'}]
                        }
                    }
                ]
            )
        )
        if _ret != 2:
            return (False, _tips, 'insert test data 1 error: %s' % str(_ret))

        # 更新固定字段json的内部栏位
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.update(
                _table_name, filter={'c_json.cj_3.1': 'b1'}, update={
                    '$set': {'c_json.cj_3.2.c1.name': 'cj_val2_upd'}
                }
            )
        )
        if _ret != 1:
            return (False, _tips, 'update c_json 1 error: [%s]' % (str(_ret)))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                _table_name, filter={'c_json.cj_3.0': 'a1'},
                projection={'_id': False, 'as_name': '$c_json.cj_3', 'n_str': True}
            )
        )
        if _ret[0]['as_name'][2]['c1']['name'] != 'cj_val2_upd':
            return (False, _tips, 'update c_json 1 query error: [%s]' % (str(_ret)))

        return (True, _tips, '')

    #############################
    # 表关联
    #############################
    def test_left_join_1(self):
        _tips = '测试表关联1'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 先删除表
        _tab_list = ['tb_left_join_main', 'tb_left_join_sub1', 'tb_left_join_sub2']
        for _tab in _tab_list:
            try:
                AsyncTools.sync_run_coroutine(self.driver.drop_collection(_tab))
            except:
                pass

        # 创建测试表
        AsyncTools.sync_run_coroutine(
            self.driver.create_collection(
                'tb_left_join_main', indexs=None,
                fixed_col_define={
                    'm_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
                    'm_join_col_11': {'type': 'str', 'len': 50, 'comment': '关联字段11'},
                    'm_join_col_12': {'type': 'str', 'len': 50, 'comment': '关联字段12'},
                    'm_join_col_21': {'type': 'str', 'len': 50, 'comment': '关联字段21'},
                    'm_join_col_22': {'type': 'str', 'len': 50, 'comment': '关联字段22'},
                    'm_info': {'type': 'str', 'comment': '辅助信息字段'},
                    'm_filter': {'type': 'int', 'comment': '过滤条件'}
                },
                comment='表关联主表'
            )
        )

        AsyncTools.sync_run_coroutine(
            self.driver.create_collection(
                'tb_left_join_sub1', indexs=None,
                fixed_col_define={
                    's1_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
                    's1_join_col_11': {'type': 'str', 'len': 50, 'comment': '关联字段11'},
                    's1_join_col_12': {'type': 'str', 'len': 50, 'comment': '关联字段12'},
                    's1_info': {'type': 'str', 'comment': '辅助信息字段'},
                    's1_filter': {'type': 'int', 'comment': '过滤条件'}
                },
                comment='表关联子表1'
            )
        )

        AsyncTools.sync_run_coroutine(
            self.driver.create_collection(
                'tb_left_join_sub2', indexs=None,
                fixed_col_define={
                    's2_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
                    's2_join_col_21': {'type': 'str', 'len': 50, 'comment': '关联字段11'},
                    's2_join_col_22': {'type': 'str', 'len': 50, 'comment': '关联字段12'},
                    's2_info': {'type': 'str', 'comment': '辅助信息字段'},
                    's2_filter': {'type': 'int', 'comment': '过滤条件'}
                },
                comment='表关联子表2'
            )
        )

        # 插入测试数据
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many('tb_left_join_main', [
                {
                    'm_index': 'm1',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'yuwen', 'm_join_col_13': 'man', 'm_join_col_14': 'old',
                    'm_join_col_21': 'car', 'm_join_col_22': 'A1', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1,子表2均有数据', 'm_filter': 1, 'json_str': 'm1_json'
                },
                {
                    'm_index': 'm2',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'english', 'm_join_col_13': 'man', 'm_join_col_14': 'old',
                    'm_join_col_21': 'car', 'm_join_col_22': 'A2', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1,子表2均有数据', 'm_filter': 1, 'json_str': 'm2_json'
                },
                {
                    'm_index': 'm3',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'yuwen', 'm_join_col_13': 'man', 'm_join_col_14': 'young',
                    'm_join_col_21': 'no', 'm_join_col_22': 'A1', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1有数据,子表2无数据', 'm_filter': 1, 'json_str': 'm3_json'
                },
                {
                    'm_index': 'm4',
                    'm_join_col_11': 'no', 'm_join_col_12': 'yuwen', 'm_join_col_13': 'man', 'm_join_col_14': 'young',
                    'm_join_col_21': 'car', 'm_join_col_22': 'A1', 'm_join_col_23': 'year', 'm_join_col_24': '2022',
                    'm_info': '子表1无数据,子表2有数据', 'm_filter': 1, 'json_str': 'm4_json'
                },
                {
                    'm_index': 'm5',
                    'm_join_col_11': 'no', 'm_join_col_12': 'yuwen', 'm_join_col_13': 'man', 'm_join_col_14': 'young',
                    'm_join_col_21': 'no', 'm_join_col_22': 'A1', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1,子表2均无数据', 'm_filter': 1, 'json_str': 'm5_json'
                },
                {
                    'm_index': 'm6',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'yuwen', 'm_join_col_13': 'man', 'm_join_col_14': 'old',
                    'm_join_col_21': 'car', 'm_join_col_22': 'A1', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1,子表2均有数据, 被过滤', 'm_filter': 0, 'json_str': 'm6_json'
                },
                {
                    'm_index': 'm7',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'english', 'm_join_col_13': 'man', 'm_join_col_14': 'old',
                    'm_join_col_21': 'car', 'm_join_col_22': 'A2', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1,子表2均有数据, 被过滤', 'm_filter': 0, 'json_str': 'm7_json'
                },
                {
                    'm_index': 'm8',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'yuwen', 'm_join_col_13': 'man', 'm_join_col_14': 'young',
                    'm_join_col_21': 'no', 'm_join_col_22': 'A1', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1有数据,子表2无数据, 被过滤', 'm_filter': 0, 'json_str': 'm8_json'
                },
                {
                    'm_index': 'm9',
                    'm_join_col_11': 'teacher', 'm_join_col_12': 'wuli', 'm_join_col_13': 'man', 'm_join_col_14': 'old',
                    'm_join_col_21': 'car', 'm_join_col_22': 'A3', 'm_join_col_23': 'year', 'm_join_col_24': '2021',
                    'm_info': '子表1,子表2均有数据, 子表1被过滤', 'm_filter': 1, 'json_str': 'm9_json'
                },
            ])
        )

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many('tb_left_join_sub1', [
                {
                    's1_index': 's11',
                    's1_join_col_11': 'teacher', 's1_join_col_12': 'yuwen', 's1_join_col_13': 'man', 's1_join_col_14': 'old',
                    's1_info': '匹配上数据', 's1_filter': 1, 'json_str': 's11_json'
                },
                {
                    's1_index': 's12',
                    's1_join_col_11': 'teacher', 's1_join_col_12': 'english', 's1_join_col_13': 'man', 's1_join_col_14': 'old',
                    's1_info': '匹配上数据', 's1_filter': 1, 'json_str': 's12_json'
                },
                {
                    's1_index': 's13',
                    's1_join_col_11': 'teacher', 's1_join_col_12': 'yuwen', 's1_join_col_13': 'man', 's1_join_col_14': 'young',
                    's1_info': '匹配上数据', 's1_filter': 1, 'json_str': 's13_json'
                },
                {
                    's1_index': 's14',
                    's1_join_col_11': 'teacher', 's1_join_col_12': 'wuli', 's1_join_col_13': 'man', 's1_join_col_14': 'old',
                    's1_info': '匹配上数据, 过滤', 's1_filter': 0, 'json_str': 's14_json'
                },
                {
                    's1_index': 's15',
                    's1_join_col_11': 'teacher', 's1_join_col_12': 'nomatch', 's1_join_col_13': 'man', 's1_join_col_14': 'young',
                    's1_info': '匹配不上数据', 's1_filter': 1, 'json_str': 's15_json'
                },
                {
                    's1_index': 's16',
                    's1_join_col_11': 'teacher1', 's1_join_col_12': 'nomatch', 's1_join_col_13': 'man', 's1_join_col_14': 'young',
                    's1_info': '匹配不上数据, 过滤', 's1_filter': 0, 'json_str': 's16_json'
                },
            ])
        )

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many('tb_left_join_sub2', [
                {
                    's2_index': 's21',
                    's2_join_col_21': 'car', 's2_join_col_22': 'A1', 's2_join_col_23': 'year', 's2_join_col_24': '2021',
                    's2_info': '匹配上数据', 's2_filter': 1, 'json_str': 's21_json'
                },
                {
                    's2_index': 's22',
                    's2_join_col_21': 'car', 's2_join_col_22': 'A2', 's2_join_col_23': 'year', 's2_join_col_24': '2021',
                    's2_info': '匹配上数据', 's2_filter': 1, 'json_str': 's22_json'
                },
                {
                    's2_index': 's23',
                    's2_join_col_21': 'car', 's2_join_col_22': 'A1', 's2_join_col_23': 'year', 's2_join_col_24': '2022',
                    's2_info': '匹配上数据', 's2_filter': 1, 'json_str': 's23_json'
                },
                {
                    's2_index': 's24',
                    's2_join_col_21': 'car', 's2_join_col_22': 'A3', 's2_join_col_23': 'year', 's2_join_col_24': '2021',
                    's2_info': '匹配上数据, 过滤', 's2_filter': 0, 'json_str': 's24_json'
                },
                {
                    's2_index': 's25',
                    's2_join_col_21': 'car', 's2_join_col_22': 'nomatch', 's2_join_col_23': 'year', 's2_join_col_24': '2021',
                    's2_info': '匹配不上数据', 's2_filter': 1, 'json_str': 's25_json'
                },
                {
                    's2_index': 's26',
                    's2_join_col_21': 'car1', 's2_join_col_22': 'nomatch', 's2_join_col_23': 'year', 's2_join_col_24': '2021',
                    's2_info': '匹配不上数据, 过滤', 's2_filter': 0, 'json_str': 's26_json'
                },
                {
                    's2_index': 's27',
                    's2_join_col_21': 'car', 's2_join_col_22': 'A3', 's2_join_col_23': 'year', 's2_join_col_24': '2021',
                    's2_info': '匹配上数据', 's2_filter': 1, 'json_str': 's27_json'
                }
            ])
        )

        # 输出所有表字段
        _left_join = [
            {
                'collection': 'tb_left_join_sub1',
                'join_fields': [('m_join_col_11', 's1_join_col_11'), ('m_join_col_12', 's1_join_col_12'), ('m_join_col_13', 's1_join_col_13'), ('m_join_col_14', 's1_join_col_14')]
            },
            {
                'collection': 'tb_left_join_sub2',
                'join_fields': [('m_join_col_21', 's2_join_col_21'), ('m_join_col_22', 's2_join_col_22'), ('m_join_col_23', 's2_join_col_23'), ('m_join_col_24', 's2_join_col_24')]
            }
        ]
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_left_join_main', filter={'m_filter': 1},
                left_join=_left_join
            )
        )
        _index_list = [_row['m_index'] for _row in _ret]
        _row_keys = list(_ret[0].keys())
        if not (
            TestTool.cmp_list(
                _index_list, ['m1', 'm2', 'm3', 'm4', 'm5', 'm9', 'm9'], sorted=True
            ) and len(_row_keys) == 31
        ):
            return (False, _tips, '输出所有表字段 1 error: [%s]' % (str(_ret)))

        # 输出主表和子表指定字段
        _left_join = [
            {
                'collection': 'tb_left_join_sub1',
                'join_fields': [('m_join_col_11', 's1_join_col_11'), ('m_join_col_12', 's1_join_col_12'), ('m_join_col_13', 's1_join_col_13'), ('m_join_col_14', 's1_join_col_14')],
                'filter': {'s1_filter': 1}
            },
            {
                'collection': 'tb_left_join_sub2',
                'join_fields': [('m_join_col_21', 's2_join_col_21'), ('m_join_col_22', 's2_join_col_22'), ('m_join_col_23', 's2_join_col_23'), ('m_join_col_24', 's2_join_col_24')],
                'filter': {'s2_filter': 1}
            }
        ]

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_left_join_main', filter={'m_filter': 1}, projection=[
                    'm_index', 'm_info', 'json_str',
                    '#0._id', '#0.s1_index', '#0.s1_info', '#0.s1_join_col_11', '#0.json_str',
                    '#1.s2_index', '#1.s2_info', '#1.s2_join_col_21', '#1.json_str'
                ],
                sort=[('m_index', 1)],
                left_join=_left_join
            )
        )

        if len(_ret) != 6 or len(list(_ret[0].keys())) != 13:
            return (False, _tips, '输出主表和子表指定字段 3 error: [%s]' % (str(_ret)))

        # 检查关联匹配结果
        if len(_ret) != 6:
            return (False, _tips, '检查关联匹配结果 4 - 记录数 error: [%s]' % (str(_ret)))

        if not (_ret[0]['m_index'] == 'm1' and _ret[0]['s1_index'] == 's11' and _ret[0]['s2_index'] == 's21'):
            return (False, _tips, '检查关联匹配结果 4 - 0 error: [%s]' % (str(_ret[0])))

        if not (_ret[1]['m_index'] == 'm2' and _ret[1]['s1_index'] == 's12' and _ret[1]['s2_index'] == 's22'):
            return (False, _tips, '检查关联匹配结果 4 - 1 error: [%s]' % (str(_ret[1])))

        if not (_ret[2]['m_index'] == 'm3' and _ret[2]['s1_index'] == 's13' and 's2_index' not in _ret[2].keys()):
            return (False, _tips, '检查关联匹配结果 4 - 2 error: [%s]' % (str(_ret[2])))

        if not (_ret[3]['m_index'] == 'm4' and 's1_index' not in _ret[3].keys() and _ret[3]['s2_index'] == 's23'):
            return (False, _tips, '检查关联匹配结果 4 - 3 error: [%s]' % (str(_ret[3])))

        if not (_ret[4]['m_index'] == 'm5' and 's1_index' not in _ret[4].keys() and 's2_index' not in _ret[4].keys()):
            return (False, _tips, '检查关联匹配结果 4 - 4 error: [%s]' % (str(_ret[4])))

        if not (_ret[5]['m_index'] == 'm9' and 's1_index' not in _ret[5].keys() and _ret[5]['s2_index'] == 's27'):
            return (False, _tips, '检查关联匹配结果 4 - 5 error: [%s]' % (str(_ret[5])))

        # 关联表字段排序
        _left_join = [
            {
                'collection': 'tb_left_join_sub1',
                'join_fields': [('m_join_col_11', 's1_join_col_11'), ('m_join_col_12', 's1_join_col_12'), ('m_join_col_13', 's1_join_col_13'), ('m_join_col_14', 's1_join_col_14')],
                'filter': {'s1_filter': 1}
            },
            {
                'collection': 'tb_left_join_sub2',
                'join_fields': [('m_join_col_21', 's2_join_col_21'), ('m_join_col_22', 's2_join_col_22'), ('m_join_col_23', 's2_join_col_23'), ('m_join_col_24', 's2_join_col_24')],
                'filter': {'s2_filter': 1}
            }
        ]

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_left_join_main', filter={'m_filter': 1},
                projection={
                    '_id': True, 'm_index': True, 'm_info': True, 'json_str': True,
                    '#0._id': True, '#0.s1_index': True, '#0.s1_info': True, '#0.s1_join_col_11': True, '#0.json_str': True,
                    '#1._id': False, 's2_index_as_name': '$#1.s2_index', 's2_info': '$#1.s2_info', '#1.s2_join_col_21': True, '#1.json_str': True
                },
                sort=[('#0.s1_index', -1), ('m_index', 1)],
                left_join=_left_join
            )
        )

        if not (_ret[2]['m_index'] == 'm1' and _ret[1]['m_index'] == 'm2' and _ret[0]['m_index'] == 'm3'):
            return (False, _tips, '关联表字段排序 5 error: [%s]' % (str(_ret)))

        # 关联表字段筛选
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_list(
                'tb_left_join_main', filter={'m_filter': 1, '#0.s1_index': 's11'},
                projection=['m_index', 'm_info', 'json_str', '#0.s1_index'],
                sort=[('#0.s1_index', -1), ('m_index', 1)],
                left_join=_left_join
            )
        )

        if len(_ret) != 1 or _ret[0]['s1_index'] != 's11':
            return (False, _tips, '关联表字段筛选 6 error: [%s]' % (str(_ret)))

        # 迭代方式获取数据
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_iter(
                'tb_left_join_main', filter={'m_filter': 1},
                projection=['m_index', 'm_info', 'json_str'],
                sort=[('#0.s1_index', -1), ('m_index', 1)],
                left_join=_left_join
            )
        )

        _query_list = []
        for _rows in AsyncTools.sync_for_async_iter(_ret):
            _query_list.extend(_rows)

        if not (_query_list[2]['m_index'] == 'm1' and _query_list[1]['m_index'] == 'm2' and _query_list[0]['m_index'] == 'm3'):
            return (False, _tips, '迭代方式获取数据 7 error: [%s]' % (str(_query_list)))

        # 查询记录数
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count(
                'tb_left_join_main', filter={'m_filter': 1, '#0.s1_index': 's11'},
                left_join=_left_join
            )
        )

        if _ret != 1:
            return (False, _tips, '查询记录数 8 error: [%s]' % (str(_ret)))

        # 测试结束删除表
        for _tab in _tab_list:
            try:
                AsyncTools.sync_run_coroutine(self.driver.drop_collection(_tab))
            except:
                pass

        return (True, _tips, '')

    #############################
    # 事务处理
    #############################
    def test_transaction_1(self):
        _tips = '测试事务处理1'

        # 获取测试库清单
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_test_dbs[0]))

        # 清空测试表
        AsyncTools.sync_run_coroutine(self.driver.turncate_collection('tb_full_type'))

        # 插入全类型表
        _rows = [
            {'c_index': 'i1', 'c_str': 'remain', 'n_str': 'nstr1'},
            {'c_index': 'i2', 'c_str': 'remain', 'n_str': 'nstr2'},
            {'c_index': 'i3', 'c_str': 'update', 'n_str': 'nstr3'},
            {'c_index': 'i4', 'c_str': 'update', 'n_str': 'nstr4'},
            {'c_index': 'i5', 'c_str': 'del', 'n_str': 'nstr5'},
            {'c_index': 'i6', 'c_str': 'del', 'n_str': 'nstr6'}
        ]

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many('tb_full_type', _rows)
        )

        if _ret != 6:
            return (False, _tips, 'insert many 1 error: %s' % str(_ret))

        # 测试事务回滚
        _session = AsyncTools.sync_run_coroutine(
            self.driver.start_transaction()
        )

        # 插入数据
        _insert_rows = [
            {'c_index': 'i7', 'c_str': 'insert_rollback', 'n_str': 'nstr7'},
            {'c_index': 'i8', 'c_str': 'insert_rollback', 'n_str': 'nstr8'}
        ]
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many('tb_full_type', _insert_rows, session=_session)
        )

        if _ret != 2:
            return (False, _tips, 'insert rollback 2 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', session=_session)
        )

        if _ret != 8:
            return (False, _tips, 'count insert before rollback 3 error: %s' % str(_ret))

        # 更新数据
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.update('tb_full_type', {'c_str': 'update'}, {'$set': {'c_str': 'update1'}}, session=_session)
        )
        if _ret != 2:
            return (False, _tips, 'update rollback 4 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', filter={'c_str': 'update1'}, session=_session)
        )
        if _ret != 2:
            return (False, _tips, 'count update before rollback 5 error: %s' % str(_ret))

        # 删除数据
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.delete('tb_full_type', {'c_str': 'del'}, session=_session)
        )
        if _ret != 2:
            return (False, _tips, 'delete rollback 6 error: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', filter={'c_str': 'del'}, session=_session)
        )
        if _ret != 0:
            return (False, _tips, 'count delete before rollback 7 error: %s' % str(_ret))

        # 回滚
        AsyncTools.sync_run_coroutine(
            self.driver.abort_transaction(_session)
        )

        # 回滚后检查
        _all_count = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type')
        )
        _update_count = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', filter={'c_str': 'update1'})
        )
        _delete_count = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', filter={'c_str': 'del'})
        )
        if not (_all_count == 6 and _update_count == 0 and _delete_count == 2):
            return (False, _tips, 'count after rollback 8 error: %s' % str((_all_count, _update_count, _delete_count)))

        # 测试事务正常提交
        _session = AsyncTools.sync_run_coroutine(
            self.driver.start_transaction()
        )
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.insert_many('tb_full_type', _insert_rows, session=_session)
        )
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.update('tb_full_type', {'c_str': 'update'}, {'$set': {'c_str': 'update1'}}, session=_session)
        )
        _ret = AsyncTools.sync_run_coroutine(
            self.driver.delete('tb_full_type', {'c_str': 'del'}, session=_session)
        )

        # 提交事务
        AsyncTools.sync_run_coroutine(
            self.driver.commit_transaction(_session)
        )

        # 提交后检查
        _all_count = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type')
        )
        _update_count = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', filter={'c_str': 'update1'})
        )
        _delete_count = AsyncTools.sync_run_coroutine(
            self.driver.query_count('tb_full_type', filter={'c_str': 'del'})
        )
        if not (_all_count == 6 and _update_count == 2 and _delete_count == 0):
            return (False, _tips, 'count after rollback 9 error: %s' % str((_all_count, _update_count, _delete_count)))

        return (True, _tips, '')


class SQLiteDriverTestCase(DriverTestCaseFW):
    """
    通用的驱动测试方法类
    """
    #############################
    # 不同驱动自有的测试方法
    #############################

    def __init__(self) -> None:
        """
        构造函数
        """
        # 清空数据
        _path = os.path.join(os.path.dirname(__file__), os.path.pardir, 'test_data/temp')
        self._path = _path
        try:
            FileTool.remove_dir(_path)
        except:
            pass
        os.makedirs(_path, exist_ok=True)

        self.driver_id = 'SQLite'

        # 创建驱动
        self.driver = SQLiteNosqlDriver(
            connect_config={
                'host': os.path.join(_path, 'sqlite_test.db'),
                'check_same_thread': False
            },
            driver_config={
                'debug': True,
                'close_action': 'commit',
                'init_db': self.init_db,
                'init_collections': self.init_collections
            }
        )

    @property
    def self_test_order(self) -> list:
        """
        当前驱动自有的测试清单
        """
        return ['self_test_attach_dbs_1']

    #############################
    # 可能有个性的测试数据
    #############################
    @property
    def init_db(self) -> dict:
        """
        启动时创建数据库的参数
        """
        return {
            'memory': {
                'index_only': False,
                'args': [':memory:']
            },
            'db_init_test': {
                'index_only': False,
                'args': [os.path.join(self._path, 'sqlite_db_init_test.db')]
            }
        }

    @property
    def test_db_info(self) -> list:
        """
        测试数据库信息
        返回[(数据库名, 固定创建参数, kv创建参数), ...]
        """
        return [
            ('db_test1', [os.path.join(self._path, 'sqlite_db_test1.db')], {}),
            ('db_test2', [os.path.join(self._path, 'sqlite_db_test2.db')], {})
        ]

    @property
    def delete_db_info(self):
        """
        删除数据库信息
        返回[(数据库名, 固定创建参数, kv创建参数), ...]
        """
        return [
            ('db_del_test1', [os.path.join(self._path, 'sqlite_db_del_test1.db')], {}),
            ('db_del_test2', [os.path.join(self._path, 'sqlite_db_del_test2.db')], {})
        ]

    #############################
    # 自有的测试函数
    #############################
    def self_test_attach_dbs_1(self) -> tuple:
        _tips = '测试启动创建数据库1'
        _dbs = AsyncTools.sync_run_coroutine(self.driver.list_dbs())
        return (
            TestTool.cmp_list(_dbs, ['main', 'memory', 'db_init_test']),
            _tips,
            _dbs
        )


class MySQLDriverTestCase(DriverTestCaseFW):
    """
    通用的驱动测试方法类
    """

    #############################
    # 不同驱动自有的测试方法
    #############################
    def __init__(self) -> None:
        """
        构造函数
        """
        self.driver_id = 'MySQL'

        # 创建驱动
        self.driver = MySQLNosqlDriver(
            connect_config={
                'host': '127.0.0.1',
                'port': 3306,
                'usedb': 'dev_tf',
                'username': 'root',
                'password': '123456'
            },
            driver_config={
                'ignore_index_error': False,
                'debug': True,
                'close_action': 'commit',
                'init_db': self.init_db,
                'init_collections': self.init_collections
            }
        )

    @property
    def self_test_order(self) -> list:
        """
        当前驱动自有的测试清单
        """
        return ['self_test_partition_1', 'self_test_partition_2']

    #############################
    # 自有的测试函数
    #############################
    def self_test_partition_1(self) -> tuple:
        _tips = '自有测试1: 测试分区处理'

        # 建表参数
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        _db = _test_dbs[0]
        _collection = 'tb_full_type_partition'
        _indexs = {
            'idx_tb_full_type_partition_c_index': {
                'keys': {
                    'c_index': {'asc': 1}
                },
                'paras': {
                    'unique': True
                }
            }
        }
        _fixed_col_define = {
            'c_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
            'c_str': {'type': 'str', 'len': 50, 'comment': '注释2'},
            'c_str_no_len': {'type': 'str', 'comment': '注释3'},
            'c_bool': {'type': 'bool'},
            'c_int': {'type': 'int'},
            'c_float': {'type': 'float'},
            'c_json': {'type': 'json', 'comment': '注释4'}
        }
        _comment = '空类型表'

        # 切换数据库并删除表
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_db))
        try:
            AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))
        except:
            pass

        # 测试hash分区
        _partition = {
            'type': 'hash', 'count': 3,
            'columns': [
                {'col_name': 'c_int'}
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test hash: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_int': 1},
                {'c_index': 'r2', 'c_int': 2},
                {'c_index': 'r3', 'c_int': 3},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test hash: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection
        ))
        if len(_ret) != 3:
            return (False, _tips, 'test hash: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试key分区
        _partition = {
            'type': 'key', 'count': 3,
            'columns': [
                {'col_name': 'c_str', 'func': 'to_days({col_name})'},  # func应无效
                {'col_name': 'c_int'}
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test key: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 1},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 2},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 3},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test key: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection
        ))
        if len(_ret) != 3:
            return (False, _tips, 'test key: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试range分区
        _partition = {
            'type': 'range',
            'columns': [
                {
                    'col_name': 'c_int',
                    'range_list': [
                        {'name': 'p_self_1', 'value': 10},
                        {'name': 'p_self_2', 'value': 20},
                        {'name': 'p_self_3', 'value': None}
                    ]
                }
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test range: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 5},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 15},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 30},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test range: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition=['p_self_3']
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 30:
            return (False, _tips, 'test range: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试range columns分区
        _partition = {
            'type': 'range_columns',
            'columns': [
                {
                    'col_name': 'c_int',
                    'range_list': [
                        {'name': 'p_self_1', 'value': 10},
                        {'name': 'p_self_2', 'value': 20},
                        {'name': 'p_self_3', 'value': None}
                    ]
                },
                {
                    'col_name': 'c_str',
                    'range_list': [
                        {'value': "'10'"},
                        {'value': "'20'"},
                        {'value': None}
                    ]
                }
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test range columns: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 5},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 15},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 30},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test range columns: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试list分区
        _partition = {
            'type': 'list',
            'columns': [
                {
                    'col_name': 'c_int',
                    'range_list': [
                        {'name': 'p_self_1', 'value': [1, 2, 3]},
                        {'name': 'p_self_2', 'value': ["to_days('2021-01-01')", 5, 6]},
                        {'name': 'p_self_3', 'value': [10, 11, 12]}
                    ]
                }
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test list: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test list: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition=['p_self_3']
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 10:
            return (False, _tips, 'test list: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试list columns分区
        _partition = {
            'type': 'list_columns',
            'columns': [
                {
                    'col_name': 'c_str',
                    'range_list': [
                        {'name': 'p_self_1', 'value': ["'test1'"]},
                        {'name': 'p_self_2', 'value': ["'test2'"]},
                        {'name': 'p_self_3', 'value': ["'test3'"]}
                    ]
                }
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test list columns: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test list columns: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition=['p_self_3']
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 10:
            return (False, _tips, 'test list columns: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 返回成功
        return (True, _tips, '')

    def self_test_partition_2(self) -> tuple:
        _tips = '自有测试2: 测试子分区处理'

        # 建表参数
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        _db = _test_dbs[0]
        _collection = 'tb_full_type_partition2'
        _indexs = {
            'idx_tb_full_type_partition2_c_index': {
                'keys': {
                    'c_index': {'asc': 1}
                },
                'paras': {
                    'unique': True
                }
            }
        }
        _fixed_col_define = {
            'c_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
            'c_str': {'type': 'str', 'len': 50, 'comment': '注释2'},
            'c_str_no_len': {'type': 'str', 'comment': '注释3'},
            'c_bool': {'type': 'bool'},
            'c_int': {'type': 'int'},
            'c_float': {'type': 'float'},
            'c_json': {'type': 'json', 'comment': '注释4'}
        }
        _comment = '空类型表'

        # 切换数据库并删除表
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_db))
        try:
            AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))
        except:
            pass

        # 测试hash子分区, 指定分区名
        _partition = {
            'type': 'list_columns',
            'columns': [
                {
                    'col_name': 'c_str',
                    'range_list': [
                        {'name': 'p_self_1', 'value': ["'test1'"]},
                        {'name': 'p_self_2', 'value': ["'test2'"]},
                        {'name': 'p_self_3', 'value': ["'test3'"]}
                    ]
                }
            ],
            'sub_partition': {
                'type': 'hash', 'columns': [{'col_name': 'c_int'}], 'count': 2,
                'sub_name': [['s0', 's1'], ['s2', 's3'], ['s4', 's5']]
            }
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test sub_partition hash with name: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test sub_partition hash with name: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition=['p_self_3']
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 10:
            return (False, _tips, 'test sub_partition hash with name: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试hash子分区, 不指定分区名
        _partition = {
            'type': 'list_columns',
            'columns': [
                {
                    'col_name': 'c_str',
                    'range_list': [
                        {'name': 'p_self_1', 'value': ["'test1'"]},
                        {'name': 'p_self_2', 'value': ["'test2'"]},
                        {'name': 'p_self_3', 'value': ["'test3'"]}
                    ]
                }
            ],
            'sub_partition': {
                'type': 'hash', 'columns': [{'col_name': 'c_int'}], 'count': 2
            }
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test sub_partition hash no name: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test sub_partition hash no name: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition=['p_self_3']
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 10:
            return (False, _tips, 'test sub_partition hash no name: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试key子分区
        _partition = {
            'type': 'list_columns',
            'columns': [
                {
                    'col_name': 'c_str',
                    'range_list': [
                        {'name': 'p_self_1', 'value': ["'test1'"]},
                        {'name': 'p_self_2', 'value': ["'test2'"]},
                        {'name': 'p_self_3', 'value': ["'test3'"]}
                    ]
                }
            ],
            'sub_partition': {
                'type': 'key', 'columns': [{'col_name': 'c_int'}, {'col_name': 'c_str_no_len'}], 'count': 2,
                'sub_name': [['s0', 's1'], ['s2', 's3'], ['s4', 's5']]
            }
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test sub_partition key with name: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3, 'c_str_no_len': 'a'},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5, 'c_str_no_len': 'b'},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10, 'c_str_no_len': 'c'},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test sub_partition key with name: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 返回成功
        return (True, _tips, '')


class PgSQLDriverTestCase(DriverTestCaseFW):
    """
    通用的驱动测试方法类
    """

    #############################
    # 不同驱动自有的测试方法
    #############################
    def __init__(self) -> None:
        """
        构造函数
        """
        self.driver_id = 'PgSQL'

        # 创建驱动
        self.driver = PgSQLNosqlDriver(
            connect_config={
                'host': '127.0.0.1',
                'port': 5432,
                'usedb': 'public',
                'username': 'root',
                'password': '123456',
                'dbname': 'test_db'
            },
            driver_config={
                'debug': True,
                'close_action': 'commit',
                'init_db': self.init_db,
                'init_collections': self.init_collections
            }
        )

    @property
    def self_test_order(self) -> list:
        """
        当前驱动自有的测试清单
        """
        return ['self_test_partition_1', 'self_test_partition_2']

    #############################
    # 自有的测试函数
    #############################
    def self_test_partition_1(self) -> tuple:
        _tips = '自有测试1: 测试分区处理'

        # 建表参数
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        _db = _test_dbs[0]
        _collection = 'tb_full_type_partition'
        _indexs = {
            'idx_tb_full_type_partition_c_index': {
                'keys': {
                    'c_index': {'asc': 1}
                },
                'paras': {
                    'unique': True
                }
            }
        }
        _fixed_col_define = {
            'c_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
            'c_str': {'type': 'str', 'len': 50, 'comment': '注释2'},
            'c_str_no_len': {'type': 'str', 'comment': '注释3'},
            'c_bool': {'type': 'bool'},
            'c_int': {'type': 'int'},
            'c_float': {'type': 'float'},
            'c_json': {'type': 'json', 'comment': '注释4'}
        }
        _comment = '空类型表'

        # 切换数据库并删除表
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_db))
        try:
            AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))
        except:
            pass

        # 测试hash分区
        _partition = {
            'type': 'hash', 'count': 3,
            'columns': [
                {'col_name': 'c_int'}, {'col_name': 'c_str'}
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test hash: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_int': 1, 'c_str': 'test1'},
                {'c_index': 'r2', 'c_int': 2, 'c_str': 'test2'},
                {'c_index': 'r3', 'c_int': 3, 'c_str': 'test3'},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test hash: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection
        ))
        if len(_ret) != 3:
            return (False, _tips, 'test hash: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试range分区
        _partition = {
            'type': 'range',
            'columns': [
                {
                    'col_name': 'c_int',
                    'range_list': [
                        {'name': 'p_self_1', 'value': 10},
                        {'name': 'p_self_2', 'value': 20},
                        {'name': 'p_self_3', 'value': None}
                    ]
                }
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test range: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 5},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 15},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 30},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test range: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition='p_self_3'
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 30:
            return (False, _tips, 'test range: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 测试list分区
        _partition = {
            'type': 'list',
            'columns': [
                {
                    'col_name': 'c_int',
                    'range_list': [
                        {'name': 'p_self_1', 'value': [1, 2, 3]},
                        {'name': 'p_self_2', 'value': ["cast(left('4test', 1) as int)", 5, 6]},
                        {'name': 'p_self_3', 'value': [10, 11, 12]}
                    ]
                }
            ]
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test list: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test list: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition='p_self_3'
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 10:
            return (False, _tips, 'test list: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 返回成功
        return (True, _tips, '')

    def self_test_partition_2(self) -> tuple:
        _tips = '自有测试2: 测试子分区处理'

        # 建表参数
        _test_dbs = [_db_info[0] for _db_info in self.test_db_info]
        _db = _test_dbs[0]
        _collection = 'tb_full_type_partition2'
        _indexs = {
            'idx_tb_full_type_partition2_c_index': {
                'keys': {
                    'c_index': {'asc': 1}
                },
                'paras': {
                    'unique': True
                }
            }
        }
        _fixed_col_define = {
            'c_index': {'type': 'str', 'len': 20, 'comment': '注释1'},
            'c_str': {'type': 'str', 'len': 50, 'comment': '注释2'},
            'c_str_no_len': {'type': 'str', 'comment': '注释3'},
            'c_bool': {'type': 'bool'},
            'c_int': {'type': 'int'},
            'c_float': {'type': 'float'},
            'c_json': {'type': 'json', 'comment': '注释4'}
        }
        _comment = '空类型表'

        # 切换数据库并删除表
        AsyncTools.sync_run_coroutine(self.driver.switch_db(_db))
        try:
            AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))
        except:
            pass

        # 测试hash子分区
        _partition = {
            'type': 'list',
            'columns': [
                {
                    'col_name': 'c_str',
                    'range_list': [
                        {'name': 'p_self_1', 'value': ["'test1'"]},
                        {'name': 'p_self_2', 'value': ["'test2'"]},
                        {'name': 'p_self_3', 'value': ["'test3'"]}
                    ]
                }
            ],
            'sub_partition': {
                'type': 'hash', 'columns': [{'col_name': 'c_int'}], 'count': 2
            }
        }

        AsyncTools.sync_run_coroutine(self.driver.create_collection(
            _collection, indexs=_indexs, fixed_col_define=_fixed_col_define,
            comment=_comment, partition=_partition
        ))
        if not AsyncTools.sync_run_coroutine(self.driver.collections_exists(_collection)):
            return (False, _tips, 'test sub_partition hash with name: table [%s] not exists on db [%s]' % (_collection, _db))

        _ret = AsyncTools.sync_run_coroutine(self.driver.insert_many(
            _collection, rows=[
                {'c_index': 'r1', 'c_str': 'test1', 'c_int': 3},
                {'c_index': 'r2', 'c_str': 'test2', 'c_int': 5},
                {'c_index': 'r3', 'c_str': 'test3', 'c_int': 10},
            ]
        ))
        if _ret != 3:
            return (False, _tips, 'test sub_partition hash with name: insert [%s.%s] row error: %d' % (_db, _collection, _ret))

        _ret = AsyncTools.sync_run_coroutine(self.driver.query_list(
            _collection, partition='p_self_3'
        ))
        if len(_ret) != 1 or _ret[0]['c_int'] != 10:
            return (False, _tips, 'test sub_partition hash with name: query [%s.%s] row error: %s' % (_db, _collection, str(_ret)))

        AsyncTools.sync_run_coroutine(self.driver.drop_collection(_collection))

        # 返回成功
        return (True, _tips, '')


class MongoDriverTestCase(DriverTestCaseFW):
    """
    MongoDB的驱动测试方法类
    """
    def __init__(self) -> None:
        """
        构造函数
        """
        self.driver_id = 'Mongo'

        # 先删除数据库, 清空数据
        self.driver = MongoNosqlDriver(
            connect_config={
                'host': '127.0.0.1', 'port': 27017, 'dbname': 'admin',
                'username': 'root', 'password': '123456'
            }
        )
        for _db_name in self.init_db.keys():
            AsyncTools.sync_run_coroutine(self.driver.drop_db(_db_name))
        for _db_info in self.test_db_info:
            AsyncTools.sync_run_coroutine(self.driver.drop_db(_db_info[0]))
        for _db_info in self.delete_db_info:
            AsyncTools.sync_run_coroutine(self.driver.drop_db(_db_info[0]))

        AsyncTools.sync_run_coroutine(self.driver.destroy())

        # 重新创建驱动
        self.driver = MongoNosqlDriver(
            connect_config={
                'host': '127.0.0.1', 'port': 27017, 'dbname': 'admin',
                'username': 'root', 'password': '123456'
            },
            driver_config={
                'init_db': self.init_db,
                'init_collections': self.init_collections
            }
        )


class TestSQLiteDriver(unittest.TestCase):

    def test(self):
        return
        # 初始化驱动
        _case = SQLiteDriverTestCase()

        try:
            # 执行自有测试案例
            for _fun_name in _case.self_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> self case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

            # 执行通用测试案例
            for _fun_name in _case.common_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> common case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

        finally:
            # 销毁连接
            _case.destroy()


class TestMySQLDriver(unittest.TestCase):

    def test(self):
        return
        # 初始化驱动
        _case = MySQLDriverTestCase()

        try:
            # 执行自有测试案例
            for _fun_name in _case.self_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> self case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

            # 执行通用测试案例
            for _fun_name in _case.common_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> common case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

        finally:
            # 销毁连接
            _case.destroy()


class TestPgSQLDriver(unittest.TestCase):

    def test(self):
        return
        # 初始化驱动
        _case = PgSQLDriverTestCase()

        try:
            # 执行自有测试案例
            for _fun_name in _case.self_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> self case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

            # 执行通用测试案例
            for _fun_name in _case.common_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> common case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

        finally:
            # 销毁连接
            _case.destroy()


class TestMongoDriver(unittest.TestCase):

    def test(self):
        # return
        # 初始化驱动
        _case = MongoDriverTestCase()

        try:
            # 执行自有测试案例
            for _fun_name in _case.self_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> self case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

            # 执行通用测试案例
            for _fun_name in _case.common_test_order:
                _fun = getattr(_case, _fun_name)
                _is_success, _tips, _show_info = _fun()
                self.assertTrue(_is_success, msg='%s -> common case[%s] %s error: %s' % (
                    _case.driver_id, _fun_name, _tips, str(_show_info))
                )

        finally:
            # 销毁连接
            _case.destroy()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
