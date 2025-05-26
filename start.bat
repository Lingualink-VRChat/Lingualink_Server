@echo off
echo Starting Lingualink Server...

REM 切换到脚本所在目录
cd /d %~dp0

REM 启动 Lingualink Server
uv run lingualink-server