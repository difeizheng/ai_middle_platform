"""
运营监控数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, BigInteger, Index, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class MonitorMetric(Base):
    """
    监控指标表

    存储系统运行指标数据
    """
    __tablename__ = "monitor_metrics"

    id = Column(BigInteger, primary_key=True, index=True)

    # 指标信息
    metric_name = Column(String(100), nullable=False, index=True)  # 指标名称
    metric_type = Column(String(50), nullable=False)  # 指标类型：counter, gauge, histogram

    # 维度标签
    labels = Column(JSON, default=dict)  # 标签（如 endpoint, method, service）

    # 指标值
    value = Column(Float, nullable=False)
    count = Column(BigInteger, default=1)  # 计数（用于直方图）
    sum_value = Column(Float)  # 总和（用于计算平均值）

    # 时间信息
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 索引 - 优化时间范围查询
    __table_args__ = (
        Index("idx_metric_name_ts", "metric_name", "timestamp"),
        Index("idx_metric_labels", "labels", postgresql_using="gin"),
    )


class SystemHealth(Base):
    """
    系统健康状态表

    记录各服务组件的健康状态
    """
    __tablename__ = "system_health"

    id = Column(Integer, primary_key=True, index=True)

    # 服务信息
    service_name = Column(String(100), nullable=False, index=True)
    service_type = Column(String(50))  # api, database, cache, queue, etc.

    # 健康状态
    status = Column(String(20), nullable=False)  # healthy, unhealthy, degraded
    latency_ms = Column(Float)  # 响应延迟
    error_rate = Column(Float)  # 错误率
    success_rate = Column(Float)  # 成功率

    # 详细信息
    details = Column(JSON, default=dict)
    message = Column(Text)  # 状态消息

    # 时间信息
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_health_service_ts", "service_name", "checked_at"),
    )


class AlertRule(Base):
    """
    告警规则表
    """
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)

    # 规则信息
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # 告警条件
    metric_name = Column(String(100), nullable=False)
    condition = Column(String(20), nullable=False)  # gt, lt, eq, ge, le
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=60)  # 持续时间触发

    # 通知配置
    notification_channels = Column(JSON, default=list)  # [email, webhook, slack]
    notification_config = Column(JSON, default=dict)

    # 状态
    is_active = Column(Boolean, default=True)
    severity = Column(String(20), default="warning")  # info, warning, error, critical

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))


class AlertHistory(Base):
    """
    告警历史表
    """
    __tablename__ = "alert_history"

    id = Column(BigInteger, primary_key=True, index=True)

    # 告警信息
    rule_id = Column(Integer, ForeignKey("alert_rules.id"))
    alert_name = Column(String(200))

    # 告警内容
    metric_value = Column(Float)
    threshold = Column(Float)
    message = Column(Text)
    severity = Column(String(20))

    # 状态
    status = Column(String(20), default="firing")  # firing, resolved, acknowledged
    acknowledged_by = Column(Integer, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # 时间信息
    fired_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 索引
    __table_args__ = (
        Index("idx_alert_status", "status", "fired_at"),
        Index("idx_alert_rule", "rule_id", "fired_at"),
    )


class DashboardConfig(Base):
    """
    仪表盘配置表

    用户自定义仪表盘布局
    """
    __tablename__ = "dashboard_configs"

    id = Column(Integer, primary_key=True, index=True)

    # 配置信息
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # 布局配置
    layout = Column(JSON, default=list)  # 仪表盘组件布局
    widgets = Column(JSON, default=list)  # 小组件配置

    # 权限
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ServiceDependency(Base):
    """
    服务依赖关系表
    """
    __tablename__ = "service_dependencies"

    id = Column(Integer, primary_key=True, index=True)

    # 服务信息
    service_name = Column(String(100), nullable=False)
    depends_on = Column(String(100), nullable=False)  # 依赖的服务

    # 依赖类型
    dependency_type = Column(String(50))  # required, optional
    protocol = Column(String(50))  # http, grpc, tcp, etc.

    # 状态
    last_check_status = Column(String(20))
    last_check_at = Column(DateTime(timezone=True))

    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_dep_service", "service_name", "depends_on", unique=True),
    )
