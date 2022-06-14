# HiveNetFileTransfer总览

HiveNetFileTransfer是HiveNetAssemble提供的文件传输处理框架, 可以基于该框架开发不同的传输协议来实现文件的远程传输处理, 此外该模块也基于HiveNetGRpc实现了gRpc协议的文件传输功能。


## 安装方法

### 源码方式安装

- HiveNetFileTransfer库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetFileTransfer


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetFileTransfer-0.1.0-py3-none-any.whl



注意：HiveNetFileTransfer库基于HiveNetGRpc实现了gRpc协议的远程文件传输功能，如果需要使用该功能，需要安装HiveNetGRpc库，命令如下：pip install HiveNetGRpc




## 库模块大纲

### transfer

文件传输框架的控制模块，提供Transfer类控制传输整体处理过程，通过该类可以进行文件传输的启动、停止处理。

### saver

文件保存模块，提供TransferSaver类进行目标端的文件保存处理相关功能，该类中封装了文件传输过程信息(例如传输了哪些数据块)，以及对目标文件的写入处理。

该模块主要提供给目标端服务实现对文件保存的管理。

### protocol

文件传输协议模块，模块中提供ProtocolFw定义了文件传输的标准框架（提供相关接口给Transfer类调用），需通过集成该框架类实现具体的文件传输协议。

在该模块中还提供LocalProtocol类，实现了本地对本地的文件传输协议（文件复制），可作为实现其他传输协议的参考。

### exceptions

提供框架标准的异常类。

### extend_protocol

扩展的传输协议实现模块，目前实现的扩展传输协议包括：

- grpc - 基于HiveNetGRpc实现了gRpc协议的远程文件传输协议




## HiveNetFileTransfer使用说明

### 实现自己的传输协议

通过当前框架可以实现自己定义的传输协议，具体步骤如下。

**1、开发服务端的文件处理服务**

通常要实现的文件传输都是网络传输，因此需要开发服务端来实现本地和远端的信息传递，通讯协议自行定义。根据需要，服务端可以实现以下两种形式（或结合提供）：

（1）文件信息查询服务

这种形式用于支持本地从服务端拉取文件，服务端要实现的功能比较简单，单纯提供文件信息和数据的获取接口即可，参考接口如下：

- 获取文件大小
- 获取文件MD5值（用于完成传输后校验）
- 获取文件指定位置的二进制数据

（2）文件信息接收服务

这种形式用于支持本地向服务端推送文件，服务端可直接使用TransferSaver类管理文件信息和进行文件储存，因此只需要将TransferSaver类的函数形成对应接口对外提供即可，接口包括：

- 初始化TransferSaver对象
- 将缓存数据写入磁盘
- 关闭TransferSaver对象
- 写入文件数据
- 通知TransferSaver对象文件已结束（文件大小未知的情况）
- 获取数据保存信息
- 获取保存的文件信息字典

**2、开发传输协议类**

传输协议类是ProtocolFw框架类的具体实现，在本地端实现与服务端的通讯处理，直接按ProtocolFw框架类实现具体的函数功能，在这些函数中实现与服务端的通讯处理。

需要注意的是要分别实现源头文件获取和目标文件存储两部分的逻辑：如果是本地向服务端推送的方式，本地实现文件信息获取的功能，并通过网络通讯将信息推送到服务端；如果是本地从服务端拉取文件的方式，本地基于TransferSaver类实现文件信息的管理，通过网络通讯从服务端获取要拉取的文件信息和数据。

注：可以直接继承LocalProtocol类，这样只需根据需要实现网络通讯端的功能即可。



### 文件传输处理简单示例（以LocalProtocol为例）

1、如果有服务端，启动服务端的服务（LocalProtocol是本地复制，因此无需服务端）；

2、在本地端实例化文件传输协议对象，并创建Transfer类对象进行开始文件传输，参考代码如下：

```
# 实例化传输协议
with LocalProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    cache_size=2, thread_num=5
) as _protocol:
  # 实例化传输控制类，将传输协议对象送入传输控制类中
  _reader = Transfer(
      _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
      process_bar_label=_tips,
      thread_interval=0.3
  )
  # 启动传输并等待传输完成
  _status = _reader.start(wait_finished=True)
  # 判断传输结果
  if _status == 'finished':
  	print('传输成功')
```



### 使用 extend_protocol.grpc 扩展进行文件网络传输

extend_protocol.grpc 扩展实现了grpc协议的服务端GRpcProtocolServer，本地向远端推送文件的传输协议GRpcPushProtocol，以及本地从远端拉取文件的传输协议GRpcPullProtocol，具体使用方法介绍如下：

**1、启动服务端GRpcProtocolServer**

```
_grpc_server = GRpcProtocolServer(
    server_config={
        'run_config': {
            'host': '127.0.0.1', 'port': 50051, 'workers': 50, 'max_connect': 400,
            'enable_health_check': True
        }
    },
    work_dir=_temp_path, lock_in_work_dir=True, logger=cls.server_logger,
    log_level=logging.INFO
)
_result = _grpc_server.start_server()
if _result.is_success():
    print('服务启动成功')
```

注: server_config的配置参考HiveNetGRpc的服务参数

**2、使用GRpcPushProtocol协议向远端推送文件**

```
# grpc的连接参数
_conn_config = {'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': False, 'ping_with_health_check': False,
    'use_sync_client': True, 'timeout': 100
}
        
# 实例化传输协议
with GRpcPushProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    cache_size=2, thread_num=100, block_size=40960,
    conn_config=_conn_config
) as _protocol:
		# 实例化传输控制类，将传输协议对象送入传输控制类中
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label=_tips,
        thread_interval=0.0
    )
    # 启动传输并等待传输完成
    _status = _reader.start(wait_finished=True)
    # 判断传输结果
    if _status == 'finished':
        print('传输成功')
```

**3、使用GRpcPullProtocol从远端拉取文件**

```
# grpc的连接参数
_conn_config = {'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': False, 'ping_with_health_check': False,
    'use_sync_client': True, 'timeout': 100
}

# 实例化传输协议
with GRpcPullProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    cache_size=2, thread_num=230, block_size=40960,
    conn_config=_conn_config
) as _protocol:
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label=_tips,
        thread_interval=0.0
    )
    # 启动传输并等待传输完成
    _status = _reader.start(wait_finished=True)
    # 判断传输结果
    if _status == 'finished':
        print('传输成功')
```

**4、支持断点续传**

```
# grpc的连接参数
_conn_config = {'host': '127.0.0.1', 'port': 50051, 'ping_on_connect': False, 'ping_with_health_check': False,
    'use_sync_client': True, 'timeout': 100
}

# 实例化传输协议
with GRpcPullProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    cache_size=2, thread_num=5, block_size=40960,
    conn_config=_conn_config
) as _protocol:
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label=_tips,
        thread_interval=0.0
    )
    # 启动传输, 异步返回
    _status = _reader.start()
    # 等待几秒后停止传输
    time.sleep(1)
    _reader.stop()
    if _reader.status == 'stop':
    	  print('停止成功')
    
# 重新连接并续传, 指定is_resume为True即可
with GRpcPullProtocol(
    _temp_file, _copy_file, is_resume=True, is_overwrite=True,
    cache_size=2, thread_num=5, block_size=40960,
    conn_config=_conn_config
) as _protocol:
    _reader = Transfer(
        _protocol, show_process_bar_fun=ProgressRate.show_cmd_process_bar,
        process_bar_label=_tips,
        thread_interval=0.0
    )
    _status = _reader.start(wait_finished=True)
    # 判断传输结果
    if _status == 'finished':
        print('传输成功')
```

