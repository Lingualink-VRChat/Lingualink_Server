from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from config.settings import settings
from src.lingualink.utils.logging_config import setup_logging
from src.lingualink.api import audio_router, auth_router, health_router

# 设置日志
setup_logging()

# 创建FastAPI应用
app = FastAPI(
    title="Lingualink Server",
    description="音频转录和翻译服务 - 支持多语言翻译和API密钥鉴权",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router)
app.include_router(audio_router)
app.include_router(auth_router)

# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    import logging
    logger = logging.getLogger("lingualink.main")
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "details": str(exc) if settings.debug else None
        }
    )

# 根路径
@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "Lingualink Server",
        "version": "1.0.0",
        "description": "音频转录和翻译服务",
        "docs": "/docs",
        "health": "/api/v1/health",
        "auth_enabled": settings.auth_enabled
    }

# 启动函数
def start_server():
    """启动服务器"""
    uvicorn.run(
        "src.lingualink.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )

if __name__ == "__main__":
    start_server() 