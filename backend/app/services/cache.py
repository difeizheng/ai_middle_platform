"""
Redis 缓存服务
"""
import json
import redis.asyncio as redis
from typing import Any, Optional, List
from functools import wraps
import hashlib
from ..core.config import settings


class CacheService:
    """
    Redis 缓存服务
    """

    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        # 缓存键前缀
        self.prefix = {
            "user": "ai:user:",
            "token": "ai:token:",
            "rate_limit": "ai:rate:",
            "knowledge": "ai:kb:",
            "model": "ai:model:",
            "application": "ai:app:",
        }

        # 缓存过期时间（秒）
        self.ttl = {
            "user_info": 3600,  # 用户信息 1 小时
            "token": 604800,  # Token 7 天
            "rate_limit": 60,  # 限流 1 分钟
            "knowledge": 300,  # 知识检索 5 分钟
            "model_config": 1800,  # 模型配置 30 分钟
        }

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            prefix: 前缀
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键字符串
        """
        key_data = f"{prefix}:" + ":".join(str(a) for a in args)
        if kwargs:
            key_data += ":" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

        # 使用 MD5 哈希避免键过长
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"{self.prefix.get(prefix, prefix)}:{key_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            # 缓存失败不应影响业务
            print(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = None,
    ) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间（秒）

        Returns:
            是否成功
        """
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            if expire:
                await self.redis.setex(key, expire, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置过期时间

        Args:
            key: 缓存键
            seconds: 过期时间（秒）

        Returns:
            是否成功
        """
        try:
            await self.redis.expire(key, seconds)
            return True
        except Exception as e:
            print(f"Cache expire error: {e}")
            return False

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        自增（用于限流等场景）

        Args:
            key: 缓存键
            amount: 增量

        Returns:
            自增后的值
        """
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            print(f"Cache incr error: {e}")
            return None

    async def incrby(self, key: str, amount: int = 1) -> Optional[int]:
        """
        自增（带过期时间）

        Args:
            key: 缓存键
            amount: 增量

        Returns:
            自增后的值
        """
        try:
            pipe = self.redis.pipeline()
            await pipe.incr(key, amount)
            await pipe.expire(key, self.ttl["rate_limit"])
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            print(f"Cache incrby error: {e}")
            return None

    async def close(self):
        """
        关闭 Redis 连接
        """
        await self.redis.close()

    # ========== 便捷方法 ==========

    async def get_user_info(self, user_id: int) -> Optional[dict]:
        """获取用户信息缓存"""
        key = self._make_key("user", "info", user_id)
        return await self.get(key)

    async def set_user_info(self, user_id: int, user_info: dict) -> bool:
        """设置用户信息缓存"""
        key = self._make_key("user", "info", user_id)
        return await self.set(key, user_info, self.ttl["user_info"])

    async def get_token_data(self, token: str) -> Optional[dict]:
        """获取 Token 数据缓存"""
        key = self._make_key("token", token)
        return await self.get(key)

    async def set_token_data(self, token: str, token_data: dict) -> bool:
        """设置 Token 数据缓存"""
        key = self._make_key("token", token)
        return await self.set(key, token_data, self.ttl["token"])

    async def get_knowledge_search(
        self, kb_id: int, query: str, top_k: int
    ) -> Optional[List]:
        """获取知识检索缓存"""
        key = self._make_key("knowledge", "search", kb_id, query, top_k)
        return await self.get(key)

    async def set_knowledge_search(
        self, kb_id: int, query: str, top_k: int, results: List
    ) -> bool:
        """设置知识检索缓存"""
        key = self._make_key("knowledge", "search", kb_id, query, top_k)
        return await self.set(key, results, self.ttl["knowledge"])


# 缓存装饰器
def cache_result(prefix: str, ttl: int = 300):
    """
    缓存结果装饰器

    Args:
        prefix: 缓存前缀
        ttl: 过期时间（秒）

    Returns:
        装饰器函数
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = cache_service

            # 生成缓存键
            cache_key = cache._make_key(prefix, *args, **kwargs)

            # 尝试从缓存获取
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# 全局缓存实例
cache_service = CacheService()
