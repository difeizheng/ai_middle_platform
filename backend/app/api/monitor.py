"""
运营监控 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.monitor import (
    MonitorMetric,
    SystemHealth,
    AlertRule,
    AlertHistory,
    DashboardConfig,
    ServiceDependency,
)
from app.services.metrics import get_metric_collector, get_request_metrics

router = APIRouter()


# ========== 监控指标 ==========

@router.get("/metrics/overview")
async def get_metrics_overview(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取监控指标概览"""
    # 默认查询最近 1 小时
    if not start_time:
        start_time = datetime.now() - timedelta(hours=1)
    if not end_time:
        end_time = datetime.now()

    # 查询指标统计
    query = select(
        MonitorMetric.metric_name,
        func.avg(MonitorMetric.value).label("avg_value"),
        func.max(MonitorMetric.value).label("max_value"),
        func.min(MonitorMetric.value).label("min_value"),
        func.count().label("count"),
    ).where(
        MonitorMetric.timestamp >= start_time,
        MonitorMetric.timestamp <= end_time,
    ).group_by(MonitorMetric.metric_name)

    result = await db.execute(query)
    metrics = result.fetchall()

    return {
        "success": True,
        "data": {
            "metrics": [
                {
                    "name": m.metric_name,
                    "avg": m.avg_value,
                    "max": m.max_value,
                    "min": m.min_value,
                    "count": m.count,
                }
                for m in metrics
            ],
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
        },
    }


@router.get("/metrics/{metric_name}")
async def get_metric_detail(
    metric_name: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取特定指标详情"""
    if not start_time:
        start_time = datetime.now() - timedelta(hours=1)
    if not end_time:
        end_time = datetime.now()

    query = select(MonitorMetric).where(
        MonitorMetric.metric_name == metric_name,
        MonitorMetric.timestamp >= start_time,
        MonitorMetric.timestamp <= end_time,
    ).order_by(MonitorMetric.timestamp)

    result = await db.execute(query)
    metrics = result.scalars().all()

    return {
        "success": True,
        "data": {
            "metric_name": metric_name,
            "values": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "value": m.value,
                    "labels": m.labels,
                }
                for m in metrics
            ],
        },
    }


@router.get("/metrics/realtime")
async def get_realtime_metrics(
    current_user: User = Depends(get_current_user),
):
    """获取实时指标（内存中的最新数据）"""
    collector = get_metric_collector()
    metrics = collector.get_all_metrics()

    return {
        "success": True,
        "data": {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        },
    }


# ========== 系统健康 ==========

@router.get("/health/services")
async def get_service_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取服务健康状态"""
    # 获取最新健康状态
    subquery = (
        select(
            SystemHealth.service_name,
            func.max(SystemHealth.checked_at).label("max_checked_at"),
        )
        .group_by(SystemHealth.service_name)
        .subquery()
    )

    query = select(SystemHealth).join(
        subquery,
        (SystemHealth.service_name == subquery.c.service_name)
        & (SystemHealth.checked_at == subquery.c.max_checked_at),
    )

    result = await db.execute(query)
    health_records = result.scalars().all()

    # 汇总状态
    healthy_count = sum(1 for r in health_records if r.status == "healthy")
    unhealthy_count = sum(1 for r in health_records if r.status == "unhealthy")
    degraded_count = sum(1 for r in health_records if r.status == "degraded")

    return {
        "success": True,
        "data": {
            "services": [
                {
                    "service_name": r.service_name,
                    "service_type": r.service_type,
                    "status": r.status,
                    "latency_ms": r.latency_ms,
                    "error_rate": r.error_rate,
                    "success_rate": r.success_rate,
                    "message": r.message,
                    "checked_at": r.checked_at.isoformat(),
                }
                for r in health_records
            ],
            "summary": {
                "total": len(health_records),
                "healthy": healthy_count,
                "unhealthy": unhealthy_count,
                "degraded": degraded_count,
                "health_score": healthy_count / len(health_records) * 100 if health_records else 0,
            },
        },
    }


@router.post("/health/report")
async def report_health(
    service_name: str = Query(..., description="服务名称"),
    status: str = Query(..., description="健康状态"),
    latency_ms: Optional[float] = Query(None, description="延迟"),
    error_rate: Optional[float] = Query(None, description="错误率"),
    details: Optional[Dict[str, Any]] = Body(None, description="详细信息"),
    message: Optional[str] = Query(None, description="状态消息"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上报服务健康状态"""
    health = SystemHealth(
        service_name=service_name,
        status=status,
        latency_ms=latency_ms,
        error_rate=error_rate,
        details=details or {},
        message=message,
    )
    db.add(health)
    await db.commit()

    return {
        "success": True,
        "message": "Health status reported",
    }


# ========== 告警管理 ==========

@router.get("/alerts/rules")
async def list_alert_rules(
    is_active: Optional[bool] = Query(None, description="是否启用"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警规则列表"""
    query = select(AlertRule)
    if is_active is not None:
        query = query.where(AlertRule.is_active == is_active)

    result = await db.execute(query)
    rules = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "metric_name": r.metric_name,
                "condition": r.condition,
                "threshold": r.threshold,
                "severity": r.severity,
                "is_active": r.is_active,
            }
            for r in rules
        ],
    }


@router.get("/alerts/history")
async def get_alert_history(
    status: Optional[str] = Query(None, description="告警状态"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警历史"""
    query = select(AlertHistory).order_by(AlertHistory.fired_at.desc())
    if status:
        query = query.where(AlertHistory.status == status)
    query = query.limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "rule_id": a.rule_id,
                "alert_name": a.alert_name,
                "metric_value": a.metric_value,
                "threshold": a.threshold,
                "message": a.message,
                "severity": a.severity,
                "status": a.status,
                "fired_at": a.fired_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in alerts
        ],
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认告警"""
    result = await db.execute(
        select(AlertHistory).where(AlertHistory.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    alert.status = "acknowledged"
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now()
    await db.commit()

    return {
        "success": True,
        "message": "告警已确认",
    }


# ========== 仪表盘 ==========

@router.get("/dashboards")
async def list_dashboards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取仪表盘列表"""
    query = select(DashboardConfig).where(
        (DashboardConfig.owner_id == current_user.id) |
        (DashboardConfig.is_public == True)
    )

    result = await db.execute(query)
    dashboards = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "is_public": d.is_public,
                "owner_id": d.owner_id,
                "created_at": d.created_at.isoformat(),
            }
            for d in dashboards
        ],
    }


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取仪表盘详情"""
    result = await db.execute(
        select(DashboardConfig).where(DashboardConfig.id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="仪表盘不存在")

    return {
        "success": True,
        "data": {
            "id": dashboard.id,
            "name": dashboard.name,
            "description": dashboard.description,
            "layout": dashboard.layout,
            "widgets": dashboard.widgets,
            "is_public": dashboard.is_public,
        },
    }


# ========== 统计摘要 ==========

@router.get("/stats/summary")
async def get_stats_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取统计摘要"""
    # 获取指标数量
    metric_count = await db.execute(
        select(func.count()).select_from(MonitorMetric)
    )

    # 获取告警统计
    alert_query = select(
        AlertHistory.status,
        func.count().label("count"),
    ).group_by(AlertHistory.status)
    alert_result = await db.execute(alert_query)
    alert_stats = {row.status: row.count for row in alert_result}

    # 获取健康服务统计
    health_query = select(
        SystemHealth.status,
        func.count(func.distinct(SystemHealth.service_name)).label("count"),
    ).group_by(SystemHealth.status)
    health_result = await db.execute(health_query)
    health_stats = {row.status: row.count for row in health_result}

    return {
        "success": True,
        "data": {
            "metrics": {
                "total_records": metric_count.scalar(),
            },
            "alerts": alert_stats,
            "health": health_stats,
        },
    }
