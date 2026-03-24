"""
使用量统计 API 路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.services.usage_stats import UsageStatsService

router = APIRouter()


@router.get("/usage/realtime")
async def get_realtime_usage(
    scope_type: Optional[str] = Query("user", description="层级类型"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取实时使用量"""
    if not scope_id:
        scope_id = current_user.id

    service = UsageStatsService(db)
    result = await service.get_realtime_usage(
        scope_type=scope_type,
        scope_id=scope_id,
    )

    return {"success": True, "data": result}


@router.get("/usage/trend")
async def get_usage_trend(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    granularity: str = Query("day", description="粒度：hour/day/week/month"),
    scope_type: Optional[str] = Query("user", description="层级类型"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取使用趋势"""
    if not scope_id:
        scope_id = current_user.id

    service = UsageStatsService(db)
    result = await service.get_usage_trend(
        scope_type=scope_type,
        scope_id=scope_id,
        days=days,
        granularity=granularity,
    )

    return {"success": True, "data": result}


@router.get("/usage/breakdown")
async def get_usage_breakdown(
    dimension: str = Query("model", description="分析维度：model/resource_type/api_endpoint"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    scope_type: Optional[str] = Query("user", description="层级类型"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按维度分析使用量"""
    if not scope_id:
        scope_id = current_user.id

    service = UsageStatsService(db)
    result = await service.get_usage_by_dimension(
        scope_type=scope_type,
        scope_id=scope_id,
        dimension=dimension,
        days=days,
    )

    return {"success": True, "data": result}


@router.get("/usage/cost-analysis")
async def get_cost_analysis(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    scope_type: Optional[str] = Query("user", description="层级类型"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """成本分析"""
    if not scope_id:
        scope_id = current_user.id

    service = UsageStatsService(db)
    result = await service.get_cost_analysis(
        scope_type=scope_type,
        scope_id=scope_id,
        days=days,
    )

    return {"success": True, "data": result}


@router.get("/usage/prediction")
async def get_usage_prediction(
    predict_days: int = Query(7, ge=1, le=30, description="预测天数"),
    scope_type: Optional[str] = Query("user", description="层级类型"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """使用量预测"""
    if not scope_id:
        scope_id = current_user.id

    service = UsageStatsService(db)
    result = await service.get_prediction(
        scope_type=scope_type,
        scope_id=scope_id,
        predict_days=predict_days,
    )

    return {"success": True, "data": result}


@router.get("/usage/top-resources")
async def get_top_resources(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    scope_type: Optional[str] = Query("user", description="层级类型"),
    scope_id: Optional[str] = Query(None, description="层级 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 TOP 资源使用排行"""
    if not scope_id:
        scope_id = current_user.id

    service = UsageStatsService(db)
    result = await service.get_top_resources(
        scope_type=scope_type,
        scope_id=scope_id,
        days=days,
        limit=limit,
    )

    return {"success": True, "data": result}
