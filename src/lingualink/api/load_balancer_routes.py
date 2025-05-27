from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from ..auth.dependencies import get_api_key
from ..core.llm_service_v2 import LoadBalancedLLMService
from ..core.load_balancer import LoadBalanceStrategy

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/load_balancer", tags=["负载均衡管理"])

# 全局LLM服务实例
llm_service: Optional[LoadBalancedLLMService] = None


def get_llm_service() -> LoadBalancedLLMService:
    """获取LLM服务实例"""
    global llm_service
    if llm_service is None:
        llm_service = LoadBalancedLLMService()
    return llm_service


# Pydantic模型
class BackendCreateRequest(BaseModel):
    name: str
    url: str
    model_name: str
    api_key: str
    weight: int = 1
    max_connections: int = 50
    timeout: float = 30.0
    tags: List[str] = []


class BackendUpdateRequest(BaseModel):
    weight: Optional[int] = None
    max_connections: Optional[int] = None
    timeout: Optional[float] = None
    tags: Optional[List[str]] = None


class StrategyUpdateRequest(BaseModel):
    strategy: str
    health_check_interval: Optional[float] = None
    max_retries: Optional[int] = None
    failure_threshold: Optional[int] = None


@router.get("/metrics")
async def get_load_balancer_metrics(api_key: str = Depends(get_api_key)):
    """获取负载均衡器指标"""
    try:
        service = get_llm_service()
        metrics = service.get_load_balancer_metrics()
        
        return {
            "status": "success",
            "data": metrics
        }
    except Exception as e:
        logger.error(f"获取负载均衡器指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")


@router.get("/backends")
async def list_backends(api_key: str = Depends(get_api_key)):
    """列出所有后端"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            raise HTTPException(status_code=400, detail="负载均衡器未初始化")
        
        backends_info = {}
        for name, backend in service.load_balancer.backends.items():
            metrics = service.load_balancer.metrics.get(name)
            backends_info[name] = {
                "config": {
                    "name": backend.name,
                    "url": backend.url,
                    "model_name": backend.model_name,
                    "weight": backend.weight,
                    "max_connections": backend.max_connections,
                    "timeout": backend.timeout,
                    "priority": backend.priority,
                    "tags": backend.tags
                },
                "metrics": {
                    "status": metrics.status.value if metrics else "unknown",
                    "total_requests": metrics.total_requests if metrics else 0,
                    "successful_requests": metrics.successful_requests if metrics else 0,
                    "failed_requests": metrics.failed_requests if metrics else 0,
                    "active_connections": metrics.active_connections if metrics else 0,
                    "average_response_time": metrics.average_response_time if metrics else 0.0,
                    "success_rate": metrics.get_success_rate() if metrics else 1.0,
                    "consecutive_failures": metrics.consecutive_failures if metrics else 0,
                    "last_error": metrics.last_error if metrics else None,
                    "last_check_time": metrics.last_check_time if metrics else 0.0
                }
            }
        
        return {
            "status": "success",
            "data": {
                "strategy": service.load_balancer.strategy.value,
                "total_backends": len(backends_info),
                "healthy_backends": len(service.load_balancer._get_available_backends()),
                "backends": backends_info
            }
        }
    except Exception as e:
        logger.error(f"列出后端失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出后端失败: {str(e)}")


@router.post("/backends")
async def add_backend(request: BackendCreateRequest, api_key: str = Depends(get_api_key)):
    """动态添加后端"""
    try:
        service = get_llm_service()
        
        success = service.add_backend(
            name=request.name,
            url=request.url,
            model_name=request.model_name,
            api_key=request.api_key,
            weight=request.weight,
            max_connections=request.max_connections,
            timeout=request.timeout
        )
        
        if success:
            return {
                "status": "success",
                "message": f"成功添加后端: {request.name}"
            }
        else:
            raise HTTPException(status_code=400, detail="添加后端失败")
            
    except Exception as e:
        logger.error(f"添加后端失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加后端失败: {str(e)}")


@router.delete("/backends/{backend_name}")
async def remove_backend(backend_name: str, api_key: str = Depends(get_api_key)):
    """动态移除后端"""
    try:
        service = get_llm_service()
        success = service.remove_backend(backend_name)
        
        if success:
            return {
                "status": "success",
                "message": f"成功移除后端: {backend_name}"
            }
        else:
            raise HTTPException(status_code=400, detail="移除后端失败")
            
    except Exception as e:
        logger.error(f"移除后端失败: {e}")
        raise HTTPException(status_code=500, detail=f"移除后端失败: {str(e)}")


@router.post("/backends/{backend_name}/enable")
async def enable_backend(backend_name: str, api_key: str = Depends(get_api_key)):
    """启用后端"""
    try:
        service = get_llm_service()
        success = service.enable_backend(backend_name)
        
        if success:
            return {
                "status": "success",
                "message": f"成功启用后端: {backend_name}"
            }
        else:
            raise HTTPException(status_code=400, detail="启用后端失败")
            
    except Exception as e:
        logger.error(f"启用后端失败: {e}")
        raise HTTPException(status_code=500, detail=f"启用后端失败: {str(e)}")


@router.post("/backends/{backend_name}/disable")
async def disable_backend(backend_name: str, api_key: str = Depends(get_api_key)):
    """禁用后端"""
    try:
        service = get_llm_service()
        success = service.disable_backend(backend_name)
        
        if success:
            return {
                "status": "success",
                "message": f"成功禁用后端: {backend_name}"
            }
        else:
            raise HTTPException(status_code=400, detail="禁用后端失败")
            
    except Exception as e:
        logger.error(f"禁用后端失败: {e}")
        raise HTTPException(status_code=500, detail=f"禁用后端失败: {str(e)}")


@router.post("/backends/{backend_name}/health_check")
async def manual_health_check(backend_name: str, api_key: str = Depends(get_api_key)):
    """手动健康检查指定后端"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            raise HTTPException(status_code=400, detail="负载均衡器未初始化")
        
        if backend_name not in service.load_balancer.backends:
            raise HTTPException(status_code=404, detail=f"后端 '{backend_name}' 不存在")
        
        # 执行健康检查
        await service.load_balancer._check_backend_health(backend_name)
        
        # 获取最新状态
        metrics = service.load_balancer.metrics.get(backend_name)
        if metrics:
            return {
                "status": "success",
                "data": {
                    "backend": backend_name,
                    "health_status": metrics.status.value,
                    "last_check_time": metrics.last_check_time,
                    "consecutive_failures": metrics.consecutive_failures,
                    "last_error": metrics.last_error
                }
            }
        else:
            raise HTTPException(status_code=500, detail="获取健康检查结果失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.get("/strategy")
async def get_strategy(api_key: str = Depends(get_api_key)):
    """获取当前负载均衡策略"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            raise HTTPException(status_code=400, detail="负载均衡器未初始化")
        
        return {
            "status": "success",
            "data": {
                "strategy": service.load_balancer.strategy.value,
                "health_check_interval": service.load_balancer.health_check_interval,
                "max_retries": service.load_balancer.max_retries,
                "failure_threshold": service.load_balancer.failure_threshold,
                "available_strategies": [strategy.value for strategy in LoadBalanceStrategy]
            }
        }
    except Exception as e:
        logger.error(f"获取策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取策略失败: {str(e)}")


@router.put("/strategy")
async def update_strategy(request: StrategyUpdateRequest, api_key: str = Depends(get_api_key)):
    """更新负载均衡策略"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            raise HTTPException(status_code=400, detail="负载均衡器未初始化")
        
        # 验证策略
        try:
            new_strategy = LoadBalanceStrategy(request.strategy)
        except ValueError:
            available = [s.value for s in LoadBalanceStrategy]
            raise HTTPException(
                status_code=400, 
                detail=f"无效的负载均衡策略。可用策略: {available}"
            )
        
        # 更新策略
        service.load_balancer.strategy = new_strategy
        
        # 更新其他参数
        if request.health_check_interval is not None:
            service.load_balancer.health_check_interval = request.health_check_interval
        
        if request.max_retries is not None:
            service.load_balancer.max_retries = request.max_retries
        
        if request.failure_threshold is not None:
            service.load_balancer.failure_threshold = request.failure_threshold
        
        # 如果策略变为一致性哈希，重建哈希环
        if new_strategy == LoadBalanceStrategy.CONSISTENT_HASH:
            service.load_balancer._build_hash_ring()
        
        return {
            "status": "success",
            "message": f"成功更新负载均衡策略为: {request.strategy}",
            "data": {
                "strategy": service.load_balancer.strategy.value,
                "health_check_interval": service.load_balancer.health_check_interval,
                "max_retries": service.load_balancer.max_retries,
                "failure_threshold": service.load_balancer.failure_threshold
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新策略失败: {str(e)}")


@router.post("/health_check/start")
async def start_health_check(background_tasks: BackgroundTasks, api_key: str = Depends(get_api_key)):
    """启动自动健康检查"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            raise HTTPException(status_code=400, detail="负载均衡器未初始化")
        
        # 在后台启动健康检查
        background_tasks.add_task(service.start_health_check)
        
        return {
            "status": "success",
            "message": "健康检查任务已启动"
        }
    except Exception as e:
        logger.error(f"启动健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动健康检查失败: {str(e)}")


@router.post("/health_check/stop")
async def stop_health_check(background_tasks: BackgroundTasks, api_key: str = Depends(get_api_key)):
    """停止自动健康检查"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            raise HTTPException(status_code=400, detail="负载均衡器未初始化")
        
        # 在后台停止健康检查
        background_tasks.add_task(service.stop_health_check)
        
        return {
            "status": "success",
            "message": "健康检查任务已停止"
        }
    except Exception as e:
        logger.error(f"停止健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止健康检查失败: {str(e)}")


@router.get("/status")
async def get_load_balancer_status(api_key: str = Depends(get_api_key)):
    """获取负载均衡器整体状态"""
    try:
        service = get_llm_service()
        if not service.load_balancer:
            return {
                "status": "success",
                "data": {
                    "enabled": False,
                    "message": "负载均衡器未初始化，使用单后端模式"
                }
            }
        
        metrics = service.load_balancer.get_metrics()
        available_backends = service.load_balancer._get_available_backends()
        
        # 计算整体统计
        total_requests = sum(m.get('total_requests', 0) for m in metrics.values())
        total_success = sum(m.get('successful_requests', 0) for m in metrics.values())
        overall_success_rate = total_success / total_requests if total_requests > 0 else 1.0
        
        avg_response_times = [
            m.get('average_response_time', 0) 
            for m in metrics.values() 
            if m.get('average_response_time', 0) > 0
        ]
        overall_avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0.0
        
        return {
            "status": "success",
            "data": {
                "enabled": True,
                "strategy": service.load_balancer.strategy.value,
                "total_backends": len(service.load_balancer.backends),
                "healthy_backends": len(available_backends),
                "unhealthy_backends": len(service.load_balancer.backends) - len(available_backends),
                "health_check_running": service.load_balancer._health_check_task is not None and not service.load_balancer._health_check_task.done(),
                "overall_statistics": {
                    "total_requests": total_requests,
                    "success_rate": overall_success_rate,
                    "average_response_time": overall_avg_response_time
                },
                "available_backends": available_backends
            }
        }
        
    except Exception as e:
        logger.error(f"获取负载均衡器状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}") 