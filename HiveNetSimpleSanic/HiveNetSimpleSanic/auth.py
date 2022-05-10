#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Sanic适配的服务鉴权模块

@module auth
@file auth.py
"""
import json
import sys
import os
from typing import Any
from sanic.request import Request
from sanic.response import HTTPResponse, json as sanic_json, text as sanic_text
from HiveNetWebUtils.auth import IPAuth, AppKeyAuth
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


class IPAuthSanic(IPAuth):
    """
    IP黑白名单模式验证模块(Sanic适配)
    """

    #############################
    # 需实现类重载的函数
    #############################

    def _format_auth_resp(self, code: int, err_msg) -> HTTPResponse:
        """
        格式化校验结果返回值

        @param {int} code - 错误码
        @param {str|dict} err_msg - 失败描述

        @returns {sanic.response.HTTPResponse} - 格式化后的返回值
        """
        if type(err_msg) == str:
            return sanic_text(err_msg, status=code)
        else:
            return sanic_json(err_msg, status=code)

    def _get_ip_from_request(self, *args, **kwargs) -> str:
        """
        从请求信息中获取ip地址

        @returns {str} - 返回ip地址
        """
        _request = args[0]  # 请求对象为第一个入参
        if type(_request) != Request:
            _request = args[1]

        return _request.ip


class AppKeyAuthSanic(AppKeyAuth):
    """
    AppKey模式验证模块(Sanic适配)
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
        if is_auth_result:
            # 是鉴权不通过的情况
            _status, _err_msg = resp
            if self.sign_resp:
                if type(_err_msg) != dict:
                    _err_msg = {'err_msg': _err_msg}
                _err_msg['app_id'] = app_id
                _err_msg = self.sign(_err_msg)

            # 转为标准模式返回
            return sanic_json(_err_msg, status=_status)
        else:
            # 是标准信息的返回
            if self.sign_resp:
                # 需区分不同类型处理
                if isinstance(resp, HTTPResponse):
                    # 正常响应返回对象
                    _status = resp.status
                    _headers = resp.headers
                    _dict = json.loads(str(resp.body, encoding='utf-8'))
                else:
                    _status = 200
                    if isinstance(resp, (tuple, list)):
                        # 是列表, 第1个是要返回的值, 第2个是http状态码
                        _dict = resp[0]
                        if len(resp) > 1:
                            _status = resp[1]
                    else:
                        _dict = resp

                    if not isinstance(_dict, dict):
                        _dict = {'msg': _dict}

                # 进行签名处理
                _dict['app_id'] = app_id
                _dict = self.sign(_dict)

                # 返回结果
                return sanic_json(_dict, status=_status, headers=_headers)
            else:
                # 不用签名, 直接返回
                return resp

    def _get_json_from_request(self, *args, **kwargs) -> dict:
        """
        从请求信息中获取消息json

        @returns {dict} - 返回json字典
        """
        _request = args[0]  # 请求对象为第一个入参
        if type(_request) != Request:
            _request = args[1]

        return _request.json
