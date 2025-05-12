@echo off
REM 切换到脚本所在目录
cd /d %~dp0

REM 激活虚拟环境
call .venv\Scripts\activate

REM 启动 uvicorn 服务
uvicorn app:app --reload --host 0.0.0.0 --port 5000