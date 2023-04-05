# HiveNetAssemble

[English Version](README.md)

HiveNetAssemble 一组方便开发人员使用的Python库集合, 旨在让开发人员用最简单的方法实现最常用的功能, 提高开发效率, 关注具体功能逻辑而非具体技术实现。
该项目是由HiveNetLib项目转化而来, 原因是HiveNetLib项目采取单库的方式导致依赖越来越多, 整个库也越来越臃肿, 因此创建本项目将HiveNetLib中的功能抽离为独立库形式, 来降低整个项目维护和使用的复杂性。

文档地址: https://hivenetassemble.readthedocs.io/zh_CN/latest/

## 更新GitHub的Host文件的方法

获取最新的Host信息：https://hosts.gitcdn.top/hosts.txt

手动修改host文件：

Linux / MacOS hosts 路径：/etc/hosts

Windows hosts 路径：C:\Windows\System32\drivers\etc\hosts

## 项目维护命令

**构建项目文档：**

```shell
# 进入文档目录
cd docs/

# 自动生成api文档索引
./apidoc.sh

# 构建html帮助文档
make clean
make html
```

**项目版本设置标签(版本为所有组件中最新的版本号)：**

```shell
# 为当前文档打上标签
git tag -a v0.1.2 -m "HiveNetAssemble version 0.1.2"

# 提交标签到git服务
git push origin --tags
```

**打包并上传版本到Pypi：**

```shell
# 检查pip上的包版本清单
pip show HiveNetAssemble

# 执行打包处理
python setup.py sdist

# 上传到Pypi
twine upload dist/*-0.1.2.*
```

**安装本地源码到python库（用于测试本地最新源码）**

```shell
# 安装包
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetCore "HiveNetCore"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetWebUtils "HiveNetWebUtils"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetSimpleSanic "HiveNetSimpleSanic"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetSimpleFlask "HiveNetSimpleFlask"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetGRpc "HiveNetGRpc"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetPipeline "HiveNetPipeline"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetPromptPlus "HiveNetPromptPlus"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetConsole "HiveNetConsole"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetFileTransfer "HiveNetFileTransfer"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetNoSql "HiveNetNoSql"
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -s HiveNetBuildTool "HiveNetBuildTool"

# 移除安装
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetCore
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetWebUtils
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetSimpleSanic
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetSimpleFlask
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetGRpc
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetPipeline
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetPromptPlus
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetConsole
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetFileTransfer
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetNoSql
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -r HiveNetBuildTool

# 查看所安装的包路径是否准确, 获取库所在路径, 例如: /Users/lhj/miniforge3/lib/python3.9/site-packages
python "HiveNetCore/HiveNetCore/utils/pyenv_tool.py" -g

# 查看指定的安装路径
view /Users/lhj/miniforge3/lib/python3.9/site-packages/HiveNetCore.pth

```

正在构建中...