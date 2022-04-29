# redirect_stdout模块使用说明

redirect_stdout模块由于重定向标准输出的处理，支持将界面的标准输出（print）重定向到其他多个输出对象，例如控制台、字符串、字符数组、日志、文件等，同时该框架也支持进行重定向对象的扩展，以实现更多的标准输出处理功能。



## 模块标准使用步骤

### 定义重定向对象句柄（Handler）

可以使用RedirectOutputHandler类定义目前已支持的控制台、字符串、字符数组、日志、文件这五种对象的句柄，代码参考如下：

```
		# 定义重定向对象
		# 字符串对象
        str_obj = ['']
        str_handler = RedirectOutputHandler(
            handler_type=EnumRedirectOutputHandlerType.String,
            output_obj=str_obj,
            is_flush=True
        )
		
		# 字符数组对象
        strlist_obj = list()
        strlist_handler = RedirectOutputHandler(
            handler_type=EnumRedirectOutputHandlerType.StringList,
            output_obj=strlist_obj,
            is_flush=True
        )
```

当然也可以参考RedirectOutputHandler类自定义个性化的重定向对象句柄，该对象只要实现了write、flush两个内置方法即可。



### 实例化重定向类（RedirectOutput）

初始化RedirectOutput类，将重定向对象句柄传入类中，代码参考如下：

```

```



### 启动及关闭重定向处理

```
		# 启动重定向处理
        redirect_obj.start_redirect()

        # 输出信息
        print(str1)
        print(str2)
        print(str3)

        # 关闭重定向处理
        redirect_obj.stop_redirect()
        
        # 访问重定向对象
        print(str(str_obj[0]))
        print(str(strlist_obj))
```



