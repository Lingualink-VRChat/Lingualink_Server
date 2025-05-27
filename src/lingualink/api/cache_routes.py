from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from ..auth.redis_cache import redis_cache
from ..auth.dependencies import get_current_admin_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


@router.get(
    "/stats",
    summary="缓存统计",
    description="获取Redis缓存统计信息（需要管理员权限）"
)
async def get_cache_stats(
    current_api_key: str = Depends(get_current_admin_api_key)
) -> Dict[str, Any]:
    """获取缓存统计信息"""
    try:
        stats = redis_cache.get_cache_stats()
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to get cache stats: {str(e)}"
            }
        )


@router.get(
    "/health",
    summary="缓存健康检查",
    description="检查Redis缓存连接状态"
)
async def check_cache_health() -> Dict[str, Any]:
    """检查缓存健康状态"""
    try:
        is_healthy = redis_cache.health_check()
        
        return {
            "status": "success",
            "data": {
                "redis_enabled": redis_cache.enabled,
                "redis_healthy": is_healthy,
                "message": "Redis is healthy" if is_healthy else "Redis is not available"
            }
        }
    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        return {
            "status": "error",
            "data": {
                "redis_enabled": False,
                "redis_healthy": False,
                "message": f"Cache health check failed: {str(e)}"
            }
        }


@router.post(
    "/clear",
    summary="清空缓存",
    description="清空所有API密钥缓存（需要管理员权限）"
)
async def clear_cache(
    current_api_key: str = Depends(get_current_admin_api_key)
) -> Dict[str, Any]:
    """清空所有缓存"""
    try:
        success = redis_cache.clear_all_cache()
        
        if success:
            logger.info(f"Cache cleared by admin: {current_api_key[:8]}...")
            return {
                "status": "success",
                "message": "All API key cache cleared successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to clear cache or cache is disabled"
            }
            
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to clear cache: {str(e)}"
            }
        )


@router.delete(
    "/invalidate/{api_key_prefix}",
    summary="使特定密钥缓存失效",
    description="使特定API密钥的缓存失效（需要管理员权限）"
)
async def invalidate_api_key_cache(
    api_key_prefix: str,
    current_api_key: str = Depends(get_current_admin_api_key)
) -> Dict[str, Any]:
    """使特定API密钥缓存失效"""
    try:
        # 注意：这里需要完整的API密钥，而不是前缀
        # 在实际使用中，管理员应该提供完整的API密钥
        success = redis_cache.invalidate_api_key(api_key_prefix)
        
        if success:
            logger.info(f"Cache invalidated for key {api_key_prefix[:8]}... by admin: {current_api_key[:8]}...")
            return {
                "status": "success",
                "message": f"Cache invalidated for API key: {api_key_prefix[:8]}..."
            }
        else:
            return {
                "status": "warning",
                "message": "Cache entry not found or cache is disabled"
            }
            
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to invalidate cache: {str(e)}"
            }
        ) 