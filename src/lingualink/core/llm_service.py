import base64
import os
import time
import copy
import json
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服务类，处理与语言模型的交互"""
    
    def __init__(self):
        self.client = self._create_client()
    
    def _create_client(self) -> OpenAI:
        """创建OpenAI客户端"""
        temp_vllm_server_url = settings.vllm_server_url.rstrip('/')
        if temp_vllm_server_url.endswith('/v1'):
            final_base_url = temp_vllm_server_url
        else:
            final_base_url = f"{temp_vllm_server_url}/v1"
        
        return OpenAI(
            api_key=settings.api_key,
            base_url=final_base_url
        )
    
    def encode_audio_to_base64(self, audio_path: str) -> tuple[str, str]:
        """将音频文件编码为base64字符串"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not audio_path.lower().endswith(".wav"):
            raise ValueError(f"Unsupported audio format: {audio_path}. Only .wav files are supported.")

        audio_format = "wav"
        
        with open(audio_path, "rb") as audio_file:
            binary_data = audio_file.read()
            base64_encoded_data = base64.b64encode(binary_data)
            base64_string = base64_encoded_data.decode('utf-8')
        
        return base64_string, audio_format
    
    def generate_system_prompt(self, target_languages: Optional[List[str]] = None) -> str:
        """生成系统提示词"""
        if target_languages is None:
            target_languages = settings.default_target_languages

        prompt_lines = [
            "你是一个高级的语音处理助手。你的任务是：",
            "1.首先将音频内容转录成其原始语言的文本。"
        ]

        for i, lang in enumerate(target_languages):
            prompt_lines.append(f"{i+2}. 将转录的文本翻译成{lang}。")
        
        prompt_lines.append("请按照以下格式清晰地组织你的输出：")
        prompt_lines.append("原文：")
        for lang in target_languages:
            prompt_lines.append(f"{lang}：")
            
        return "\n".join(prompt_lines)
    
    def _parse_model_response(self, content: str) -> Dict[str, Any]:
        """解析模型响应内容"""
        parsed_output = {"raw_text": content}
        current_key = None
        current_value_lines = []
        
        try:
            lines = content.strip().split('\n')
            for line_content in lines:
                stripped_content = line_content.strip()

                if not stripped_content:
                    if current_key:
                        current_value_lines.append("")  # 保留空行
                    continue

                parts = re.split(r'[:：]', stripped_content, maxsplit=1)

                if len(parts) == 2:  # 可能的新键
                    new_key_candidate = parts[0].strip()
                    new_value_first_line = parts[1].strip()

                    if new_key_candidate:  # 有效的新键
                        if current_key:  # 保存前一个键的内容
                            parsed_output[current_key] = "\n".join(current_value_lines)
                        
                        current_key = new_key_candidate
                        current_value_lines = [new_value_first_line]
                    elif current_key:  # 键部分为空，作为延续处理
                        current_value_lines.append(stripped_content)

                elif current_key:  # 没有冒号，有活跃键，追加内容
                    current_value_lines.append(stripped_content)

            # 保存最后一个键
            if current_key:
                parsed_output[current_key] = "\n".join(current_value_lines)
        
        except Exception as parse_error:
            logger.warning(f"Could not fully parse model output: {parse_error}")

        return parsed_output
    
    def process_audio(self, audio_path: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """处理音频文件，返回结构化响应"""
        try:
            # 编码音频
            base64_encoded_audio, audio_format = self.encode_audio_to_base64(audio_path)
            logger.info(f"Successfully encoded audio file: {audio_path} (Format: {audio_format})")
        except Exception as e:
            logger.error(f"Error encoding audio: {e}")
            return {
                "status": "error", 
                "message": f"Audio encoding error: {e}", 
                "details": None
            }

        try:
            # 构建消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            user_content = []
            if user_prompt:
                user_content.append({"type": "text", "text": user_prompt})

            user_content.append({
                "type": "input_audio",
                "input_audio": {
                    "data": base64_encoded_audio,
                    "format": audio_format
                },
            })
            messages.append({"role": "user", "content": user_content})
            
            # 记录请求（截断音频数据）
            payload_to_display = {
                "model": settings.model_name,
                "messages": copy.deepcopy(messages),
                "max_tokens": 200,
                "temperature": 0
            }
            for msg_log in payload_to_display["messages"]:
                if msg_log["role"] == "user" and isinstance(msg_log["content"], list):
                    for content_item_log in msg_log["content"]:
                        if content_item_log.get("type") == "input_audio":
                            data_to_log = content_item_log["input_audio"]["data"]
                            if len(data_to_log) > 100:
                                content_item_log["input_audio"]["data"] = data_to_log[:100] + "...[TRUNCATED]"
            
            logger.info(f"Sending request to: {self.client.base_url}chat/completions")
            logger.debug(f"Payload (audio data truncated): {json.dumps(payload_to_display, indent=2)}")

            # 发送请求
            start_time = time.monotonic()
            chat_completion = self.client.chat.completions.create(
                model=settings.model_name,
                messages=messages,
                max_tokens=200,
                temperature=0 
            )
            duration = time.monotonic() - start_time
            logger.info(f"API call completed in {duration:.2f} seconds.")

            # 处理响应
            if chat_completion.choices and len(chat_completion.choices) > 0:
                message_content = chat_completion.choices[0].message.content
                parsed_output = self._parse_model_response(message_content)

                return {
                    "status": "success",
                    "duration_seconds": duration,
                    "data": parsed_output
                }
            else:
                logger.error(f"No valid choice found in response: {chat_completion}")
                return {
                    "status": "error", 
                    "message": "No valid choice in model response", 
                    "details": str(chat_completion)
                }

        except Exception as e:
            duration = time.monotonic() - start_time if 'start_time' in locals() else 0
            logger.error(f"API call error: {e}", exc_info=True)
            
            error_message = f"An API call error occurred: {e}"
            response_details = None
            if hasattr(e, 'response') and e.response is not None:
                response_details = {"status_code": e.response.status_code}
                try:
                    response_details["content"] = e.response.json()
                except ValueError:
                    response_details["content"] = e.response.text
            
            return {
                "status": "error", 
                "message": error_message, 
                "details": response_details, 
                "duration_seconds": duration
            } 