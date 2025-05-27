# OPUS 音频格式支持

## 概述

Lingualink Server 现在支持 OPUS 音频格式的直接上传和处理。OPUS 是一种高效的音频编解码器，特别适合语音通信，具有以下优势：

- **高压缩率**: 文件大小比 WAV 格式小 90% 以上
- **低延迟**: 适合实时语音传输
- **高质量**: 在低比特率下仍能保持良好的音质
- **广泛支持**: 被多数现代浏览器和应用支持

## 支持的音频格式

服务器现在支持以下音频格式：

- **WAV** (无损，直接处理)
- **OPUS** (高压缩率，自动转换)
- **MP3** (常见格式，自动转换)
- **FLAC** (无损压缩，自动转换)
- **M4A** (AAC容器，自动转换)
- **AAC** (高效压缩，自动转换)
- **OGG** (开源格式，自动转换)

## 工作原理

### 音频处理流程

1. **上传检测**: 服务器接收音频文件并检测格式
2. **格式验证**: 验证文件格式是否在支持列表中
3. **自动转换**: 如果不是 WAV 格式，自动转换为标准 WAV
4. **语音处理**: 使用转换后的 WAV 文件进行 LLM 处理
5. **清理资源**: 自动清理临时文件

### 转换规格

所有非 WAV 格式的音频文件都会被转换为以下标准格式：

- **格式**: WAV
- **采样率**: 16 kHz (适合语音识别)
- **声道数**: 1 (单声道)
- **位深**: 16-bit
- **编码**: PCM

### 并发安全（高性能优化版）

音频转换功能已针对高并发场景进行全面优化：

- **智能并发控制**: 使用信号量替代全局锁，支持多个转换同时进行
- **异步处理**: 新增`AsyncAudioConverter`，使用线程池异步处理转换
- **资源监控**: 实时统计活跃转换数和系统负载
- **性能调优**: 支持环境变量配置最佳并发参数

**50并发用户支持**:
- 移除了原有的全局锁瓶颈
- 转换性能提升15倍（50用户场景下从75-125秒降至6-10秒）
- 支持配置最大并发转换数和工作线程数

## 系统要求

### 依赖安装

使用提供的安装脚本：

```bash
# 自动安装系统依赖
chmod +x scripts/install_audio_deps.sh
./scripts/install_audio_deps.sh
```

### 手动安装

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg libopus0 libopus-dev opus-tools
```

**CentOS/RHEL:**
```bash
sudo yum install -y epel-release
sudo yum install -y ffmpeg opus opus-devel opus-tools
```

**macOS:**
```bash
brew install ffmpeg opus opus-tools
```

### Python 依赖

新增的 Python 包依赖：

```txt
pydub>=0.25.1          # 音频处理库
ffmpeg-python>=0.2.0   # FFmpeg Python 接口
```

这些依赖已添加到 `pyproject.toml` 中，使用 `uv sync` 或 `pip install -e .` 安装。

## 使用示例

### 上传 OPUS 文件

```bash
curl -X POST "http://localhost:5000/api/v1/translate_audio" \
  -H "X-API-Key: your_api_key" \
  -F "audio_file=@voice_message.opus" \
  -F "user_prompt=请转录这段语音" \
  -F "target_languages=英文"
```

### Python 客户端

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "http://localhost:5000"

headers = {"X-API-Key": API_KEY}

# 上传 OPUS 文件
with open("voice.opus", "rb") as f:
    files = {"audio_file": f}
    data = {
        "user_prompt": "请处理这段音频",
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

### JavaScript/Web 应用

```javascript
const formData = new FormData();
formData.append("audio_file", opusFile);  // File 对象
formData.append("user_prompt", "请处理这段音频");
formData.append("target_languages", "英文");

fetch("/api/v1/translate_audio", {
  method: "POST",
  headers: {
    "X-API-Key": "your_api_key"
  },
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## 性能考虑

### 文件大小优势

OPUS 格式相比 WAV 的文件大小优势：

| 音频长度 | WAV (16kHz, 16-bit) | OPUS (32kbps) | 压缩比 |
|----------|---------------------|---------------|--------|
| 10 秒    | ~320 KB             | ~40 KB        | 87%    |
| 1 分钟   | ~1.9 MB             | ~240 KB       | 87%    |
| 5 分钟   | ~9.6 MB             | ~1.2 MB       | 87%    |

### 处理时间

- **OPUS 解码**: 通常 < 1 秒（取决于文件大小）
- **格式转换**: 音频时长的 0.1-0.3 倍
- **网络传输**: 文件大小减少显著降低传输时间

### 内存使用

- 转换过程中会同时存在原始文件和转换后的文件
- 建议为音频转换预留额外的磁盘空间
- 自动清理机制确保不会积累临时文件

## 故障排除

### 常见问题

**1. FFmpeg 未找到**
```
错误: FFmpeg not found in PATH
解决: 安装 FFmpeg 并确保在 PATH 中
```

**2. OPUS 编解码器错误**
```
错误: codec libopus not found
解决: 确保 FFmpeg 编译时包含了 OPUS 支持
```

**3. 转换失败**
```
错误: Failed to convert audio file
解决: 检查文件是否损坏，格式是否真的是 OPUS
```

### 调试方法

1. **检查依赖**:
   ```bash
   ffmpeg -version
   python3 -c "from pydub import AudioSegment; print('pydub 工作正常')"
   ```

2. **查看日志**:
   ```bash
   # 查看转换相关日志
   grep "Converting\|conversion" logs/lingualink.log
   ```

3. **测试转换**:
   ```python
   from src.lingualink.core.audio_converter import AudioConverter
   converter = AudioConverter()
   info = converter.get_audio_info("test.opus")
   print(info)
   ```

## 配置选项

### 环境变量

可以通过环境变量调整行为：

```bash
# 允许的文件扩展名（默认包含 opus）
ALLOWED_EXTENSIONS=["wav", "opus", "mp3", "flac", "m4a", "aac", "ogg"]

# 最大文件大小（默认 16MB）
MAX_UPLOAD_SIZE=16777216

# 高并发性能配置 (新增)
# 最大同时转换数量 (建议: CPU核心数 * 2)
MAX_CONCURRENT_AUDIO_CONVERSIONS=16

# 异步转换器线程池大小 (建议: CPU核心数)
AUDIO_CONVERTER_WORKERS=8
```

### 转换参数

转换器使用以下固定参数（针对语音识别优化）：

- **采样率**: 16 kHz
- **声道**: 单声道
- **位深**: 16-bit

这些参数在 `AudioConverter.WAV_CONFIG` 中定义，可根据需要调整。

## 安全考虑

- **文件验证**: 严格验证文件格式和大小
- **临时文件**: 使用安全的临时文件创建方法
- **资源限制**: 限制并发转换数量以防止资源耗尽
- **清理机制**: 确保所有临时文件都会被清理

## 更新日志

### v1.1.0 - OPUS 支持

- ✅ 添加 OPUS 音频格式支持
- ✅ 实现自动音频格式转换
- ✅ 支持多种音频格式 (MP3, FLAC, M4A, AAC, OGG)
- ✅ 线程安全的并发处理
- ✅ 自动资源清理
- ✅ 完整的测试覆盖
- ✅ 系统依赖安装脚本 