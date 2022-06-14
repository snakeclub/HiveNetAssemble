#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
服务鉴权模块

@module auth
@file auth.py
"""
import sys
import os
import copy
import re
import json
import datetime
from typing import Any
from functools import wraps
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetCore.utils.string_tool import StringTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetWebUtils.utils.cryptography import HCrypto


class AuthBaseFw(object):
    """
    服务鉴权基础框架
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        模块初始化函数
        (需由实现类继承实现)
        """
        pass

    #############################
    # 通用鉴权的修饰符处理函数
    #############################

    def auth_required(self, f=None):
        """
        当前模块的鉴权修饰符函数

        @param {function} f=None - 所执行的函数
        """
        def auth_required_internal(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 执行实际处理函数函数
                return AsyncTools.sync_run_coroutine(self.auth_required_call(f, *args, **kwargs))
            return decorated

        if f:
            return auth_required_internal(f)
        return auth_required_internal

    async def auth_required_call(self, f, *args, **kwargs):
        """
        直接执行的鉴权修饰符函数

        @param {function} f - 要执行的函数
        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {Any} - 返回响应信息(如果执行成功返回函数返回信息, 如果执行失败返回验证失败信息)
        """
        # 执行校验操作
        _result = await AsyncTools.async_run_coroutine(self._auth_call(*args, **kwargs))
        _is_auth_result = False
        if not _result[0]:
            # 校验失败, 获取校验失败的返回值
            _ret = await AsyncTools.async_run_coroutine(
                self._format_auth_resp(_result[1], _result[2])
            )
            _is_auth_result = True
        else:
            # 校验通过, 执行函数
            _ret = await AsyncTools.async_run_coroutine(f(*args, **kwargs))

        # 格式化响应对象并返回处理结果
        _last_ret = await AsyncTools.async_run_coroutine(
            self._format_last_resp(_ret, _is_auth_result)
        )
        return _last_ret

    #############################
    # 需实现类重载的函数
    #############################

    async def _auth_call(self, *args, **kwargs) -> tuple:
        """
        真正的校验处理函数

        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {tuple} - 返回校验结果数组: (校验是否通过true/false, 错误码, 失败描述)
            注: 错误码由实现类自行定义
        """
        raise NotImplementedError()

    def _format_auth_resp(self, code: Any, err_msg: str) -> Any:
        """
        格式化校验结果返回值

        @param {Any} code - 错误码
        @param {str} err_msg - 失败描述

        @returns {Any} - 格式化后的返回值
        """
        raise NotImplementedError()

    def _format_last_resp(self, resp: Any, is_auth_result: bool) -> Any:
        """
        格式化最后的响应对象

        @param {Any} resp - 最后的响应对象
        @param {bool} is_auth_result - 是否服务鉴权所返回的结果

        @returns {Any} - 转换以后的响应对象
        """
        return resp


class IPAuth(AuthBaseFw):
    """
    IP黑白名单模式验证模块
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        IP黑白名单模式验证模块

        @param {list} init_blacklist=None - 初始化的黑名单
            名单可以使用通配符禁止某个网段, 例如 ['127.0.*.*', '138.*.*.*']
        @param {list} init_whitelist=None - 初始化的白名单
        @param {int} error_resp_status=403 - 验证失败返回状态码
        @param {str|dict} error_resp_msg={'status': '10409', 'msg':'IP地址验证失败'} - 验证失败返回的信息
        """
        self.para = kwargs
        self.error_resp_status = self.para.get('error_resp_status', 403)
        self.error_resp_msg = self.para.get(
            'error_resp_msg', {'status': '10409', 'msg': 'IP地址验证失败'}
        )

        # 黑白名单管理
        self.ip_dict = {
            'blacklist': {
                'show': list(),  # 显示配置
                'reg': dict()  # 正则表的配置, key为show中的显示名, value为正则表达式规则
            },
            'whitelist': {
                'show': list(),  # 显示配置
                'reg': dict()  # 正则表的配置, key为show中的显示名, value为正则表达式规则
            }
        }

        # 初始化黑白名单
        if kwargs.get('init_blacklist', None) is not None:
            self.add_blacklist(kwargs['init_blacklist'])

        if kwargs.get('init_whitelist', None) is not None:
            self.add_whitelist(kwargs['init_whitelist'])

    #############################
    # 黑白名单检查工具
    #############################

    def verify_blacklist(self, ip: str) -> bool:
        """
        验证是否匹配黑名单

        @param {str} ip - 要验证的ip

        @returns {bool} - 检查结果, 匹配到返回True
        """
        return self._verify_ip('blacklist', ip)

    def verify_whitelist(self, ip: str) -> bool:
        """
        验证是否匹配白名单

        @param {str} ip - 要验证的ip

        @returns {bool} - 检查结果, 匹配到返回True
        """
        return self._verify_ip('whitelist', ip)

    #############################
    # 黑白名单维护工具
    #############################

    def add_blacklist(self, ips):
        """
        添加黑名单

        @param {str|list} ips - 要添加的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._add_list('blacklist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._add_list('blacklist', _ip)

    def remove_blacklist(self, ips):
        """
        删除黑名单

        @param {str|list} ips - 要删除的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._remove_list('blacklist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._remove_list('blacklist', _ip)

    def clear_blacklist(self):
        """
        清除黑名单
        """
        self.ip_dict['blacklist'].clear()
        self.ip_dict['blacklist']['show'] = list()
        self.ip_dict['blacklist']['reg'] = dict()

    def add_whitelist(self, ips):
        """
        添加白名单

        @param {str|list} ips - 要添加的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._add_list('whitelist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._add_list('whitelist', _ip)

    def remove_whitelist(self, ips):
        """
        删除白名单

        @param {str|list} ips - 要删除的ip或ip列表
        """
        if type(ips) == str:
            # 单个黑名单
            self._remove_list('whitelist', ips)
        else:
            # 多个黑名单
            for _ip in ips:
                self._remove_list('whitelist', _ip)

    def clear_whitelist(self):
        """
        清除白名单
        """
        self.ip_dict['whitelist'].clear()
        self.ip_dict['whitelist']['show'] = list()
        self.ip_dict['whitelist']['reg'] = dict()

    #############################
    # 内部函数
    #############################

    def _add_list(self, ip_type: str, ip: str):
        """
        插入名单数据

        @param {str} ip_type - 'blacklist' 或 'whitelist'
        @param {str} ip - 要插入的ip地址
        """
        _dict = self.ip_dict[ip_type]
        if ip in _dict['show']:
            # 名单已存在
            return

        # 加入显示名单
        _dict['show'].append(ip)

        # 生成名单的匹配正则表达式
        if ip.find('*') >= 0:
            # 需要生成正则表达式
            _re = re.compile('^' + ip.replace('.', '\\.').replace('*', '.*') + '$')
            _dict['reg'][ip] = _re

    def _remove_list(self, ip_type: str, ip: str):
        """
        删除名单数据

        @param {str} ip_type - 'blacklist' 或 'whitelist'
        @param {str} ip - 要删除的ip地址
        """
        _dict = self.ip_dict[ip_type]
        if ip in _dict['show']:
            # 删除正则表达式
            _dict['reg'].pop(ip, None)

            # 删除显示ip
            _dict['show'].remove(ip)

    def _verify_ip(self, ip_type: str, ip: str) -> bool:
        """
        检查ip是否匹配名单

        @param {str} ip_type - 'blacklist' 或 'whitelist'
        @param {str} ip - 要检查的ip地址

        @returns {bool} - 检查结果, 匹配到返回True
        """
        _dict = self.ip_dict[ip_type]
        if ip in _dict['show']:
            return True

        # 遍历正则规则
        for _re in _dict['reg'].values():
            if _re.search(ip) is not None:
                return True

        # 没有匹配上
        return False

    #############################
    # 重载基础框架的函数
    #############################

    async def _auth_call(self, *args, **kwargs) -> tuple:
        """
        真正的校验处理函数

        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {tuple} - 返回校验结果数组: (校验是否通过true/false, 错误码, 失败描述)
            错误码定义如下: 200-成功, 其他-失败
        """
        _status = 200
        _ip = await AsyncTools.async_run_coroutine(self._get_ip_from_request(*args, **kwargs))

        # 先检查白名单
        if len(self.ip_dict['whitelist']['show']) > 0:
            if not self.verify_whitelist(_ip):
                # 不在白名单内
                _status = self.error_resp_status
                _resp_msg = copy.deepcopy(self.error_resp_msg)

        # 再检查黑名单
        if _status == 200 and self.verify_blacklist(_ip):
            # 在黑名单内
            _status = self.error_resp_status
            _resp_msg = copy.deepcopy(self.error_resp_msg)

        if _status == 200:
            # 返回校验成功
            return (True, _status, 'success')
        else:
            # 校验失败
            return (False, _status, _resp_msg)

    #############################
    # 需实现类重载的函数
    #############################

    def _format_auth_resp(self, code: Any, err_msg: str) -> Any:
        """
        格式化校验结果返回值

        @param {Any} code - 错误码
        @param {str} err_msg - 失败描述

        @returns {Any} - 格式化后的返回值
        """
        raise NotImplementedError()

    def _get_ip_from_request(self, *args, **kwargs) -> str:
        """
        从请求信息中获取ip地址

        @returns {str} - 返回ip地址
        """
        raise NotImplementedError()


class AppKeyAuth(AuthBaseFw):
    """
    AppKey模式验证模块
    整体流程: 调用方对请求报文签名 -> 服务方验证请求签名 -> 服务方处理并对返回报文签名 -> 调用方验证返回报文签名
    详细说明如下:
        1. 服务端生成APP信息, 线下提供给商户
            AppId: 商户id
            AppKey: 公匙(相当于账号)
            AppSecret: 私匙(相当于密码)
        2. 客户端对要发送的数据进行签名, 算法如下:
        (1) 客户端生成 nonce_str 随机字符串, 例如: 'ibuaiVcKdpRxkhJA'
        (2) 设要发送的数据为集合M, 将所有非空参数值的参数按照参数名ASCII码从小到大排序(字典序),
        使用URL键值对的格式(即key1=value1&key2=value2…)拼接成字符串stringA, 例如:
            stringA="body=test&device_info=1000&mch_id=10000100"
        (3) 拼接API密钥
            # 拼接app_id、app_key、app_secret、nonce_str、timestamp进入签名字符串
            stringSignTemp=stringA+"&app_id=1333&app_key=123456&app_secret=192006250b4c09247ec02edce69f6a2d&nonce_str=xx&timestamp=xx"
            # 如果选择MD5签名方式, 处理及得到结果如下
            sign=MD5(stringSignTemp).toUpperCase()="9A0A8659F005D6984697E2CA0A9CF3B7"
            # 如果选择HMAC-SHA256算法签名方式, 处理及得到结果如下
            # 注意: 部分语言的hmac方法生成结果二进制结果, 需要调对应函数转化为十六进制字符串。
            sign=hash_hmac("sha256",stringSignTemp,AppSecret).toUpperCase()="6A9AE1657590FD6257D693A078E1C3E4BB6BA4DC30B23E0EE2496E54170DACD6"
        (4) 将sign放入要发送的数据集合中, 客户端调用api接口
        (5) 服务器端同样做相应的认证检查
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        AppKey模式验证模块

        @param {fuction} get_secret_fun - 取 (app_key, app_secret) 密钥对的函数, 默认使用当前类的自有AppKey管理工具函数
            fun(app_id:str) -> tuple
        @param {bool} sign_resp=False - 是否对返回的报文进行签名
        @param {int} sign_error_resp_status=403 - 签名验证失败返回状态码
        @param {str|dict} sign_error_resp_msg={'status': '13007', 'msg':'签名检查失败'} - 签名验证失败返回的信息
        @param {float} timestamp_expired_time=300.0 - 允许服务器时间差异时长, 单位为秒, 默认5分钟
        @param {int} timestamp_error_resp_status=403 - timestamp已过期时返回状态码
        @param {str|dict} timestamp_error_resp_msg={'status': '13008', 'msg':'时间戳已过期'} - timestamp已过期返回的信息
        @param {int} nonce_len=8 - nonce字符串的长度
        @param {str} timestamp_fmt='%Y%m%d%H%M%S' - timestamp的格式
        @param {str} encoding='utf-8' - 对中文内容的转换编码
        @param {str} algorithm='MD5' - 使用的签名算法名, 支持算法如下
            MD5
            HMAC-SHA256
        @param {dict} algorithm_extend=None - 扩展算法支持, key为algorithm名, value为扩展的算法函数
            扩展函数定义如下: fun(value:str, key:str) -> str
        """
        self.para = kwargs
        self.get_secret_fun = self.para.get('get_secret_fun', self.apk_get_secret_fun)
        self.sign_resp = self.para.get('sign_resp', False)
        self.interface_id_name = self.para.get('interface_id_name', '')
        self.sign_error_resp_status = self.para.get('sign_error_resp_status', 403)
        self.sign_error_resp_msg = self.para.get(
            'sign_error_resp_msg', {'status': '13007', 'msg': '签名检查失败'}
        )
        self.timestamp_expired_time = self.para.get('timestamp_expired_time', 300.0)
        self.timestamp_error_resp_status = self.para.get('timestamp_error_resp_status', 403)
        self.timestamp_error_resp_msg = self.para.get(
            'timestamp_error_resp_msg', {'status': '13008', 'msg': '时间戳已过期'}
        )
        self.timestamp_fmt = self.para.get('timestamp_fmt', '%Y%m%d%H%M%S')
        self.encoding = self.para.get('encoding', 'utf-8')

        # 算法扩展支持
        self.algorithm_mapping = {
            'MD5': HCrypto.md5,
            'HMAC-SHA256': HCrypto.hmac_sha256
        }
        self.algorithm_mapping.update(self.para.get('algorithm_extend', {}))
        self.algorithm = self.para.get('algorithm', 'MD5')

        # 简易的AppKey管理台, 内存字典管理, key为app_id, value为(app_key, app_secret) 键值对
        self._app_key_manager = dict()

    #############################
    # 签名工具
    #############################
    def get_signature(self, msg: dict, app_key: str, app_secret: str, algorithm: str = None) -> str:
        """
        对消息字典进行签名

        @param {dict} msg - 要签名的字典
        @param {str} app_key - 商户持有的app_key(相当于公钥)
        @param {str} app_secret - 商户持有的AppSecret私匙(相当于密码)
        @param {str} algorithm=None - 使用的签名算法名, 如果不传使用初始化类的指定算法, 支持算法如下
            MD5
            HMAC-SHA256
        @returns {str} - 返回签名验证字符串
        """
        # 必须要有的参数
        _app_id = msg['app_id']
        _nonce_str = msg['nonce_str']
        _timestamp = msg['timestamp']

        # 参数清单组合, 按参数名排序, 去掉非空值, URL键值对方式组合
        _para_list = list(msg.keys())
        _para_list.sort()
        _str_sign_temp = ''
        for _para in _para_list:
            if _para not in ('app_id', 'nonce_str', 'timestamp', 'sign') and msg[_para] not in (None, ''):
                _value = msg[_para]
                if type(_value) != str:
                    _value = json.dumps(_value, ensure_ascii=False, sort_keys=True)

                _str_sign_temp = '%s%s=%s&' % (
                    _str_sign_temp, _para, _value
                )

        # 增加app_id、app_key、app_secret, nonce_str、timestamp到键值对中
        _str_sign_temp = '%sapp_id=%s&app_key=%s&app_secret=%s&nonce_str=%s&timestamp=%s' % (
            _str_sign_temp, _app_id, app_key, app_secret, _nonce_str, _timestamp
        )

        # 进行加密处理并返回签名串
        _algorithm = self.algorithm if algorithm is None else algorithm
        return self.algorithm_mapping[_algorithm](
            _str_sign_temp, key=app_secret, encoding=self.encoding
        )

    def sign(self, msg: dict) -> dict:
        """
        对报文消息字典进行签名

        @param {dict} msg - 要签名的报文字典

        @returns {dict} - 签名后的报文字典
        """
        _app_id = msg['app_id']
        msg['nonce_str'] = HCrypto.generate_nonce(self.para.get('nonce_len', 8))  # 随机字符串
        msg['timestamp'] = datetime.datetime.now().strftime(self.timestamp_fmt)  # 时间戳
        _sign_type = msg.get('sign_type', self.algorithm)  # 签名类型, 如果有送值代表指定算法
        _app_key, _app_secret = self.get_secret_fun(_app_id)  # 通过指定的算法获取
        msg['sign'] = self.get_signature(msg, _app_key, _app_secret, algorithm=_sign_type)

        return msg

    def verify_sign(self, msg: dict) -> bool:
        """
        验证报文签名是否准确

        @param {dict} msg - 要验证的报文字典

        @returns {bool} - 报文验证结果
        """
        try:
            _app_id = msg['app_id']
            _sign_type = msg.get('sign_type', self.algorithm)  # 签名类型, 如果有送值代表指定算法
            _app_key, _app_secret = self.get_secret_fun(_app_id)  # 通过指定的算法获取
            _sign = self.get_signature(msg, _app_key, _app_secret, algorithm=_sign_type)
            return _sign == msg['sign']
        except:
            return False

    def verify_timestamp(self, msg: dict) -> bool:
        """
        验证时间戳是否已过期

        @param {dict} msg - 要验证的报文字典

        @returns {bool} - 验证结果
        """
        try:
            _timestamp = datetime.datetime.strptime(msg['timestamp'], self.timestamp_fmt)
            if abs((datetime.datetime.now() - _timestamp).total_seconds()) > self.timestamp_expired_time:
                return False
            return True
        except:
            return False

    #############################
    # 简易AppKey管理台工具
    #############################
    def apk_get_secret_fun(self, app_id: str) -> tuple:
        """
        自有AppKey管理工具(无安全控制)的取密钥对函数

        @param {str} app_id - 要获取的app_id

        @returns {tuple} - (app_key, app_secret) 密钥对
        """
        return self._app_key_manager[app_id]

    def apk_update_secret(self, app_id: str, key_pair: tuple):
        """
        自有AppKey管理工具的密钥对更新

        @param {str} app_id - 要更新的app_id
        @param {tuple} key_pair - (app_key, app_secret) 密钥对
        """
        self._app_key_manager[app_id] = key_pair

    def apk_generate_key_pair(self, app_id: str) -> tuple:
        """
        自有AppKey管理工具的生成新密钥对函数(同时可以加入管理工具)

        @param {str} app_id - 要获取的app_id

        @returns {tuple} - (app_key, app_secret) 密钥对
        """
        # 随机生成字符串, app_key 8位, app_secret 32位
        _app_key = StringTool.get_random_str(random_length=8)
        _app_secret = StringTool.get_random_str(random_length=32)
        self._app_key_manager[app_id] = (_app_key, _app_secret)

        return (_app_key, _app_secret)

    #############################
    # 重载基础框架的函数
    #############################
    async def auth_required_call(self, f, *args, **kwargs):
        """
        直接执行的鉴权修饰符函数
        注: 进行了重载, 增加app_id的获取并送入_format_last_resp函数

        @param {function} f - 要执行的函数
        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {Any} - 返回响应信息(如果执行成功返回函数返回信息, 如果执行失败返回验证失败信息)
        """
        # 执行校验操作
        _result = await AsyncTools.async_run_coroutine(self._auth_call(*args, **kwargs))
        _is_auth_result = False
        if not _result[0]:
            # 校验失败, 获取校验失败的返回值
            _ret = await AsyncTools.async_run_coroutine(
                self._format_auth_resp(_result[1], _result[2])
            )
            _is_auth_result = True
        else:
            # 校验通过, 执行函数
            _ret = await AsyncTools.async_run_coroutine(f(*args, **kwargs))

        # 格式化响应对象并返回处理结果
        _json = self._get_json_from_request(*args, **kwargs)
        _last_ret = await AsyncTools.async_run_coroutine(
            self._format_last_resp(_ret, _is_auth_result, _json['app_id'])
        )
        return _last_ret

    async def _auth_call(self, *args, **kwargs) -> tuple:
        """
        真正的校验处理函数

        @param {args} - 执行函数的固定入参
        @param {kwargs} - 执行函数的kv入参

        @returns {tuple} - 返回校验结果数组: (校验是否通过true/false, 错误码, 失败描述)
            错误码定义如下: 200-成功, 其他-失败
        """
        _status = 200
        _json_dict = await AsyncTools.async_run_coroutine(self._get_json_from_request(*args, **kwargs))

        if not self.verify_timestamp(_json_dict):
            # 日期验证失败
            _status = self.timestamp_error_resp_status
            _resp_msg = copy.deepcopy(self.timestamp_error_resp_msg)
        elif not self.verify_sign(_json_dict):
            # 验证失败, 返回标准的错误信息
            _status = self.sign_error_resp_status
            _resp_msg = copy.deepcopy(self.sign_error_resp_msg)

        if _status == 200:
            # 返回校验成功
            return (True, _status, 'success')
        else:
            # 校验失败
            return (False, _status, _resp_msg)

    def _format_auth_resp(self, code: Any, err_msg: str) -> Any:
        """
        格式化校验结果返回值

        @param {Any} code - 错误码
        @param {str} err_msg - 失败描述

        @returns {tuple} - 返回校验结果数组: (错误码, 失败描述)
            错误码定义如下: 200-成功, 其他-失败
        """
        return (code, err_msg)

    #############################
    # 需实现类重载的函数
    #############################

    def _format_last_resp(self, resp: Any, is_auth_result: bool, app_id: str) -> Any:
        """
        格式化最后的响应对象
        注意: 实现类需实现以下的伪代码逻辑
        if self.sign_resp:
            resp_dict = get resp_dict from resp
            put app_id to resp_dict
            resp_dict = self.sign(resp_dict)
            put resp_dict back to resp

        @param {Any} resp - 最后的响应对象
        @param {bool} is_auth_result - 是否服务鉴权所返回的结果
        @param {str} app_id - 送入的app_id

        @returns {Any} - 转换以后的响应对象
        """
        raise NotImplementedError()

    def _get_json_from_request(self, *args, **kwargs) -> dict:
        """
        从请求信息中获取消息json

        @returns {dict} - 返回json字典
        """
        raise NotImplementedError()
