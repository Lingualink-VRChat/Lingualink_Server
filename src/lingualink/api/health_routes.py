from fastapi import APIRouter
from datetime import datetime
import time
import logging

from ..models.request_models import HealthCheckResponse
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])

# 服务启动时间
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="健康检查",
    description="检查服务运行状态"
)
async def health_check():
    """服务健康检查"""
    current_time = time.time()
    uptime = current_time - _start_time
    
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        uptime=uptime
    )


@router.get(
    "/status",
    summary="服务状态",
    description="获取详细的服务状态信息"
)
async def get_status():
    """获取服务状态"""
    current_time = time.time()
    uptime = current_time - _start_time
    
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": uptime,
        "uptime_formatted": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
        "version": "1.0.0",
        "config": {
            "auth_enabled": settings.auth_enabled,
            "max_upload_size_mb": settings.max_upload_size // (1024 * 1024),
            "allowed_extensions": settings.allowed_extensions,
            "default_target_languages": settings.default_target_languages,
            "vllm_server_url": settings.vllm_server_url,
            "model_name": settings.model_name
        }
    }


@router.get(
    "/ping",
    summary="简单ping",
    description="简单的ping接口，用于快速检查服务可用性"
)
async def ping():
    """简单ping"""
    return {"message": "pong", "timestamp": datetime.now().isoformat()} 