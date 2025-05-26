import os
import tempfile
from typing import List, Optional
from werkzeug.utils import secure_filename
from fastapi import UploadFile
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    """音频处理器类，处理音频文件的上传、验证和临时存储"""
    
    def __init__(self):
        self.max_upload_size = settings.max_upload_size
        self.allowed_extensions = set(settings.allowed_extensions)
    
    def is_allowed_file(self, filename: str) -> bool:
        """检查文件扩展名是否被允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def validate_file_size(self, content: bytes) -> bool:
        """验证文件大小"""
        return len(content) <= self.max_upload_size
    
    async def save_upload_file(self, upload_file: UploadFile) -> str:
        """
        保存上传的文件到临时位置
        
        Args:
            upload_file: FastAPI UploadFile对象
            
        Returns:
            str: 临时文件路径
            
        Raises:
            ValueError: 文件验证失败
            IOError: 文件保存失败
        """
        # 验证文件名
        if not upload_file.filename:
            raise ValueError("No file selected")
        
        if not self.is_allowed_file(upload_file.filename):
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}")
        
        # 读取文件内容
        try:
            contents = await upload_file.read()
        except Exception as e:
            raise IOError(f"Failed to read uploaded file: {e}")
        
        # 验证文件大小
        if not self.validate_file_size(contents):
            max_size_mb = self.max_upload_size // (1024 * 1024)
            raise ValueError(f"File too large. Maximum {max_size_mb}MB allowed.")
        
        # 生成安全的文件名
        filename = secure_filename(upload_file.filename)
        suffix = os.path.splitext(filename)[1]
        
        # 保存到临时文件
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="lingualink_") as temp_f:
                temp_f.write(contents)
                temp_file_path = temp_f.name
            
            logger.info(f"Audio file saved temporarily to: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            raise IOError(f"Failed to save temporary file: {e}")
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        清理临时文件
        
        Args:
            file_path: 临时文件路径
            
        Returns:
            bool: 清理是否成功
        """
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Temporary file {file_path} deleted.")
                return True
            except Exception as e:
                logger.error(f"Error deleting temporary file {file_path}: {e}")
                return False
        return True
    
    def get_file_info(self, file_path: str) -> dict:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 文件信息
        """
        if not os.path.exists(file_path):
            return {"exists": False}
        
        stat = os.stat(file_path)
        return {
            "exists": True,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": os.path.splitext(file_path)[1].lower(),
            "created_at": stat.st_ctime
        } 