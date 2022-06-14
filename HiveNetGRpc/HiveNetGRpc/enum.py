#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""
grpc服务和客户端涉及的通用枚举对象

@module enum
@file enum.py
"""
from enum import Enum


class EnumCallMode(Enum):
    """
    调用模式
    @enum {string}
    """
    Simple = 'Simple'  # 简单模式
    ClientSideStream = 'ClientSideStream'  # 客户端流式
    ServerSideStream = 'ServerSideStream'  # 服务端流式
    BidirectionalStream = 'BidirectionalStream'  # 双向数据流模式


class EnumGRpcStatus(Enum):
    """
    GRpc服务检测状态
    @enum {string}
    """
    Unknow = 'unknow'  # 未知
    ServiceUnknown = 'ServiceUnknown'  # 服务对象未知
    NotServing = 'NotServing'  # 未提供服务
    Serving = 'Serving'  # 正常服务
    NotFound = 'NotFound'  # 服务不存在