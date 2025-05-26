#!/usr/bin/env python3
"""
Lingualink Server 管理脚本
统一的服务启动、停止、重启和状态管理
"""

import os
import sys
import subprocess
import argparse
import signal
import time
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()
VENV_PATH = PROJECT_ROOT / ".venv"
PYTHON_PATH = VENV_PATH / "bin" / "python"
PID_FILE = PROJECT_ROOT / "lingualink.pid"
LOG_FILE = PROJECT_ROOT / "logs" / "lingualink.log"

def ensure_log_dir():
    """确保日志目录存在"""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir

def get_pid():
    """获取服务进程ID"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # 检查进程是否存在
            try:
                os.kill(pid, 0)
                return pid
            except OSError:
                # 进程不存在，删除过期的PID文件
                PID_FILE.unlink()
                return None
        except (ValueError, FileNotFoundError):
            return None
    return None

def is_running():
    """检查服务是否正在运行"""
    return get_pid() is not None

def start_service(debug=False, port=5000, host="0.0.0.0"):
    """启动服务"""
    if is_running():
        print("❌ 服务已经在运行中")
        return False
    
    print("🚀 启动 Lingualink Server...")
    
    # 确保虚拟环境存在
    if not PYTHON_PATH.exists():
        print("❌ 虚拟环境不存在，请先运行: uv sync")
        return False
    
    # 确保日志目录存在
    ensure_log_dir()
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    
    if debug:
        # 开发模式：前台运行，自动重载
        cmd = [
            str(PYTHON_PATH), "-m", "uvicorn",
            "src.lingualink.main:app",
            "--host", host,
            "--port", str(port),
            "--reload",
            "--log-level", "debug"
        ]
        print(f"🔧 开发模式启动: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)
        except KeyboardInterrupt:
            print("\n⏹️  服务已停止")
        return True
    else:
        # 生产模式：后台运行
        cmd = [
            str(PYTHON_PATH), "-m", "uvicorn",
            "src.lingualink.main:app",
            "--host", host,
            "--port", str(port),
            "--log-level", "info"
        ]
        
        with open(LOG_FILE, 'a') as log_f:
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        # 保存PID
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
        
        # 等待一下确保启动成功
        time.sleep(2)
        if is_running():
            print(f"✅ 服务启动成功 (PID: {process.pid})")
            print(f"📊 服务地址: http://{host}:{port}")
            print(f"📚 API文档: http://{host}:{port}/docs")
            print(f"📝 日志文件: {LOG_FILE}")
            return True
        else:
            print("❌ 服务启动失败，请检查日志")
            return False

def stop_service():
    """停止服务"""
    pid = get_pid()
    if not pid:
        print("⚠️  服务未运行")
        return True
    
    print(f"⏹️  停止服务 (PID: {pid})...")
    try:
        # 发送SIGTERM信号
        os.kill(pid, signal.SIGTERM)
        
        # 等待进程结束
        for _ in range(10):
            time.sleep(0.5)
            if not is_running():
                break
        else:
            # 如果还没结束，强制杀死
            print("🔨 强制停止服务...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
        
        # 清理PID文件
        if PID_FILE.exists():
            PID_FILE.unlink()
        
        print("✅ 服务已停止")
        return True
    except OSError as e:
        print(f"❌ 停止服务失败: {e}")
        return False

def restart_service(**kwargs):
    """重启服务"""
    print("🔄 重启服务...")
    stop_service()
    time.sleep(1)
    return start_service(**kwargs)

def status_service():
    """查看服务状态"""
    pid = get_pid()
    if pid:
        print(f"✅ 服务正在运行 (PID: {pid})")
        
        # 尝试获取更多信息
        try:
            import psutil
            process = psutil.Process(pid)
            print(f"📊 内存使用: {process.memory_info().rss / 1024 / 1024:.1f} MB")
            print(f"⏱️  运行时间: {time.time() - process.create_time():.0f} 秒")
        except ImportError:
            pass
        except Exception:
            pass
        
        return True
    else:
        print("❌ 服务未运行")
        return False

def show_logs(lines=50, follow=False):
    """显示日志"""
    if not LOG_FILE.exists():
        print("📝 日志文件不存在")
        return
    
    if follow:
        # 实时跟踪日志
        cmd = ["tail", "-f", str(LOG_FILE)]
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n⏹️  停止日志跟踪")
    else:
        # 显示最后N行
        cmd = ["tail", "-n", str(lines), str(LOG_FILE)]
        subprocess.run(cmd)

def cleanup():
    """清理临时文件"""
    print("🧹 清理临时文件...")
    
    # 清理PID文件
    if PID_FILE.exists():
        PID_FILE.unlink()
        print("✅ 清理PID文件")
    
    # 清理日志文件（可选）
    if LOG_FILE.exists():
        response = input("是否清理日志文件? (y/N): ")
        if response.lower() == 'y':
            LOG_FILE.unlink()
            print("✅ 清理日志文件")
    
    print("✅ 清理完成")

def main():
    parser = argparse.ArgumentParser(description="Lingualink Server 管理工具")
    parser.add_argument("action", choices=[
        "start", "stop", "restart", "status", "logs", "cleanup"
    ], help="操作类型")
    
    parser.add_argument("--debug", "-d", action="store_true", help="开发模式（自动重载）")
    parser.add_argument("--port", "-p", type=int, default=5000, help="端口号")
    parser.add_argument("--host", "-H", default="0.0.0.0", help="监听地址")
    parser.add_argument("--lines", "-n", type=int, default=50, help="显示日志行数")
    parser.add_argument("--follow", "-f", action="store_true", help="实时跟踪日志")
    
    args = parser.parse_args()
    
    # 切换到项目目录
    os.chdir(PROJECT_ROOT)
    
    if args.action == "start":
        success = start_service(debug=args.debug, port=args.port, host=args.host)
        sys.exit(0 if success else 1)
    elif args.action == "stop":
        success = stop_service()
        sys.exit(0 if success else 1)
    elif args.action == "restart":
        success = restart_service(debug=args.debug, port=args.port, host=args.host)
        sys.exit(0 if success else 1)
    elif args.action == "status":
        success = status_service()
        sys.exit(0 if success else 1)
    elif args.action == "logs":
        show_logs(lines=args.lines, follow=args.follow)
    elif args.action == "cleanup":
        cleanup()

if __name__ == "__main__":
    main() 