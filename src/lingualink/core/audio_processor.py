import os
import tempfile
import time
from typing import List, Optional, Tuple
from werkzeug.utils import secure_filename
from fastapi import UploadFile
from config.settings import settings
import logging
from .audio_converter import AudioConverter, AsyncAudioConverter

logger = logging.getLogger(__name__)


class AudioProcessor:
    """音频处理器类，处理音频文件的上传、验证、转换和临时存储（高并发优化版本）"""
    
    def __init__(self):
        self.max_upload_size = settings.max_upload_size
        self.allowed_extensions = set(settings.allowed_extensions)
        # 使用异步音频转换器以提升并发性能
        self.audio_converter = AudioConverter()
        self.async_audio_converter = AsyncAudioConverter()  # 自动从settings获取配置
        self.request_count = 0
        self.total_processing_time = 0.0
    
    def is_allowed_file(self, filename: str) -> bool:
        """检查文件扩展名是否被允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def validate_file_size(self, content: bytes) -> bool:
        """验证文件大小"""
        return len(content) <= self.max_upload_size
    
    async def save_upload_file(self, upload_file: UploadFile) -> str:
        """
        保存上传的文件到临时目录
        
        Args:
            upload_file: FastAPI UploadFile对象
            
        Returns:
            str: 保存的文件路径
            
        Raises:
            ValueError: 文件验证失败
            IOError: 文件保存失败
        """
        if not upload_file.filename:
            raise ValueError("No filename provided")
        
        if not self.is_allowed_file(upload_file.filename):
            raise ValueError(f"File type not allowed. Allowed extensions: {self.allowed_extensions}")
        
        # 读取文件内容
        content = await upload_file.read()
        
        if not content:
            raise ValueError("Empty file uploaded")
        
        if not self.validate_file_size(content):
            max_size_mb = self.max_upload_size / (1024 * 1024)
            raise ValueError(f"File too large. Maximum size: {max_size_mb:.1f}MB")
        
        # 安全的文件名
        safe_filename = secure_filename(upload_file.filename)
        
        # 创建临时文件
        _, temp_path = tempfile.mkstemp(
            suffix=f"_{safe_filename}",
            prefix="lingualink_upload_"
        )
        
        try:
            # 保存文件内容
            with open(temp_path, 'wb') as temp_file:
                temp_file.write(content)
            
            logger.info(f"File saved: {upload_file.filename} -> {temp_path} "
                       f"({len(content)} bytes)")
            return temp_path
            
        except Exception as e:
            # 清理失败的文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise IOError(f"Failed to save uploaded file: {e}")
    
    async def process_and_convert_audio(self, upload_file: UploadFile) -> Tuple[str, str]:
        """
        处理上传的音频文件，如果需要则转换为WAV格式（高并发优化版本）
        
        Args:
            upload_file: FastAPI UploadFile对象
            
        Returns:
            Tuple[str, str]: (处理后的WAV文件路径, 原始文件路径)
            
        Raises:
            ValueError: 文件验证失败
            IOError: 文件处理失败
        """
        start_time = time.time()
        self.request_count += 1
        current_request = self.request_count
        
        logger.info(f"Processing audio request #{current_request}: {upload_file.filename}")
        
        # 首先保存原始文件
        original_file_path = await self.save_upload_file(upload_file)
        
        try:
            # 检查是否需要转换
            if self.audio_converter.needs_conversion(original_file_path):
                logger.info(f"Converting audio file #{current_request}: {upload_file.filename}")
                
                # 使用异步转换器进行转换
                conversion_start = time.time()
                wav_file_path = await self.async_audio_converter.convert_to_wav_async(original_file_path)
                conversion_time = time.time() - conversion_start
                
                # 验证转换后的文件
                if not os.path.exists(wav_file_path):
                    raise IOError("Audio conversion failed - output file not created")
                
                total_time = time.time() - start_time
                self.total_processing_time += total_time
                
                # 获取转换统计信息
                stats = self.audio_converter.get_conversion_stats()
                
                logger.info(f"Audio conversion completed #{current_request}: "
                          f"{original_file_path} -> {wav_file_path} "
                          f"(conversion: {conversion_time:.2f}s, total: {total_time:.2f}s, "
                          f"active: {stats.get('active_conversions', 0)})")
                
                return wav_file_path, original_file_path
            else:
                # 已经是WAV格式，直接返回
                total_time = time.time() - start_time
                self.total_processing_time += total_time
                
                logger.info(f"Audio file #{current_request} is already in WAV format: "
                          f"{upload_file.filename} (processed in {total_time:.2f}s)")
                return original_file_path, original_file_path
                
        except Exception as e:
            # 转换失败时清理原始文件
            self.cleanup_temp_file(original_file_path)
            
            if "Unsupported audio format" in str(e):
                raise ValueError(f"Unsupported audio format. Supported formats: {', '.join(self.allowed_extensions)}")
            else:
                raise IOError(f"Audio processing failed: {e}")
    
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
    
    def cleanup_audio_files(self, wav_file_path: str, original_file_path: str) -> None:
        """
        清理音频处理过程中产生的所有临时文件
        
        Args:
            wav_file_path: WAV文件路径
            original_file_path: 原始文件路径
        """
        # 清理转换后的WAV文件（如果与原始文件不同）
        if wav_file_path != original_file_path:
            self.audio_converter.cleanup_converted_file(wav_file_path, original_file_path)
        
        # 清理原始文件
        self.cleanup_temp_file(original_file_path)
    
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
    
    def get_performance_stats(self) -> dict:
        """
        获取性能统计信息
        
        Returns:
            dict: 性能统计
        """
        conversion_stats = self.audio_converter.get_conversion_stats()
        avg_processing_time = (
            self.total_processing_time / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            "total_requests": self.request_count,
            "total_processing_time": round(self.total_processing_time, 2),
            "average_processing_time": round(avg_processing_time, 2),
            "conversion_stats": conversion_stats
        } 