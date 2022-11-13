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
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetNoSql.mongo import MongoNosqlDriver

# 开启异步事件嵌套执行支持
AsyncTools.nest_asyncio_apply()


class TestMongoNosqlDriver(unittest.TestCase):
    """
    测试nosql数据库Mongodb适配器
    """

    def test(self):
        _driver = MongoNosqlDriver(
            connect_config={
                'host': '127.0.0.1', 'port': 27017, 'dbname': 'admin',
                'username': 'root', 'password': '123456'
            },
            driver_config={
                'init_collections': {
                    # 启动时创建表
                    'auto_db': {
                        't_auto_table': {
                            'index_only': False,
                            'indexs': {
                                'idx_t_auto_table_name': {
                                    'keys': {'c_name': {'asc': 1}},
                                    'paras': {
                                        'unique': True
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )

        # 创建数据库并切换
        _ret = _driver.create_db('my_db')

        # 列出所有数据库名
        _ret = AsyncTools.sync_run_coroutine(_driver.list_dbs())
        print(_ret)

        # 删除表
        _ret = AsyncTools.sync_run_coroutine(_driver.drop_collection('t_test1'))
        _ret = AsyncTools.sync_run_coroutine(_driver.drop_collection('t_test2'))

        # 创建表和对应的索引
        _ret = AsyncTools.sync_run_coroutine(
            _driver.create_collection(
                't_test1', indexs={
                    'idx_t_test1_name': {
                        'keys': {'c_name': {'asc': 1}},
                        'paras': {
                            'unique': True
                        }
                    },
                    'idx_t_test1_sex_job': {
                        'keys': {'c_sex': {'asc': 1}, 'c_job': {'asc': -1}},
                    }
                }
            )
        )

        _ret = AsyncTools.sync_run_coroutine(
            _driver.create_collection(
                't_test2', indexs={
                    'idx_t_test2_name': {
                        'keys': {'c_name': {'asc': 1}},
                        'paras': {
                            'unique': True
                        }
                    },
                    'idx_t_test2_age': {'keys': {'c_age': {'asc': 1}}},
                    'idx_t_test2_sex_job': {
                        'keys': {'c_sex': {'asc': 1}, 'c_job': {'asc': -1}},
                    }
                }
            )
        )

        # 列出所有表名
        _ret = AsyncTools.sync_run_coroutine(_driver.list_collections())
        self.assertTrue('t_test1' in _ret, msg='list collections error: %s' % str(_ret))

        # 列出指定表名
        _ret = AsyncTools.sync_run_coroutine(_driver.list_collections(filter={'name': 't_test2'}))
        self.assertTrue('t_test2' in _ret and len(_ret) == 1, msg='list collections error: %s' % str(_ret))

        # 插入一条记录
        _ret = AsyncTools.sync_run_coroutine(_driver.insert_one('t_test1', {
            'c_name': 'name1', 'c_sex': 'male', 'c_job': 'teacher'
        }))
        print(_ret)

        # 插入多条记录
        _ret = AsyncTools.sync_run_coroutine(
            _driver.insert_many(
                't_test1', [
                    {'c_name': 'name2', 'c_sex': 'female', 'c_job': 'teacher'},
                    {'c_name': 'name3', 'c_sex': 'male', 'c_job': 'worker'},
                    {'c_name': 'name4', 'c_sex': 'female', 'c_job': 'teacher'},
                ]
            )
        )
        self.assertTrue(_ret == 3, msg='insert_many error: %s' % str(_ret))

        # 查询记录
        _ret = AsyncTools.sync_run_coroutine(_driver.query_list(
            't_test1', filter={'c_job': 'teacher'},
            projection={'_id': False, 'c_name': True, 'c_job': True},
            sort=[('c_name', -1), ('c_sex', 1)], skip=1, limit=1
        ))
        # 查询记录
        self.assertTrue(
            len(_ret) == 1 and _ret[0]['c_name'] == 'name2' and _ret[0].get('_id', None) is None,
            msg='query_list error: %s' % str(_ret)
        )

        # 迭代方式返回结果
        def query_iter_deal_func(item):
            print(item)

        _ret = AsyncTools.sync_run_coroutine(_driver.query_iter('t_test1'))
        AsyncTools.sync_run_coroutine(
            AsyncTools.async_for_iter(_ret, query_iter_deal_func)
        )

        # 查询记录数量
        _ret = AsyncTools.sync_run_coroutine(_driver.query_count('t_test1'))
        self.assertTrue(_ret == 4, msg='query_count error: %s' % str(_ret))

        # 更新记录
        _filter = {'c_name': 'not exist'}
        _update = {'$set': {'c_job': 'driver'}}
        _ret = AsyncTools.sync_run_coroutine(_driver.update(
            't_test1', _filter, _update, multi=False
        ))
        self.assertTrue(_ret == 0, msg='update one not exists: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(_driver.update(
            't_test1', _filter, _update
        ))
        self.assertTrue(_ret == 0, msg='update many not exists: %s' % str(_ret))

        _filter = {'c_sex': 'male'}
        _update = {'$set': {'c_addr': 'unknow'}}
        _ret = AsyncTools.sync_run_coroutine(_driver.update(
            't_test1', _filter, _update, multi=False
        ))
        self.assertTrue(_ret == 1, msg='update one exists: %s' % str(_ret))

        _ret = AsyncTools.sync_run_coroutine(_driver.update(
            't_test1', _filter, _update
        ))
        self.assertTrue(_ret == 1, msg='update many exists: %s' % str(_ret))

        # 删除记录
        _ret = AsyncTools.sync_run_coroutine(_driver.delete(
            't_test1', {'c_name': 'name4'}
        ))
        self.assertTrue(_ret == 1, msg='delete many exists: %s' % str(_ret))

        # 更新及删除后展示, $set也可以添加新字段
        print('after update')
        _ret = AsyncTools.sync_run_coroutine(_driver.query_iter('t_test1'))
        AsyncTools.sync_run_coroutine(
            AsyncTools.async_for_iter(_ret, query_iter_deal_func)
        )

        # 测试汇总
        print('测试汇总')
        _ret = AsyncTools.sync_run_coroutine(
            _driver.insert_many(
                't_test2', [
                    {'c_name': 'name1', 'c_sex': 'female', 'c_job': 'teacher', 'c_age': 1},
                    {'c_name': 'name2', 'c_sex': 'male', 'c_job': 'worker', 'c_age': 2},
                    {'c_name': 'name3', 'c_sex': 'female', 'c_job': 'teacher', 'c_age': 3},
                    {'c_name': 'name4', 'c_sex': 'male', 'c_job': 'teacher', 'c_age': 4},
                    {'c_name': 'name5', 'c_sex': 'female', 'c_job': 'teacher', 'c_age': 5},
                ]
            )
        )

        _ret = AsyncTools.sync_run_coroutine(
            _driver.query_group_by(
                't_test2',
                group={'sex': '$c_sex', 'job': '$c_job', 'count': {'$sum': 1}, 'sum_age': {'$sum': '$c_age'}, 'name_first': {'$first': '$c_name'}, 'name_last': {'$last': '$c_name'}},
                projection={'sex': True, 'job': True, 'count': True, 'sum_age': True, 'name_first': True},
                sort=[('count', -1)]
            )
        )

        print(_ret)

        # 测试更新插入
        _filter = {'c_name': 'not exist'}
        _update = {
            '$set': {'c_job': 'driver'}, '$inc': {'age': 3}, '$mul': {'mul': 2}, '$min': {'min': 4},
            '$max': {'max': 5}, '$unset': {'unset': 1}, '$rename': {'a': 'b'}
        }
        _ret = AsyncTools.sync_run_coroutine(
            _driver.update(
                't_test2', _filter, _update, upsert=True
            )
        )
        print(_ret)
        print('after update insert')
        _ret = AsyncTools.sync_run_coroutine(_driver.query_iter('t_test2'))
        AsyncTools.sync_run_coroutine(
            AsyncTools.async_for_iter(_ret, query_iter_deal_func)
        )

        # 测试事务, 注意只有在mongodb副本部署的情况才能正常执行, 单机模式不支持事务处理
        # _session = AsyncTools.sync_run_coroutine(_driver.start_transaction())
        # _ret = AsyncTools.sync_run_coroutine(_driver.insert_one(
        #     't_test1', {
        #         'c_name': 'name100', 'c_sex': 'male', 'c_job': 'teacher'
        #     }, session=_session
        # ))
        # AsyncTools.sync_run_coroutine(_driver.commit_transaction(_session))
        # _ret = AsyncTools.sync_run_coroutine(_driver.query_list(
        #     't_test1', filter={'c_name': 'name100'}
        # ))
        # print(_ret)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
