import secrets
import sys
from typing import Optional


def generate_initial_api_key(name: Optional[str] = None) -> str:
    """
    生成初始API密钥的工具函数
    
    Args:
        name: 密钥名称
        
    Returns:
        str: 生成的API密钥
    """
    api_key = f"lls_{secrets.token_urlsafe(32)}"
    
    print(f"Generated API Key: {api_key}")
    if name:
        print(f"Key Name: {name}")
    print("\nPlease save this API key securely. You will need it to access the API.")
    print("Add it to your .env file as:")
    print(f'API_KEYS=["your-existing-keys", "{api_key}"]')
    
    return api_key


def main():
    """命令行工具入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate API key for Lingualink Server")
    parser.add_argument("--name", "-n", help="Name for the API key", default=None)
    
    args = parser.parse_args()
    
    generate_initial_api_key(args.name)


if __name__ == "__main__":
    main() 