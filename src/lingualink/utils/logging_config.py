import logging
import sys
from typing import Optional
from config.settings import settings


def setup_logging(level: Optional[str] = None) -> None:
    """
    设置应用日志配置
    
    Args:
        level: 日志级别，如果不提供则根据debug模式自动设置
    """
    if level is None:
        level = "DEBUG" if settings.debug else "INFO"
    
    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    # 设置应用日志器
    app_logger = logging.getLogger("lingualink")
    app_logger.setLevel(getattr(logging, level.upper()))
    
    app_logger.info(f"Logging configured with level: {level}")
    app_logger.info(f"Debug mode: {settings.debug}")


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 日志器实例
    """
    return logging.getLogger(f"lingualink.{name}") 