# server模块说明

server模块提供了一个通用Web服务管理抽象框架(ServerBaseFW)，支持实现类进行Web服务的启动、关闭，添加/移除服务函数等功能，支持快速实现一个新的Web服务；此外实现了一个基于Socket的TcpIpServer，可以通过简单的协议实现服务端的数据收发，可以作为ServerBaseFW的一个实现类参考示例。



## 遵循标准

hivenet_error_code_standards_v1.1.0

hivenet_log_standards_v1.0.0



## 基于ServerBaseFW实现自己的Web服务

**1、实现类必须继承ServerBaseFW**

```
class MyWebServer(ServerBaseFW):
    ...
```



**2、按需要是否重载 `__init__` 函数**

```
def __init__(self, app_name: str, server_config: dict = {}, support_auths: dict = {},
    before_server_start=None, after_server_start=None,
    before_server_stop=None, after_server_stop=None, logger=None, log_level: int = logging.INFO,
    load_i18n_para=None, **kwargs):
    """自己的注释"""
    # 引用框架的构造函数
    super().__init__(
        app_name, server_config=server_config, support_auths=support_auths,
        before_server_start=before_server_start,
        after_server_start=after_server_start, before_server_stop=before_server_stop,
        after_server_stop=after_server_stop, logger=logger, log_level=log_level,
        load_i18n_para=load_i18n_para, **kwargs
    )
    # 自己的其他逻辑
    ...
```

**注：一般来说，重载 `__init__` 函数的目的更多是进行注释内容变更，便于进行代码的提示；如果需要进行参数初始化处理，也可以直接把逻辑放到 `_std_init_config` 函数内，并不一定要在  `__init__` 函数内处理初始化逻辑。**



**3、重载 `_std_init_config` 函数，实现 `__init__` 函数初始化的自定义逻辑：**

```
def _std_init_config(self):
    """
    标准化服务初始配置
    """
    # 实现类可以通过该函数设置或修改内部参数
    pass
```



**4、重载真正的服务启动和停止相关的函数：**

```
async def _real_server_initialize(self, tid) -> CResult:
    """
    初始化真正的服务端处理对象
    注: 可以在该函数中启动真正的服务, 例如绑定监听端口

    @param {int} tid - 服务线程id

    @returns {CResult} - 启动结果:
        result.code: '00000'-成功, 其他值为失败
        result.server_info: 启动成功后的服务信息, 用于传递到后续的服务处理函数
    """
    _result = CResult(code='00000')  # 成功
    _result.server_info = NullObj()
    with ExceptionTool.ignored_cresult(_result):
        # 注: 重载该函数, 可在该部分实现自定义的服务初始化或启动逻辑
        pass

    # 返回处理结果
    return _result

async def _real_server_accept_and_run(self, tid, server_info) -> CResult:
    """
    真正的服务获取请求并运行
    注: 支持同步或异步函数, 可以在该函数中获取请求, 并启动线程执行请求处理

    @param {int} tid - 线程id
    @param {Any} server_info - 启动成功后的服务信息

    @returns {CResult} - 处理结果:
        result.code: '00000'-成功, 其他值为失败, 如果为失败将停止服务
        result.is_finished: 指示服务是否已完成, True - 已处理完成可停止服务, False - 未完成, 需循环处理下一个请求
    """
    _result = CResult(code='00000')  # 成功
    _result.is_finished = False
    with ExceptionTool.ignored_cresult(
        _result, logger=self._logger,
        self_log_msg='[SER][NAME:%s]%s: ' % (
            self._app_name, _('server run error')),
        force_log_level=logging.ERROR
    ):
        # 注: 重载该函数, 可在该部分实现自定义的获取请求及处理逻辑
        pass

    # 返回处理结果
    return _result

async def _real_server_prepare_stop(self, tid) -> CResult:
    """
    服务关闭前的处理函数
    注: 支持同步或异步函数, 可以在该函数中等待已接入的请求或线程完成处理

    @param {int} tid - 线程id

    @returns {CResult} - 处理结果:
        result.code: '00000'-成功, 其他值为失败
        result.is_finished: 指示停止前的预处理是否已完成, True - 已处理完成可停止服务, False - 未完成, 需循环继续调用本函数
    """
    _result = CResult(code='00000')  # 成功
    _result.is_finished = True
    with ExceptionTool.ignored_cresult(
        _result, logger=self._logger,
        self_log_msg='[SER-PRE-STOP][NAME:%s]%s: ' % (
            self._app_name, _('stop net server error')),
        force_log_level=logging.ERROR
    ):
        # 注: 重载该函数, 可在该部分实现自定义的服务关闭前处理
        pass

    return _result

async def _real_server_stop(self, tid, server_info):
    """
    真正服务的关闭处理
    注: 支持同步或异步函数, 可以在该函数中清理处理线程并关闭监听

    @param {int} tid - 线程id
    @param {Any} server_info - 启动成功后的服务信息
    """
    # 子类必须定义该功能
    with ExceptionTool.ignored_all(
        logger=self._logger,
        self_log_msg='[SER-STOP][NAME:%s]%s error: ' % (
            self._app_name, _('stop net server error')
        )
    ):
        # 注: 重载该函数, 可在该部分实现自定义的服务关闭处理
        pass
```

**注：在重载 `_real_server_accept_and_run` 函数时涉及到客户端请求的处理逻辑，处理逻辑中可以使用 `self._service_router` 字典获取到服务所添加的处理函数对象，来进行真正的业务处理。**



**5、根据需要重载其他函数**

正常情况完成上述4个步骤就可以完成一个Web服务的实现，框架启动一个服务子线程，通过 `_real_server_initialize` 函数进行服务对象的初始化（例如绑定IP并启动监听），以及通过循环调用 `_real_server_accept_and_run` 函数从服务对象中获取客户端请求并进行对应的业务逻辑处理。

如果您的服务对象无法按照该流程进行初始化和获取请求处理，则需重载其他相关函数来实现具体逻辑，例如Sanic本身启动就是阻断式的方式，需要直接重载 `start` 函数实现相关功能。



## ServerBaseFW服务的使用

**1、基于ServerBaseFW实现的web服务使用**

```
from HiveNetCore.utils.run_tool import AsyncTools

# 服务处理函数定义
def deal_fun_1(...):
   ...

def deal_fun_2(...):
   ...

# 初始化服务对象, 具体参数说明直接参考源码的注释定义
_server = MyWebServer(...)

# 添加处理函数，注意是异步调用方式, 如果是异步函数内部，可以使用await来处理
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun/uri1', deal_fun_1, ...)
)
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun/uri2', deal_fun_2, ...)
)

# 启动服务, 这里指定同步模式，也就是服务不停止就阻塞该线程
AsyncTools.sync_run_coroutine(
	_server.start(is_asyn=True)
)
```



**2、auth鉴权功能的使用**

结合auth鉴权框架，可以在服务处理函数上增加修饰符，实现对客户端强求的鉴权，例如：

```
# 加载鉴权实现类
from xxx import IPAuthXXX

# 服务处理函数定义, 增加ip鉴权修饰符
@MyWebServer.auth_required_static(auth_name='IPAuth', app_name='MyAppName')
def deal_fun_1(...):
   ...

@MyWebServer.auth_required_static(auth_name='IPAuth', app_name='MyAppName')
def deal_fun_2(...):
   ...

# 实例化IPAuth鉴权对象， 增加访问白名单
_ip_auth = IPAuthXXX(init_whitelist=['10.1.43.*', '10.2.*, *'])

# 初始化服务对象, 指定修饰符中相同的app_name, support_auths参数与auth_name对应
_server = MyWebServer('MyAppName', ..., support_auths={'IPAuthXXX': _ip_auth}, ...)

# 添加处理函数
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun/uri1', deal_fun_1, ...)
)
AsyncTools.sync_run_coroutine(
	_server.add_service('/deal_fun/uri2', deal_fun_2, ...)
)

...
```

