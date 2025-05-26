#!/usr/bin/env bash

# Lingualink Server 启动脚本
# 使用统一的管理脚本启动服务

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "🚀 启动 Lingualink Server..."
echo "📍 项目目录: $(pwd)"

# 检查是否传入了参数
if [ "$1" = "--debug" ] || [ "$1" = "-d" ]; then
    echo "🔧 开发模式启动（自动重载）"
    python3 manage.py start --debug
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  --debug, -d    开发模式启动（自动重载）"
    echo "  --help, -h     显示帮助信息"
    echo ""
    echo "更多选项请使用: python3 manage.py start --help"
else
    echo "🏭 生产模式启动（后台运行）"
    python3 manage.py start
fi 