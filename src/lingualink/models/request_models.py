from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AudioTranslationRequest(BaseModel):
    """音频翻译请求模型"""
    user_prompt: str = Field(default="请处理下面的音频。", description="用户提示词")
    target_languages: Optional[List[str]] = Field(default=None, description="目标语言列表")


class AudioTranslationResponse(BaseModel):
    """音频翻译响应模型"""
    status: str = Field(description="响应状态: success 或 error")
    message: Optional[str] = Field(default=None, description="错误消息")
    duration_seconds: Optional[float] = Field(default=None, description="处理耗时(秒)")
    data: Optional[Dict[str, Any]] = Field(default=None, description="处理结果数据")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(description="服务状态")
    timestamp: str = Field(description="检查时间")
    version: str = Field(description="服务版本")
    uptime: float = Field(description="运行时间(秒)")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    status: str = Field(default="error", description="响应状态")
    message: str = Field(description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情") 