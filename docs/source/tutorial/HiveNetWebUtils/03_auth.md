# auth模块说明

auth模块提供了一个通用的Web服务的鉴权处理框架(AuthBaseFw), 基于该框架可以快速实现基于修饰符的服务请求鉴权处理。同时该模块中也提供了针对客户端IP鉴权(IPAuth)和使用AppKey模式进行鉴权(AppKeyAuth)的两个实现框架(需继承并适配对应的Web服务)。



## 构建自定义的AuthBaseFw实现类

**1、实现类必须继承AuthBaseFw**

需要继承框架类，并实现自定义的 `__init__`函数：

```
class MyAuth(AuthBaseFw):

    def __init__(self, **kwargs):
        """
        模块初始化函数
        (需由实现类继承实现)
        """
        pass
```



**2、重载实现鉴权是否通过的判断逻辑函数**

```
async def _auth_call(self, *args, **kwargs) -> tuple:
    """
    真正的校验处理函数

    @param {args} - 执行函数的固定入参
    @param {kwargs} - 执行函数的kv入参

    @returns {tuple} - 返回校验结果数组: (校验是否通过true/false, 错误码, 失败描述)
        注: 错误码由实现类自行定义
    """
    raise NotImplementedError()
```



**3、重载实现对鉴权结果格式化的函数**

该函数将_auth_call返回失败的结果，格式化为与处理函数返回结果格式相同的值类型

```
def _format_auth_resp(self, code: Any, err_msg: str) -> Any:
    """
    格式化校验结果返回值

    @param {Any} code - 错误码
    @param {str} err_msg - 失败描述

    @returns {Any} - 格式化后的返回值
    """
    raise NotImplementedError()
```



**4、重载实现对处理函数返回结果格式化的函数**

该函数将正常运行的处理函数的返回值，或者_format_auth_resp格式化后的鉴权失败返回值，格式化为所需的格式，供web服务处理最终的返回：

```
def _format_last_resp(self, resp: Any, is_auth_result: bool) -> Any:
    """
    格式化最后的响应对象

    @param {Any} resp - 最后的响应对象
    @param {bool} is_auth_result - 是否服务鉴权所返回的结果

    @returns {Any} - 转换以后的响应对象
    """
    return resp
```



## AuthBaseFw实现类的使用

1、直接实例化，并使用实例化后对象对处理函数进行修饰

```
# 实例化IPAuth鉴权对象， 增加访问白名单
_ip_auth = IPAuthXXX(init_whitelist=['10.1.43.*', '10.2.*, *'])

# 服务处理函数定义, 增加_ip_auth对象的鉴权修饰符
@_ip_auth.auth_required
def deal_fun_1(...):
   ...

@_ip_auth.auth_required
def deal_fun_2(...):
   ...

```



2、使用Web服务的support_auths功能

具体见 [server](02_server.md) 的模块说明。