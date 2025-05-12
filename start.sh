#!/usr/bin/env bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
source .venv/bin/activate

# 启动 uvicorn 服务
uvicorn app:app --reload --host 0.0.0.0 --port 5000 