# Lingualink Server 使用说明

## 快速开始

### 1. 安装和配置

```bash
# 克隆项目
git clone <your-repo-url>
cd Lingualink_Server

# 安装依赖
uv sync

# 复制环境配置
cp .env.template .env

# 生成API密钥
uv run generate-api-key --name "my-first-key"
```

### 2. 配置环境变量

编辑 `.env` 文件：

```env
# 必须配置的项目
VLLM_SERVER_URL=http://your-vllm-server:8000  # 你的vLLM服务地址
MODEL_NAME=your-model-name                    # 你的模型名称
API_KEY=your-llm-api-key                      # vLLM服务的API密钥

# 添加生成的API密钥
API_KEYS=["lls_your_generated_api_key_here"]

# 可选配置
DEBUG=true                                    # 开发模式
AUTH_ENABLED=true                            # 启用鉴权
```

### 3. 启动服务

```bash
# 方式1: 使用uv命令
uv run lingualink-server

# 方式2: 使用启动脚本
./start.sh          # Linux/macOS
start.bat           # Windows

# 方式3: 直接运行Python模块
uv run python -m src.lingualink.main
```

服务启动后访问：
- **API文档**: http://localhost:5000/docs
- **健康检查**: http://localhost:5000/api/v1/health

## 基本使用

### 1. 验证API密钥

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/v1/auth/verify
```

### 2. 音频翻译

```bash
curl -X POST "http://localhost:5000/api/v1/translate_audio" \
  -H "X-API-Key: your-api-key" \
  -F "audio_file=@your-audio.wav" \
  -F "user_prompt=请处理下面的音频。" \
  -F "target_languages=英文" \
  -F "target_languages=日文"
```

### 3. 查看支持的格式

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/v1/supported_formats
```

## API密钥管理

Lingualink Server 使用基于 SQLite 数据库的 API 密钥管理系统。
你可以使用 `manage_api_keys.py` 工具来管理密钥。

### 生成新密钥

#### 本地模式 (推荐)
```bash
# 生成永久密钥
python3 manage_api_keys.py --local generate --name "my-key" --description "My main key"

# 生成30天有效期的管理员密钥
python3 manage_api_keys.py --local generate --name "temp-admin" --expires-in-days 30 --description "Temporary admin access" --make-admin
```

#### 远程模式 (需要服务器运行和有效的管理员API密钥)
```bash
# 远程生成永久密钥
python3 manage_api_keys.py --api-key <admin_key> generate --name "remote-key"

# 远程生成带有效期密钥
python3 manage_api_keys.py --api-key <admin_key> generate --name "remote-temp" --expires-in-days 7
```

#### 通过API生成
```bash
curl -X POST "http://localhost:5000/api/v1/auth/generate_key" \
  -H "X-API-Key: <your_admin_key>" \
  -d "name=api-generated-key&expires_in_days=30&description=Key via API"
```

### 管理现有密钥

#### 列出所有密钥
```bash
# 本地模式
python3 manage_api_keys.py --local list

# 本地模式 (包含已撤销密钥)
python3 manage_api_keys.py --local list --include-inactive

# 远程模式
python3 manage_api_keys.py --api-key <your_key> list
```

#### 验证密钥状态
```bash
# 本地模式
python3 manage_api_keys.py --local verify --api-key <key_to_verify>

# 远程模式
python3 manage_api_keys.py --api-key <key_to_verify> verify
```

#### 撤销密钥
```bash
# 本地模式
python3 manage_api_keys.py --local revoke --key <key_to_revoke>

# 远程模式
python3 manage_api_keys.py --api-key <admin_key> revoke --key <key_to_revoke>
```

#### 更新密钥描述 (通过API)
```bash
curl -X PUT "http://localhost:5000/api/v1/auth/update_description" \
  -H "X-API-Key: <admin_key>" \
  -d "api_key_to_update=<key_to_update>&description=New description"
```

#### 清理过期密钥 (通过API)
```bash
curl -X POST "http://localhost:5000/api/v1/auth/cleanup_expired" \
  -H "X-API-Key: <admin_key>"
```

#### 设置/撤销管理员权限 (仅本地模式)
```bash
python3 manage_api_keys.py --local set-admin <api_key_value> true
python3 manage_api_keys.py --local set-admin <api_key_value> false
```

## 开发和调试

### 启用调试模式

在 `.env` 文件中设置：
```env
DEBUG=true
```

### 禁用鉴权（仅开发）

```env
AUTH_ENABLED=false
```

### 查看日志

服务会输出详细的日志信息，包括：
- 请求处理过程
- API密钥验证
- LLM服务调用
- 错误信息

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_auth.py -v

# 运行测试并显示覆盖率
uv run pytest --cov=src/lingualink
```

## 常见问题

### 1. 服务无法启动

**问题**: `ImportError` 或模块找不到
**解决**: 
```bash
# 确保依赖已安装
uv sync

# 检查Python版本
python --version  # 需要3.13+
```

### 2. API密钥无效

**问题**: `401 Unauthorized`
**解决**:
- 检查密钥格式是否正确（以 `lls_` 开头）
- 确认密钥是否已在数据库中创建并激活
- 验证密钥是否已过期或被撤销
- 使用 `python3 manage_api_keys.py --local list` 查看密钥状态

### 3. 文件上传失败

**问题**: 文件格式或大小错误
**解决**:
- 确保文件是 `.wav` 格式
- 检查文件大小不超过16MB
- 验证文件没有损坏

### 4. LLM服务连接失败

**问题**: 无法连接到vLLM服务
**解决**:
- 检查 `VLLM_SERVER_URL` 配置
- 确认vLLM服务正在运行
- 验证网络连接和防火墙设置

### 5. 响应解析错误

**问题**: LLM返回的内容无法解析
**解决**:
- 检查模型是否支持音频输入
- 调整 `user_prompt` 提示词
- 查看原始响应内容（在 `raw_text` 字段中）

## 性能优化

### 1. 文件大小限制

根据需要调整最大上传文件大小：
```env
MAX_UPLOAD_SIZE=33554432  # 32MB
```

### 2. 并发处理

FastAPI自动处理并发请求，但可以通过以下方式优化：
- 使用更多的worker进程
- 配置适当的超时时间
- 监控内存使用情况

### 3. 缓存策略

考虑为频繁请求的音频文件添加缓存：
- 文件哈希缓存
- 结果缓存
- Redis缓存

## 部署建议

### 1. 生产环境配置

```env
DEBUG=false
SECRET_KEY=your-very-secure-secret-key-here
AUTH_ENABLED=true
```

### 2. 反向代理

使用Nginx配置HTTPS和负载均衡：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 监控和日志

- 配置日志轮转
- 设置监控告警
- 使用健康检查端点

## 扩展开发

### 1. 添加新的音频格式

1. 更新 `ALLOWED_EXTENSIONS` 配置
2. 修改 `AudioProcessor` 类
3. 更新LLM服务的音频处理逻辑

### 2. 添加新的API端点

1. 在 `src/lingualink/api/` 下创建新的路由文件
2. 在 `main.py` 中注册路由
3. 添加相应的测试

### 3. 自定义鉴权策略

1. 修改 `AuthService` 类
2. 更新依赖项函数
3. 添加新的鉴权模型

## 支持

如果遇到问题：
1. 查看日志输出
2. 检查配置文件
3. 运行测试套件
4. 查阅API文档
5. 提交Issue 