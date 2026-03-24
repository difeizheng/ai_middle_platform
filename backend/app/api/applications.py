"""
应用管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from ..core.database import get_db
from ..core.exceptions import NotFoundError, ConflictError
from ..models.user import User
from ..models.app import Application, APIKey
from ..auth.dependencies import get_current_user
from ..services.api_key_manager import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
    rotate_api_key,
    delete_api_key,
)

router = APIRouter()


@router.get("")
async def list_applications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取应用列表
    """
    result = await db.execute(
        select(Application)
        .where(Application.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    apps = result.scalars().all()

    return {
        "total": len(apps),
        "applications": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "app_type": a.app_type,
                "is_active": a.is_active,
                "total_calls": a.total_calls,
            }
            for a in apps
        ],
    }


@router.post("")
async def create_application(
    name: str,
    description: str = None,
    app_type: str = "web",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建应用

    返回格式：
    {
        "id": int,
        "name": str,
        "api_key": str,  # 完整 API Key（仅返回一次）
        "api_secret": str,  # API Secret（仅返回一次）
        "key_prefix": str,
        "message": str
    }
    """
    app = Application(
        name=name,
        description=description,
        owner_id=current_user.id,
        app_type=app_type,
    )

    db.add(app)
    await db.commit()
    await db.refresh(app)

    # 使用加密服务自动生成 API Key 和 Secret
    key_info = await create_api_key(
        db=db,
        app_id=app.id,
        expires_days=None,  # 永不过期
    )

    return {
        "id": app.id,
        "name": app.name,
        "api_key": key_info["api_key"],  # 完整 API Key（仅返回一次）
        "api_secret": key_info["api_secret"],  # API Secret（仅返回一次）
        "key_prefix": key_info["key_prefix"],
        "message": "应用创建成功，请妥善保存 API Key 和 Secret",
    }


@router.get("/{app_id}")
async def get_application(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取应用详情
    """
    result = await db.execute(
        select(Application).where(
            Application.id == app_id,
            Application.owner_id == current_user.id,
        )
    )
    app = result.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="应用不存在",
        )

    return {
        "id": app.id,
        "name": app.name,
        "description": app.description,
        "app_type": app.app_type,
        "is_active": app.is_active,
        "quota_config": app.quota_config,
        "rate_limit": app.rate_limit,
        "total_calls": app.total_calls,
        "total_tokens": app.total_tokens,
    }


@router.get("/{app_id}/keys")
async def list_api_keys(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取应用的 API Key 列表
    """
    # 验证应用归属
    app = await db.get(Application, app_id)
    if not app or app.owner_id != current_user.id:
        raise NotFoundError(resource="应用")

    keys = await list_api_keys(db=db, app_id=app_id)

    return {
        "total": len(keys),
        "api_keys": [
            {
                "id": k.id,
                "key_prefix": k.key_prefix,
                "is_active": k.is_active,
                "is_revoked": k.is_revoked,
                "created_at": str(k.created_at),
                "last_used_at": str(k.last_used_at) if k.last_used_at else None,
                "expires_at": str(k.expires_at) if k.expires_at else None,
            }
            for k in keys
        ],
    }


@router.post("/{app_id}/keys")
async def create_new_api_key(
    app_id: int,
    expires_days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    为应用创建新的 API Key

    返回格式：
    {
        "id": int,
        "api_key": str,  # 完整 API Key（仅返回一次）
        "api_secret": str,  # API Secret（仅返回一次）
        "key_prefix": str,
        "expires_at": datetime,
    }
    """
    # 验证应用归属
    app = await db.get(Application, app_id)
    if not app or app.owner_id != current_user.id:
        raise NotFoundError(resource="应用")

    key_info = await create_api_key(
        db=db,
        app_id=app_id,
        expires_days=expires_days,
    )

    return {
        "id": key_info["id"],
        "api_key": key_info["api_key"],
        "api_secret": key_info["api_secret"],
        "key_prefix": key_info["key_prefix"],
        "expires_at": key_info["expires_at"],
        "message": "API Key 创建成功，请妥善保存",
    }


@router.post("/keys/{key_id}/rotate")
async def rotate_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    轮换 API Key

    轮换后会生成新的 API Key 和 Secret，旧的会立即失效。

    返回格式：
    {
        "id": int,
        "api_key": str,  # 新 API Key（仅返回一次）
        "api_secret": str,  # 新 API Secret（仅返回一次）
        "key_prefix": str,
    }
    """
    # 验证 Key 归属
    key = await db.get(APIKey, key_id)
    if not key:
        raise NotFoundError(resource="API Key")

    app = await db.get(Application, key.app_id)
    if not app or app.owner_id != current_user.id:
        raise NotFoundError(resource="应用")

    key_info = await rotate_api_key(db=db, api_key_id=key_id)

    return {
        "id": key_info["id"],
        "api_key": key_info["api_key"],
        "api_secret": key_info["api_secret"],
        "key_prefix": key_info["key_prefix"],
        "message": "API Key 轮换成功，旧 Key 已失效",
    }


@router.post("/keys/{key_id}/revoke")
async def revoke_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    吊销 API Key

    吊销后的 Key 无法恢复，如需使用请创建新的 Key。
    """
    # 验证 Key 归属
    key = await db.get(APIKey, key_id)
    if not key:
        raise NotFoundError(resource="API Key")

    app = await db.get(Application, key.app_id)
    if not app or app.owner_id != current_user.id:
        raise NotFoundError(resource="应用")

    await revoke_api_key(db=db, api_key_id=key_id)

    return {"message": "API Key 已吊销"}


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除 API Key

    删除操作不可恢复，请谨慎使用。
    """
    # 验证 Key 归属
    key = await db.get(APIKey, key_id)
    if not key:
        raise NotFoundError(resource="API Key")

    app = await db.get(Application, key.app_id)
    if not app or app.owner_id != current_user.id:
        raise NotFoundError(resource="应用")

    await delete_api_key(db=db, api_key_id=key_id)

    return {"message": "API Key 已删除"}
