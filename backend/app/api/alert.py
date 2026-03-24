"""
告警中心 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.alert import AlertChannel, AlertSubscription, WarningAlert, AlertTemplate
from app.services.alert import (
    AlertChannelService,
    AlertSubscriptionService,
    WarningAlertService,
    AlertTemplateService,
)
from app.utils.permissions import verify_admin_user

router = APIRouter()


# ========== 告警渠道管理 ==========

@router.get("/alert/channels")
async def list_alert_channels(
    is_active: Optional[bool] = Query(True, description="是否启用"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警渠道列表"""
    service = AlertChannelService(db)
    channels = await service.list_channels(is_active=is_active)

    return {
        "success": True,
        "data": [channel.to_dict() for channel in channels],
    }


@router.get("/alert/channels/{channel_id}")
async def get_alert_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警渠道详情"""
    service = AlertChannelService(db)
    channel = await service.get_channel(channel_id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警渠道不存在",
        )

    return {
        "success": True,
        "data": channel.to_dict(),
    }


@router.post("/alert/channels")
async def create_alert_channel(
    name: str = Body(..., description="渠道名称"),
    channel_type: str = Body(..., description="渠道类型：email/sms/webhook/slack"),
    display_name: str = Body(None, description="显示名称"),
    config: Dict[str, Any] = Body({}, description="渠道配置"),
    is_active: bool = Body(True, description="是否启用"),
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """创建告警渠道（管理员）"""
    service = AlertChannelService(db)

    channel = await service.create_channel(
        name=name,
        channel_type=channel_type,
        display_name=display_name,
        config=config,
        is_active=is_active,
        created_by=current_user.id,
    )

    return {
        "success": True,
        "data": channel.to_dict(),
        "message": "告警渠道创建成功",
    }


@router.put("/alert/channels/{channel_id}")
async def update_alert_channel(
    channel_id: int,
    display_name: Optional[str] = Body(None),
    config: Optional[Dict[str, Any]] = Body(None),
    is_active: Optional[bool] = Body(None),
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新告警渠道（管理员）"""
    service = AlertChannelService(db)

    update_data = {
        k: v for k, v in {
            "display_name": display_name,
            "config": config,
            "is_active": is_active,
        }.items() if v is not None
    }

    channel = await service.update_channel(channel_id, **update_data)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警渠道不存在",
        )

    return {
        "success": True,
        "data": channel.to_dict(),
        "message": "告警渠道更新成功",
    }


@router.delete("/alert/channels/{channel_id}")
async def delete_alert_channel(
    channel_id: int,
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除告警渠道（管理员）"""
    service = AlertChannelService(db)
    success = await service.delete_channel(channel_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警渠道不存在",
        )

    return {
        "success": True,
        "message": "告警渠道已删除",
    }


# ========== 告警订阅管理 ==========

@router.get("/alert/subscriptions")
async def list_alert_subscriptions(
    alert_type: Optional[str] = Query(None, description="告警类型"),
    is_enabled: Optional[bool] = Query(True, description="是否启用"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警订阅列表"""
    service = AlertSubscriptionService(db)

    # 普通用户只能查看自己的订阅
    user_id = current_user.id if not current_user.is_superuser else None
    subscriptions = await service.list_subscriptions(
        user_id=user_id,
        alert_type=alert_type,
        is_enabled=is_enabled,
    )

    return {
        "success": True,
        "data": [sub.to_dict() for sub in subscriptions],
    }


@router.get("/alert/subscriptions/{subscription_id}")
async def get_alert_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警订阅详情"""
    service = AlertSubscriptionService(db)
    subscription = await service.get_subscription(subscription_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警订阅不存在",
        )

    # 权限检查
    if not current_user.is_superuser and subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看该订阅",
        )

    return {
        "success": True,
        "data": subscription.to_dict(),
    }


@router.post("/alert/subscriptions")
async def create_alert_subscription(
    alert_type: str = Body(..., description="告警类型：balance/quota/cost"),
    resource_type: str = Body(None, description="资源类型"),
    resource_id: str = Body(None, description="资源 ID"),
    channel_ids: List[int] = Body([], description="通知渠道 ID 列表"),
    custom_threshold: float = Body(None, description="自定义阈值"),
    custom_severity: str = Body(None, description="自定义严重级别"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建告警订阅"""
    service = AlertSubscriptionService(db)

    subscription = await service.create_subscription(
        user_id=current_user.id,
        alert_type=alert_type,
        resource_type=resource_type,
        resource_id=resource_id,
        channel_ids=channel_ids,
        custom_threshold=custom_threshold,
        custom_severity=custom_severity,
    )

    return {
        "success": True,
        "data": subscription.to_dict(),
        "message": "告警订阅创建成功",
    }


@router.put("/alert/subscriptions/{subscription_id}")
async def update_alert_subscription(
    subscription_id: int,
    channel_ids: Optional[List[int]] = Body(None),
    custom_threshold: Optional[float] = Body(None),
    custom_severity: Optional[str] = Body(None),
    is_enabled: Optional[bool] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新告警订阅"""
    service = AlertSubscriptionService(db)

    subscription = await service.get_subscription(subscription_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警订阅不存在",
        )

    # 权限检查
    if not current_user.is_superuser and subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作该订阅",
        )

    update_data = {
        k: v for k, v in {
            "channel_ids": channel_ids,
            "custom_threshold": custom_threshold,
            "custom_severity": custom_severity,
            "is_enabled": is_enabled,
        }.items() if v is not None
    }

    subscription = await service.update_subscription(subscription_id, **update_data)

    return {
        "success": True,
        "data": subscription.to_dict(),
        "message": "告警订阅更新成功",
    }


@router.delete("/alert/subscriptions/{subscription_id}")
async def delete_alert_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除告警订阅"""
    service = AlertSubscriptionService(db)

    subscription = await service.get_subscription(subscription_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警订阅不存在",
        )

    # 权限检查
    if not current_user.is_superuser and subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作该订阅",
        )

    success = await service.delete_subscription(subscription_id)

    return {
        "success": True,
        "message": "告警订阅已删除",
    }


# ========== 预警记录管理 ==========

@router.get("/alert/warnings")
async def list_warning_alerts(
    alert_type: Optional[str] = Query(None, description="告警类型"),
    status: Optional[str] = Query(None, description="状态"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    resource_id: Optional[str] = Query(None, description="资源 ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取预警记录列表"""
    service = WarningAlertService(db)

    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始日期格式不正确",
            )
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="结束日期格式不正确",
            )

    # 普通用户只能查看自己的预警
    user_id = current_user.id if not current_user.is_superuser else None

    alerts = await service.list_alerts(
        alert_type=alert_type,
        status=status,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": [alert.to_dict() for alert in alerts],
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/alert/warnings/{alert_id}")
async def get_warning_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取预警详情"""
    result = await db.execute(
        select(WarningAlert).where(WarningAlert.id == alert_id)
    )
    from sqlalchemy import select
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警记录不存在",
        )

    # 权限检查
    if not current_user.is_superuser and alert.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看该预警",
        )

    return {
        "success": True,
        "data": alert.to_dict(),
    }


@router.post("/alert/warnings/{alert_id}/acknowledge")
async def acknowledge_warning_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认预警"""
    service = WarningAlertService(db)
    alert = await service.acknowledge_alert(alert_id, current_user.id)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警记录不存在",
        )

    return {
        "success": True,
        "message": "预警已确认",
        "data": alert.to_dict(),
    }


@router.post("/alert/warnings/{alert_id}/resolve")
async def resolve_warning_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """解决预警"""
    service = WarningAlertService(db)
    alert = await service.resolve_alert(alert_id)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预警记录不存在",
        )

    return {
        "success": True,
        "message": "预警已解决",
        "data": alert.to_dict(),
    }


# ========== 预警检查（定时任务调用） ==========

@router.post("/alert/check")
async def run_warning_checks(
    check_type: Optional[str] = Body(None, description="检查类型：balance/quota/cost/all"),
    account_id: Optional[str] = Body(None, description="账户 ID"),
    user_id: Optional[int] = Body(None, description="用户 ID"),
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """运行预警检查（管理员/系统任务）"""
    service = WarningAlertService(db)
    alerts = []

    if check_type in [None, "all", "balance"]:
        balance_alerts = await service.check_balance_warning(
            account_id=account_id,
            user_id=user_id,
        )
        alerts.extend(balance_alerts)

    if check_type in [None, "all", "quota"]:
        quota_alerts = await service.check_quota_warning()
        alerts.extend(quota_alerts)

    if check_type in [None, "all", "cost"]:
        cost_alerts = await service.check_cost_warning(
            account_id=account_id,
            user_id=user_id,
        )
        alerts.extend(cost_alerts)

    return {
        "success": True,
        "message": f"预警检查完成，发现 {len(alerts)} 个预警",
        "data": {
            "check_type": check_type or "all",
            "alerts_found": len(alerts),
            "alerts": [alert.to_dict() for alert in alerts],
        },
    }


# ========== 告警模板管理 ==========

@router.get("/alert/templates")
async def list_alert_templates(
    template_type: Optional[str] = Query(None, description="模板类型"),
    is_active: Optional[bool] = Query(True, description="是否启用"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警模板列表"""
    service = AlertTemplateService(db)
    templates = await service.list_templates(
        template_type=template_type,
        is_active=is_active,
    )

    return {
        "success": True,
        "data": [template.to_dict() for template in templates],
    }


@router.get("/alert/templates/{template_id}")
async def get_alert_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警模板详情"""
    service = AlertTemplateService(db)
    template = await service.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警模板不存在",
        )

    return {
        "success": True,
        "data": template.to_dict(),
    }


@router.post("/alert/templates")
async def create_alert_template(
    name: str = Body(..., description="模板名称"),
    template_type: str = Body(..., description="模板类型：email/sms/webhook"),
    content_template: str = Body(..., description="内容模板"),
    subject_template: str = Body(None, description="主题模板"),
    alert_types: List[str] = Body([], description="适用的告警类型"),
    is_default: bool = Body(False, description="是否默认模板"),
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """创建告警模板（管理员）"""
    service = AlertTemplateService(db)

    template = await service.create_template(
        name=name,
        template_type=template_type,
        content_template=content_template,
        subject_template=subject_template,
        alert_types=alert_types,
        is_default=is_default,
        created_by=current_user.id,
    )

    return {
        "success": True,
        "data": template.to_dict(),
        "message": "告警模板创建成功",
    }


@router.put("/alert/templates/{template_id}")
async def update_alert_template(
    template_id: int,
    name: Optional[str] = Body(None),
    content_template: Optional[str] = Body(None),
    subject_template: Optional[str] = Body(None),
    alert_types: Optional[List[str]] = Body(None),
    is_active: Optional[bool] = Body(None),
    is_default: Optional[bool] = Body(None),
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新告警模板（管理员）"""
    service = AlertTemplateService(db)

    update_data = {
        k: v for k, v in {
            "name": name,
            "content_template": content_template,
            "subject_template": subject_template,
            "alert_types": alert_types,
            "is_active": is_active,
            "is_default": is_default,
        }.items() if v is not None
    }

    template = await service.update_template(template_id, **update_data)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警模板不存在",
        )

    return {
        "success": True,
        "data": template.to_dict(),
        "message": "告警模板更新成功",
    }


@router.delete("/alert/templates/{template_id}")
async def delete_alert_template(
    template_id: int,
    current_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除告警模板（管理员）"""
    service = AlertTemplateService(db)
    success = await service.delete_template(template_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警模板不存在",
        )

    return {
        "success": True,
        "message": "告警模板已删除",
    }


# ========== 告警统计 ==========

@router.get("/alert/stats")
async def get_alert_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取告警统计信息"""
    from sqlalchemy import select, func
    from datetime import timedelta

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 总预警数
    total_result = await db.execute(
        select(func.count(WarningAlert.id))
        .where(WarningAlert.created_at >= start_date)
    )
    total = total_result.scalar() or 0

    # 按状态统计
    status_result = await db.execute(
        select(WarningAlert.status, func.count(WarningAlert.id))
        .where(WarningAlert.created_at >= start_date)
        .group_by(WarningAlert.status)
    )
    by_status = {row[0]: row[1] for row in status_result.fetchall()}

    # 按类型统计
    type_result = await db.execute(
        select(WarningAlert.alert_type, func.count(WarningAlert.id))
        .where(WarningAlert.created_at >= start_date)
        .group_by(WarningAlert.alert_type)
    )
    by_type = {row[0]: row[1] for row in type_result.fetchall()}

    # 按严重级别统计
    severity_result = await db.execute(
        select(WarningAlert.severity, func.count(WarningAlert.id))
        .where(WarningAlert.created_at >= start_date)
        .group_by(WarningAlert.severity)
    )
    by_severity = {row[0]: row[1] for row in severity_result.fetchall()}

    return {
        "success": True,
        "data": {
            "days": days,
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "by_severity": by_severity,
        },
    }
