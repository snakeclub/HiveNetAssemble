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

## 整体设计说明

### 整体设计

`HiveNetBuildTool.build.BuildPipeline`是构建工具的核心，该类初始化会构建Pipeline对象，并通过start_build执行构建的管道实现构建。

自定义构建工具的整体目录结构如下:

```
HiveNetBuildTool (内置目录)
  |__plugins （内置管道插件目录）
  |__extend_para.yaml （内置管道插件的扩展参数配置）

SelfBuildTool (base_path, 自定义构建工具目录)
  |__plugins (可选, 自定义管道插件目录)
  |__config.yaml  (必须, config_file, 自定义构建工具配置)
  |__build_pipeline.yaml  (必须, 自定义构建工具管道配置)
  |__extend_para.yaml (可选, 自定义管道插件的扩展参数配置)

BuildDemo (自定义构建实例 - 一个构建工具可以支持多个构建实例)
  |__build.yaml (必需, build_file, 构建文件, 配置当前实例的构建具体参数)
  |__build.py (可选, 构建脚本, 用于简化初始化BuildPipeline实例并执行start_build的方法)

```

主体流程:

1、从config.yaml中获取build_pipeline.yaml的路径，加载管道配置；

2、按build_pipeline.yaml中的管道顺序执行每个节点的处理, 节点配置的processor指定当前节点使用的管道插件；

3、管道插件从context中获取各类信息并进行构建处理，在处理过程中可以同步修改context的内容；context初始化的信息包括:

- build_type_config: config.yaml配置文件中对应构建类型(type)的具体配置
- base_path: 自定义构建工具目录
- cmd_opts: 传入的命令行key-value参数
- build: build.yaml配置文件的build(构建参数)配置信息, 注意type、source、output这3个配置，如果cmd_opts有设置则会以cmd_opts中的配置为准
- build_config: build.yaml配置文件

### 关键配置文件说明

#### config.yaml

config.yaml是自定义构建工具配置, 正常情况可以直接放在自定义构建工具目录的根路径下。该配置可以定义不同构建类型构建工具配置，包括自定义插件目录、构建管道（Pipeline）的配置文件，以及自定义的构建参数，参考如下:

```yaml
# ******************************************
# 构建工具配置(支持配置多个不同的构建类型)
# Item Key: 构建类型标识(type)
#   plugins: str|list, 该构建类型的自有管道插件目录(构建工具目录的相对路径)
#     注: 如果为str代表指定1个路径, 如果是list则通过数组形式指定多个管道插件目录
#   pipeline: str, 构建管道配置文件(构建工具目录的相对路径)
#   selfConfig: dict, 不同类型构建工具的自有配置参数
# ******************************************
SeflBuildTool:
  plugins: plugins
  pipeline: build_pipeline.yaml
  selfConfig:

MyBuildTool:
  ...
```

#### build_pipeline.yaml

build_pipeline.yaml是自定义构建工具管道配置，针对不同的构建类型，可以创建多个不同的build_pipeline.yaml文件，构建类型和构建工具管道配置的对应在config.yaml中指定。

该配置文件配置的是管道执行中不同节点的配置，定义与HiveNetPipeline的管道定义一致，只是增加了`tips`，用于在构建节点开始和完成进行提示信息打印。

示例如下:

```yaml
# 构建管道配置
# ******************************************
# name: 节点配置名, 为选填，可以设置为唯一的名字，便于处理路由通过名字唯一定位到处理节点id
# tips: 节点构建提示信息，为选填
# predealer: 预处理器, 为选填, 指定该处理节点所使用的管道预处理器(在执行管道处理器前会先执行, 执行结果可以控制是否跳过当前节点的执行)
# predealer_execute_para: 预处理器执行参数, 为选填, 指定执行预处理器时送入的kwargs扩展参数
# processor: 处理器名, 为必填，指定该处理节点所使用的管道处理器
# processor_execute_para: 处理器执行参数, 为选填, 指定执行处理器时送入的kwargs扩展参数
# is_sub_pipeline: 是否子管道处理器, 为选填，如果指定为True，则执行对应的子管道任务
# sub_pipeline_para: 子管道参数, 为选填，为生成子管道的参数，按具体的子管道处理器定义
# context: 更新上下文, 为选填，如果传值，则在执行处理器前会通过该上下文更新（update）管道任务的整体上下文
# router: 路由器名, 为选填，如果不传值代表节点运行完成后，直接运行下一个相临节点；如果传值则在运行后通过执行路由器找到下一个运行的节点
# router_para: 路由器执行参数, 为选填，将作为 **kwargs 参数在路由器执行时传入
# exception_router: 异常路由器名, 为选填，如果设置有值，则当处理器执行出现异常时，通过异常路由器来找到下一个运行的节点
# exception_router_para: 异常路由器执行参数, 为选填，将作为 **kwargs 参数在异常路由器执行时传入
# ******************************************
"1":
  name: BuildDirs
  tips: 构建应用文件夹（使用框架自带的构建插件）
  processor: ProcesserBuildDir  # 管道插件处理器标识
  context:
    current_key: dirs  # 设置上下文, 指定该节点的配置标识

"2":
  name: RunDemo
  tips: 示例处理（使用自定义的构建插件）
  processor: ProcesserBuildDemo
  context:
    current_key: demoKey
...
```

**注1: 大部分构建管道处理器都会从`context > current_key`获取当前节点的配置标识，以获取build.yaml中的具体配置信息，建议统一遵循该规则。**

**注2: 管道配置完全兼容HiveNetPipeline的用法，因此也可以配置router来实现不同条件的执行顺序跳转，例如可以设置内置的GoToNode路由器，并在构建组件中设置上下文的`goto_node_id`或`goto_node_name`来指定跳转**

#### extend_para.yaml

extend_para.yaml是管道插件扩展配置信息，必须直接放在自定义构建工具目录的根路径下，才能正常加载使用。

该配置中的信息将会加载到全局变量`BUILD_PROCESSER_EXTEND_PARA`中，可以通过`BuildPipeline.get_processer_extend_para`工具函数获取指定的参数值。

```yaml
# ******************************************
# 构建处理插件扩展参数
# Item Key: 扩展插件名(processer_name)
#   ... # 插件的参数
# ******************************************
ProcesserBuildGetSysInfos:
  # ******************************************
  # 获取系统信息参数配置
  # Item Key: 信息类型标识
  #   getKey: 获取参数的key, 如果不设置代表直接使用参数类型标识
  #   func: 已加载后的处理函数对象, 加载过一次以后可以直接使用, 正常情况下不需要配置
  #   libConfig:  要加载函数的配置
  #       path: str, 文件路径或加载模块的指定搜索路径(当前工作目录下的相对路径)
  #       module_name: str, 指定要加载的模块名, 如果path包含完整文件名可以不设置
  #       class: str, 插件入口类名
  #       function: str, 指定要获取的函数名
  #       instantiation: bool, 是否要初始化类(缓存实例), 默认为False
  #       init_args {list} - 类实例的初始化固定参数, 以*args方式传入
  #       init_kwargs {dict} - 类实例的初始化kv参数, 以*kwargs方式传入
  # ******************************************
  platform:
    # 获取操作系统信息
    libConfig:
      module_name: HiveNetCore.utils.run_tool
      class: RunTool
      function: platform_info
```

#### build.yaml

build.yaml是构建某个特定应用的具体配置，里面放置不同构建节点的具体参数（格式由构建管道插件定义）。

构建工具可以基于构建配置文件生成最终的应用，构建配置文件需按照构建工具的要求，以及构建插件格式要求进行配置，主要的配置和说明参考如下：

```yaml
# 自定义构建配置文件示例
# ******************************************
# build: 构建参数（通用配置）
#   name: 当前构建的标识(仅用于区分不同构建配置)
#   type: 构建类型, 指定为HiveNetMicro
#   source: str, 构建源文件目录, 为当前构建配置文件所在目录的相对目录
#   output: str, 构建结果输出目录, 为当前构建配置文件所在目录的相对目录
#   successTips: list, 构建成功后的提示内容, 按行显示列表内容
# ******************************************
build:
  name: 'demo'
  type: SeflBuildTool
  source: ~
  output: "../build"
  successTips:
    - "成功构建"
    - "提示信息"

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
    clear: true  # 自动创建config目录

...
```

## 创建自定义构建工具的步骤

具体可参考：[《创建自定义构建工具的步骤》](02_self_define_build_tool.md)


## 内置的构建插件

具体可参考：[《内置的构建插件》](02_self_define_build_tool.md)