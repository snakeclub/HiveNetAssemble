#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from six import string_types
from sphinx.ext.napoleon.docstring import NumpyDocstring


class SnakerPyDocstring(NumpyDocstring):
    """Convert SnakerPy style docstrings to reStructuredText.

    Parameters
    ----------
    docstring : :obj:`str` or :obj:`list` of :obj:`str`
        The docstring to parse, given either as a string or split into
        individual lines.
    config: :obj:`sphinx.ext.napoleon_snakerpy.Config` or :obj:`sphinx.config.Config`
        The configuration settings to use. If not given, defaults to the
        config object on `app`; or if `app` is not given defaults to the
        a new :class:`sphinx.ext.napoleon_snakerpy.Config` object.


    Other Parameters
    ----------------
    app : :class:`sphinx.application.Sphinx`, optional
        Application object representing the Sphinx process.
    what : :obj:`str`, optional
        A string specifying the type of the object to which the docstring
        belongs. Valid values: "module", "class", "exception", "function",
        "method", "attribute".
    name : :obj:`str`, optional
        The fully qualified name of the object.
    obj : module, class, exception, function, method, or attribute
        The object to which the docstring belongs.
    options : :class:`sphinx.ext.autodoc.Options`, optional
        The options given to the directive: an object with attributes
        inherited_members, undoc_members, show_inheritance and noindex that
        are True if the flag option of same name was given to the auto
        directive.


    Example
    -------
    >>> from sphinx.ext.napoleon import Config
    >>> config = Config(napoleon_use_param=True, napoleon_use_rtype=True)
    >>> docstring = '''One line summary.
    ...
    ... Extended description.
    ...
    ... Parameters
    ... ----------
    ... arg1 : int
    ...     Description of `arg1`
    ... arg2 : str
    ...     Description of `arg2`
    ... Returns
    ... -------
    ... str
    ...     Description of return value.
    ... '''
    >>> print(NumpyDocstring(docstring, config))
    One line summary.
    <BLANKLINE>
    Extended description.
    <BLANKLINE>
    :param arg1: Description of `arg1`
    :type arg1: int
    :param arg2: Description of `arg2`
    :type arg2: str
    <BLANKLINE>
    :returns: Description of return value.
    :rtype: str
    <BLANKLINE>

    Methods
    -------
    __str__()
        Return the parsed docstring in reStructuredText format.

        Returns
        -------
        str
            UTF-8 encoded version of the docstring.

    __unicode__()
        Return the parsed docstring in reStructuredText format.

        Returns
        -------
        unicode
            Unicode version of the docstring.

    lines()
        Return the parsed lines of the docstring in reStructuredText format.

        Returns
        -------
        list(str)
            The lines of the docstring in a list.

    """
    def __init__(self, docstring, config=None, app=None, what='', name='',
                 obj=None, options=None):
        # type: (Union[unicode, List[unicode]], SphinxConfig, Sphinx, unicode, unicode, Any, Any) -> None  # NOQA
        # 直接将docstring转换为NumPy格式，然后直接引用父对象初始化即可
        self._what = what
        # print('----------%s %s--------' % (what, name))
        # print('"""' + str(docstring) + '"""')
        # print('-----To-----')
        _docstring = self._snakerpy_to_numpy(docstring)
        # print('"""' + str(_docstring) + '"""')
        # print('-----------------------')
        super(SnakerPyDocstring, self).__init__(_docstring, config, app, what,
                                             name, obj, options)

    def _snakerpy_to_numpy(self, docstring):
        """将snakerpy格式转换为numpy格式

        """
        _snakerpy_dict = self._structured_snakerpy(docstring)
        _docstring = ''
        if 'ignore' in _snakerpy_dict.keys():
            # 有忽略注释的标签，不处理docstring
            return _docstring

        # summary
        _docstring += self._get_numpy_summary(_snakerpy_dict)

        if self._what == 'class':
            # 类
            _docstring += self._get_numpy_param(_snakerpy_dict)
            _docstring += self._get_numpy_throws(_snakerpy_dict)
            _docstring += self._get_numpy_function(_snakerpy_dict)
        elif self._what == 'module':
            # 模块，不需要特别处理
            pass
        elif self._what == 'method':
            # 函数
            _docstring += self._get_numpy_param(_snakerpy_dict)
            _docstring += self._get_numpy_returns(_snakerpy_dict)
            _docstring += self._get_numpy_throws(_snakerpy_dict)
        elif self._what == 'object':
            # 对象，不需要特别处理
            pass
        else:
            # 其他类型，直接取值处理
            return docstring

        _docstring += self._get_numpy_see(_snakerpy_dict)
        _docstring += self._get_numpy_tutorial(_snakerpy_dict)
        _docstring += self._get_numpy_example(_snakerpy_dict)

        # 返回转换后的结果
        _docstring += '\r\n'
        return _docstring

    def _structured_snakerpy(self, docstring):
        """Convert SnakerPy style docstrings to dict

        Parameters
        ----------
        docstring : :obj:`str` or :obj:`list` of :obj:`str`
            The docstring to parse, given either as a string or split into
            individual lines.

        """
        # 转为行清单，逐行处理
        if isinstance(docstring, string_types):
            docstring = docstring.splitlines()

        _dict = {
            'summary': '',
            'desc': '',
            'param': [],
            'returns': [],
            'throws': [],
            'example': [],
            'see': [],
            'tutorial': [],
            'function': []
        }
        _is_summary = True
        _line_num = 0
        _last_key = ''  # 描述接上一个对象的key
        _last_index = 0  # 描述接上一个对象对应list的位置
        for _line in docstring:
            if _line_num == 0:
                if _line == '':
                    # 第1行为空行，当作第2行为开始
                    continue
                else:
                    _dict['summary'] = _line
                    _line_num = 1
                    continue

            if _is_summary:
                if _line != '' and _line[0] != '@':
                    if _dict['desc'] == '':
                        _dict['desc'] = _line
                    else:
                        _dict['desc'] += '\r\n' + _line
                    continue
                else:
                    # 遇到空行，描述部分完结
                    _is_summary = False
                    continue

            if _line == '':
                # 如果遇到空行，跳过不处理
                continue

            if _line[0] == '@':
                # 是新的对象，与上一个没有关系
                _last_key = ''
                _last_index = 0

                _items = self._split_content(_line)
                _last_key = _items[0][1:]
                if _last_key not in _dict.keys():
                    _dict[_last_key] = []

                if _last_key in ['param', 'typedef']:
                    # @param {type} <paraname> - <descript>
                    _dict[_last_key].append(self._get_param_like_info(_last_key, _items[1]))
                elif _last_key in ['returns', 'throws', 'function']:
                    _dict[_last_key].append(self._get_returns_like_info(_last_key, _items[1]))
                else:
                    # 只有两个信息
                    _dict[_last_key].append(self._get_default_info(_last_key, _items[1]))

                _last_index = len(_dict[_last_key]) - 1
            elif _last_key != '':
                # 接入上一个对象的内容，需通过2个回车换行实现真正展示的换行
                if _last_key == 'example' and _line[0: 4] == '    ':
                    # 要去掉前4个空格
                    _dict[_last_key][_last_index][1] += '\r\n\r\n' + _line[4:]
                else:
                    _dict[_last_key][_last_index][1] += '\r\n\r\n' + _line

        # 返回结构化后的字典
        return _dict

    def _split_content(self, line, split_str=' '):
        """将注释行切分为关键字和内容

        @example
            @param {type} <paraname> - <descript>
            转为
            ['@param', '{type} <paraname> - <descript>']
        """
        _list = ['', '']
        _index = line.find(split_str)
        if _index >= 0:
            _list[0] = line[0: _index]
            _list[1] = line[_index + len(split_str):].strip()
        else:
            _list[0] = line
        return _list

    def _get_param_like_info(self, key, content):
        """获取@param类型的值

        @example
            @param {type} <paraname=default> - <descript>
            key 为 param
            content 为 {type} <paraname=default> - <descript>
            转为
            [['param', 'type', 'paraname', 'default'], 'descript']

        """
        _list = [
            [key, '', '', ''],
            ''
        ]
        # 解析content
        _temp = self._split_content(content)
        _list[0][1] = _temp[0].strip().replace('{', '').replace('}', '')
        if _temp[1] != '':
            _temp = self._split_content(_temp[1].strip(), split_str=' - ')
            if _temp[1] != '':
                _list[1] = _temp[1].strip()  # descript
            # 默认值
            _temp = self._split_content(_temp[0], split_str='=')
            _list[0][2] = _temp[0].strip()
            _list[0][3] = _temp[1].strip()

        # 返回结果
        return _list

    def _get_returns_like_info(self, key, content):
        """获取@returns类型的值

        @example
            @returns {type} - <descript>
            key 为 returns
            content 为 {type} - <descript>
            转为
            [['returns', 'type', '', ''], 'descript']

        """
        _list = [
            [key, '', '', ''],
            ''
        ]
        # 解析content
        _temp = self._split_content(content, split_str=' - ')
        _list[0][1] = _temp[0].strip().replace('{', '').replace('}', '')
        if _temp[1] != '':
            _list[1] = _temp[1].strip()
        # 返回结果
        return _list

    def _get_default_info(self, key, content):
        """获取默认类型的值

        @example
            @example <descript>
            key 为 example
            content 为 <descript>
            转为
            [['example', '', '', ''], 'descript']

        """
        _list = [
            [key, '', '', ''],
            content
        ]
        return _list

    def _get_numpy_summary(self, snakerpy_dict):
        """获取numpy的描述内容"""
        _str = snakerpy_dict['summary'] + '\r\n'
        _add_desc = ''  # 用于补充一些numpy不支持的标签信息
        if 'api' in snakerpy_dict.keys():
            # 标识api接口
            _add_desc += self._what + (' is api : %s' % (snakerpy_dict['api'][0][1])) + '\r\n'
        if 'deprecated' in snakerpy_dict.keys():
            # 声明已经废弃
            _add_desc += self._what + (' is deprecated%s' % (': ' + snakerpy_dict['deprecated'][0][1])) + '\r\n'
        if 'since' in snakerpy_dict.keys():
            # 标识对象在哪个特定版本开始添加进来的
            _add_desc += self._what + (' is added since %s' % (snakerpy_dict['since'][0][1])) + '\r\n'
        if 'version' in snakerpy_dict.keys():
            # 标识对象的版本
            _add_desc += self._what + (' version is %s' % (snakerpy_dict['version'][0][1])) + '\r\n'
        if 'requires' in snakerpy_dict.keys():
            # 标识依赖
            _add_desc += self._what + (' requires: %s' % (snakerpy_dict['requires'][0][1])) + '\r\n'
        if 'author' in snakerpy_dict.keys():
            # 标识作者
            _add_desc += self._what + (' author is %s' % (snakerpy_dict['author'][0][1])) + '\r\n'
        if 'license' in snakerpy_dict.keys():
            # 标识许可
            _add_desc += self._what + (' license is %s' % (snakerpy_dict['license'][0][1])) + '\r\n'
        if 'copyright' in snakerpy_dict.keys():
            # 标识版权
            _add_desc += self._what + (' copyright %s' % (snakerpy_dict['copyright'][0][1])) + '\r\n'
        if 'todo' in snakerpy_dict.keys():
            # 标识对象后续还会进行的改进
            _add_desc += self._what + (' will do this later: %s' % (snakerpy_dict['todo'][0][1])) + '\r\n'
        if snakerpy_dict['desc'] != '':
            if _add_desc == '':
                _add_desc = snakerpy_dict['desc']
            else:
                _add_desc = snakerpy_dict['desc'] + '\r\n' + _add_desc
        if _add_desc != '':
            _str += '\r\n' + _add_desc + '\r\n'
        return _str

    def _get_numpy_param(self, snakerpy_dict):
        """获取numpy的param内容"""
        _str = ''
        if len(snakerpy_dict['param']) > 0:
            _str = '\r\nParameters\r\n----------\r\n'
            for _item in snakerpy_dict['param']:
                _str += _item[0][2] + ' : ' + _item[0][1] + '\r\n'
                if _item[1] != '' or _item[0][3] != '':
                    _str += '    '
                if _item[0][3] != '':
                    _str += 'default=' + _item[0][3] + ', '
                if _item[1] != '':
                    _str += _item[1] + '\r\n'
        return _str

    def _get_numpy_returns(self, snakerpy_dict):
        """获取numpy的returns内容"""
        _str = ''
        if len(snakerpy_dict['returns']) > 0:
            _str = '\r\nReturns\r\n----------\r\n'
            for _item in snakerpy_dict['returns']:
                _str += _item[0][1] + '\r\n    ' + _item[1] + '\r\n'
        return _str

    def _get_numpy_throws(self, snakerpy_dict):
        """获取numpy的throws内容"""
        _str = ''
        if len(snakerpy_dict['throws']) > 0:
            _str = '\r\nRaises\r\n----------\r\n'
            for _item in snakerpy_dict['throws']:
                _str += _item[0][1] + '\r\n    ' + _item[1] + '\r\n'
        return _str

    def _get_numpy_see(self, snakerpy_dict):
        """获取numpy的see内容"""
        _str = ''
        if len(snakerpy_dict['see']) > 0:
            _str = '\r\nSee Also\r\n----------\r\n'
            for _item in snakerpy_dict['see']:
                _str += _item[1] + '\r\n'
        return _str

    def _get_numpy_example(self, snakerpy_dict):
        """获取numpy的example内容"""
        _str = ''
        if len(snakerpy_dict['example']) > 0:
            _str = '\r\nExample\r\n----------\r\n'
            for _item in snakerpy_dict['example']:
                # 把第1行如果是回车，去掉
                _info = _item[1].strip()
                # print('a%a' % _info)
                _str += _info + '\r\n'
        return _str

    def _get_numpy_tutorial(self, snakerpy_dict):
        """获取numpy的tutorial内容"""
        _str = ''
        if len(snakerpy_dict['tutorial']) > 0:
            _str = '\r\nReferences\r\n----------\r\n'
            for _item in snakerpy_dict['tutorial']:
                _str += _item[1] + '\r\n'
        return _str

    def _get_numpy_function(self, snakerpy_dict):
        """获取numpy的function内容"""
        _str = ''
        if len(snakerpy_dict['function']) > 0:
            _str = '\r\nMethods\r\n----------\r\n'
            for _item in snakerpy_dict['function']:
                _str += _item[0][1] + '\r\n    ' + _item[1] + '\r\n'
        return _str
