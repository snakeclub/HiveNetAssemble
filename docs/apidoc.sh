#!/bin/bash

# 当前目录
CURRENT_DIR=$(cd $(dirname $0); pwd)

# 跳转到当前目录
cd $CURRENT_DIR

# 生成模块对应的接口文档
for module_name in {HiveNetCore,HiveNetWebUtils,HiveNetSimpleSanic,HiveNetSimpleFlask,HiveNetGRpc,HiveNetPipeline,HiveNetPromptPlus,HiveNetConsole,HiveNetFileTransfer,HiveNetNoSql}
do
sphinx-apidoc -f -e -d 4 -o ./source/$module_name ../$module_name/$module_name
done

echo "Done"
