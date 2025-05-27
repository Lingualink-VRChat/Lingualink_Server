# 负载均衡配置指南

## 🎯 配置逻辑

Lingualink Server的负载均衡有三种运行模式：

### 1. **传统单后端模式** (向后兼容)
- **启用条件**: 没有配置`LLM_BACKENDS`，且`LOAD_BALANCE_ENABLED`未设置或为`false`
- **特点**: 完全使用原有代码逻辑，性能最佳，无额外开销
- **适用场景**: 只有一个LLM后端，追求最简配置

### 2. **单后端负载均衡模式**
- **启用条件**: 没有配置`LLM_BACKENDS`，但`LOAD_BALANCE_ENABLED=true`
- **特点**: 启用负载均衡框架但只有一个后端，有健康检查等功能
- **适用场景**: 为将来扩展做准备，或需要健康检查功能

### 3. **多后端负载均衡模式**
- **启用条件**: 配置了`LLM_BACKENDS`，或`LOAD_BALANCE_ENABLED=true`
- **特点**: 完整的负载均衡功能，支持故障转移、性能监控等
- **适用场景**: 多个LLM后端，需要高可用性

## 📝 具体配置示例

### 示例1: 传统单后端 (最简配置)
```env
# 基本配置，和之前完全一样
VLLM_SERVER_URL=http://192.168.8.6:8000
MODEL_NAME=qwenOmni7
API_KEY=abc123

# 不配置 LLM_BACKENDS 和 LOAD_BALANCE_ENABLED
# 系统自动使用传统单后端模式
```

### 示例2: 启用负载均衡但只有单后端
```env
# 基本配置
VLLM_SERVER_URL=http://192.168.8.6:8000
MODEL_NAME=qwenOmni7
API_KEY=abc123

# 显式启用负载均衡
LOAD_BALANCE_ENABLED=true
HEALTH_CHECK_INTERVAL=30.0
```

### 示例3: 多后端负载均衡 (自动启用)
```env
# 配置多个后端，系统自动启用负载均衡
LLM_BACKENDS='[
  {
    "name": "primary",
    "url": "http://192.168.8.6:8000",
    "model_name": "qwenOmni7",
    "api_key": "abc123",
    "weight": 3,
    "max_connections": 50,
    "timeout": 30.0,
    "priority": 0,
    "tags": ["primary", "fast"]
  },
  {
    "name": "backup",
    "url": "http://192.168.8.7:8000",
    "model_name": "qwenOmni7",
    "api_key": "def456",
    "weight": 1,
    "max_connections": 30,
    "timeout": 35.0,
    "priority": 1,
    "tags": ["backup", "stable"]
  }
]'

# 负载均衡配置
LOAD_BALANCE_STRATEGY=weighted_round_robin
HEALTH_CHECK_INTERVAL=30.0
MAX_RETRIES=2
FAILURE_THRESHOLD=3
```

### 示例4: 多后端但禁用负载均衡
```env
# 即使配置了多个后端，也不启用负载均衡
LLM_BACKENDS='[{"name": "backend1", ...}, {"name": "backend2", ...}]'
LOAD_BALANCE_ENABLED=false

# 这种情况下，系统只会使用第一个后端
```

## ⚙️ 配置参数详解

### 核心开关
- **`LOAD_BALANCE_ENABLED`**: 负载均衡总开关
  - `true`: 强制启用负载均衡
  - `false`: 强制禁用负载均衡
  - 不设置: 自动判断（有多后端时启用）

### 后端配置
- **`LLM_BACKENDS`**: JSON格式的后端列表
- **`VLLM_SERVER_URL`**: 单后端模式的服务器地址
- **`MODEL_NAME`**: 模型名称
- **`API_KEY`**: API密钥

### 负载均衡策略
- **`LOAD_BALANCE_STRATEGY`**: 负载均衡算法
  - `round_robin`: 轮询（默认）
  - `weighted_round_robin`: 加权轮询
  - `least_connections`: 最少连接数
  - `random`: 随机
  - `consistent_hash`: 一致性哈希
  - `response_time`: 响应时间最优

### 健康检查
- **`HEALTH_CHECK_INTERVAL`**: 健康检查间隔（秒）
- **`MAX_RETRIES`**: 最大重试次数
- **`FAILURE_THRESHOLD`**: 故障阈值

## 🔄 运行时切换

可以通过API动态管理后端：

```bash
# 查看当前状态
python3 manage_load_balancer.py --api-key <key> status

# 添加新后端
python3 manage_load_balancer.py --api-key <key> add \
  --name new-backend \
  --url http://192.168.8.8:8000 \
  --model-name qwenOmni7 \
  --backend-api-key xyz789

# 切换负载均衡策略
python3 manage_load_balancer.py --api-key <key> strategy set \
  --strategy least_connections
```

## 📊 监控和观察

### 日志输出
系统启动时会输出当前模式：
```
负载均衡未启用，使用传统单后端模式
# 或
启用负载均衡但未检测到多后端配置，使用单后端负载均衡模式  
# 或
负载均衡LLM服务初始化完成，包含 3 个后端
```

### API监控
```bash
# 获取负载均衡器状态
curl -H "X-API-Key: <key>" http://localhost:5000/api/v1/load_balancer/status

# 获取后端列表和指标
curl -H "X-API-Key: <key>" http://localhost:5000/api/v1/load_balancer/backends
```

## 🎯 推荐配置

### 开发环境
```env
# 最简单的单后端配置
VLLM_SERVER_URL=http://localhost:8000
MODEL_NAME=qwenOmni7
API_KEY=your-key
```

### 生产环境
```env
# 多后端高可用配置
LLM_BACKENDS='[
  {
    "name": "primary",
    "url": "http://llm-1.internal:8000",
    "model_name": "qwenOmni7",
    "api_key": "prod-key-1",
    "weight": 3,
    "max_connections": 100,
    "timeout": 30.0
  },
  {
    "name": "secondary", 
    "url": "http://llm-2.internal:8000",
    "model_name": "qwenOmni7",
    "api_key": "prod-key-2",
    "weight": 2,
    "max_connections": 80,
    "timeout": 30.0
  },
  {
    "name": "backup",
    "url": "http://llm-3.internal:8000", 
    "model_name": "qwenOmni7",
    "api_key": "prod-key-3",
    "weight": 1,
    "max_connections": 50,
    "timeout": 45.0
  }
]'

LOAD_BALANCE_STRATEGY=weighted_round_robin
HEALTH_CHECK_INTERVAL=15.0
MAX_RETRIES=3
FAILURE_THRESHOLD=2
``` 