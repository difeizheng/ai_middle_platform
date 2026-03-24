"""
配额管理数据模型
"""
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey, Boolean, Text, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from .base import Base, TimestampMixin


class Quota(Base, TimestampMixin):
    """配额定义表"""
    __tablename__ = "quotas"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # 配额类型
    quota_type = Column(String(50), nullable=False)  # qps/daily_calls/token_usage/concurrent
    resource_type = Column(String(50), nullable=False)  # model_call/knowledge_base/agent/skill

    # 配额限制
    limit_value = Column(Integer, nullable=False)  # 限制值
    unit = Column(String(20))  # 单位：calls/tokens/second

    # 配额周期
    period_type = Column(String(20), default="daily")  # hourly/daily/weekly/monthly/none
    reset_time = Column(String(20))  # 重置时间，如 "00:00" 表示每天零点

    # 配额层级
    scope_type = Column(String(20), nullable=False)  # user/app/api_key
    scope_id = Column(String(36))  # 对应的 user_id/app_id/api_key_id

    # 继承关系
    parent_quota_id = Column(String(36), ForeignKey("quotas.id"))
    is_inherited = Column(Boolean, default=False)  # 是否从上级继承

    # 超额处理
    over_limit_action = Column(String(20), default="reject")  # reject/allow/log
    over_limit_rate = Column(DECIMAL(10, 4), default=1)  # 超额费率系数

    # 状态
    is_active = Column(Boolean, default=True)

    # 元数据
    extra_config = Column(Text, default='{}')  # JSON 格式额外配置

    # 关系
    parent = relationship("Quota", remote_side=[id], backref="children")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quota_type": self.quota_type,
            "resource_type": self.resource_type,
            "limit_value": self.limit_value,
            "unit": self.unit,
            "period_type": self.period_type,
            "reset_time": self.reset_time,
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "parent_quota_id": self.parent_quota_id,
            "is_inherited": self.is_inherited,
            "over_limit_action": self.over_limit_action,
            "over_limit_rate": float(self.over_limit_rate) if self.over_limit_rate else 1,
            "is_active": self.is_active,
            "extra_config": json.loads(self.extra_config) if self.extra_config else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QuotaUsage(Base, TimestampMixin):
    """配额使用量表"""
    __tablename__ = "quota_usage"

    id = Column(String(36), primary_key=True)
    quota_id = Column(String(36), ForeignKey("quotas.id"), nullable=False)
    scope_type = Column(String(20), nullable=False)  # user/app/api_key
    scope_id = Column(String(36), nullable=False)

    # 统计周期
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # 使用量
    used_value = Column(Integer, default=0)
    limit_value = Column(Integer, nullable=False)
    remaining_value = Column(Integer, default=0)

    # 超额记录
    exceeded_value = Column(Integer, default=0)

    # 元数据
    extra_data = Column(Text, default='{}')  # JSON 格式额外数据

    # 关系
    quota = relationship("Quota", backref="usages")

    def to_dict(self):
        return {
            "id": self.id,
            "quota_id": self.quota_id,
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "used_value": self.used_value,
            "limit_value": self.limit_value,
            "remaining_value": self.remaining_value,
            "exceeded_value": self.exceeded_value,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QuotaCheckLog(Base, TimestampMixin):
    """配额检查日志表"""
    __tablename__ = "quota_check_logs"

    id = Column(String(36), primary_key=True)
    quota_id = Column(String(36), ForeignKey("quotas.id"))
    scope_type = Column(String(20), nullable=False)
    scope_id = Column(String(36), nullable=False)

    # 检查详情
    check_type = Column(String(20), nullable=False)  # pre_check/post_update
    resource_type = Column(String(50))
    requested_amount = Column(Integer, default=1)

    # 检查结果
    is_allowed = Column(Boolean, nullable=False)
    reject_reason = Column(String(100))  # quota_exceeded/quota_not_found/other

    # 上下文
    context = Column(Text, default='{}')  # JSON 格式上下文

    # 关系
    quota = relationship("Quota", backref="check_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "quota_id": self.quota_id,
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "check_type": self.check_type,
            "resource_type": self.resource_type,
            "requested_amount": self.requested_amount,
            "is_allowed": self.is_allowed,
            "reject_reason": self.reject_reason,
            "context": json.loads(self.context) if self.context else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
