#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
请求测试脚本
@module req_locust_script
@file req_locust_script.py

执行步骤：
1、在命令行运行： locust -f req_locust_script.py --host http://127.0.0.1:5000 -u 2 -r 1
2、浏览器打开：http://0.0.0.0:8089 启动任务
"""

from locust import HttpUser, task


class QuickstartUser(HttpUser):
    @task
    def hello_world(self):
        with self.client.get("/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Got wrong status code")
            else:
                response.success()


if __name__ == '__main__':
    pass
