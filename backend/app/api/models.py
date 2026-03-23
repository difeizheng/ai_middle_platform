"""
模型管理路由 - 模型工厂核心 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from ..core.database import get_db
from ..models.user import User
from ..models.model import Model, ModelRegistry
from ..auth.dependencies import get_current_user

router = APIRouter()


@router.get("")
async def list_models(
    model_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取模型列表
    """
    query = select(Model)
    if model_type:
        query = query.where(Model.model_type == model_type)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    models = result.scalars().all()

    return {
        "total": len(models),
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "display_name": m.display_name,
                "model_type": m.model_type,
                "provider": m.provider,
                "is_active": m.is_active,
                "is_default": m.is_default,
                "avg_latency_ms": m.avg_latency_ms,
            }
            for m in models
        ],
    }


@router.post("")
async def create_model(
    name: str,
    model_type: str,
    display_name: str = None,
    provider: str = "openai",
    base_url: str = None,
    api_key: str = None,
    max_context_length: int = 4096,
    max_tokens: int = 2048,
    config: dict = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    注册新模型
    """
    # 检查模型是否已存在
    result = await db.execute(select(Model).where(Model.name == name))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="模型已存在",
        )

    # 创建模型
    model = Model(
        name=name,
        display_name=display_name or name,
        model_type=model_type,
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        max_context_length=max_context_length,
        max_tokens=max_tokens,
        config=config or {},
    )

    db.add(model)
    await db.commit()
    await db.refresh(model)

    return {
        "id": model.id,
        "name": model.name,
        "message": "模型注册成功",
    }


@router.get("/{model_id}")
async def get_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取模型详情
    """
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    return {
        "id": model.id,
        "name": model.name,
        "display_name": model.display_name,
        "model_type": model.model_type,
        "provider": model.provider,
        "base_url": model.base_url,
        "max_context_length": model.max_context_length,
        "max_tokens": model.max_tokens,
        "supports_function_call": model.supports_function_call,
        "is_active": model.is_active,
        "is_default": model.is_default,
        "avg_latency_ms": model.avg_latency_ms,
        "config": model.config,
    }


@router.put("/{model_id}")
async def update_model(
    model_id: int,
    display_name: str = None,
    base_url: str = None,
    api_key: str = None,
    max_context_length: int = None,
    max_tokens: int = None,
    is_active: bool = None,
    is_default: bool = None,
    config: dict = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新模型配置
    """
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    # 更新字段
    if display_name is not None:
        model.display_name = display_name
    if base_url is not None:
        model.base_url = base_url
    if api_key is not None:
        model.api_key = api_key
    if max_context_length is not None:
        model.max_context_length = max_context_length
    if max_tokens is not None:
        model.max_tokens = max_tokens
    if is_active is not None:
        model.is_active = is_active
    if is_default is not None:
        model.is_default = is_default
    if config is not None:
        model.config = config

    await db.commit()
    await db.refresh(model)

    return {"message": "模型更新成功"}


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除模型
    """
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在",
        )

    await db.delete(model)
    await db.commit()

    return {"message": "模型删除成功"}
