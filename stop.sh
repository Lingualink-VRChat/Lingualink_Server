#!/usr/bin/env bash

# Lingualink Server 停止脚本

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "⏹️  停止 Lingualink Server..."
python3 manage.py stop 