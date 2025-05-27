import base64
import os
import time
import copy
import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config.settings import settings
import logging
from .load_balancer import (
    LLMLoadBalancer, BackendConfig, LoadBalanceStrategy,
    BackendStatus
)

logger = logging.getLogger(__name__)


class LoadBalancedLLMService:
    """支持负载均衡的LLM服务类"""
    
    def __init__(self):
        self.load_balancer: Optional[LLMLoadBalancer] = None
        self._clients: Dict[str, OpenAI] = {}
        self._initialize_load_balancer()
    
    def _initialize_load_balancer(self):
        """初始化负载均衡器"""
        # 检查是否启用负载均衡
        if not settings.is_load_balance_enabled():
            logger.info("负载均衡未启用，使用传统单后端模式")
            self.load_balancer = None
            # 创建单个客户端
            self._clients["default"] = self._create_single_client()
            return
        
        backends = self._parse_backend_configs()
        
        if not backends:
            # 如果启用了负载均衡但没有配置多后端，使用原有的单后端配置
            logger.info("启用负载均衡但未检测到多后端配置，使用单后端负载均衡模式")
            backend = BackendConfig(
                name="default",
                url=settings.vllm_server_url,
                model_name=settings.model_name,
                api_key=settings.api_key,
                weight=1
            )
            backends = [backend]
        
        strategy = LoadBalanceStrategy(getattr(settings, 'load_balance_strategy', 'round_robin'))
        
        self.load_balancer = LLMLoadBalancer(
            backends=backends,
            strategy=strategy,
            health_check_interval=getattr(settings, 'health_check_interval', 30.0),
            max_retries=getattr(settings, 'max_retries', 2),
            failure_threshold=getattr(settings, 'failure_threshold', 3)
        )
        
        # 为每个后端创建客户端
        for backend in backends:
            self._clients[backend.name] = self._create_client(backend)
        
        logger.info(f"负载均衡LLM服务初始化完成，包含 {len(backends)} 个后端")
    
    def _parse_backend_configs(self) -> List[BackendConfig]:
        """解析后端配置"""
        backends = []
        
        # 检查是否有多后端配置
        llm_backends = getattr(settings, 'llm_backends', None)
        if llm_backends:
            for backend_config in llm_backends:
                backend = BackendConfig(
                    name=backend_config.get('name'),
                    url=backend_config.get('url'),
                    model_name=backend_config.get('model_name'),
                    api_key=backend_config.get('api_key'),
                    weight=backend_config.get('weight', 1),
                    max_connections=backend_config.get('max_connections', 50),
                    timeout=backend_config.get('timeout', 30.0),
                    priority=backend_config.get('priority', 0),
                    tags=backend_config.get('tags', [])
                )
                backends.append(backend)
        
        return backends
    
    def _create_client(self, backend: BackendConfig) -> OpenAI:
        """为指定后端创建OpenAI客户端"""
        temp_url = backend.url.rstrip('/')
        if temp_url.endswith('/v1'):
            final_base_url = temp_url
        else:
            final_base_url = f"{temp_url}/v1"
        
        return OpenAI(
            api_key=backend.api_key,
            base_url=final_base_url,
            timeout=backend.timeout
        )
    
    def _create_single_client(self) -> OpenAI:
        """为单后端模式创建OpenAI客户端"""
        temp_url = settings.vllm_server_url.rstrip('/')
        if temp_url.endswith('/v1'):
            final_base_url = temp_url
        else:
            final_base_url = f"{temp_url}/v1"
        
        return OpenAI(
            api_key=settings.api_key,
            base_url=final_base_url,
            timeout=30.0
        )
    
    async def start_health_check(self):
        """启动健康检查"""
        if self.load_balancer:
            await self.load_balancer.start_health_check()
    
    async def stop_health_check(self):
        """停止健康检查"""
        if self.load_balancer:
            await self.load_balancer.stop_health_check()
    
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
    
    def process_audio(self, audio_path: str, system_prompt: str, user_prompt: str,
                     request_hash: Optional[str] = None) -> Dict[str, Any]:
        """处理音频文件，使用负载均衡或单后端"""
        
        # 编码音频
        try:
            base64_encoded_audio, audio_format = self.encode_audio_to_base64(audio_path)
            logger.info(f"Successfully encoded audio file: {audio_path} (Format: {audio_format})")
        except Exception as e:
            logger.error(f"Error encoding audio: {e}")
            return {
                "status": "error", 
                "message": f"Audio encoding error: {e}", 
                "details": None
            }
        
        # 如果没有启用负载均衡，使用传统单后端模式
        if not self.load_balancer:
            return self._process_single_backend(
                base64_encoded_audio, audio_format, system_prompt, user_prompt
            )
        
        # 负载均衡模式：尝试多个后端
        max_retries = self.load_balancer.max_retries if self.load_balancer else 1
        
        for attempt in range(max_retries + 1):
            # 选择后端
            backend_name = self.load_balancer.select_backend(request_hash) if self.load_balancer else "default"
            
            if not backend_name:
                return {
                    "status": "error",
                    "message": "没有可用的后端服务器",
                    "details": None
                }
            
            backend_config = self.load_balancer.get_backend_config(backend_name)
            client = self._clients.get(backend_name)
            
            if not client or not backend_config:
                logger.error(f"后端 {backend_name} 的客户端或配置不存在")
                continue
            
            try:
                result = self._make_request(
                    client=client,
                    backend_config=backend_config,
                    base64_encoded_audio=base64_encoded_audio,
                    audio_format=audio_format,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                )
                
                # 记录成功
                if self.load_balancer:
                    self.load_balancer.record_request_result(
                        backend_name, True, result.get("duration_seconds", 0)
                    )
                    self.load_balancer.release_connection(backend_name)
                
                # 添加后端信息到结果中
                result["backend"] = backend_name
                return result
                
            except Exception as e:
                logger.warning(f"后端 {backend_name} 请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                
                # 记录失败
                if self.load_balancer:
                    self.load_balancer.record_request_result(
                        backend_name, False, 0, str(e)
                    )
                    self.load_balancer.release_connection(backend_name)
                
                # 如果是最后一次尝试，返回错误
                if attempt == max_retries:
                    return {
                        "status": "error",
                        "message": f"所有后端都请求失败，最后错误: {e}",
                        "details": {"backend": backend_name, "error": str(e)}
                    }
        
        return {
            "status": "error",
            "message": "请求处理失败",
            "details": None
        }
    
    def _make_request(self, client: OpenAI, backend_config: BackendConfig,
                     base64_encoded_audio: str, audio_format: str,
                     system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """向指定后端发送请求"""
        
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
            "model": backend_config.model_name,
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
        
        logger.info(f"Sending request to: {client.base_url}chat/completions")
        logger.debug(f"Payload (audio data truncated): {json.dumps(payload_to_display, indent=2)}")

        # 发送请求
        start_time = time.monotonic()
        chat_completion = client.chat.completions.create(
            model=backend_config.model_name,
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
            raise Exception("No valid choice in model response")
    
    def _process_single_backend(self, base64_encoded_audio: str, audio_format: str,
                               system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """传统单后端处理模式"""
        client = self._clients.get("default")
        if not client:
            return {
                "status": "error",
                "message": "单后端客户端未初始化",
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
            
            logger.info(f"Sending request to: {client.base_url}chat/completions")
            logger.debug(f"Payload (audio data truncated): {json.dumps(payload_to_display, indent=2)}")

            # 发送请求
            start_time = time.monotonic()
            chat_completion = client.chat.completions.create(
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
                    "data": parsed_output,
                    "backend": "default"
                }
            else:
                logger.error(f"No valid choice found in response: {chat_completion}")
                return {
                    "status": "error",
                    "message": "No valid choice in model response",
                    "details": str(chat_completion)
                }
        except Exception as e:
            logger.error(f"单后端API调用失败: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"API调用失败: {e}",
                "details": None
            }
    
    def get_load_balancer_metrics(self) -> Dict[str, Any]:
        """获取负载均衡器指标"""
        if not self.load_balancer:
            return {"error": "负载均衡器未初始化"}
        
        return {
            "strategy": self.load_balancer.strategy.value,
            "backends": self.load_balancer.get_metrics(),
            "total_backends": len(self.load_balancer.backends),
            "healthy_backends": len(self.load_balancer._get_available_backends())
        }
    
    def add_backend(self, name: str, url: str, model_name: str, api_key: str,
                   weight: int = 1, max_connections: int = 50, timeout: float = 30.0):
        """动态添加后端"""
        if not self.load_balancer:
            logger.error("负载均衡器未初始化")
            return False
        
        backend = BackendConfig(
            name=name,
            url=url,
            model_name=model_name,
            api_key=api_key,
            weight=weight,
            max_connections=max_connections,
            timeout=timeout
        )
        
        self.load_balancer.add_backend(backend)
        self._clients[name] = self._create_client(backend)
        
        logger.info(f"动态添加后端: {name}")
        return True
    
    def remove_backend(self, backend_name: str):
        """动态移除后端"""
        if not self.load_balancer:
            logger.error("负载均衡器未初始化")
            return False
        
        self.load_balancer.remove_backend(backend_name)
        if backend_name in self._clients:
            del self._clients[backend_name]
        
        logger.info(f"动态移除后端: {backend_name}")
        return True
    
    def enable_backend(self, backend_name: str):
        """启用后端"""
        if self.load_balancer:
            self.load_balancer.enable_backend(backend_name)
            return True
        return False
    
    def disable_backend(self, backend_name: str):
        """禁用后端"""
        if self.load_balancer:
            self.load_balancer.disable_backend(backend_name)
            return True
        return False


# 向后兼容的类，保持原有接口
class LLMService(LoadBalancedLLMService):
    """向后兼容的LLM服务类"""
    
    def __init__(self):
        super().__init__()
        
        # 如果只有一个后端，保持原有接口的兼容性
        if len(self._clients) == 1:
            self.client = list(self._clients.values())[0] 