# HiveNetWetUtils总览

HiveNetWebUtils是HiveNetAssemble的Web应用工具组件, 提供常用的Web服务抽象类和工具类。

## 安装方法

### 源码方式安装

- HiveNetWebUtils库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetWetUtils


- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetWetUtils-0.1.0-py3-none-any.whl


## 库模块大纲

### server

[server](02_server.md)模块提供了一个通用Web服务管理抽象框架(ServerBaseFW)，支持实现类进行Web服务的启动、关闭，添加/移除服务函数等功能，支持快速实现一个新的Web服务；此外实现了一个基于Socket的TcpIpServer，可以通过简单的协议实现服务端的数据收发，可以作为ServerBaseFW的一个实现类参考示例。

### auth
[auth](03_auth.md)模块提供了一个通用的Web服务的鉴权处理框架(AuthBaseFw), 基于该框架可以快速实现基于修饰符的服务请求鉴权处理。同时该模块中也提供了针对客户端IP鉴权(IPAuth)和使用AppKey模式进行鉴权(AppKeyAuth)的两个实现框架(需继承并适配对应的Web服务)。

### client

client模块提供了一个通用客户端连接抽象框架(ClientBaseFw)，支持实现类连接服务端，进行远程调用等，支持快速实现一个新的客户端连接类；此外实现了http连接客户端的实现类AIOHttpClient（异步IO客户端）和HttpClient（同步客户端）。

### utils
utils包提供了一些Web服务所需的公共工具模块，例如cryptography模块提供了加解密处理的通用工具，socket模块提供了socket客户端连接、端口收发数据等通用工具。

### parser
parser包提供各类数据解析器, 目前支持解析器包括: html。

### connection_pool
connection_pool 模块已迁移到HiveNetCore组件中，当前组件保留的只是对应的模块链接，用来兼容此前使用本组件该模块功能的情况。
