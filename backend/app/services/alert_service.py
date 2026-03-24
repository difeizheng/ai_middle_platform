"""
告警服务

负责告警规则匹配、告警触发和通知发送
以及余额、配额、成本预警检查
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from app.core.logger import get_logger
from app.core.database import get_db_session
from app.models.monitor import AlertRule, AlertHistory, SystemHealth
from app.models.alert import WarningAlert
from app.services.notification import get_notifier, send_alert
from app.services.metrics import get_metric_collector
from app.services.alert import WarningAlertService  # 新增预警服务

logger = get_logger(__name__)


class AlertService:
    """
    告警服务

    功能:
    - 定期检查告警规则
    - 触发告警并发送通知
    - 告警历史记录
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 60  # 默认 60 秒检查一次

    async def start(self, interval: int = 60):
        """启动告警检查"""
        self._check_interval = interval
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"告警检查器已启动，检查间隔：{interval}秒")

    async def stop(self):
        """停止告警检查"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("告警检查器已停止")

    async def _check_loop(self):
        """告警检查循环"""
        while self._running:
            try:
                await self._check_alerts()
            except Exception as e:
                logger.error(f"告警检查出错：{e}")
            await asyncio.sleep(self._check_interval)

    async def _check_alerts(self):
        """检查所有告警规则"""
        db = await get_db_session().__anext__()

        try:
            # 1. 检查传统告警规则（基于监控指标）
            from sqlalchemy import select
            result = await db.execute(
                select(AlertRule).where(AlertRule.is_active == True)
            )
            rules = result.scalars().all()

            for rule in rules:
                await self._evaluate_rule(rule, db)

            # 2. 检查余额、配额、成本预警（新增）
            await self._check_warning_alerts(db)

        finally:
            await db.close()

    async def _check_warning_alerts(self, db):
        """检查余额、配额、成本预警"""
        try:
            warning_service = WarningAlertService(db)

            # 检查余额预警
            await warning_service.check_balance_warning()

            # 检查配额预警
            await warning_service.check_quota_warning()

            # 检查成本预警
            await warning_service.check_cost_warning()

        except Exception as e:
            logger.error(f"预警检查出错：{e}")

    async def _evaluate_rule(self, rule: AlertRule, db):
        """评估告警规则"""
        try:
            # 获取当前指标值
            collector = get_metric_collector()
            current_value = collector.get(rule.metric_name)

            if current_value is None:
                return  # 没有数据，不触发告警

            # 检查是否满足告警条件
            triggered = self._check_condition(current_value, rule.condition, rule.threshold)

            if triggered:
                # 检查是否有重复告警（避免短时间重复通知）
                from sqlalchemy import select
                recent_alert = await db.execute(
                    select(AlertHistory)
                    .where(AlertHistory.rule_id == rule.id)
                    .where(AlertHistory.status.in_(["fired", "acknowledged"]))
                    .order_by(AlertHistory.fired_at.desc())
                )
                recent = recent_alert.scalar_one_or_none()

                # 如果最近 5 分钟内已有告警，不再重复触发
                if recent and (datetime.now() - recent.fired_at).total_seconds() < 300:
                    return

                # 创建告警记录
                alert = AlertHistory(
                    rule_id=rule.id,
                    alert_name=rule.name,
                    metric_name=rule.metric_name,
                    metric_value=current_value,
                    threshold=rule.threshold,
                    message=f"指标 {rule.metric_name} 当前值 {current_value} {rule.condition} 阈值 {rule.threshold}",
                    severity=rule.severity,
                    status="fired",
                )
                db.add(alert)
                await db.commit()
                await db.refresh(alert)

                # 发送通知
                alert_data = {
                    "rule_name": rule.name,
                    "metric_name": rule.metric_name,
                    "metric_value": current_value,
                    "threshold": rule.threshold,
                    "condition": rule.condition,
                    "severity": rule.severity,
                    "message": alert.message,
                    "fired_at": alert.fired_at.isoformat(),
                }

                await send_alert(alert_data)
                logger.info(f"告警已触发并发送通知：{rule.name}")

        except Exception as e:
            logger.error(f"评估告警规则失败 {rule.name}: {e}")

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """检查是否满足告警条件"""
        condition_map = {
            "gt": lambda v, t: v > t,  # greater than
            "gte": lambda v, t: v >= t,  # greater than or equal
            "lt": lambda v, t: v < t,  # less than
            "lte": lambda v, t: v <= t,  # less than or equal
            "eq": lambda v, t: v == t,  # equal
            "ne": lambda v, t: v != t,  # not equal
        }

        checker = condition_map.get(condition.lower())
        if not checker:
            logger.warning(f"未知的告警条件：{condition}")
            return False

        return checker(value, threshold)

    async def trigger_manual_alert(
        self,
        rule_id: int,
        message: str,
        severity: str = "warning",
    ) -> Optional[AlertHistory]:
        """
        手动触发告警

        Args:
            rule_id: 告警规则 ID
            message: 告警消息
            severity: 严重程度

        Returns:
            告警记录
        """
        db = await get_db_session().__anext__()

        try:
            from sqlalchemy import select

            # 获取告警规则
            result = await db.execute(
                select(AlertRule).where(AlertRule.id == rule_id)
            )
            rule = result.scalar_one_or_none()

            if not rule:
                raise ValueError(f"告警规则不存在：{rule_id}")

            # 创建告警记录
            alert = AlertHistory(
                rule_id=rule_id,
                alert_name=rule.name,
                metric_name=rule.metric_name,
                metric_value=0,
                threshold=rule.threshold,
                message=message,
                severity=severity,
                status="fired",
            )
            db.add(alert)
            await db.commit()
            await db.refresh(alert)

            # 发送通知
            alert_data = {
                "rule_name": rule.name,
                "metric_name": rule.metric_name,
                "severity": severity,
                "message": message,
                "fired_at": alert.fired_at.isoformat(),
                "notify_kwargs": {"at_all": False},
            }

            await send_alert(alert_data)
            logger.info(f"手动告警已发送：{rule.name}")

            return alert

        finally:
            await db.close()


# 全局告警服务实例
_global_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """获取全局告警服务"""
    global _global_alert_service
    if _global_alert_service is None:
        _global_alert_service = AlertService()
    return _global_alert_service


async def start_alert_service(interval: int = 60):
    """启动告警服务"""
    service = get_alert_service()
    await service.start(interval)


async def stop_alert_service():
    """停止告警服务"""
    service = get_alert_service()
    await service.stop()
