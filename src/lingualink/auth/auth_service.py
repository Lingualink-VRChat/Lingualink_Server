import hashlib
import secrets
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """简单的鉴权服务"""
    
    def __init__(self):
        self.api_keys: Dict[str, dict] = {}
        self._load_api_keys()
    
    def _load_api_keys(self):
        """从配置加载API密钥"""
        for api_key in settings.api_keys:
            self.api_keys[api_key] = {
                "name": f"key_{api_key[:8]}",
                "created_at": datetime.now(),
                "expires_at": None,
                "is_active": True,
                "usage_count": 0,
                "rate_limit": None
            }
        logger.info(f"Loaded {len(self.api_keys)} API keys")
    
    def generate_api_key(self, name: Optional[str] = None, expires_in_days: Optional[int] = None) -> str:
        """生成新的API密钥"""
        api_key = f"lls_{secrets.token_urlsafe(32)}"
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        self.api_keys[api_key] = {
            "name": name or f"key_{api_key[:8]}",
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "is_active": True,
            "usage_count": 0,
            "rate_limit": None
        }
        
        logger.info(f"Generated new API key: {name or api_key[:8]}")
        return api_key
    
    def verify_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        if not settings.auth_enabled:
            return True
            
        if api_key not in self.api_keys:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            return False
        
        key_info = self.api_keys[api_key]
        
        # 检查是否激活
        if not key_info["is_active"]:
            logger.warning(f"Inactive API key attempted: {api_key[:8]}...")
            return False
        
        # 检查是否过期
        if key_info["expires_at"] and datetime.now() > key_info["expires_at"]:
            logger.warning(f"Expired API key attempted: {api_key[:8]}...")
            return False
        
        # 更新使用次数
        key_info["usage_count"] += 1
        logger.debug(f"API key verified: {key_info['name']}, usage: {key_info['usage_count']}")
        
        return True
    
    def revoke_api_key(self, api_key: str) -> bool:
        """撤销API密钥"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["is_active"] = False
            logger.info(f"API key revoked: {self.api_keys[api_key]['name']}")
            return True
        return False
    
    def list_api_keys(self) -> List[dict]:
        """列出所有API密钥信息（不包含密钥本身）"""
        return [
            {
                "name": info["name"],
                "created_at": info["created_at"],
                "expires_at": info["expires_at"],
                "is_active": info["is_active"],
                "usage_count": info["usage_count"],
                "rate_limit": info["rate_limit"]
            }
            for info in self.api_keys.values()
        ]
    
    def get_key_info(self, api_key: str) -> Optional[dict]:
        """获取API密钥信息"""
        return self.api_keys.get(api_key)


# 全局鉴权服务实例
auth_service = AuthService() 