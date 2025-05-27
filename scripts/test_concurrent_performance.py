#!/usr/bin/env python3
"""
Lingualink Server 并发性能测试脚本

用途: 测试50并发用户的OPUS音频转换性能
要求: 需要准备测试音频文件和有效的API密钥
"""

import asyncio
import aiohttp
import time
import argparse
import json
import statistics
from pathlib import Path
from typing import List, Dict, Any
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class PerformanceResult:
    """性能测试结果"""
    
    def __init__(self):
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_time = 0.0
        self.response_times = []
        self.error_details = []
        
    def add_success(self, response_time: float):
        """添加成功请求"""
        self.successful_requests += 1
        self.response_times.append(response_time)
        
    def add_failure(self, error: str, response_time: float = 0.0):
        """添加失败请求"""
        self.failed_requests += 1
        self.error_details.append({
            "error": error,
            "response_time": response_time
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        total_requests = self.successful_requests + self.failed_requests
        success_rate = (self.successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        if self.response_times:
            avg_response_time = statistics.mean(self.response_times)
            median_response_time = statistics.median(self.response_times)
            p95_response_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
            min_response_time = min(self.response_times)
            max_response_time = max(self.response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = 0
            min_response_time = max_response_time = 0
            
        throughput = self.successful_requests / self.total_time if self.total_time > 0 else 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": round(success_rate, 2),
            "total_test_time_seconds": round(self.total_time, 2),
            "throughput_requests_per_second": round(throughput, 2),
            "response_times": {
                "average_seconds": round(avg_response_time, 2),
                "median_seconds": round(median_response_time, 2),
                "p95_seconds": round(p95_response_time, 2),
                "min_seconds": round(min_response_time, 2),
                "max_seconds": round(max_response_time, 2)
            },
            "errors": self.error_details[:10]  # 只显示前10个错误
        }


async def upload_audio_file(
    session: aiohttp.ClientSession,
    server_url: str,
    audio_file_path: Path,
    api_key: str,
    user_prompt: str = "请处理这段音频",
    target_languages: List[str] = None
) -> Dict[str, Any]:
    """
    上传单个音频文件进行处理
    
    Args:
        session: aiohttp客户端会话
        server_url: 服务器URL
        audio_file_path: 音频文件路径
        api_key: API密钥
        user_prompt: 用户提示词
        target_languages: 目标语言列表
        
    Returns:
        dict: 请求结果
    """
    start_time = time.time()
    
    try:
        # 准备表单数据
        data = aiohttp.FormData()
        
        # 添加音频文件
        with open(audio_file_path, 'rb') as f:
            data.add_field(
                'audio_file',
                f.read(),
                filename=audio_file_path.name,
                content_type='audio/opus' if audio_file_path.suffix.lower() == '.opus' else 'audio/wav'
            )
        
        # 添加其他参数
        data.add_field('user_prompt', user_prompt)
        
        if target_languages:
            for lang in target_languages:
                data.add_field('target_languages', lang)
        
        # 设置请求头
        headers = {'X-API-Key': api_key}
        
        # 发送请求
        url = f"{server_url}/api/v1/translate_audio"
        async with session.post(url, data=data, headers=headers) as response:
            response_time = time.time() - start_time
            
            if response.status == 200:
                result = await response.json()
                return {
                    "success": True,
                    "response_time": response_time,
                    "status_code": response.status,
                    "result": result
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "response_time": response_time,
                    "status_code": response.status,
                    "error": f"HTTP {response.status}: {error_text}"
                }
                
    except Exception as e:
        response_time = time.time() - start_time
        return {
            "success": False,
            "response_time": response_time,
            "status_code": 0,
            "error": str(e)
        }


async def run_concurrent_test(
    server_url: str,
    audio_file_path: Path,
    api_key: str,
    concurrent_users: int = 50,
    user_prompt: str = "请处理这段音频",
    target_languages: List[str] = None,
    timeout: int = 300
) -> PerformanceResult:
    """
    运行并发性能测试
    
    Args:
        server_url: 服务器URL
        audio_file_path: 测试音频文件路径
        api_key: API密钥
        concurrent_users: 并发用户数
        user_prompt: 用户提示词
        target_languages: 目标语言列表
        timeout: 请求超时时间（秒）
        
    Returns:
        PerformanceResult: 测试结果
    """
    print(f"🚀 开始并发性能测试")
    print(f"   服务器: {server_url}")
    print(f"   音频文件: {audio_file_path}")
    print(f"   并发用户: {concurrent_users}")
    print(f"   超时时间: {timeout}秒")
    print("-" * 60)
    
    result = PerformanceResult()
    
    # 创建HTTP客户端连接池
    connector = aiohttp.TCPConnector(
        limit=concurrent_users + 10,  # 连接池大小
        limit_per_host=concurrent_users + 10,
        ttl_dns_cache=300
    )
    
    timeout_config = aiohttp.ClientTimeout(total=timeout)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout_config
    ) as session:
        
        # 创建并发任务
        tasks = [
            upload_audio_file(
                session=session,
                server_url=server_url,
                audio_file_path=audio_file_path,
                api_key=api_key,
                user_prompt=user_prompt,
                target_languages=target_languages
            )
            for _ in range(concurrent_users)
        ]
        
        # 开始计时
        start_time = time.time()
        print(f"⏱️  {time.strftime('%H:%M:%S')} - 开始发送 {concurrent_users} 个并发请求...")
        
        # 执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 结束计时
        result.total_time = time.time() - start_time
        print(f"⏱️  {time.strftime('%H:%M:%S')} - 所有请求完成，总耗时: {result.total_time:.2f}秒")
        
        # 处理结果
        for i, task_result in enumerate(results):
            if isinstance(task_result, Exception):
                result.add_failure(f"Task exception: {task_result}")
            elif task_result["success"]:
                result.add_success(task_result["response_time"])
            else:
                result.add_failure(task_result["error"], task_result["response_time"])
        
    return result


async def get_server_status(server_url: str, api_key: str) -> Dict[str, Any]:
    """获取服务器状态"""
    try:
        headers = {'X-API-Key': api_key}
        async with aiohttp.ClientSession() as session:
            # 检查健康状态
            async with session.get(f"{server_url}/api/v1/health") as response:
                if response.status != 200:
                    return {"error": f"Health check failed: {response.status}"}
                
            # 获取并发状态（需要API密钥）
            async with session.get(f"{server_url}/api/v1/concurrent-status", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Failed to get concurrent status: {response.status}"}
                    
    except Exception as e:
        return {"error": str(e)}


def print_test_results(result: PerformanceResult, concurrent_users: int):
    """打印测试结果"""
    summary = result.get_summary()
    
    print("\n" + "=" * 60)
    print("📊 并发性能测试结果")
    print("=" * 60)
    
    print(f"总请求数: {summary['total_requests']}")
    print(f"成功请求: {summary['successful_requests']} ({summary['success_rate_percent']}%)")
    print(f"失败请求: {summary['failed_requests']}")
    print(f"总测试时间: {summary['total_test_time_seconds']}秒")
    print(f"吞吐量: {summary['throughput_requests_per_second']} 请求/秒")
    
    print("\n📈 响应时间统计:")
    response_times = summary['response_times']
    print(f"  平均响应时间: {response_times['average_seconds']}秒")
    print(f"  中位数响应时间: {response_times['median_seconds']}秒")
    print(f"  95百分位响应时间: {response_times['p95_seconds']}秒")
    print(f"  最快响应时间: {response_times['min_seconds']}秒")
    print(f"  最慢响应时间: {response_times['max_seconds']}秒")
    
    if summary['errors']:
        print(f"\n❌ 错误示例 (显示前10个):")
        for i, error in enumerate(summary['errors'][:10], 1):
            print(f"  {i}. {error['error']}")
    
    # 性能评估
    print(f"\n🎯 性能评估:")
    avg_time = response_times['average_seconds']
    throughput = summary['throughput_requests_per_second']
    
    if avg_time < 3 and throughput > 5:
        print("  ✅ 优秀 - 满足50并发用户需求")
    elif avg_time < 5 and throughput > 3:
        print("  ⚠️  良好 - 基本满足需求，可考虑优化")
    else:
        print("  ❌ 需要优化 - 未达到性能目标")
        
    print("=" * 60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Lingualink Server 并发性能测试")
    parser.add_argument("--server", default="http://localhost:5000", help="服务器URL")
    parser.add_argument("--audio-file", required=True, help="测试音频文件路径")
    parser.add_argument("--api-key", required=True, help="API密钥")
    parser.add_argument("--concurrent", type=int, default=50, help="并发用户数")
    parser.add_argument("--prompt", default="请处理这段音频", help="用户提示词")
    parser.add_argument("--languages", nargs="+", default=["英文", "日文"], help="目标语言")
    parser.add_argument("--timeout", type=int, default=300, help="请求超时时间（秒）")
    parser.add_argument("--pre-check", action="store_true", help="测试前检查服务器状态")
    parser.add_argument("--output", help="结果输出到JSON文件")
    
    args = parser.parse_args()
    
    # 验证音频文件
    audio_file = Path(args.audio_file)
    if not audio_file.exists():
        print(f"❌ 音频文件不存在: {audio_file}")
        return 1
        
    # 检查服务器状态
    if args.pre_check:
        print("🔍 检查服务器状态...")
        status = await get_server_status(args.server, args.api_key)
        if "error" in status:
            print(f"❌ 服务器状态检查失败: {status['error']}")
            return 1
        else:
            print("✅ 服务器状态正常")
            concurrent_config = status.get("concurrent_processing", {})
            print(f"   当前活跃转换: {concurrent_config.get('active_conversions', 0)}")
            print(f"   最大并发数: {concurrent_config.get('max_concurrent_conversions', 'Unknown')}")
            print()
    
    # 运行性能测试
    try:
        result = await run_concurrent_test(
            server_url=args.server,
            audio_file_path=audio_file,
            api_key=args.api_key,
            concurrent_users=args.concurrent,
            user_prompt=args.prompt,
            target_languages=args.languages,
            timeout=args.timeout
        )
        
        # 打印结果
        print_test_results(result, args.concurrent)
        
        # 保存结果到文件
        if args.output:
            summary = result.get_summary()
            summary["test_config"] = {
                "server_url": args.server,
                "audio_file": str(audio_file),
                "concurrent_users": args.concurrent,
                "user_prompt": args.prompt,
                "target_languages": args.languages,
                "timeout": args.timeout
            }
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"\n💾 结果已保存到: {args.output}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  程序被中断")
        sys.exit(130) 