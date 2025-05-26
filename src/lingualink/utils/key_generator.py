import secrets
import sys
from typing import Optional
from datetime import datetime, timedelta


def generate_initial_api_key(name: Optional[str] = None, expires_in_days: Optional[int] = None) -> str:
    """
    生成初始API密钥的工具函数
    
    Args:
        name: 密钥名称
        expires_in_days: 过期天数（可选）
        
    Returns:
        str: 生成的API密钥
    """
    api_key = f"lls_{secrets.token_urlsafe(32)}"
    
    print(f"Generated API Key: {api_key}")
    if name:
        print(f"Key Name: {name}")
    
    if expires_in_days:
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        print(f"Expires in: {expires_in_days} days ({expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
    else:
        print("Expires in: Never (permanent key)")
    
    print("\nPlease save this API key securely. You will need it to access the API.")
    print("Add it to your .env file as:")
    print(f'API_KEYS=["your-existing-keys", "{api_key}"]')
    
    if expires_in_days:
        print(f"\n⚠️  提醒：此密钥将在 {expires_in_days} 天后过期")
        print("   你可以通过 API 或重新生成密钥来更新")
    
    return api_key


def main():
    """命令行工具入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate API key for Lingualink Server")
    parser.add_argument("--name", "-n", help="Name for the API key", default=None)
    parser.add_argument("--expires-in-days", "-e", type=int, help="Expiration time in days", default=None)
    
    args = parser.parse_args()
    
    generate_initial_api_key(args.name, args.expires_in_days)


if __name__ == "__main__":
    main() 