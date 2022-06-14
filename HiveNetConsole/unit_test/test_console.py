#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetConsole import ConsoleServer


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    _path = os.path.join(
        os.path.dirname(__file__), os.path.pardir, 'HiveNetConsole'
    )
    ConsoleServer.console_main(
        execute_file_path=_path
    )
