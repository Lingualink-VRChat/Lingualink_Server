import pytest
from fastapi.testclient import TestClient
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.lingualink.main import app
from src.lingualink.auth.auth_service import auth_service

client = TestClient(app)


class TestAuth:
    """鉴权功能测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 生成测试用的API密钥
        self.test_api_key = auth_service.generate_api_key("test_key")
    
    def test_health_check_no_auth(self):
        """测试健康检查不需要鉴权"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_ping_no_auth(self):
        """测试ping不需要鉴权"""
        response = client.get("/api/v1/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "pong"
    
    def test_verify_api_key_valid(self):
        """测试验证有效的API密钥"""
        headers = {"X-API-Key": self.test_api_key}
        response = client.get("/api/v1/auth/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "API key is valid"
    
    def test_verify_api_key_invalid(self):
        """测试验证无效的API密钥"""
        headers = {"X-API-Key": "invalid_key"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"
    
    def test_verify_api_key_missing(self):
        """测试缺少API密钥"""
        response = client.get("/api/v1/auth/verify")
        assert response.status_code == 401
        data = response.json()
        assert data["status"] == "error"
    
    def test_generate_new_api_key(self):
        """测试生成新的API密钥"""
        headers = {"X-API-Key": self.test_api_key}
        response = client.post(
            "/api/v1/auth/generate_key",
            headers=headers,
            params={"name": "new_test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "api_key" in data["data"]
        assert data["data"]["name"] == "new_test_key"
    
    def test_list_api_keys(self):
        """测试列出API密钥"""
        headers = {"X-API-Key": self.test_api_key}
        response = client.get("/api/v1/auth/keys", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "keys" in data["data"]
        assert "total" in data["data"]
    
    def test_bearer_token_auth(self):
        """测试Bearer token认证"""
        headers = {"Authorization": f"Bearer {self.test_api_key}"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success" 