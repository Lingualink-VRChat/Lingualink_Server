from fastapi import APIRouter, Depends
from datetime import datetime
import time
import logging
import psutil
import os

from ..models.request_models import HealthCheckResponse
from ..auth.dependencies import get_current_api_key
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
    "/performance",
    summary="性能监控",
    description="获取系统性能和音频转换统计信息",
    dependencies=[Depends(get_current_api_key)]
)
async def get_performance_stats():
    """获取性能统计信息"""
    try:
        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取当前进程信息
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        # 获取音频处理统计（需要从全局实例获取）
        from ..api.audio_routes import audio_processor
        audio_stats = audio_processor.get_performance_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": round((disk.used / disk.total) * 100, 1)
                }
            },
            "process": {
                "memory_mb": round(process_memory.rss / (1024**2), 2),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads()
            },
            "audio_processing": {
                **audio_stats,
                "config": {
                    "max_concurrent_conversions": settings.max_concurrent_audio_conversions,
                    "max_converter_workers": settings.audio_converter_workers,
                    "max_upload_size_mb": settings.max_upload_size // (1024 * 1024),
                    "supported_formats": list(settings.allowed_extensions)
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return {
            "error": "Failed to retrieve performance statistics",
            "details": str(e)
        }


@router.get(
    "/concurrent-status", 
    summary="并发状态",
    description="获取当前音频转换的并发状态",
    dependencies=[Depends(get_current_api_key)]
)
async def get_concurrent_status():
    """获取并发处理状态"""
    try:
        from ..api.audio_routes import audio_processor
        
        # 获取转换统计
        conversion_stats = audio_processor.audio_converter.get_conversion_stats()
        
        # 计算利用率
        active_conversions = conversion_stats.get("active_conversions", 0)
        max_concurrent = settings.max_concurrent_audio_conversions
        utilization_percent = (active_conversions / max_concurrent * 100) if max_concurrent > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "concurrent_processing": {
                "active_conversions": active_conversions,
                "max_concurrent_conversions": max_concurrent,
                "utilization_percent": round(utilization_percent, 1),
                "total_conversions": conversion_stats.get("total_conversions", 0),
                "queue_available_slots": max_concurrent - active_conversions
            },
            "worker_pool": {
                "max_workers": settings.audio_converter_workers,
                "estimated_load": "Unknown"  # 难以从ThreadPoolExecutor获取精确信息
            },
            "performance_metrics": {
                "total_requests_processed": audio_processor.request_count,
                "average_processing_time_seconds": round(
                    audio_processor.total_processing_time / max(audio_processor.request_count, 1), 2
                )
            }
        }
    except Exception as e:
        logger.error(f"Error getting concurrent status: {e}")
        return {
            "error": "Failed to retrieve concurrent status",
            "details": str(e)
        }


@router.get(
    "/ping",
    summary="简单ping",
    description="简单的ping接口，用于快速检查服务可用性"
)
async def ping():
    """简单ping"""
    return {"message": "pong", "timestamp": datetime.now().isoformat()} 