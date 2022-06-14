# HiveNetSimpleFlask总览

HiveNetSimpleFlask是HiveNetAssemble提供的对Flask的封装, 简化基于Flask构建Restful Api的复杂度。


## 安装方法

### 源码方式安装

- HiveNetSimpleFlask库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetSimpleFlask


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetSimpleFlask-0.1.0-py3-none-any.whl




## 库模块大纲

### server

server模块提供ServerBaseFW服务框的Flask实现类FlaskServer，可基于该实现类快速构建高性能的Restful Api服务。此外该模块也提供了一个FlaskTool工具类，对Sanic原生服务对象提供了简单的路由添加和返回值格式化处理的相关工具函数。

另外该模块基于FlaskServer扩展了socketio的实现类SocketIOServer，可以基于该实现了快速构建socketio服务。

### auth

auth模块提供了IPAuth和AppKeyAuth的两个鉴权框架的Flask实现，可以便捷地实现FlaskServer处理函数的IP和AppKey模式鉴权处理。

### client

client模块提供ClientBaseFw服务框架的socketio客户端实现类SocketIOClient，可使用该客户端类进行socketio的处理。




## FlaskServer使用说明

### 服务端参考示例

```
from flask import jsonify, request as flask_request
from HiveNetSimpleFlask.server import FlaskTool, FlaskServer
from HiveNetSimpleFlask.auth import IPAuthFlask

# 步骤1:
# 定义处理函数, 请求参数可通过flask.request对象获取
# 返回值可以支持两种形式:
# 1、Response对象, 如果返回为str对象, 将自动通过Response('str')转换为该对象; 如果是其他对象, 可以通过flask.jsonify转换
# 2、返回三元组(data: str|Response, status_code: int, headers: dict), 例如("", 200, {"ContentType":"application/json"})
def deal_fun_1():
	"""
	无函数参数的处理函数
	"""
	print(flask_request.json)  # 打印http送入的json信息
	return "run deal_fun_1"  # 返回字符串格式返回值

# 函数参数将传入路由url指定位置的<xxx>形式的值, 如果添加服务时使用with_para参数, 则使用定义指定的methods参数
def deal_fun_2(arg1: str, arg2: int, methods=['POST']):
  """
  带函数参数的处理函数
  """
  print(arg1, arg2)  # 打印传入的参数
  return jsonify({'func_name': 'deal_fun_2'})  # 返回json格式的返回值

# 利用FlaskTool支持通用python对象直接返回
@FlaskTool.support_object_resp
def deal_fun_3():
  """
  通用python对象直接返回
  """
  return {'func_name': 'deal_fun_3'}

# 使用鉴权
@FlaskTool.support_object_resp
@FlaskServer.auth_required_static(auth_name='IPAuth', app_name='demo_server')
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
_ip_auth = IPAuthFlask(
    init_blacklist=['127.0.*.*']
)

# 步骤4:
# 初始化服务对象, 注意app_name必须与鉴权修饰符的一致, 指定生命周期执行函数
_server = FlaskServer(
	 'demo_server', server_config={
        'debug': True,
        'flask_run': {
            'host': '127.0.0.1', 'port': 5000
        },
    },
    support_auths={
        'IPAuth': _ip_auth
    },
    before_server_start=before_server_start
)

# 步骤5:
# 添加服务处理函数
_server.add_service('/deal_fun_1', deal_fun_1, methods=['GET', 'POST'])  # 指定路由支持的方法

# 指定通过路由函数入参生成路由，因此会使用函数的methods入参, 另外路由也会根据入参定义进行调整
# 真实uri为'/deal_fun_2/<arg1>/<arg2>'
_server.add_service('/deal_fun_2', deal_fun_1, with_para=True)

# 默认支持方法为['GET']
_server.add_service('/deal_fun_3', deal_fun_3)
_server.add_service('/deal_fun_3', deal_fun_4)


# 步骤6:
# 启动服务, 可以使用阻塞线程的模式，通过ctrl+c停止服务
_server.start(is_asyn=True)
```

### 客户端参考示例

可以直接使用HiveNetWebUtils.client模块的HttpClient或AIOHttpClient作为http客户端进行连接处理，参考代码如下：

```
from HiveNetWebUtils.client import HttpClient

# 连接客户端
with HttpClient({
    'conn_str': 'http://127.0.0.1:5000/'
}) as _client:
	_url = '/deal_fun_2/test/10'
	_result = _http_client.call(_url)
	if _result.is_success():
		print(_result.resp['data'])  # 返回的数据
```



## SocketIOServer使用说明

socketio是双向长连接，服务端和客户端之间连接后可以通过事件（event）发送不同的消息，服务端和客户端都可以发送和监听消息，并设置不同消息的处理函数。

### 服务端参考示例

```
from HiveNetSimpleFlask.server import SocketIOServer


# 步骤1: 定义服务端事件处理函数
# 函数格式如下: func(request: dict) -> dict
# 送入的request字典格式为:
#   {
#     'id': '', # 事件请求id
#     'service_uri': '', # 请求服务uri
#     'data': ... # 请求数据对象
#   }
# 可以直接返回支持json转换的原生python对象反馈到客户端
# 注1: 如果返回的对象是iter, 则客户端也可以以iter方式处理返回值
# 注2: 处理函数内部可以通过emit或broadcast函数进行向客户端推送其他事件(非当前请求的响应事件)
def main_resp_service(request: dict) -> dict:
    """
    直接返回收到的信息
    """
    print('dict_service get: %s' % str(request))
    return request['data']

# 返回迭代对象的服务处理函数
def main_iter_service(request: dict):
    """
    返回迭代数据
    """
    print('main_iter_service get: %s' % str(request))
    for _item in request['data']:
        yield _item

# 步骤2: 初始化服务对象
_server = SocketIOServer(
    'test_sio_server', server_config={
        'debug': True,
        'flask_run': {
            'host': '127.0.0.1', 'port': 5001
        },
        'service_namespace': ['/test', '/prd']
    }
)

# 步骤3: 添加服务处理函数
_server.add_service(
    'main_resp_service', main_resp_service, namespace='/test'
)
_server.add_service(
    'main_iter_service', main_iter_service, namespace='/test'
)

# 步骤4: 启动服务
_result = _server.start(is_asyn=True)
if not _result.is_success():
    raise RuntimeError('start server error: %s' % str(_result))
```

### 客户端参考示例

```
from HiveNetSimpleFlask.client import SocketIOClient


# 连接客户端
with SocketIOClient({
    'url': 'http://127.0.0.1:5001',
    'is_native_mode': False,
    'service_namespace': ['/test', '/prd']
}) as _client:
		# 客户端发送请求字典数据
    _except = {'a': 'val_a', 'b': 'val_b'}
    _result = _client.call(
        'main_resp_service', _except, namespace='/test'
    )
    if _result.is_success():
			  print(_result.resp)  # 返回的数据
	 
	 # 迭代模式
	 _except = ['a', 'b', 'c', 'd']
   _result = _client.call(
       'main_iter_service', _except, namespace='/test'
   )
   if _result.is_success():
       for _item in _result.resp:
            print(_item)  # 返回的迭代对象
```

### 服务端特殊说明

#### 服务初始化特殊参数

- **server_config > is_native_mode**

​        是否使用原生模式, 默认为False

​        如果使用原生模式，需自行通过bind_on_event函数进行处理事件的绑定，并且无法通过add_service来绑定处理事件；默认的非原生模式，对事件绑定进行了封装处理，可以类似FlaskServer一样直接通过service_uri来匹配处理函数并进行执行。

- **server_config > service_event**

​        指定服务模式的事件标识, 默认为'socketio_service'。可以通过修改该参数，来自定义service处理的事件标识字符串（事件名）。

- **server_config > service_namespace**

​        指定服务模式对应的命名空间, 默认为None(全局命名空间)，如果传入的类型是list, 则会在清单中的命名空间都进行服务事件的注册。

​        注意socketio的服务通过命名空间进行隔离，通过该参数可以指定服务所支持的命名空间清单，如果命名空间不在该清单中，则该命名空间下将无法正常进行服务的处理。

#### broadcast和emit函数

在服务端处理函数里可以直接使用broadcast和emit向客户端发送消息，如果是broadcast代表向所有的连接客户端广播消息，而emit则代表仅向当前连接发送消息。



### 客户端特殊说明

#### 客户端初始化特殊参数

- **is_native_mode、service_event、service_namespace**

​        这三个参数必须与服务端保持一致。

- **namespaces**

​        指定要连接的命名空间, 如果不传则只会连接已经注册了事件的命名空间，没有连接的命名空间说明无法触发对应命名空间下的事件处理函数。
