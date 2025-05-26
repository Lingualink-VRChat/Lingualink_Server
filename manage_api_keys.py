#!/usr/bin/env python3
"""
Lingualink Server API密钥管理工具 v2.0
基于SQLite数据库的密钥管理系统
支持查看、生成、撤销API密钥，包括有效期管理
"""

import requests
import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os


class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    def set_api_key(self, api_key: str):
        """设置API密钥"""
        self.api_key = api_key
        self.headers["X-API-Key"] = api_key
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def verify_current_key(self) -> Dict:
        """验证当前密钥"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/auth/verify",
                headers=self.headers,
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def list_keys(self, include_inactive: bool = False) -> Dict:
        """列出所有密钥"""
        try:
            params = {}
            if include_inactive:
                params["include_inactive"] = "true"
            
            response = requests.get(
                f"{self.base_url}/api/v1/auth/keys",
                headers=self.headers,
                params=params,
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def generate_key(self, name: str = None, expires_in_days: int = None, description: str = None) -> Dict:
        """生成新密钥"""
        try:
            data = {}
            if name:
                data["name"] = name
            if expires_in_days:
                data["expires_in_days"] = expires_in_days
            if description:
                data["description"] = description
            
            response = requests.post(
                f"{self.base_url}/api/v1/auth/generate_key",
                headers=self.headers,
                data=data,
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def revoke_key(self, api_key_to_revoke: str) -> Dict:
        """撤销密钥"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/revoke_key",
                headers=self.headers,
                data={"api_key_to_revoke": api_key_to_revoke},
                timeout=10
            )
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}


class LocalKeyManager:
    """本地密钥管理器（直接操作数据库）"""
    
    def __init__(self):
        # 添加项目路径到Python路径
        import sys
        # Get the absolute path to the project root directory
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        src_path = os.path.join(project_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        if project_root not in sys.path: # also add project root for lingualink itself
             sys.path.insert(0, project_root)
        
        try:
            from lingualink.auth.auth_service import auth_service # Adjusted import
            from lingualink.models.database import get_db_session # Adjusted import
            self.auth_service = auth_service
        except ImportError as e:
            print(f"❌ 无法导入本地服务: {e}")
            self.auth_service = None
    
    def is_available(self) -> bool:
        """检查本地管理器是否可用"""
        return self.auth_service is not None
    
    def list_keys(self, include_inactive: bool = False) -> List[Dict]:
        """列出所有密钥"""
        if not self.is_available():
            return []
        
        try:
            return self.auth_service.list_api_keys(include_inactive)
        except Exception as e:
            print(f"❌ 获取密钥列表失败: {e}")
            return []
    
    def generate_key(self, name: str = None, expires_in_days: int = None, description: str = None, is_admin: bool = False) -> Optional[str]:
        """生成新密钥"""
        if not self.is_available():
            return None
        
        try:
            return self.auth_service.generate_api_key(
                name=name,
                expires_in_days=expires_in_days,
                description=description,
                created_by="local_cli",
                is_admin=is_admin
            )
        except Exception as e:
            print(f"❌ 生成密钥失败: {e}")
            return None
    
    def revoke_key(self, api_key: str) -> bool:
        """撤销密钥"""
        if not self.is_available():
            return False
        
        try:
            return self.auth_service.revoke_api_key(api_key)
        except Exception as e:
            print(f"❌ 撤销密钥失败: {e}")
            return False
    
    def get_key_info(self, api_key: str) -> Optional[Dict]:
        """获取密钥信息"""
        if not self.is_available():
            return None
        
        try:
            return self.auth_service.get_key_info(api_key)
        except Exception as e:
            print(f"❌ 获取密钥信息失败: {e}")
            return None

    def set_admin_status(self, api_key: str, is_admin: bool) -> bool:
        """设置密钥的管理员状态"""
        if not self.is_available():
            return False
        
        try:
            return self.auth_service.set_admin_status(api_key, is_admin)
        except Exception as e:
            print(f"❌ 设置管理员状态失败: {e}")
            return False


def format_datetime(dt_str: str) -> str:
    """格式化日期时间显示"""
    if not dt_str:
        return "永不过期"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


def format_expiry_status(expires_at: str) -> str:
    """格式化过期状态"""
    if not expires_at:
        return "✅ 永久有效"
    
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        now = datetime.now(expires_dt.tzinfo) if expires_dt.tzinfo else datetime.now()
        
        if now > expires_dt:
            return "❌ 已过期"
        
        days_left = (expires_dt - now).days
        if days_left == 0:
            hours_left = int((expires_dt - now).total_seconds() / 3600)
            return f"⚠️ 今天过期（还剩{hours_left}小时）"
        elif days_left <= 7:
            return f"⚠️ {days_left}天后过期"
        else:
            return f"✅ {days_left}天后过期"
    except:
        return "❓ 无法解析过期时间"


def cmd_list_keys(manager, args):
    """列出所有密钥命令"""
    print("📋 获取API密钥列表...")
    
    if isinstance(manager, LocalKeyManager):
        keys = manager.list_keys(args.include_inactive)
        if not keys:
            print("📭 暂无API密钥")
            return
        
        result_data = {"keys": keys}
    else:
        result = manager.list_keys(args.include_inactive)
        if result.get("status") != "success":
            print(f"❌ 获取失败: {result.get('message', '未知错误')}")
            return
        
        result_data = result.get("data", {})
        keys = result_data.get("keys", [])
        
        if not keys:
            print("📭 暂无API密钥")
            return
    
    keys = result_data.get("keys", [])
    print(f"\n🗝️  共找到 {len(keys)} 个API密钥:")
    print("=" * 100)
    
    for i, key_info in enumerate(keys, 1):
        print(f"\n#{i} 密钥: {key_info.get('name', 'Unknown')}")
        print(f"   ID: {key_info.get('id', 'N/A')}")
        print(f"   创建时间: {format_datetime(key_info.get('created_at'))}")
        print(f"   过期时间: {format_datetime(key_info.get('expires_at'))}")
        print(f"   使用次数: {key_info.get('usage_count', 0)}")
        print(f"   最后使用: {format_datetime(key_info.get('last_used_at')) if key_info.get('last_used_at') else '从未使用'}")
        print(f"   状态: {format_expiry_status(key_info.get('expires_at'))}")
        print(f"   活跃状态: {'✅ 活跃' if key_info.get('is_active') else '🚫 已禁用'}")
        print(f"   创建者: {key_info.get('created_by', 'Unknown')}")
        if key_info.get('is_admin'):
            print(f"   权限: 👑 管理员")
        if key_info.get('description'):
            print(f"   描述: {key_info['description']}")


def cmd_generate_key(manager, args):
    """生成新密钥命令"""
    name = args.name or input("请输入密钥名称（可选，按回车跳过）: ").strip() or None
    
    if args.expires_in_days is not None:
        expires_days = args.expires_in_days
    else:
        expires_input = input("请输入有效天数（可选，按回车创建永久密钥）: ").strip()
        expires_days = int(expires_input) if expires_input.isdigit() else None
    
    description = args.description or input("请输入密钥描述（可选，按回车跳过）: ").strip() or None
    
    is_admin_input = ""
    if args.make_admin is None:
        is_admin_input = input("是否设置为管理员密钥? (y/N): ").strip().lower()
    make_admin = args.make_admin or (is_admin_input == 'y')

    print(f"🔄 生成新的API密钥...")
    if expires_days:
        print(f"   名称: {name or '(未设置)'}")
        print(f"   有效期: {expires_days} 天")
        print(f"   描述: {description or '(未设置)'}")
    if make_admin:
        print(f"   权限: 👑 管理员")
    
    if isinstance(manager, LocalKeyManager):
        new_key = manager.generate_key(name, expires_days, description, make_admin)
        if not new_key:
            print("❌ 生成失败")
            return
        
        key_name = name or f"key_{new_key[:8]}"
        success = True
    else:
        result = manager.generate_key(name, expires_days, description)
        if result.get("status") != "success":
            print(f"❌ 生成失败: {result.get('message', '未知错误')}")
            return
        
        data = result.get("data", {})
        new_key = data.get("api_key")
        key_name = data.get("name")
        success = True
    
    if success:
        print(f"\n✅ 密钥生成成功!")
        print("=" * 80)
        print(f"密钥名称: {key_name}")
        print(f"API密钥: {new_key}")
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
            print(f"过期时间: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} ({expires_days}天后)")
        else:
            print(f"过期时间: 永不过期")
        
        print(f"\n📝 使用方法:")
        print(f"curl -H 'X-API-Key: {new_key}' http://localhost:5000/api/v1/health")
        
        print(f"\n⚠️  重要提醒:")
        print(f"   请妥善保存此密钥，系统不会再次显示完整密钥")


def cmd_verify_key(manager, args):
    """验证密钥命令"""
    if isinstance(manager, LocalKeyManager):
        if args.api_key:
            key_info = manager.get_key_info(args.api_key)
            if not key_info:
                print("❌ 密钥不存在")
                return
            
            print("✅ 密钥验证成功!")
            print("=" * 50)
            print(f"密钥名称: {key_info.get('name')}")
            print(f"创建时间: {format_datetime(key_info.get('created_at'))}")
            print(f"过期时间: {format_datetime(key_info.get('expires_at'))}")
            print(f"使用次数: {key_info.get('usage_count', 0)}")
            print(f"状态: {format_expiry_status(key_info.get('expires_at'))}")
        else:
            print("❌ 请提供要验证的API密钥")
    else:
        print("🔍 验证当前API密钥...")
        
        result = manager.verify_current_key()
        if result.get("status") != "success":
            print(f"❌ 验证失败: {result.get('message', '未知错误')}")
            return
        
        data = result.get("data", {})
        if not data.get("name"):  # 认证被禁用
            print("✅ 认证已禁用，无需密钥验证")
            return
        
        print("✅ 密钥验证成功!")
        print("=" * 50)
        print(f"密钥名称: {data.get('name')}")
        print(f"创建时间: {format_datetime(data.get('created_at'))}")
        print(f"过期时间: {format_datetime(data.get('expires_at'))}")
        print(f"使用次数: {data.get('usage_count', 0)}")
        print(f"状态: {format_expiry_status(data.get('expires_at'))}")


def cmd_revoke_key(manager, args):
    """撤销密钥命令"""
    if args.key_to_revoke:
        key_to_revoke = args.key_to_revoke
    else:
        key_to_revoke = input("请输入要撤销的API密钥: ").strip()
    
    if not key_to_revoke:
        print("❌ 未提供要撤销的密钥")
        return
    
    # 确认操作
    confirm = input(f"确认撤销密钥 {key_to_revoke[:16]}...? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 操作已取消")
        return
    
    print("🔄 撤销API密钥...")
    
    if isinstance(manager, LocalKeyManager):
        success = manager.revoke_key(key_to_revoke)
        if success:
            print("✅ 密钥撤销成功!")
        else:
            print("❌ 撤销失败: 密钥不存在或已撤销")
    else:
        result = manager.revoke_key(key_to_revoke)
        
        if result.get("status") == "success":
            print("✅ 密钥撤销成功!")
        else:
            print(f"❌ 撤销失败: {result.get('message', '未知错误')}")


def cmd_set_admin(manager, args):
    """设置密钥的管理员状态命令"""
    if not args.key_to_modify:
        print("❌ 未提供要修改的密钥")
        return

    new_status_str = args.status.lower()
    if new_status_str not in ["true", "false"]:
        print("❌ 无效的状态，请输入 'true' 或 'false'")
        return
    new_status = new_status_str == "true"

    print(f"🔄 设置密钥 '{args.key_to_modify[:16]}...' 的管理员状态为 {new_status}...")

    if isinstance(manager, LocalKeyManager):
        success = manager.set_admin_status(args.key_to_modify, new_status)
        if success:
            print("✅ 管理员状态更新成功!")
        else:
            print("❌ 更新管理员状态失败。")
    else:
        # Note: Remote setting of admin status via API is intentionally not directly supported by this client
        # for security reasons. Admin status should be managed locally or via a highly secured admin API endpoint if ever implemented.
        print("❌ 通过远程API设置管理员状态当前不受此工具直接支持。请使用 --local 模式。")


def main():
    parser = argparse.ArgumentParser(description="Lingualink Server API密钥管理工具 v2.0")
    parser.add_argument("--url", default="http://localhost:5000", help="服务器地址")
    parser.add_argument("--api-key", help="当前API密钥（用于认证）")
    parser.add_argument("--local", action="store_true", help="使用本地数据库管理（无需服务器运行）")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出密钥
    list_parser = subparsers.add_parser("list", help="列出所有API密钥")
    list_parser.add_argument("--include-inactive", action="store_true", help="包含已撤销的密钥")
    
    # 生成密钥
    gen_parser = subparsers.add_parser("generate", help="生成新的API密钥")
    gen_parser.add_argument("--name", help="密钥名称")
    gen_parser.add_argument("--expires-in-days", type=int, help="有效天数")
    gen_parser.add_argument("--description", help="密钥描述")
    gen_parser.add_argument("--make-admin", action=argparse.BooleanOptionalAction, help="将新密钥设置为管理员")
    
    # 验证密钥
    verify_parser = subparsers.add_parser("verify", help="验证API密钥")
    
    # 撤销密钥
    revoke_parser = subparsers.add_parser("revoke", help="撤销API密钥")
    revoke_parser.add_argument("--key", dest="key_to_revoke", help="要撤销的密钥")
    
    # 设置管理员状态 (仅本地)
    set_admin_parser = subparsers.add_parser("set-admin", help="设置密钥的管理员状态 (仅本地模式)")
    set_admin_parser.add_argument("key_to_modify", help="要修改的API密钥值")
    set_admin_parser.add_argument("status", choices=["true", "false"], help="管理员状态 (true/false)")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 选择管理器
    if args.local:
        print("🗃️  使用本地数据库管理模式")
        manager = LocalKeyManager()
        if not manager.is_available():
            print("❌ 本地管理器不可用，请检查环境配置")
            return
    else:
        print("🌐 使用远程API管理模式")
        manager = APIKeyManager(args.url, args.api_key)
        
        # 测试连接
        if not manager.test_connection():
            print(f"❌ 无法连接到服务器: {args.url}")
            print("请确认服务器正在运行且地址正确，或使用 --local 参数进行本地管理")
            return
        
        # 获取API密钥（如果未提供）
        if not args.api_key and args.command in ["list", "generate", "revoke"]:
            api_key = input("请输入API密钥: ").strip()
            if not api_key:
                print("❌ 未提供API密钥")
                return
            manager.set_api_key(api_key)
    
    # 执行命令
    commands = {
        "list": cmd_list_keys,
        "generate": cmd_generate_key,
        "verify": cmd_verify_key,
        "revoke": cmd_revoke_key,
        "set-admin": cmd_set_admin
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            cmd_func(manager, args)
        except KeyboardInterrupt:
            print("\n\n❌ 操作已取消")
        except Exception as e:
            print(f"\n❌ 执行命令时发生错误: {e}")
            if args.local:
                import traceback
                traceback.print_exc()
    else:
        print(f"❌ 未知命令: {args.command}")


if __name__ == "__main__":
    main() 