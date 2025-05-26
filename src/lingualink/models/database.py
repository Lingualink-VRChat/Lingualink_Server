"""
数据库模型定义
使用SQLite管理API密钥
"""

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class APIKey(Base):
    """API密钥数据模型"""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # None表示永不过期
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    rate_limit = Column(Integer, nullable=True)  # 每分钟请求限制
    description = Column(Text, nullable=True)  # 密钥描述
    created_by = Column(String(255), default='system', nullable=False)  # 创建者
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间
    is_admin = Column(Boolean, default=False, nullable=False)  # 是否为管理员密钥
    
    def __repr__(self):
        return f"<APIKey(name='{self.name}', active={self.is_active}, expires_at={self.expires_at})>"
    
    def is_expired(self):
        """检查密钥是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """检查密钥是否有效（活跃且未过期）"""
        return self.is_active and not self.is_expired()
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'rate_limit': self.rate_limit,
            'description': self.description,
            'created_by': self.created_by,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_expired': self.is_expired(),
            'is_valid': self.is_valid(),
            'is_admin': self.is_admin
        }


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/api_keys.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        # 确保数据库目录存在
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建数据库连接
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        self.create_tables()
        
        logger.info(f"Database initialized at: {db_path}")
    
    def create_tables(self):
        """创建数据库表"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# 全局数据库管理器实例
db_manager = None


def get_db_manager():
    """获取数据库管理器实例"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


def get_db_session():
    """获取数据库会话的便捷函数"""
    return get_db_manager().get_session() 