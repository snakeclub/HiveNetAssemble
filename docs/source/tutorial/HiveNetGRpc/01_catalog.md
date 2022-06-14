# HiveNetGRpc总览

HiveNetGRpc是HiveNetAssemble提供的gRpc的封装, 可以简单实现兼容 HiveNetWebUtils.server.ServerBaseFW 和 HiveNetWebUtils.client.ClientBaseFw 的服务器和客户端功能。


## 安装方法

### 源码方式安装

- HiveNetGRpc库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetGRpc


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetGRpc-0.1.0-py3-none-any.whl




## 库模块大纲

### server

server模块提供ServerBaseFW服务框的gPpc实现类GRpcServer和AIOGRpcServer(异步IO模式)，可基于该实现类快速构建gRpc服务。

注意：AIOGRpcServer是新的特性，隐含了一些异步的bug（表面看不影响程序处理，只是会打印一些错误），如果对异步IO没有要求建议直接使用GRpcServer。

### client

client模块提供ClientBaseFw客户端连接框架的gRpc实现类AIOGRpcClient(异步IO模式)和GRpcClient，以及支持AIOConnectionPool连接池应用的PoolConnectionFW连接池对象实现类GRpcPoolConnection。

### tool

tool模块提供GRpcTool工具类，支持一些常用的gRpc信息提取及处理。

### proto

proto包提供HiveNetGRpc默认支持的消息定义，包括：

- msg_json (JsonService) - 支持json信息收发的消息定义
- msg_bytes (BytesService) - 支持bytes信息收发的消息定义

### msg_formater

msg_formater模块提供HiveNetGRpc默认支持消息格式化处理类，包括：

- RemoteCallFormater - 远程调用函数的消息格式化类，该类基于默认的JsonService报文格式进行处理，可以便捷地实现客户端通过gRpc方式对远程服务端函数的调用。




## HiveNetGRpc使用说明

### 原生使用模式

该模式大部分处理需使用gRpc原生对象，可以根据自己的需要进行更灵活的扩展。

#### 1、自定义gRpc的消息格式（protobuf）

您可以直接使用HiveNetGRpc默认支持的msg_json和msg_bytes，同样也可以自定义自己所需要的消息格式，操作步骤说明如下：

（1）创建 .proto 文件，例如 msg_test.proto，内容和格式可参考HiveNetGRpc.proto.msg_json.proto，按需要定义RpcRequest、RpcResponse的结构，注意除消息结构以及服务名以外，其他内容中的命名请保持与HiveNetGRpc.proto.msg_json.proto一致，例如：

```
syntax = "proto3";

package HiveNetGRPC;

// 服务名可按需要修改为不同的服务名(注意同一个包中的服务名不要重复)
// rpc名请保证跟示例保持一致, 为标识名称和Service的组合
service TestService {
 rpc GRpcCallSimple (RpcRequest) returns (RpcResponse){};  // 简单调用
 rpc GRpcCallClientSideStream (stream RpcRequest) returns (RpcResponse){};  // 客户端流式
 rpc GRpcCallServerSideStream (RpcRequest) returns (stream RpcResponse){};  // 服务端流式
 rpc GRpcCallBidirectionalStream (stream RpcRequest) returns (stream RpcResponse){};  // 双向数据流模式
 rpc GRpcCallHealthCheck (HealthRequest) returns (HealthResponse){}; // 健康检查
}

// 请求消息结构
message RpcRequest {
  // 可以自定义请求消息结构
  ...
}

// 响应消息结构
message RpcResponse {
  // 可以自定义响应消息结构
  ...
}

// 自定义健康检查的服务
message HealthRequest {
  string service = 1; // 健康监控请求
}

message HealthResponse {
  enum ServingStatus {
    UNKNOWN = 0;
    SERVING = 1;
    NOT_SERVING = 2;
    SERVICE_UNKNOWN = 3;
  }
  ServingStatus status = 1;
}
```

（2）编译.proto文件

命令行进入.proto所在的目录，执行以下命令进行编译：

```
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. test_json.proto
```

编译后将生成test_json_pb2.py、msg_json_pb2_grpc.py两个文件。

**注意：编译前需使用pip安装grpcio-tools和googleapis-common-protos**

（3）修改test_json_pb2_grpc.py文件，增加上库路径指定 test_json_pb2 对象引入

```
import sys
import os
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import xxx.msg_json_pb2 as msg__json__pb2
```

#### 2、自定义服务管理类（Servicer）

服务管理类Servicer实现的功能包括管理请求处理函数路由和为gRpc提供标准接入接口，HiveNetGRpc已实现了通用的服务管类GRpcServicer(与GRpcServer配套使用)和AIOGRpcServicer(与AIOGRpcServer配套使用)，如果需要自定义服务管理的逻辑（例如改变处理函数的入参和出参格式，以及增加获取到请求的自定义处理逻辑等），则可参考GRpcServicer或AIOGRpcServicer来实现自己的服务管理类（公开函数的接口需要保持一致）。

注意：GRpcServicer、AIOGRpcServicer必须与服务器类GRpcServicer、AIOGRpcServer配套使用，如果将AIOGRpcServicer用于GRpcServicer将无法正常处理。

#### 3、开发服务端请求处理函数

开发服务端请求的处理函数，函数位置可以在模块中，也可以是类的静态函数或实例成员函数，同时函数也可以是异步IO函数。例如：

```
def deal_func(request: dict) -> msg_test_pb2.RpcResponse:
	"""服务端处理函数"""
	# 自定义的处理逻辑
	...
	
	# 返回响应对象 RpcResponse
	...
```

注意，处理函数的入参和出参是需要根据不同的服务管理类（Servicer）进行定义，如果使用默认的GRpcServicer，函数定义说明如下：

```
（1）函数入参固定为 func(request):
    request为请求字典，说明如下:
    {
        'request': xxx_pb2.RpcRequest/xxx_pb2.RpcRequest迭代器,  # 请求报文对象, 如果是流模式则为请求报文对象的迭代器
        'context': context,  # 请求服务端上下文, grpc.ServicerContext
        'call_mode': call_mode  # 调用模式，具体见 HiveNetGRpc.enum.EnumCallMode
    }
    注意: 如果call_mode为ClientSideStream或BidirectionalStream，客户端通过流方式发送数据，则请求对象为迭代器，可以通过 __anext__()来逐个进行获取，参考代码如下：
    while True:
        try:
        	  # 逐个获取客户端发送过来的请求
            _item: xxx_pb2.RpcRequest = AsyncTools.sync_run_coroutine(
                request_iter.__anext__()
            )
            # 处理逻辑
            ...
        except StopAsyncIteration:
            break
    
（2）函数的返回值为xxx_pb2.RpcResponse或xxx_pb2.RpcResponse的迭代对象，如果call_mode为ServerSideStream和BidirectionalStream，服务端应通过流方式返回数据，需要返回异步IO的迭代对象，参考处理函数的返回方式如下：
	async def deal_fun(request):
		  # 请求处理逻辑
		  ...
		  # 流方式返回处理结果
		  for xx in xxx:
		  	...
		  	_ret: xxx_pb2.RpcResponse = ...
		  	yield _ret
```

#### 4、gRpc服务端代码

服务端的参考代码如下：

```
# 创建服务管理类的映射字典, key为服务名, value维护服务管理类实例对象, 可以支持送入多个服务管理类
# 如果不需要自定义服务管理类可以不送该参数, 服务端会默认使用JsonService(msg_json格式)和GRpcServicer作为默认的服务管理类
_servicer_mapping = {
	'JsonService': GRpcServicer(...),
	'BytesService': GRpcServicer(...)
}

# 初始化gRpc服务对象
_server = GRpcServer(
  'my_server', server_config={
      'run_config': {
          'host': '127.0.0.1', 'port': 50051, 'workers': 2,
          'enable_health_check': True,
      }
  },
  servicer_mapping=_servicer_mapping
)

# 添加请求处理函数
AsyncTools.sync_run_coroutine(_server.add_service(
   'my_deal_func_uri', deal_func, call_mode=EnumCallMode.Simple, servicer_name='JsonService'
))

# 启动gRpc服务
AsyncTools.sync_run_coroutine(_server.start(is_asyn=False))
```

#### 5、gRpc客户端代码

gRpc客户端可以根据需要使用AIOGRpcClient(异步IO模式)或GRpcClient(同步模式)，参考代码如下：

```
with AIOGRpcClient({
    'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
    'use_sync_client': False, 'timeout': 3
}) as _client:
  _request = xxx_pb2.RpcRequest(
  	xx1='value1', xx2='value2', ...
  )
	_result = AsyncTools.sync_run_coroutine(client.call(
      'my_deal_func_uri', _request, call_mode=EnumCallMode.Simple
  ))
```



### 通过RemoteCallFormater实现函数远程调用

HiveNetGRpc.msg_formater.RemoteCallFormater实现基于json格式传输数据的函数远程调用的服务端和客户端处理支持，可以让您能更便捷地进行gRpc远程应用，使用方法大致说明如下：

**1、服务端通过RemoteCallFormater.format_service对请求处理函数进行修饰**

format_service支持对请求对象和响应对象的格式转换处理，简化函数处理的逻辑，示例如下：

```
@RemoteCallFormater.format_service(with_request=False)
async def service_simple_call_para(a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试简单调用，直接返回传入的参数(数组形式)
    """
    return [a, b, args, c, d, kwargs]


@RemoteCallFormater.format_service(with_request=True)
async def service_client_stream(request, a, b, c=10):
    """
    测试客户端流(数字加总)
    """
    d = 0
    for _item in request['request']:
        d += _item
    return [a, b, c, d]
    
    
@RemoteCallFormater.format_service(with_request=True)
async def service_server_stream_async(request, a, b, *args, c=10, d={'d1': 'd1value'}, **kwargs):
    """
    测试服务端流(异步函数)
    """
    print([a, b, args, c, d, kwargs])
    for i in [1, 2, 3, 4]:
        yield i
```

使用的注意事项如下：

（1）with_request指定入参是否包含gRpc服务原始的请求字典对象，如果为True则在第一个参数送入该请求字典，此时需要处理函数定义对应的入参；

（2）该修饰符可以同时支持流模式和普通模式，如果为客户端流，with_request固定为True（设置了False也没有用），处理函数需要从request['request']中获取对应的迭代对象进行循环处理；

（3）返回值可以支持直接返回python对象（注意需要能转换为json的对象）；如果为服务端流，则需要通过yield方式返回迭代对象。



**2、服务端处理，初始化无需指定servicer_mapping**

参考代码如下：

```
# 初始化gRpc服务对象
_server = GRpcServer(
  'my_server', server_config={
      'run_config': {
          'host': '127.0.0.1', 'port': 50051, 'workers': 2,
          'enable_health_check': True,
      }
  }
)

# 添加请求处理函数，建议service_uri直接为函数名
AsyncTools.sync_run_coroutine(_server.add_service(
   'service_simple_call_para', service_simple_call_para, call_mode=EnumCallMode.Simple
))
AsyncTools.sync_run_coroutine(_server.add_service(
   'service_client_stream', service_client_stream, call_mode=EnumCallMode.ClientSideStream
))
AsyncTools.sync_run_coroutine(_server.add_service(
   'service_server_stream_async', service_server_stream_async, call_mode=EnumCallMode.ServerSideStream
))

# 启动gRpc服务
AsyncTools.sync_run_coroutine(_server.start(is_asyn=False))
```



3、客户端处理，通过RemoteCallFormater工具处理请求和返回值

```
with AIOGRpcClient({
    'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
    'use_sync_client': False, 'timeout': 3
}) as _client:
		# 将远程函数的入参转换为标准请求函数
    _request = RemoteCallFormater.paras_to_grpc_request(
        ['a_val', 'b_val', 'fixed_add1', 'fixed_add2'],
        {
            'c': 14, 'e': 'e_val'
        }
    )
    # 远程调用
    _result = AsyncTools.sync_run_coroutine(_client.call(
        'service_simple_call_para', _request
    ))
    # 将返回值转换为标准的CResult对象，如果成功，_result.resp为对应的返回值
    _result = RemoteCallFormater.format_call_result(_result)
    
    # 客户端流的调用方式
    _request = RemoteCallFormater.paras_to_grpc_request_iter(
        [1, 2, 3, 4],
        ['a_val', 'b_val'],
        {
            'c': 14
        }
    )
    _result = AsyncTools.sync_run_coroutine(client.call(
        'service_client_stream', _request, call_mode=EnumCallMode.ClientSideStream
    ))
    _result = RemoteCallFormater.format_call_result(_result)
```



### 客户端使用连接池管理

客户端支持使用 HiveNetCore.connection_pool.AIOConnectionPool 进行连接池的管理，参考代码如下：

```
_creator = AIOGRpcClient  # 连接创建模块，也可以设置为GRpcClient
_connect_config = {
    'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': True, 'ping_with_health_check': True,
    'use_sync_client': False, 'timeout': 3
}

# 建立连接池
_pool = AIOConnectionPool(
    _creator, GRpcPoolConnection, args=[_connect_config],
    connect_method_name=None, max_size=3, min_size=0, connect_on_init=True,
    get_timeout=1,
    free_idle_time=5, ping_on_get=True, ping_on_back=True, ping_on_idle=True,
    ping_interval=5
)

# 获取一个连接对象
client = AsyncTools.sync_run_coroutine(_pool.connection())

# 通过连接对象执行call等处理
...

# 退回连接对象到连接池
AsyncTools.sync_run_coroutine(client.close())
```



### 使用SSL/TSL进行安全验证

HiveNetGRpc支持通过SSL/TSL进行验证，包括服务端验证和客户端反向验证，参考如下：

**1、证书的生成**

可以通过openssl来进行相关证书的生成，参考命令如下：

```
# 需先生成相应证书文件（域名为localhost）
# --执行前先进入HiveNetGRpc/test_data/路径
# --创建CA根证书（自签名证书）
# --生成rsa私钥文件，使用des3加密文件（密码111111）
# openssl genrsa -passout pass:111111 -des3 -out ca.key 4096
# --通过私钥生成签名证书
# openssl req -passin pass:111111 -new -x509 -days 365 -key ca.key -out ca.crt -subj "/CN=localhost"
#
# --创建服务器证书
# --生成rsa私钥文件
# openssl genrsa -passout pass:111111 -des3 -out server.key 4096
# --通过私钥生成签名证书签名请求文件
# openssl req -passin pass:111111 -new -key server.key -out server.csr -subj "/CN=localhost"
# --由CA根证书签发根据请求文件签发证书
# openssl x509 -req -passin pass:111111 -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt
# --私钥文件由加密转为非加密
# openssl rsa -passin pass:111111 -in server.key -out server.key
#
# --创建客户端证书
# openssl genrsa -passout pass:111111 -des3 -out client.key 4096
# openssl req -passin pass:111111 -new -key client.key -out client.csr -subj "/CN=localhost"
# openssl x509 -passin pass:111111 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out client.crt
# openssl rsa -passin pass:111111 -in client.key -out client.key
#
# --对私钥进行pkcs8编码
# openssl pkcs8 -topk8 -nocrypt -in client.key -out client.pem
# openssl pkcs8 -topk8 -nocrypt -in server.key -out server.pem
```



**2、服务器端单向验证**

服务器端可以验证客户端的证书是否有效，参考代码如下：

```
# 服务端指定证书的参考代码如下：
_server = GRpcServer(
    'server_server_ssl', server_config={
        'run_config': {
            'host': '127.0.0.1', 'port': 50052, 'workers': 2,
            'enable_health_check': True,
            'use_ssl': True,
            'ssl': [{
                'cert': os.path.join(_ca_path, 'server.crt'),
                'key': os.path.join(_ca_path, 'server.pem')
            }]
        }
    }
)

...

# 客户端建立的参数参考如下（注意host必须为域名，使用ip会验证不通过）：
with AIOGRpcClient({
        'host': 'localhost', 'port': 50052, 'ping_on_connect': True, 'ping_with_health_check': True,
        'use_sync_client': False, 'timeout': 3,
        'use_ssl': True, 'root_certificates': os.path.join(self.ca_path, 'server.crt')
}) as _client:
	...
```



**3、双向验证（服务器验证客户端，客户端验证服务器）**

参考代码如下：

```
# 服务端指定证书的参考代码如下：
_server = GRpcServer(
    'server_double_ssl', server_config={
        'run_config': {
            'host': '127.0.0.1', 'port': 50053, 'workers': 2,
            'enable_health_check': True,
            'use_ssl': True,
            'ssl': [{
                'cert': os.path.join(_ca_path, 'server.crt'),
                'key': os.path.join(_ca_path, 'server.pem')
            }],
            'root_certificates': os.path.join(_ca_path, 'client.crt')  # 客户端反向验证的证书指定
        }
    }
)

...

# 客户端建立的参数参考如下（注意host必须为域名，使用ip会验证不通过）：
with AIOGRpcClient({
        'host': 'localhost', 'port': 50053, 'ping_on_connect': True, 'ping_with_health_check': True,
        'use_sync_client': False, 'timeout': 3,
        'use_ssl': True, 
        'root_certificates': os.path.join(self.ca_path, 'server.crt'),  # 客户端反向验证的证书指定
        'ssl': {
            'cert': os.path.join(self.ca_path, 'client.crt'),
            'key': os.path.join(self.ca_path, 'client.pem')
        }
}) as _client:
	...
```

