# HiveNetBuildTool - 创建自定义构建工具的步骤

## 主要步骤说明

您可以基于HiveNetBuildTool创建自定义的构建步骤，参考步骤如下：

### 1、创建自定义构建工具的基础目录（用于放置自定义构建相关配置和文件），例如:

```
MyBuildTool : 自定义构建工具
  |__plugins : 可选, 该目录下放置自定义的构建管道插件
  |__build_pipeline.yaml : 必须，自定义构建管道配置(定义构建步骤)
  |__config.yaml : 必须，自定义构建工具配置

Build : 构建工具实例
  |__src : 可选，放置源码或其他信息，目录名，目录数量由构建工具自定义
  |__build.yaml : 必须, 构建配置
  |__build.py : 可选, 构建脚本, 也可以不使用脚本，而是自己通过代码方式进行构建
```

### 2、开发自定义构建管道插件

自定义管道插件必须继承`HiveNetPipeline.PipelineProcesser`类，实现该类的`processer_name`和`execute`两个方法。

完成开发的自定义管道插件请放置在`plugins`目录下，由框架进行加载。

需要注意的点包括:

(1) `processer_name` 返回当前处理器名称，建议与实现类的类名一致；

(2) `execute` 是管道执行方法，也就是当前节点的构建处理方法，可以通过入参的`context`上下文获取配置信息，推荐的获取方式如下:

```python
from HiveNetPipeline import PipelineProcesser

class ProcesserBuildConfigTemplates(PipelineProcesser):

    @classmethod
    def processer_name(cls) -> str:
        return 'ProcesserBuildConfigTemplates'

    @classmethod
    def execute(cls, input_data, context: dict, pipeline_obj, run_id: str):
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

注: context初始化的信息包括:

- build_type_config: config.yaml配置文件中对应构建类型(type)的具体配置
- base_path: 自定义构建工具目录
- cmd_opts: 传入的命令行key-value参数
- build: build.yaml配置文件的build(构建参数)配置信息, 注意type、source、output这3个配置，如果cmd_opts有设置则会以cmd_opts中的配置为准
- build_config: build.yaml配置文件


### 3、编写build_pipeline.yaml管道配置文件

按照实际构建的顺序要求编写build_pipeline.yaml管道配置文件，该配置文件必须为yaml格式，配置内容要求与HiveNetPipeline的管道配置要求一致。

### 4、编写config.yaml配置文件

在config.yaml配置文件中指定构建类型，以及自定义管道插件所在目录(plugins)和管道配置文件(pipeline),

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
```

### 5、在真正的构建实例目录下创建build.yaml构建配置文件

build.yaml包含了真正进行构建的具体参数配置。

### 7、创建构建脚本

参考脚本如下:

```python
from HiveNetBuildTool.build import BuildPipeline

if __name__ == '__main__':
  # 初始化构建管道对象
    _pipeline = BuildPipeline(
        '/MyBuildTool', config_file='config.yaml', build_file='build.yaml',
        cmd_opts={'source': './源码目录', 'output': './输出目录'}
    )

    # 启动构建
    _pipeline.start_build()

```
