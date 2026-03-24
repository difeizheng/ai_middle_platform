"""
配额管理服务层
"""
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging

from ..models.quota import Quota, QuotaUsage, QuotaCheckLog
from ..models.user import User

logger = logging.getLogger(__name__)


class QuotaService:
    """配额服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_quota(self, quota_id: str) -> Optional[Quota]:
        """获取配额定义"""
        result = await self.db.execute(
            select(Quota).where(Quota.id == quota_id)
        )
        return result.scalar_one_or_none()

    async def list_quotas(
        self,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        quota_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Quota]:
        """获取配额列表"""
        query = select(Quota)

        if scope_type:
            query = query.where(Quota.scope_type == scope_type)
        if scope_id:
            query = query.where(Quota.scope_id == scope_id)
        if quota_type:
            query = query.where(Quota.quota_type == quota_type)
        if is_active is not None:
            query = query.where(Quota.is_active == is_active)

        query = query.order_by(Quota.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_quota(
        self,
        name: str,
        quota_type: str,
        resource_type: str,
        limit_value: int,
        scope_type: str,
        scope_id: str,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        period_type: str = "daily",
        reset_time: Optional[str] = None,
        parent_quota_id: Optional[str] = None,
        over_limit_action: str = "reject",
        over_limit_rate: float = 1,
        extra_config: Optional[Dict[str, Any]] = None,
    ) -> Quota:
        """创建配额定义"""
        quota = Quota(
            id=str(hash(f"{name}{datetime.utcnow().isoformat()}"))[:36],
            name=name,
            description=description,
            quota_type=quota_type,
            resource_type=resource_type,
            limit_value=limit_value,
            unit=unit,
            period_type=period_type,
            reset_time=reset_time,
            scope_type=scope_type,
            scope_id=scope_id,
            parent_quota_id=parent_quota_id,
            is_inherited=parent_quota_id is not None,
            over_limit_action=over_limit_action,
            over_limit_rate=Decimal(str(over_limit_rate)),
            extra_config=json.dumps(extra_config) if extra_config else '{}',
        )

        self.db.add(quota)
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def update_quota(
        self,
        quota_id: str,
        **kwargs,
    ) -> Optional[Quota]:
        """更新配额定义"""
        quota = await self.get_quota(quota_id)
        if not quota:
            return None

        for key, value in kwargs.items():
            if key == "extra_config" and isinstance(value, dict):
                setattr(quota, key, json.dumps(value))
            elif key == "over_limit_rate":
                setattr(quota, key, Decimal(str(value)))
            elif hasattr(quota, key):
                setattr(quota, key, value)

        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def delete_quota(self, quota_id: str) -> bool:
        """删除配额定义"""
        quota = await self.get_quota(quota_id)
        if not quota:
            return False

        await self.db.delete(quota)
        await self.db.commit()
        return True

    async def get_or_create_usage(
        self,
        quota_id: str,
        scope_type: str,
        scope_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> QuotaUsage:
        """获取或创建配额使用记录"""
        result = await self.db.execute(
            select(QuotaUsage).where(
                and_(
                    QuotaUsage.quota_id == quota_id,
                    QuotaUsage.scope_type == scope_type,
                    QuotaUsage.scope_id == scope_id,
                    QuotaUsage.period_start == period_start,
                    QuotaUsage.period_end == period_end,
                )
            )
        )
        usage = result.scalar_one_or_none()

        if not usage:
            quota = await self.get_quota(quota_id)
            if not quota:
                raise ValueError(f"Quota {quota_id} not found")

            usage = QuotaUsage(
                id=str(hash(f"{quota_id}{scope_id}{period_start.isoformat()}"))[:36],
                quota_id=quota_id,
                scope_type=scope_type,
                scope_id=scope_id,
                period_start=period_start,
                period_end=period_end,
                used_value=0,
                limit_value=quota.limit_value,
                remaining_value=quota.limit_value,
                exceeded_value=0,
            )
            self.db.add(usage)
            await self.db.commit()
            await self.db.refresh(usage)

        return usage

    async def check_quota(
        self,
        scope_type: str,
        scope_id: str,
        resource_type: str,
        requested_amount: int = 1,
    ) -> Dict[str, Any]:
        """
        检查配额是否充足

        Returns:
            检查结果：{"allowed": bool, "quotas": [...], "reason": str}
        """
        # 获取所有适用的配额
        quotas = await self.list_quotas(
            scope_type=scope_type,
            scope_id=scope_id,
            is_active=True,
        )

        # 过滤出适用于该资源类型的配额
        applicable_quotas = [
            q for q in quotas
            if q.resource_type == resource_type or q.resource_type == "all"
        ]

        if not applicable_quotas:
            return {"allowed": True, "quotas": [], "reason": "No quota restrictions"}

        # 检查每个配额
        now = datetime.utcnow()
        for quota in applicable_quotas:
            period_start, period_end = self._calculate_period(now, quota.period_type, quota.reset_time)

            usage = await self.get_or_create_usage(
                quota_id=quota.id,
                scope_type=scope_type,
                scope_id=scope_id,
                period_start=period_start,
                period_end=period_end,
            )

            remaining = usage.remaining_value

            if remaining < requested_amount:
                # 配额不足
                if quota.over_limit_action == "reject":
                    await self._log_quota_check(
                        quota_id=quota.id,
                        scope_type=scope_type,
                        scope_id=scope_id,
                        resource_type=resource_type,
                        requested_amount=requested_amount,
                        is_allowed=False,
                        reject_reason="quota_exceeded",
                    )
                    return {
                        "allowed": False,
                        "quotas": [q.to_dict() for q in applicable_quotas],
                        "reason": f"Quota exceeded for {quota.name}",
                        "quota_name": quota.name,
                        "limit": quota.limit_value,
                        "used": usage.used_value,
                        "remaining": remaining,
                    }
                elif quota.over_limit_action == "log":
                    # 仅记录日志，允许使用
                    await self._log_quota_check(
                        quota_id=quota.id,
                        scope_type=scope_type,
                        scope_id=scope_id,
                        resource_type=resource_type,
                        requested_amount=requested_amount,
                        is_allowed=True,
                        reject_reason=None,
                    )

        return {
            "allowed": True,
            "quotas": [q.to_dict() for q in applicable_quotas],
            "reason": "All quotas OK",
        }

    async def update_quota_usage(
        self,
        scope_type: str,
        scope_id: str,
        resource_type: str,
        used_amount: int,
    ) -> Dict[str, Any]:
        """更新配额使用量"""
        quotas = await self.list_quotas(
            scope_type=scope_type,
            scope_id=scope_id,
            is_active=True,
        )

        applicable_quotas = [
            q for q in quotas
            if q.resource_type == resource_type or q.resource_type == "all"
        ]

        now = datetime.utcnow()
        updates = []

        for quota in applicable_quotas:
            period_start, period_end = self._calculate_period(now, quota.period_type, quota.reset_time)

            usage = await self.get_or_create_usage(
                quota_id=quota.id,
                scope_type=scope_type,
                scope_id=scope_id,
                period_start=period_start,
                period_end=period_end,
            )

            # 更新使用量
            old_remaining = usage.remaining_value
            usage.used_value += used_amount
            usage.remaining_value = max(0, usage.limit_value - usage.used_value)

            if usage.used_value > usage.limit_value:
                usage.exceeded_value += used_amount

            updates.append({
                "quota_name": quota.name,
                "old_remaining": old_remaining,
                "new_remaining": usage.remaining_value,
                "exceeded": usage.exceeded_value > 0,
            })

        await self.db.commit()

        return {
            "success": True,
            "updates": updates,
        }

    def _calculate_period(
        self,
        now: datetime,
        period_type: str,
        reset_time: Optional[str],
    ) -> tuple:
        """计算周期起止时间"""
        if period_type == "hourly":
            period_start = now.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
        elif period_type == "daily":
            if reset_time:
                hour, minute = map(int, reset_time.split(":"))
                period_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if period_start > now:
                    period_start -= timedelta(days=1)
            else:
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif period_type == "weekly":
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(weeks=1)
        elif period_type == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start > now:
                period_start -= timedelta(days=1)
            next_month = period_start.month + 1
            next_year = period_start.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            period_end = period_start.replace(year=next_year, month=next_month)
        else:  # none or custom
            period_start = now
            period_end = now + timedelta(days=365)  # 默认一年

        return period_start, period_end

    async def _log_quota_check(
        self,
        quota_id: str,
        scope_type: str,
        scope_id: str,
        resource_type: str,
        requested_amount: int,
        is_allowed: bool,
        reject_reason: Optional[str],
    ):
        """记录配额检查日志"""
        log = QuotaCheckLog(
            id=str(hash(f"{quota_id}{scope_id}{datetime.utcnow().isoformat()}"))[:36],
            quota_id=quota_id,
            scope_type=scope_type,
            scope_id=scope_id,
            check_type="pre_check",
            resource_type=resource_type,
            requested_amount=requested_amount,
            is_allowed=is_allowed,
            reject_reason=reject_reason,
        )
        self.db.add(log)
        await self.db.commit()

    async def get_usage_stats(
        self,
        scope_type: str,
        scope_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """获取配额使用统计"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        result = await self.db.execute(
            select(
                QuotaUsage.quota_id,
                func.sum(QuotaUsage.used_value).label("total_used"),
                func.avg(QuotaUsage.used_value).label("avg_used"),
                func.max(QuotaUsage.exceeded_value).label("max_exceeded"),
            )
            .where(QuotaUsage.scope_type == scope_type)
            .where(QuotaUsage.scope_id == scope_id)
            .where(QuotaUsage.period_start >= start_date)
            .group_by(QuotaUsage.quota_id)
        )

        stats = []
        for row in result.fetchall():
            quota = await self.get_quota(row.quota_id)
            stats.append({
                "quota_id": row.quota_id,
                "quota_name": quota.name if quota else "Unknown",
                "total_used": row.total_used or 0,
                "avg_used": float(row.avg_used) if row.avg_used else 0,
                "max_exceeded": row.max_exceeded or 0,
            })

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "days": days,
            "stats": stats,
        }
