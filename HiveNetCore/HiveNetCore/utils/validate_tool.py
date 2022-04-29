#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
数据校验工具
@module validate_tool
@file validate_tool.py
"""

import sys
import os
import re
import datetime
import traceback
import copy
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.generic import CResult


__MOUDLE__ = 'validate_tool'  # 模块名
__DESCRIPT__ = u'数据校验工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.11.15'  # 发布日期


# 标准验证错误信息, 可以在运行中改变成自定义的值
VALIDATE_ERR_MSG = {
    'str_not_null': '[$2] must not null',
    'str_len': 'Len of [$2] must between $4 and $5',
    'str_lenb': 'Bytes Len of [$2] must between $4 and $5',
    'str_is_int': '[$2]("$1") is not int number',
    'str_is_float': '[$2]("$1") is not float number',
    'str_is_email': '[$2]("$1") is not a Email address',
    'str_is_datetime': '[$2]("$1") is not match format "$4"',
    'str_check_date': '[$2]("$1") is not a legal date',
    'str_check_num_area': '[$2]("$1") must between $4 and $5',
    'str_check_float_size': 'The precision of [$2]("$1") not match: integer precision must less than $4 bits, decimal precision must less than $5 bits',
    'str_check_regex': '[$2]("$1") not match the regex "/$4/"',
    'check_fun': '[$2]("$1") validate failure by self define function',
    'not_null': '[$2] must not null',
    'DEFAULT_EXCEPT': '[$2]("$1") validate get exception: $4',
    'DEFAULT': '[$2]("$1") validate failure',
    'NOT_ENOUGH_VALUES': 'Object[$2] list has not enough values, at least $4 value',
    'OBJ_MUST_DICT': 'Object[$2] type must dict',
    'OBJ_MISS_KEY': '[$2] not found in object',

}

# 标识组合逻辑验证函数名清单(And/Or), 如果需要自定义组合函逻辑函数, 可修改该list
VALIDATE_LOGIC_FUN_NAME = [
    'And', 'Or', 'List'
]


class ValidateTool(object):
    """
    字符串基础校验函数
    """
    #############################
    # 内部通用工具
    #############################
    @classmethod
    def datetime_fmt_to_py(cls, format_str):
        """
        将类Oracle格式的日期时间格式化字符串转换为Python格式

        @param {string} format_str - 类Oracle格式的日期时间格式, 支持的格式如下:
            'yyyy' : 四位年份
            'yy' : 两位年份
            'MM' : 两位月份, 0－9月前面需补0
            'M' :  一位月份, 0-9月不能补0
            'dd' : 两位日期, 这里限制到不能超过31
            'd' : 一位日期, 这里限制到不能超过31
            'hh' : 两位小时, 12小时制, 这里限制到不能超过12
            'hh24' : 两位小时, 24小时制, 这里限制到不能超过23
            'h' :  一位小时, 12小时制, 这里限制到不能超过12
            'h24' :  一位小时, , 24小时制, 这里限制到不能超过23
            'mm' : 两位分钟, 这里限制到不能超过60
            'm' : 一位分钟, 这里限制到不能超过60
            'ss' : 两位秒, 这里限制到不能超过60
            's' : 一位秒, 这里限制到不能超过60
            'p' : 早上, 下午标识, AM 或 PM

        @return {string} - 转换后的Python格式
            %y 两位数的年份表示( 00-99)
            %Y 四位数的年份表示( 000-9999)
            %m 月份( 01-12)
            %d 月内中的一天( 0-31)
            %H 24小时制小时数( 0-23)
            %I 12小时制小时数( 01-12)
            %M 分钟数( 00=59)
            %S 秒( 00-59)
            %p 本地A.M.或P.M.的等价符
        """
        _format_str = format_str
        # 进行替换, 剔除有转义符的情况, 例如\y不转换
        _format_str = re.sub(r'yyyy', '%Y', _format_str)  # 四位年份
        _format_str = re.sub(r'yy', '%y', _format_str)  # 两位年份
        _format_str = re.sub(r'MM', '%m', _format_str)  # 月份
        _format_str = re.sub(r'M', '%m', _format_str)  # 月份
        _format_str = re.sub(r'dd', '%d', _format_str)  # 日期
        _format_str = re.sub(r'(?<!%)d', '%d', _format_str)  # 日期, 注意不会把%d重新替换了
        _format_str = re.sub(r'hh24', '%H', _format_str)  # 小时
        _format_str = re.sub(r'h24', '%H', _format_str)  # 小时
        _format_str = re.sub(r'hh', '%I', _format_str)  # 小时
        _format_str = re.sub(r'h', '%I', _format_str)  # 小时
        _format_str = re.sub(r'(?<!%)mm', '%M', _format_str)  # 分钟, 注意不会把%m重新替换了
        _format_str = re.sub(r'(?<!%)m', '%M', _format_str)  # 分钟, 注意不会把%m重新替换了
        _format_str = re.sub(r'ss', '%S', _format_str)  # 秒
        _format_str = re.sub(r's', '%S', _format_str)  # 秒
        _format_str = re.sub(r'p', '%p', _format_str)  # 早上, 下午标识, AM 或 PM

        # 返回结果
        return _format_str

    #############################
    # 字符串基础校验函数
    #############################
    @classmethod
    def str_not_null(cls, obj):
        """
        检查字符串是否非空

        @param {string} obj - 要检查的字符串对象

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        return (obj is not None and obj != '' and type(obj) == str)

    @classmethod
    def str_len(cls, obj, min_len, max_len):
        """
        检查字符串长度(包含两端的值)
        注: 一个汉字长度为1

        @param {string} obj - 要检查的字符串对象
        @param {int} min_len - 最小长度
        @param {int} max_len - 最大长度

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        if min_len is None:
            min_len = -1
        if max_len is None:
            max_len = -1
        _len = len(obj)
        return not (_len < min_len or (max_len > 0 and _len > max_len))

    @classmethod
    def str_lenb(cls, obj, min_len, max_len, encoding='utf-8'):
        """
        检查字符串长度(包含两端的值)
        注: gbk编码时一个汉字长度为2, utf-8编码时, 一个汉字长度为2-3

        @param {string} obj - 要检查的字符串对象
        @param {int} min_len - 最小长度
        @param {int} max_len - 最大长度
        @param {string} encoding='utf-8' - 字节编码

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        if min_len is None:
            min_len = -1
        if max_len is None:
            max_len = -1
        _len = len(obj.encode(encoding))
        return not (_len < min_len or (max_len > 0 and _len > max_len))

    @classmethod
    def str_is_int(cls, obj):
        """
        校验是否整数

        @param {string} obj - 要检查的字符串对象

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        _rep = re.search('^[+-]{0,1}\\d{1,}$', obj)
        return False if _rep is None else True

    @classmethod
    def str_is_float(cls, obj):
        """
        校验是否浮点数

        @param {string} obj - 要检查的字符串对象

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        _rep = re.search('^[+-]{0,1}\\d{1,}\\.{0,1}\\d{0,}$', obj)
        return False if _rep is None else True

    @classmethod
    def str_is_email(cls, obj):
        """
        校验是否Email

        @param {string} obj - 要检查的字符串对象

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        _rep = re.search('^[^@.]+@[^@]+$', obj)
        return False if _rep is None else True

    @classmethod
    def str_is_datetime(cls, obj, format_str='yyyy-MM-dd'):
        """
        校验是否Email

        @param {string} obj - 要检查的字符串对象
        @param {string} format_str='yyyy-MM-dd' - 时间日期格式, 支持的通配符包括:
            'yyyy' : 四位年份
            'yy' : 两位年份
            'MM' : 两位月份, 0－9月前面需补0
            'M' :  一位月份, 0-9月不能补0
            'dd' : 两位日期, 这里限制到不能超过31
            'd' : 一位日期, 这里限制到不能超过31
            'hh' : 两位小时, 12小时制, 这里限制到不能超过12
            'hh24' : 两位小时, 24小时制, 这里限制到不能超过23
            'h' :  一位小时, 12小时制, 这里限制到不能超过12
            'h24' :  一位小时, , 24小时制, 这里限制到不能超过23
            'mm' : 两位分钟, 这里限制到不能超过60
            'm' : 一位分钟, 这里限制到不能超过60
            'ss' : 两位秒, 这里限制到不能超过60
            's' : 一位秒, 这里限制到不能超过60
            'p' : 早上, 下午标识, AM 或 PM

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        _regstr = format_str.replace('\\', '\\\\')  # 将\替换为转义后的\\
        # _regstr = format_str

        def re_group_replace(text):
            # 通过正则表达式替换匹配到的组的字符串, 增加转义符
            return '\\%s' % text.group()

        # 替换转义符
        _regstr = re.sub(r'[\$\(\)\*\+\.\[\]\?\/\^\{\}\|]', re_group_replace, _regstr)
        _regstr = re.sub(r'yyyy', '[0-9]{4,4}', _regstr)  # 四位年份, 剔除有转义符的情况
        _regstr = re.sub(r'yy', '[0-9]{2,2}', _regstr)  # 两位年份, 剔除有转义符的情况
        _regstr = re.sub(r'MM', '((0[0-9])|(1[012]))', _regstr)  # 两位月份, 0－9月前面需补0
        _regstr = re.sub(r'M', '([0-9]|(1[012]))', _regstr)  # 一位月份, 0-9月不能补0
        _regstr = re.sub(r'dd', '(([012][0-9])|(3[01]))', _regstr)  # 两位日期, 这里限制到不能超过31
        _regstr = re.sub(r'd', '(([12]{0,1}[0-9])|(3[01]))', _regstr)  # 一位日期, 这里限制到不能超过31
        _regstr = re.sub(r'hh24', '(([01][0-9])|(2[0-3]))', _regstr)  # 两位小时, 这里限制到不能超过23
        _regstr = re.sub(r'hh', '(([01][0-2]))', _regstr)  # 两位小时, 这里限制到不能超过12
        _regstr = re.sub(r'h24', '((1{0,1}[0-9])|(2[0-3]))', _regstr)  # 一位小时, 这里限制到不能超过23
        _regstr = re.sub(r'h', '(([0-9]|[1][0-2]))', _regstr)  # 一位小时, 这里限制到不能超过12
        _regstr = re.sub(r'mm', '(([0-5][0-9]))', _regstr)  # 两位分钟, 这里限制到不能超过59
        _regstr = re.sub(r'm', '(([0-9]|[1-5][0-9]))', _regstr)  # 一位分钟, 这里限制到不能超过59
        _regstr = re.sub(r'ss', '(([0-5][0-9]))', _regstr)  # 两位分钟, 这里限制到不能超过59
        _regstr = re.sub(r's', '(([0-9]|[1-5][0-9]))', _regstr)  # 一位分钟, 这里限制到不能超过59
        _regstr = re.sub(r'p', '(AM|PM)', _regstr)  # 一位分钟, 这里限制到不能超过59
        _regstr = '^%s$' % _regstr

        _rep = re.search(_regstr, obj)
        if _rep is None:
            return False
        else:
            try:
                # 尝试转换为日期格式
                _format_str = cls.datetime_fmt_to_py(format_str)
                datetime.datetime.strptime(obj, _format_str)
                return True
            except:
                return False

    @classmethod
    def str_check_date(cls, obj, format_str='yyyy-MM-dd'):
        """
        校验日期是否为有效日期

        @param {string} obj - 要检查的字符串对象
        @param {string} format_str='yyyy-MM-dd' - 日期时间格式

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        # 替换为标准转换格式
        _format_str = cls.datetime_fmt_to_py(format_str)
        try:
            datetime.datetime.strptime(obj, _format_str)
            return True
        except:
            return False

    @classmethod
    def str_check_num_area(cls, obj, min_val, max_val, is_eq_min=True, is_eq_max=True):
        """
        校验数字是否在取值范围内

        @param {string} obj - 要检查的字符串对象
        @param {float} min_val - 最小值, 如果不需要比较传入None
        @param {float}} max_val - 最大值, 如果不需要比较传入None
        @param {bool} is_eq_min=True - 是否可以等于最小值
        @param {bool} is_eq_max=True - 是否可以等于最大值

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        _num = None
        try:
            _num = float(obj)
        except:
            # 转换出现异常
            return False

        # 比较最小值
        if min_val is not None:
            if not(_num > min_val or (_num == min_val and is_eq_min)):
                return False

        # 比较最大值
        if max_val is not None:
            if not(_num < max_val or (_num == max_val and is_eq_max)):
                return False

        # 比较通过
        return True

    @classmethod
    def str_check_float_size(cls, obj, int_len, decimal_len):
        """
        校验数字的精度是否满足要求

        @param {string} obj - 要检查的字符串对象
        @param {int} int_len - 整数位
        @param {int} decimal_len - 小数位

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        try:
            float(obj)
        except:
            # 转换失败说明不是数字
            return False

        _strs = obj.split('.')
        if len(_strs[0]) > int_len:
            return False
        if len(_strs) > 1 and len(_strs[1]) > decimal_len:
            return False

        # 检查通过
        return True

    @classmethod
    def str_check_regex(cls, obj, regex_str, flags='0'):
        """
        根据传入的正则表达式进行判断

        @param {string} obj - 要检查的字符串对象
        @param {string} regex_str - 正则表达式
        @param {string} flags='0' - 正则表达处理标记生成字符串, 可以多个标记组合, 例如're.I|re.L'
            可支持的标记包括:
            re.I 忽略大小写
            re.L 表示特殊字符集 \w, \W, \b, \B, \s, \S 依赖于当前环境
            re.M 多行模式
            re.S 即为 . 并且包括换行符在内的任意字符( . 不包括换行符)
            re.U 表示特殊字符集 \w, \W, \b, \B, \d, \D, \s, \S 依赖于 Unicode 字符属性数据库
            re.X 为了增加可读性, 忽略空格和 # 后面的注释

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空字符串才继续校验后面的, 如果是空字符返回成功( 空字符不校验)
        if not cls.str_not_null(obj):
            return True

        _flags = eval(flags)
        _rep = re.search(regex_str, obj, flags=_flags)
        return False if _rep is None else True

    #############################
    # 非字符串校验函数
    #############################
    @classmethod
    def check_fun(cls, obj, fun, *args, **kwargs):
        """
        根据传入的函数进行对象校验
        注: 函数不会检查对象是否为None

        @param {string} obj - 要检查的字符串对象
        @param {function} fun - 用于检查的函数, 定义如下:
            fun(obj, *args, **kwargs):
                return True/False
        @param {args} - 要传入的占位参数值
        @param {kwargs} - 要传入校验函数的参数值

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        if not callable(fun):
            return False

        try:
            _rep = fun(obj, *args, **kwargs)
            if _rep:
                return True
            else:
                return False
        except:
            return False

    @classmethod
    def not_null(cls, obj):
        """
        检查对象是否非空

        @param {object} obj - 要检查的对象

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        return (obj is not None and obj != '')

    @classmethod
    def is_type(cls, obj, data_type):
        """
        检查对象是否指定的数据类型

        @param {object} obj - 要检查的对象
        @param {type} data_type - 对象类型, 可以是基础类型如int, str, list等, 也可以是如VaildateTool等自定义类型

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空对象才继续校验后面的, 如果None返回校验通过
        if obj is None:
            return True

        if type(obj) == data_type:
            return True
        else:
            return False

    @classmethod
    def check_num_area(cls, obj, min_val, max_val, is_eq_min=True, is_eq_max=True):
        """
        校验数字是否在取值范围内

        @param {object} obj - 要检查的字符串对象
        @param {float} min_val - 最小值, 如果不需要比较传入None
        @param {float}} max_val - 最大值, 如果不需要比较传入None
        @param {bool} is_eq_min=True - 是否可以等于最小值
        @param {bool} is_eq_max=True - 是否可以等于最大值

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空对象才继续校验后面的, 如果None返回校验通过
        if obj is None:
            return True

        # 比较最小值
        if min_val is not None:
            if not(obj > min_val or (obj == min_val and is_eq_min)):
                return False

        # 比较最大值
        if max_val is not None:
            if not(obj < max_val or (obj == max_val and is_eq_max)):
                return False

        # 比较通过
        return True

    @classmethod
    def check_len(cls, obj, min_len, max_len):
        """
        检查对象长度(例如tuple、list)

        @param {obj} obj - 要检查的对象
        @param {int} min_len - 最小长度
        @param {int} max_len - 最大长度

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空对象才继续校验后面的, 如果None返回校验通过
        if obj is None:
            return True

        if min_len is None:
            min_len = -1
        if max_len is None:
            max_len = -1
        _len = len(obj)
        return not (_len < min_len or (max_len > 0 and _len > max_len))

    @classmethod
    def check_time_btween(cls, obj, min_date, max_date, format_str='yyyy-MM-dd', is_eq_min=True, is_eq_max=True):
        """
        送入的日期是否在两个日期之间

        @param {string|datetime} obj - 要检查的日期对象
            注: 如果传入的是string, 将自动通过format_str进行转换
        @param {string|datetime} min_date - 比较的最小日期时间, None代表不比较
            注: 如果传入的是string, 将自动通过format_str进行转换
        @param {string|datetime} max_date - 比较的最大日期时间, None代表不比较
            注: 如果传入的是string, 将自动通过format_str进行转换
        @param {bool} is_eq_min=True - 是否可以等于最小值
        @param {bool} is_eq_max=True - 是否可以等于最大值

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空对象才继续校验后面的, 如果None返回校验通过
        if obj is None:
            return True

        try:
            _format_str = cls.datetime_fmt_to_py(format_str)
            _obj = obj
            if type(obj) == str:
                _obj = datetime.datetime.strptime(obj, _format_str)

            if min_date is not None:
                _min_date = min_date
                if type(min_date) == str:
                    _min_date = datetime.datetime.strptime(min_date, _format_str)

                if not(_obj > _min_date or (_obj == _min_date and is_eq_min)):
                    return False

            if max_date is not None:
                _max_date = max_date
                if type(max_date) == str:
                    _max_date = datetime.datetime.strptime(max_date, _format_str)

                if not(_obj < _max_date or (_obj == _max_date and is_eq_max)):
                    return False

            # 比较通过
            return True
        except:
            return False

    @classmethod
    def check_in_enum(cls, obj, enums):
        """
        检查对象是否在枚举值中

        @param {object} obj - 要检查的对象
        @param {list|tuple} enums - 枚举列表

        @return {bool} - 校验结果, True-通过; False-不通过
        """
        # 只有非空对象才继续校验后面的, 如果None返回校验通过
        if obj is None:
            return True

        if obj in enums:
            return True
        else:
            return False

    #############################
    # 校验关系组合函数
    #############################
    @classmethod
    def And(cls, obj, rules, obj_id='object', ignore_list_miss_value=True, i18n_obj=None,
            is_use_pre_obj_id=True, pre_obj_id=''):
        """
        组合多个校验规则对同一个对象进行校验, 以'与'的关系返回检查结果

        @param {object} obj - 要检查的对象
        @param {list|tuple} rules - 校验规则列表, 格式为 (单个校验规则1, 单个校验规则2, ...)
            或 [单个校验规则1, 单个校验规则2, ...], 格式参考单个校验规则 (参考_check_by_single_rule的定义)
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        @param {string} pre_obj_id='' 内部使用, 前置对象id

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败
        """
        for _rule in rules:
            _result = cls._check_by_rule_list(
                _rule, obj, obj_id=obj_id, ignore_list_miss_value=ignore_list_miss_value,
                i18n_obj=i18n_obj, is_use_pre_obj_id=is_use_pre_obj_id, pre_obj_id=pre_obj_id
            )
            if not _result.is_success():
                return _result

        # 全部检查通过
        return CResult(code='00000', i18n_obj=i18n_obj)

    @classmethod
    def Or(cls, obj, rules, obj_id='object', ignore_list_miss_value=True, i18n_obj=None,
            is_use_pre_obj_id=True, pre_obj_id=''):
        """
        组合多个校验规则对同一个对象进行校验, 以'或'的关系返回检查结果

        @param {object} obj - 要检查的对象
        @param {list|tuple} rules - 校验规则列表, 格式为 (单个校验规则1, 单个校验规则2, ...)
            或 [单个校验规则1, 单个校验规则2, ...], 格式参考单个校验规则 (参考_check_by_single_rule的定义)
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        @param {string} pre_obj_id='' 内部使用, 前置对象id

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败
        """
        _result = None
        for _rule in rules:
            _result = cls._check_by_rule_list(
                _rule, obj, obj_id=obj_id, ignore_list_miss_value=ignore_list_miss_value,
                i18n_obj=i18n_obj, is_use_pre_obj_id=is_use_pre_obj_id, pre_obj_id=pre_obj_id
            )
            if _result.is_success():
                # 有一个通过
                return _result

        # 执行完成, 最后一个reslut一定是不成功的
        return _result

    @classmethod
    def List(cls, obj, rule, obj_id='object', ignore_list_miss_value=True, i18n_obj=None,
             is_use_pre_obj_id=True, pre_obj_id=''):
        """
        按清单方式对传入的对象列表逐一处理

        @param {tuple|list} obj - 要检查的对象列表, 本函数将会使用送入的规则(rule)逐一对列表中的对象进行校验
            注: 如果传入的obj不是列表类型, 则函数会自动将其转为[obj, ]列表进行校验, 以兼容对单一对象进行校验的情况
        @param {list|tuple|object} rule - 对对象列表的单一校验规则:
            type(rule) == list: 针对表格形式的数据进行验证, 校验规则格式为 [rule1, rule2, rule3, ...], 针对obj
                的格式为 [ [data11, data12, data13, ...], [data21, data22, data23, ...], ... ]
            type(rule) != list: 视为单一校验规则, 格式参考单个校验规则 (参考_check_by_single_rule的定义)
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        @param {string} pre_obj_id='' 内部使用, 前置对象id

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败
        """
        _check_obj = obj
        _obj_type = type(obj)
        if _obj_type not in [tuple, list]:
            _check_obj = [obj, ]

        # 遍历对象用规则执行
        _index = 0
        for _item in _check_obj:
            _show_obj_id = obj_id if not is_use_pre_obj_id else ('%s~%d' % (obj_id, _index))
            _result = cls._check_by_rule_list(
                rule, _item, obj_id=_show_obj_id, ignore_list_miss_value=ignore_list_miss_value,
                i18n_obj=i18n_obj, is_use_pre_obj_id=is_use_pre_obj_id, pre_obj_id=pre_obj_id
            )
            if not _result.is_success():
                return _result
            _index += 1

        # 全部检查通过
        return CResult(code='00000', i18n_obj=i18n_obj)

    #############################
    # 通用校验函数
    #############################
    @classmethod
    def check_by_rule(cls, rule, obj, obj_id='object', ignore_list_miss_value=True,
                      ignore_extra_keys=True, option_rule=None, i18n_obj=None, is_list_call=False,
                      is_use_pre_obj_id=True, pre_obj_id=''):
        """
        按规则检查对象

        @param {dict|list|tuple|object} rule - 检查规则, 不同类型的参数说明如下:
            dict : 实现按字典遍历检查, 检查对象也必须为对应格式的字典
                其中key为对应关键字, value为检查的具体规则(rule)
            list : 按规则列表检查对应的对象列表, 注意对象也应为list对象
                即: [rule1, rule2, rule3] <-> [obj1, obj2, obj3]
            tuple|object : 单个校验规则, 完整模式为 (校验函数, args参数, kwargs参数, 自定义错误信息)
                1、完整模式传入的是一个tuple对象, 数组每个位置说明如下:
                    第1位: 校验函数, 传入检查函数对象(如: ValidateTool.str_len), 也可传入自定义的函数
                        自定义函数的格式为: my_fun(obj, *args, **kwargs) -> bool,
                            其中args和kwargs是示意, 除第一个入参必须固定为检查对象以外, 其他的入参按需设计
                        如果要使用的校验函数是ValidateTool的静态函数, 可以直接传函数名文本, 例如'str_len'
                    第2位: args参数, 调用校验函数所需传入的占位参数, 如果没有参数可传None; 该参数应为一个tuple对象, 例如:
                        ('str_len', (3, 4), ) - 将用以下方式调用校验函数: str_len(obj, 3, 4)
                        注意: 如果args参数放置的对象不是tuple类型, 函数会自动把其加入到一个空数组中, 实现兼容处理, 例如:
                            ('str_check_regex', '^[abc]+$', ) - 将用以下方式调用校验函数: str_check_regex(obj, ('^[abc]+$'))
                    第3位: kwargs参数, 调用校验函数所需传入kv模式的字典, 如果没有参数可传None; 该参数应为一个dict对象, 例如:
                        ('str_is_datetime', None, {'format_str': 'yyyy/MM/dd'}) - 将用以下方式调用校验函数:
                            str_is_datetime(obj, format_str='yyyy/MM/dd')
                    第4位: 自定义校验不通过时返回的CResult对象的错误信息, 如果不传, 将会根据函数名自动从字典变量'VALIDATE_ERR_MSG'
                        中获取对应函数名的错误信息, 当然也可以自己增加或修改'VALIDATE_ERR_MSG'的值来自定义错误信息
                        注意: 错误信息中可以通过'$1'、'$2'等占位符将校验本身的信息替换到错误信息中, 可送入的占位变量顺序如下:
                            校验对象本身(obj)、校验对象标识(obj_id)、校验函数名、args参数(按顺序拆开)、kwargs参数(按顺序拆开)
                2、传入不完整的tuple对象, 可以只传前几个位置的参数, 例如: (校验函数, ) , (校验函数, None, kwargs参数, )
                    程序会自动将该tuple对象补全, 缺失的后面几位会使用None进行补充, 例如:
                    ('str_is_float', ) --> ('str_is_float', None, None, None)
                3、仅传入函数名(string), 针对ValidateTool自带校验函数, 且无需其他入参的情况, 例如:
                    'str_is_float' -> (ValidateTool.str_is_float, None, None, None)
                4、仅传入可执行函数, 针对自定义校验函数, 且无需其他入参的情况, 例如:
                    ValidateTool.str_is_float -> (ValidateTool.str_is_float, None, None, None)
                5、传入其他类型的对象, 程序将自动将对象转换为string去尝试对应回ValidateTool自带校验函数, 例如:
                    object -> (str(object), None, None, None)
        @param {dict|object} obj - 要检查的对象, 根据校验规则的不同应按不同格式传入:
            rule为dict : 代表按字典进行校验, 传入的obj对象也应为dict
            rule为list : 代表按列表进行相应位置的数据校验, 传入的obj对象应为list或tuple格式
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
        @param {bool} ignore_extra_keys=True - 当规则为dict时, 是否忽略数据中不存在的key
        @param {dict} option_rule=None - 指示字段是否可忽略, 只有当rule为dict的时候与rule配套使用,
            字典结构与rule一致, key为要检查的字段, value为二元列表['M'或'O', {子字典}]
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_list_call=False - 内部针对dict的校验规则使用, 用于区分函数是否已进行过列表拆分处理
            注: 指一个dict规则处理列表中的多个dict数据
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        @param {string} pre_obj_id='' 内部使用, 前置对象id

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败

        """
        _rule_type = type(rule)
        if _rule_type == dict:
            # 按字典遍历进行检查
            if not is_list_call and type(obj) in [list, tuple]:
                # 字典规则对列表时, 拆分列表检查, 相当于多行检查, 调用自己进行处理
                _index = 0
                for _obj_item in obj:
                    _obj_id = obj_id if not is_use_pre_obj_id else ('%s~%d' % (obj_id, _index))
                    _result = cls.check_by_rule(
                        rule, _obj_item, obj_id=_obj_id, ignore_list_miss_value=ignore_list_miss_value,
                        ignore_extra_keys=ignore_extra_keys, i18n_obj=i18n_obj, is_list_call=True,
                        is_use_pre_obj_id=is_use_pre_obj_id,
                        pre_obj_id=pre_obj_id
                    )
                    if not _result.is_success():
                        return _result
                    _index += 1

                # 全部检查通过, 返回成功
                return CResult(code='00000', i18n_obj=i18n_obj)
            else:
                _pre_obj_id = '' if obj_id == '' else ('%s%s->' % (pre_obj_id, obj_id))
                # 检查对象是否字典, 如果不是要返回失败
                if type(obj) != dict:
                    _show_obj_id = obj_id if not is_use_pre_obj_id else (_pre_obj_id + obj_id)
                    return CResult(code='19999', msg=VALIDATE_ERR_MSG['OBJ_MUST_DICT'],
                                   i18n_obj=i18n_obj, i18n_msg_paras=(obj, _show_obj_id, ''))

                # 遍历字典一一对应进行检查
                for _key, _value in rule.items():
                    # 检查对象的key是不是对应存在
                    if _key not in obj.keys():
                        if ignore_extra_keys and (option_rule is None or _key not in option_rule.keys() or option_rule[_key][0] != 'M'):
                            # 结合option_rule检查字段是否必填
                            continue
                        else:
                            # 检查对象不存在key
                            _show_obj_id = _key if not is_use_pre_obj_id else (_pre_obj_id + _key)
                            return CResult(code='19999', msg=VALIDATE_ERR_MSG['OBJ_MISS_KEY'],
                                           i18n_obj=i18n_obj, i18n_msg_paras=(obj, _show_obj_id, ''))

                    # key存在
                    _result = None
                    if type(rule[_key]) == dict:
                        # 下一级还是dict, 递归处理
                        _option_rule = None
                        if option_rule is not None:
                            _option_rule = option_rule[_key][1]

                        _result = cls.check_by_rule(
                            rule[_key], obj[_key], obj_id=_key, ignore_list_miss_value=ignore_list_miss_value,
                            ignore_extra_keys=ignore_extra_keys, option_rule=_option_rule,
                            i18n_obj=i18n_obj, is_list_call=False,
                            is_use_pre_obj_id=is_use_pre_obj_id,
                            pre_obj_id=_pre_obj_id
                        )
                    else:
                        # 执行检查
                        _result = cls._check_by_rule_list(
                            rule[_key], obj[_key], obj_id=_key, ignore_list_miss_value=ignore_list_miss_value,
                            i18n_obj=i18n_obj, is_use_pre_obj_id=is_use_pre_obj_id,
                            pre_obj_id=_pre_obj_id
                        )

                    # 判断检查结果
                    if not _result.is_success():
                        return _result

                # 遍历校验通过, 返回成功
                return CResult(code='00000', i18n_obj=i18n_obj)
        else:
            # 按规则列表处理
            return cls._check_by_rule_list(
                rule, obj, obj_id=obj_id, ignore_list_miss_value=ignore_list_miss_value,
                i18n_obj=i18n_obj, is_use_pre_obj_id=is_use_pre_obj_id,
                pre_obj_id=pre_obj_id
            )

    @classmethod
    def _check_by_single_rule(cls, rule, obj, obj_id='object', ignore_list_miss_value=True, i18n_obj=None,
                              is_use_pre_obj_id=True, pre_obj_id=''):
        """
        内部函数, 按一个规则校验一个对象

        @param {tuple|object} rule - 单个校验规则, 完整模式为 (校验函数, args参数, kwargs参数, 自定义错误信息)
            1、完整模式传入的是一个tuple对象, 数组每个位置说明如下:
                第1位: 校验函数, 传入检查函数对象(如: ValidateTool.str_len), 也可传入自定义的函数
                    自定义函数的格式为: my_fun(obj, *args, **kwargs) -> bool,
                        其中args和kwargs是示意, 除第一个入参必须固定为检查对象以外, 其他的入参按需设计
                    如果要使用的校验函数是ValidateTool的静态函数, 可以直接传函数名文本, 例如'str_len'
                第2位: args参数, 调用校验函数所需传入的占位参数, 如果没有参数可传None; 该参数应为一个tuple对象, 例如:
                    ('str_len', (3, 4), ) - 将用以下方式调用校验函数: str_len(obj, 3, 4)
                    注意: 如果args参数放置的对象不是tuple类型, 函数会自动把其加入到一个空数组中, 实现兼容处理, 例如:
                        ('str_check_regex', '^[abc]+$', ) - 将用以下方式调用校验函数: str_check_regex(obj, ('^[abc]+$'))
                第3位: kwargs参数, 调用校验函数所需传入kv模式的字典, 如果没有参数可传None; 该参数应为一个dict对象, 例如:
                    ('str_is_datetime', None, {'format_str': 'yyyy/MM/dd'}) - 将用以下方式调用校验函数:
                        str_is_datetime(obj, format_str='yyyy/MM/dd')
                第4位: 自定义校验不通过时返回的CResult对象的错误信息, 如果不传, 将会根据函数名自动从字典变量'VALIDATE_ERR_MSG'
                    中获取对应函数名的错误信息, 当然也可以自己增加或修改'VALIDATE_ERR_MSG'的值来自定义错误信息
                    注意: 错误信息中可以通过'$1'、'$2'等占位符将校验本身的信息替换到错误信息中, 可送入的占位变量顺序如下:
                        校验对象本身(obj)、校验对象标识(obj_id)、校验函数名、args参数(按顺序拆开)、kwargs参数(按顺序拆开)
            2、传入不完整的tuple对象, 可以只传前几个位置的参数, 例如: (校验函数, ) , (校验函数, None, kwargs参数, )
                程序会自动将该tuple对象补全, 缺失的后面几位会使用None进行补充, 例如:
                ('str_is_float', ) --> ('str_is_float', None, None, None)
            3、仅传入函数名(string), 针对ValidateTool自带校验函数, 且无需其他入参的情况, 例如:
                'str_is_float' -> (ValidateTool.str_is_float, None, None, None)
            4、仅传入可执行函数, 针对自定义校验函数, 且无需其他入参的情况, 例如:
                ValidateTool.str_is_float -> (ValidateTool.str_is_float, None, None, None)
            5、传入其他类型的对象, 程序将自动将对象转换为string去尝试对应回ValidateTool自带校验函数, 例如:
                object -> (str(object), None, None, None)
        @param {object} obj - 要检查的对象( 单一对象)
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        @param {string} pre_obj_id='' 内部使用, 前置对象id

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败
        """
        if rule is None or rule == '':
            # 没有传规则进来, 直接返回成功
            return CResult(code='00000', i18n_obj=i18n_obj)

        # 将校验规则标准化
        _check_fun_str = ''  # 校验函数名, 用来匹配固定错误信息
        _check_fun = None  # 校验函数对象
        _args = None  # 函数的args参数
        _kwargs = None  # 函数的kwargs参数
        _err_msg = None  # 错误信息

        _rule_type = type(rule)
        if _rule_type == tuple:
            # 传入的是标准校验清单
            _check_fun = rule[0]
            _args = None if len(rule) < 2 else rule[1]
            _kwargs = None if len(rule) < 3 else rule[2]
            _err_msg = None if len(rule) < 4 else str(rule[3])

            # 支持传入一个参数时不用括号括上
            if _args is not None and type(_args) != tuple:
                _args = (rule[1], )
        elif _rule_type == str:
            _check_fun = rule
        elif callable(rule):
            _check_fun = rule
        else:
            # 不匹配的校验对象, 转换为str
            _check_fun = str(rule)

        if type(_check_fun) == str:
            # 转换为正确的检查函数
            _check_fun_str = _check_fun
            _check_fun = eval('cls.' + _check_fun_str)
        else:
            # 从函数中获取名字
            try:
                _check_fun_str = _check_fun.__name__
            except:
                pass

        _show_obj_id = obj_id if not is_use_pre_obj_id else (pre_obj_id + obj_id)
        # 如果是组合逻辑函数, 需要修改入参
        _is_logic_fun = (_check_fun_str in VALIDATE_LOGIC_FUN_NAME)
        if _is_logic_fun:
            if _kwargs is None or type(_kwargs) != dict:
                _kwargs = dict()
            # 传入obj_id, i18n_obj
            _kwargs['obj_id'] = obj_id
            _kwargs['i18n_obj'] = i18n_obj
            _kwargs['ignore_list_miss_value'] = ignore_list_miss_value
            _kwargs['is_use_pre_obj_id'] = is_use_pre_obj_id
            _kwargs['pre_obj_id'] = pre_obj_id

        # 开始进行校验
        _result = None
        _i18n_msg_paras = (obj, _show_obj_id, _check_fun_str)
        try:
            _rep = None
            if _args is None and _kwargs is None:
                _rep = _check_fun(obj)
            elif _args is None and _kwargs is not None:
                _rep = _check_fun(obj, **_kwargs)
            elif _args is not None and _kwargs is None:
                _rep = _check_fun(obj, *_args)
            else:
                _rep = _check_fun(obj, *_args, **_kwargs)

            # 处理返回值
            if type(_rep) == CResult:
                # 如果是标准的返回值, 直接返回即可
                return _rep
            elif _rep:
                _result = CResult(code='00000', i18n_obj=i18n_obj)
            else:
                # 错误信息处理(没有传入自定义错误信息)
                if _err_msg is None:
                    if _check_fun_str in VALIDATE_ERR_MSG.keys():
                        _err_msg = VALIDATE_ERR_MSG[_check_fun_str]
                    else:
                        _err_msg = VALIDATE_ERR_MSG['DEFAULT']

                # 错误信息的占位信息
                if _args is not None:
                    for _item in _args:
                        _i18n_msg_paras = _i18n_msg_paras + (_item, )
                if _kwargs is not None:
                    for _item in _kwargs.values():
                        _i18n_msg_paras = _i18n_msg_paras + (_item, )

                _result = CResult(code='19999', msg=_err_msg, i18n_obj=i18n_obj,
                                  i18n_msg_paras=_i18n_msg_paras)
        except:
            # 出现异常, 特殊处理
            _error = str(sys.exc_info()[0])
            _trace_str = traceback.format_exc()
            if _err_msg is None:
                _i18n_msg_paras = _i18n_msg_paras + (_error, _trace_str)
                _err_msg = VALIDATE_ERR_MSG['DEFAULT_EXCEPT']
            else:
                # 自定义错误, 错误信息的占位信息
                if _args is not None:
                    for _item in _args:
                        _i18n_msg_paras = _i18n_msg_paras + (_item, )
                if _kwargs is not None:
                    for _item in _kwargs.values():
                        _i18n_msg_paras = _i18n_msg_paras + (_item, )
            # 组织错误信息
            _result = CResult(code='29999', msg=_err_msg, i18n_obj=i18n_obj, error=_error,
                              trace_str=_trace_str, i18n_msg_paras=_i18n_msg_paras)

        # 返回校验结果
        return _result

    @classmethod
    def _check_by_rule_list(cls, rules, obj, obj_id='object', ignore_list_miss_value=True, i18n_obj=None,
                            is_use_pre_obj_id=True, pre_obj_id=''):
        """
        内部函数, 按规则列表校验一个列表中对应位置的对象
        注: 如果传入的规则对象(rules)不是列表(list), 则将其当作标准单一规则进行检查, 兼容普通模式

        @param {list|object} rules - 规则列表, 根据传入对象的类型不同进行不同处理:
            type(rules) == list : 按规则列表检查对应的对象列表, 即: [rule1, rule2, rule3] <-> [obj1, obj2, obj3]
            type(rules) != list : 将rules整体视为单个规则对传入的对象进行检查, 即: rules <-> obj
        @param {list|tuple|object} obj - 要检查的对象列表, 规则如下:
            1、如果rules为list, 则obj也应为list|tuple; 当obj不为list|tuple的情况, 会自动转换为[obj, ]进行兼容;
            2、如果rules不为list, 则会将obj视为一个整体进行检查(不会按列表拆分)
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
            例如当为True时, [rule1, rule2, rule3] <-> [obj1, obj2, ] 不会报错
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        @param {string} pre_obj_id='' 内部使用, 前置对象id

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败
        """
        if type(rules) != list:
            # 非列表, 就是单个检查
            return cls._check_by_single_rule(
                rules, obj, obj_id=obj_id, ignore_list_miss_value=ignore_list_miss_value,
                i18n_obj=i18n_obj, is_use_pre_obj_id=is_use_pre_obj_id, pre_obj_id=pre_obj_id
            )
        else:
            _check_obj = obj
            if type(obj) not in [list, tuple]:
                # 如果传入的不是一个列表, 当作一个对象的列表处理
                _check_obj = [obj, ]
            _rules_len = len(rules)
            _obj_len = len(_check_obj)
            if not ignore_list_miss_value and _obj_len < _rules_len:
                # 不忽略不足对象时校验失败
                return CResult(code='19999', msg=VALIDATE_ERR_MSG['NOT_ENOUGH_VALUES'], i18n_obj=i18n_obj,
                               i18n_msg_paras=(obj, obj_id, '', _rules_len))

            # 遍历进行检查
            _index = 0
            while _index < _obj_len:
                _show_obj_id = obj_id if not is_use_pre_obj_id else ('%s~%d' % (obj_id, _index))
                _check_rule_fun = cls._check_by_single_rule
                if type(rules[_index]) == dict:
                    # 字典形式的校验
                    _check_rule_fun = cls.check_by_rule

                _result = _check_rule_fun(
                    rules[_index], _check_obj[_index], obj_id=_show_obj_id,
                    ignore_list_miss_value=ignore_list_miss_value, i18n_obj=i18n_obj,
                    is_use_pre_obj_id=is_use_pre_obj_id, pre_obj_id=pre_obj_id
                )
                if not _result.is_success():
                    # 校验失败
                    return _result
                _index += 1

        # 全部校验成功
        return CResult(code='00000', i18n_obj=i18n_obj)

    #############################
    # 实例化对象的处理
    #############################
    def __init__(self, rule, ignore_list_miss_value=True, ignore_extra_keys=True, i18n_obj=None,
                 is_use_pre_obj_id=True):
        """
        构造函数, 创建指定规则进行校验的实例对象

        @param {dict|list|tuple|object} rule - 校验规则, 详细定义见check_by_rule
        @param {bool} ignore_list_miss_value=True - 是否忽略列表中不足的对象
        @param {bool} ignore_extra_keys=True - 当规则为dict时, 是否忽略数据中不存在的key
        @param {SimpleI18N} i18n_obj=None - 国际化类的实例对象, 如不传入会尝试自动加载全局的国际化控件
        @param {bool} is_use_pre_obj_id=True - 是否使用前置obj_id, 当指定为True时会根据dict的层级以及列表
            中的位置修改obj_id的显示
        """
        self._rule = copy.deepcopy(rule)
        self._ignore_list_miss_value = ignore_list_miss_value
        self._ignore_extra_keys = ignore_extra_keys
        self._i18n_obj = i18n_obj
        self._is_use_pre_obj_id = is_use_pre_obj_id

    def check(self, obj, obj_id='object'):
        """
        使用实例初始化的规则进行数据检查

        @param {dict|object} obj - 要检查的对象, 根据校验规则的不同应按不同格式传入:
            rule为dict : 代表按字典进行校验, 传入的obj对象也应为dict
            rule为list : 代表按列表进行相应位置的数据校验, 传入的obj对象应为list或tuple格式
        @param {string} obj_id='object' - 要检查对象的id, 用于在错误信息中显示

        @return {CResult} - 检查结果, '00000' - 检查成功, 其他 - 检查失败
        """
        return self.check_by_rule(
            self._rule, obj, obj_id=obj_id,
            ignore_list_miss_value=self._ignore_list_miss_value,
            ignore_extra_keys=self._ignore_extra_keys,
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
