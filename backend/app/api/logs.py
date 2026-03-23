"""
日志管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from datetime import datetime, timedelta

from ..core.database import get_db
from ..models.user import User
from ..models.api_log import APILog, AuditLog
from ..auth.dependencies import get_current_user

router = APIRouter()


@router.get("/api-calls")
async def list_api_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    endpoint: Optional[str] = None,
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 API 调用日志
    """
    query = select(APILog)

    # 时间范围
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.where(APILog.created_at >= start_date)

    # 筛选条件
    if user_id:
        query = query.where(APILog.user_id == user_id)
    if endpoint:
        query = query.where(APILog.endpoint == endpoint)

    # 排序
    query = query.order_by(desc(APILog.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "trace_id": log.trace_id,
                "request_id": log.request_id,
                "method": log.method,
                "path": log.path,
                "endpoint": log.endpoint,
                "response_status": log.response_status,
                "latency_ms": log.latency_ms,
                "model_name": log.model_name,
                "tokens_used": log.tokens_used,
                "is_success": log.is_success,
                "created_at": str(log.created_at),
            }
            for log in logs
        ],
    }


@router.get("/audit")
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取审计日志
    """
    query = select(AuditLog)

    # 时间范围
    start_date = datetime.utcnow() - timedelta(days=days)
    query = query.where(AuditLog.created_at >= start_date)

    # 筛选条件
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    # 排序
    query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "trace_id": log.trace_id,
                "action": log.action,
                "username": log.username,
                "resource_type": log.resource_type,
                "resource_name": log.resource_name,
                "operation": log.operation,
                "result": log.result,
                "ip_address": log.ip_address,
                "created_at": str(log.created_at),
            }
            for log in logs
        ],
    }


@router.get("/stats")
async def get_statistics(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取调用统计
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # 总调用次数
    total_result = await db.execute(
        select(func.count(APILog.id))
        .where(APILog.created_at >= start_date)
    )
    total_calls = total_result.scalar()

    # 成功调用次数
    success_result = await db.execute(
        select(func.count(APILog.id))
        .where(APILog.created_at >= start_date)
        .where(APILog.is_success == True)
    )
    success_calls = success_result.scalar()

    # 平均延迟
    latency_result = await db.execute(
        select(func.avg(APILog.latency_ms))
        .where(APILog.created_at >= start_date)
    )
    avg_latency = latency_result.scalar() or 0

    # Token 使用量
    tokens_result = await db.execute(
        select(func.sum(APILog.tokens_used))
        .where(APILog.created_at >= start_date)
    )
    total_tokens = tokens_result.scalar() or 0

    return {
        "period_days": days,
        "total_calls": total_calls,
        "success_calls": success_calls,
        "success_rate": success_calls / total_calls * 100 if total_calls > 0 else 0,
        "avg_latency_ms": round(avg_latency, 2),
        "total_tokens": total_tokens,
    }
