"""
告警中心数据模型 - 余额、配额、成本预警
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, BigInteger, ForeignKey, Index
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class AlertChannel(Base):
    """
    告警通知渠道配置表
    """
    __tablename__ = "alert_channels"

    id = Column(Integer, primary_key=True, index=True)

    # 渠道信息
    name = Column(String(100), nullable=False, unique=True)  # 渠道名称
    channel_type = Column(String(50), nullable=False)  # 渠道类型：email/sms/webhook/slack
    display_name = Column(String(200))  # 显示名称

    # 渠道配置
    config = Column(JSON, default=dict)  # 渠道配置（如 SMTP 配置、Webhook URL 等）
    is_active = Column(Boolean, default=True)

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))


class AlertSubscription(Base):
    """
    告警订阅表 - 用户订阅的告警类型
    """
    __tablename__ = "alert_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # 订阅信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # 告警类型：balance/quota/cost
    resource_type = Column(String(50))  # 资源类型：account/app/api_key
    resource_id = Column(String(100))  # 资源 ID（用户 ID/应用 ID/APIKey ID）

    # 通知配置
    channel_ids = Column(JSON, default=list)  # 通知渠道 ID 列表
    is_enabled = Column(Boolean, default=True)

    # 阈值配置（可覆盖全局配置）
    custom_threshold = Column(Float)  # 自定义阈值
    custom_severity = Column(String(20))  # 自定义严重级别

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_subscription_user_type", "user_id", "alert_type"),
    )


class WarningAlert(Base):
    """
    预警记录表 - 余额、配额、成本预警记录
    """
    __tablename__ = "warning_alerts"

    id = Column(BigInteger, primary_key=True, index=True)

    # 预警信息
    alert_type = Column(String(50), nullable=False, index=True)  # balance/quota/cost
    alert_subtype = Column(String(50))  # 子类型：low_balance/high_usage/over_budget

    # 资源信息
    resource_type = Column(String(50))  # 资源类型：account/app/api_key
    resource_id = Column(String(100), index=True)  # 资源 ID
    user_id = Column(Integer, ForeignKey("users.id"), index=True)  # 关联用户

    # 预警内容
    current_value = Column(Float)  # 当前值
    threshold_value = Column(Float)  # 阈值
    unit = Column(String(50))  # 单位：CNY/tokens/calls/percent

    # 严重级别
    severity = Column(String(20), default="warning")  # info/warning/error/critical

    # 状态
    status = Column(String(20), default="pending")  # pending/sent/acknowledged/resolved
    message = Column(Text)  # 预警消息

    # 通知信息
    notified_channels = Column(JSON, default=list)  # 已通知的渠道
    notified_at = Column(DateTime(timezone=True))  # 通知时间

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_alert_type_status", "alert_type", "status"),
        Index("idx_alert_resource", "resource_type", "resource_id"),
    )


class AlertTemplate(Base):
    """
    告警模板表
    """
    __tablename__ = "alert_templates"

    id = Column(Integer, primary_key=True, index=True)

    # 模板信息
    name = Column(String(200), nullable=False)
    template_type = Column(String(50), nullable=False)  # email/sms/webhook

    # 模板内容
    subject_template = Column(Text)  # 邮件主题模板
    content_template = Column(Text, nullable=False)  # 模板内容（支持 Jinja2 变量）

    # 适用告警类型
    alert_types = Column(JSON, default=list)  # 适用的告警类型列表

    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))
