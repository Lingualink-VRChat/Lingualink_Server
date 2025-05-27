import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.lingualink.core.audio_converter import AudioConverter


class TestAudioConverter:
    """音频转换器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.converter = AudioConverter()
    
    def test_get_audio_format(self):
        """测试音频格式识别"""
        assert self.converter.get_audio_format("test.opus") == "opus"
        assert self.converter.get_audio_format("test.wav") == "wav"
        assert self.converter.get_audio_format("test.mp3") == "mp3"
        assert self.converter.get_audio_format("test.unknown") == "unknown"
    
    def test_is_format_supported(self):
        """测试格式支持检查"""
        assert self.converter.is_format_supported("test.opus") is True
        assert self.converter.is_format_supported("test.wav") is True
        assert self.converter.is_format_supported("test.mp3") is True
        assert self.converter.is_format_supported("test.unknown") is False
    
    def test_needs_conversion(self):
        """测试转换需求检查"""
        assert self.converter.needs_conversion("test.opus") is True
        assert self.converter.needs_conversion("test.mp3") is True
        assert self.converter.needs_conversion("test.wav") is False
    
    @patch('src.lingualink.core.audio_converter.AudioSegment')
    def test_convert_to_wav_opus(self, mock_audio_segment):
        """测试OPUS到WAV转换"""
        # 模拟AudioSegment行为
        mock_audio = Mock()
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        mock_audio_segment.from_file.return_value = mock_audio
        
        # 创建临时OPUS文件
        with tempfile.NamedTemporaryFile(suffix='.opus', delete=False) as temp_opus:
            temp_opus.write(b'fake opus data')
            temp_opus_path = temp_opus.name
        
        try:
            # 测试转换
            with patch('os.path.exists', return_value=True):
                wav_path = self.converter.convert_to_wav(temp_opus_path)
                
                # 验证调用
                mock_audio_segment.from_file.assert_called_once_with(
                    temp_opus_path, format="ogg", codec="libopus"
                )
                mock_audio.set_frame_rate.assert_called_once_with(16000)
                mock_audio.set_channels.assert_called_once_with(1)
                mock_audio.set_sample_width.assert_called_once_with(2)
                mock_audio.export.assert_called_once()
                
                assert wav_path.endswith('.wav')
                
        finally:
            # 清理
            if os.path.exists(temp_opus_path):
                os.remove(temp_opus_path)
    
    def test_convert_to_wav_file_not_exists(self):
        """测试转换不存在的文件"""
        with pytest.raises(IOError, match="Input file does not exist"):
            self.converter.convert_to_wav("nonexistent.opus")
    
    def test_convert_to_wav_unsupported_format(self):
        """测试转换不支持的格式"""
        with tempfile.NamedTemporaryFile(suffix='.unknown', delete=False) as temp_file:
            temp_file.write(b'fake data')
            temp_file_path = temp_file.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported audio format"):
                self.converter.convert_to_wav(temp_file_path)
        finally:
            os.remove(temp_file_path)
    
    @patch('src.lingualink.core.audio_converter.AudioSegment')
    def test_get_audio_info_opus(self, mock_audio_segment):
        """测试获取OPUS音频信息"""
        # 模拟AudioSegment行为
        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=5000)  # 5秒
        mock_audio.frame_rate = 48000
        mock_audio.channels = 2
        mock_audio.sample_width = 2
        mock_audio_segment.from_file.return_value = mock_audio
        
        with tempfile.NamedTemporaryFile(suffix='.opus', delete=False) as temp_opus:
            temp_opus.write(b'fake opus data')
            temp_opus_path = temp_opus.name
        
        try:
            info = self.converter.get_audio_info(temp_opus_path)
            
            assert info['exists'] is True
            assert info['format'] == 'opus'
            assert info['duration_seconds'] == 5.0
            assert info['frame_rate'] == 48000
            assert info['channels'] == 2
            assert info['sample_width'] == 2
            assert info['needs_conversion'] is True
            
        finally:
            os.remove(temp_opus_path)
    
    def test_get_audio_info_nonexistent(self):
        """测试获取不存在文件的信息"""
        info = self.converter.get_audio_info("nonexistent.opus")
        assert info['exists'] is False
    
    def test_cleanup_converted_file(self):
        """测试清理转换后的文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False) as temp_converted:
            temp_converted.write(b'converted data')
            converted_path = temp_converted.name
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_original:
            temp_original.write(b'original data')
            original_path = temp_original.name
        
        try:
            # 测试清理转换后的文件
            result = self.converter.cleanup_converted_file(converted_path, original_path)
            assert result is True
            assert not os.path.exists(converted_path)
            assert os.path.exists(original_path)  # 原始文件不应被删除
            
        finally:
            # 清理剩余文件
            if os.path.exists(original_path):
                os.remove(original_path)
    
    def test_cleanup_converted_file_same_as_original(self):
        """测试清理转换后的文件（与原始文件相同）"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'same file')
            file_path = temp_file.name
        
        try:
            # 文件路径相同时不应删除
            result = self.converter.cleanup_converted_file(file_path, file_path)
            assert result is True
            assert os.path.exists(file_path)  # 文件应该存在
            
        finally:
            os.remove(file_path)


@pytest.mark.asyncio
class TestAudioProcessorIntegration:
    """音频处理器集成测试"""
    
    @patch('src.lingualink.core.audio_processor.AudioConverter')
    async def test_process_and_convert_audio_opus(self, mock_converter_class):
        """测试处理OPUS音频文件"""
        from src.lingualink.core.audio_processor import AudioProcessor
        from fastapi import UploadFile
        from io import BytesIO
        
        # 模拟转换器
        mock_converter = Mock()
        mock_converter.needs_conversion.return_value = True
        mock_converter.convert_to_wav.return_value = "/tmp/converted.wav"
        mock_converter_class.return_value = mock_converter
        
        processor = AudioProcessor()
        
        # 创建模拟的OPUS文件上传
        file_content = b'fake opus content'
        upload_file = UploadFile(
            filename="test.opus",
            file=BytesIO(file_content)
        )
        
        # 模拟保存上传文件和文件存在检查
        with patch.object(processor, 'save_upload_file') as mock_save, \
             patch('os.path.exists', return_value=True):
            mock_save.return_value = "/tmp/original.opus"
            
            # 测试处理
            wav_path, original_path = await processor.process_and_convert_audio(upload_file)
            
            assert wav_path == "/tmp/converted.wav"
            assert original_path == "/tmp/original.opus"
            mock_converter.needs_conversion.assert_called_once_with("/tmp/original.opus")
            mock_converter.convert_to_wav.assert_called_once_with("/tmp/original.opus")
    
    @patch('src.lingualink.core.audio_processor.AudioConverter')
    async def test_process_and_convert_audio_wav(self, mock_converter_class):
        """测试处理WAV音频文件（无需转换）"""
        from src.lingualink.core.audio_processor import AudioProcessor
        from fastapi import UploadFile
        from io import BytesIO
        
        # 模拟转换器
        mock_converter = Mock()
        mock_converter.needs_conversion.return_value = False
        mock_converter_class.return_value = mock_converter
        
        processor = AudioProcessor()
        
        # 创建模拟的WAV文件上传
        file_content = b'fake wav content'
        upload_file = UploadFile(
            filename="test.wav",
            file=BytesIO(file_content)
        )
        
        # 模拟保存上传文件
        with patch.object(processor, 'save_upload_file') as mock_save:
            mock_save.return_value = "/tmp/original.wav"
            
            # 测试处理
            wav_path, original_path = await processor.process_and_convert_audio(upload_file)
            
            assert wav_path == "/tmp/original.wav"
            assert original_path == "/tmp/original.wav"
            mock_converter.needs_conversion.assert_called_once_with("/tmp/original.wav")
            mock_converter.convert_to_wav.assert_not_called() 