#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir
)))
from HiveNetCore.utils.import_tool import ImportTool


__MOUDLE__ = 'import_tool_demo'  # 模块名
__DESCRIPT__ = u'动态模块加载示例'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.10.02'  # 发布日期


if __name__ == '__main__':
    # 示例1，导入公共库
    print('datetime库导入状态：%s' % (str(ImportTool.check_module_imported('datetime'))))
    _datetime = ImportTool.import_module('datetime')  # 导入公共库
    # 执行公共库
    print('当前时间为：%s' % (str(_datetime.datetime.now())))
    print('datetime库导入状态：%s' % (str(ImportTool.check_module_imported('datetime'))))

    # 示例2，导入模块
    _generic = ImportTool.import_module('HiveNetCore.generic')
    # 使用模块的对象
    _result = _generic.CResult('00000')
    print('\nCResult: %s' % (str(_result)))

    # 示例3，导入具体对象，并访问该成员属性，或类
    _CResult = ImportTool.import_module('HiveNetCore.generic', import_member='CResult')
    _result1 = ImportTool.get_attr(_CResult, 'CResult')('29999')
    print('\nCResult: %s' % (str(_result1)))
