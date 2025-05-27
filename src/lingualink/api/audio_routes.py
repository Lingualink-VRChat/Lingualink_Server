from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from typing import Optional, List
import logging

from ..models.request_models import AudioTranslationResponse, ErrorResponse
from ..core.llm_service import LLMService
from ..core.audio_processor import AudioProcessor
from ..auth.dependencies import get_current_api_key
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["audio"])

# 初始化服务
llm_service = LLMService()
audio_processor = AudioProcessor()


@router.post(
    "/translate_audio",
    response_model=AudioTranslationResponse,
    summary="音频翻译",
    description="上传音频文件，进行转录和翻译处理"
)
async def translate_audio(
    audio_file: UploadFile = File(..., description="音频文件 (支持 .wav, .opus 等格式)"),
    user_prompt: str = Form(default=settings.default_user_query, description="用户提示词"),
    target_languages: Optional[List[str]] = Form(default=None, description="目标语言列表"),
    api_key: str = Depends(get_current_api_key)
):
    """
    音频翻译接口
    
    - **audio_file**: 上传的音频文件，支持 .wav, .opus 等多种格式
    - **user_prompt**: 用户提示词，默认为"请处理下面的音频。"
    - **target_languages**: 目标语言列表，如 ["英文", "日文"]
    """
    wav_file_path: Optional[str] = None
    original_file_path: Optional[str] = None
    
    try:
        logger.info(f"Received translation request: filename={audio_file.filename}, "
                   f"user_prompt={user_prompt}, target_languages={target_languages}")
        
        # 处理和转换音频文件
        wav_file_path, original_file_path = await audio_processor.process_and_convert_audio(audio_file)
        
        # 处理目标语言
        final_target_languages: Optional[List[str]] = None
        if target_languages:
            cleaned_languages = [
                lang.strip() for lang in target_languages 
                if isinstance(lang, str) and lang.strip()
            ]
            if cleaned_languages:
                final_target_languages = cleaned_languages
        
        # 生成系统提示词
        system_prompt = llm_service.generate_system_prompt(final_target_languages)
        logger.info(f"Using system prompt with languages: {final_target_languages or settings.default_target_languages}")
        
        # 在线程池中处理音频（使用转换后的WAV文件）
        result = await run_in_threadpool(
            llm_service.process_audio,
            wav_file_path,
            system_prompt,
            user_prompt
        )
        
        logger.info(f"Processing completed with status: {result.get('status')}")
        return result

    except ValueError as ve:
        # 文件验证错误
        logger.warning(f"File validation error: {ve}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": str(ve)
            }
        )
    except IOError as ioe:
        # 文件I/O错误
        logger.error(f"File I/O error: {ioe}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error", 
                "message": f"File processing error: {str(ioe)}"
            }
        )
    except Exception as e:
        # 其他未预期的错误
        logger.error(f"Unexpected error in translate_audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Internal server error: {str(e)}"
            }
        )
    finally:
        # 清理临时文件
        if wav_file_path and original_file_path:
            audio_processor.cleanup_audio_files(wav_file_path, original_file_path)
        
        # 关闭上传文件
        if audio_file:
            await audio_file.close()


@router.get(
    "/supported_formats",
    summary="支持的音频格式",
    description="获取当前支持的音频文件格式列表"
)
async def get_supported_formats():
    """获取支持的音频格式"""
    return {
        "status": "success",
        "data": {
            "supported_formats": settings.allowed_extensions,
            "max_file_size_mb": settings.max_upload_size // (1024 * 1024),
            "default_target_languages": settings.default_target_languages
        }
    } 