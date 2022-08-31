#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2022 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
proto生成工具模块

@module proto_generate
@file proto_generate.py
"""
import os
import sys
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetCore.utils.run_tool import RunTool
from HiveNetCore.utils.file_tool import FileTool


class ProtoTools(object):
    """
    处理Proto文件的工具类
    """

    #############################
    # 静态工具类
    #############################
    @classmethod
    def generate_python_proto(cls, proto: str, output: str = None, add_hivenet_ref: bool = False,
            python_cmd: str = 'python'):
        """
        生成python的proto适配文件

        @param {str} proto - 原始proto文件
        @param {str} output=None - 要输出的目录, 如果为None代表在原始文件相同目录下
        @param {bool} add_hivenet_ref=False - 是否在pb2_grpc添加HiveNet的引用代码
        @param {str} python_cmd='python' - python的命令, 根据环境传入, 例如修改为python3
        """
        _proto = os.path.abspath(proto)
        if not os.path.exists(_proto):
            raise FileNotFoundError('proto file not found')

        # 输出目录和文件名
        _proto_path, _filename = os.path.split(_proto)
        if output is not None:
            _output = os.path.abspath(output)
        else:
            _output = _proto_path

        if not os.path.exists(_output):
            FileTool.create_dir(_output, exist_ok=True)

        # 将当前目录切换到输出目录中, 执行编译命令
        _cmd = '%s -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. --proto_path="%s" %s' % (
            python_cmd, _proto_path, _filename
        )
        os.chdir(_output)
        _cmd_ret = RunTool.exec_sys_cmd(_cmd)
        if _cmd_ret[0] != 0:
            print(_cmd_ret[1])  # 打印
            raise RuntimeError('execute cmd error: %s' % _cmd)

        if add_hivenet_ref:
            # 修改pb2_grpc文件
            _pb2_name = '%s_pb2' % _filename[0: -6]
            _pb2_grpc_name = '%s_grpc.py' % _pb2_name
            _start_code = [
                'import sys',
                'import os',
                'sys.path.append(os.path.abspath(os.path.join(',
                '    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))',
                ''
            ]

            with open(_pb2_grpc_name, 'r', encoding='utf-8') as _f:
                _new_code_str = '%s\r\n%s' % (
                    '\r\n'.join(_start_code), _f.read().replace(
                        'import %s as %s' % (
                            _pb2_name, _pb2_name.replace('_', '__')
                        ), 'import HiveNetGRpc.proto.%s as %s' % (
                            _pb2_name, _pb2_name.replace('_', '__')
                        )
                    )
                )

            with open(_pb2_grpc_name, 'w', encoding='utf-8') as _f:
                _f.write(_new_code_str)

    @classmethod
    def generate_python_proto_by_path(cls, path: str, output: str = None, add_hivenet_ref: bool = False,
            python_cmd: str = 'python'):
        """
        把目录里的所有proto文件生成python适配文件

        @param {str} path - 要处理的目录
        @param {str} output=None - 要输出的目录, 如果为None代表在原始文件相同目录下
        @param {bool} add_hivenet_ref=False - 是否在pb2_grpc添加HiveNet的引用代码
        @param {str} python_cmd='python' - python的命令, 根据环境传入, 例如修改为python3
        """
        _file_list = FileTool.get_filelist(path=path, regex_str=r'.*\.proto$')
        for _file in _file_list:
            cls.generate_python_proto(
                _file, output=output, add_hivenet_ref=add_hivenet_ref, python_cmd=python_cmd
            )


if __name__ == '__main__':
    # 运行命令生成当前目录的适配器
    _path = os.path.abspath(os.path.join(
        os.path.dirname(__file__)
    ))
    ProtoTools.generate_python_proto_by_path(_path, add_hivenet_ref=True)
