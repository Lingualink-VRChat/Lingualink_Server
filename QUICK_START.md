# 🚀 Lingualink Server 快速启动指南

## 一键启动

### Linux/macOS
```bash
# 开发模式（推荐用于开发和测试）
./start.sh --debug

# 生产模式（后台运行）
./start.sh
```

### Windows
```cmd
# 开发模式
start.bat --debug

# 生产模式
start.bat
```

## 管理命令

```bash
# 查看服务状态
python3 manage.py status

# 停止服务
python3 manage.py stop
# 或者
./stop.sh

# 重启服务
python3 manage.py restart

# 查看日志
python3 manage.py logs

# 实时跟踪日志
python3 manage.py logs --follow
```

## 访问服务

启动成功后，访问以下地址：

- **API 文档**: http://localhost:5000/docs
- **健康检查**: http://localhost:5000/api/v1/health
- **服务信息**: http://localhost:5000/

## 常见问题

### 端口被占用
```bash
# 查看占用端口的进程
sudo lsof -i :5000

# 停止旧服务
python3 manage.py stop
```

### 权限问题
```bash
# 添加执行权限
chmod +x start.sh stop.sh manage.py
```

### 虚拟环境问题
```bash
# 重新安装依赖
uv sync
```

## 更多信息

- 详细文档: [README.md](README.md)
- 服务管理: [SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md) 