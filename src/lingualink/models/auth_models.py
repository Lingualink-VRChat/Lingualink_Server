from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class APIKeyAuth(BaseModel):
    """API Key 鉴权模型"""
    api_key: str = Field(description="API密钥")
    name: Optional[str] = Field(default=None, description="密钥名称")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    is_active: bool = Field(default=True, description="是否激活")
    usage_count: int = Field(default=0, description="使用次数")
    rate_limit: Optional[int] = Field(default=None, description="速率限制(每分钟)")


class TokenAuth(BaseModel):
    """Token 鉴权模型"""
    access_token: str = Field(description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间(秒)")


class AuthRequest(BaseModel):
    """鉴权请求模型"""
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    api_key: Optional[str] = Field(default=None, description="API密钥")


class AuthResponse(BaseModel):
    """鉴权响应模型"""
    status: str = Field(description="鉴权状态")
    message: str = Field(description="响应消息")
    token: Optional[TokenAuth] = Field(default=None, description="令牌信息") 