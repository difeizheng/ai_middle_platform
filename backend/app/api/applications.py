"""
应用管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
import hashlib

from ..core.database import get_db
from ..models.user import User
from ..models.app import Application, APIKey
from ..auth.dependencies import get_current_user

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

    # 自动生成 API Key
    api_key_str = f"sk_{uuid.uuid4().hex}"
    api_key_hash = hashlib.sha256(api_key_str.encode()).hexdigest()

    api_key = APIKey(
        app_id=app.id,
        key=api_key_hash,
        key_prefix=api_key_str[:10],
    )

    db.add(api_key)
    await db.commit()

    return {
        "id": app.id,
        "name": app.name,
        "api_key": api_key_str,  # 只在创建时返回一次
        "message": "应用创建成功",
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
    result = await db.execute(
        select(APIKey).where(
            APIKey.app_id == app_id,
            APIKey.is_active == True,
        )
    )
    keys = result.scalars().all()

    return {
        "total": len(keys),
        "api_keys": [
            {
                "id": k.id,
                "key_prefix": k.key_prefix,
                "is_active": k.is_active,
                "created_at": str(k.created_at),
                "last_used_at": str(k.last_used_at) if k.last_used_at else None,
            }
            for k in keys
        ],
    }
