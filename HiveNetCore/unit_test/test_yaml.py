#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
测试yaml模块

@module test_yaml
@file test_yaml.py
"""
import os
import sys
import unittest
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetCore.yaml import SimpleYaml, EnumYamlObjType
from HiveNetCore.utils.file_tool import FileTool
from HiveNetCore.utils.test_tool import TestTool


_TEMP_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), os.path.pardir, 'test_data/temp/yaml'
    )
)
if not os.path.exists(_TEMP_DIR):
    FileTool.create_dir(_TEMP_DIR, exist_ok=True)


class TestSimpleYaml(unittest.TestCase):
    """
    测试SimpleYaml模块
    """

    def setUp(self):
        """
        启动测试执行的初始化
        """
        self.file_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.path.pardir, 'test_data/yaml')
        )

    def tearDown(self):
        """
        结束测试执行的销毁
        """
        pass

    def test_yaml_get(self):
        """
        测试SimpleYaml获取数据
        """
        print('测试SimpleYaml - 获取数据')

        _tips = '测试SimpleYaml数据类型'
        _yaml = SimpleYaml(
            os.path.join(self.file_path, 'main.yaml'), obj_type=EnumYamlObjType.File
        )
        _yaml_dict = _yaml.yaml_dict['config1']['example_dict']
        self.assertTrue(
            _yaml_dict['int_val'] == 11,
            msg='%s, int_val error: %s' % (_tips, str(_yaml_dict['int_val']))
        )
        self.assertTrue(
            _yaml_dict['float_val'] == 10.1,
            msg='%s, float_val error: %s' % (_tips, str(_yaml_dict['float_val']))
        )
        self.assertTrue(
            _yaml_dict['bool_val'] is True,
            msg='%s, bool_val error: %s' % (_tips, str(_yaml_dict['bool_val']))
        )
        self.assertTrue(
            _yaml_dict['str_zh'] == '中文内容',
            msg='%s, str_zh error: %s' % (_tips, str(_yaml_dict['str_zh']))
        )
        self.assertTrue(
            TestTool.cmp_dict(_yaml_dict['list_val'][3], {'list_key1': 'list_key1_val', 'list_key2': 'list_key2_val'}),
            msg='%s, list_val error: %s' % (_tips, str(_yaml_dict['list_val'][4]))
        )
        self.assertTrue(
            TestTool.cmp_list(_yaml_dict['list_val'][4], ['list2_val1', 'list2_val2']),
            msg='%s, list_val error: %s' % (_tips, str(_yaml_dict['list_val'][4]))
        )

        _tips = '测试SimpleYaml配置路径获取'
        _val = _yaml.get_value('config2/example_3')
        self.assertTrue(
            _val == 'example_3_value', msg='%s, config2/example_3 error: %s' % (_tips, str(_val))
        )
        _val = _yaml.get_value('config2[0]')
        self.assertTrue(
            _val == 'example_3_value', msg='%s, config2[0] error: %s' % (_tips, str(_val))
        )
        _val = _yaml.get_value('config2[1]')
        self.assertTrue(
            _val is None, msg='%s, config2[0] error: %s' % (_tips, str(_val))
        )
        _val = _yaml.get_value('config1/example_dict/list_val[2]')
        self.assertTrue(
            _val == 3, msg='%s, config1/example_dict/list_val[2] error: %s' % (_tips, str(_val))
        )
        _val = _yaml.get_value('config1/example_dict/list_val[4][1]')
        self.assertTrue(
            _val == 'list2_val2', msg='%s, config1/example_dict/list_val[4][1] error: %s' % (_tips, str(_val))
        )
        _val = _yaml.get_value('config1[1]/list2_val')
        self.assertTrue(
            TestTool.cmp_list(_val, ['list2_value_1', 'list2_value_2']),
            msg='%s, config1[1]/list2_val error: %s' % (_tips, str(_val))
        )
        _val = _yaml.get_value('config1[1]/list2_val[1]')
        self.assertTrue(
            _val == 'list2_value_2',
            msg='%s, config1[1]/list2_val[1] error: %s' % (_tips, str(_val))
        )

    def test_yaml_del(self):
        """
        测试SimpleYaml删除数据
        """
        print('测试SimpleYaml - 删除数据')

        _tips = '测试SimpleYaml删除数据'
        _yaml = SimpleYaml(
            os.path.join(self.file_path, 'main.yaml'), obj_type=EnumYamlObjType.File
        )

        _yaml.remove('config1/example_dict/bool_val')
        _val = _yaml.get_value('config1/example_dict/bool_val')
        self.assertTrue(
            _val is None,
            msg='%s, config1/example_dict/bool_val error: %s' % (_tips, str(_val))
        )

        _yaml.remove('config1/example_dict[1]')
        _val = _yaml.get_value('config1/example_dict/float_val')
        self.assertTrue(
            _val is None,
            msg='%s, config1/example_dict[1] error: %s' % (_tips, str(_val))
        )

        _yaml.remove('config1/example_dict/list_val[1]')
        _val = _yaml.get_value('config1/example_dict/list_val')
        self.assertTrue(
            TestTool.cmp_list(_val[0: 2], ['value_1', 3]),
            msg='%s, config1/example_dict/list_val[1] error: %s' % (_tips, str(_val))
        )

        _yaml.remove('config1[0]/list_val[2][0]')
        _val = _yaml.get_value('config1/example_dict/list_val[2]')
        self.assertTrue(
            TestTool.cmp_dict(dict(_val), {'list_key2': 'list_key2_val'}),
            msg='%s, config1[0]/list_val[2][1] error: %s' % (_tips, str(_val))
        )

        _yaml.remove('config1[0]/list_val[3][1]')
        _val = _yaml.get_value('config1/example_dict/list_val[3]')
        self.assertTrue(
            TestTool.cmp_list(_val, ['list2_val1']),
            msg='%s, config1[0]/list_val[3][1] error: %s' % (_tips, str(_val))
        )

        _yaml.remove('config2')
        _val = _yaml.get_value('config2')
        self.assertTrue(
            _val is None,
            msg='%s, config2 error: %s' % (_tips, str(_val))
        )

    def test_yaml_set(self):
        print('测试SimpleYaml - 设置数据')

        _tips = '测试SimpleYaml设置数据'
        _yaml = SimpleYaml(
            os.path.join(self.file_path, 'main.yaml'), obj_type=EnumYamlObjType.File
        )

        _yaml.set_value('config5', 'set_root_val')
        _val = _yaml.get_value('config5')
        self.assertTrue(
            _val == 'set_root_val',
            msg='%s, config5 error: %s' % (_tips, str(_val))
        )
        _yaml.set_value('config5', 'set_root_val_upd')
        _val = _yaml.get_value('config5')
        self.assertTrue(
            _val == 'set_root_val_upd',
            msg='%s, config5 upd error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config4/set_str', 'set_str_val')
        _val = _yaml.get_value('config4/set_str')
        self.assertTrue(
            _val == 'set_str_val',
            msg='%s, config4/set_str error: %s' % (_tips, str(_val))
        )
        _yaml.set_value('config4/set_str', 'set_str_val_upd')
        _val = _yaml.get_value('config4/set_str')
        self.assertTrue(
            _val == 'set_str_val_upd',
            msg='%s, config4/set_str upd error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config3/set_dict', {'a': 'a_val', 'b': 'b_val', 'c': [1, 2, 3]})
        _val = _yaml.get_value('config3/set_dict')
        self.assertTrue(
            TestTool.cmp_dict(_val, {'a': 'a_val', 'b': 'b_val', 'c': [1, 2, 3]}),
            msg='%s, config3/set_dict error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config3/set_list', [1, 2, 3])
        _val = _yaml.get_value('config3/set_list')
        self.assertTrue(
            TestTool.cmp_list(_val, [1, 2, 3]),
            msg='%s, config3/set_list error: %s' % (_tips, str(_val))
        )
        _yaml.set_value('config3/set_list[1]', 5)
        _val = _yaml.get_value('config3/set_list')
        self.assertTrue(
            TestTool.cmp_list(_val, [1, 5, 3]),
            msg='%s, config3/set_list[1] error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config3/set_nest_list[3][2]', [5, 6, 7])
        _val = _yaml.get_value('config3/set_nest_list')
        self.assertTrue(
            TestTool.cmp_list(_val, [None, None, None, [None, None, [5, 6, 7]]]),
            msg='%s, config3/set_nest_list[3][2] error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config3/set_nest_dict/dict1/dict2', 'nest_dict_val')
        _val = _yaml.get_value('config3/set_nest_dict/dict1/dict2')
        self.assertTrue(
            _val == 'nest_dict_val',
            msg='%s, config3/set_nest_list[3][2] error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config1[0][5][3][1]', 'list_key2_val_upd')
        _val = _yaml.get_value('config1/example_dict/list_val[3]/list_key2')
        self.assertTrue(
            _val == 'list_key2_val_upd',
            msg='%s, config3/set_nest_list[3][2] error: %s' % (_tips, str(_val))
        )

        _yaml.set_value('config1/example_dict', 'example_dict_upd')
        _val = _yaml.get_value('config1/example_dict')
        self.assertTrue(
            _val == 'example_dict_upd',
            msg='%s, config1/example_dict error: %s' % (_tips, str(_val))
        )

    def test_yaml_save(self):
        print('测试SimpleYaml - 保存文件')

        _yaml = SimpleYaml(
            os.path.join(self.file_path, 'main.yaml'), obj_type=EnumYamlObjType.File
        )
        _yaml_extend = SimpleYaml(
            os.path.join(self.file_path, 'extend.yaml'), obj_type=EnumYamlObjType.File
        )

        # 合并两个文件
        _yaml.set_value('config3', _yaml_extend.yaml_config)

        # 添加自定义的内容
        _yaml.set_value('config3/self_list[3][4]', [1, 2, 3])

        # 保存文件
        _yaml.save(
            os.path.join(_TEMP_DIR, 'yaml_temp.yaml'), encoding='utf-8'
        )


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    unittest.main()
