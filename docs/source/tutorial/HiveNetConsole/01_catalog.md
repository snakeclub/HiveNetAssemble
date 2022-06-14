# HiveNetConsole模块说明

HiveNetConsole是简单的命令行执行框架，可在该框架上基于yaml配置文件扩展增加不同的命令支持，主要特点如下：

1. 支持yaml配置不同命令扩展;
2. 支持多国语言显示；
3. 进入控制台可支持命令提示；
4. 支持直接在shell中执行命令，以及执行批量命令文件；
5. 跨平台;



## 开发命令行应用的步骤

### 开发命令执行函数

#### 直接实现命令执行函数

您可以直接实现命令执行函数，只要函数的输入和返回值满足以下要求即可：

1、函数格式为 cmd_deal_fun(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs) -> CResult

2、入参说明如下：

- message : prompt提示信息
- cmd : 执行的命令key值
- cmd_para : 传入的命令参数(命令后的字符串, 去掉第一个空格)
- prompt_obj : 传入调用函数的PromptPlus对象, 可以通过该对象的一些方法控制输出显示
- kwargs : 如果实现类是继承了CmdBaseFW, 则是传入实例化的kwargs参数

3、返回值为CResult, 可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理。

例如：

```
# 直接在模块中定义执行函数
def deal_func_on_main(message='', cmd='', cmd_para='', prompt_obj=None, **kwargs) -> CResult:
	# 执行处理逻辑
	...
	# 返回结果
	return CResult(code='00000')


# 在类中定义执行函数
class CmdFuns(object):
	def __init__(self, **kwargs):
		...
	
	# 静态函数调用
	@classmethod
	def deal_func_class_static(cls, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs) -> CResult:
	   # 执行处理逻辑
    ...
    # 返回结果
    return CResult(code='00000')
    
  # 实例函数调用
  def deal_func_class_static(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs) -> CResult:
	   # 执行处理逻辑
    ...
    # 返回结果
    return CResult(code='00000')
```



#### 继承CmdBaseFW开发扩展命令类1（一个类支持一个命令执行）

可以基于CmdBaseFW自行开发扩展命令，示例如下：

```
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _
from HiveNetConsole.base_cmd import CmdBaseFW

class YourClass(CmdBaseFW):
	  #############################
    # 需具体实现类覆盖实现的类
    #############################
    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数
        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）
        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        您的自定义初始化内容...

    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        实现类需要覆盖实现的命令处理函数
        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        您自己的处理函数内容
```

关注点如下：

- 通过 self._console_global_para 可以获取命令行框架的公共变量，有用的公共变量包括：
  - execute_file_path ：您的应用程序主目录
  - work_path ： 工作目录，也就是启动命令行的当前目录
  
- 框架会自动加载i18n控件作为全局多国语言控件，您可以通过"from HiveNetCore.i18n import _"载入方法，并在您的应用打印时进行多国语言转换，具体用法参考simple_i18n的手册

- 您可以在一个类中实现多个命令函数，自行通过“_cmd_dealfun”做逻辑路由即可，可以参考“HiveNetConsole.base_cmd.CommonCmd”的方法

- “cmd”和“cmd_para” 两个参数将输入的命令传给执行函数；

  

#### 继承CmdBaseFW开发扩展命令类2（一个类支持多个命令执行）

由于命令配置只支持配置到类，框架会直接执行 _cmd_dealfun 函数来处理命令，因此通常开发以一个类执行一个命令的方式处理。但如果需要一个类支持多个命令，可以采取以下方式进行扩展：

```
from HiveNetCore.generic import CResult
from HiveNetCore.i18n import _
from HiveNetConsole.base_cmd import CmdBaseFW

class YourClass(CmdBaseFW):
	  #############################
    # 需具体实现类覆盖实现的类
    #############################
    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数
        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）
        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        # 自定义初始化函数中设置命令的映射关系，并且请不要重载 _cmd_dealfun 函数
        self._CMD_DEALFUN_DICT = {
        	  'cmd1': self._my_cmd_dealfun1,
            'cmd2': self._my_cmd_dealfun2,
        }

    def _my_cmd_dealfun1(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        自定义命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        您自己的处理函数内容

    def _my_cmd_dealfun2(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        自定义命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
            shell_cmd {bool} - 如果传入参数有该key，且值为True，代表是命令行直接执行，非进入控制台执行
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        您自己的处理函数内容
```



### 部署您的应用目录

1、请将HiveNetConsole下的“conf/config.yaml”复制到您的应用目录下，例如"/yourapp/conf/config.yaml"；当然您也可以放到不同目录或指定不同文件名，但这样后续需要有些特殊的编码处理；

2、在应用目录下创建 "i18n"目录用于放置多国语言文件；您也可以放到不同目录下，但需要修改config.yaml中的 “i18n” 配置指定目录；

3、创建多国语言文件，不同语言的文件名为"message_语言标识.json"，例如"message_en.json"，翻译样式非常简单，就是类似以下格式的json字符串， 详细信息请参考HiveNetCore.i18n的手册：

```
{
    "'$1' is not support command!": "控制台不支持 '$1' 命令！",
    "You will shutdown $1 Console, continue?(y/N)": "您将关闭 $1 控制台，请确认是否继续(y/N)?",
    "Exit $1 Console": "退出 $1 控制台",
    "Cancel Exit": "取消退出操作"
}
```

4、创建一个用于启动控制台的py文件（例如console.py），用于执行启动操作，代码非常简单：

```
import sys
import os
from HiveNetCore.utils.file_tool import FileTool
from HiveNetConsole import ConsoleServer

def main(**kwargs):
    ConsoleServer.console_main(
        execute_file_path=os.path.realpath(FileTool.get_file_path(__file__)),
        **kwargs
    )

if __name__ == '__main__':
    main()
```

注：如果您希望将config放到不同目录，请在console_main函数传入default_config_file参数。



### 配置应用命令

1、所有配置都在config.yaml中，一些显示的配置项如下：

- console > name : 您的应用名称，在帮助文本中可以通过 {{NAME}} 进行替换

- console > version : 应用版本, 在帮助文本中可以通过 {{VERSION}} 进行替换

- console > shell_cmd_name: 您的程序建立的系统软连接名称, 在帮助文本中可以通过 {{SHELL_CMD_NAME}} 进行替换

- console > message : 控制台前面显示的提示符



2、将您的扩展命令配置到框架中，您需要在“console > cmd_list”下新增相应的数组值，例如：

```
 -
 	...  # 其他配置
 -
 	command: mdtowiki
  module_name: mediawikiTool.lib.mediawiki_cmd  # 注意如果这样配置需要安装mediawikiTool包到python中
  class: MediaWikiCmd
  function: cmd_dealfun  # 如果是继承CmdBaseFW的实现，则固定为cmd_dealfun，否则为对应的函数名
  instantiation: true
  cmd_para |-
    {
        "long_para": {
            "in": [],
            "out": [],
            "name": [],
            "stdpic": []
        }
    }
   help: |-
     {
        "en": [
                "convert markdown file to mediawiki format",
                "",
                "mdtowiki -in file [-out outpath] [-name title] [-stdpic]",
                "    -in : Markdown file path (include filename), if just filename then search on the current working directory",
                "    -out : the MediaWiki file output path, If not specified to represent output on the current working directory",
                "    -name : MediaWiki page title, If you do not specify the filename that represents the use of Markdown filename (without the extension)",
                "    -stdpic : Set this parameter to automatically rename the pictures in order;Otherwise it will be named after the original file name",
                "",
                "demo: mdtowiki -in mdtowiki.md",
                ""
        ],
        "zh_cn": [
                "将markdown格式文件转换为mediawiki格式",
                "",
                "mdtowiki -in file [-out outpath] [-name title] [-stdpic]",
                "    -in : Markdown文件路径(含名称), 如果在当前工作目录下可以只输入名称",
                "    -out : 要输出的MediaWiki文件路径, 如果不指定代表输出在当前工作目录上",
                "    -name : MediaWiki标题名字，如果不指定代表使用Markdown的文件名(不含扩展名)",
                "    -stdpic : 设置该参数可以自动将图片按顺序重命名; 否则将按原文件名命名",
                "",
                "示例: mdtowiki -in mdtowiki.md",
                ""
        ]
    }
```

说明如下：

- “command ” 是命令字符，及在命令行中输入的最前面的词
- 加载执行函数的说明可参考配置文件中的 "通用说明: 动态加载的命令函数通用配置"
- “cmd_para” 是命令提示的参数，格式可参考prompt_plus
- “help” 是命令的帮助，如上例，可以设置多语言的支持



3、如果您希望不使用"python console.py"这种方式执行，可以修改您的setup.py文件，增加以下参数，让安装的时候直接建立软连接，如以下示例，会建立一个wikitool的软连接直接启动程序，连接到console.py的main函数执行：

```
# 示例
entry_points={'console_scripts': [
    "wikitool = mediawikiTool.console:main"
]},
```



### 修改命令行配色方案

通过修改config.xml配置文件可以改变命令行展现的不同特性，其中一个比较关键的配置是修改命令行配色方案，如果遇到命令需要在不同颜色主题的命令行中执行，默认的配色方案可能有问题，这时候就需要修改配色方案来保证字体输出能清晰看到，可以修改配置中的 color_set 参数调整配色方案：

```
color_set : 命令行配色方案，如果采用默认方案可不传，每个配色格式类似为'#000088 bg:#aaaaff underline'
    input : 用户输入，默认为'#F2F2F2'
    cmd : 命令，默认为'#13A10E'
    name_para : key-value形式参数名， 默认为'#C19C00'
    short_para: -char形式的短参数字符， 默认为'#3B78FF'
    long_para: -name形式的长参数字符，默认为'#FFFF00'
    word_para: word 形式的词字符，默认为'#C19C00',  # word 形式的词字符
    wrong_tip: 错误的命令或参数名提示，默认为'#FF0000 bg:#303030', 也可以参考格式：#ff0000 bg:#ffffff reverse
    prompt: prompt提示信息，默认为'#F2F2F2'
```

示例：

```
...
color_set:
  # 设置为空让字体能同时适应黑白背景 -->
  input: ""
  prompt: ""
...
```



## 使用HiveNetConsole框架

1、执行上例中实现的console.py，将进入控制台进行命令的执行，该方式的好处是可以有命令提示；

2、可以通过传入参数直接在shell中执行内部的命令，具体方式可使用"python console.py help=y"查看。