#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
GRPC的工具模块

@module tool
@file tool.py
"""
import os
import sys
import grpc
from grpc_health.v1 import health_pb2
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir)))
from HiveNetGRpc.enum import EnumGRpcStatus


#############################
# GRpc的状态映射字典
#############################
ENUM_TO_GRPC_STATUS = {
    EnumGRpcStatus.Unknow: health_pb2.HealthCheckResponse.UNKNOWN,
    EnumGRpcStatus.ServiceUnknown: health_pb2.HealthCheckResponse.SERVICE_UNKNOWN,
    EnumGRpcStatus.Serving: health_pb2.HealthCheckResponse.SERVING,
    EnumGRpcStatus.NotServing: health_pb2.HealthCheckResponse.NOT_SERVING,
    EnumGRpcStatus.NotFound: grpc.StatusCode.NOT_FOUND
}

GRPC_STATUS_TO_ENUM = {
    health_pb2.HealthCheckResponse.UNKNOWN: EnumGRpcStatus.Unknow,
    health_pb2.HealthCheckResponse.SERVICE_UNKNOWN: EnumGRpcStatus.ServiceUnknown,
    health_pb2.HealthCheckResponse.SERVING: EnumGRpcStatus.Serving,
    health_pb2.HealthCheckResponse.NOT_SERVING: EnumGRpcStatus.NotServing,
    grpc.StatusCode.NOT_FOUND: EnumGRpcStatus.NotFound
}


class GRpcTool(object):
    """
    grpc的工具函数
    """
    #############################
    # context上下文信息获取及处理函数
    #############################

    @classmethod
    def metadata_to_dict(cls, context: grpc.ServicerContext) -> dict:
        """
        将grpc上下文中的metadata转换为字典对象

        @param {grpc.ServicerContext} context - grpc上下文对象

        @returns {dict} - metadata转换后的字典对象
        """
        return dict(context.invocation_metadata())

    @classmethod
    def context_info_ip(cls, context: grpc.ServicerContext) -> dict:
        """
        获取grpc上下文中的ip信息

        @param {grpc.ServicerContext} context - grpc上下文对象

        @returns {dict} - 获取到的ip信息
            {
                'client_ip': '',  # 客户端ip
                'client_port': xx,  # 客户端端口
                'server_ip': '',  # 服务端IP
                'server_port': xxx  # 服务端端口
            }
        """
        _peer = str(context.peer()).split(':')
        _server = str(context._rpc_event.call_details.host, 'utf-8').split(':')
        return {
            'client_ip': _peer[1],
            'client_port': int(_peer[2]),
            'server_ip': _server[0],
            'server_port': int(_server[1])
        }
