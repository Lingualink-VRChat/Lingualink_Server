#!/bin/bash

# Lingualink Server - 音频依赖安装脚本
# 安装OPUS音频格式支持所需的系统依赖

set -e

echo "=== Lingualink Server 音频依赖安装 ==="

# 检测操作系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "检测到 Linux 系统"
    
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        echo "使用 apt-get 安装依赖..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg libopus0 libopus-dev opus-tools
        
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        echo "使用 yum 安装依赖..."
        sudo yum install -y epel-release
        sudo yum install -y ffmpeg opus opus-devel opus-tools
        
    elif command -v dnf &> /dev/null; then
        # Fedora
        echo "使用 dnf 安装依赖..."
        sudo dnf install -y ffmpeg opus opus-devel opus-tools
        
    elif command -v pacman &> /dev/null; then
        # Arch Linux
        echo "使用 pacman 安装依赖..."
        sudo pacman -S ffmpeg opus opus-tools
        
    else
        echo "错误: 无法识别的 Linux 包管理器"
        echo "请手动安装 ffmpeg 和 opus 相关包"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "检测到 macOS 系统"
    
    if command -v brew &> /dev/null; then
        echo "使用 Homebrew 安装依赖..."
        brew install ffmpeg opus opus-tools
    else
        echo "错误: 未找到 Homebrew"
        echo "请先安装 Homebrew: https://brew.sh/"
        exit 1
    fi
    
else
    echo "错误: 不支持的操作系统: $OSTYPE"
    echo "请手动安装 ffmpeg 和 opus"
    exit 1
fi

# 验证安装
echo ""
echo "=== 验证安装 ==="

if command -v ffmpeg &> /dev/null; then
    echo "✓ FFmpeg 已安装: $(ffmpeg -version | head -n1)"
else
    echo "✗ FFmpeg 未找到"
    exit 1
fi

if command -v opusenc &> /dev/null; then
    echo "✓ OPUS 工具已安装: $(opusenc --version 2>&1 | head -n1)"
else
    echo "✗ OPUS 工具未找到"
    exit 1
fi

echo ""
echo "=== 安装完成 ==="
echo "现在可以运行 Lingualink Server 并支持 OPUS 音频格式了！"
echo ""
echo "测试命令:"
echo "  python3 -c \"from pydub import AudioSegment; print('pydub 工作正常')\""
echo "  ffmpeg -version"
echo "" 