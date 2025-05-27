import asyncio
import time
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager
import aiohttp
from threading import Lock
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(Enum):
    """负载均衡策略枚举"""
    ROUND_ROBIN = "round_robin"           # 轮询
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询
    LEAST_CONNECTIONS = "least_connections"  # 最少连接数
    RANDOM = "random"                     # 随机
    CONSISTENT_HASH = "consistent_hash"   # 一致性哈希
    RESPONSE_TIME = "response_time"       # 响应时间最优


class BackendStatus(Enum):
    """后端状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy" 
    DISABLED = "disabled"


@dataclass
class BackendConfig:
    """后端配置"""
    name: str
    url: str
    model_name: str
    api_key: str
    weight: int = 1
    max_connections: int = 50
    timeout: float = 30.0
    priority: int = 0  # 优先级，数值越小优先级越高
    tags: List[str] = field(default_factory=list)


@dataclass
class BackendMetrics:
    """后端性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    active_connections: int = 0
    average_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    last_check_time: float = 0.0
    status: BackendStatus = BackendStatus.HEALTHY
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    
    def update_response_time(self, response_time: float):
        """更新响应时间统计"""
        self.response_times.append(response_time)
        # 只保留最近50次的响应时间
        if len(self.response_times) > 50:
            self.response_times = self.response_times[-50:]
        
        self.average_response_time = statistics.mean(self.response_times)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class LLMLoadBalancer:
    """LLM负载均衡器"""
    
    def __init__(self, 
                 backends: List[BackendConfig],
                 strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
                 health_check_interval: float = 30.0,
                 max_retries: int = 2,
                 failure_threshold: int = 3):
        self.backends = {backend.name: backend for backend in backends}
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self.max_retries = max_retries
        self.failure_threshold = failure_threshold
        
        # 性能指标
        self.metrics: Dict[str, BackendMetrics] = {}
        for backend in backends:
            self.metrics[backend.name] = BackendMetrics()
        
        # 状态管理
        self._lock = Lock()
        self._round_robin_index = 0
        self._hash_ring: Dict[int, str] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 初始化一致性哈希环
        self._build_hash_ring()
        
        logger.info(f"LLM负载均衡器初始化完成，包含 {len(backends)} 个后端")
    
    def _build_hash_ring(self):
        """构建一致性哈希环"""
        self._hash_ring.clear()
        for backend_name, backend in self.backends.items():
            # 为每个后端创建多个虚拟节点
            for i in range(backend.weight * 10):
                virtual_node = f"{backend_name}#{i}"
                hash_value = int(hashlib.md5(virtual_node.encode()).hexdigest(), 16)
                self._hash_ring[hash_value] = backend_name
    
    async def start_health_check(self):
        """启动健康检查任务"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("健康检查任务已启动")
    
    async def stop_health_check(self):
        """停止健康检查任务"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("健康检查任务已停止")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_backends()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查出错: {e}")
    
    async def _check_all_backends(self):
        """检查所有后端的健康状态"""
        tasks = []
        for backend_name in self.backends:
            task = asyncio.create_task(self._check_backend_health(backend_name))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_backend_health(self, backend_name: str):
        """检查单个后端的健康状态"""
        backend = self.backends[backend_name]
        metrics = self.metrics[backend_name]
        
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                # 发送健康检查请求
                health_url = f"{backend.url.rstrip('/')}/v1/models"
                async with session.get(
                    health_url,
                    headers={"Authorization": f"Bearer {backend.api_key}"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        with self._lock:
                            metrics.status = BackendStatus.HEALTHY
                            metrics.consecutive_failures = 0
                            metrics.last_check_time = time.time()
                            metrics.update_response_time(response_time)
                        logger.debug(f"后端 {backend_name} 健康检查通过")
                    else:
                        raise Exception(f"HTTP {response.status}")
        
        except Exception as e:
            with self._lock:
                metrics.consecutive_failures += 1
                metrics.last_error = str(e)
                metrics.last_check_time = time.time()
                
                if metrics.consecutive_failures >= self.failure_threshold:
                    metrics.status = BackendStatus.UNHEALTHY
                    logger.warning(f"后端 {backend_name} 标记为不健康: {e}")
    
    def _get_available_backends(self) -> List[str]:
        """获取可用的后端列表"""
        available = []
        for backend_name, metrics in self.metrics.items():
            if metrics.status == BackendStatus.HEALTHY:
                available.append(backend_name)
        return available
    
    def select_backend(self, request_hash: Optional[str] = None) -> Optional[str]:
        """根据策略选择后端"""
        available_backends = self._get_available_backends()
        
        if not available_backends:
            logger.error("没有可用的后端")
            return None
        
        with self._lock:
            if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
                backend = self._round_robin_select(available_backends)
            elif self.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
                backend = self._weighted_round_robin_select(available_backends)
            elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
                backend = self._least_connections_select(available_backends)
            elif self.strategy == LoadBalanceStrategy.RANDOM:
                backend = self._random_select(available_backends)
            elif self.strategy == LoadBalanceStrategy.CONSISTENT_HASH:
                backend = self._consistent_hash_select(request_hash or "default")
            elif self.strategy == LoadBalanceStrategy.RESPONSE_TIME:
                backend = self._response_time_select(available_backends)
            else:
                backend = available_backends[0]
            
            # 增加连接计数
            if backend:
                self.metrics[backend].active_connections += 1
            
            return backend
    
    def _round_robin_select(self, available_backends: List[str]) -> str:
        """轮询策略"""
        if not available_backends:
            return None
        
        backend = available_backends[self._round_robin_index % len(available_backends)]
        self._round_robin_index = (self._round_robin_index + 1) % len(available_backends)
        return backend
    
    def _weighted_round_robin_select(self, available_backends: List[str]) -> str:
        """加权轮询策略"""
        if not available_backends:
            return None
        
        weighted_backends = []
        for backend_name in available_backends:
            weight = self.backends[backend_name].weight
            weighted_backends.extend([backend_name] * weight)
        
        if not weighted_backends:
            return available_backends[0]
        
        backend = weighted_backends[self._round_robin_index % len(weighted_backends)]
        self._round_robin_index = (self._round_robin_index + 1) % len(weighted_backends)
        return backend
    
    def _least_connections_select(self, available_backends: List[str]) -> str:
        """最少连接数策略"""
        if not available_backends:
            return None
        
        min_connections = float('inf')
        selected_backend = available_backends[0]
        
        for backend_name in available_backends:
            connections = self.metrics[backend_name].active_connections
            if connections < min_connections:
                min_connections = connections
                selected_backend = backend_name
        
        return selected_backend
    
    def _random_select(self, available_backends: List[str]) -> str:
        """随机策略"""
        if not available_backends:
            return None
        return random.choice(available_backends)
    
    def _consistent_hash_select(self, request_hash: str) -> Optional[str]:
        """一致性哈希策略"""
        if not self._hash_ring:
            return None
        
        hash_value = int(hashlib.md5(request_hash.encode()).hexdigest(), 16)
        
        # 找到第一个大于等于hash_value的节点
        for ring_hash in sorted(self._hash_ring.keys()):
            if ring_hash >= hash_value:
                backend_name = self._hash_ring[ring_hash]
                if self.metrics[backend_name].status == BackendStatus.HEALTHY:
                    return backend_name
        
        # 如果没有找到，选择第一个节点
        if self._hash_ring:
            first_hash = min(self._hash_ring.keys())
            backend_name = self._hash_ring[first_hash]
            if self.metrics[backend_name].status == BackendStatus.HEALTHY:
                return backend_name
        
        return None
    
    def _response_time_select(self, available_backends: List[str]) -> str:
        """响应时间最优策略"""
        if not available_backends:
            return None
        
        best_backend = available_backends[0]
        best_time = float('inf')
        
        for backend_name in available_backends:
            avg_time = self.metrics[backend_name].average_response_time
            if avg_time > 0 and avg_time < best_time:
                best_time = avg_time
                best_backend = backend_name
        
        return best_backend
    
    def release_connection(self, backend_name: str):
        """释放连接"""
        if backend_name in self.metrics:
            with self._lock:
                if self.metrics[backend_name].active_connections > 0:
                    self.metrics[backend_name].active_connections -= 1
    
    def record_request_result(self, backend_name: str, success: bool, 
                            response_time: float, error: Optional[str] = None):
        """记录请求结果"""
        if backend_name not in self.metrics:
            return
        
        with self._lock:
            metrics = self.metrics[backend_name]
            metrics.total_requests += 1
            
            if success:
                metrics.successful_requests += 1
                metrics.update_response_time(response_time)
            else:
                metrics.failed_requests += 1
                metrics.last_error = error
    
    def get_backend_config(self, backend_name: str) -> Optional[BackendConfig]:
        """获取后端配置"""
        return self.backends.get(backend_name)
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有后端的指标"""
        result = {}
        with self._lock:
            for backend_name, metrics in self.metrics.items():
                result[backend_name] = {
                    "status": metrics.status.value,
                    "total_requests": metrics.total_requests,
                    "successful_requests": metrics.successful_requests,
                    "failed_requests": metrics.failed_requests,
                    "active_connections": metrics.active_connections,
                    "average_response_time": metrics.average_response_time,
                    "success_rate": metrics.get_success_rate(),
                    "consecutive_failures": metrics.consecutive_failures,
                    "last_error": metrics.last_error,
                    "last_check_time": metrics.last_check_time
                }
        return result
    
    def add_backend(self, backend: BackendConfig):
        """动态添加后端"""
        with self._lock:
            self.backends[backend.name] = backend
            self.metrics[backend.name] = BackendMetrics()
            self._build_hash_ring()
        logger.info(f"添加后端: {backend.name}")
    
    def remove_backend(self, backend_name: str):
        """动态移除后端"""
        with self._lock:
            if backend_name in self.backends:
                del self.backends[backend_name]
                del self.metrics[backend_name]
                self._build_hash_ring()
        logger.info(f"移除后端: {backend_name}")
    
    def enable_backend(self, backend_name: str):
        """启用后端"""
        if backend_name in self.metrics:
            with self._lock:
                self.metrics[backend_name].status = BackendStatus.HEALTHY
        logger.info(f"启用后端: {backend_name}")
    
    def disable_backend(self, backend_name: str):
        """禁用后端"""
        if backend_name in self.metrics:
            with self._lock:
                self.metrics[backend_name].status = BackendStatus.DISABLED
        logger.info(f"禁用后端: {backend_name}") 