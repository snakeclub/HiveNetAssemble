# utils.validate_tool使用说明

validate_tool通用验证工具，提供便捷的数据验证方法，可以支持单值验证、列表值验证、字典验证等。



## ValidateTool工具类

### 校验规则格式规范

在ValidateTool工具类中校验规则应按照一定的规范送入，才能保证按照自己的需要进行相应校验，具体规范如下：

#### 1、单个校验规则格式（完整格式）

完整的标准格式为一个tuple对象，格式为： (校验函数, args参数, kwargs参数, 自定义错误信息)， 数组每个位置说明如下:

- **第1位: 校验函数**

​	传入检查函数对象(如: ValidateTool.str_len), 也可传入自定义的函数，自定义函数的格式为: my_fun(obj, *args, **kwargs) -> bool, 其中args和kwargs是示意，除第一个入参必须固定为检查对象以外，其他的入参按需设计；

​	如果要使用的校验函数是ValidateTool的静态函数，可以直接传函数名文本，例如'str_len'

- **第2位: args参数**

  调用校验函数所需传入的占位参数, 如果没有参数可传None; 该参数应为一个tuple对象，例如:

  ​         ('str_len', (3, 4), ) - 将用以下方式调用校验函数: str_len(obj, 3, 4)

​		注意: 如果args参数放置的对象不是tuple类型，函数会自动把其加入到一个空数组中，实现兼容处理，例如:

​				('str_check_regex', '^[abc]+$', ) - 将用以下方式调用校验函数: str_check_regex(obj, ('^[abc]+$'))

- **第3位: kwargs参数**

  调用校验函数所需传入kv模式的字典, 如果没有参数可传None; 该参数应为一个dict对象, 例如:

​          ('str_is_datetime', None, {'format_str': 'yyyy/MM/dd'}) - 将用以下方式调用校验函数:

​           str_is_datetime(obj, format_str='yyyy/MM/dd')

- **第4位: 自定义校验不通过时返回的CResult对象的错误信息**

  ​	如果不传, 将会根据函数名自动从字典变量'VALIDATE_ERR_MSG'中获取对应函数名的错误信息，当然也可以自己增加或修改'VALIDATE_ERR_MSG'的值来自定义错误信息

​          注意: 错误信息中可以通过'$1'、'$2'等占位符将校验本身的信息替换到错误信息中, 可送入的占位变量顺序如下:  校验对象本身(obj)、校验对象标识(obj_id)、校验函数名、args参数(按顺序拆开)、kwargs参数(按顺序拆开)



#### 2、单个校验规则格式（不完整格式）

​      对单个校验规则可以进行简化，工具类支持送入不完整的格式：

- **传入不完整的tuple对象**

  ​		可以只传前几个位置的参数，例如: (校验函数, ) , (校验函数, None, kwargs参数, ) , 程序会自动将该tuple对象补全，缺失的后面几位会使用None进行补充，例如：('str_is_float', ) --> ('str_is_float', None, None, None)

- **仅传入函数名(string)**

  针对ValidateTool自带校验函数，且无需其他入参的情况，例如:

​        'str_is_float' -> (ValidateTool.str_is_float, None, None, None)

- **仅传入可执行函数**

​		针对自定义校验函数，且无需其他入参的情况，例如:

​        ValidateTool.str_is_float -> (ValidateTool.str_is_float, None, None, None)

- **传入其他类型的对象**

  程序将自动将对象转换为string去尝试对应回ValidateTool自带校验函数，例如:

​        object -> (str(object), None, None, None)



#### 3、校验规则列表对单行列表数据进行校验

通过校验列表可对单行的列表数据进行对应位置的数据校验（校验列表的类型必须是list），校验数据也应为列表类型(list或tuple)，如果对象不为列表类型，则会自定将对象转换为 [obj, ] 进行校验

规则格式为: [rule1, rule2, ..., ...] ，其中rule1，rule2的格式参考上两个章节

可对应校验单行数据列表: (data1, data2, ..., ...) 或 [data1, data2, ..., ...]



#### 4、校验规则字典对字典数据进行校验

通过校验规则字典可对字典数据进行对应位置的数据校验（校验字典的类型必须是dict），校验数据也应为字典类型(dict)，字典可以支持多层嵌套

规则格式为（其中rule的格式参考前几个章节）:

```
{
	'key1': rule1,
	'key2': rule2,
	'key3': {
		'key4': rule4,
		'key5': rule5
	}
}
```

可校验对应的字典数据:

```
{
	'key1': data1,
	'key2': data2,
	'key3': {
		'key4': data4,
		'key5': data5
	}
}
```



#### 5、使用And/Or逻辑组件进行校验规则的组合

可以使用And/Or逻辑组件进行多项校验规则的组合，使用这些规则同时对一个数据对象进行校验（格式中的rule的格式参考前几个章节）

格式为：('And/Or', [rule1, rule2, ... ], )

And和Or可以支持多层嵌套以实现复杂的校验规则，例如：

('Or', [rule1, rule2, ('And', [rule3, rule4], ), ], )   -  等同于 if rule1 or rule2 or (rule3 and rule4)



#### 6、使用List逻辑组件进行列表数据的逐个校验

可以使用List逻辑组件来说明校验对象是一个列表，来取出列表中的每个数据进行校验处理（格式中的rule的格式参考前几个章节）

格式为: ('List', rule, )  - 通过rule对对象列表中的每个数据逐个校验

通过List与And/Or以及其他校验规则的组合实现更复杂的校验处理，例如：

('List', ('And', [rule1, rule2, ], ), )  - 通过rule1、rule2对对象列表中的每个数据逐个校验

('List', [rule1, rule2, rule3, ...], )  - 通过 [rule1, rule2, rule3, ...]对表格数据进行校验，数据格式类似：

​		[ [data11, data12, data13, ...], [data21, data22, data23, ...], ... ]

注意：List的参数是单个rule对象，如果传入的是list对象代表的是校验表格数据，因此如果需要多规则校验，应通过And或Or来组合多规则。



#### 7、校验规则使用示例

（1）使用单个规则验证单个对象

```
# 验证规则
_rule1 = 'str_not_null'  # ValidateTool自带函数，无入参，可以使用字符串传函数名方式传入
_rule2 = ValidateTool.str_not_null  # 效果和上面一样，可以直接传入函数对象，自定义函数可以这样传入
_rule3 = ('str_len', (10, 20), )  # 带入参情况，通过数组第2位传入占位参数，即*args=(10, 20)
# _rule4与_rule3类似，通过数组第3位传入扩展字典参数，即*kwargs={'encoding': 'gbk'}
_rule4 = ('str_lenb', (10, 20), {'encoding': 'gbk'})
# 自定义失败错误信息，可以通过$1、$2等占位符获取调用参数（顺序为: 检查对象obj、对象标识obj_id、展开的args列表, 展开的kwargs.values列表）; 注意数组的其他参数如果不使用可以传None进来
_rule5 = ('str_not_null', None, None, '[$2] must not null')

# 进行验证, _result1为标准的CResult对象，包含失败后的错误信息
_result1 = ValidateTool.check_by_rule(
	_rule1, '', obj_id='登陆名'
)
```

（2）组合多个校验规则验证单个对象

```
# 可通过And、Or指令组合对象
_rule6 = ('And', [_rule1, _rule2, _rule3, ], )  # _rule1等变量的格式参见上1章节

# And和Or可以嵌套形成更复杂的规则，例如
_rule7 = ('Or', [_rule3, _rule4, ('And', [_rule2, _rule5], ), ], )
```

（3）列表形式的校验规则验证列表对象

```
# 校验规则
_rule = [_rule1, _rule1, _rule2, _rule3]
_obj = ['', 'text1', 'text2', 'text3']

# 进行验证, 工具将按规则与数据一一对应进行验证
_result1 = ValidateTool.check_by_rule(
	_rule, _obj, obj_id='列表'
)
```

4、一套规则验证列表中的多个对象

```
# 校验规则，通过List标签说明验证对象是多行数据
_rule = ('List', ('And', [_rule1, _rule2, _rule3, ]))
_obj = ['row1', 'row2', 'row3']
# 进行验证
_result1 = ValidateTool.check_by_rule(
	_rule, _obj, obj_id='验证多行'
)
```

5、验证表格形式的数据

```
# 校验规则，通过List标签说明验证对象是多行数据
_rule = ('List', [_rule1, _rule1, _rule2, _rule3])
_obj = [
	['row1', 'text1', 'text2', 'text3'],
	['row2', 'text1', 'text2', 'text3'],
	['row3', 'text1', 'text2', 'text3']
]
```

6、验证字典格式的数据

```
# 校验规则，检查dict模数据
_rule = {
    'a': 'str_not_null',
    'b': ('And', ['str_not_null', ('str_len', (3, 4))]),
    'c': {
        'c1': 'str_not_null',
        'c2': ['str_not_null', ('str_len', (3, 4)), 'str_is_email'],
        'c3': ('List', ['str_not_null', ('str_len', (3, 4)), 'str_is_email'])
    }
}

# 要验证的数据，如果需要一个规则验证多个dict，可以通过list传入，如 [{...},{...}, ]
_obj = {
    'a': 'not null',
    'b': 'abc',
    'c': {
        'c1': '',
        'c2': ['not null', 'abc', 'abc@123.com'],
        'c3': [
            ['not null1', 'abc1', 'abc@123.com1'],
            ['not null2', 'abc2', 'abc@123.com2'],
            ['not null3', 'abc3', 'abc@123.com3'],
        ]
    }
}

# 进行验证
_result1 = ValidateTool.check_by_rule(
	_rule, _obj, obj_id=''
)
```



### 空值及缺失值的校验规则

1、工具原生的校验函数在遇到校验数据空值的情况（None或''），不会进行实际的数据校验而是直接返回True（校验通过），因此如果需要保证一个数据非空且满足校验规则，建议使用'not_null'或'str_not_null'限定对象非空，并于实际要校验的规则通过And逻辑组合在一起进行校验；

注：自定义的函数可根据实际的需要决定是否增加空值通过校验的规则；

2、对于列表规则校验列表数据的情况（ [rule1, rule2, rule3] <-> [obj1, obj2, obj3] ），在数据项比规则项少的情况，工具默认不会校验失败；如果需要这种情况出现校验失败，需将参数ignore_list_miss_value置为False；

3、对于字典规则校验数据的情况，如果字典规则的key在待校验数据字典缺失，工具默认不会校验失败；如果需要这种情况出现校验失败，需将参数ignore_extra_keys置为False；



### 错误提示中obj_id的显示规则

错误提示中的$2可以替换为对象标识（obj_id），如果是非单个数据的校验情况，工具默认会将obj_id显示为具体数据的访问数据信息，具体包括以下几种情况：

1、列表规则校验列表数据的情况（ [rule1, rule2, rule3] <-> [obj1, obj2, obj3] ），会显示出错的位置，显示格式为'obj_id~n'，其中n为数据位置（从0开始），使用‘~’作为标识和位置的连接；

2、校验表格数据的情况，会显示出错的位置，显示格式为'obj_id~n~m'，其中n为数据行位置（从0开始），m为位置列位置，使用‘~’作为标识和位置的连接；

3、校验字典的情况，会显示出错的key的位置，显示格式为'obj_id->key1->key2'，使用'->'作为上下级标识的连接；

4、校验字典的情况，如果不希望显示obj_id，可以传入obj_id=''，这样显示格式将直接为‘key1->key2’；

5、校验字典列表的情况，会在开头显示字典所在的位置，根据obj_id是否有值分别显示的格式为'obj_id~n->key1->key2'或‘~n->key1->key2’;

如果不希望obj_id显示为访问数据信息，直接只显示obj_id，可将参数中的is_use_pre_obj_id置为False。



### 建立校验规则实例对象对多个数据进行校验

如果不希望多次传入规则进行同类数据的多次校验，可以创建校验实例对象，并利用该实例对象进行多次的数据校验，示例如下：

```
# 创建实例对象
_vaildate_obj = ValidateTool(_rule, ignore_list_miss_value=True, ignore_extra_keys=True, i18n_obj=None, is_use_pre_obj_id=True)

# 多次使用校验
_result1 = _vaildate_obj.check(obj1)
_result2 = _vaildate_obj.check(obj2)
```



## 自主扩展校验规则

可以自主对工具进行扩展，来实现更多的校验规则。

### 修改或增加默认校验失败提示信息

可以通过修改 **VALIDATE_ERR_MSG** 字典，改变默认的校验失败提示信息或增加新的失败提示信息。该字典的key为校验函数名（注意只有函数自身的名字，不包括所在包、模块及类等信息），value为提示信息，提示信息的格式可以参考签名第1章节的“单个校验规则格式（完整格式）”中的“自定义校验不通过时返回的CResult对象的错误信息”。



### 自定义校验函数

可以自主开发校验函数，函数定义为 fun(obj, *args, **kwargs) -> bool ，例如：

```
# 检查对象大小不超过1024
check_max_size(obj, max=1024):
	if len(obj) > 1024:
		return False
	else:
		return True
```

自定义校验函数的调用方式有两种：

1、直接在校验规则中使用，例如：

```
# max参数可以认为是args参数传入
_rule = (check_max_size, (1024), None, 'Object[$2]($1) must less than $4!')
或
# max参数认为是kwargs参数传入
_rule = (check_max_size, None, {'max': 1024}, 'Object[$2]($1) must less than $4!')
```

2、使用工具内置的check_fun调用，例如：

```
# max参数可以认为是args参数传入
_rule = ('check_fun', (check_max_size, 1024), None, 'Object[$2]($1) must less than $4!')
或
# max参数认为是kwargs参数传入
_rule = ('check_fun', (check_max_size), {'max': 1024}, 'Object[$2]($1) must less than $4!')
```



### 自定义逻辑组件

可以仿照And/Or/List的函数定义建立自主的逻辑处理组件，形成不同的规则组合或对校验数据的不同拆分处理。

逻辑组件函数的定义要求如下：

```
Fun(obj, 自定义args参数, 自定义kwargs参数, obj_id='object', ignore_list_miss_value=True, i18n_obj=None, is_use_pre_obj_id=True, pre_obj_id='') --> CResult

例如：
Fun(obj, mypara1, mypara2, mypara3='', mypara4=10, obj_id='object', ignore_list_miss_value=True, i18n_obj=None, is_use_pre_obj_id=True, pre_obj_id=''):
	...
```

注意obj_id, ignore_list_miss_value, i18n_obj, is_use_pre_obj_id, pre_obj_id 是必须要保留的kwargs参数。