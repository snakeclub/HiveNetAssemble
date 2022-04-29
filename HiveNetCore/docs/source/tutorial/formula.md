# formula使用说明

formula模块可用于对一段文本进行关键字解析，以及进行公式（表达式）匹配和公式值计算。主要应用场景包括代码解析结构化处理（例如将html代码按标签解析为字典形式进行处理）、对一段文本进行自定义公式识别和计算处理。



## 算法框架说明

### 第1步：检索单个关键字

- 将keywords（公式定义，包括开始标签及结束标签信息）分解为match_list（单关键字信息清单）
- 将解析文本按流处理方式（引用StringStream模块）按顺序逐字符分析和处理，算法如下：
  - 判断流当前字符是否匹配上match_list中每个关键字的第一个字符（如果有前置字符则为前置字符），如果匹配上，则将待继续匹配的结果压入compare_stack堆栈（登记已部分匹配上的信息），待流的下一个字符处理中继续向后匹配
  - 遍历compare_stack堆栈中的所有部分匹配信息清单，根据以下结果分别处理：
    - 流当前字符与要匹配结果的下一个预期字符不同，认定匹配失败，从compare_stack堆栈删除
    - 流当前字符与要匹配结果的下一个预期字符相同，且不是预期的结束字符，认定可继续匹配，更新compare_stack堆栈的匹配信息，等待下一次流字符处理
    - 流当前字符与要匹配结果的下一个预期字符相同，且是预期的结束字符，认定已匹配完成，将匹配结果存入match_result，然后从compare_stack堆栈删除

- 文本流处理完，得到match_result（单关键字的分析结果），该结果登记登记了每个关键字的开始位置（start_pos）、结束位置（end_pos）、前置字符（front_char）、后置字符（end_char）等信息；**注意：这个结果可能存在同一部分文本被多个关键字共同匹配上的情况**

### 第2步：单个关键字结果的处理

- 如果检索参数不允许多重匹配（multiple_match，即同一段文本有多个关键字命中），则按照关键字获取顺序优先级参数（EnumFormulaSearchSortOrder）进行结果的处理，将关键字结果有位置重叠的情况删除多余的匹配关键字信息
- 对匹配结果按位置先后的顺序进行排序，生成匹配结果按顺序排序的list清单

### 第3步：根据单关键字结果解析公式（表达式）

- 根据公式定义清单，从match_result按位置顺序找公式开始标签及结束标签，以此获取到一个完整的公式，更新至公式解析对象（StructFormula）中
- 查到到公式中间部分的单关键字匹配结果采用递归算法，由其父公式发起检索匹配，更新至公式解析对象（StructFormula）中
- 最终获得完整的公式解析对象（StructFormula）

### 第4步：根据公式解析对象计算公式值

采用递归算法，从第1个公式开始，逐级向下找到子公式，调用对应公式关键字的计算算法函数（deal_fun）计算公式的值，并更新到公式解析对象（StructFormula）中



## FormulaTool使用参考

### 静态工具

#### FormulaTool.search 

可直接调用类的该静态方法，匹配获取单关键字信息清单（match_list）的匹配结果（match_result）

match_list的定义 @see FormulaTool/match_list

dict格式的match_result  参考 @see FormulaTool/match_result

参考代码如下：

```
# 尝试解析SQL语句的关键字
_source_str = 'select * From test where t.name \tlike \'%fromxxx\' order by name'
_split_common = ('\\^', '\r', '\n', ' ', '\t', '\\$')  # 关键字前置及后置字符
_match_list = {
	'select': (_split_common, _split_common),
	'from': (_split_common, _split_common),
	'where': (_split_common, _split_common),
	'like': (_split_common, _split_common),
	'order': (_split_common, _split_common),
	'by': (_split_common, _split_common)
}

# 解析关键字
_match_result = FormulaTool.search(source_str=_source_str, match_list=_match_list, ignore_case=True,multiple_match=False, sort_oder=EnumFormulaSearchSortOrder.ListDesc)
```



#### FormulaTool.match_result_to_sorted_list

将dict格式的匹配结果（match_result）转换为已排序后的list格式

```
_match_result_list = FormulaTool.match_result_to_sorted_list(_match_result)
```



#### FormulaTool.analyse_formula

直接按keyworks参数解析公式文本，形成结构化字典的公式对象 @see StructFormula，该对象通过子公式的方式递归展示所有的公式信息。

示例如下：

```
# 解析带公式的字符串
_source_str = '[full begin] formula {$PY=[PY1 begin] xxxx{$single=$}xx{$PY=[PY2 begin]eeeee[PY2 end]$}x [PY1 end]$} from {$end=[End begin]abc {$abc=[abc begin]"[string begin]kkkaf{$PY=not formula$}dfdf,\\",""haha[string end]"[abc end]$} PY=eeffff [full end]'

# 定义字符串公式的公共关键字参数，例如python中的""引起来的认为是字符串
_string_para = StructFormulaKeywordPara()
_string_para.is_string = True  # 声明是字符串参数
_string_para.has_sub_formula = False  # 声明公式中不会有子公式
# 在查找字符串结束关键字时忽略的转义情况，例如"this is a string ,ignore \" , this is real end"
_string_para.string_ignore_chars = ['\\"', '""']

# 定义单关键字公式的公共参数（没有结束关键字）
_single_para = StructFormulaKeywordPara()
_single_para.is_single_tag = True  # 声明是单标签公式关键字

# 定义以字符串结尾为结束标签的公共参数
_end_para = StructFormulaKeywordPara()
_end_para.end_tags = ['\\$']

# 定义公式解析的关键字参数
_keywords = {
	# 第一个定义了字符串的公式匹配参数
	'String': [
		['"', list(), list()],  # 公式开始标签
		['"', list(), list()],  # 公式结束标签
		_string_para  # 公式检索参数
	],
	'PY': [
		['{$PY=', list(), list()],  # 公式开始标签
		['$}', list(), list()],  # 公式结束标签
		StructFormulaKeywordPara()  # 公式检索参数
	],
	'abc': [
		['{$abc=', list(), list()],
		['$}', list(), list()],
		StructFormulaKeywordPara()
	],
	'Single': [
		['{$single=$}', list(), list()],
		None,
		_single_para
	],
	'End': [
		['{$end=', list(), list()],
		None,
		_end_para
	]
}

# 解析公式
_formula = FormulaTool.analyse_formula(formula_str=_source_str, keywords=_keywords, ignore_case=False)

```



### 解析并执行公式计算

如果需要执行公式计算，则需实例化FormulaTool类才能处理，具体步骤如下：

1、准备keyworks公式参数、公式标签对应的处理函数

2、实例化FormulaTool类

3、执行公式计算

示例如下：

```
# 要解析的公式
_source_str = '[开始] {$PY=10 + 21$} {$PY=\'[PY1开始]{$ab=[ab开始]testab[时间开始]{$single=$}[时间结束][ab结束]$}} [PY1结束]\'$} "[string 开始]{$PY=string py$} [string 结束]" [结束]'

# 定义字符串公式的公共关键字参数，例如python中的""引起来的认为是字符串
_string_para = StructFormulaKeywordPara()
_string_para.is_string = True  # 声明是字符串参数
_string_para.has_sub_formula = False  # 声明公式中不会有子公式
# 在查找字符串结束关键字时忽略的转义情况，例如"this is a string ,ignore \" , this is real end"
_string_para.string_ignore_chars = ['\\"', '""']

# 定义单关键字公式的公共参数（没有结束关键字）
_single_para = StructFormulaKeywordPara()
_single_para.is_single_tag = True  # 声明是单标签公式关键字

# 定义公式解析的关键字参数
_keywords = {
            # 第一个定义了字符串的公式匹配参数
            'String': [
                ['"', list(), list()],  # 公式开始标签
                ['"', list(), list()],  # 公式结束标签
                _string_para  # 公式检索参数
            ],
            'PY': [
                ['{$PY=', list(), list()],  # 公式开始标签
                ['$}', list(), list()],  # 公式结束标签
                StructFormulaKeywordPara()  # 公式检索参数
            ],
            'ab': [
                ['{$ab=', list(), list()],
                ['$}', list(), list()],
                StructFormulaKeywordPara()
            ],
            'Single': [
                ['{$single=$}', list(), list()],
                None,
                _single_para
            ]
        }

# 定义公式对象处理函数
_deal_fun_list = {
            'PY': FormulaTool.default_deal_fun_python,  # 执行python语句
            'String': FormulaTool.default_deal_fun_string_content,  # 只保留标签内容
            'ab': formula_deal_fun_test,  # 自定义公式处理函数
            'Single': FormulaTool.default_deal_fun_datetime_str  # 获取日期
        }

# 初始化公式类
_formula_obj = FormulaTool(
            keywords=_keywords,
            ignore_case=False,
            deal_fun_list=_deal_fun_list,
            default_deal_fun=None
        )

# 计算公式，所有结果转换为字符串
_formula = _formula_obj.run_formula_as_string(_source_str)

# 打印公式执行结果
print(_formula.formula_value)
```



### 自定义公式处理函数

可按照以下格式自定义公式的处理函数：

fun(formular_obj, **kwargs):

                formular_obj : StructFormula 要处理公式对象（函数直接修改对象），该函数需更新对象的formula_value
    
                kwargs ：计算公式所传入的key=value格式的参数，参数key由处理函数定义（建议统一定义便于简化处理,由run_formula_as_string函数的kwargs参数传入）



公式处理类FormulaTool已经定义了几个默认的处理函数：

default_deal_fun_string_full ：将标签自身的字符串作为设置值

default_deal_fun_string_content ：将标签内容的字符串作为设置值

default_deal_fun_python ：标签内容作为python代码执行，将执行结果的对象作为设置值

default_deal_fun_datetime_str ：获取当前时间日期字符格式



## 参数详细说明

```
keywords - {dict} - 公式关键字定义，格式如下：
	key - string 关键字标识名
	value - list 匹配定义数组，按顺序定义为:
		开始标签 - [string-匹配字符串, list-前置字符, list-后置字符]
		结束标签 - [string-匹配字符串, list-前置字符, list-后置字符]，结束标签可以置None（表示使用匹配参数）
		匹配参数 - StructFormulaKeywordPara, 对象属性为：
			object.is_single_tag : bool 该标签是否单独一个标识，不含公式内容
			object.has_sub_formula : bool 是否包含子公式，如果为True则代表继续分解公式里面的子公式
			object.is_string : bool 是否字符串，如果为True代表是字符串（字符串不包含子公式）
			object.string_ignore_chars : list 字符串的结束标签忽略字符，例如["\\'", "''"]
			object.end_tags : list 当结束标签为None时，且不是单独标签，通过该参数获取结束标识（可以为多个字符）:
				\$ : 以结尾为结束标签'\\$'
				\t : 以下一个标签开始为当前结束标签'\\t'，注意不是代表tab的'\t'
```

