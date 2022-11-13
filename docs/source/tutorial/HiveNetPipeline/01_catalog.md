# HiveNetPipeline使用说明

HiveNetPipeline模块提供一个易于使用的管道执行框架，支持快速实现可配置的数据流处理，例如数据对象的按步处理、工作流等场景。

## HiveNetPipeline的主要概念

- pipeline ：管道控制器，定义管道的执行流程、同步/异步执行方式、执行通知函数等，管道控制器控制管道的每次执行
- sub_pipeline: 子管道控制器，实际上也是一个管道，但通过子管道控制器，可以让一个管道执行子管道，实现执行流程的嵌套
- run_id : 管道运行id，一个管道控制器可以支持执行多个管道任务（可以并发），不同的管道任务通过运行id（run_id）进行区分，管道执行时可以支持送入自定义运行id，也可以由控制器自动生成运行id
- input_data ：输入数据对象，每个管道任务需要指定管道需要处理的输入数据；输入数据建议采用可支持 json 转换的基础变量类型，以支持可在执行过程中将暂停的管道任务保存到 json 格式的检查点中
- output : 输出数据，每个管道执行完成后将输出处理后的数据对象
- node : 管道执行节点，定义了当前节点的处理器参数，以及获取下一个处理节点的路由器参数配置，多个执行节点形成的管道配置（pipeline_config）可用于控制管道的执行流程
- predealer ：管道预处理器, 每个管道预处理器必须集成预处理器框架 (PipelinePredealer), 预处理器在管道节点运行开始时执行, 可以放入自定义的预处理逻辑; 预处理可以返回True/False控制当前节点继续执行还是跳过, 如果返回True则正常继续执行当前节点, 如果返回False则跳过当前节点的执行(不执行processer和router), 直接跳到下一个相临节点执行(注意, 当前节点的router并不会执行, 所以只会跳到下一个相临节点运行)
- processer ：管道处理器，每个管道处理器必须继承处理器框架（PipelineProcesser），按标准模式对输入数据对象进行处理，并输出结果数据；结果数据可以供下一个管道处理器进行处理，如果是最后一个管道处理器，则结果数据为最后管道任务执行的输出结果
- router : 管道路由器，每个管道路由器必须继承路由器框架（PipelineRouter），管道路由器用于指定管道的下一个处理节点，以支持形成非串型执行的处理工作流
- context : 上下文信息，用于在整个管道任务执行过程中传递共享的信息，可以在开始执行管道任务或执行节点中对上下文信息进行修改
- checkpoint : 管道检查点，可以通过检查点保存当前管道的中间状态，并在后续加载重新执行
- step_by_step ：管道逐步执行，可以在管道执行（start）中通过 is_step_by_step 参数指定管道逐步执行，每执行一步就将管道置为 pause 状态，通过调用 resume 执行下一步
- trace_list {list} - 执行追踪列表，按顺序放入执行信息，每个执行信息包括
  - node_id {str} 节点配置id
  - node_name {str} 节点配置名
  - processor_name {str} 处理器名
  - start_time {str} 开始时间，格式为'%Y-%m-%d %H:%M:%S.%f'
  - end_time {str} 结束时间，格式为'%Y-%m-%d %H:%M:%S.%f'
  - status {str} 执行状态，'S' - 成功，'E' - 出现异常, 'K' - 跳过节点
  - status_msg {str} 状态描述，当异常时送入异常信息
  - router_name : 路由名(直线路由可以不设置路由器)
  - is_sub_pipeline {bool} 是否子管道执行
  - sub_trace_list {list} 子管道执行的trace_list，记录子管道执行记录

## HiveNetPipeline的使用

**1、开发所需的管道处理器（processer）和管道路由器（router）、管道预处理器 (predealer)**

（1）管道处理器开发要点

- 每个处理器需继承 HiveNetPipeline.PipelineProcesser 类或 HiveNetPipeline.SubPipeLineProcesser 类，通过实现 processer_name 函数指定管道处理器的唯一标识名
- 如果处理器使用前需要进行初始化操作，可通过实现 initialize 函数进行初始化，该函数将在加载管道插件时执行且只执行一次
- 实现 execute 函数实现数据输入（input_data）和数据输出（output）的具体处理逻辑
- 如果数据处理耗时较长，可以将处理器设置为异步模式，通过指定 is_asyn 函数返回 True 实现；注意此时 execute 函数应通过线程模式执行处理，并在启动线程后直接返回 None，实际数据处理完成后，通过 pipeline_obj 的 asyn_node_feeback 函数返回执行结果

​     对于子管道处理器（SubPipeLineProcesser），还有以下的开发要点：

- 实现 get_sub_pipeline 函数，根据传入的参数返回所需执行的子管道（Pipeline）实例对象，根据该函数，可以在执行时再生成子管道对象，也可以提前生成后，每次执行的时候由函数取出并返回；**这里需要注意：子管道的异步（is_asyn）模式必须与当前处理器的 is_asyn 函数一致**；
- 如果没有特殊情况，可以不重载 execute 函数；也可以自行实现 execute 函数，控制每次执行子管道的重新开始及恢复执行的机制

​     **注：管道处理器的 processer_name 要求全局唯一，也就是如果加载两个相同名字的处理器，后面一个将会覆盖前一个**

（2）管道路由器开发要点

- 每个路由器需继承 HiveNetPipeline.PipelineRouter 类，通过实现 router_name 函数指定管道路由器的唯一标识名
- 如果路由器使用前需要进行初始化操作，可通过实现 initialize 函数进行初始化，该函数将在加载管道插件时执行且只执行一次
- 实现 get_next 函数实现路由的下一个处理节点判断处理， 如果当前节点是最后一个节点则返回 None（注意： get_next 的 kwargs 参数将传入管道配置 pipeline_config 的 router_para 参数）
- 可以通过 HiveNetPipeline.Tools 的 get_node_id_by_name 函数，通过处理节点名获取对应的id

（3）管道预处理器开发要点

- 每个预处理器需继承 HiveNetPipeline.PipelinePredealer 类，通过实现 predealer_name 函数指定管道预处理器的唯一标识名
- 如果预处理器使用前需要进行初始化操作，可通过实现 initialize 函数进行初始化，该函数将在加载管道插件时执行且只执行一次
- 实现 pre_deal 函数放入自定义的处理逻辑, 该函数的返回值可以控制当前节点是否继续执行: 如果返回True则正常继续执行当前节点, 如果返回False则跳过当前节点的执行(不执行processer和router), 直接跳到下一个相临节点执行(注意, 当前节点的router并不会执行, 所以只会跳到下一个相临节点运行)


**2、加载管道处理器和路由器、预处理器插件**

在创建管道前通过以下函数加载所需的管道处理器和路由器、预处理器插件：

- HiveNetPipeline.Pipeline.add_plugin :  直接装载管道处理器或路由器、预处理器的类对象
- HiveNetPipeline.Pipeline.load_plugins_by_file : 通过装载python文件的方式装载文件中的处理器及路由器、预处理器类对象
- HiveNetPipeline.Pipeline.load_plugins_by_path : 通过指定目录装载目录下python文件的方式装载文件中的处理器及路由器、预处理器类对象
- HiveNetPipeline.Pipeline.load_plugins_embed : 加载内嵌管道处理器和路由器、预处理器插件

**3、设置管道配置字典/json**

管道配置可以理解为管道的工作流配置，支持字典（dict）和json字符串两种类型，示例如下：

```
{
    "1": {
        "name": "节点配置名",
        "predealer": "预处理器名",
        "predealer_execute_para": {},
        "processor": "处理器名",
        "processor_execute_para": {},
        "is_sub_pipeline": False,
        "sub_pipeline_para": {},
        "context": {},
        "router": "",
        "router_para": {},
        "exception_router": "",
        "exception_router_para": {}
    },
    "2": {
        ...
    },
    ...
}
```

通过管道配置的路由器和异常路由器的插件扩展和设置，可以实现复杂的管道执行工作流。

需要注意的要点如下：

- 字典中的 key 为处理节点id，必须定义为从 “1” 开始的连续数字，且数字不能出现重复和断开的情况
- 预处理器 (predealer) 为选填, 指定该处理节点所使用的管道预处理器(在执行管道处理器前会先执行, 执行结果可以控制是否跳过当前节点的执行)
- 预处理器执行参数(predealer_execute_para)为选填, 指定执行预处理器时送入的kwargs扩展参数
- 处理器名（processor）为必填，指定该处理节点所使用的管道处理器
- 处理器执行参数(processor_execute_para)为选填, 指定执行处理器时送入的kwargs扩展参数
- 是否子管道处理器（is_sub_pipeline）为选填，如果指定为True，则执行对应的子管道任务
- 子管道参数（sub_pipeline_para）为选填，为生成子管道的参数，按具体的子管道处理器定义
- 节点配置名（name）为选填，可以设置为唯一的名字，便于处理路由通过名字唯一定位到处理节点id
- 更新上下文（context）为选填，如果传值，则在执行处理器前会通过该上下文更新（update）管道任务的整体上下文
- 路由器名（router）为选填，如果不传值代表节点运行完成后，直接运行下一个相临节点；如果传值则在运行后通过执行路由器找到下一个运行的节点
- 路由器执行参数（router_para）为选填，将作为 **kwargs 参数在路由器执行时传入
- 异常路由器名（exception_router）为选填，如果设置有值，则当处理器执行出现异常时，通过异常路由器来找到下一个运行的节点
- 异常路由器执行参数（exception_router_para）为选填，将作为 **kwargs 参数在异常路由器执行时传入

**4、创建管道控制器（Pipeline）**

使用上一步的管道配置，创建管道实例：

```
_pl = HiveNetPipeline.Pipeline(
    'my pipeline', _pipeline_config, ……
)
```

- 可以通过参数 is_asyn 指定管道是否异步管道（执行函数同步返回结果，还是异步返回）
- 通过参数 asyn_notify_fun 指定异步执行完成后的主动通知函数
- 通过参数 running_notify_fun、end_running_notify_fun 指定节点运行的通知函数，可以用于显示执行过程

**5、运行管道任务**

同步执行模式，函数执行完直接返回管道结果：

```
_run_id, _status, _output = _pl.start(input_data=_input_data)
```

异步执行模式，可以在管道执行完成后查询最后的输出结果：

```
# 异步执行，获取运行id
_run_id = _pl.start(input_data=_input_data)
# 等待执行完成
while _pl.status(run_id=_run_id) not in ['success', 'exception']:
    time.sleep(0.01)
# 获取执行结果
_output = _pl.output(run_id=_run_id)
```

## 管道执行控制

**1、暂停管道执行**

对于异步执行的管道任务，可以在执行过程中暂停执行，通过以下函数：

```
_pl.pause(_run_id)
```

**2、恢复管道执行**

对于暂停、异常中止的管道任务，可以通过以下函数恢复管道的执行：

```
_pl.resume(_run_id)
```

此外对于暂停或已完成的管道任务，可以通过start函数重新从头开始执行：

```
_run_id = _pl.start(input_data=_input_data, run_id=_run_id)
```

**3、删除已完成的管道状态数据**

如果管道有很多执行的管道任务，将占用大量内存保存管道任务的执行记录，可以通过以下方法删除已无用的管道任务数据：

```
_pl.remove(_run_id)
```

**4、保存管道任务执行中间件状态**

在管道任务在非执行的情况下，可以通过以下命令将管道任务状态保存为json字符串，应用可以存储到文件中用于后续恢复执行，但要注意，如果要支持必须保障管道任务的input_data和处理器的output对象均可支持json转换：

```
_json_str = _pl.save_checkpoint(_run_id)
```

注：也可以不传入 run_id，这将保存所有管道任务的状态

**5、装载管道任务执行状态**

可以将管道任务执行状态装载回一个新创建的管道中（注意配置需一样），然后通过resume重新执行中断的管道任务：

```
_pl.load_checkpoint(_json_str)
```

**6、控制任务逐步执行**

在启动任务的时候（start）可以指定任务逐步执行（is_step_by_step 参数设置为True），这样管道将执行一步就将管道置为暂停（同时也会支持子管道的任务按步暂停），便于自行控制管道任务执行节奏。



## 内嵌的管道处理器和路由器、预处理器插件介绍

### 管道预处理器

- ConditionPredealer : 条件判断预处理器, 该预处理器可通过 predealer_execute_para 配置项送入conditions条件参数, 条件参数执行返回True/False可控制是否跳过当前节点的执行

### 管道处理器

- Null ：空处理器，不做任何处理


### 管道路由器

- GoToNode ：指定节点跳转路由器，可根据上下文或路由器参数进行跳转；优先根据上下文参数判断要跳转的节点，该参数可以由对应节点的处理器主动写入，goto_node_id - 要跳转到的节点id，goto_node_name - 要跳转到的节点名；如果上下文找不到跳转参数，则从路由器参数判断要跳转的节点，参数命名与上下文一致

- IfGotoNode ：指定节点按条件跳转路由器, 可根据上下文或路由器参数进行条件跳转；优先根据上下文参数判断要跳转的节点，该参数可以由对应节点的处理器主动写入，如果上下文找不到跳转参数，则从路由器参数判断要跳转的节点，参数命名与上下文一致; 具体支持的参数参考路由器的get_next函数注释
