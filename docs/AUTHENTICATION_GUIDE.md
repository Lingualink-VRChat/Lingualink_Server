# 🔐 Lingualink Server 认证配置指南

## 📋 概述

Lingualink Server 使用两种不同的认证机制来保护 API 访问：

1. **API_KEYS** - 用于 API 访问控制的简单密钥认证
2. **SECRET_KEY** - 用于内部加密和签名的应用密钥

## 🔑 API_KEYS vs SECRET_KEY 详解

### API_KEYS（API 访问密钥）

**用途**：用于验证客户端对 API 的访问权限

**特点**：
- ✅ 可以有多个密钥（支持多个客户端）
- ✅ 客户端在请求时需要提供
- ✅ 可以独立生成、撤销和管理
- ✅ 用于 HTTP 请求的身份验证

**使用场景**：
- 客户端调用 API 时提供的凭证
- 可以为不同的客户端/应用分发不同的密钥
- 密钥泄露时可以单独撤销某个密钥

### SECRET_KEY（应用密钥）

**用途**：用于应用内部的数据加密、签名和安全操作

**特点**：
- ✅ 只有一个，整个应用共享
- ✅ 客户端永远不应该知道这个密钥
- ✅ 用于服务器内部的安全操作
- ✅ 更改后会影响所有现有的加密数据

**使用场景**：
- JWT Token 签名
- 会话数据加密
- 内部数据签名验证
- 其他需要服务器端加密的场景

## 🚀 快速配置

### 步骤 1：生成 SECRET_KEY

```bash
# 生成一个强随机密钥
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

示例输出：
```
SECRET_KEY=xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1aB4cD7eF0gH2jK5m
```

### 步骤 2：生成 API_KEYS

```bash
# 使用项目提供的工具生成 API 密钥
uv run generate-api-key --name "主要客户端"

# 或者直接使用 Python
python3 -c "import secrets; print('lls_' + secrets.token_urlsafe(32))"
```

示例输出：
```
Generated API Key: lls_xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1
Key Name: 主要客户端

Please save this API key securely. You will need it to access the API.
Add it to your .env file as:
API_KEYS=["your-existing-keys", "lls_xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1"]
```

### 步骤 3：配置 .env 文件

```env
# 应用密钥（用于内部加密）
SECRET_KEY=xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1aB4cD7eF0gH2jK5m

# API 访问密钥（用于客户端认证）
API_KEYS=["lls_xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1"]

# 启用认证
AUTH_ENABLED=true
```

## 🔧 详细配置

### 多个 API 密钥管理

```env
# 支持多个 API 密钥，用于不同的客户端
API_KEYS=[
  "lls_client1_key_here",
  "lls_client2_key_here", 
  "lls_mobile_app_key_here",
  "lls_web_dashboard_key_here"
]
```

### 生产环境安全配置

```env
# 生产环境强密钥示例
SECRET_KEY=prod_very_long_and_random_secret_key_change_this_in_production_123456
API_KEYS=["lls_prod_client_key_12345", "lls_prod_admin_key_67890"]

# 启用认证
AUTH_ENABLED=true

# 较短的令牌过期时间
ACCESS_TOKEN_EXPIRE_MINUTES=15
```

## 📡 客户端使用方式

### 方式 1：X-API-Key 头部（推荐）

```bash
curl -X POST "http://localhost:5000/api/v1/translate_audio" \
  -H "X-API-Key: lls_xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1" \
  -F "audio_file=@test.wav" \
  -F "user_prompt=请处理下面的音频。"
```

### 方式 2：Authorization Bearer 头部

```bash
curl -X POST "http://localhost:5000/api/v1/translate_audio" \
  -H "Authorization: Bearer lls_xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1" \
  -F "audio_file=@test.wav" \
  -F "user_prompt=请处理下面的音频。"
```

### Python 客户端示例

```python
import requests

# 配置
API_BASE_URL = "http://localhost:5000/api/v1"
API_KEY = "lls_xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1"

# 请求头
headers = {
    "X-API-Key": API_KEY
}

# 健康检查
response = requests.get(f"{API_BASE_URL}/health", headers=headers)
print(response.json())

# 音频翻译
with open("test.wav", "rb") as audio_file:
    files = {"audio_file": audio_file}
    data = {
        "user_prompt": "请处理下面的音频。",
        "target_languages": ["英文", "日文"]
    }
    response = requests.post(
        f"{API_BASE_URL}/translate_audio",
        headers=headers,
        files=files,
        data=data
    )
    print(response.json())
```

## 🛡️ 安全最佳实践

### 1. SECRET_KEY 安全

```bash
# ✅ 好的做法
SECRET_KEY=very_long_random_string_with_at_least_32_characters_12345

# ❌ 不好的做法
SECRET_KEY=123456
SECRET_KEY=my-secret-key
SECRET_KEY=your-secret-key-change-this  # 默认值
```

**注意事项**：
- 至少 32 个字符长度
- 使用随机生成的字符串
- 不要使用可预测的内容
- 生产环境必须更改默认值

### 2. API_KEYS 安全

```bash
# ✅ 好的做法
API_KEYS=["lls_very_long_random_api_key_string"]

# ❌ 不好的做法
API_KEYS=["simple-key"]
API_KEYS=["lls_example_key_replace_with_real_key"]  # 默认值
```

**注意事项**：
- 使用 `lls_` 前缀便于识别
- 至少 32 个字符的随机字符串
- 定期轮换密钥
- 为不同客户端使用不同密钥

### 3. 密钥管理

```bash
# 生成强密钥的便捷命令
generate_secret() {
    python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
}

generate_api_key() {
    python3 -c "import secrets; print('lls_' + secrets.token_urlsafe(32))"
}

# 使用
generate_secret
generate_api_key
```

## 🔄 密钥轮换

### 轮换 SECRET_KEY

**⚠️ 注意**：更改 SECRET_KEY 会使所有现有的 JWT token 失效

```bash
# 1. 生成新的 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. 更新 .env 文件
# SECRET_KEY=新生成的密钥

# 3. 重启服务
python3 manage.py restart
```

### 轮换 API_KEYS

**✅ 安全**：可以渐进式轮换，不会影响现有客户端

```bash
# 1. 生成新的 API 密钥
uv run generate-api-key --name "新客户端"

# 2. 添加到现有密钥列表（保持旧密钥）
API_KEYS=["旧密钥1", "旧密钥2", "新密钥"]

# 3. 重启服务
python3 manage.py restart

# 4. 更新客户端使用新密钥

# 5. 移除旧密钥
API_KEYS=["新密钥"]
```

## 🧪 测试认证

### 测试脚本

```bash
#!/bin/bash

API_KEY="your-api-key-here"
BASE_URL="http://localhost:5000/api/v1"

echo "=== 测试健康检查 ==="
curl -H "X-API-Key: $API_KEY" "$BASE_URL/health"

echo -e "\n=== 测试认证验证 ==="
curl -H "X-API-Key: $API_KEY" "$BASE_URL/auth/verify"

echo -e "\n=== 测试无效密钥 ==="
curl -H "X-API-Key: invalid-key" "$BASE_URL/health"
```

### 验证配置

```bash
# 检查配置是否正确加载
python3 -c "
from config.settings import settings
print(f'认证启用: {settings.auth_enabled}')
print(f'API密钥数量: {len(settings.api_keys)}')
print(f'SECRET_KEY长度: {len(settings.secret_key)}')
"
```

## 🐛 常见问题

### 1. 认证失败

**错误**: `{"detail": "Invalid API key"}`

**解决方案**：
```bash
# 检查 API 密钥是否在配置中
python3 -c "
from config.settings import settings
print('配置的API密钥:', settings.api_keys)
"

# 检查密钥格式
echo "你的密钥应该以 'lls_' 开头"
```

### 2. 配置加载失败

**错误**: `ValidationError`

**解决方案**：
```bash
# 检查 .env 文件格式
cat .env | grep -E "(SECRET_KEY|API_KEYS)"

# API_KEYS 必须是 JSON 格式的字符串数组
# 正确格式: API_KEYS=["key1", "key2"]
# 错误格式: API_KEYS=key1,key2
```

### 3. 禁用认证（仅开发环境）

```env
# 临时禁用认证用于测试
AUTH_ENABLED=false
```

**注意**：生产环境绝不应该禁用认证！

## 📚 相关文档

- [快速启动指南](../QUICK_START.md)
- [服务管理指南](../SERVICE_MANAGEMENT.md)
- [API 文档](http://localhost:5000/docs)（启动服务后访问） 