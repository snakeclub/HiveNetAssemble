#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Flask适配的服务鉴权模块
@module auth
@file auth.py
"""
import sys
import os
from typing import Any
from flask import request
from flask.wrappers import Response
from HiveNetCore.utils.string_tool import StringTool
from HiveNetWebUtils.auth import IPAuth, AppKeyAuth
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))


class IPAuthFlask(IPAuth):
    """
    IP黑白名单模式验证模块(Flask适配)
    """

    #############################
    # 需实现类重载的函数
    #############################

    def _format_auth_resp(self, code: int, err_msg) -> Response:
        """
        格式化校验结果返回值

        @param {int} code - 错误码
        @param {str|dict} err_msg - 失败描述

        @returns {flask.wrappers.Response} - 格式化后的返回值
        """
        if type(err_msg) == str:
            return err_msg, code
        else:
            return StringTool.json_dumps_hive_net(err_msg, ensure_ascii=False), code

    def _get_ip_from_request(self, *args, **kwargs) -> str:
        """
        从请求信息中获取ip地址

        @returns {str} - 返回ip地址
        """
        return request.remote_addr


class AppKeyAuthFlask(AppKeyAuth):
    """
    AppKey模式验证模块(Flask适配)
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
                if not isinstance(_err_msg, dict):
                    _err_msg = {'err_msg': _err_msg}
                _err_msg['app_id'] = app_id
                _err_msg = self.sign(_err_msg)

            # 转为标准模式返回
            return StringTool.json_dumps_hive_net(_err_msg, ensure_ascii=False), _status
        else:
            # 是标准信息的返回
            if self.sign_resp:
                # 需区分不同类型处理
                _headers = {}
                if isinstance(resp, Response):
                    # 正常响应返回对象
                    _status = resp.status
                    _headers = resp.headers
                    _dict = StringTool.json_loads_hive_net.loads(str(resp.response, encoding='utf-8'))
                else:
                    _status = 200
                    if isinstance(resp, (tuple, list)):
                        # 是列表, 第1个是要返回的值, 第2个是http状态码, 第3个是header字典
                        _dict = resp[0]
                        if len(resp) > 1:
                            _status = resp[1]
                        if len(resp) > 2:
                            _headers = resp[2]
                    else:
                        _dict = resp

                    if not isinstance(_dict, dict):
                        _dict = {'msg': _dict}

                # 进行签名处理
                _dict['app_id'] = app_id
                _dict = self.sign(_dict)

                # 返回结果
                return StringTool.json_dumps_hive_net(_dict, ensure_ascii=False), _status, _headers
            else:
                # 不用签名, 直接返回
                return resp

    def _get_json_from_request(self, *args, **kwargs) -> dict:
        """
        从请求信息中获取消息json

        @returns {dict} - 返回json字典
        """
        return request.json
