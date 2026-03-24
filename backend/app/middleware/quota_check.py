"""
配额检查中间件
在 API 调用时自动检查和更新配额
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, List, Callable
import logging

from app.core.database import get_db_session
from app.services.quota import QuotaService
from app.models.user import User
from app.auth.dependencies import get_current_user_from_request

logger = logging.getLogger(__name__)


# 需要配额检查的端点映射
# 格式：{端点路径：资源类型}
QUOTA_CHECK_ENDPOINTS = {
    "/api/v1/inference/chat/completions": "model_call",
    "/api/v1/inference/embeddings": "model_call",
    "/api/v1/inference/generate": "model_call",
    "/api/v1/knowledge/search": "knowledge_base",
    "/api/v1/agents/execute": "agent",
    "/api/v1/skills/skills/": "skill",  # 前缀匹配
}


class QuotaCheckMiddleware(BaseHTTPMiddleware):
    """配额检查中间件"""

    def __init__(
        self,
        app,
        enabled: bool = True,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.enabled = enabled
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth",
            "/api/v1/quota",  # 配额管理 API 自身不检查
        ]

    async def dispatch(self, request: Request, call_next):
        # 如果中间件未启用，直接跳过
        if not self.enabled:
            return await call_next(request)

        # 检查是否需要跳过
        if self._should_skip(request):
            return await call_next(request)

        # 获取端点对应的资源类型
        resource_type = self._get_resource_type(request.url.path)
        if not resource_type:
            return await call_next(request)

        # 获取数据库会话
        db = next(get_db_session())

        try:
            # 获取当前用户
            user = await self._get_current_user(request, db)
            if not user:
                return await call_next(request)

            # 创建配额服务
            quota_service = QuotaService(db)

            # 预检查配额
            check_result = await quota_service.check_quota(
                scope_type="user",
                scope_id=user.id,
                resource_type=resource_type,
                requested_amount=1,
            )

            if not check_result["allowed"]:
                # 配额不足，返回 429 错误
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": "quota_exceeded",
                        "message": check_result.get("reason", "配额已用尽"),
                        "quota_name": check_result.get("quota_name"),
                        "limit": check_result.get("limit"),
                        "used": check_result.get("used"),
                        "remaining": check_result.get("remaining"),
                    },
                    headers={
                        "X-Quota-Limit": str(check_result.get("limit", 0)),
                        "X-Quota-Used": str(check_result.get("used", 0)),
                        "X-Quota-Remaining": str(check_result.get("remaining", 0)),
                    },
                )

            # 执行请求
            response = await call_next(request)

            # 后更新配额使用量
            if response.status_code < 400:  # 仅成功请求更新配额
                await quota_service.update_quota_usage(
                    scope_type="user",
                    scope_id=user.id,
                    resource_type=resource_type,
                    used_amount=1,
                )

            return response

        except HTTPException as e:
            logger.warning(f"Quota check HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Quota check error: {e}", exc_info=True)
            # 配额检查失败不阻断请求，仅记录日志
            return await call_next(request)
        finally:
            await db.close()

    def _should_skip(self, request: Request) -> bool:
        """检查是否应该跳过配额检查"""
        path = request.url.path
        method = request.method

        # GET 请求通常不需要配额检查（除了查询类）
        if method == "GET" and not path.endswith("/search"):
            return True

        # 检查排除路径
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True

        return False

    def _get_resource_type(self, path: str) -> Optional[str]:
        """根据路径获取资源类型"""
        # 精确匹配
        if path in QUOTA_CHECK_ENDPOINTS:
            return QUOTA_CHECK_ENDPOINTS[path]

        # 前缀匹配
        for endpoint_prefix, resource_type in QUOTA_CHECK_ENDPOINTS.items():
            if endpoint_prefix.endswith("/"):
                # 前缀匹配
                if path.startswith(endpoint_prefix):
                    return resource_type

        return None

    async def _get_current_user(
        self,
        request: Request,
        db: AsyncSession,
    ) -> Optional[User]:
        """获取当前用户"""
        try:
            # 从请求头获取 Authorization
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            token = auth_header.split(" ")[1]

            # 使用依赖函数获取用户
            user = await get_current_user_from_request(request, db)
            return user
        except Exception as e:
            logger.warning(f"Failed to get current user: {e}")
            return None


# 中间件工厂
def setup_quota_middleware(app, enabled: bool = True):
    """设置配额检查中间件"""
    app.add_middleware(QuotaCheckMiddleware, enabled=enabled)
    logger.info(f"Quota check middleware {'enabled' if enabled else 'disabled'}")


# 装饰器方式检查配额
def check_quota(resource_type: str, amount: int = 1):
    """
    配额检查装饰器
    用于在特定 API 端点上检查配额
    """
    from functools import wraps

    async def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取 db 和 current_user
            db = kwargs.get("db")
            current_user = kwargs.get("current_user")

            if not db or not current_user:
                # 如果缺少必要参数，跳过检查
                return await func(*args, **kwargs)

            quota_service = QuotaService(db)

            # 检查配额
            result = await quota_service.check_quota(
                scope_type="user",
                scope_id=current_user.id,
                resource_type=resource_type,
                requested_amount=amount,
            )

            if not result["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=result.get("reason", "配额已用尽"),
                    headers={
                        "X-Quota-Limit": str(result.get("limit", 0)),
                        "X-Quota-Used": str(result.get("used", 0)),
                        "X-Quota-Remaining": str(result.get("remaining", 0)),
                    },
                )

            # 执行函数
            response = await func(*args, **kwargs)

            # 更新配额使用量
            await quota_service.update_quota_usage(
                scope_type="user",
                scope_id=current_user.id,
                resource_type=resource_type,
                used_amount=amount,
            )

            return response

        return wrapper

    return decorator
