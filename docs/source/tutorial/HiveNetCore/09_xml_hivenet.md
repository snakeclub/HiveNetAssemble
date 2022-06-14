# xml_hivenet模块说明

xml_hivenet模块主要实现了xml文件的简单处理处理，模块使用lxml.etree进行底层处理。

支持的主要功能：

1、支持xml文件解析处理，以及与字典对象的相互转换；

2、支持html文件解析（基于xpath）；

3、扩展支持xpath2.0语法。



## SimpleXml的基本使用参考

### 基本使用说明

1、构造函数

```
示例：xmldoc = SimpleXml('test.xml', obj_type=EnumXmlObjType.File)

主要参数如下：
@param {object} xml_obj - 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：
            obj_type = EnumXmlObjType.File 时，obj为文件路径
            obj_type = EnumXmlObjType.FileHandle 时，obj为文件句柄
            obj_type = EnumXmlObjType.String 时，obj为报文文本
        @param {EnumXmlObjType} obj_type=EnumXmlObjType.File - xml对象类型
        @param {string} encoding=encoding - 装载字符编码，如果传None代表自动判断
        @param {bool} use_chardet=True - 当自动判断的时候，是否使用chardet库
        @param {str} parser='xml' - 解析器类型，默认为xml
            xml - 标准xml解析器
            html - html解析器，兼容html一些不规范的地方
        @param {dict} register_namespace=None - 注册命名空间别名，格式为：
            {prefix: uri, prefix: uri, ... }  其中prefix和uri都为字符串
            注册命名空间后，后续的节点就可以通过tag='{uri}tagname'的方式添加带命名空间的节点
        @param {bool} use_xpath2=False - 使用xpath2.0，默认只支持xpath1.0
        @param {**kwargs} kwargs - 扩展的装载参数，包括XMLParser的参数
            attribute_defaults - inject default attributes from DTD or XMLSchema
            dtd_validation - validate against a DTD referenced by the document
            load_dtd - use DTD for parsing
            no_network - prevent network access for related files (default: True)
            ns_clean - clean up redundant namespace declarations
            recover - try hard to parse through broken XML
            remove_blank_text - discard blank text nodes that appear ignorable
                装载时是否将空白文本去掉，只有含这个参数，打印时pretty_print才生效
            remove_comments - discard comments
            remove_pis - discard processing instructions
            strip_cdata - replace CDATA sections by normal text content (default: True)
            compact - save memory for short text content (default: True)
            collect_ids - use a hash table of XML IDs for fast access (default: True, always True with DTD validation)
            resolve_entities - replace entities by their text value (default: True)
            huge_tree - disable security restrictions and support very deep trees
            target - a parser target object that will receive the parse events
            schema - an XMLSchema to validate against
```

2、提供各类函数获取及修改节点值和属性，主要的检索使用XPath语法；

3、支持另存为文件

```
示例：xmldoc.save('test1.xml', encoding='utf-8', xml_declaration=True)

@param {string|object} file=None - 要保存的文件的完整路径，如果不传代表修改原文件
    注：也可以传入打开的文件句柄
@param {string} encoding=None - 文件编码，如果为None代表使用创建时的编码
@param {**kwargs} kwargs - 扩展的装载参数，包括ElementTree.write的参数
	xml_declaration=None - 控制是否在文件中添加xml的声明，True - 一直添加, False - 不添加
    如果传None，代表只有encoding不是US-ASCII or UTF-8 or Unicode的时候才添加声明
```

### 存在命名空间的情况

对于存在命名空间的情况，SimpleXml并不支持“{namespace}tag”这种类型的xPath语法处理，标准的使用方法如下：

```
# 指定命名空间字典，key值为命名空间的别名，可自定义
_ns = {
    'people': 'http://people.example.com',
    'role': 'http://characters.example.com'
}

# 获取节点值，需注意xPath中命名空间下的每个节点都需要指定别名
_text = _pfile.get_value('people:actor[1]/people:name', default='None', namespaces=_ns)
_text = _pfile.get_value(
    '/people:actors/people:actor[1]/role:character[1]', default='None', namespaces=_ns)

# 创建带命名空间的节点，节点tag需要带命名空间的指定标识"{namespace}"
_tag = '{%s}%s' % (_ns['role'], 'tagname')
_node = ET.Element(_tag, nsmap=_ns)
_pfile.append_node('/people:actors', _node, namespaces=_ns)
```

### 将指定节点生成字典对象

to_dict函数可以将指定的节点生成字典对象（需注意不支持节点属性的情况），规则如下：

1、访问字典从节点的标签（tag）作为key，例如根节点的tag为data，则可通过_dict['data']进行对应的节点信息访问；

```
例如：
<data>
	<a>val1</a>
	<b>val2</b>
</data>
转换为字典：{'data': {'a': 'val1', 'b': 'val2'} }
```

2、xml中可通过type属性指定节点的类型，支持 dict, list, tuple, bool, int, float, string 这7种类型：其中dict 类型是默认类型，在字典中对应的value是一个字典，key为子节点的tag； bool, int, float, string 类型在字典中对应的value是节点的text转换过来的值；list、tuple是列表类型，在字典中对应得value是列表；

```
例如：
<data type='dict'>
	<a>val1</a>
	<b type='int'>3</b>
	<c type='list'>
		<c1>v1</c1>
		<c2>v2</c2>
		<c3><d>d1</d></c3>
	</c>
</data>
转换为字典：
{
	'data': {
		'a': 'val1',
		'b': 3,
		'c': ['v1', 'v2', {'d': 'd1'}]
	}
}
```

3、如果节点没有指定type属性，将自动根据子节点判断当前节点的类型，如果当前节点没有子节点，按string类型转换；如果当前节点有子节点，且子节点的tag没有重复情况，则按dict类型转换；如果子节点的tag有重复，则按list类型转换；

4、可以通过item_dict_xpaths参数指定某个list节点的列表项，不是直接取节点值，而是生成key值为tag的列表项：

```
例如：
<data>
	<a type='list'>
		<a1>x1</a1>
		<a2>x2</a2>
	</a>
	<c type='list'>
		<c1>v1</c1>
		<c2>v2</c2>
		<c3><d>d1</d></c3>
	</c>
<data>
指定item_dict_xpaths={'/data/c': None}
转换为字典：
{
	'data': {
		'a': ['x1', 'x2'],
		'c': [{'c1': 'v1'}, {'c2': 'v2'}, {'c3': {'d': 'd1'}}, ]
	}
}
```

### 将字典对象添加到xml中

可以通过 set_value_by_dict 函数将字典对象添加到xml文档的指定节点中，程序会自动判断类型并进行相应转换，示例如下：

```
# 创建SimpleXml对象
_doc = SimpleXml('<root><a type="list"><item>test1</item></a><b></b></root>',
                     obj_type=EnumXmlObjType.String)

# 要添加到b节点下的字典对象
_dict = {
    'b': True, 'c': 10, 'd': 3.4, 'e': 'teste', 'f': [
        False, 11, 4.5, 'haha', {'g': 'gteset', 'h': False}
    ],
    'i': {'a': 'tet', 'b': 'ddd'}
}

# 执行添加动作，通过with_type指定自动识别对象类型
_doc.set_value_by_dict('/root/b', _dict, with_type=True, debug=True)

print(_doc.to_string())

执行结果显示如下：
<root>
  <a type="list">
    <item>test1</item>
  </a>
  <b>
    <b type="bool">true</b>
    <c type="int">10</c>
    <d type="float">3.4</d>
    <e>teste</e>
    <f type="list">
      <item type="bool">false</item>
      <item type="int">11</item>
      <item type="float">4.5</item>
      <item>haha</item>
      <item>
        <g>gteset</g>
        <h type="bool">false</h>
      </item>
    </f>
    <i>
      <a>tet</a>
      <b>ddd</b>
    </i>
  </b>
</root>
```



## lxml.etree的基本使用参考

官方参考文档见：https://lxml.de/api/lxml-module.html

### 主要方法列表

**访问元素属性**
Element.tag(): 字符串类型，标识标识次元素类型
Element.text():  元素内容
Element.attrib():  属性字典
Element.clear(): 清楚所有子元素
Element.get(key, default=None): 获取key的元素属性，返回属性值，默认None
Element.items(): 将元素属性以元组形式返回
Element.keys():  列表形式返回属性名称
Element.set(key, value): 将元素上的属性设置为value

**元素子元素操作**
append(subelement): 添加子元素
extend(subelements)：零个或多个元素序列追加子元素
find(match, namespaces=None)：查找匹配第一个子元素，返回一个元素示例或None，match为标签名或xpath路径
findall(match, namespaces=None): 按照标签名称寻找子元素，match为标签名或者xpath路径
findtext(match, default=None, namespaces=None)：返回匹配到的第一个子元素的文本，match可以是标签名或xpath路径，如果一个元素都匹配不到，返回default的值
insert(index, element):在元素指定位置插入子元素
iter(tag=None): 使用当前元素作为跟创建树迭代器
iterfind(match, namespaces=None): 按照标签名和xpath查找所有匹配的子元素，返回迭代
itertext()：创建文本迭代器，迭代器按照文本顺序遍历元素和子元素，返回全部文本
remove(subelement): 从元素中删除子元素



### 遍历XML节点

1、遍历指定节点的子节点

```
import xml.etree as ET

tree = ET.parse('demo.xml')
root = tree.getroot()  # 获得根节点

# 遍历子节点，可以通过该方法遍历递归遍历所有节点
for child in root:
   print('%s %s' % (child.tag, child.attrib))
```

2、遍历所有节点重可符合匹配条件的节点

```
for n in root.iter(tag='neighbor'):
	# 遍历所有节点中tag为'neighbor'的节点
	print(n.attrib)
```



### 查找节点

1、通过XPath查找对象

```
for n in root.findall(".//year/..[@name='Singapore']")
	print(n.attrib)
```

2、带命名空间的情况

xml示例文件：

```
<?xml version="1.0"?>
<actors xmlns:fictional="http://characters.example.com"
        xmlns="http://people.example.com">
    <actor>
        <name>John Cleese</name>
        <fictional:character>Lancelot</fictional:character>
        <fictional:character>Archie Leach</fictional:character>
    </actor>
    <actor>
        <name>Eric Idle</name>
        <fictional:character>Sir Robin</fictional:character>
        <fictional:character>Gunther</fictional:character>
        <fictional:character>Commander Clement</fictional:character>
    </actor>
</actors>
```

方法1：

```
for actor in root.findall('{http://people.example.com}actor'):
    name = actor.find('{http://people.example.com}name')
        print(name.text)
        for char in actor.findall('{http://characters.example.com}character'):
            print(' |-->%s' % char.text)
```

方法2（推荐）：

```
ns = {
    'real_person': 'http://people.example.com',
    'role': 'http://characters.example.com'
}
for actor in root.findall('real_person:actor', ns):
    name = actor.find('real_person:name', ns)
        print(name.text)
        for char in actor.findall('role:character', ns):
            print(' |-->%s' % char.text)
```



### 添加节点

1、先创建要添加的节点元素

```
# 生成新节点：ET.Element(tag, attrib={}, **extra)
# <a attr1='value1' attr2='value2' />
a = ET.Element('a', attrib={'attr1': 'value1', 'attr2': 'value2'})
# <b>b text</b>
b = ET.Element('b', text='b text')
# <c>c text</c>c-tail
c = ET.Element('c', text='c text', tail='c-tail')

# 组合节点：ET.SubElement(parent, tag, attrib={}, **extra)
# <a attr1='value1' attr2='value2'><d /></a>
d = ET.SubElement(a, 'd')
```

2、添加节点到根节点

```
# <a attr1='value1' attr2='value2'><d /><b>b text</b><c>c text</c>c-tail</a>
n = a.append(
	b.append(c)
)

# 添加到根节点
root.append(n)
```



## XPath参考

具体参考学习网站：https://www.w3school.com.cn/xpath/index.asp

### XML 实例文档

我们将在下面的例子中使用这个 XML 文档。

```
<?xml version="1.0" encoding="ISO-8859-1"?>
<bookstore>
    <book>
      <title lang="eng">Harry Potter</title>
      <price>29.99</price>
    </book>
    <book>
      <title lang="eng">Learning XML</title>
      <price>39.95</price>
    </book>
</bookstore>
```



### 选取节点

XPath 使用路径表达式在 XML 文档中选取节点。节点是通过沿着路径或者 step 来选取的。

**下面列出了最有用的路径表达式：**

| 表达式   | 描述                                                       |
| :------- | :--------------------------------------------------------- |
| nodename | 选取此节点的所有子节点。                                   |
| /        | 从根节点选取。                                             |
| //       | 从匹配选择的当前节点选择文档中的节点，而不考虑它们的位置。 |
| .        | 选取当前节点。                                             |
| ..       | 选取当前节点的父节点。                                     |
| @        | 选取属性。                                                 |

**实例**

在下面的表格中，我们已列出了一些路径表达式以及表达式的结果：

| 路径表达式      | 结果                                                         |
| :-------------- | :----------------------------------------------------------- |
| bookstore       | 选取 bookstore 元素的所有子节点。                            |
| /bookstore      | 选取根元素 bookstore。 注释：假如路径起始于正斜杠( / )，则此路径始终代表到某元素的绝对路径！ |
| bookstore/book  | 选取属于 bookstore 的子元素的所有 book 元素。                |
| //book          | 选取所有 book 子元素，而不管它们在文档中的位置。             |
| bookstore//book | 选择属于 bookstore 元素的后代的所有 book 元素，而不管它们位于 bookstore 之下的什么位置。 |
| //@lang         | 选取名为 lang 的所有属性。                                   |



### 谓语（Predicates）

谓语用来查找某个特定的节点或者包含某个指定的值的节点。

谓语被嵌在方括号中。

**实例**

在下面的表格中，我们列出了带有谓语的一些路径表达式，以及表达式的结果：

| 路径表达式                         | 结果                                                         |
| :--------------------------------- | :----------------------------------------------------------- |
| /bookstore/book[1]                 | 选取属于 bookstore 子元素的第一个 book 元素。                |
| /bookstore/book[last()]            | 选取属于 bookstore 子元素的最后一个 book 元素。              |
| /bookstore/book[last()-1]          | 选取属于 bookstore 子元素的倒数第二个 book 元素。            |
| /bookstore/book[position()<3]      | 选取最前面的两个属于 bookstore 元素的子元素的 book 元素。    |
| //title[@lang]                     | 选取所有拥有名为 lang 的属性的 title 元素。                  |
| //title[@lang='eng']               | 选取所有 title 元素，且这些元素拥有值为 eng 的 lang 属性。   |
| /bookstore/book[price>35.00]       | 选取 bookstore 元素的所有 book 元素，且其中的 price 元素的值须大于 35.00。 |
| /bookstore/book[price>35.00]/title | 选取 bookstore 元素中的 book 元素的所有 title 元素，且其中的 price 元素的值须大于 35.00。 |



### 选取未知节点

XPath 通配符可用来选取未知的 XML 元素。

| 通配符 | 描述                 |
| :----- | :------------------- |
| *      | 匹配任何元素节点。   |
| @*     | 匹配任何属性节点。   |
| node() | 匹配任何类型的节点。 |

**实例**

在下面的表格中，我们列出了一些路径表达式，以及这些表达式的结果：

| 路径表达式   | 结果                              |
| :----------- | :-------------------------------- |
| /bookstore/* | 选取 bookstore 元素的所有子元素。 |
| //*          | 选取文档中的所有元素。            |
| //title[@*]  | 选取所有带有属性的 title 元素。   |



### 选取若干路径

通过在路径表达式中使用“|”运算符，您可以选取若干个路径。

**实例**

在下面的表格中，我们列出了一些路径表达式，以及这些表达式的结果：

| 路径表达式                       | 结果                                                         |
| :------------------------------- | :----------------------------------------------------------- |
| //book/title \| //book/price     | 选取 book 元素的所有 title 和 price 元素。                   |
| //title \| //price               | 选取文档中的所有 title 和 price 元素。                       |
| /bookstore/book/title \| //price | 选取属于 bookstore 元素的 book 元素的所有 title 元素，以及文档中所有的 price 元素。 |



