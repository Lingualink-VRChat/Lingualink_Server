import os
import tempfile
import logging
from typing import Optional
from pydub import AudioSegment
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 移除全局锁，改为并发控制
class ConcurrencyManager:
    """并发管理器，控制音频转换的并发数量"""
    
    def __init__(self, max_concurrent_conversions: int = 10):
        self.semaphore = threading.Semaphore(max_concurrent_conversions)
        self.active_conversions = 0
        self.total_conversions = 0
        self.lock = threading.Lock()
        
    @contextmanager
    def acquire_conversion_slot(self):
        """获取转换槽位"""
        self.semaphore.acquire()
        try:
            with self.lock:
                self.active_conversions += 1
                self.total_conversions += 1
            yield
        finally:
            with self.lock:
                self.active_conversions -= 1
            self.semaphore.release()
    
    def get_stats(self) -> dict:
        """获取并发统计"""
        with self.lock:
            return {
                "active_conversions": self.active_conversions,
                "total_conversions": self.total_conversions
            }

# 全局并发管理器（使用settings配置）
def get_concurrency_manager():
    """获取并发管理器实例"""
    from config.settings import settings
    return ConcurrencyManager(
        max_concurrent_conversions=settings.max_concurrent_audio_conversions
    )

_concurrency_manager = None

def _get_global_concurrency_manager():
    """获取全局并发管理器"""
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = get_concurrency_manager()
    return _concurrency_manager


class AudioConverter:
    """音频格式转换器，支持多种音频格式转换为WAV，优化为高并发处理"""
    
    # 支持的输入格式
    SUPPORTED_INPUT_FORMATS = {
        'opus': 'opus',
        'ogg': 'ogg',
        'mp3': 'mp3',
        'flac': 'flac',
        'm4a': 'mp4',
        'aac': 'aac',
        'wav': 'wav'  # 直接返回，无需转换
    }
    
    # WAV输出格式配置
    WAV_CONFIG = {
        'format': 'wav',
        'frame_rate': 16000,  # 16kHz采样率，适合语音识别
        'channels': 1,        # 单声道
        'sample_width': 2     # 16-bit
    }
    
    def __init__(self):
        """初始化音频转换器"""
        self._validate_ffmpeg()
        self.conversion_count = 0
        self.local_lock = threading.Lock()
    
    def _validate_ffmpeg(self) -> None:
        """验证FFmpeg是否可用"""
        try:
            from pydub.utils import which
            if not which("ffmpeg"):
                logger.warning("FFmpeg not found in PATH. Some audio formats may not be supported.")
        except Exception as e:
            logger.warning(f"Could not verify FFmpeg installation: {e}")
    
    def get_audio_format(self, file_path: str) -> str:
        """
        从文件路径获取音频格式
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            str: 音频格式
        """
        extension = os.path.splitext(file_path)[1].lower().lstrip('.')
        return self.SUPPORTED_INPUT_FORMATS.get(extension, extension)
    
    def is_format_supported(self, file_path: str) -> bool:
        """
        检查音频格式是否支持
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            bool: 是否支持该格式
        """
        extension = os.path.splitext(file_path)[1].lower().lstrip('.')
        return extension in self.SUPPORTED_INPUT_FORMATS
    
    def needs_conversion(self, file_path: str) -> bool:
        """
        检查文件是否需要转换
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            bool: 是否需要转换
        """
        extension = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        # 如果不是WAV格式，肯定需要转换
        if extension != 'wav':
            return True
            
        # 如果是WAV格式，检查是否兼容我们的要求
        return not self._is_wav_compatible(file_path)
    
    def convert_to_wav(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        将音频文件转换为WAV格式（高并发优化版本）
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出WAV文件路径，如果为None则创建临时文件
            
        Returns:
            str: 输出WAV文件路径
            
        Raises:
            ValueError: 不支持的音频格式
            IOError: 转换失败
        """
        if not os.path.exists(input_path):
            raise IOError(f"Input file does not exist: {input_path}")
        
        if not self.is_format_supported(input_path):
            extension = os.path.splitext(input_path)[1].lower().lstrip('.')
            raise ValueError(f"Unsupported audio format: {extension}")
        
        # 如果已经是WAV格式，检查是否符合要求
        if not self.needs_conversion(input_path):
            if self._is_wav_compatible(input_path):
                logger.info(f"File {input_path} is already in compatible WAV format")
                return input_path
        
        # 生成输出路径
        if output_path is None:
            temp_fd, output_path = tempfile.mkstemp(suffix='.wav', prefix='lingualink_converted_')
            os.close(temp_fd)  # 关闭文件描述符，但保留文件路径
        
        start_time = time.time()
        
        # 使用并发管理器进行转换
        concurrency_manager = _get_global_concurrency_manager()
        with concurrency_manager.acquire_conversion_slot():
            try:
                with self.local_lock:
                    self.conversion_count += 1
                    current_count = self.conversion_count
                
                logger.info(f"Converting {input_path} to WAV format (conversion #{current_count})")
                
                # 获取输入格式
                input_format = self.get_audio_format(input_path)
                
                # 加载音频文件
                if input_format == 'opus':
                    # OPUS需要特殊处理
                    audio = AudioSegment.from_file(input_path, format="ogg", codec="libopus")
                else:
                    audio = AudioSegment.from_file(input_path, format=input_format)
                
                # 转换为标准WAV格式
                audio = audio.set_frame_rate(self.WAV_CONFIG['frame_rate'])
                audio = audio.set_channels(self.WAV_CONFIG['channels'])
                audio = audio.set_sample_width(self.WAV_CONFIG['sample_width'])
                
                # 导出为WAV
                audio.export(
                    output_path,
                    format=self.WAV_CONFIG['format'],
                    parameters=["-ar", str(self.WAV_CONFIG['frame_rate'])]
                )
                
                conversion_time = time.time() - start_time
                stats = concurrency_manager.get_stats()
                
                logger.info(f"Successfully converted to: {output_path} in {conversion_time:.2f}s "
                          f"(active: {stats['active_conversions']}, total: {stats['total_conversions']})")
                return output_path
                
            except Exception as e:
                # 清理失败的输出文件
                if output_path and os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                
                error_msg = f"Failed to convert audio file {input_path}: {e}"
                logger.error(error_msg)
                raise IOError(error_msg)
    
    def _is_wav_compatible(self, wav_path: str) -> bool:
        """
        检查WAV文件是否符合要求的格式
        
        Args:
            wav_path: WAV文件路径
            
        Returns:
            bool: 是否兼容
        """
        try:
            audio = AudioSegment.from_wav(wav_path)
            return (
                audio.frame_rate == self.WAV_CONFIG['frame_rate'] and
                audio.channels == self.WAV_CONFIG['channels'] and
                audio.sample_width == self.WAV_CONFIG['sample_width']
            )
        except Exception:
            return False
    
    def get_audio_info(self, file_path: str) -> dict:
        """
        获取音频文件信息
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            dict: 音频信息
        """
        try:
            if not os.path.exists(file_path):
                return {"exists": False}
            
            input_format = self.get_audio_format(file_path)
            
            if input_format == 'opus':
                audio = AudioSegment.from_file(file_path, format="ogg", codec="libopus")
            else:
                audio = AudioSegment.from_file(file_path, format=input_format)
            
            return {
                "exists": True,
                "format": input_format,
                "duration_seconds": len(audio) / 1000.0,
                "frame_rate": audio.frame_rate,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "needs_conversion": self.needs_conversion(file_path)
            }
        except Exception as e:
            logger.error(f"Failed to get audio info for {file_path}: {e}")
            return {
                "exists": True,
                "error": str(e)
            }
    
    def cleanup_converted_file(self, file_path: str, original_path: str) -> bool:
        """
        清理转换后的文件（如果不是原始文件）
        
        Args:
            file_path: 要清理的文件路径
            original_path: 原始文件路径
            
        Returns:
            bool: 清理是否成功
        """
        # 只清理转换生成的文件，不清理原始文件
        if file_path != original_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Converted file {file_path} cleaned up")
                return True
            except Exception as e:
                logger.error(f"Failed to cleanup converted file {file_path}: {e}")
                return False
        return True
    
    def get_conversion_stats(self) -> dict:
        """获取转换统计信息"""
        concurrency_manager = _get_global_concurrency_manager()
        global_stats = concurrency_manager.get_stats()
        with self.local_lock:
            local_stats = {"instance_conversions": self.conversion_count}
        
        return {**global_stats, **local_stats}


# 异步音频转换器（用于高并发场景）
class AsyncAudioConverter:
    """异步音频转换器，适合高并发Web应用"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化异步转换器
        
        Args:
            max_workers: 最大工作线程数，如果为None则从settings获取
        """
        if max_workers is None:
            from config.settings import settings
            max_workers = settings.audio_converter_workers
            
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.sync_converter = AudioConverter()
        
    async def convert_to_wav_async(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        异步转换音频文件为WAV格式
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出WAV文件路径
            
        Returns:
            str: 输出WAV文件路径
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.sync_converter.convert_to_wav,
            input_path,
            output_path
        )
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True) 