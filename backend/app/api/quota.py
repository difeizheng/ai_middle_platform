"""
配额管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.quota import Quota, QuotaUsage
from app.services.quota import QuotaService
from app.utils.permissions import verify_admin_user  # 管理员权限检查

router = APIRouter()


# ========== 配额定义管理 ==========

@router.get("/quotas")
async def list_quotas(
    scope_type: Optional[str] = Query(None, description="配额层级：user/app/api_key"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    quota_type: Optional[str] = Query(None, description="配额类型：qps/daily_calls/token_usage"),
    is_active: Optional[bool] = Query(True, description="是否生效"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取配额列表"""
    service = QuotaService(db)
    quotas = await service.list_quotas(
        scope_type=scope_type,
        scope_id=scope_id,
        quota_type=quota_type,
        is_active=is_active,
    )

    return {
        "success": True,
        "data": [quota.to_dict() for quota in quotas],
    }


@router.get("/quotas/{quota_id}")
async def get_quota(
    quota_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取配额详情"""
    service = QuotaService(db)
    quota = await service.get_quota(quota_id)

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在",
        )

    return {
        "success": True,
        "data": quota.to_dict(),
    }


@router.post("/quotas")
async def create_quota(
    name: str = Body(..., description="配额名称"),
    quota_type: str = Body(..., description="配额类型：qps/daily_calls/token_usage/concurrent"),
    resource_type: str = Body(..., description="资源类型：model_call/knowledge_base/agent/skill/all"),
    limit_value: int = Body(..., gt=0, description="限制值"),
    scope_type: str = Body(..., description="配额层级：user/app/api_key"),
    scope_id: str = Body(..., description="层级 ID（用户 ID/应用 ID/APIKey ID）"),
    description: Optional[str] = Body(None, description="配额描述"),
    unit: Optional[str] = Body(None, description="单位：calls/tokens/second"),
    period_type: str = Body("daily", description="周期类型：hourly/daily/weekly/monthly/none"),
    reset_time: Optional[str] = Body(None, description="重置时间，如 00:00"),
    parent_quota_id: Optional[str] = Body(None, description="父配额 ID"),
    over_limit_action: str = Body("reject", description="超额处理：reject/allow/log"),
    over_limit_rate: float = Body(1, description="超额费率系数"),
    extra_config: Optional[Dict[str, Any]] = Body(None, description="额外配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建配额"""
    service = QuotaService(db)

    # 验证 scope_id 是否有效（如果是 user 层级）
    if scope_type == "user":
        from sqlalchemy import select
        from app.models.user import User as UserModel
        result = await db.execute(select(UserModel).where(UserModel.id == scope_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"用户不存在：{scope_id}",
            )

    quota = await service.create_quota(
        name=name,
        quota_type=quota_type,
        resource_type=resource_type,
        limit_value=limit_value,
        scope_type=scope_type,
        scope_id=scope_id,
        description=description,
        unit=unit,
        period_type=period_type,
        reset_time=reset_time,
        parent_quota_id=parent_quota_id,
        over_limit_action=over_limit_action,
        over_limit_rate=over_limit_rate,
        extra_config=extra_config or {},
    )

    return {
        "success": True,
        "data": quota.to_dict(),
    }


@router.put("/quotas/{quota_id}")
async def update_quota(
    quota_id: str,
    name: Optional[str] = Body(None, description="配额名称"),
    description: Optional[str] = Body(None, description="配额描述"),
    limit_value: Optional[int] = Body(None, description="限制值"),
    period_type: Optional[str] = Body(None, description="周期类型"),
    reset_time: Optional[str] = Body(None, description="重置时间"),
    over_limit_action: Optional[str] = Body(None, description="超额处理"),
    over_limit_rate: Optional[float] = Body(None, description="超额费率系数"),
    is_active: Optional[bool] = Body(None, description="是否生效"),
    extra_config: Optional[Dict[str, Any]] = Body(None, description="额外配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新配额"""
    service = QuotaService(db)

    update_data = {
        k: v for k, v in {
            "name": name,
            "description": description,
            "limit_value": limit_value,
            "period_type": period_type,
            "reset_time": reset_time,
            "over_limit_action": over_limit_action,
            "over_limit_rate": over_limit_rate,
            "is_active": is_active,
            "extra_config": extra_config,
        }.items() if v is not None
    }

    quota = await service.update_quota(quota_id, **update_data)

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在",
        )

    return {
        "success": True,
        "data": quota.to_dict(),
    }


@router.delete("/quotas/{quota_id}")
async def delete_quota(
    quota_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除配额"""
    service = QuotaService(db)
    success = await service.delete_quota(quota_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在",
        )

    return {
        "success": True,
        "message": "配额已删除",
    }


# ========== 配额检查 ==========

@router.post("/quotas/check")
async def check_quota(
    scope_type: str = Body(..., description="配额层级：user/app/api_key"),
    scope_id: str = Body(..., description="层级 ID"),
    resource_type: str = Body(..., description="资源类型"),
    requested_amount: int = Body(1, description="请求数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查配额是否充足"""
    service = QuotaService(db)
    result = await service.check_quota(
        scope_type=scope_type,
        scope_id=scope_id,
        resource_type=resource_type,
        requested_amount=requested_amount,
    )

    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=result["reason"],
            headers={
                "X-Quota-Limit": str(result.get("limit", 0)),
                "X-Quota-Used": str(result.get("used", 0)),
                "X-Quota-Remaining": str(result.get("remaining", 0)),
            },
        )

    return {
        "success": True,
        "data": result,
    }


@router.post("/quotas/usage/update")
async def update_quota_usage(
    scope_type: str = Body(..., description="配额层级"),
    scope_id: str = Body(..., description="层级 ID"),
    resource_type: str = Body(..., description="资源类型"),
    used_amount: int = Body(..., gt=0, description="使用数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新配额使用量"""
    service = QuotaService(db)
    result = await service.update_quota_usage(
        scope_type=scope_type,
        scope_id=scope_id,
        resource_type=resource_type,
        used_amount=used_amount,
    )

    return {
        "success": True,
        "data": result,
    }


# ========== 配额使用统计 ==========

@router.get("/quotas/usage")
async def get_quota_usage(
    scope_type: Optional[str] = Query(None, description="配额层级"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前配额使用情况"""
    # 默认查询当前用户的配额使用
    if not scope_id:
        scope_id = current_user.id
        scope_type = "user"

    service = QuotaService(db)
    quotas = await service.list_quotas(
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=True,
    )

    now = datetime.utcnow()
    usage_data = []

    for quota in quotas:
        period_start, period_end = service._calculate_period(
            now, quota.period_type, quota.reset_time
        )

        usage = await service.get_or_create_usage(
            quota_id=quota.id,
            scope_type=scope_type,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
        )

        usage_data.append({
            "quota": quota.to_dict(),
            "usage": usage.to_dict(),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
        })

    return {
        "success": True,
        "data": usage_data,
    }


@router.get("/quotas/usage/stats")
async def get_usage_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    scope_type: Optional[str] = Query(None, description="配额层级"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取配额使用统计"""
    if not scope_id:
        scope_id = current_user.id
        scope_type = "user"

    service = QuotaService(db)
    stats = await service.get_usage_stats(
        scope_type=scope_type,
        scope_id=scope_id,
        days=days,
    )

    return {
        "success": True,
        "data": stats,
    }


# ========== 配额重置 ==========

@router.post("/quotas/{quota_id}/reset")
async def reset_quota(
    quota_id: str,
    scope_id: str = Body(..., description="层级 ID"),
    scope_type: str = Body("user", description="配额层级"),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
    db: AsyncSession = Depends(get_db),
):
    """重置配额使用量（管理员操作）"""
    service = QuotaService(db)

    quota = await service.get_quota(quota_id)
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额不存在",
        )

    # 获取当前使用记录并重置
    now = datetime.utcnow()
    period_start, period_end = service._calculate_period(
        now, quota.period_type, quota.reset_time
    )

    usage = await service.get_or_create_usage(
        quota_id=quota_id,
        scope_type=scope_type,
        scope_id=scope_id,
        period_start=period_start,
        period_end=period_end,
    )

    usage.used_value = 0
    usage.remaining_value = quota.limit_value
    usage.exceeded_value = 0

    await db.commit()

    return {
        "success": True,
        "message": "配额已重置",
        "data": {
            "quota": quota.to_dict(),
            "usage": usage.to_dict(),
        },
    }
