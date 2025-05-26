import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置类"""
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=5000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # LLM 服务配置
    vllm_server_url: str = Field(default="http://192.168.8.6:8000", env="VLLM_SERVER_URL")
    model_name: str = Field(default="qwenOmni7", env="MODEL_NAME")
    api_key: str = Field(default="abc123", env="API_KEY")
    
    # 文件上传配置
    max_upload_size: int = Field(default=16 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 16MB
    allowed_extensions: List[str] = Field(default=["wav"], env="ALLOWED_EXTENSIONS")
    
    # 鉴权配置
    auth_enabled: bool = Field(default=True, env="AUTH_ENABLED")
    secret_key: str = Field(default="your-secret-key-change-this", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 数据库配置
    database_path: str = Field(default="data/api_keys.db", env="DATABASE_PATH")
    
    # 默认语言配置
    default_target_languages: List[str] = Field(default=["英文", "日文"], env="DEFAULT_TARGET_LANGUAGES")
    default_user_query: str = Field(default="请处理下面的音频。", env="DEFAULT_USER_QUERY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局设置实例
settings = Settings() 