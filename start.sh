#!/usr/bin/env bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 启动 Lingualink Server
echo "Starting Lingualink Server..."
uv run lingualink-server 