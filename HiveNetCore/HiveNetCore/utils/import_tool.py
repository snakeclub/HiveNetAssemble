#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
库导入工具

@module import_tool
@file import_tool.py

"""

import sys
import os
from types import ModuleType
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.utils.file_tool import FileTool


__MOUDLE__ = 'import_tool'  # 模块名
__DESCRIPT__ = u'库导入工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class ImportTool(object):
    """
    库导入工具
    提供库导入相关功能, 包括动态导入库的支持

    """

    @staticmethod
    def check_module_imported(module_name):
        """
        检查指定模块名是否已导入

        @param {string} module_name - 要检查的模块名, 形式有以下几种:
            (1)基础库的情况, 例如'sys'
            (2)子库情况, 例如'simple_log.Logger'

        @returns {bool} - True-模块已导入, False-模块未导入
        """
        return module_name in sys.modules.keys()

    @staticmethod
    def get_imported_module(module_name):
        """
        根据模块名称获取已导入的模块, 如果模块不存在返回None

         @param {string} module_name - 要获取的模块名, 形式有以下几种:
            (1)基础库的情况, 例如'sys'
            (2)子库情况, 例如'simple_log.Logger'

        @returns {Module} - 已导入的模块对象, 可以直接引用该对象执行操作
        """
        if ImportTool.check_module_imported(module_name):
            return sys.modules[module_name]
        else:
            return None

    @staticmethod
    def get_member_from_module(module, member_name):
        """
        从指定模块中获取成员对象( 例如类)

        @param {Module} module - 要处理的模块对象
        @param {string} member_name - 成员对象名

        @return {object} - 返回成员对象
        """
        return getattr(module, member_name)

    @staticmethod
    def import_module(module_name, as_name=None, extend_path=None, import_member=None, is_force=False):
        """
        导入指定模块
        如果不指定is_force参数强制加载, 已经加载过的模块不会重新加载, 对使用有import_member模式的
        使用方式可能会存在问题

        @param {string} module_name - 要导入的模块名
        @param {string} as_name=None - 对导入的模块名设置的别名
        @param {string} extend_path=None - 对于存放在非python搜索路径( sys.path) 外的模块, 需要指定扩展搜索路径
        @param {string} import_member=None - 指定导入模块对应的成员对象, None代表不指定导入对象, "*"代表导入模块的所有对象:
            效果如from module_name import import_member
        @param {bool} is_force=False - 是否强制执行导入的命令动作, True-强制再执行导入命令, Fasle-如果模块已存在则不导入

        @returns {Module} - 已导入的模块对象, 可以直接引用该对象执行操作

        @example
            lib_obj = ImportTools.import_module('os')
            print(lib_obj.path.realpath(''))

        """
        if is_force or not ImportTool.check_module_imported(module_name):
            # 模块未导入, 导入模块
            if extend_path is not None:
                # 指定了路径, 组装路径
                lib_path = os.path.realpath(extend_path)
                if lib_path not in sys.path:
                    sys.path.append(lib_path)

            # 导入对象
            _exec_code = ''
            if import_member is None or import_member == '':
                # 无需指定对象导入
                _exec_code = 'import %s' % module_name
                if as_name is not None:
                    _exec_code = '%s as %s' % (_exec_code, as_name)
            else:
                _exec_code = 'from %s import %s' % (module_name, import_member)

            # 执行导入动作
            exec(_exec_code)

        # 返回模块
        return sys.modules[module_name]

    @staticmethod
    def unimport_module(module_name):
        """
        卸载已导入的模块

        @param {string} module_name - 要卸载的模块名
        """
        if module_name in sys.modules.keys():
            del sys.modules[module_name]

    @staticmethod
    def has_attr(module_obj, attr_name):
        """
        检查模块或对象是否有指定名称的属性

        @param {Module} module_obj - 模块对象
        @param {string} attr_name - 属性名( 类名/函数名/属性名)

        @returns {bool} - 是否包含属性, True-包含, False-不包含

        """
        return hasattr(module_obj, attr_name)

    @staticmethod
    def get_attr(module_obj, attr_name):
        """
        获取对象的指定属性( 直接使用)

        @param {Module} module_obj - 模块对象
        @param {string} attr_name - 属性名( 类名/函数名/属性名)

        @returns {object} - 具体属性引用, 可以直接使用

        """
        return getattr(module_obj, attr_name)

    @staticmethod
    def get_module_name(module_obj):
        """
        获取模块名, 如果模块是包中, 模块名会包括包路径

        @param {Module} module_obj - 模块对象

        @returns {string} - 模块对象的名称

        """
        return module_obj.__name__


class DynamicLibManager(object):
    """
    动态库加载管理类
    """

    def __init__(self, base_lib_path: str) -> None:
        """
        构造函数

        @param {str} base_lib_path - 默认加载动态模块所在目录
        """
        # 默认支持插件所在目录
        self.base_lib_path = os.path.abspath(base_lib_path)

        # 已加载的模块字典, key为模块名, value为模块对象
        self.modules = dict()
        # 已经初始化的产品实例对象缓存, key为'real_module_name.real_class_name.cache_id', value为实例对象
        self.instances = dict()
        # 模块检索字典, key为检索名, value为模块名
        self.modules_mapping = dict()

    #############################
    # 公共函数
    #############################
    def load(self, path: str = None, module_name: str = None, as_name: str = None, class_mapping: dict = None):
        """
        装载指定模块模块

        @param {str} path=None - 文件路径或加载模块的指定搜索路径
        @param {str} module_name=None - 要加载的模块名, 注意模块名必须全局唯一
        @param {str} as_name=None - 获取模块对象的检索名
        @param {dict} class_mapping=None - 类名映射字典, key为类别名, value为真实的类名
            注: 类名映射是设置在as_name下, 因此如果要使用该参数, 请设置as_name(例如设置为和模块名一致)

        @returns {tuple} - 返回 (module_name, module_obj)

        @example path和module_name组合使用的例子
            1、path为完整文件路径, module_name不设置, 则导入模块名为文件名(不含.py)
                例如: path='/test/xxx.py', module_name=None
            2、path为文件所在目录, module_name设置为文件名(不含.py), 按文件名自动获取文件进行导入
                例如: path='/test', module_name='xxx'
            3、path为包所在目录, module_name设置为包含后续包路径的模块名, 需注意每个包路径下要有__init__.py文件
                例如: path='./test', module_name='aaa.bbb.xxx'
            4、path设置为None, module_name设置为要搜索的模块名, 会自动从python搜索路径(sys.path)中查找模块
        """
        # 标准化模块名和路径
        _path = path
        _module_name = module_name
        if _path is not None and _module_name is None:
            _module_name = FileTool.get_file_name_no_ext(_path)
            _path = FileTool.get_file_path(_path)

        # 如果已导入, 则无需重新导入
        _module_obj = self.modules.get(_module_name, None)
        if _module_obj is None:
            _module_obj = ImportTool.import_module(
                _module_name, extend_path=_path, is_force=True
            )
            # 添加到搜索字典中
            self.modules[_module_name] = _module_obj

        # 设置检索字典
        if as_name is not None:
            self.modules_mapping[as_name] = {
                'module_name': _module_name, 'class_mapping': {} if class_mapping is None else class_mapping
            }

        return _module_name, _module_obj

    def set_as_name(self, module_name: str, as_name: str, class_mapping: dict = None, as_name_first: bool = True):
        """
        为模块获取设置检索名

        @param {str} module_name - 模块名
        @param {str} as_name - 模块对象的检索名
        @param {dict} class_mapping=None - 类名映射字典, key为类别名, value为真实的类名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        _module_name, _class_mapping = self._get_module_search_info(
            module_name, as_name_first=as_name_first
        )

        # 没有找到模块, 抛出异常
        if _module_name is None:
            raise ModuleNotFoundError('module [%s] not found' % module_name)

        # 添加配置或覆盖掉原配置
        self.modules_mapping[as_name] = {
            'module_name': _module_name, 'class_mapping': {} if class_mapping is None else class_mapping
        }

    def remove_as_name(self, as_name: str):
        """
        删除指定模块检索别名

        @param {str} as_name - 要删除的别名
        """
        self.modules_mapping.pop(as_name, None)

    def get_module(self, module_name: str, as_name_first: bool = True) -> ModuleType:
        """
        获取指定模块对象

        @param {str} module_name - 模块名或检索名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {ModuleType} - 返回模块对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        _module_name, _class_mapping = self._get_module_search_info(
            module_name, as_name_first=as_name_first
        )
        # 没有找到模块, 抛出异常
        if _module_name is None:
            raise ModuleNotFoundError('module [%s] not found' % module_name)

        return self.modules[_module_name]

    def get_class(self, module_name: str, class_name: str, as_name_first: bool = True):
        """
        获取指定模块的类对象(或成员函数)

        @param {str} module_name - 模块名或检索名
        @param {str} class_name - 类名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {Any} - 查找到的类对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        _module_name, _class_mapping = self._get_module_search_info(
            module_name, as_name_first=as_name_first
        )
        # 没有找到模块, 抛出异常
        if _module_name is None:
            raise ModuleNotFoundError('module [%s] not found' % module_name)

        # 获取真实类名
        _mapping_class_name = _class_mapping.get(class_name, None)
        _class_name = class_name if _mapping_class_name is None else _mapping_class_name

        return ImportTool.get_member_from_module(
            self.modules[_module_name], _class_name
        )

    def init_class(self, module_name: str, class_name: str, init_args: list = None,
            init_kwargs: dict = None, stand_alone: bool = False,
            cache_id: str = None, as_name_first: bool = True):
        """
        初始化类实例

        @param {str} module_name - 模块名或检索名
        @param {str} class_name - 类名
        @param {list} init_args=None - 类实例的初始化固定参数, 以*args方式传入
        @param {dict} init_kwargs=None - 类实例的初始化kv参数, 以*kwargs方式传入
        @param {bool} stand_alone=False - 是否生成新的独立实例(不缓存)
        @param {str} cache_id=None - 缓存的唯一检索id
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {object} - 返回初始化后的实例对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        # 获取真实模块和类名
        _real_module_name, _class_mapping = self._get_module_search_info(
            module_name, as_name_first=as_name_first
        )
        _real_class_name = _class_mapping.get(class_name, class_name)

        if stand_alone:
            # 创新新的独立实例
            _class_obj = self.get_class(_real_module_name, _real_class_name, as_name_first=False)
            return self._init_class(_class_obj, init_args=init_args, init_kwargs=init_kwargs)
        else:
            # 共享实例
            _cache_id = '' if cache_id is None else cache_id
            _instance_key = '%s.%s.%s' % (_real_module_name, _real_class_name, _cache_id)
            _instance = self.instances.get(_instance_key, None)
            if _instance is None:
                _class_obj = self.get_class(_real_module_name, _real_class_name, as_name_first=False)
                _instance = self._init_class(_class_obj, init_args=init_args, init_kwargs=init_kwargs)
                self.instances[_instance_key] = _instance
            # 返回实例
            return _instance

    def get_instance(self, module_name: str, class_name: str, cache_id: str = None, as_name_first: bool = True):
        """
        获取缓存的类实例对象

        @param {str} module_name - 模块名或检索名
        @param {str} class_name - 类名
        @param {str} cache_id=None - 缓存的唯一检索id
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {object} - 返回实例对象

        @throws {ModuleNotFoundError} - 当模块名找不到模块时抛出异常
        """
        _real_module_name, _class_mapping = self._get_module_search_info(
            module_name, as_name_first=as_name_first
        )
        _real_class_name = _class_mapping.get(class_name, class_name)
        _cache_id = '' if cache_id is None else cache_id
        _instance_key = '%s.%s.%s' % (_real_module_name, _real_class_name, _cache_id)
        _instance = self.instances.get(_instance_key, None)
        if _instance is None:
            raise ModuleNotFoundError('class [%s] instance is not found' % _instance_key)

        return _instance

    def load_by_config(self, lib_config: dict, self_lib_path: str = None, force_self_lib: bool = False):
        """
        装载动态库

        @param {dict} lib_config - 动态库加载配置
            is_self_lib {bool} - 是否私有库, 默认为False(直接管理类初始化的默认路径查找库文件)
            path {str} - 文件路径或加载模块的指定搜索路径, 该参数可以设置为None或不设置
            module_name {str} - 指定要加载的模块名, 如果path包含完整文件名可以不设置
            class {str} - 指定要获取的类名
            function {str} - 指定要获取的函数名
            instantiation {bool} - 是否要初始化类, 默认为False
            stand_alone {bool} - 是否生成新的独立实例(不缓存), 默认为False
            cache_id {str} - 缓存的唯一检索id, 可以设置为None
                注: 可以通过cache_id的不同控制一个类可以有多个实例的情况
            init_args {list} - 类实例的初始化固定参数, 以*args方式传入
            init_kwargs {dict} - 类实例的初始化kv参数, 以*kwargs方式传入
        @param {str} self_lib_path=None - 查找私有库的基础路径
        @param {bool} force_self_lib=False - 是否强制指定为私有哭(不再判断lib_config中的is_self_lib参数)

        @returns {str|object} - 根据不同情况返回不同的结果
            class和function均不设置: 返回模块名
            设置了class, 未设置function: 返回class类或class实例对象(instantiation为True的情况)
            设置了function: 返回指定的函数对象(如果class未指定, 返回的是模块中定义的函数)
        """
        # 根据是否自有插件设置不同的搜索目录
        if force_self_lib:
            _is_self_lib = True
        else:
            _is_self_lib = lib_config.get('is_self_lib', False)

        if _is_self_lib is None:
            _is_self_lib = False

        _base_lib_path = self_lib_path if _is_self_lib and self_lib_path is not None else self.base_lib_path

        _file_path = None if lib_config.get('path', None) is None else os.path.abspath(
            os.path.join(_base_lib_path, lib_config['path'])
        )

        _module_name, _module_obj = self.load(
            path=_file_path, module_name=lib_config.get('module_name', None)
        )

        _class = lib_config.get('class', None)
        _function = lib_config.get('function', None)
        if _class is None:
            if _function is None:
                return _module_name
            else:
                # 返回模块定义的函数实例
                return ImportTool.get_member_from_module(_module_obj, _function)

        # 确定产品是否需实例化
        if lib_config.get('instantiation', False):
            # 需要初始化类
            _class_obj = self.init_class(
                _module_name, _class, init_args=lib_config.get('init_args', None),
                init_kwargs=lib_config.get('init_kwargs', None),
                stand_alone=lib_config.get('stand_alone', False),
                cache_id=lib_config.get('cache_id', None),
                as_name_first=True
            )
        else:
            _class_obj = self.get_class(_module_name, _class)

        # 最后的返回处理, 判断返回的是类还是函数
        if _function is None:
            return _class_obj
        else:
            return getattr(_class_obj, _function)

    #############################
    # 内部函数
    #############################
    def _get_module_search_info(self, module_name: str, as_name_first: bool = True) -> tuple:
        """
        获取模块的检索信息

        @param {str} module_name - 模块名或检索名
        @param {bool} as_name_first=True - 优先按检索名查找模块

        @returns {tuple} - 返回真实模块名和类映射字典(real_module_name, class_mapping)
        """
        _module_name = module_name
        _class_mapping = {}
        if as_name_first:
            # 优先通过检索名获取
            _mapping_index = self.modules_mapping.get(module_name, None)
            if _mapping_index is not None:
                _module_name = _mapping_index['module_name']
                _class_mapping = _mapping_index['class_mapping']
            else:
                if self.modules.get(module_name, None) is None:
                    _module_name = None
        else:
            if self.modules.get(module_name, None) is None:
                _module_name = None

        return _module_name, _class_mapping

    def _init_class(self, class_obj, init_args: list = None, init_kwargs: dict = None):
        """
        实例化类

        @param {object} class_obj - 类对象
        @param {list} init_args=None - 类实例的初始化固定参数, 以*args方式传入
        @param {dict} init_kwargs=None - 类实例的初始化kv参数, 以*kwargs方式传入

        @returns {object} - 返回初始化的实例对象
        """
        if init_args is None and init_kwargs is None:
            return class_obj()
        elif init_args is None:
            return class_obj(**init_kwargs)
        elif init_kwargs is None:
            return class_obj(*init_args)
        else:
            return class_obj(*init_args, **init_kwargs)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
