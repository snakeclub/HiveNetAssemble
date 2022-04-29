#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试xml块
@module test_xml
@file test_xml.py
"""

import os
import sys
import unittest
import lxml.etree as ET
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.xml import EnumXmlObjType, SimpleXml
from HiveNetCore.utils.file_tool import FileTool


__MOUDLE__ = 'test_xml'  # 模块名
__DESCRIPT__ = u'测试xml模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.10.21'  # 发布日期


_TEMP_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), os.path.pardir, 'test_data/temp/simple_xml'
    )
)
if not os.path.exists(_TEMP_DIR):
    FileTool.create_dir(_TEMP_DIR, exist_ok=True)


class TestSimpleXml(unittest.TestCase):
    """
    测试simple_id模块
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        self.file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, 'test_data/simple_xml')
        )

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_xml_gbk(self):
        """
        测试SimpleXml
        """
        print('测试SimpleXml - gbk编码文件')
        _file = os.path.join(self.file_path, 'encode_gbk.xml')
        _pfile = SimpleXml(_file, obj_type=EnumXmlObjType.File, encoding=None,
                           use_chardet=True, remove_blank_text=True)
        _text = _pfile.get_attr('country[1]', 'name', default='None')
        self.assertTrue(_text == '中国',
                        '失败：测试SimpleXml - gbk编码文件 - 获取属性值错误：%s' % _text)
        _text = _pfile.get_value('country[1]/year')
        self.assertTrue(_text == '2008',
                        '失败：测试SimpleXml - gbk编码文件 - 获取值错误：%s' % _text)

        print('测试SimpleXml - 获取xpath')
        _node = _pfile.get_nodes('/data/country[1]/year')[0]
        _xpath = _pfile.get_xpath(_node)
        self.assertTrue(_xpath == '/data/country[1]/year',
                        '失败：测试SimpleXml - 获取xpath - 路径错误：%s' % _xpath)

        print('测试SimpleXml - 设置值')
        _pfile.set_value('country[@name="Singapore"]/year', '设置值-原节点')
        _text = _pfile.get_value('country[@name="Singapore"]/year')
        self.assertTrue(_text == '设置值-原节点',
                        '失败：测试SimpleXml - 测试SimpleXml - 设置值-原节点 - 值错误：%s' % _text)
        _pfile.set_value('new_node/my_node/test', '设置值-新节点')
        _text = _pfile.get_value('new_node/my_node/test')
        self.assertTrue(_text == '设置值-新节点',
                        '失败：测试SimpleXml - 测试SimpleXml - 设置值-新节点 - 值错误：%s' % _text)
        _pfile.set_attr('country[@name="Singapore"]/rank', 'updated', '设置属性值-原节点')
        _text = _pfile.get_attr('country[@name="Singapore"]/rank', 'updated')
        self.assertTrue(_text == '设置属性值-原节点',
                        '失败：测试SimpleXml - 测试SimpleXml - 设置属性值-新节点 - 值错误：%s' % _text)
        _pfile.set_attr('new_node/my_node/test1', 'updated', '设置属性值-新节点')
        _text = _pfile.get_attr('new_node/my_node/test1', 'updated', '设置属性值-新节点')
        self.assertTrue(_text == '设置属性值-新节点',
                        '失败：测试SimpleXml - 测试SimpleXml - 设置属性值-新节点 - 值错误：%s' % _text)

        print('测试SimpleXml - 删除节点')
        _pfile.remove('new_node', hold_tail=True)
        _node = _pfile.get_nodes('new_node')
        self.assertTrue(len(_node) == 0,
                        '失败：测试SimpleXml - 测试SimpleXml - 删除节点 - 删除错误：%d' % len(_node))

        print('测试SimpleXml - 保存文件')
        _file = os.path.join(_TEMP_DIR, 'encode_gbk_temp.xml')
        _pfile.save(file=_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

    def test_xml_namespace(self):
        """
        测试带命名空间的处理
        """
        print('测试命名空间处理')
        print('测试命名空间处理 - 装载文件并访问信息')
        _file = os.path.join(self.file_path, 'with_namespace.xml')
        _pfile = SimpleXml(_file, obj_type=EnumXmlObjType.File, encoding=None,
                           use_chardet=True, remove_blank_text=True)
        ns = {
            'people': 'http://people.example.com',
            'role': 'http://characters.example.com'
        }
        _text = _pfile.get_value('people:actor[1]/people:name', default='None', namespaces=ns)
        self.assertTrue(_text == 'John Cleese - 中文',
                        '失败：测试命名空间处理 - 装载文件并访问信息 - 步骤1获取值错误：%s' % _text)
        _text = _pfile.get_value(
            '/people:actors/people:actor[1]/role:character[1]', default='None', namespaces=ns)
        self.assertTrue(_text == 'Lancelot',
                        '失败：测试命名空间处理 - 装载文件并访问信息 - 步骤2获取值错误：%s' % _text)

        print('测试命名空间处理 - 新增节点')
        _pfile.set_value('people:test/role:myname', '新值', namespaces=ns)
        _text = _pfile.get_value('people:test/role:myname',
                                 default='None', namespaces=ns)
        self.assertTrue(_text == '新值',
                        '失败：测试命名空间处理 - 新增节点 - 值错误：%s' % _text)

    def test_xml_to_dict(self):
        """
        测试xml转换为字典的情况
        """
        print('测试SimpleXml - to_dict')
        _file = os.path.join(self.file_path, 'to_dict.xml')
        _pfile = SimpleXml(_file, obj_type=EnumXmlObjType.File, encoding=None,
                           use_chardet=True, remove_blank_text=True)
        _item_dict_xpaths = {
            '/data/country[2]/list': None
        }
        _dict = _pfile.to_dict(item_dict_xpaths=_item_dict_xpaths)
        print(_dict)
        self.assertTrue(_dict['data'][0][0] == 2,
                        '失败：测试SimpleXml - to_dict - 检查1：%d' % _dict['data'][0][0])
        self.assertTrue(_dict['data'][0][3][3] is True,
                        '失败：测试SimpleXml - to_dict - 检查2：%s' % str(_dict['data'][0][3][3]))
        self.assertTrue(_dict['data'][1]['list'][0]['b1'] == 'b1',
                        '失败：测试SimpleXml - to_dict - 检查3：%s' % str(_dict['data'][1]['list'][0]['b1']))


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
    # import re
    # pattern = re.compile(r'{[\S\s]+?}')
    # str = 'abc/{http://fdfd.com.cn}bcd/{http://fdfdfd.33}cde/{http://fdfd.com.cn}33/fdfd/sss'
    # list = pattern.findall(str)
    # print(list)
    # print(pattern.sub('X', str))

    # pattern = re.compile(r'(({[\S\s]+?}){0,}[^/]+)')
    # list = pattern.findall(str)
    # print(list)
