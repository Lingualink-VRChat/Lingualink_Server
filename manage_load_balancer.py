#!/usr/bin/env python3
"""
负载均衡器管理工具

用于管理多LLM后端的负载均衡配置，支持添加、移除、启用、禁用后端，
以及查看状态和指标。

使用方法:
    python3 manage_load_balancer.py --help
"""

import argparse
import asyncio
import json
import sys
import os
import time
from typing import Dict, Any, List, Optional
import requests

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings


class LoadBalancerManager:
    """负载均衡器管理器"""
    
    def __init__(self, server_url: str = None, api_key: str = None):
        self.server_url = server_url or f"http://{settings.host}:{settings.port}"
        self.api_key = api_key
        self.headers = {}
        
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == "POST":
                if data:
                    response = requests.post(url, headers=self.headers, json=data, timeout=30)
                else:
                    response = requests.post(url, headers=self.headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"请求失败 ({response.status_code}): {response.text}"
                return {"error": error_msg}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"网络请求失败: {str(e)}"}
    
    def get_status(self) -> Dict[str, Any]:
        """获取负载均衡器状态"""
        return self._make_request("GET", "/api/v1/load_balancer/status")
    
    def list_backends(self) -> Dict[str, Any]:
        """列出所有后端"""
        return self._make_request("GET", "/api/v1/load_balancer/backends")
    
    def add_backend(self, name: str, url: str, model_name: str, api_key: str,
                   weight: int = 1, max_connections: int = 50, timeout: float = 30.0) -> Dict[str, Any]:
        """添加后端"""
        data = {
            "name": name,
            "url": url,
            "model_name": model_name,
            "api_key": api_key,
            "weight": weight,
            "max_connections": max_connections,
            "timeout": timeout
        }
        return self._make_request("POST", "/api/v1/load_balancer/backends", data)
    
    def remove_backend(self, backend_name: str) -> Dict[str, Any]:
        """移除后端"""
        return self._make_request("DELETE", f"/api/v1/load_balancer/backends/{backend_name}")
    
    def enable_backend(self, backend_name: str) -> Dict[str, Any]:
        """启用后端"""
        return self._make_request("POST", f"/api/v1/load_balancer/backends/{backend_name}/enable")
    
    def disable_backend(self, backend_name: str) -> Dict[str, Any]:
        """禁用后端"""
        return self._make_request("POST", f"/api/v1/load_balancer/backends/{backend_name}/disable")
    
    def health_check(self, backend_name: str) -> Dict[str, Any]:
        """手动健康检查"""
        return self._make_request("POST", f"/api/v1/load_balancer/backends/{backend_name}/health_check")
    
    def get_strategy(self) -> Dict[str, Any]:
        """获取负载均衡策略"""
        return self._make_request("GET", "/api/v1/load_balancer/strategy")
    
    def update_strategy(self, strategy: str, health_check_interval: float = None,
                       max_retries: int = None, failure_threshold: int = None) -> Dict[str, Any]:
        """更新负载均衡策略"""
        data = {"strategy": strategy}
        if health_check_interval is not None:
            data["health_check_interval"] = health_check_interval
        if max_retries is not None:
            data["max_retries"] = max_retries
        if failure_threshold is not None:
            data["failure_threshold"] = failure_threshold
        
        return self._make_request("PUT", "/api/v1/load_balancer/strategy", data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self._make_request("GET", "/api/v1/load_balancer/metrics")
    
    def start_health_check(self) -> Dict[str, Any]:
        """启动健康检查"""
        return self._make_request("POST", "/api/v1/load_balancer/health_check/start")
    
    def stop_health_check(self) -> Dict[str, Any]:
        """停止健康检查"""
        return self._make_request("POST", "/api/v1/load_balancer/health_check/stop")


def format_json(data: Any, indent: int = 2) -> str:
    """格式化JSON输出"""
    return json.dumps(data, ensure_ascii=False, indent=indent)


def print_result(result: Dict[str, Any]):
    """打印结果"""
    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        sys.exit(1)
    else:
        print("✅ 成功:")
        print(format_json(result))


def print_table(data: List[Dict], headers: List[str]):
    """打印表格"""
    if not data:
        print("📝 没有数据")
        return
    
    # 计算列宽
    widths = {}
    for header in headers:
        widths[header] = len(header)
        for row in data:
            value = str(row.get(header, ""))
            widths[header] = max(widths[header], len(value))
    
    # 打印表头
    header_line = " | ".join(header.ljust(widths[header]) for header in headers)
    print(header_line)
    print("-" * len(header_line))
    
    # 打印数据行
    for row in data:
        row_line = " | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers)
        print(row_line)


def cmd_status(manager: LoadBalancerManager, args):
    """查看负载均衡器状态"""
    result = manager.get_status()
    print_result(result)


def cmd_list(manager: LoadBalancerManager, args):
    """列出所有后端"""
    result = manager.list_backends()
    
    if "error" in result:
        print_result(result)
        return
    
    if "data" in result and "backends" in result["data"]:
        backends_data = result["data"]["backends"]
        
        # 准备表格数据
        table_data = []
        for name, info in backends_data.items():
            config = info.get("config", {})
            metrics = info.get("metrics", {})
            
            table_data.append({
                "名称": name,
                "URL": config.get("url", ""),
                "模型": config.get("model_name", ""),
                "权重": config.get("weight", 1),
                "状态": metrics.get("status", "unknown"),
                "成功率": f"{metrics.get('success_rate', 0):.2%}",
                "平均响应时间": f"{metrics.get('average_response_time', 0):.2f}s",
                "总请求数": metrics.get("total_requests", 0),
                "活跃连接": metrics.get("active_connections", 0)
            })
        
        print(f"\n📊 负载均衡策略: {result['data'].get('strategy', 'unknown')}")
        print(f"🔢 总后端数: {result['data'].get('total_backends', 0)}")
        print(f"✅ 健康后端数: {result['data'].get('healthy_backends', 0)}")
        print("\n📋 后端列表:")
        
        headers = ["名称", "URL", "模型", "权重", "状态", "成功率", "平均响应时间", "总请求数", "活跃连接"]
        print_table(table_data, headers)
    else:
        print_result(result)


def cmd_add(manager: LoadBalancerManager, args):
    """添加后端"""
    result = manager.add_backend(
        name=args.name,
        url=args.url,
        model_name=args.model_name,
        api_key=args.backend_api_key,
        weight=args.weight,
        max_connections=args.max_connections,
        timeout=args.timeout
    )
    print_result(result)


def cmd_remove(manager: LoadBalancerManager, args):
    """移除后端"""
    result = manager.remove_backend(args.backend_name)
    print_result(result)


def cmd_enable(manager: LoadBalancerManager, args):
    """启用后端"""
    result = manager.enable_backend(args.backend_name)
    print_result(result)


def cmd_disable(manager: LoadBalancerManager, args):
    """禁用后端"""
    result = manager.disable_backend(args.backend_name)
    print_result(result)


def cmd_health_check(manager: LoadBalancerManager, args):
    """手动健康检查"""
    result = manager.health_check(args.backend_name)
    print_result(result)


def cmd_strategy(manager: LoadBalancerManager, args):
    """管理负载均衡策略"""
    if args.action == "get":
        result = manager.get_strategy()
        print_result(result)
    elif args.action == "set":
        result = manager.update_strategy(
            strategy=args.strategy,
            health_check_interval=args.health_check_interval,
            max_retries=args.max_retries,
            failure_threshold=args.failure_threshold
        )
        print_result(result)


def cmd_metrics(manager: LoadBalancerManager, args):
    """查看指标"""
    result = manager.get_metrics()
    print_result(result)


def cmd_health_check_control(manager: LoadBalancerManager, args):
    """控制健康检查"""
    if args.action == "start":
        result = manager.start_health_check()
    elif args.action == "stop":
        result = manager.stop_health_check()
    else:
        print("❌ 无效的健康检查操作")
        return
    
    print_result(result)


def main():
    parser = argparse.ArgumentParser(description="Lingualink负载均衡器管理工具")
    parser.add_argument("--server-url", default=None, help="服务器URL")
    parser.add_argument("--api-key", default=None, help="API密钥")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 状态命令
    subparsers.add_parser("status", help="查看负载均衡器状态")
    
    # 列出后端命令
    subparsers.add_parser("list", help="列出所有后端")
    
    # 添加后端命令
    add_parser = subparsers.add_parser("add", help="添加后端")
    add_parser.add_argument("--name", required=True, help="后端名称")
    add_parser.add_argument("--url", required=True, help="后端URL")
    add_parser.add_argument("--model-name", required=True, help="模型名称")
    add_parser.add_argument("--backend-api-key", required=True, help="后端API密钥")
    add_parser.add_argument("--weight", type=int, default=1, help="权重")
    add_parser.add_argument("--max-connections", type=int, default=50, help="最大连接数")
    add_parser.add_argument("--timeout", type=float, default=30.0, help="超时时间")
    
    # 移除后端命令
    remove_parser = subparsers.add_parser("remove", help="移除后端")
    remove_parser.add_argument("backend_name", help="后端名称")
    
    # 启用后端命令
    enable_parser = subparsers.add_parser("enable", help="启用后端")
    enable_parser.add_argument("backend_name", help="后端名称")
    
    # 禁用后端命令
    disable_parser = subparsers.add_parser("disable", help="禁用后端")
    disable_parser.add_argument("backend_name", help="后端名称")
    
    # 健康检查命令
    health_parser = subparsers.add_parser("health-check", help="手动健康检查")
    health_parser.add_argument("backend_name", help="后端名称")
    
    # 策略管理命令
    strategy_parser = subparsers.add_parser("strategy", help="管理负载均衡策略")
    strategy_subparsers = strategy_parser.add_subparsers(dest="action", help="策略操作")
    
    strategy_subparsers.add_parser("get", help="获取当前策略")
    
    set_strategy_parser = strategy_subparsers.add_parser("set", help="设置策略")
    set_strategy_parser.add_argument("--strategy", required=True, 
                                   choices=["round_robin", "weighted_round_robin", 
                                          "least_connections", "random", 
                                          "consistent_hash", "response_time"],
                                   help="负载均衡策略")
    set_strategy_parser.add_argument("--health-check-interval", type=float, help="健康检查间隔")
    set_strategy_parser.add_argument("--max-retries", type=int, help="最大重试次数")
    set_strategy_parser.add_argument("--failure-threshold", type=int, help="故障阈值")
    
    # 指标命令
    subparsers.add_parser("metrics", help="查看性能指标")
    
    # 健康检查控制命令
    hc_control_parser = subparsers.add_parser("health-check-control", help="控制自动健康检查")
    hc_control_parser.add_argument("action", choices=["start", "stop"], help="操作")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 创建管理器
    manager = LoadBalancerManager(args.server_url, args.api_key)
    
    # 执行命令
    command_map = {
        "status": cmd_status,
        "list": cmd_list,
        "add": cmd_add,
        "remove": cmd_remove,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "health-check": cmd_health_check,
        "strategy": cmd_strategy,
        "metrics": cmd_metrics,
        "health-check-control": cmd_health_check_control
    }
    
    if args.command in command_map:
        command_map[args.command](manager, args)
    else:
        print(f"❌ 未知命令: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main() 