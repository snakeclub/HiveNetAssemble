# generic使用说明

generic模块主要定义一些公共的基础通用类。



## NullObj（空对象定义类）

NullObj为空对象定义类，用于支持可动态增加属性的使用场景。

### 普通用法

```
# 定义需含属性的对象
_obj = NullObj()

# 动态增加属性和值
_obj.attr1 = 'attr1_value'
_obj.attr2 = (5, 6, 7)
_obj.attr3 = NullObj()  # 属性嵌套属性
_obj.attr3.prop = 'level 2 value'

# 访问属性
for item in _obj.attr2:
	print(_obj.attr3.prop + str(item)
```

### 与dict对象相互转换

```
# dict转换为NullObj
_dict = {
	'attr1': 'attr1_value',
	'attr2': (5, 6, 7),
	'attr3': {'prop': 'level 2 value'},  # 如果还有字典，则会生成嵌套属性
}
_obj = NullObj.get_nullobj_from_dict(_dict)
# 访问对象值
print(_obj.attr3.prop)

# NullObj转换为dict，可以指定某些属性不参加转换
_dict = NullObj.get_object_attr_dict(_obj, ignored_key='attr2')
```

### json字符串转换

主要用于支持base_tools.string_tool.StringTool的json对象转换方法：object_to_json和json_to_object。

```
# 创建对象
_obj = NullObj()
_obj.attr1 = 'attr1_value'
_obj.attr2 = (5, 6, 7)

# 与json直接转换
_json_str = _obj.__json__()
_new_obj = NullObj.__fromjson__(_json_str)

# 通过StringTool处理
_json_str = StringTool.object_to_json(_obj)
_new_obj = StringTool.json_to_object(_json_str, class_ref=NullObj)  # 需指定对象类型
```



## CResult(通用错误类)

通用错误类定义，便于规范所有的错误信息返回判断标准，该类继承自NullObj，因此可直接在该类的实例对象上直接添加属性用于各类返回值。

**注意：CResult是HiveNetCore中的基础类，大部分函数交互都会使用该类进行返回处理，建议严格按照这个规则进行编码**

错误类的主要属性包括：

- code - 错误码，'00000'代表成功，参照HiveNet的错误码规范
- msg - 错误信息描述，如果i18n_obj不为None时，该参数传入的是国际化的消息ID；如果传入msg=None，则代表自动通过code查找HiveNet的错误码具体的错误描述（需要增加或修改错误码映射，可到包安装目录的HiveNetCore.hivenet_error_code目录下修改错误码映射及国际化文件，格式参考simple_i18n）
- error - 发生异常时的异常类型type的字符串
- trace_str - 错误追踪堆栈日志，异常时的traceback.format_exc()
- i18n_msg_paras - 与msg配套使用，可通过$1,$2等占位符进行消息内容的变量替换

### 创建并使用CResult

```
# 如果错误码是使用HiveNet错误码规范的情况,msg可以自动获取并填写
_result = CResult(code='00000')
# 补充其他返回值
_result.attr = '其他返回值'

# 判断是否成功,注意该方法只适用HiveNet错误码规范
if not _result.is_success():
	print('失败：' + _result.msg)

# 自定义错误码，使用占位符的方式
_result = CResult(code='-1', msg='run error: $1', error=str(type(Exception)), i18n_msg_paras=('EX Model'))
```

### 配合exception_tool使用错误码

```
_result = CResult(code='00000')
with ExceptionTools.ignored_CResult(result_obj=_result, error_map={ZeroDivisionError: ('10001', 'zero division error')},expect=(ValueError),logger=None,self_log_msg=''):
	# 当遇到异常时可以自动匹配并修改错误类的值
	i = 1/0
	i = i + 1000
```

### json字符串转换

主要用于支持base_tools.string_tool.StringTool的json对象转换方法：object_to_json和json_to_object。与NullObj类似，不再重复说明，但注意这种方式转换，不支持国际化控件的转换处理。