# 🔐 Lingualink Server 认证配置指南 v2.0

## 📋 概述

Lingualink Server 使用以下认证和授权机制：

1. **API密钥 (API Keys)** - 用于客户端访问API的身份验证，存储在SQLite数据库中。
2. **应用密钥 (SECRET_KEY)** - 用于应用内部的加密和签名操作，配置在 `.env` 文件中。

## 🔑 API密钥 vs 应用密钥

### API密钥 (API Keys)

**用途**: 验证客户端对API的访问权限
**存储**: SQLite数据库 (`data/api_keys.db`)
**管理**: 通过 `manage_api_keys.py` 工具或API接口进行管理

**特点**:
- ✅ 可以动态创建、撤销和管理多个密钥
- ✅ 支持设置密钥名称、描述和有效期
- ✅ 记录使用次数和最后使用时间
- ✅ 客户端在请求时通过 `X-API-Key` 或 `Authorization: Bearer` 头部提供

**使用场景**:
- 控制不同客户端或应用的API访问
- 为临时访问或特定场景创建带有效期的密钥

### 应用密钥 (SECRET_KEY)

**用途**: 应用内部的数据加密、签名和安全操作
**存储**: `.env` 文件
**管理**: 手动在 `.env` 文件中配置

**特点**:
- ✅ 只有一个，整个应用共享
- ✅ 客户端永远不应该知道此密钥
- ✅ 更改后会影响所有现有的加密数据和会话

**使用场景**:
- JWT Token 签名 (如果未来实现)
- 会话数据加密
- 内部数据签名验证
- 其他需要服务器端加密的场景

## 🚀 快速配置

### 步骤 1：生成应用密钥 (SECRET_KEY)

```bash
# 生成一个强随机密钥
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

将生成的 `SECRET_KEY` 添加到你的 `.env` 文件中。

### 步骤 2：配置数据库路径 (可选)

默认API密钥数据库路径为 `data/api_keys.db`。如果需要更改，请在 `.env` 文件中设置：
```env
DATABASE_PATH=your/custom/path/api_keys.db
```

### 步骤 3：生成第一个API密钥

使用 `manage_api_keys.py` 工具在本地生成第一个API密钥。强烈建议将第一个密钥设置为**管理员密钥**，以便后续管理。
```bash
# 生成一个名为 "admin-key" 的永久管理员密钥
python3 manage_api_keys.py --local generate --name "admin-key" --description "Administrator key" --make-admin

# 或者，如果已生成密钥，可以后续设置为管理员
# python3 manage_api_keys.py --local generate --name "initial-key"
# python3 manage_api_keys.py --local set-admin <initial_key_value> true
```

**重要**: 请妥善保管生成的API密钥，它将用于后续API请求的认证。

### 步骤 4：配置 `.env` 文件示例

```env
# 应用密钥 (用于内部加密)
SECRET_KEY=xK9mN2pQ7rS4vT8wZ1aB5cD6eF9gH3jL4mN7pQ0rS5tU8wX1aB4cD7eF0gH2jK5m

# 数据库文件路径 (用于存储API密钥)
DATABASE_PATH=data/api_keys.db

# 启用认证
AUTH_ENABLED=true
```

**注意**: `API_KEYS` 和 `API_KEYS_METADATA` 已被移除，因为密钥现在存储在数据库中。

## 🔧 API密钥管理 (`manage_api_keys.py`)

`manage_api_keys.py` 是一个强大的命令行工具，用于管理API密钥。它支持本地模式（直接操作数据库）和远程模式（通过API与运行中的服务交互）。

### 本地模式 (推荐)

本地模式直接操作SQLite数据库，无需运行服务器。适合初始化设置和维护。

**基本命令格式**:
`python3 manage_api_keys.py --local [命令] [选项]`

**常用命令**:
- `generate`: 生成新密钥
  ```bash
  python3 manage_api_keys.py --local generate --name "my-client" --expires-in-days 30 --description "Client key"
  ```
- `list`: 列出所有密钥
  ```bash
  python3 manage_api_keys.py --local list
  python3 manage_api_keys.py --local list --include-inactive  # 包含已撤销的
  ```
- `revoke`: 撤销密钥
  ```bash
  python3 manage_api_keys.py --local revoke --key <api_key_to_revoke>
  ```
- `verify`: 验证密钥 (显示详细信息)
  ```bash
  python3 manage_api_keys.py --local verify --api-key <api_key_to_verify>
  ```
- `set-admin`: 设置或撤销密钥的管理员权限 (仅本地模式)
  ```bash
  python3 manage_api_keys.py --local set-admin <api_key_value> true
  python3 manage_api_keys.py --local set-admin <api_key_value> false
  ```

### 远程模式

远程模式通过API与正在运行的Lingualink Server实例交互。需要提供一个有效的 **管理员API密钥** 进行认证。

**基本命令格式**:
`python3 manage_api_keys.py --api-key <your_auth_key> [命令] [选项]`

**常用命令** (与本地模式类似，但通过API执行):
- `generate`, `list`, `revoke`, `verify`

**示例**:
```bash
# 使用现有密钥 <admin_key> 生成一个新密钥
python3 manage_api_keys.py --api-key <admin_key> generate --name "new-user" --expires-in-days 7
```

## ⏰ API密钥有效期管理

### 有效期概念

API密钥支持设置有效期，提供更好的安全控制：

- **永久密钥**: `expires_at: null`，适用于长期服务
- **临时密钥**: 设置具体过期时间，适用于临时访问、测试或租期使用

### 设置有效期的方式

#### 1. 生成时设置
```bash
# 本地模式生成30天有效期的密钥
python3 manage_api_keys.py --local generate --name "temp-client" --expires-in-days 30

# 远程模式通过API设置
curl -X POST "http://localhost:5000/api/v1/auth/generate_key" \
  -H "X-API-Key: <admin_key>" \
  -d "name=temp-key&expires_in_days=30&description=API generated temp key"
```

### 监控和管理有效期

#### 1. 查看密钥状态
```bash
# 使用管理工具查看所有密钥状态 (本地模式)
python3 manage_api_keys.py --local list

# 输出示例：
# 🗝️  共找到 2 个API密钥:
# ====================================================================================================
# 
# #1 密钥: admin-key
#    ID: 1
#    创建时间: 2024-01-01 12:00:00
#    过期时间: 永不过期
#    使用次数: 156
#    最后使用: 2024-01-15 10:00:00
#    状态: ✅ 永久有效
#    活跃状态: ✅ 活跃
#    创建者: local_cli
#    描述: Administrator key
# 
# #2 密钥: temp-user
#    ID: 2
#    创建时间: 2024-01-15 12:00:00
#    过期时间: 2024-02-14 12:00:00
#    使用次数: 42
#    最后使用: 2024-01-20 08:30:00
#    状态: ✅ 15天后过期
#    活跃状态: ✅ 活跃
#    创建者: local_cli
#    权限: 👑 管理员
#    描述: Temporary access for testing
```

#### 2. 验证单个密钥
```bash
python3 manage_api_keys.py --local verify --api-key <api_key_to_verify>
```

### 自动清理过期密钥

服务器提供了API端点 `/api/v1/auth/cleanup_expired` 来自动将已过期的密钥设置为非活跃状态。你可以定期调用此端点。

```bash
curl -X POST "http://localhost:5000/api/v1/auth/cleanup_expired" -H "X-API-Key: <admin_key>"
```

## 🛡️ 安全最佳实践

### 1. 应用密钥 (SECRET_KEY) 安全
- 保持 `SECRET_KEY` 的机密性，不要泄露。
- 使用至少32个字符的随机字符串。
- 定期轮换 `SECRET_KEY`，特别是在发生安全事件后。

### 2. API密钥安全
- **最小权限原则**: 为不同客户端或服务生成不同的API密钥。普通密钥不应授予管理员权限。
- **管理员密钥保护**: 严格保护管理员密钥，仅用于必要的管理操作。
- **有效期**: 为临时访问或测试密钥设置合理的有效期。
- **定期审计**: 使用 `manage_api_keys.py --local list --include-inactive` 定期审计密钥列表。
- **安全存储**: 客户端应安全存储其API密钥。
- **密钥轮换**: 定期轮换长期使用的API密钥。

### 3. 数据库安全
- 保护 `data/api_keys.db` 文件的访问权限。
- 定期备份数据库文件。

## 🔄 密钥轮换

### 轮换应用密钥 (SECRET_KEY)

**⚠️ 注意**: 更改 `SECRET_KEY` 会使所有依赖于它的现有加密数据（如会话）失效。

1. 生成新的 `SECRET_KEY`。
2. 更新 `.env` 文件中的 `SECRET_KEY` 值。
3. 重启 Lingualink Server。

### 轮换API密钥

1. 使用 `manage_api_keys.py` 或API生成新的API密钥，并设置合适的有效期和描述。
   ```bash
   python3 manage_api_keys.py --local generate --name "new-client-key-v2" --expires-in-days 90
   ```
2. 将新密钥分发给相关客户端。
3. 监控旧密钥的使用情况 (`last_used_at` 字段)。
4. 在确认所有客户端已切换到新密钥后，撤销旧密钥。
   ```bash
   python3 manage_api_keys.py --local revoke --key <old_api_key>
   ```

## 🧪 测试认证

### 测试脚本

```bash
#!/bin/bash

API_KEY="<your_generated_api_key>"
BASE_URL="http://localhost:5000/api/v1"

echo "=== 测试健康检查 (需要有效密钥) ==="
curl -H "X-API-Key: $API_KEY" "$BASE_URL/health"

echo -e "\n=== 测试认证验证 ==="
curl -H "X-API-Key: $API_KEY" "$BASE_URL/auth/verify"

echo -e "\n=== 测试无效密钥 ==="
curl -H "X-API-Key: invalid-key" "$BASE_URL/health"
```

### 验证配置

```bash
# 检查配置是否正确加载 (主要检查AUTH_ENABLED和DATABASE_PATH)
python3 -c "from config.settings import settings; print(f'认证启用: {settings.auth_enabled}'); print(f'数据库路径: {settings.database_path}')"

# 检查数据库文件是否存在
ls -l data/api_keys.db
```

## 🐛 常见问题

### 1. 认证失败

**错误**: `{"detail": "Invalid or expired API key."}` 或 `{"detail": "Admin privileges required for this operation."}`

**解决方案**:
- 确认提供的API密钥是否正确。
- 使用 `python3 manage_api_keys.py --local verify --api-key <your_key>` 检查密钥状态（是否激活、是否过期、是否为管理员）。
- 确保证书启用 (`AUTH_ENABLED=true` in `.env`)。
- 如果操作需要管理员权限，请确保使用的密钥是管理员密钥。

### 2. 数据库问题

**错误**: `sqlalchemy.exc...` 或无法连接数据库

**解决方案**:
- 确认 `DATABASE_PATH` 在 `.env` 文件中配置正确。
- 检查 `data/` 目录 (或自定义路径) 是否有写入权限。
- 确保SQLite3已正确安装和配置。

### 3. 禁用认证 (仅开发环境)

在 `.env` 文件中设置:
```env
AUTH_ENABLED=false
```
**注意**: 生产环境绝不应该禁用认证！

## 📚 相关文档

- [快速启动指南](../QUICK_START.md)
- [服务管理指南](../SERVICE_MANAGEMENT.md)
- [API 文档](http://localhost:5000/docs) (启动服务后访问) 