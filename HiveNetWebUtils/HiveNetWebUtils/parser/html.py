#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
html代码解析器

@module html_parser
@file html_parser.py
"""

import sys
import os
import lxml.etree as ET
from HiveNetCore.xml_hivenet import SimpleXml, EnumXmlObjType
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
)


__MOUDLE__ = 'html'  # 模块名
__DESCRIPT__ = u'html代码解析器'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2021.07.15'  # 发布日期


class HtmlElement(object):
    """
    自己封装的Html元素, 方法与 selenium 的 WebElement 一致
    """

    def __init__(self, elemnet: ET._Element):
        """
        Html元素

        @param {lxml.etree.Element} elemnet - lxml获取到的元素
        """
        self.element = elemnet

    #############################
    # 属性
    #############################
    @property
    def id(self):
        """
        获取元素的id
        @property {str} - id, 不存在返回None
        """
        return self.element.get('id', None)

    @property
    def tag_name(self):
        """
        获取元素标签名

        @property {str}
        """
        return self.element.tag

    @property
    def text(self):
        """
        获取元素文本

        @property {str}
        """
        return self.element.text

    @property
    def parent(self):
        """
        获取元素的父元素

        @property {HtmlElement} - 如果找不到返回None
        """
        _parent = self.element.getparent()
        if _parent is None:
            return None
        else:
            return HtmlElement(_parent)

    @property
    def position(self) -> int:
        """
        获取当前节点在父节点下的位置

        @property {int} - 返回位置, 如果是顶层的情况返回None
        """
        _parent = self.parent
        if _parent is None:
            return None
        else:
            return _parent.element.index(self.element)

    #############################
    # 公共函数
    #############################
    def get_property(self, name: str):
        """
        获取属性值

        @param {str} name - 获取对象属性值

        @returns {Any} - 返回属性值, 不存在返回None
        """
        return self.element.get(name, None)

    def get_attribute(self, name: str):
        """
        获取属性值

        @param {str} name - 获取对象属性值

        @returns {Any} - 返回属性值, 不存在返回None
        """
        return self.element.get(name, None)

    def is_selected(self):
        """
        获取元素是否被选中
        注: checkbox或radio

        @returns {bool} - 是否被选中
        """
        if self.element.tag.lower() in ('radio', 'checkbox'):
            return self.element.get('selected', None) is not None
        else:
            return self.element.get('selected', default='false') == 'true'

    def is_enabled(self):
        """
        判断元素是否启用

        @returns {bool} - 是否启用
        """
        return self.element.get('enabled', default='true') == 'true'

    def is_same_with(self, el, with_path: bool = True) -> bool:
        """
        比较当前节点和另一个节点是否同一个

        @param {HtmlElement} element - 要比较的元素
        @param {bool} with_path=True - 是否比较路径

        @returns {bool} - 比较结果
        """
        _a = self.element
        _b = el.element
        # 比较属性
        for attrib in _a.attrib:
            if _a.get(attrib) != _b.get(attrib):
                return False

        # 比较其他值
        if _a.text != _b.text:
            return False
        if _a.tag != _b.tag:
            return False
        if _a.prefix != _b.prefix:
            return False
        if _a.tail != _b.tail:
            return False
        if _a.values() != _b.values():  # may be redundant to the attrib matching
            return False
        if _a.keys() != _b.keys():  # may also be redundant to the attrib matching
            return False

        # 比较路径
        _pa = self
        _pb = el
        while with_path:
            # 比较位置
            _pos_a = _pa.position
            _pos_b = _pb.position
            if _pos_a is None and _pos_b is None:
                # 已经是顶层
                break

            if _pos_a != _pos_b:
                return False

            # 比较父节点, 只需比较tag
            _pa = _pa.parent
            _pb = _pb.parent
            if _pa.tag_name != _pb.tag_name:
                return False

        return True


class HtmlParser(object):
    """
    Html解析器
    基于lxml实现的html文档的解析, 元素查找方式与 WebDriver 相似, 以便解析功能的兼容
    """

    def __init__(self, html: str, use_xpath2=False):
        """
        html解析器

        @param {str} html - 要解析的html代码
        @param {bool} use_xpath2=False - 是否使用xpath2.0, 默认为False
        """
        self.html_doc = SimpleXml(
            html, obj_type=EnumXmlObjType.String, parser='html', use_xpath2=use_xpath2
        )

    #############################
    # 元素查找
    #############################
    def find_elements(self, steps: list, parent: HtmlElement = None) -> list:
        """
        按步骤逐级查询对象

        @param {list} steps - 要查询的步骤列表, 每一个步骤为一个操作列表, 第0个为操作类型, 后面为操作参数
            [
                ['pos': 0],  # 获取当前清单中指定位置的元素
                ['children'],  # 获取当前清单元素中的所有子元素
                ['id', 'myId'],  # 通过id获取元素
                ['xpath', '//img[@id="dracga" and @style]'],  # 通过xpaht获取元素
                ['name', 'myName'],  # 通过元素的name属性获取
                ['tag_name', 'img'],  # 通过元素的标签名获取
                ['class_name', 'styleClass'],  # 通过元素的class名获取
                ['css_selector', '#kw'],  # 通过css选择器方式获取, id用#kw, class用.s_ipt, 与css的简写方式相同
                ['link_text', 'hao123'],  # 通过超文本链接上的文字信息来定位元素
                ['partial_link_text', 'hao']  # 通过超文本连接上的文字的一部分关键字信息来定位元素
            ]
        @param {HtmlElement} parent=None - 开始的父节点, 如果不传代表重新开始

        @returns {list} - 返回查找到的对象列表
            注: 对象类型为 HtmlElement
        """
        # 转换为底层类型
        _parent = None
        if parent is not None:
            _parent = parent.element

        # 查找第一个步骤
        _elements = self._find_elements_step(steps[0], parent=_parent)

        # 循环处理后面每个步骤(从第2个开始)
        for _i in range(1, len(steps)):
            if len(_elements) == 0:
                # 没有找到任何元素, 直接退出循环
                break

            # 执行子元素的查找处理
            _step = steps[_i]
            _op = _step[0]
            _new_elements = list()
            if _op == 'pos':
                # 获取当前列表中指定位置的元素
                _new_elements.append(_elements[_step[1]])
            else:
                # 遍历每个元素进行查找
                for _element in _elements:
                    _new_elements.extend(
                        self._find_elements_step(_step, parent=_element)
                    )

            # 更新清单
            _elements = _new_elements

        # 转换为标准类型并返回结果
        _trans_list = list()
        for _element in _elements:
            _trans_list.append(HtmlElement(_element))

        return _trans_list

    #############################
    # 内部函数
    #############################
    def _find_elements_step(self, step: list, parent: ET._Element = None) -> list:
        """
        单步查找元素

        @param {list} step - 执行步骤参数, 参数数组中的第0个是查找指令, 其他数组对象是查找参数
            ['children']  # 获取当前清单元素中的所有子元素
            ['id', 'myId']  # 通过id获取元素
            ['xpath', '//img[@id="dracga" and @style]']  # 通过xpaht获取元素
            ['name', 'myName']  # 通过元素的name属性获取
            ['tag_name', 'img']  # 通过元素的标签名获取
            ['class_name', 'styleClass']  # 通过元素的class名获取
            ['css_selector', '#kw']  # 通过css选择器方式获取, id用#kw, class用.s_ipt, 与css的简写方式相同
                注: 暂不支持
            ['link_text', 'hao123']  # 通过超文本链接上的文字信息来定位元素
            ['partial_link_text', 'hao']  # 通过超文本连接上的文字的一部分关键字信息来定位元素
        @param {lxml.etree._Element} parent=None - 父节点, 如果不传代表全局搜索

        @returns {list} - 返回查找到的对象列表
            注: 对象类型为 lxml.etree._Element
        """
        # 处理查找操作
        _elements = list()
        _op = step[0]  # 查找指令
        if _op == 'children':
            # 获取所有子元素
            _elements = self._find_elements_by_xpath('.//*', parent=parent)
        elif _op == 'id':
            # 通过id查找
            _elements = self._find_elements_by_xpath('.//*[@id="%s"]' % step[1], parent=parent)
        elif _op == 'xpath':
            _elements = self._find_elements_by_xpath(step[1], parent=parent)
        elif _op == 'name':
            _elements = self._find_elements_by_xpath('.//*[@name="%s"]' % step[1], parent=parent)
        elif _op == 'tag_name':
            _elements = self._find_elements_by_xpath('.//%s' % step[1], parent=parent)
        elif _op == 'class_name':
            _elements = self._find_elements_by_xpath(
                './/*[@class="{0}" or starts-with(@class, "{0} ") or contains(@class, " {0} ") or ends-with(@class, " {0}")]'.format(step[1]), parent=parent
            )
        elif _op == 'link_text':
            _elements = self._find_elements_by_xpath(
                './/*[@href and text()="%s"]' % step[1], parent=parent
            )
        elif _op == 'partial_link_text':
            _elements = self._find_elements_by_xpath(
                './/*[@href and contains(string(), "%s")]' % step[1], parent=parent
            )
        elif _op == 'css_selector':
            if parent is None:
                parent = self.html_doc.root
            _elements = parent.cssselect(step[1])
        else:
            # 没有匹配到类型
            raise KeyError('not support find elements operator [%s]' % _op)

        return _elements

    def _find_elements_by_xpath(self, xpath: str, parent: ET._Element = None) -> list:
        """
        通过XPath获取元素

        @param {str} xpath - xpath字符串

        @param {lxml.etree.Element} parent=None - 父节点

        @returns {list} - 返回查找到的对象列表
            注: 对象类型为 lxml.etree.Element
        """
        if parent is None:
            # 全局查找
            return self.html_doc.get_nodes(xpath)
        else:
            # 查找子节点
            return self.html_doc.get_childnodes_on_node(parent, xpath)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
