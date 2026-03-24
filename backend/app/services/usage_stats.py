"""
使用量统计服务
提供全方位的使用量统计和分析功能
"""
from sqlalchemy import select, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from ..models.billing import BillingRecord, BillingStats, Account
from ..models.quota import QuotaUsage
from ..models.api_log import APILog

logger = logging.getLogger(__name__)


class UsageStatsService:
    """使用量统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_realtime_usage(
        self,
        scope_type: str,
        scope_id: str,
    ) -> Dict[str, Any]:
        """
        获取实时使用量

        返回当前的调用量、Token 使用量等实时数据
        """
        # 获取当前小时的统计
        now = datetime.utcnow()
        hour_start = now.replace(minute=0, second=0, microsecond=0)

        # 当前小时消费
        result = await self.db.execute(
            select(
                func.sum(BillingRecord.amount).label("current_hour_cost"),
                func.sum(BillingRecord.tokens_used).label("current_hour_tokens"),
                func.count(BillingRecord.id).label("current_hour_calls"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= hour_start)
        )
        row = result.first()

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "timestamp": now.isoformat(),
            "current_hour": {
                "cost": float(row[0] or 0),
                "tokens": row[1] or 0,
                "calls": row[2] or 0,
            },
        }

    async def get_usage_trend(
        self,
        scope_type: str,
        scope_id: str,
        days: int = 7,
        granularity: str = "day",  # hour/day/week/month
    ) -> Dict[str, Any]:
        """
        获取使用趋势

        Args:
            days: 统计天数
            granularity: 粒度：hour/day/week/month
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 根据粒度选择分组字段
        if granularity == "hour":
            date_trunc = extract("hour", BillingRecord.created_at)
        elif granularity == "day":
            date_trunc = func.date(BillingRecord.created_at)
        elif granularity == "month":
            date_trunc = func.date_trunc("month", BillingRecord.created_at)
        else:
            date_trunc = func.date_trunc("week", BillingRecord.created_at)

        result = await self.db.execute(
            select(
                date_trunc.label("period"),
                func.sum(BillingRecord.amount).label("total_cost"),
                func.sum(BillingRecord.tokens_used).label("total_tokens"),
                func.count(BillingRecord.id).label("total_calls"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= start_date)
            .group_by("period")
            .order_by("period")
        )

        trend_data = [
            {
                "period": row[0].isoformat() if row[0] else None,
                "total_cost": float(row[1]) if row[1] else 0,
                "total_tokens": row[2] or 0,
                "total_calls": row[3] or 0,
            }
            for row in result.fetchall()
        ]

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "days": days,
            "granularity": granularity,
            "trend": trend_data,
        }

    async def get_usage_by_dimension(
        self,
        scope_type: str,
        scope_id: str,
        dimension: str,  # model/resource_type/api_endpoint
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        按维度分析使用量

        Args:
            dimension: 分析维度：model/resource_type/api_endpoint
            days: 统计天数
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 根据维度选择分组字段
        if dimension == "model":
            # 从 extra_data 中解析模型名称
            group_field = func.json_extract_text(BillingRecord.extra_data, "$.model_name")
        elif dimension == "resource_type":
            group_field = BillingRecord.resource_type
        elif dimension == "api_endpoint":
            group_field = func.json_extract_text(BillingRecord.extra_data, "$.api_endpoint")
        else:
            raise ValueError(f"Unsupported dimension: {dimension}")

        result = await self.db.execute(
            select(
                group_field.label("dimension_value"),
                func.sum(BillingRecord.amount).label("total_cost"),
                func.sum(BillingRecord.tokens_used).label("total_tokens"),
                func.count(BillingRecord.id).label("total_calls"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= start_date)
            .group_by("dimension_value")
            .order_by(func.sum(BillingRecord.amount).desc())
        )

        breakdown = [
            {
                dimension: row[0] or "unknown",
                "total_cost": float(row[1]) if row[1] else 0,
                "total_tokens": row[2] or 0,
                "total_calls": row[3] or 0,
            }
            for row in result.fetchall()
        ]

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "dimension": dimension,
            "days": days,
            "breakdown": breakdown,
        }

    async def get_cost_analysis(
        self,
        scope_type: str,
        scope_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        成本分析

        分析资源消耗成本和使用效率
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 总成本
        total_result = await self.db.execute(
            select(
                func.sum(BillingRecord.amount).label("total_cost"),
                func.sum(BillingRecord.tokens_used).label("total_tokens"),
                func.count(BillingRecord.id).label("total_calls"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= start_date)
        )
        total_row = total_result.first()

        total_cost = float(total_row[0] or 0)
        total_tokens = total_row[1] or 0
        total_calls = total_row[2] or 0

        # 平均成本
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
        avg_cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0

        # 按资源类型分析成本
        resource_result = await self.db.execute(
            select(
                BillingRecord.resource_type,
                func.sum(BillingRecord.amount).label("cost"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= start_date)
            .group_by(BillingRecord.resource_type)
        )

        cost_by_resource = {
            row[0]: float(row[1]) if row[1] else 0
            for row in resource_result.fetchall()
        }

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "days": days,
            "summary": {
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "total_calls": total_calls,
                "avg_cost_per_call": avg_cost_per_call,
                "avg_cost_per_token": avg_cost_per_token,
            },
            "cost_by_resource": cost_by_resource,
        }

    async def get_prediction(
        self,
        scope_type: str,
        scope_id: str,
        predict_days: int = 7,
    ) -> Dict[str, Any]:
        """
        使用量预测

        基于历史数据预测未来用量
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)  # 使用过去 30 天数据

        # 获取过去 30 天的日均用量
        result = await self.db.execute(
            select(
                func.avg(
                    func.sum(BillingRecord.amount).over(
                        partition_by=func.date(BillingRecord.created_at)
                    )
                ).label("avg_daily_cost"),
                func.avg(
                    func.sum(BillingRecord.tokens_used).over(
                        partition_by=func.date(BillingRecord.created_at)
                    )
                ).label("avg_daily_tokens"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= start_date)
        )
        row = result.first()

        avg_daily_cost = float(row[0] or 0)
        avg_daily_tokens = row[1] or 0

        # 预测未来用量
        prediction = {
            "days": predict_days,
            "predicted_cost": avg_daily_cost * predict_days,
            "predicted_tokens": int(avg_daily_tokens * predict_days),
            "confidence": "medium",  # 简单预测，置信度中等
        }

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "prediction": prediction,
            "based_on_days": 30,
        }

    async def get_top_resources(
        self,
        scope_type: str,
        scope_id: str,
        days: int = 7,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        获取 TOP 资源使用排行
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 按模型排行
        model_result = await self.db.execute(
            select(
                func.json_extract_text(BillingRecord.extra_data, "$.model_name").label("model"),
                func.sum(BillingRecord.amount).label("total_cost"),
                func.sum(BillingRecord.tokens_used).label("total_tokens"),
                func.count(BillingRecord.id).label("total_calls"),
            )
            .where(BillingRecord.account_id.in_(
                select(Account.id).where(Account.user_id == scope_id)
            ))
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= start_date)
            .group_by("model")
            .order_by(func.sum(BillingRecord.amount).desc())
            .limit(limit)
        )

        top_models = [
            {
                "model": row[0] or "unknown",
                "total_cost": float(row[1]) if row[1] else 0,
                "total_tokens": row[2] or 0,
                "total_calls": row[3] or 0,
            }
            for row in model_result.fetchall()
        ]

        return {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "days": days,
            "top_models": top_models,
        }
