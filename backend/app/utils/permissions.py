"""
权限验证工具
"""
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from ..core.database import get_db
from ..models.user import User
from ..auth.jwt import get_current_user


security = HTTPBearer()


class PermissionDenied(Exception):
    """权限拒绝异常"""
    pass


def verify_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    验证用户是否为管理员

    Args:
        current_user: 当前登录用户

    Returns:
        User: 管理员用户对象

    Raises:
        HTTPException: 非管理员用户
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：需要管理员权限",
        )
    return current_user


def verify_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    验证用户是否激活

    Args:
        current_user: 当前登录用户

    Returns:
        User: 激活用户对象

    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )
    return current_user


def require_permission(permission: str):
    """
    权限检查装饰器

    Args:
        permission: 权限标识符

    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 获取 current_user
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证",
                )

            # 检查用户是否有权限
            if not current_user.is_superuser:
                # 检查用户权限列表
                user_permissions = current_user.permissions or []
                if permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"权限不足：需要 {permission} 权限",
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 依赖注入
require_admin = Depends(verify_admin_user)
require_active = Depends(verify_active_user)


class PermissionChecker:
    """权限检查器类"""

    def __init__(self, required_permissions: list[str]):
        """
        初始化权限检查器

        Args:
            required_permissions: 需要的权限列表
        """
        self.required_permissions = required_permissions

    def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> bool:
        """
        检查权限

        Args:
            current_user: 当前用户
            db: 数据库会话

        Returns:
            bool: 是否有权限
        """
        # 管理员拥有所有权限
        if current_user.is_superuser:
            return True

        # 检查用户权限
        user_permissions = current_user.permissions or []
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足：需要 {permission} 权限",
                )

        return True


def check_resource_owner(
    resource_user_id: str,
    current_user: User = Depends(get_current_user),
) -> bool:
    """
    检查资源所有权

    Args:
        resource_user_id: 资源所属用户 ID
        current_user: 当前用户

    Returns:
        bool: 是否有所有权
    """
    # 管理员可以访问所有资源
    if current_user.is_superuser:
        return True

    # 检查是否为资源所有者
    if current_user.id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该资源",
        )

    return True
