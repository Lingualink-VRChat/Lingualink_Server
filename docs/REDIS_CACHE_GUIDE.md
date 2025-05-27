# 🚀 Redis缓存配置指南

## 📋 概述

Lingualink Server 支持使用Redis缓存来大幅提升API密钥验证性能。启用Redis缓存后，API密钥验证的响应时间可以从2-8ms降低到0.1-0.5ms，性能提升80-90%。

## 🔧 安装Redis

### Ubuntu/Debian
```bash
# 更新包列表
sudo apt update

# 安装Redis
sudo apt install redis-server

# 启动Redis服务
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 验证安装
redis-cli ping
# 应该返回: PONG
```

### CentOS/RHEL
```bash
# 安装EPEL仓库
sudo yum install epel-release

# 安装Redis
sudo yum install redis

# 启动Redis服务
sudo systemctl start redis
sudo systemctl enable redis

# 验证安装
redis-cli ping
```

### macOS
```bash
# 使用Homebrew安装
brew install redis

# 启动Redis服务
brew services start redis

# 验证安装
redis-cli ping
```

### Docker方式
```bash
# 运行Redis容器
docker run -d \
  --name lingualink-redis \
  -p 6379:6379 \
  redis:7-alpine

# 验证安装
docker exec lingualink-redis redis-cli ping
```

## ⚙️ 配置Lingualink Server

### 1. 启用Redis缓存

在你的`.env`文件中添加或修改以下配置：

```env
# 启用Redis缓存
REDIS_ENABLED=true

# Redis连接URL（默认本地Redis）
REDIS_URL=redis://localhost:6379/0

# API密钥缓存过期时间（秒，默认5分钟）
API_KEY_CACHE_TTL=300
```

### 2. 高级配置选项

```env
# 使用密码保护的Redis
REDIS_URL=redis://:your_password@localhost:6379/0

# 使用远程Redis服务器（无密码）
REDIS_URL=redis://redis-server.example.com:6379/0

# 使用远程Redis服务器（有密码）
REDIS_URL=redis://:your_password@redis-server.example.com:6379/0

# 使用不同的数据库编号
REDIS_URL=redis://:your_password@localhost:6379/1

# 调整缓存过期时间
API_KEY_CACHE_TTL=600  # 10分钟
```

## 🚀 启动服务

```bash
# 确保Redis正在运行
sudo systemctl status redis-server

# 启动Lingualink Server
python3 -m src.lingualink.main
```

启动时你应该看到类似的日志：
```
INFO:src.lingualink.auth.redis_cache:Redis cache initialized: redis://localhost:6379/0
```

## 📊 监控和管理

### 1. 检查缓存健康状态

```bash
curl http://localhost:5000/api/v1/cache/health
```

响应示例：
```json
{
  "status": "success",
  "data": {
    "redis_enabled": true,
    "redis_healthy": true,
    "message": "Redis is healthy"
  }
}
```

### 2. 获取缓存统计信息（需要管理员权限）

```bash
curl -H "X-API-Key: your-admin-key" \
     http://localhost:5000/api/v1/cache/stats
```

响应示例：
```json
{
  "status": "success",
  "data": {
    "enabled": true,
    "redis_version": "7.0.11",
    "connected_clients": 2,
    "used_memory_human": "1.23M",
    "api_key_cache_count": 15,
    "cache_ttl": 300
  }
}
```

### 3. 清空所有缓存（需要管理员权限）

```bash
curl -X POST \
     -H "X-API-Key: your-admin-key" \
     http://localhost:5000/api/v1/cache/clear
```

### 4. 使特定API密钥缓存失效（需要管理员权限）

```bash
curl -X DELETE \
     -H "X-API-Key: your-admin-key" \
     http://localhost:5000/api/v1/cache/invalidate/lls_target_api_key
```

## 🔍 性能对比

### 未启用Redis缓存
- API密钥验证时间：2-8ms
- 数据库查询：每次请求
- 并发性能：受数据库连接限制

### 启用Redis缓存后
- 缓存命中验证时间：0.1-0.5ms
- 缓存未命中验证时间：2-8ms（首次查询）
- 性能提升：80-90%
- 并发性能：显著提升

## 🛡️ 安全考虑

### 1. Redis安全配置

编辑Redis配置文件（通常在`/etc/redis/redis.conf`）：

```conf
# 绑定到特定IP（不要使用0.0.0.0在生产环境）
bind 127.0.0.1

# 设置密码
requirepass your-strong-password

# 禁用危险命令
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 2. 网络安全

```bash
# 配置防火墙只允许特定IP访问Redis端口
sudo ufw allow from 192.168.1.0/24 to any port 6379
```

### 3. 缓存数据保护

- 缓存中只存储验证结果，不存储完整API密钥
- 只缓存有效的密钥，无效密钥不会被缓存
- 缓存键使用API密钥的前16个字符，避免完整密钥泄露

## 🔧 故障排除

### 1. Redis连接失败

**问题**：启动时看到"Redis connection failed, disabling cache"

**解决方案**：
```bash
# 检查Redis是否运行
sudo systemctl status redis-server

# 检查Redis端口是否监听
netstat -tlnp | grep 6379

# 测试Redis连接
redis-cli ping

# 检查防火墙设置
sudo ufw status
```

### 2. 缓存未生效

**问题**：API响应时间没有改善

**解决方案**：
```bash
# 检查缓存健康状态
curl http://localhost:5000/api/v1/cache/health

# 查看缓存统计
curl -H "X-API-Key: admin-key" \
     http://localhost:5000/api/v1/cache/stats

# 检查日志中的缓存命中信息
tail -f logs/lingualink.log | grep "Cache hit"
```

### 3. 内存使用过高

**解决方案**：
```bash
# 调整缓存过期时间（减少到2分钟）
# 在.env文件中设置：
API_KEY_CACHE_TTL=120

# 或者配置Redis最大内存限制
# 在redis.conf中添加：
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## 📈 性能调优建议

### 1. 缓存过期时间调优

```env
# 高频访问场景（推荐）
API_KEY_CACHE_TTL=300  # 5分钟

# 超高频访问场景
API_KEY_CACHE_TTL=600  # 10分钟

# 安全优先场景
API_KEY_CACHE_TTL=60   # 1分钟
```

### 2. Redis配置优化

```conf
# redis.conf 优化配置
maxmemory 512mb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
```

### 3. 监控指标

定期监控以下指标：
- 缓存命中率（目标：>80%）
- Redis内存使用量
- API响应时间
- 并发连接数

## 🔄 维护操作

### 定期清理过期缓存

```bash
# 创建定时任务清理过期密钥缓存
# 添加到crontab：
0 2 * * * curl -X POST -H "X-API-Key: admin-key" http://localhost:5000/api/v1/auth/cleanup_expired
```

### 备份Redis数据

```bash
# Redis会自动创建RDB快照，也可以手动备份
redis-cli BGSAVE

# 备份RDB文件
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
```

## 📚 相关文档

- [Redis官方文档](https://redis.io/documentation)
- [Redis安全指南](https://redis.io/topics/security)
- [Lingualink认证指南](./AUTHENTICATION_GUIDE.md)
- [性能优化建议](../optimization_suggestions.md) 