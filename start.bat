@echo off
REM Lingualink Server 启动脚本 (Windows)
REM 使用统一的管理脚本启动服务

echo 🚀 启动 Lingualink Server...

REM 切换到脚本所在目录
cd /d %~dp0

echo 📍 项目目录: %CD%

REM 检查参数
if "%1"=="--debug" goto debug
if "%1"=="-d" goto debug
if "%1"=="--help" goto help
if "%1"=="-h" goto help

REM 默认生产模式
echo 🏭 生产模式启动（后台运行）
python manage.py start
goto end

:debug
echo 🔧 开发模式启动（自动重载）
python manage.py start --debug
goto end

:help
echo 用法: %0 [选项]
echo 选项:
echo   --debug, -d    开发模式启动（自动重载）
echo   --help, -h     显示帮助信息
echo.
echo 更多选项请使用: python manage.py start --help
goto end

:end
pause