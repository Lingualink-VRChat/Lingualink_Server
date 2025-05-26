# Lingualink 服务管理指南

本文档提供 Lingualink Server 的完整服务管理方案，包括开发和生产环境的部署方式。

## 🚀 快速开始

### 统一管理脚本（推荐）

项目提供了统一的 `manage.py` 脚本来管理服务：

```bash
# 启动服务（生产模式，后台运行）
python3 manage.py start

# 启动服务（开发模式，前台运行，自动重载）
python3 manage.py start --debug

# 查看服务状态
python3 manage.py status

# 停止服务
python3 manage.py stop

# 重启服务
python3 manage.py restart

# 查看日志（最后50行）
python3 manage.py logs

# 实时跟踪日志
python3 manage.py logs --follow

# 清理临时文件
python3 manage.py cleanup
```

### 便捷脚本

```bash
# Linux/macOS
./start.sh              # 生产模式启动
./start.sh --debug      # 开发模式启动
./stop.sh               # 停止服务

# Windows
start.bat               # 生产模式启动
start.bat --debug       # 开发模式启动
```

## 📋 管理脚本详细说明

### 启动选项

```bash
python3 manage.py start [选项]

选项:
  --debug, -d           开发模式（自动重载）
  --port PORT, -p PORT  指定端口（默认5000）
  --host HOST, -H HOST  指定监听地址（默认0.0.0.0）
```

### 日志选项

```bash
python3 manage.py logs [选项]

选项:
  --lines N, -n N       显示最后N行日志（默认50）
  --follow, -f          实时跟踪日志
```

## 🔧 Systemd 服务管理

### 安装 Systemd 服务

1. **复制服务文件**：
```bash
sudo cp lingualink.service /etc/systemd/system/
```

2. **重新加载 systemd 配置**：
```bash
sudo systemctl daemon-reload
```

3. **启用服务（开机自启）**：
```bash
sudo systemctl enable lingualink.service
```

### Systemd 服务命令

```bash
# 启动服务
sudo systemctl start lingualink.service

# 停止服务
sudo systemctl stop lingualink.service

# 重启服务
sudo systemctl restart lingualink.service

# 查看服务状态
sudo systemctl status lingualink.service

# 查看服务日志
sudo journalctl -u lingualink.service

# 实时跟踪日志
sudo journalctl -u lingualink.service -f

# 启用开机自启
sudo systemctl enable lingualink.service

# 禁用开机自启
sudo systemctl disable lingualink.service
```

## 🐳 Docker 部署

### 创建 Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY . .

# 安装依赖
RUN uv sync --frozen

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# 启动服务
CMD ["python3", "manage.py", "start"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  lingualink-server:
    build: .
    ports:
      - "5000:5000"
    environment:
      - HOST=0.0.0.0
      - PORT=5000
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 📊 监控和日志

### 日志文件位置

- **应用日志**: `logs/lingualink.log`
- **PID 文件**: `lingualink.pid`
- **Systemd 日志**: `journalctl -u lingualink.service`

### 日志级别

- **生产模式**: INFO 级别
- **开发模式**: DEBUG 级别

### 监控检查

```bash
# 检查服务是否运行
python3 manage.py status

# 检查端口是否监听
netstat -tlnp | grep :5000

# 检查健康状态
curl http://localhost:5000/api/v1/health
```

## 🔧 故障排除

### 常见问题

1. **端口被占用**：
```bash
# 查看端口占用
sudo lsof -i :5000

# 杀死占用进程
sudo kill -9 <PID>
```

2. **权限问题**：
```bash
# 确保脚本有执行权限
chmod +x manage.py start.sh stop.sh
```

3. **虚拟环境问题**：
```bash
# 重新创建虚拟环境
uv sync
```

4. **服务启动失败**：
```bash
# 查看详细日志
python3 manage.py logs --follow

# 检查配置文件
cat .env
```

### 清理和重置

```bash
# 停止所有相关进程
python3 manage.py stop
sudo systemctl stop lingualink.service

# 清理临时文件
python3 manage.py cleanup

# 重新启动
python3 manage.py start
```

## 🔄 版本升级

### 升级步骤

1. **停止服务**：
```bash
python3 manage.py stop
```

2. **备份配置**：
```bash
cp .env .env.backup
```

3. **更新代码**：
```bash
git pull origin main
```

4. **更新依赖**：
```bash
uv sync
```

5. **重启服务**：
```bash
python3 manage.py start
```

## 📝 最佳实践

### 开发环境

- 使用 `--debug` 模式进行开发
- 定期查看日志排查问题
- 使用 `manage.py` 脚本管理服务

### 生产环境

- 使用 systemd 服务管理
- 启用开机自启
- 配置日志轮转
- 设置监控告警
- 定期备份配置文件

### 安全建议

- 限制服务运行用户权限
- 配置防火墙规则
- 使用强密码和API密钥
- 定期更新依赖包
- 监控异常访问 