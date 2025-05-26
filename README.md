# Lingualink Server

一个基于 FastAPI 的音频转录和翻译服务，支持多语言翻译和简单的 API 密钥鉴权。

## 功能特性

- 🎵 **音频转录**: 支持 WAV 格式音频文件的转录
- 🌍 **多语言翻译**: 支持将转录文本翻译成多种目标语言
- 🔐 **API 密钥鉴权**: 简单而安全的 API 密钥认证系统
- 📊 **健康检查**: 内置服务状态监控
- 📝 **自动文档**: 基于 OpenAPI 的交互式 API 文档
- 🚀 **高性能**: 基于 FastAPI 的异步处理

## 项目结构

```
Lingualink_Server/
├── config/                 # 配置文件
│   └── settings.py         # 应用配置
├── src/lingualink/         # 主要源代码
│   ├── api/                # API 路由
│   │   ├── audio_routes.py # 音频处理路由
│   │   ├── auth_routes.py  # 鉴权路由
│   │   └── health_routes.py# 健康检查路由
│   ├── auth/               # 鉴权模块
│   │   ├── auth_service.py # 鉴权服务
│   │   └── dependencies.py # FastAPI 依赖项
│   ├── core/               # 核心业务逻辑
│   │   ├── llm_service.py  # LLM 服务
│   │   └── audio_processor.py # 音频处理
│   ├── models/             # 数据模型
│   │   ├── request_models.py  # 请求/响应模型
│   │   └── auth_models.py     # 鉴权模型
│   ├── utils/              # 工具模块
│   │   ├── logging_config.py  # 日志配置
│   │   └── key_generator.py   # API 密钥生成器
│   └── main.py             # 主应用入口
├── tests/                  # 测试文件
├── docs/                   # 文档
├── .env.template           # 环境变量模板
├── pyproject.toml          # 项目配置
└── README.md               # 项目说明
```

## 快速开始

### 1. 环境要求

- Python 3.13+
- uv (推荐) 或 pip

### 2. 安装依赖

使用 uv (推荐):
```bash
# 安装依赖
uv sync

# 安装开发依赖
uv sync --dev
```

使用 pip:
```bash
pip install -e .
```

### 3. 配置环境

复制环境变量模板并配置:
```bash
cp .env.template .env
```

编辑 `.env` 文件，配置必要的参数:
```env
# LLM 服务配置
VLLM_SERVER_URL=http://your-vllm-server:8000
MODEL_NAME=your-model-name
API_KEY=your-llm-api-key

# 生成 API 密钥
API_KEYS=["your-generated-api-key"]
```

### 4. 生成 API 密钥

```bash
# 使用 uv
uv run generate-api-key --name "my-first-key"

# 或直接运行
python -m src.lingualink.utils.key_generator --name "my-first-key"
```

将生成的密钥添加到 `.env` 文件的 `API_KEYS` 中。

### 5. 启动服务

```bash
# 使用 uv
uv run lingualink-server

# 或直接运行
python -m src.lingualink.main

# 开发模式 (自动重载)
DEBUG=true uv run lingualink-server
```

服务将在 `http://localhost:5000` 启动。

### 6. 访问文档

- **交互式 API 文档**: http://localhost:5000/docs
- **ReDoc 文档**: http://localhost:5000/redoc
- **健康检查**: http://localhost:5000/api/v1/health

## API 使用

### 鉴权

所有 API 请求都需要提供有效的 API 密钥，支持两种方式:

1. **X-API-Key 头部** (推荐):
```bash
curl -H "X-API-Key: your-api-key" http://localhost:5000/api/v1/health
```

2. **Authorization Bearer 头部**:
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:5000/api/v1/health
```

### 音频翻译

```bash
curl -X POST "http://localhost:5000/api/v1/translate_audio" \
  -H "X-API-Key: your-api-key" \
  -F "audio_file=@your-audio.wav" \
  -F "user_prompt=请处理下面的音频。" \
  -F "target_languages=英文" \
  -F "target_languages=日文"
```

### 管理 API 密钥

```bash
# 生成新密钥
curl -X POST "http://localhost:5000/api/v1/auth/generate_key" \
  -H "X-API-Key: your-api-key" \
  -d "name=new-key&expires_in_days=30"

# 列出所有密钥
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/v1/auth/keys"

# 验证密钥
curl -H "X-API-Key: your-api-key" \
  "http://localhost:5000/api/v1/auth/verify"
```

## 配置选项

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `HOST` | `0.0.0.0` | 服务器监听地址 |
| `PORT` | `5000` | 服务器端口 |
| `DEBUG` | `false` | 调试模式 |
| `VLLM_SERVER_URL` | `http://192.168.8.6:8000` | vLLM 服务器地址 |
| `MODEL_NAME` | `qwenOmni7` | 模型名称 |
| `API_KEY` | `abc123` | LLM API 密钥 |
| `MAX_UPLOAD_SIZE` | `16777216` | 最大上传文件大小 (字节) |
| `ALLOWED_EXTENSIONS` | `["wav"]` | 允许的文件扩展名 |
| `AUTH_ENABLED` | `true` | 是否启用鉴权 |
| `API_KEYS` | `[]` | API 密钥列表 |
| `DEFAULT_TARGET_LANGUAGES` | `["英文", "日文"]` | 默认目标语言 |

### 禁用鉴权 (仅用于开发)

```env
AUTH_ENABLED=false
```

## 开发

### 运行测试

```bash
# 使用 uv
uv run pytest

# 或直接运行
python -m pytest tests/
```

### 代码格式化

```bash
# 格式化代码
uv run black src/ tests/
uv run isort src/ tests/

# 检查代码质量
uv run flake8 src/ tests/
```

### 添加新的依赖

```bash
# 添加运行时依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name
```

## 部署

### Docker 部署 (推荐)

创建 `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY . .

# 安装依赖
RUN uv sync --frozen

# 暴露端口
EXPOSE 5000

# 启动服务
CMD ["uv", "run", "lingualink-server"]
```

构建和运行:
```bash
docker build -t lingualink-server .
docker run -p 5000:5000 --env-file .env lingualink-server
```

### 生产环境配置

1. **设置强密钥**:
```env
SECRET_KEY=your-very-secure-secret-key
```

2. **限制 CORS**:
修改 `src/lingualink/main.py` 中的 CORS 配置。

3. **使用 HTTPS**:
在反向代理 (如 Nginx) 中配置 SSL。

4. **监控和日志**:
配置适当的日志级别和监控系统。

## 故障排除

### 常见问题

1. **导入错误**:
   - 确保使用正确的 Python 版本 (3.13+)
   - 检查依赖是否正确安装

2. **API 密钥无效**:
   - 确保密钥格式正确 (以 `lls_` 开头)
   - 检查密钥是否在 `API_KEYS` 列表中

3. **文件上传失败**:
   - 检查文件格式是否为 WAV
   - 确认文件大小不超过限制

4. **LLM 服务连接失败**:
   - 检查 `VLLM_SERVER_URL` 配置
   - 确认 LLM 服务正在运行

### 日志调试

启用调试模式获取详细日志:
```env
DEBUG=true
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持音频转录和翻译
- API 密钥鉴权系统
- 完整的 API 文档
