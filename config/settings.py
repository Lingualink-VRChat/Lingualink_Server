import os
import json
from typing import List, Optional, Dict, Any, Union
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """应用配置类"""
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=5000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # LLM 服务配置 (单后端，向后兼容)
    vllm_server_url: str = Field(default="http://192.168.8.6:8000", env="VLLM_SERVER_URL")
    model_name: str = Field(default="qwenOmni7", env="MODEL_NAME")
    api_key: str = Field(default="abc123", env="API_KEY")
    
    # 多LLM后端配置 (新增)
    llm_backends: Optional[List[Dict[str, Any]]] = Field(default=None, env="LLM_BACKENDS")
    
    # 负载均衡配置 (新增)
    load_balance_enabled: Optional[bool] = Field(default=None, env="LOAD_BALANCE_ENABLED")  # 显式控制开关
    load_balance_strategy: str = Field(default="round_robin", env="LOAD_BALANCE_STRATEGY")
    health_check_interval: float = Field(default=30.0, env="HEALTH_CHECK_INTERVAL")
    max_retries: int = Field(default=2, env="MAX_RETRIES")
    failure_threshold: int = Field(default=3, env="FAILURE_THRESHOLD")
    
    # 文件上传配置
    max_upload_size: int = Field(default=16 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 16MB
    allowed_extensions: List[str] = Field(default=["wav", "opus", "mp3", "flac", "m4a", "aac", "ogg"], env="ALLOWED_EXTENSIONS")
    
    # 音频转换性能配置 (新增)
    max_concurrent_audio_conversions: int = Field(default=10, env="MAX_CONCURRENT_AUDIO_CONVERSIONS")
    audio_converter_workers: int = Field(default=5, env="AUDIO_CONVERTER_WORKERS")
    
    # 鉴权配置
    auth_enabled: bool = Field(default=True, env="AUTH_ENABLED")
    secret_key: str = Field(default="your-secret-key-change-this", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Redis缓存配置
    redis_enabled: bool = Field(default=False, env="REDIS_ENABLED")
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    api_key_cache_ttl: int = Field(default=300, env="API_KEY_CACHE_TTL")  # 5分钟缓存
    
    # 数据库配置
    database_path: str = Field(default="data/api_keys.db", env="DATABASE_PATH")
    
    # 默认语言配置
    default_target_languages: List[str] = Field(default=["英文", "日文"], env="DEFAULT_TARGET_LANGUAGES")
    default_user_query: str = Field(default="请处理下面的音频。", env="DEFAULT_USER_QUERY")
    
    @validator('llm_backends', pre=True)
    def parse_llm_backends(cls, v):
        """解析LLM后端配置"""
        if v is None:
            return None
        
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        
        if isinstance(v, list):
            return v
        
        return None
    
    @validator('load_balance_strategy')
    def validate_load_balance_strategy(cls, v):
        """验证负载均衡策略"""
        valid_strategies = [
            "round_robin", "weighted_round_robin", "least_connections",
            "random", "consistent_hash", "response_time"
        ]
        if v not in valid_strategies:
            raise ValueError(f"负载均衡策略必须是以下之一: {valid_strategies}")
        return v
    
    def is_load_balance_enabled(self) -> bool:
        """判断是否启用负载均衡"""
        # 如果显式设置了开关，使用显式设置
        if self.load_balance_enabled is not None:
            return self.load_balance_enabled
        
        # 否则根据是否配置了多后端自动判断
        return self.llm_backends is not None and len(self.llm_backends) > 1
    
    def get_effective_backends(self) -> List[Dict[str, Any]]:
        """获取有效的后端配置"""
        if self.llm_backends:
            return self.llm_backends
        
        # 如果没有多后端配置，返回单后端配置
        return [{
            "name": "default",
            "url": self.vllm_server_url,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "weight": 1,
            "max_connections": 50,
            "timeout": 30.0,
            "priority": 0,
            "tags": []
        }]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局设置实例
settings = Settings() 