"""
告警中心服务层
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.alert import AlertChannel, AlertSubscription, WarningAlert, AlertTemplate
from app.models.billing import Account, BillingRecord
from app.models.quota import Quota, QuotaUsage
from app.models.user import User
from app.core.config import settings
from app.services.email import send_template_email


class AlertChannelService:
    """告警渠道服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_channels(self, is_active: bool = True) -> List[AlertChannel]:
        """获取告警渠道列表"""
        query = select(AlertChannel)
        if is_active:
            query = query.where(AlertChannel.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_channel(self, channel_id: int) -> Optional[AlertChannel]:
        """获取渠道详情"""
        result = await self.db.execute(
            select(AlertChannel).where(AlertChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def create_channel(
        self,
        name: str,
        channel_type: str,
        display_name: str = None,
        config: dict = None,
        is_active: bool = True,
        created_by: int = None,
    ) -> AlertChannel:
        """创建告警渠道"""
        channel = AlertChannel(
            name=name,
            channel_type=channel_type,
            display_name=display_name or name,
            config=config or {},
            is_active=is_active,
            created_by=created_by,
        )
        self.db.add(channel)
        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def update_channel(
        self,
        channel_id: int,
        **update_data,
    ) -> Optional[AlertChannel]:
        """更新告警渠道"""
        channel = await self.get_channel(channel_id)
        if not channel:
            return None

        for key, value in update_data.items():
            if hasattr(channel, key):
                setattr(channel, key, value)

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def delete_channel(self, channel_id: int) -> bool:
        """删除告警渠道"""
        channel = await self.get_channel(channel_id)
        if not channel:
            return False

        await self.db.delete(channel)
        await self.db.commit()
        return True


class AlertSubscriptionService:
    """告警订阅服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_subscriptions(
        self,
        user_id: int = None,
        alert_type: str = None,
        is_enabled: bool = True,
    ) -> List[AlertSubscription]:
        """获取订阅列表"""
        query = select(AlertSubscription)
        if user_id:
            query = query.where(AlertSubscription.user_id == user_id)
        if alert_type:
            query = query.where(AlertSubscription.alert_type == alert_type)
        if is_enabled:
            query = query.where(AlertSubscription.is_enabled == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_subscription(self, subscription_id: int) -> Optional[AlertSubscription]:
        """获取订阅详情"""
        result = await self.db.execute(
            select(AlertSubscription).where(AlertSubscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def create_subscription(
        self,
        user_id: int,
        alert_type: str,
        resource_type: str = None,
        resource_id: str = None,
        channel_ids: list = None,
        custom_threshold: float = None,
        custom_severity: str = None,
    ) -> AlertSubscription:
        """创建告警订阅"""
        subscription = AlertSubscription(
            user_id=user_id,
            alert_type=alert_type,
            resource_type=resource_type,
            resource_id=resource_id,
            channel_ids=channel_ids or [],
            custom_threshold=custom_threshold,
            custom_severity=custom_severity,
        )
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def update_subscription(
        self,
        subscription_id: int,
        **update_data,
    ) -> Optional[AlertSubscription]:
        """更新告警订阅"""
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return None

        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def delete_subscription(self, subscription_id: int) -> bool:
        """删除告警订阅"""
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return False

        await self.db.delete(subscription)
        await self.db.commit()
        return True


class WarningAlertService:
    """预警服务 - 余额、配额、成本预警"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_service = AlertSubscriptionService(db)

    async def check_balance_warning(
        self,
        account_id: str = None,
        user_id: int = None,
    ) -> List[WarningAlert]:
        """检查余额预警"""
        alerts = []
        query = select(Account)

        if account_id:
            query = query.where(Account.id == account_id)
        if user_id:
            query = query.where(Account.user_id == user_id)

        result = await self.db.execute(query)
        accounts = list(result.scalars().all())

        for account in accounts:
            balance = float(account.balance) if account.balance else 0
            threshold = settings.BALANCE_WARNING_THRESHOLD

            if balance < threshold:
                # 检查是否已有未处理的预警
                exists = await self._check_existing_alert(
                    alert_type="balance",
                    resource_type="account",
                    resource_id=account.id,
                    status="pending",
                )

                if not exists:
                    alert = await self._create_warning_alert(
                        alert_type="balance",
                        alert_subtype="low_balance",
                        resource_type="account",
                        resource_id=account.id,
                        user_id=account.user_id,
                        current_value=balance,
                        threshold_value=threshold,
                        unit="CNY",
                        severity="warning" if balance > 0 else "error",
                        message=f"账户余额不足：当前余额 {balance:.2f} CNY，低于阈值 {threshold:.2f} CNY",
                    )
                    alerts.append(alert)
                    await self._send_alert_notifications(alert)

        return alerts

    async def check_quota_warning(
        self,
        scope_type: str = None,
        scope_id: str = None,
    ) -> List[WarningAlert]:
        """检查配额预警"""
        alerts = []
        query = select(QuotaUsage).join(Quota)

        if scope_type and scope_id:
            query = query.where(
                and_(
                    QuotaUsage.scope_type == scope_type,
                    QuotaUsage.scope_id == scope_id,
                )
            )

        # 只查询当前周期的使用记录
        now = datetime.utcnow()
        query = query.where(QuotaUsage.period_start <= now)
        query = query.where(QuotaUsage.period_end >= now)

        result = await self.db.execute(query)
        usages = list(result.scalars().all())

        threshold = settings.QUOTA_WARNING_THRESHOLD  # 80%

        for usage in usages:
            if usage.limit_value and usage.limit_value > 0:
                usage_rate = usage.used_value / usage.limit_value

                if usage_rate >= threshold:
                    exists = await self._check_existing_alert(
                        alert_type="quota",
                        alert_subtype="high_usage",
                        resource_type=usage.scope_type,
                        resource_id=usage.scope_id,
                        status="pending",
                    )

                    if not exists:
                        severity = "critical" if usage_rate >= 1.0 else "warning"
                        alert = await self._create_warning_alert(
                            alert_type="quota",
                            alert_subtype="high_usage",
                            resource_type=usage.scope_type,
                            resource_id=usage.scope_id,
                            user_id=None,  # 配额可能是应用层级
                            current_value=usage_rate * 100,
                            threshold_value=threshold * 100,
                            unit="percent",
                            severity=severity,
                            message=f"配额使用率过高：{usage_rate * 100:.1f}%，超过阈值 {threshold * 100:.1f}%",
                        )
                        alerts.append(alert)
                        await self._send_alert_notifications(alert)

        return alerts

    async def check_cost_warning(
        self,
        account_id: str = None,
        user_id: int = None,
        budget: float = None,
    ) -> List[WarningAlert]:
        """检查成本预警（超出预算）"""
        alerts = []
        query = select(Account)

        if account_id:
            query = query.where(Account.id == account_id)
        if user_id:
            query = query.where(Account.user_id == user_id)

        result = await self.db.execute(query)
        accounts = list(result.scalars().all())

        for account in accounts:
            # 计算本月消费
            start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            result = await self.db.execute(
                select(func.sum(BillingRecord.amount))
                .where(BillingRecord.account_id == account.id)
                .where(BillingRecord.record_type == "consume")
                .where(BillingRecord.created_at >= start_of_month)
            )
            month_consumption = float(result.scalar() or 0)

            # 使用账户的月度预算（如果有）或默认预算
            account_budget = budget or getattr(account, 'monthly_budget', 1000.0)

            if month_consumption >= account_budget * 0.8:  # 80% 预算时预警
                exists = await self._check_existing_alert(
                    alert_type="cost",
                    alert_subtype="over_budget",
                    resource_type="account",
                    resource_id=account.id,
                    status="pending",
                )

                if not exists:
                    severity = "critical" if month_consumption >= account_budget else "warning"
                    alert = await self._create_warning_alert(
                        alert_type="cost",
                        alert_subtype="over_budget",
                        resource_type="account",
                        resource_id=account.id,
                        user_id=account.user_id,
                        current_value=month_consumption,
                        threshold_value=account_budget,
                        unit="CNY",
                        severity=severity,
                        message=f"本月消费超出预算：{month_consumption:.2f} CNY，预算 {account_budget:.2f} CNY",
                    )
                    alerts.append(alert)
                    await self._send_alert_notifications(alert)

        return alerts

    async def _check_existing_alert(
        self,
        alert_type: str,
        resource_type: str,
        resource_id: str,
        status: str,
    ) -> bool:
        """检查是否已存在未处理的预警"""
        result = await self.db.execute(
            select(WarningAlert)
            .where(WarningAlert.alert_type == alert_type)
            .where(WarningAlert.resource_type == resource_type)
            .where(WarningAlert.resource_id == resource_id)
            .where(WarningAlert.status == status)
        )
        return result.scalar_one_or_none() is not None

    async def _create_warning_alert(
        self,
        alert_type: str,
        alert_subtype: str,
        resource_type: str,
        resource_id: str,
        user_id: int,
        current_value: float,
        threshold_value: float,
        unit: str,
        severity: str,
        message: str,
    ) -> WarningAlert:
        """创建预警记录"""
        alert = WarningAlert(
            alert_type=alert_type,
            alert_subtype=alert_subtype,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            current_value=current_value,
            threshold_value=threshold_value,
            unit=unit,
            severity=severity,
            message=message,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def _send_alert_notifications(self, alert: WarningAlert) -> bool:
        """发送预警通知"""
        # 获取订阅该告警类型的用户
        subscriptions = await self.subscription_service.list_subscriptions(
            alert_type=alert.alert_type,
            is_enabled=True,
        )

        notified_channels = []
        for subscription in subscriptions:
            # 检查资源匹配
            if subscription.resource_id and subscription.resource_id != alert.resource_id:
                continue

            # 获取通知渠道
            channel_ids = subscription.channel_ids or []
            for channel_id in channel_ids:
                channel_result = await self.db.execute(
                    select(AlertChannel).where(AlertChannel.id == channel_id)
                )
                channel = channel_result.scalar_one_or_none()

                if channel and channel.is_active and channel.channel_type == "email":
                    # 发送邮件通知
                    config = channel.config or {}
                    recipient = config.get("recipient_email")
                    if recipient:
                        success = await self._send_alert_email(alert, recipient)
                        if success:
                            notified_channels.append(f"email:{channel.name}")

        # 更新预警记录
        alert.notified_channels = notified_channels
        alert.notified_at = datetime.utcnow()
        alert.status = "sent"
        await self.db.commit()

        return len(notified_channels) > 0

    async def _send_alert_email(self, alert: WarningAlert, recipient: str) -> bool:
        """发送预警邮件"""
        severity_colors = {
            "info": "#1890ff",
            "warning": "#faad14",
            "error": "#f5222d",
            "critical": "#722ed1",
        }

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: {severity_colors.get(alert.severity, '#333')};">
                [{alert.severity.upper()}] {alert.alert_type.upper()} 预警通知
            </h2>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>预警类型:</strong> {alert.alert_type} ({alert.alert_subtype})</p>
                <p><strong>资源类型:</strong> {alert.resource_type}</p>
                <p><strong>资源 ID:</strong> {alert.resource_id}</p>
                <p><strong>当前值:</strong> {alert.current_value} {alert.unit}</p>
                <p><strong>阈值:</strong> {alert.threshold_value} {alert.unit}</p>
                <p><strong>严重级别:</strong> {alert.severity}</p>
                <p><strong>发生时间:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p style="color: #666;">{alert.message}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                此邮件由 AI 中台预警系统自动发送，请勿回复。
                如需取消订阅，请前往系统设置。
            </p>
        </body>
        </html>
        """

        try:
            await send_template_email(
                to=recipient,
                subject=f"[{alert.severity.upper()}] {alert.alert_type.upper()} 预警通知 - {alert.alert_subtype}",
                html_content=html_content,
            )
            return True
        except Exception as e:
            print(f"发送预警邮件失败：{e}")
            return False

    async def list_alerts(
        self,
        alert_type: str = None,
        status: str = None,
        resource_type: str = None,
        resource_id: str = None,
        user_id: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WarningAlert]:
        """获取预警记录列表"""
        query = select(WarningAlert)

        if alert_type:
            query = query.where(WarningAlert.alert_type == alert_type)
        if status:
            query = query.where(WarningAlert.status == status)
        if resource_type:
            query = query.where(WarningAlert.resource_type == resource_type)
        if resource_id:
            query = query.where(WarningAlert.resource_id == resource_id)
        if user_id:
            query = query.where(WarningAlert.user_id == user_id)
        if start_date:
            query = query.where(WarningAlert.created_at >= start_date)
        if end_date:
            query = query.where(WarningAlert.created_at <= end_date)

        query = query.order_by(WarningAlert.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def acknowledge_alert(self, alert_id: int, user_id: int) -> Optional[WarningAlert]:
        """确认预警"""
        result = await self.db.execute(
            select(WarningAlert).where(WarningAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = "acknowledged"
            alert.acknowledged_by = user_id
            await self.db.commit()
            await self.db.refresh(alert)
        return alert

    async def resolve_alert(self, alert_id: int) -> Optional[WarningAlert]:
        """解决预警"""
        result = await self.db.execute(
            select(WarningAlert).where(WarningAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = "resolved"
            alert.resolved_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(alert)
        return alert


class AlertTemplateService:
    """告警模板服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_templates(
        self,
        template_type: str = None,
        is_active: bool = True,
    ) -> List[AlertTemplate]:
        """获取模板列表"""
        query = select(AlertTemplate)
        if template_type:
            query = query.where(AlertTemplate.template_type == template_type)
        if is_active:
            query = query.where(AlertTemplate.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_template(self, template_id: int) -> Optional[AlertTemplate]:
        """获取模板详情"""
        result = await self.db.execute(
            select(AlertTemplate).where(AlertTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def create_template(
        self,
        name: str,
        template_type: str,
        content_template: str,
        subject_template: str = None,
        alert_types: list = None,
        is_default: bool = False,
        created_by: int = None,
    ) -> AlertTemplate:
        """创建告警模板"""
        if is_default:
            # 取消其他默认模板
            await self.db.execute(
                AlertTemplate.update()
                .where(AlertTemplate.template_type == template_type)
                .values(is_default=False)
            )

        template = AlertTemplate(
            name=name,
            template_type=template_type,
            subject_template=subject_template,
            content_template=content_template,
            alert_types=alert_types or [],
            is_default=is_default,
            created_by=created_by,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(
        self,
        template_id: int,
        **update_data,
    ) -> Optional[AlertTemplate]:
        """更新告警模板"""
        template = await self.get_template(template_id)
        if not template:
            return None

        for key, value in update_data.items():
            if hasattr(template, key):
                setattr(template, key, value)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: int) -> bool:
        """删除告警模板"""
        template = await self.get_template(template_id)
        if not template:
            return False

        await self.db.delete(template)
        await self.db.commit()
        return True
