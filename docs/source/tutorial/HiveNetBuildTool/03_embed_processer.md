# HiveNetBuildTool - 内置的构建插件

## ProcesserBuildDir（目录创建及文件复制）

该插件支持进行应用目录的创建和从源目录复制所需的文件（或文件夹），构建配置参数参考说明如下：

```yaml
# ******************************************
# dirs: 要创建的文件夹
# Item Key: 要在输出目录下创建的文件夹, 支持使用"/"创建多级文件夹
#   clear: bool, 文件夹已存在的情况是否清空目录, 默认为false
#   copy: list, 复制的文件或目录清单, 每项为一个复制操作, 支持以下两种配置方式
#     src_file: str, 直接传入要复制文件的路径(为源文件目录的相对目录), 直接复制到当前配置文件夹的根目录下
#     ["src_file", "dest_file"]: list, 第1个参数为要复制的文件路径, 第2个参数为要保存的文件路径(当前配置文件夹的相对路径)
#   copyAll: list, 要复制所有子文件及子文件夹的目录清单，每项为一个复制操作，支持以下两种配置方式
#     src_dir: str, 直接传入要复制的文件夹(为源文件目录的相对目录), 直接将该文件夹的所有子文件和子目录复制到当前配置文件夹的根目录下
#     ["src_dir", "dest_dir"]: list, 第1个参数为要复制文件夹, 第2个参数为要保存的文件夹(当前配置文件夹的相对路径)
# ******************************************
dirs:
  config:
    clear: true
  logs:
    clear: true
  plugins:
  i18n:
  services:
    clear: true
  tasks:
    clear: true
```

## ProcesserBuildGetSysInfos（获取系统信息并写入上下文）

该插件支持根据配置获取相关系统信息，并将获取到的值写入构建管道的上下文，供后续的构建管道插件使用。

可以在管道执行配置上通过上下文指定插件所获取到的系统信息放置在上下文中的key值，上下文配置key为"sys_infos_set_key"，不设置默认以"sysInfos"作为key放入上下文。

改插件处理的build配置格式参考如下:

```yaml
# ******************************************
# getSysInfos: 要获取并放置到管道上下文的配置
#   Item Key: 获取信息唯一标识(自定义)
#     infoType: str, 信息类型标识（extend_para.yaml中ProcesserGetSysInfos下的信息类型）
#       注: 如果不设置代表使用Item Key作为信息类型标识
#     getKey: str, 自定义写入上下文的信息获取key, 如果不设置则使用extend_para.yaml中对应信息类型的默认值
#     args: list, 调用获取信息函数的固定位置入参, 根据实际extend_para.yaml中对应信息类型的获取函数要求传参
#     kwargs: dict, 调用获取信息函数的key-value入参, 根据实际extend_para.yaml中对应信息类型的获取函数要求传参
# ******************************************
getSysInfos:
  platform:
  EnvOracleHome:
    infoType: sysEnviron
    getKey: EnvOracleHome
    args:
      - ORACLE_HOME
    kwargs:
      default: '/Oracle'
  ...
```

当前可支持获取的系统信息类型包括:

- platform: 获取系统操作系统信息, 无入参, 以字典形式返回不同操作系统信息, 具体参考HiveNetCore.utils.run_tool.RunTool.platform_info函数

- sysEnviron: 获取指定的系统环境变量值, args必须传入要获取的环境变量key, 例如['ORACLE_HOME']; kwargs参数可以支持传入找不到key时的默认值, 例如{'default': '/Oracle'}; 具体参考HiveNetCore.utils.run_tool.RunTool.get_sys_environ函数


## ProcesserBuildPrint（打印上下文指定信息）

该插件支持打印上下文的指定信息。

配置参考如下:

```yaml
# ******************************************
# print: 要打印的上下文信息
#   Item Key: 打印步骤唯一标识
#     showTips: str, 打印内容前的提示信息, 选填
#     path: str, 要打印的上下文字典检索路径
#       注1: 从根目录开始搜索, 路径下多个key之间使用'/'分隔, 例如 'root/key1/key2'
#       注2: 可以通过[索引值]搜索特定key下第几个配置(数组或字典), 例如 'root/key1[0]'搜素key1下第一个对象
#     default: Any, 路径找不到时打印的默认值
#     jsonPrint: bool, 使用json方式打印(格式化后的显示), 默认为True
# ******************************************
print:
  sysPrint:
    showTips: 系统信息
    path: sysInfos
  ...
```

## ProcesserBuildPrompt(用户输入交互)

该插件通过命令行获取用户输入并存入上下文对象中。

配置参考如下：

```yaml
# ******************************************
# prompt: 获取交互输入
#   配置为数组对象, 数组每个项为一次输入交互，可配置参数如下:
#   engine: 使用的交互引擎, 支持inquirer、PromptPlus、PromptPlusConsoleApp三种类型, 默认为inquirer
#     promptType: 交互类型, 支持以下几种类型, 默认为input
#       input - 文本输入
#       confirm - 操作确认
#       radio - 单选
#       checkbox - 复选
#     text: 提示文本, 可不设置
#     isUseEditor: 指示是否使用编辑器, 仅inquirer引擎支持, 默认为False
#     isPassword: 指示input输入交互内容是否密码, 默认为False
#     default: 默认值, 如果为input设置默认的文本, 如果为radio设置为默认选中的选项值, 如果为checkbox设置为默认选中的选项数组
#     title: 对话框标题, 仅PromptPlusConsoleApp引擎使用, 可不设置
#     yes_text: 对话框确认按钮文本, 仅PromptPlusConsoleApp引擎使用, 可不设置
#     no_text: 对话框取消按钮文本, 仅PromptPlusConsoleApp引擎使用, 可不设置
#     values: radio和类型checkbox使用, 选项清单数组, PromptPlus引擎不支持
#         [
#             ('选项值', '选项显示文本'),
#             ...
#         ]
#         注: 选项显示文本可以支持样式, 例如设置为: HTML('<style bg="red" fg="white">Red</style>')
#     setValuePath: 交互结果要设置到context上下文的值路径, 例如'key1/key2', 默认为'prompt'
# ******************************************
prompt:
  -
    promptType: radio
    values:
      - ["val1", "text1"]
      - ["val2", "text2"]
    default: "val2"
    setValuePath: "prompt/radio"
  -
    engine: PromptPlus
    text: "input you word: "
    default: "no"
    setValuePath: "prompt/input"
  ...
```
