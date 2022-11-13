# HiveNetBuildTool总览

HiveNetBuildTool是HiveNetAssemble的通用代码构建工具, 基于HiveNetPipeline管道执行的方式提供代码可扩展的代码构建框架, 不同应用可通过开发HiveNetPipeline管道插件的方式快速实现自定义的构建逻辑。

## 安装方法

### 源码方式安装

- HiveNetBuildTool库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetBuildTool

- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetBuildTool-0.1.0-py3-none-any.whl

## 创建自定义构建工具的步骤

您可以基于HiveNetBuildTool创建自定义的构建步骤，以自定义的HiveNetMicro构建工具为例，参考步骤如下：

1、创建自定义构建工具的基础目录（用于放置自定义构建相关配置和文件），例如/MyBuild

2、创建/MyBuild/HiveNetMicroPlugin目录，放置该类型的构建相关配置和文件（支持一个构建工具构建多种不同类型应用）；

3、开发自定义的构建配置（build.yaml构建配置文件的具体配置）的自定义管道处理插件，放在 /MyBuild/HiveNetMicroPlugin/plugins目录下，例如以下的代码参考：/MyBuild/HiveNetMicroPlugin/plugins/processer_config_templates.py

```python
# 自定义构建配置处理管道插件
from HiveNetPipeline import PipelineProcesser


class ProcesserBuildConfigTemplates(PipelineProcesser):
    """
    配置文件模版生成
    """

    @classmethod
    def processer_name(cls) -> str:
        """
        处理器名称，唯一标识处理器

        @returns {str} - 当前处理器名称
        """
        return 'ProcesserBuildConfigTemplates'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
        """
        执行处理

        @param {object} input_data - 处理器输入数据值，除第一个处理器外，该信息为上一个处理器的输出值
        @param {dict} context - 传递上下文，该字典信息将在整个管道处理过程中一直向下传递，可以在处理器中改变该上下文信息
        @param {Pipeline} pipeline_obj - 管道对象

        @returns {object} - 处理结果输出数据值, 供下一个处理器处理, 异步执行的情况返回None
        """
        # 获取当前要处理的配置标识
        _current_key = context.get('current_key', 'configTemplates')  # 获取当前要处理的配置标识(从构建管道配置中获取)
        _config = context['build_config'].get(_current_key, None)  # 根据标识获取到该配置标识的具体构建配置

        # 获取不到配置, 不处理
        if _config is None:
            return input_data

        # 自定义的处理逻辑
        ...

        # 返回输出结果
        return input_data

```

注：插件可以通过管道的上下文对象（context）获取构建的相关信息，该上下文对象包含的信息包括：

- build_type_config : 构建器配置config.yaml中，对应的构建类型的配置参数字典

- base_path ： 构建器的基础目录

- cmd_opts ：传入的命令行key-value参数

- build ：当前构建参数

- build_config ： 当前构建的完整配置参数



4、创建自定义类型的构建执行步骤配置文件（HiveNetPipeline的配置），例如：/MyBuild/HiveNetMicroPlugin/build_pipeline.yaml

```yaml
# 构建管道配置
"1":
  name: 构建应用文件夹（使用框架自带的构建插件）
  processor: ProcesserBuildDir  # 管道插件处理器标识
  context:
    current_key: dirs  # 设置上下文, 指定该节点的配置标识
"2":
  name: 构建配置文件模版（使用自定义的构建插件）
  processor: ProcesserBuildConfigTemplates
  context:
    current_key: configTemplates

...
```

5、创建构建工具的加载配置，放置在/MyBuild目录下，例如：/MyBuild/config.yaml

```yaml
# ******************************************
# 构建工具配置
# Item Key: 构建类型标识
#   plugins: str, 该构建类型的自有管道插件目录(构建工具目录的相对路径)
#   pipeline: str, 构建管道配置文件(构建工具目录的相对路径)
#   selfConfig: dict, 不同类型构建工具的自有配置参数
# ******************************************
HiveNetMicro:
  plugins: HiveNetMicroPlugin/plugins
  pipeline: HiveNetMicroPlugin/build_pipeline.yaml
  selfConfig:
    # ******************************************
    # configTemplatesPath: 配置模版路径
    # ******************************************
    configTemplatesPath: ../template/configTemplates
    noSqlDbInitScriptPath: ../template/noSqlDbInitScript
...
```

6、可以自行创建一个执行脚本，用于执行构建操作



## 构建配置文件说明

构建工具可以基于构建配置文件生成最终的应用，构建配置文件需按照构建工具的要求，以及构建插件格式要求进行配置，主要的配置和说明参考如下：

```yaml
# ******************************************
# build: 构建参数（通用配置）
# name: 当前构建的标识(仅用于区分不同构建配置)
# type: 构建类型, 指定为HiveNetMicro
# source: str, 构建源文件目录, 为当前构建配置文件所在目录的相对目录
# output: str, 构建结果输出目录, 为当前构建配置文件所在目录的相对目录
# successTips: list, 构建成功后的提示内容, 按行显示列表内容
# ******************************************
build:
  name: 'unit_test_local_demo'
  type: HiveNetMicro
  source: ~
  output: "../build"
  successTips:
    - "以下操作需进入到localdemo目录下操作"
    - "构建应用: python src/build.py"
    - "测试应用: python test_service.py"

# ******************************************
# dirs: 要创建的文件夹(自定义配置，使用公共的ProcesserBuildDir插件)
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
  ...

# ******************************************
# configTemplates: 配置文件模版生成处理（使用HiveNetMicro的自定义构建插件）
# Item Key: 要复制的配置文件模版名(不包含.yaml后缀)
#   key: 模版文件下的配置key, 如果有多级可以按该结构设置多层, 最末级的值为list, 为对应配置项下要添加的配置模版清单
#     注: key除了可以按结构设置多层以外, 也可以支持yaml_path的模式, 例如 root/key1/key2[0]这种形式
#     - 配置项参数字典
#       template: str, 配置的模版文件名(不包含.yaml后缀)
#       remplate_path: str, 选填, 配置的模版文件路径, 如果不设置代表按配置层级路径获取, 该路径为编译器模版路径的相对路径
#       config_name: str, 选填, 配置项的key标识, 如果不设置代表直接使用模版名
# ******************************************
configTemplates:
  ...

```



## 内置的构建插件（可以直接使用）

### ProcesserBuildDir（目录创建及文件复制）

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

### ProcesserBuildGetSysInfos（获取系统信息并写入上下文）

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


### ProcesserBuildPrint（打印上下文指定信息）

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
