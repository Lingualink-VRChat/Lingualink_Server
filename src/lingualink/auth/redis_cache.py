import redis
import json
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from config.settings import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(self):
        """初始化Redis连接"""
        self._client = None
        self._enabled = settings.redis_enabled
        
        if self._enabled:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    health_check_interval=30,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    retry_on_timeout=True
                )
                # 测试连接
                self._client.ping()
                logger.info(f"Redis cache initialized: {settings.redis_url}")
            except Exception as e:
                logger.warning(f"Redis connection failed, disabling cache: {e}")
                self._enabled = False
                self._client = None
    
    @property
    def enabled(self) -> bool:
        """检查缓存是否可用"""
        return self._enabled and self._client is not None
    
    def _get_cache_key(self, api_key: str) -> str:
        """生成缓存键"""
        # 使用API密钥的前16个字符作为缓存键，避免完整密钥泄露
        return f"api_key_auth:{api_key[:16]}"
    
    def get_api_key_auth(self, api_key: str) -> Optional[Tuple[bool, bool]]:
        """
        从缓存获取API密钥验证结果
        
        Args:
            api_key: API密钥
            
        Returns:
            Optional[Tuple[bool, bool]]: (is_valid, is_admin) 或 None
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self._get_cache_key(api_key)
            cached_data = self._client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for API key: {api_key[:8]}...")
                return data.get("is_valid", False), data.get("is_admin", False)
            
            logger.debug(f"Cache miss for API key: {api_key[:8]}...")
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set_api_key_auth(self, api_key: str, is_valid: bool, is_admin: bool) -> bool:
        """
        缓存API密钥验证结果
        
        Args:
            api_key: API密钥
            is_valid: 是否有效
            is_admin: 是否为管理员
            
        Returns:
            bool: 是否成功缓存
        """
        if not self.enabled:
            return False
        
        # 只缓存有效的密钥，避免缓存无效密钥被暴力破解
        if not is_valid:
            return False
        
        try:
            cache_key = self._get_cache_key(api_key)
            cache_data = {
                "is_valid": is_valid,
                "is_admin": is_admin,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            result = self._client.setex(
                cache_key,
                settings.api_key_cache_ttl,
                json.dumps(cache_data)
            )
            
            if result:
                logger.debug(f"Cached API key auth: {api_key[:8]}... for {settings.api_key_cache_ttl}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def invalidate_api_key(self, api_key: str) -> bool:
        """
        使特定API密钥的缓存失效
        
        Args:
            api_key: API密钥
            
        Returns:
            bool: 是否成功删除
        """
        if not self.enabled:
            return False
        
        try:
            cache_key = self._get_cache_key(api_key)
            result = self._client.delete(cache_key)
            
            if result:
                logger.info(f"Invalidated cache for API key: {api_key[:8]}...")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear_all_cache(self) -> bool:
        """
        清空所有API密钥缓存
        
        Returns:
            bool: 是否成功清空
        """
        if not self.enabled:
            return False
        
        try:
            # 查找所有API密钥缓存
            pattern = "api_key_auth:*"
            keys = self._client.keys(pattern)
            
            if keys:
                deleted_count = self._client.delete(*keys)
                logger.info(f"Cleared {deleted_count} API key cache entries")
                return deleted_count > 0
            
            return True
            
        except Exception as e:
            logger.error(f"Redis clear cache error: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计
        """
        if not self.enabled:
            return {"enabled": False, "error": "Redis not available"}
        
        try:
            info = self._client.info()
            pattern = "api_key_auth:*"
            keys = self._client.keys(pattern)
            
            return {
                "enabled": True,
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "api_key_cache_count": len(keys),
                "cache_ttl": settings.api_key_cache_ttl
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"enabled": False, "error": str(e)}
    
    def health_check(self) -> bool:
        """
        Redis健康检查
        
        Returns:
            bool: Redis是否健康
        """
        if not self.enabled:
            return False
        
        try:
            response = self._client.ping()
            return response is True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# 全局Redis缓存实例
redis_cache = RedisCache() 