from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
from .auth_service import auth_service
from config.settings import settings
from ..models.database import APIKey, get_db_session

# API Key 认证方式
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Bearer Token 认证方式  
security = HTTPBearer(auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """验证API密钥依赖项"""
    if not settings.auth_enabled:
        return "auth_disabled"
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "API key is required. Please provide X-API-Key header."
            }
        )
    
    is_valid, _ = auth_service.verify_api_key(api_key) # Ignore is_admin for basic verification
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error", 
                "message": "Invalid or expired API key."
            }
        )
    
    return api_key


async def get_current_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header)
) -> str:
    """获取当前API密钥（支持多种认证方式）"""
    if not settings.auth_enabled:
        return "auth_disabled"
    
    # 优先使用 X-API-Key header
    if api_key:
        is_valid, _ = auth_service.verify_api_key(api_key)
        if is_valid:
            return api_key
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": "Invalid API key in X-API-Key header."
                }
            )
    
    # 其次使用 Bearer token
    if credentials:
        token = credentials.credentials
        is_valid, _ = auth_service.verify_api_key(token)
        if is_valid:
            return token
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": "Invalid API key in Authorization header."
                }
            )
    
    # 都没有提供
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "status": "error",
            "message": "Authentication required. Please provide API key via X-API-Key header or Authorization: Bearer <token>."
        }
    ) 


async def get_current_admin_api_key(
    api_key: str = Depends(get_current_api_key) # Reuse the basic key getter
) -> str:
    """
    获取当前API密钥，并验证其是否为管理员密钥。
    依赖于 get_current_api_key 先成功获取并验证密钥的基本有效性。
    """
    if api_key == "auth_disabled": # 处理认证禁用的情况
        return api_key

    session = get_db_session() # Assuming you have this utility from database.py
    try:
        key_record = session.query(APIKey).filter(APIKey.api_key == api_key).first()
        # At this point, get_current_api_key has already validated the key exists and is active/not expired.
        # We just need to check the is_admin flag.
        if key_record and key_record.is_admin:
            return api_key
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "message": "Admin privileges required for this operation."
                }
            )
    finally:
        session.close() 