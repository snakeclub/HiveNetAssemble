# HiveNetPromptPlus使用说明

HiveNetPromptPlus是基Python语言开发的一个增强的交互命令行扩展处理库，基于[prompt_toolkit2](https://github.com/jonathanslenders/python-prompt-toolkit)进行封装和扩展，简化需要命令行交互所需要的代码量，不需要了解prompt_toolkit的过多参数设置即可通过数组参数实现命令行和参数的高亮显示和提示输入。

如果您需要了解prompt_toolkit的使用可查看相关文档：http://python-prompt-toolkit.readthedocs.io/en/master/



## prompt_toolkit部分参数介绍

**default** :  string 交互输入的默认值，直接显示在界面上，可以进行修改后回车输入

**wrap_lines** :  bool or Filter，默认为True，输入内容超长自动换行显示，如果选否则只在1行中显示，通过滚动查看前后内容

**is_password** :  bool or Filter， 默认为False,是否密码输入（如果是密码输入显示*）

**multiline** :  bool or Filter， 默认为False，是否支持多行输入，如果是多行输入，有两种退出方式:

            1、输入结束后按Esc键，并接着按Enter键

            2、输入结束后按“Ctrl + Enter”

**validate_while_typing** :  bool or Filter， 默认为False，是否在启动时同步进行输入验证，和validator参数共同应用

**enable_history_search** :  bool or Filter， 默认为False, 是否启用通过上箭头键获取输入历史，和history参数共同应用；如果未指定history参数，则默认使用InMemoryHistory



前面提到的Filter的说明： prompt_toolkit.filters.Filter类（抽象类，继承类必须至少实现__call__函数-必须返回bool值）:

            可以利用prompt_toolkit.filters内置的一些类简化处理，例如：

            1、Condition类: is_password=Condition(lambda: hidden[0])

            2、利用修饰符，将无入参的函数转换为Filter类:

                @Condition

                def feature_is_active():  # `feature_is_active` becomes a Filter.

                    return True



## 单次获取输入

无需进行实例化，直接调用`PromptPlus.simple_prompt`即可。

**示例1：获取命令行输入，执行自定义函数，返回自定义提示结果：**

```
from HiveNetPromptPlus import PromptPlus

def fun1(prompt_text=''):
    """自定义获取输入后的执行函数"""
    # 在这里填入您的处理
    print('fun1 - your input is: ' + prompt_text)
    return 'deal "' + prompt_text + '" and return'

result1 = PromptPlus.simple_prompt(message='fun1输入>', deal_fun=fun1)
print('fun1 return :' + result1 + '\n')
```

**示例2：使用prompt_toolkit的参数，输入HTML代码带颜色标注**

```
from pygments.lexers import HtmlLexer
from prompt_toolkit2.shortcuts import prompt
from prompt_toolkit2.styles import Style
from prompt_toolkit2.lexers import PygmentsLexer
from HiveNetPromptPlus import PromptPlus

result3 = PromptPlus.simple_prompt(message='输入HTML代码>', deal_fun=None,
                                       lexer=PygmentsLexer(HtmlLexer), style=our_style)
print('html return :' + result3 + '\n')
```

## 实现命令行交互控制台

要实现命令行交互控制台，步骤是先进行PromptPlus 类的实例化`prompt_obj = PromptPlus(...)` ，然后通过实例的prompt_once或start_prompt_service方法来实现交互处理。

### 通过函数返回值确定退出控制台

可以通过执行的函数（包括deal_fun、default_dealfun、on_abort、on_exit）的返回值控制是否退出控制台，当遇到返回值为CResult类型，且错误码为10101时，将退出控制台。



### 部分重要参数

#### cmd_para

命令参数字典 ，PromptPlus最核心的参数，其基本类型是dict，具体定义如下：

- key为命令标识

- value仍为dict()，value的key为参数名，参数名与参数值的定义如下:
  - **deal_fun** (匹配到命令要执行的函数) : fun 函数定义（function类型），函数固定入参为fun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs)

       ```
       @param {string} message - prompt提示信息
       @param {string} cmd - 执行的命令key值
       @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
       @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
       @param {kwargs} - 扩展参数，建议带上以支持未来的扩展
     @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
     	注：控制台也支持处理函数返回string、iter这两类对象，框架将对这两类对象执行打印处理, 但这种模式未来将不再支持，建议通过prompt_obj.prompt_print自行输出，或通过CResult的print_str属性进行打印
     ```

  - **name_para** (para_name=para_value形式的参数) : dict(para_name: para_value_list)

      para_name {string} - 参数名
      para_value_list {string[]} - 对应参数名下的可选参数值清单，如果para_value_list为None代表可以输入任意值
  - **short_para** (-para_char para_value 形式的参数) : dict(para_char, para_value_list)

      para_char {char} - 短参数标识字符（单字符，不带-）
      para_value_list {string[]} - 对应参数名下的可选参数值清单，如果para_value_list为None代表可以输入任意值
      注：该形式可以支持多个字符写在一个'-'后面，例如: -xvrt

  - **long_para** (-para_name para_value形式的参数) : dict(para_name, para_value_list)


      para_name {string} - 参数名（可以多字符，不带-）
      para_value_list {string[]} - 对应参数名下的可选参数值清单，如果para_value_list为None代表可以输入任意值
  - **word_para** (直接一个词形式的参数) : dict(word_name, '')

  ​       word_name {string} - 直接参数名



  **cmd_para** 的示例如下：

      # 示例：dir para1=value12 -a value2a -bc -abc value1abc -ci
      test_cmd_para = {
          'help': {
              'deal_fun': help_cmd_dealfun,
              'name_para': None,
              'short_para': None,
              'long_para': None,
              'word_para': {
              	'help': '',
              	'start': ''
              }
          },
          'dir': {
              'deal_fun': dir_cmd_dealfun,
              'name_para': {
                  'para1': ['value11', 'value12'],
                  'para2': ['value21', 'value22']
              },
              'short_para': {
                  'a': ['value1a', 'value2a'],
                  'b': None,
                  'c': []
              },
              'long_para': {
                  'abc': ['value1abc', 'value2abc'],
                  'bcd': None,
                  'ci': []
              }
          }
      }
      ```
#### default_dealfun

在命令处理函数字典中没有匹配到的命令，默认执行的处理函数。函数的定义为fun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs)，返回值为CResult，是执行命令函数处理结果，可以通过CResult的print_str属性控制框架进行打印。

```
def default_cmd_dealfun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
    """默认命令处理函数"""
    # 这里做您希望的处理代码
    Cresult(code='00000')
    Cresult.print_str = '您要打印的内容'
    return Cresult
```

#### on_abort /on_exit

on_abort 是当用户取消输入（Ctrl + C）时执行的函数 ；on_exit 是当用户退出（Ctrl + D）时执行的函数（**注意如果已输入部分内容，Ctrl + D将不生效**）。两类函数的定义一样，为fun(message='', prompt_obj=None, **kwargs)，返回值为CResult，是执行命令函数处理结果，可以通过CResult的print_str属性控制框架进行打印。

注：可通过错误码10101退出命令行

```
def on_abort(message='', prompt_obj=None, **kwargs):
    """Ctrl + C : abort,取消本次输入"""
    # 这里做您希望的处理代码
    return CResult(code='00000')

def on_exit(message='', prompt_obj=None, **kwargs):
    """Ctrl + D : exit,关闭命令行"""
    # 这里做您希望的处理代码
    return CResult(code='10100', msg=u'get abort single(KeyboardInterrupt)')
```

### 1. 实例化PromptPlus

实例化PromptPlus类，传入建立命令行交互的各类参数，具体参数见构造函数的定义，示例如下：

```
	_prompt = PromptPlus(
        message='请输入>',
        default='help',  # 默认输入值
        cmd_para=test_cmd_para,  # 命令定义参数
        default_dealfun=default_cmd_dealfun,  # 默认处理函数
        on_abort=on_abort,  # Ctrl + C 取消本次输入执行函数
        on_exit=on_exit  # Ctrl + D 关闭命令行执行函数
    )
```

### 2. prompt_once方式

prompt_once 方法每次只执行一次的输入获取（与simple_prompt类似，但主要的处理参数可在PromptPlus对象中定义好）。用prompt_once 方法需要代码自行控制循环和退出，通过执行的结果的CResult.code值确认用户操作情况，CResult.code的定义为：

```
'00000' - 处理成功
'29999' - 出现未知异常
'10100' - 用户中断输入（Ctrl + C）
'10101' - 用户退出应用（Ctrl + D）
```

示例：

```
    # 循环使用prompt_once一个获取命令和执行
    while True:
        prompt_result = _prompt.prompt_once(default='help')
        print('prompt_result: %s', prompt_result.msg)
        if prompt1_result.code == '10002':
            break
    # 结束提示循环
    print('prompt1 stop！')
```

### 3. start_prompt_service方式

start_prompt_service方法是更简便的发起命令控制台的方式，只要一行代码，示例如下：

```
prompt1.start_prompt_service(
        tips=u'命令处理服务(输入过程中可通过Ctrl+C取消输入，通过Ctrl+D退出命令行处理服务)',
        is_async=False,
        is_print_async_execute_info=True
)
```

其中is_async控制是否异步模式，即在命令执行完成前就可以接收下一个命令输入，否则等待命令结束后才接收下一个命令输入。

注：异步模式还有一个bug未解决，就是如果执行的函数有屏幕输出，会导致自己输入的内容显示不到最后一行，信息会乱掉，所以使用时要注意，最好将异步模式的输出打印在后台日志中，结束时一次性显示即可。

## 直接执行命令

有些情况需要在后台代码中直接执行指定的命令，可以通过执行call_cmd_directly函数进行处理，定义如下：

```
def call_cmd_directly(self, cmd_str):
    """
    外部直接使用实例执行命令, 不通过命令行获取
    @param {string} cmd_str - 要实行的命令(含命令本身和参数)
    @return {CResult} - 执行返回结果
    """
```



## 控制打印输出

推荐的打印输出模式如下：

1、在调用命令函数时会传入prompt_obj对象，建议直接通过prompt_obj.prompt_print进行打印；

2、如果希望返回再打印，可以通过返回的CResult的print_str属性进行打印处理;



## 自定义配色方案

主要在PromptPlus 时指定配色方案，涉及以下两个参数：

**enable_color_set** {bool} - 默认True，使用配色集方案，如果选否则自行通过python-prompt-toolkit的方式设定配色方案

**color_set** {dict} - 要使用的配色集方案，如果传None则使用系统默认配色集

默认的配色方案如下，可以按自己喜好调整：

```
	_default_color_set = {
            # 用户输入
            '': '#F2F2F2',  # 默认输入
            'cmd': '#13A10E',  # 命令
            'name_para': '#C19C00',  # key-value形式参数名
            'short_para': '#3B78FF',  # -char形式的短参数字符
            'long_para': '#FFFF00',  # -name形式的长参数字符
            'word_para': '#C19C00', # word 形式的词字符
            'wrong_tip': '#FF0000 bg:#303030',  # 错误的命令或参数名提示

            # prompt提示信息
            'prompt': '#F2F2F2'
        }
```

