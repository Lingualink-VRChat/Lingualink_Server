# Lingualink Server API 文档

## 概述

Lingualink Server 提供音频转录和翻译服务的 RESTful API。所有 API 都需要有效的 API 密钥进行鉴权。

**基础 URL**: `http://localhost:5000`

## 鉴权

### API 密钥认证

所有受保护的端点都需要提供有效的 API 密钥。支持两种认证方式：

#### 方式 1: X-API-Key 头部 (推荐)
```http
X-API-Key: lls_your_api_key_here
```

#### 方式 2: Authorization Bearer 头部
```http
Authorization: Bearer lls_your_api_key_here
```

### 获取 API 密钥

使用管理工具生成：
```bash
# 本地模式生成 (推荐，无需服务器运行)
python3 manage_api_keys.py --local generate --name "my-key" --expires-in-days 30 --description "Test key"

# 远程模式生成 (需要服务器运行和有效密钥)
python3 manage_api_keys.py --api-key <admin_key> generate --name "my-key" --expires-in-days 30
```

## 端点详情

### 1. 健康检查

#### GET /api/v1/health
检查服务运行状态。

**无需鉴权**

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "1.0.0",
  "uptime": 3600.5
}
```

#### GET /api/v1/ping
简单的 ping 检查。

**无需鉴权**

**响应示例**:
```json
{
  "message": "pong",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### GET /api/v1/status
获取详细的服务状态信息。

**无需鉴权**

**响应示例**:
```json
{
  "status": "running",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "uptime_seconds": 3600.5,
  "uptime_formatted": "1h 0m 0s",
  "version": "1.0.0",
  "config": {
    "auth_enabled": true,
    "max_upload_size_mb": 16,
    "allowed_extensions": ["wav"],
    "default_target_languages": ["英文", "日文"],
    "vllm_server_url": "http://192.168.8.6:8000",
    "model_name": "qwenOmni7"
  }
}
```

### 2. 音频处理

#### POST /api/v1/translate_audio
上传音频文件进行转录和翻译。

**需要鉴权**

**请求参数**:
- `audio_file` (file, required): 音频文件 (.wav 格式)
- `user_prompt` (string, optional): 用户提示词，默认为"请处理下面的音频。"
- `target_languages` (array[string], optional): 目标语言列表，如 ["英文", "日文"]

**请求示例**:
```bash
curl -X POST "http://localhost:5000/api/v1/translate_audio" \
  -H "X-API-Key: lls_your_api_key" \
  -F "audio_file=@example.wav" \
  -F "user_prompt=请转录并翻译这段音频" \
  -F "target_languages=英文" \
  -F "target_languages=日文"
```

**成功响应示例**:
```json
{
  "status": "success",
  "duration_seconds": 2.5,
  "data": {
    "raw_text": "原文：你好，世界！\n英文：Hello, world!\n日文：こんにちは、世界！",
    "原文": "你好，世界！",
    "英文": "Hello, world!",
    "日文": "こんにちは、世界！"
  }
}
```

**错误响应示例**:
```json
{
  "status": "error",
  "message": "File type not allowed. Allowed types: wav",
  "details": null
}
```

#### GET /api/v1/supported_formats
获取支持的音频格式信息。

**需要鉴权**

**响应示例**:
```json
{
  "status": "success",
  "data": {
    "supported_formats": ["wav"],
    "max_file_size_mb": 16,
    "default_target_languages": ["英文", "日文"]
  }
}
```

### 3. 鉴权管理

#### GET /api/v1/auth/verify
验证当前 API 密钥的有效性。

**需要鉴权**

**响应示例**:
```json
{
  "status": "success",
  "message": "API key is valid",
  "data": {
    "id": 1,
    "name": "my-key",
    "created_at": "2024-01-01T12:00:00Z",
    "expires_at": "2024-02-01T12:00:00Z",
    "is_active": true,
    "usage_count": 42,
    "rate_limit": null,
    "description": "Test key",
    "created_by": "local_cli",
    "last_used_at": "2024-01-15T10:00:00Z",
    "is_expired": false,
    "is_valid": true
  }
}
```

**字段说明**:
- `id`: 密钥ID
- `expires_at`: 过期时间，`null` 表示永不过期
- `description`: 密钥描述
- `created_by`: 创建者
- `last_used_at`: 最后使用时间
- `is_expired`: 是否已过期
- `is_valid`: 是否有效（活跃且未过期）

#### POST /api/v1/auth/generate_key
生成新的 API 密钥。

**需要鉴权**

**请求参数**:
- `name` (string, optional): 密钥名称
- `expires_in_days` (integer, optional): 过期天数
- `description` (string, optional): 密钥描述

**请求示例**:
```bash
curl -X POST "http://localhost:5000/api/v1/auth/generate_key" \
  -H "X-API-Key: lls_your_api_key" \
  -d "name=new-key&expires_in_days=30&description=New key for testing"
```

**响应示例**:
```json
{
  "status": "success",
  "message": "API key generated successfully",
  "data": {
    "api_key": "lls_new_generated_key_here",
    "name": "new-key",
    "expires_in_days": 30,
    "expires_at": "2024-02-01T12:00:00Z",
    "description": "New key for testing"
  }
}
```

#### GET /api/v1/auth/keys
列出所有 API 密钥信息（不包含密钥本身）。

**需要鉴权**

**请求参数**:
- `include_inactive` (boolean, optional, default=false): 是否包含已撤销的密钥

**响应示例**:
```json
{
  "status": "success",
  "data": {
    "keys": [
      {
        "id": 1,
        "name": "my-key",
        "created_at": "2024-01-01T12:00:00Z",
        "expires_at": "2024-02-01T12:00:00Z",
        "is_active": true,
        "usage_count": 42,
        "rate_limit": null,
        "description": "Test key",
        "created_by": "local_cli",
        "last_used_at": "2024-01-15T10:00:00Z",
        "is_expired": false,
        "is_valid": true
      }
    ],
    "total": 1
  }
}
```

#### POST /api/v1/auth/revoke_key
撤销指定的 API 密钥。

**需要鉴权**

**请求参数**:
- `api_key_to_revoke` (string, required): 要撤销的 API 密钥

**请求示例**:
```bash
curl -X POST "http://localhost:5000/api/v1/auth/revoke_key" \
  -H "X-API-Key: lls_your_api_key" \
  -d "api_key_to_revoke=lls_key_to_revoke"
```

**响应示例**:
```json
{
  "status": "success",
  "message": "API key revoked successfully"
}
```

### 4. 更新密钥描述

#### PUT /api/v1/auth/update_description
更新指定API密钥的描述信息。

**需要鉴权**

**请求参数**:
- `api_key_to_update` (string, required): 要更新的API密钥
- `description` (string, required): 新的描述信息

**请求示例**:
```bash
curl -X PUT "http://localhost:5000/api/v1/auth/update_description" \
  -H "X-API-Key: lls_your_api_key" \
  -d "api_key_to_update=lls_key_to_update&description=New key description"
```

**响应示例**:
```json
{
  "status": "success",
  "message": "API key description updated successfully"
}
```

### 5. 清理过期密钥

#### POST /api/v1/auth/cleanup_expired
清理所有已过期的API密钥。

**需要鉴权**

**请求示例**:
```bash
curl -X POST "http://localhost:5000/api/v1/auth/cleanup_expired" \
  -H "X-API-Key: lls_your_api_key"
```

**响应示例**:
```json
{
  "status": "success",
  "message": "Cleaned up 5 expired API keys",
  "data": {
    "cleaned_count": 5
  }
}
```

## 错误处理

### HTTP 状态码

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 鉴权失败
- `404 Not Found`: 资源不存在
- `413 Payload Too Large`: 文件过大
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

所有错误响应都遵循统一格式：

```json
{
  "status": "error",
  "message": "错误描述",
  "details": {
    "additional": "error details"
  }
}
```

### 常见错误

#### 1. 鉴权错误
```json
{
  "status": "error",
  "message": "API key is required. Please provide X-API-Key header."
}
```

#### 2. 文件格式错误
```json
{
  "status": "error",
  "message": "File type not allowed. Allowed types: wav"
}
```

#### 3. 文件过大
```json
{
  "status": "error",
  "message": "File too large. Maximum 16MB allowed."
}
```

#### 4. LLM 服务错误
```json
{
  "status": "error",
  "message": "An API call error occurred: Connection timeout",
  "details": {
    "status_code": 500,
    "content": "Internal server error"
  }
}
```

## 速率限制

目前版本暂未实现速率限制，但 API 密钥系统支持为每个密钥设置速率限制。

## 示例代码

### Python 示例

```python
import requests

# 配置
API_KEY = "lls_your_api_key"
BASE_URL = "http://localhost:5000"

headers = {
    "X-API-Key": API_KEY
}

# 健康检查
response = requests.get(f"{BASE_URL}/api/v1/health")
print(response.json())

# 音频翻译
with open("audio.wav", "rb") as f:
    files = {"audio_file": f}
    data = {
        "user_prompt": "请处理下面的音频",
        "target_languages": ["英文", "日文"]
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/translate_audio",
        headers=headers,
        files=files,
        data=data
    )
    print(response.json())
```

### JavaScript 示例

```javascript
const API_KEY = "lls_your_api_key";
const BASE_URL = "http://localhost:5000";

// 健康检查
fetch(`${BASE_URL}/api/v1/health`)
  .then(response => response.json())
  .then(data => console.log(data));

// 音频翻译
const formData = new FormData();
formData.append("audio_file", audioFile);
formData.append("user_prompt", "请处理下面的音频");
formData.append("target_languages", "英文");
formData.append("target_languages", "日文");

fetch(`${BASE_URL}/api/v1/translate_audio`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY
  },
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## 交互式文档

访问 `http://localhost:5000/docs` 获取完整的交互式 API 文档，可以直接在浏览器中测试 API。 