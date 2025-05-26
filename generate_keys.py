#!/usr/bin/env python3
"""
Lingualink Server 密钥生成工具
一键生成 SECRET_KEY 和 API_KEYS
"""

import secrets
import argparse
import json
import os
from pathlib import Path


def generate_secret_key():
    """生成 SECRET_KEY"""
    return secrets.token_urlsafe(32)


def generate_api_key(name=None):
    """生成 API 密钥"""
    key = f"lls_{secrets.token_urlsafe(32)}"
    return key


def update_env_file(secret_key, api_keys, env_file=".env"):
    """更新 .env 文件"""
    env_path = Path(env_file)
    
    # 读取现有内容
    lines = []
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # 更新或添加配置
    secret_key_updated = False
    api_keys_updated = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.startswith('SECRET_KEY='):
            lines[i] = f'SECRET_KEY={secret_key}\n'
            secret_key_updated = True
        elif line_stripped.startswith('API_KEYS='):
            api_keys_str = json.dumps(api_keys)
            lines[i] = f'API_KEYS={api_keys_str}\n'
            api_keys_updated = True
    
    # 如果没有找到配置项，添加到末尾
    if not secret_key_updated:
        lines.append(f'SECRET_KEY={secret_key}\n')
    
    if not api_keys_updated:
        api_keys_str = json.dumps(api_keys)
        lines.append(f'API_KEYS={api_keys_str}\n')
    
    # 写回文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def main():
    parser = argparse.ArgumentParser(description="生成 Lingualink Server 认证密钥")
    parser.add_argument("--secret-only", action="store_true", help="只生成 SECRET_KEY")
    parser.add_argument("--api-only", action="store_true", help="只生成 API_KEYS")
    parser.add_argument("--api-key-names", nargs="+", default=["main-client"], 
                       help="API 密钥名称列表")
    parser.add_argument("--count", type=int, default=1, help="生成的 API 密钥数量")
    parser.add_argument("--update-env", action="store_true", help="自动更新 .env 文件")
    parser.add_argument("--env-file", default=".env", help=".env 文件路径")
    
    args = parser.parse_args()
    
    print("🔐 Lingualink Server 密钥生成工具")
    print("=" * 50)
    
    secret_key = None
    api_keys = []
    
    # 生成 SECRET_KEY
    if not args.api_only:
        secret_key = generate_secret_key()
        print(f"\n🔑 SECRET_KEY (应用密钥):")
        print(f"SECRET_KEY={secret_key}")
        print("\n💡 用途: 用于应用内部加密、JWT签名等")
        print("⚠️  注意: 服务器端使用，客户端永远不应该知道此密钥")
    
    # 生成 API_KEYS
    if not args.secret_only:
        print(f"\n🗝️  API_KEYS (API访问密钥):")
        
        # 根据名称或数量生成密钥
        if len(args.api_key_names) > 1:
            # 使用提供的名称
            for name in args.api_key_names:
                key = generate_api_key(name)
                api_keys.append(key)
                print(f"  {name}: {key}")
        else:
            # 根据数量生成
            for i in range(args.count):
                name = args.api_key_names[0] if args.count == 1 else f"{args.api_key_names[0]}-{i+1}"
                key = generate_api_key(name)
                api_keys.append(key)
                print(f"  {name}: {key}")
        
        # 显示 JSON 格式
        api_keys_json = json.dumps(api_keys, indent=2)
        print(f"\nJSON 格式:")
        print(f"API_KEYS={json.dumps(api_keys)}")
        
        print(f"\n💡 用途: 客户端调用 API 时在请求头中提供")
        print(f"📝 使用方式: curl -H 'X-API-Key: {api_keys[0]}' ...")
    
    # 更新 .env 文件
    if args.update_env:
        try:
            # 如果只生成一种密钥，需要读取现有配置
            if args.secret_only or args.api_only:
                env_path = Path(args.env_file)
                existing_secret = None
                existing_api_keys = []
                
                if env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('SECRET_KEY='):
                                existing_secret = line.split('=', 1)[1]
                            elif line.startswith('API_KEYS='):
                                try:
                                    api_keys_str = line.split('=', 1)[1]
                                    existing_api_keys = json.loads(api_keys_str)
                                except json.JSONDecodeError:
                                    pass
                
                # 使用现有值或新生成的值
                final_secret = secret_key if secret_key else existing_secret
                final_api_keys = api_keys if api_keys else existing_api_keys
            else:
                final_secret = secret_key
                final_api_keys = api_keys
            
            if final_secret and final_api_keys:
                update_env_file(final_secret, final_api_keys, args.env_file)
                print(f"\n✅ 已更新 {args.env_file} 文件")
            else:
                print(f"\n❌ 无法更新 {args.env_file}，缺少必要的密钥")
                
        except Exception as e:
            print(f"\n❌ 更新 {args.env_file} 失败: {e}")
    
    print("\n" + "=" * 50)
    print("📋 接下来的步骤:")
    
    if not args.update_env:
        print("1. 将上述密钥复制到你的 .env 文件中")
        print("   或使用 --update-env 参数自动更新")
    
    print("2. 重启 Lingualink Server:")
    print("   python3 manage.py restart")
    
    print("3. 测试认证:")
    if api_keys:
        print(f"   curl -H 'X-API-Key: {api_keys[0]}' http://localhost:5000/api/v1/health")
    
    print("\n📚 更多信息请查看: docs/AUTHENTICATION_GUIDE.md")


if __name__ == "__main__":
    main() 