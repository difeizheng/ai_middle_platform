# 缓存命中率提升方案

## 当前缓存服务状态

### 现有缓存配置

```python
# Redis 连接配置
redis = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)

# 缓存键前缀
prefix = {
    "user": "ai:user:",
    "token": "ai:token:",
    "rate_limit": "ai:rate:",
    "knowledge": "ai:kb:",
    "model": "ai:model:",
    "application": "ai:app:",
}

# 缓存过期时间
ttl = {
    "user_info": 3600,       # 用户信息 1 小时
    "token": 604800,         # Token 7 天
    "rate_limit": 60,        # 限流 1 分钟
    "knowledge": 300,        # 知识检索 5 分钟
    "model_config": 1800,    # 模型配置 30 分钟
}
```

## 缓存命中率优化方案

### 1. 分层缓存策略

```
┌─────────────────────────────────────────────────────────────┐
│                    分层缓存架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  L1: 应用层缓存 (内存)                                      │
│  - 热点数据：用户信息、模型配置                              │
│  - 命中时间：< 1ms                                          │
│  - 过期时间：1-5 分钟                                       │
│                                                             │
│  L2: Redis 缓存 (集中式)                                    │
│  - 共享数据：Token、限流、会话                               │
│  - 命中时间：< 5ms                                          │
│  - 过期时间：5-60 分钟                                      │
│                                                             │
│  L3: 数据库 (持久化)                                        │
│  - 全量数据                                                 │
│  - 查询时间：10-100ms                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. 热点数据缓存

```python
# app/services/cache.py

class CacheService:
    def __init__(self):
        # 本地内存缓存（L1）
        self._local_cache = {}
        self._local_cache_ttl = {}

        # Redis 缓存（L2）
        self.redis = redis.Redis(...)

    async def get(self, key: str, use_local: bool = True) -> Optional[Any]:
        """获取缓存（优先 L1）"""
        # 1. 尝试 L1 缓存
        if use_local and self._is_local_valid(key):
            return self._local_cache.get(key)

        # 2. 尝试 Redis 缓存
        value = await self._get_redis(key)

        # 3. 回写到 L1 缓存
        if use_local and value is not None:
            self._local_cache[key] = value
            self._local_cache_ttl[key] = time.time() + 60  # L1 默认 1 分钟

        return value

    def _is_local_valid(self, key: str) -> bool:
        """检查 L1 缓存是否有效"""
        if key not in self._local_cache:
            return False
        expire_at = self._local_cache_ttl.get(key, 0)
        return time.time() < expire_at
```

### 3. 缓存预热

```python
# app/services/cache_warmup.py

class CacheWarmupService:
    """缓存预热服务"""

    async def warmup_models(self):
        """预热模型配置"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(Model).where(Model.is_active == True)
            )
            models = result.scalars().all()

            for model in models:
                key = f"ai:model:config:{model.id}"
                await cache_service.set(
                    key,
                    {
                        "name": model.name,
                        "provider": model.provider,
                        "config": model.config,
                    },
                    expire=3600  # 1 小时
                )

    async def warmup_applications(self):
        """预热应用配置"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(Application).where(Application.is_active == True)
            )
            apps = result.scalars().all()

            for app in apps:
                key = f"ai:app:{app.id}"
                await cache_service.set(
                    key,
                    {
                        "name": app.name,
                        "owner_id": app.owner_id,
                        "rate_limit": app.rate_limit,
                    },
                    expire=1800  # 30 分钟
                )

    async def warmup_users(self, user_ids: List[int]):
        """预热用户信息"""
        for user_id in user_ids:
            user = await get_user_by_id(user_id)
            if user:
                await cache_service.set_user_info(
                    user_id,
                    {
                        "username": user.username,
                        "email": user.email,
                        "role": user.role,
                    }
                )

# 启动时执行缓存预热
async def warmup_cache_on_startup():
    """应用启动时预热缓存"""
    warmup_service = CacheWarmupService()
    await warmup_service.warmup_models()
    await warmup_service.warmup_applications()
```

### 4. 缓存穿透保护

```python
class CacheService:
    async def get_with_protection(
        self,
        key: str,
        fallback_func: Callable,
        ttl: int = 300,
    ) -> Any:
        """
        带穿透保护的缓存获取

        Args:
            key: 缓存键
            fallback_func: 缓存未命中时的回退函数
            ttl: 过期时间

        Returns:
            缓存值或回退函数结果
        """
        # 1. 尝试获取缓存
        cached = await self.get(key)
        if cached is not None:
            return cached

        # 2. 检查是否是"空值缓存"（用于防穿透）
        if await self.exists(f"{key}:null"):
            return None

        # 3. 执行回退函数
        try:
            result = await fallback_func()
        except Exception as e:
            logger.error(f"Fallback function error: {e}")
            return None

        # 4. 存储结果
        if result is not None:
            await self.set(key, result, ttl)
        else:
            # 空值也缓存，防止穿透
            await self.set(f"{key}:null", True, expire=60)

        return result
```

### 5. 缓存雪崩保护

```python
class CacheService:
    async def set_with_jitter(
        self,
        key: str,
        value: Any,
        base_ttl: int,
        jitter_ratio: float = 0.2,
    ) -> bool:
        """
        带随机抖动的缓存设置（防雪崩）

        Args:
            key: 缓存键
            value: 缓存值
            base_ttl: 基础过期时间
            jitter_ratio: 抖动比例 (0-1)

        Returns:
            是否成功
        """
        # 添加随机抖动
        jitter = base_ttl * jitter_ratio * (random.random() - 0.5)
        actual_ttl = int(base_ttl + jitter)

        return await self.set(key, value, expire=actual_ttl)
```

### 6. 缓存击穿保护（互斥锁）

```python
class CacheService:
    async def get_with_lock(
        self,
        key: str,
        fallback_func: Callable,
        ttl: int = 300,
        lock_timeout: int = 10,
    ) -> Any:
        """
        带互斥锁的缓存获取（防击穿）

        Args:
            key: 缓存键
            fallback_func: 回退函数
            ttl: 缓存过期时间
            lock_timeout: 锁超时时间

        Returns:
            缓存值
        """
        # 1. 尝试获取缓存
        cached = await self.get(key)
        if cached is not None:
            return cached

        # 2. 尝试获取分布式锁
        lock_key = f"{key}:lock"
        lock_acquired = await self.redis.set(
            lock_key,
            "1",
            nx=True,  # 仅当键不存在时设置
            ex=lock_timeout,
        )

        if lock_acquired:
            try:
                # 3. 双重检查（避免重复计算）
                cached = await self.get(key)
                if cached is not None:
                    return cached

                # 4. 执行回退函数
                result = await fallback_func()
                await self.set(key, result, ttl)
                return result
            finally:
                # 5. 释放锁
                await self.redis.delete(lock_key)
        else:
            # 6. 等待锁释放后重试
            await asyncio.sleep(0.1)
            return await self.get_with_lock(
                key, fallback_func, ttl, lock_timeout
            )
```

## 推荐的缓存策略

### 用户信息缓存

```python
@cache_result("user:info", ttl=3600)
async def get_user_info(user_id: int) -> Optional[dict]:
    """获取用户信息（带缓存）"""
    user = await db.get(User, user_id)
    if user:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
    return None
```

### 模型配置缓存

```python
async def get_model_config(model_id: int) -> Optional[dict]:
    """获取模型配置（带缓存）"""
    cache_key = f"ai:model:config:{model_id}"

    config = await cache_service.get(cache_key)
    if config:
        return config

    # 从数据库查询
    model = await db.get(Model, model_id)
    if model:
        config = {
            "name": model.name,
            "provider": model.provider,
            "config": model.config,
        }
        await cache_service.set_with_jitter(
            cache_key, config, base_ttl=3600, jitter_ratio=0.3
        )
        return config

    return None
```

### Token 验证缓存

```python
async def verify_token(token: str) -> Optional[dict]:
    """验证 Token（带缓存）"""
    cache_key = f"ai:token:{token}"

    # 尝试从缓存获取
    token_data = await cache_service.get(cache_key)
    if token_data:
        return token_data

    # 从数据库验证
    token_obj = await db.execute(
        select(BlacklistToken).where(
            BlacklistToken.token == token,
            BlacklistToken.expires_at > datetime.utcnow(),
        )
    )
    token_obj = token_obj.scalar_one_or_none()

    if token_obj:
        token_data = {
            "user_id": token_obj.user_id,
            "expires_at": str(token_obj.expires_at),
        }
        # Token 剩余有效期
        remaining = (token_obj.expires_at - datetime.utcnow()).total_seconds()
        await cache_service.set(cache_key, token_data, expire=int(remaining))
        return token_data

    return None
```

## 缓存监控

```python
# app/services/cache_monitor.py

class CacheMonitor:
    """缓存监控服务"""

    def __init__(self):
        self.redis = cache_service.redis
        self.hits = 0
        self.misses = 0

    async def get_stats(self) -> dict:
        """获取缓存统计"""
        info = await self.redis.info("stats")

        return {
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": self._calculate_hit_rate(info),
            "memory_used": await self._get_memory_usage(),
            "keys_count": await self._get_keys_count(),
        }

    def _calculate_hit_rate(self, info: dict) -> float:
        """计算命中率"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 0
        return hits / total * 100

    async def _get_memory_usage(self) -> int:
        """获取内存使用"""
        info = await self.redis.info("memory")
        return info.get("used_memory", 0)

    async def _get_keys_count(self) -> int:
        """获取键数量"""
        db_size = await self.redis.dbsize()
        return db_size

    async def get_hot_keys(self, limit: int = 10) -> List[str]:
        """获取热键（通过监控命令）"""
        # 使用 Redis 4.0+ 的--hotkeys 选项
        # 或使用 MONITOR 命令分析（生产环境慎用）
        pass

cache_monitor = CacheMonitor()
```

## 缓存优化检查清单

- [ ] 热点数据有缓存（用户、模型、配置）
- [ ] 缓存有过期时间
- [ ] 缓存有过期抖动（防雪崩）
- [ ] 空值有缓存保护（防穿透）
- [ ] 互斥锁保护（防击穿）
- [ ] 缓存预热机制
- [ ] 缓存监控和统计
- [ ] 缓存失败不阻断业务
- [ ] 缓存键命名规范
- [ ] 定期清理过期缓存

## 目标指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 缓存命中率 | - | > 80% |
| 平均响应时间 | - | < 10ms |
| 数据库查询减少 | - | > 60% |
