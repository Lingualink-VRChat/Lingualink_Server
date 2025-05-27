import hashlib
import secrets
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from config.settings import settings
from ..models.database import APIKey, get_db_session
from .redis_cache import redis_cache
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """基于数据库的鉴权服务"""
    
    def __init__(self):
        """初始化鉴权服务"""
        logger.info("Auth service initialized with database backend")
    
    def generate_api_key(self, name: Optional[str] = None, expires_in_days: Optional[int] = None, 
                        description: Optional[str] = None, created_by: str = "system",
                        is_admin: bool = False) -> str:
        """
        生成新的API密钥
        
        Args:
            name: 密钥名称
            expires_in_days: 过期天数
            description: 密钥描述
            created_by: 创建者
            is_admin: 是否为管理员密钥
            
        Returns:
            str: 生成的API密钥
        """
        api_key = f"lls_{secrets.token_urlsafe(32)}"
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # 保存到数据库
        session = get_db_session()
        try:
            key_record = APIKey(
                api_key=api_key,
                name=name or f"key_{api_key[:8]}",
                expires_at=expires_at,
                description=description,
                created_by=created_by,
                is_admin=is_admin
            )
            session.add(key_record)
            session.commit()
            
            logger.info(f"Generated new API key: {name or key_record.name}")
            return api_key
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to generate API key: {e}")
            raise
        finally:
            session.close()
    
    def verify_api_key(self, api_key: str) -> tuple[bool, bool]:
        """
        验证API密钥（支持Redis缓存）
        
        Args:
            api_key: API密钥
            
        Returns:
            tuple[bool, bool]: (is_valid, is_admin)
        """
        if not settings.auth_enabled:
            return True, False
        
        # 首先尝试从Redis缓存获取
        cached_result = redis_cache.get_api_key_auth(api_key)
        if cached_result is not None:
            is_valid, is_admin = cached_result
            if is_valid:
                # 异步更新使用统计（不影响响应时间）
                self._async_update_usage_stats(api_key)
                logger.debug(f"API key verified from cache: {api_key[:8]}...")
                return True, is_admin
        
        # 缓存未命中，查询数据库
        return self._verify_api_key_from_db(api_key)
    
    def _verify_api_key_from_db(self, api_key: str) -> tuple[bool, bool]:
        """
        从数据库验证API密钥
        
        Args:
            api_key: API密钥
            
        Returns:
            tuple[bool, bool]: (is_valid, is_admin)
        """
        session = get_db_session()
        try:
            key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
            
            if not key_record:
                logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
                return False, False  # valid, is_admin
            
            is_admin = key_record.is_admin
            
            if not key_record.is_valid():
                if key_record.is_expired():
                    logger.warning(f"Expired API key attempted: {api_key[:8]}...")
                else:
                    logger.warning(f"Inactive API key attempted: {api_key[:8]}...")
                return False, is_admin
            
            # 更新使用次数和最后使用时间
            key_record.usage_count += 1
            key_record.last_used_at = datetime.utcnow()
            session.commit()
            
            # 缓存验证结果
            redis_cache.set_api_key_auth(api_key, True, is_admin)
            
            logger.debug(f"API key verified from DB: {key_record.name}, usage: {key_record.usage_count}")
            return True, is_admin
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error verifying API key: {e}")
            return False, False
        finally:
            session.close()
    
    def _async_update_usage_stats(self, api_key: str):
        """
        异步更新API密钥使用统计（用于缓存命中的情况）
        
        Args:
            api_key: API密钥
        """
        # 这里可以用异步队列来批量更新，暂时用同步方式
        try:
            session = get_db_session()
            key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
            if key_record:
                key_record.usage_count += 1
                key_record.last_used_at = datetime.utcnow()
                session.commit()
            session.close()
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
    
    def revoke_api_key(self, api_key: str) -> bool:
        """
        撤销API密钥（设置为非活跃状态）
        
        Args:
            api_key: 要撤销的API密钥
            
        Returns:
            bool: 是否成功撤销
        """
        session = get_db_session()
        try:
            key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
            
            if not key_record:
                return False
            
            key_record.is_active = False
            session.commit()
            
            # 立即清除缓存
            redis_cache.invalidate_api_key(api_key)
            
            logger.info(f"API key revoked: {key_record.name}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error revoking API key: {e}")
            return False
        finally:
            session.close()
    
    def list_api_keys(self, include_inactive: bool = False) -> List[Dict]:
        """
        列出所有API密钥信息（不包含密钥本身）
        
        Args:
            include_inactive: 是否包含已撤销的密钥
            
        Returns:
            List[Dict]: 密钥信息列表
        """
        session = get_db_session()
        try:
            query = session.query(APIKey)
            if not include_inactive:
                query = query.filter(APIKey.is_active == True)
            
            keys = query.all()
            return [key.to_dict() for key in keys]
            
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return []
        finally:
            session.close()
    
    def get_key_info(self, api_key: str) -> Optional[Dict]:
        """
        获取API密钥信息
        
        Args:
            api_key: API密钥
            
        Returns:
            Optional[Dict]: 密钥信息
        """
        session = get_db_session()
        try:
            key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
            
            if key_record:
                return key_record.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting key info: {e}")
            return None
        finally:
            session.close()
    
    def update_key_description(self, api_key: str, description: str) -> bool:
        """
        更新密钥描述
        
        Args:
            api_key: API密钥
            description: 新的描述
            
        Returns:
            bool: 是否成功更新
        """
        session = get_db_session()
        try:
            key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
            
            if not key_record:
                return False
            
            key_record.description = description
            session.commit()
            
            logger.info(f"Updated description for API key: {key_record.name}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating key description: {e}")
            return False
        finally:
            session.close()
    
    def set_admin_status(self, api_key: str, is_admin: bool) -> bool:
        """
        设置密钥的管理员状态
        
        Args:
            api_key: API密钥
            is_admin: 是否设为管理员
            
        Returns:
            bool: 是否成功设置
        """
        session = get_db_session()
        try:
            key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
            
            if not key_record:
                logger.warning(f"Attempted to set admin status for non-existent key: {api_key[:8]}...")
                return False
            
            key_record.is_admin = is_admin
            session.commit()
            
            logger.info(f"Admin status for API key {key_record.name} set to {is_admin}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error setting admin status for key {api_key[:8]}: {e}")
            return False
        finally:
            session.close()
    
    def cleanup_expired_keys(self) -> int:
        """
        清理已过期的密钥（设置为非活跃状态）
        
        Returns:
            int: 清理的密钥数量
        """
        session = get_db_session()
        try:
            now = datetime.utcnow()
            expired_keys = session.query(APIKey).filter(
                APIKey.expires_at < now,
                APIKey.is_active == True
            ).all()
            
            count = 0
            for key in expired_keys:
                key.is_active = False
                count += 1
            
            session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired API keys")
            
            return count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up expired keys: {e}")
            return 0
        finally:
            session.close()


# 全局鉴权服务实例
auth_service = AuthService() 