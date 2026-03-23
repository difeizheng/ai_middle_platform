"""
API 网关中间件
认证鉴权、限流熔断、请求审计
"""
import time
import uuid
from functools import wraps
from typing import Optional, Callable, Dict, Any

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.logger import get_logger
from ..core.config import settings
from ..models.app import APIKey
from ..models.api_log import APILog

logger = get_logger(__name__)

# HTTP Bearer 认证
security = HTTPBearer(auto_error=False)


class RateLimiter:
    """
    限流器（基于 Token Bucket 算法）
    """

    def __init__(self):
        # 存储每个 API Key 的令牌桶状态
        self.buckets: Dict[str, Dict[str, Any]] = {}

    def get_bucket(self, key: str) -> Dict[str, Any]:
        """获取或创建令牌桶"""
        if key not in self.buckets:
            self.buckets[key] = {
                "tokens": settings.RATE_LIMIT_REQUESTS,
                "last_update": time.time(),
            }
        return self.buckets[key]

    def consume(self, key: str, tokens: int = 1) -> bool:
        """
        消费令牌

        Args:
            key: API Key
            tokens: 消耗的令牌数

        Returns:
            是否成功消费
        """
        bucket = self.get_bucket(key)
        now = time.time()

        # 补充令牌
        elapsed = now - bucket["last_update"]
        refill = int(elapsed / settings.RATE_LIMIT_WINDOW * settings.RATE_LIMIT_REQUESTS)
        bucket["tokens"] = min(
            settings.RATE_LIMIT_REQUESTS,
            bucket["tokens"] + refill
        )
        bucket["last_update"] = now

        # 消费令牌
        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return True
        return False


# 全局限流器
rate_limiter = RateLimiter()


async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = None,
) -> Optional[APIKey]:
    """
    验证 API Key

    Args:
        request: 请求对象
        credentials: Bearer 凭证

    Returns:
        APIKey 或 None
    """
    # 尝试从 Header 获取 API Key
    api_key = request.headers.get("X-API-Key")

    if not api_key and credentials:
        api_key = credentials.credentials

    if not api_key:
        return None

    # 验证 API Key
    # 实际实现应该查询数据库
    # 这里简化处理
    if api_key.startswith("sk_"):
        return APIKey(
            id=1,
            key=api_key,
            key_prefix=api_key[:10],
            is_active=True,
        )

    return None


async def audit_log_middleware(
    request: Request,
    call_next: Callable,
) -> Response:
    """
    审计日志中间件
    """
    import hashlib
    from datetime import datetime

    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # 执行请求
    try:
        response = await call_next(request)
    except Exception as e:
        # 记录错误日志
        logger.error(f"请求处理失败：{e}", exc_info=True)
        raise

    # 计算延迟
    latency_ms = (time.time() - start_time) * 1000

    # 异步记录日志（不阻塞响应）
    # 实际实现应该使用消息队列或后台任务
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Latency: {latency_ms:.2f}ms"
    )

    # 添加响应头
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{latency_ms:.2f}"

    return response


def rate_limit(max_requests: int = None, window: int = None):
    """
    限流装饰器

    Args:
        max_requests: 最大请求数
        window: 时间窗口（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取 API Key
            request = kwargs.get("request")
            if request:
                api_key = request.headers.get("X-API-Key", "anonymous")
                max_req = max_requests or settings.RATE_LIMIT_REQUESTS
                win = window or settings.RATE_LIMIT_WINDOW

                if not rate_limiter.consume(api_key):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"请求过于频繁，限制为 {max_req} 次/{win}秒",
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_permission(
    request: Request,
    required_permission: str,
) -> bool:
    """
    权限检查

    Args:
        request: 请求对象
        required_permission: 所需权限

    Returns:
        是否有权限
    """
    # 获取 API Key
    api_key = await verify_api_key(request)

    if not api_key:
        return False

    # 检查权限
    # 实际实现应该查询数据库
    permissions = api_key.permissions or []

    if required_permission in permissions or api_key.is_active:
        return True

    return False


class CircuitBreaker:
    """
    熔断器
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        调用函数（带熔断保护）
        """
        if self.state == "open":
            # 检查是否可以尝试恢复
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="服务暂时不可用，请稍后重试",
                )

        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = "open"
                logger.error(f"熔断器打开：{self.failure_threshold} 次失败")

            raise


# 全局熔断器实例
circuit_breaker = CircuitBreaker()
