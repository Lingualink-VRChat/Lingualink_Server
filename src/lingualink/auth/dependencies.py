from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
from .auth_service import auth_service
from config.settings import settings

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
    
    if not auth_service.verify_api_key(api_key):
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
        if auth_service.verify_api_key(api_key):
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
        if auth_service.verify_api_key(token):
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