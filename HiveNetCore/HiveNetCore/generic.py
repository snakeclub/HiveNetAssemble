#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
通用基础模块

@module generic
@file generic.py

"""
import sys
import os
import json
import re
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.i18n import get_global_i18n


__MOUDLE__ = 'generic'  # 模块名
__DESCRIPT__ = '通用基础模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = '黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


def null_fun(*args, **kwargs):
    """
    空函数
    """
    pass


class NullObj(object):
    """
    空对象定义类, 用于动态增加属性的使用场景

    @example
        msg_obj = NullObj()
        msg_obj.text = u'动态添加属性'

    """
    #############################
    # 通用的JSON转换处理函数
    #############################

    def __json__(self):
        """
        将对象转换为json字符串

        @return {string} - 转换后的json字符串
        """
        return json.dumps(NullObj.get_object_attr_dict(self), ensure_ascii=False)

    @staticmethod
    def __fromjson__(json_str):
        """
        通过json字符串获取对象实例

        @param {string} json_str - json字符串
        """
        _json_obj = json.loads(json_str)
        return NullObj.get_nullobj_from_dict(_json_obj)

    #############################
    # 内部函数
    #############################
    @staticmethod
    def get_object_attr_dict(obj, ignored_key=[]):
        """
        获取对象的属性清单字典( 循环递归获取)

        @param {object} obj - 要处理的对象
        @param {list} ignored_key=[] - 忽略的属性名清单

        """
        if type(obj) in (
            int, float, bool, complex,
            str, list, tuple, dict, set
        ):
            # 基本数据类型, 直接返回自身
            return obj
        else:
            # 对象, 统一转换为字典格式
            _dict = dict()
            _attr_dir = dir(obj)
            for _item in _attr_dir:
                if _item[0: 2] != '__' and _item not in ignored_key and not callable(getattr(obj, _item)):
                    _dict[_item] = NullObj.get_object_attr_dict(getattr(obj, _item))
            return _dict

    @staticmethod
    def get_nullobj_from_dict(obj_dict):
        """
        通过字典对象生成NullObj实例

        @param {dict} obj_dict - 字典对象

        @return {NullObj} - 生成的实例
        """
        _obj = NullObj()
        for _key in obj_dict.keys():
            if type(obj_dict[_key]) == dict:
                # 还是字典, 继续往下一层处理
                exec('_obj.%s = NullObj.get_nullobj_from_dict(obj_dict[_key])' % (_key))
            else:
                exec('_obj.%s = obj_dict[_key]' % (_key))
        return _obj


class CResult(NullObj):
    """
    通用错误类定义, 便于规范所有的错误信息返回判断标准, 可直接在该类的实例对象上直接添加其他返回值

    @example
        def fun():
            result = CResult('00000',u'success')
            result.job = 'NewJob'
            result.k1 = 10
            return result

    """

    #############################
    # 内部变量
    #############################

    _i18n_obj = None  # 国际化类实例化对象
    i18n_error_type_msg_id = ''  # 国际化记录下来的错误类型ID串( 第1位的错误说明)
    i18n_msg_id = ''  # 国际化记录下来的错误明细编码ID串
    i18n_msg_paras = None  # 国际化记录下来的可替换参数变量

    def __init__(self, code='00000', msg=None, error='', trace_str='',
                 i18n_obj=None, i18n_msg_paras=()):
        """
        构造函数

        @param {string} code='00000' - 错误码, '00000'代表成功, 参照HiveNet的错误码规范
        @param {string} msg=None - 错误信息描述, 如果i18n_obj不为None时, 该参数传入的是国际化的消息ID
            注意: 如果初始化时不传入msg( 即msg=None时) , 自动通过code查找具体的错误信息, 且在i18n_obj为None时使用全局国际化对象处理国际化信息
        @param {string} error=None - 发生异常时的异常类型type的字符串
        @param {string} trace_str='' - 错误追踪堆栈日志, 异常时的traceback.format_exc()
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {tuple} i18n_msg_paras=() - 与msg配套使用, 当使用国际化时, 可以传入变量, 用于替换msg中的$1占位符

        """
        self.code = code
        self.msg = msg
        self.i18n_msg_id = msg
        self.i18n_msg_paras = i18n_msg_paras
        self._i18n_obj = i18n_obj
        self.error = error
        self.trace_str = trace_str
        if i18n_obj is None:
            # 没有传国际化对象, 尝试获取全局的国际化对象
            self._i18n_obj = get_global_i18n()
        # 如果msg为None, 需重新设置i18n_msg_id和i18n_error_type_msg_id的值
        self.__get_i18n_msg_id()
        # 重新设置msg
        self.reset_msg()

    def is_success(self):
        """
        判断当前错误对象是否成功

        """
        return (self.code[0] == '0')

    def reset_msg(self):
        """
        重新设置错误对象的msg显示值( 例如修改了国际化控件默认语言后处理)
        """
        if self._i18n_obj is None:
            # 没有国际化, 只是通过i18n_msg_id重新设置值
            self.msg = self.i18n_msg_id
            if self.msg != '':
                # 替换占位参数
                i = 1  # 记录是第几个
                for para in self.i18n_msg_paras:
                    if self.msg.find('$' + str(i)) >= 0:
                        # 找到需要替换才处理, 提升效率
                        self.msg = re.sub(r'\$' + str(i), str(para), self.msg)
                    i = i + 1
            # 补充错误类型位
            if self.i18n_error_type_msg_id != '':
                if self.msg != '':
                    self.msg = '%s: %s' % (self.i18n_error_type_msg_id, self.msg)
                else:
                    self.msg = self.i18n_error_type_msg_id
        else:
            # 国际化处理
            self.msg = ''
            if self.i18n_error_type_msg_id != '':
                self.msg = self._i18n_obj.translate(self.i18n_error_type_msg_id)
                if self.i18n_msg_id != '':
                    self.msg = self.msg + ': '

            if self.i18n_msg_id != '':
                self.msg = self.msg + \
                    self._i18n_obj.translate(self.i18n_msg_id, self.i18n_msg_paras)

    def reset_msg_by_code(self):
        """
        根据错误码重置错误信息( 忽略原来的错误信息, 按HiveNet规范处理)
        """
        # 重置
        self.i18n_msg_id = None
        self.i18n_error_type_msg_id = None
        self.__get_i18n_msg_id()
        # 重新设置msg
        self.reset_msg()

    def change_code(self, code='00000', msg=None, i18n_msg_paras=None):
        """
        改变错误码及错误信息

        @param {string} code='00000' - 错误码
        @param {string} msg=None - 错误信息描述, 如果i18n_obj不为None时, 该参数传入的是国际化的消息ID
            注意: 如果初始化时不传入msg( 即msg=None时) , 自动通过code查找具体的错误信息, 且在i18n_obj为None时使用全局国际化对象处理国际化信息
        @param {tuple} i18n_msg_paras=() - 与msg配套使用, 当使用国际化时, 可以传入变量, 用于替换msg中的$1占位符
            注意: 如果初始化时不传入i18n_msg_paras( 即i18n_msg_paras=None时) , 代表不改变原来传入的占位符变量

        """
        self.code = code
        self.msg = msg
        self.i18n_msg_id = msg
        if i18n_msg_paras is not None:
            self.i18n_msg_paras = i18n_msg_paras
        # 如果msg为None, 需重新设置i18n_msg_id和i18n_error_type_msg_id的值
        self.__get_i18n_msg_id()
        # 重新设置msg
        self.reset_msg()

    def standard_copy_to(self, dest_obj):
        """
        复制结果对象的标准返回值到新对象中
        简单数据类型( int、string) 只要共享地址即可, 因为对变量重新复制会指向新的地址,
        不会影响原来的变量值；复杂数据类型( dict等) 要通过deepcopy方式拷贝, 避免同一内存信息改变互相影响

        @param {object} dest_obj - 要复制到的CResult对象

        """
        dest_obj.code = self.code
        dest_obj.msg = self.msg
        dest_obj.error = self.error
        dest_obj.trace_str = self.trace_str
        dest_obj.i18n_msg_id = self.i18n_msg_id
        dest_obj.i18n_msg_paras = self.i18n_msg_paras
        dest_obj.i18n_error_type_msg_id = self.i18n_error_type_msg_id

    def __get_i18n_msg_id(self):
        """
        获取并设置i18n_msg_id的值
        """
        # 尝试先装载错误码映射
        _map_error_code = self.__get_map_error_code()

        # 获取代码表, 区分错误类型及错误明细编码
        if self.code[0] in _map_error_code.keys():
            self.i18n_error_type_msg_id = _map_error_code[self.code[0]]
        else:
            self.i18n_error_type_msg_id = 'unknow'  # 没有定义国际化时使用未知代替

        if self.i18n_msg_id is None or self.i18n_msg_id == '':
            # 只有原来没有设置过才通过标准错误码映射修改, 否则保持不变
            if self.code[1:] in _map_error_code.keys():
                self.i18n_msg_id = _map_error_code[self.code[1:]]
            else:
                self.i18n_msg_id = ''

    def __get_map_error_code(self):
        """
        获取全局的错误码映射表

        """
        _map_error_code = RunTool.get_global_var('HIVENET_ERROR_CODE_MAP')
        if _map_error_code is None:
            _map_file = os.path.realpath(os.path.abspath(os.path.dirname(__file__) + '/') +
                                         '/hivenet_error_code/map_error_code.json')
            _map_error_code = {}
            with open(_map_file, 'rt', encoding='utf-8') as f:
                _map_error_code = json.load(f)
            RunTool.set_global_var('HIVENET_ERROR_CODE_MAP', _map_error_code)
        return _map_error_code

    def __str__(self):
        """
        提供系统层级的str输出格式化字符

        """
        _str = '%s:\n' % (str(type(self)))
        # 其他属性
        _attr_dir = dir(self)
        for _item in _attr_dir:
            if _item[0: 2] != '__' and not callable(getattr(self, _item)) and _item not in ['_i18n_obj', 'i18n_msg_paras', 'i18n_msg_id', 'error']:
                _str += '  (attr).%s=%s\n' % (_item, str(getattr(self, _item)))
        # __dict__上的属性
        if hasattr(self, '__dict__'):
            for _item in self.__dict__.items():
                if _item[0] not in _attr_dir and _item[0] not in ['_i18n_obj', 'i18n_msg_paras', 'i18n_msg_id', 'error']:
                    _str += '  (dict).%s=%s\n' % (_item[0], str(_item[1]))

        return _str

    #############################
    # 通用的JSON转换处理函数
    #############################
    def __json__(self):
        """
        将对象转换为json字符串

        @return {string} - 转换后的json字符串
        """
        return json.dumps(NullObj.get_object_attr_dict(self, ignored_key=['_i18n_obj', ]), ensure_ascii=False)

    @staticmethod
    def __fromjson__(json_str):
        """
        通过json字符串获取对象实例

        @param {string} json_str - json字符串
        """
        _json_obj = json.loads(json_str)
        _obj = CResult(
            code=_json_obj['code'],
            msg=_json_obj['msg'],
            error=_json_obj['error'],
            trace_str=_json_obj['trace_str'],
            i18n_msg_paras=_json_obj['i18n_msg_paras']
        )
        _obj.i18n_error_type_msg_id = _json_obj['i18n_error_type_msg_id']
        _obj.i18n_msg_id = _json_obj['i18n_msg_id']
        return _obj


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
