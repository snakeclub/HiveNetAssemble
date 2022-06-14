# HiveNetSimpleSanic总览

HiveNetSimpleSanic是HiveNetAssemble提供的对Sanic的封装, 简化基于Sanic构建Restful Api的复杂度。



## 安装方法

### 源码方式安装

- HiveNetSimpleSanic库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetSimpleSanic


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetSimpleSanic-0.1.0-py3-none-any.whl




## 库模块大纲

### server

server模块提供ServerBaseFW服务框的Sanic实现类SanicServer，可基于该实现类快速构建高性能的Restful Api服务。此外该模块也提供了一个SanicTool工具类，对Sanic原生服务对象提供了简单的路由添加和返回值格式化处理的相关工具函数。

### auth

auth模块提供了IPAuth和AppKeyAuth的两个鉴权框架的Sanic实现，可以便捷地实现SanicServer处理函数的IP和AppKey模式鉴权处理。




## SanicServer使用说明

### 简单使用方法

```
from sanic.response import text as sanic_text, json as sanic_json
from HiveNetCore.utils.run_tool import AsyncTools
from HiveNetSimpleSanic.server import SanicTool, SanicServer
from HiveNetSimpleSanic.auth import IPAuthSanic

# 步骤1:
# 定义处理函数, 处理函数传入的第一个参数固定为sanic.request.Request对象
# 处理函数的返回结果必须为sanic.response.HTTPResponse对象，可以通过sanic_text或sanic_json进行转换
def deal_fun_1(request):
	"""
	无函数参数的处理函数
	"""
	print(request.json)  # 打印http送入的json信息
	return sanic_text("run deal_fun_1")  # 返回字符串格式返回值

# 函数参数将传入路由url指定位置的<xxx>形式的值, 如果添加服务时使用with_para参数, 则使用定义指定的methods参数
def deal_fun_2(request, arg1: str, arg2: int, methods=['POST']):
  """
  带函数参数的处理函数
  """
  print(arg1, arg2)  # 打印传入的参数
  return sanic_json({'func_name': 'deal_fun_2'})  # 返回json格式的返回值

# 利用SanicTool支持通用python对象直接返回
@SanicTool.support_object_resp
def deal_fun_3(request):
  """
  通用python对象直接返回
  """
  return {'func_name': 'deal_fun_3'}
  
# 使用鉴权
@SanicTool.support_object_resp
@SanicServer.auth_required_static(auth_name='IPAuth', app_name='demo_server')
def deal_fun_4(request):
  """
  通用python对象直接返回
  """
  return {'func_name': 'deal_fun_4'}
  
# 步骤2:
# 定义生命周期函数, 这里示例只定义before_server_start
def before_server_start(server_obj):
   print('before server start')
  
# 步骤3:
# 初始化鉴权实例对象(如果无需鉴权功能可不忽略)
_ip_auth = IPAuthSanic(
    init_blacklist=['127.0.*.*']
)

# 步骤4:
# 初始化服务对象, 注意app_name必须与鉴权修饰符的一致, 指定生命周期执行函数
_server = SanicServer(
	'demo_server', server_config={
        'run_config': {
            'debug': True,
            'host': '0.0.0.0',
            'port': 5002,
            'workers': 2,
            'access_log': True
        },
        'run_in_thread': False
    },
    support_auths={
        'IPAuth': _ip_auth
    },
    before_server_start=before_server_start
)

# 步骤5:
# 添加服务处理函数, 注意为异步函数, 需要用await调用
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun_1', deal_fun_1, methods=['GET', 'POST'])  # 指定路由支持的方法
)

# 指定通过路由函数入参生成路由，因此会使用函数的methods入参, 另外路由也会根据入参定义进行调整
# 真实uri为'/deal_fun_2/<arg1: str>/<arg2: int>'
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun_2', deal_fun_1, with_para=True)
)

# 默认支持方法为['GET']
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun_3', deal_fun_3)
)
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun_3', deal_fun_4)
)


# 步骤6:
# 启动服务, 可以使用阻塞线程的模式，通过ctrl+c停止服务
AsyncTools.sync_run_coroutine(
	_server.start(is_asyn=True)
)
```



### asgi服务模式启动

原生的Sanic支持通过asgi第三方Web容器方式启动，这里同意也支持，您可以使用daphne、uvicorn、hypercorn、Gunicorn等第三方asgi服务管理SanicServer，需要注意的操作如下：

1、初始化参数的server_config要指定use_asgi=True；

2、不要调用start方法进行启动；

3、指定asgi管理对象为初始化后的_server.native_app



### 特殊说明

1、由于Sanic不支持进程内关闭服务，因此SanicServer同样不支持stop方法；

2、server_config的run_in_thread参数指定是否通过线程启动，只有线程启动模式支持start的异步方式（不阻塞线程）；但线程启动模式只能支持一个worker，不支持多worker并发；
