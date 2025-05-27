# 🚀 API密钥验证性能优化建议

## 1. 内存缓存方案

### Redis缓存实现
```python
import redis
from datetime import timedelta

class CachedAuthService(AuthService):
    def __init__(self):
        super().__init__()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.cache_ttl = 300  # 5分钟缓存
    
    def verify_api_key(self, api_key: str) -> tuple[bool, bool]:
        # 首先检查缓存
        cache_key = f"api_key:{api_key[:16]}"  # 使用部分密钥作为缓存键
        cached_result = self.redis_client.get(cache_key)
        
        if cached_result:
            is_valid, is_admin = json.loads(cached_result)
            return is_valid, is_admin
        
        # 缓存未命中，查询数据库
        is_valid, is_admin = super().verify_api_key(api_key)
        
        # 存入缓存（只缓存有效的密钥）
        if is_valid:
            self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps([is_valid, is_admin])
            )
        
        return is_valid, is_admin
```

**性能提升：**
- 缓存命中：~0.1-0.5ms
- 缓存未命中：~2-8ms（首次查询）
- 整体性能提升：80-90%

## 2. 数据库优化

### 索引优化
```sql
-- 确保API密钥字段有索引（已有）
CREATE INDEX IF NOT EXISTS idx_api_key ON api_keys(api_key);

-- 添加复合索引优化查询
CREATE INDEX IF NOT EXISTS idx_api_key_active_expires 
ON api_keys(api_key, is_active, expires_at);
```

### 连接池优化
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# 使用连接池减少数据库连接开销
engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## 3. 异步更新策略

将使用统计更新改为异步，减少实时验证延迟：

```python
import asyncio
from collections import deque

class AsyncStatsUpdater:
    def __init__(self):
        self.update_queue = deque()
        self.batch_size = 100
        
    async def queue_usage_update(self, api_key: str):
        """异步队列使用统计更新"""
        self.update_queue.append({
            'api_key': api_key,
            'timestamp': datetime.utcnow()
        })
        
        if len(self.update_queue) >= self.batch_size:
            await self.flush_updates()
    
    async def flush_updates(self):
        """批量更新使用统计"""
        # 批量更新数据库，减少事务开销
        pass
```

## 4. 混合方案：API密钥 + 短期会话

```python
class HybridAuthService:
    """混合认证：API密钥验证 + 短期会话缓存"""
    
    def create_session_token(self, api_key: str) -> str:
        """验证API密钥后，创建短期会话令牌"""
        is_valid, is_admin = self.verify_api_key_from_db(api_key)
        if not is_valid:
            raise AuthError("Invalid API key")
        
        # 创建30分钟有效的会话令牌
        session_token = jwt.encode({
            'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest()[:16],
            'is_admin': is_admin,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, settings.secret_key)
        
        return session_token
    
    def verify_session_token(self, token: str) -> tuple[bool, bool]:
        """验证会话令牌（无需数据库查询）"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=['HS256'])
            return True, payload.get('is_admin', False)
        except jwt.InvalidTokenError:
            return False, False
```

## 5. 配置建议

### 高并发场景配置
```env
# .env 配置
# 启用Redis缓存
REDIS_URL=redis://localhost:6379/0
API_KEY_CACHE_TTL=300

# 数据库连接池
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# 异步更新配置
ASYNC_STATS_UPDATE=true
STATS_BATCH_SIZE=100
```

## 6. 监控指标

添加性能监控：
```python
import time
from functools import wraps

def monitor_auth_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        # 记录到监控系统
        logger.info(f"Auth verification took {duration*1000:.2f}ms")
        return result
    return wrapper
```

## 总结

**推荐的优化优先级：**
1. **Redis缓存**（立即生效，大幅提升性能）
2. **数据库索引优化**（简单有效）
3. **异步统计更新**（中等复杂度，显著减少延迟）
4. **混合方案**（复杂但兼顾安全和性能）

**预期性能提升：**
- 基础优化：50-70%
- 加上缓存：80-90%
- 完整优化：95%+

这样既保持了API密钥的安全优势，又解决了性能问题。 