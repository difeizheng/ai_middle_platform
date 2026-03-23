"""
应用和 API Key 相关模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class Application(Base):
    """
    应用表 - 接入 AI 中台的业务系统
    """
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 应用名称
    description = Column(Text)  # 应用描述

    # 所有者
    owner_id = Column(Integer, ForeignKey("users.id"))

    # 应用类型
    app_type = Column(String(50))  # web, mobile, api, internal

    # 状态
    is_active = Column(Boolean, default=True)

    # 配额配置
    quota_config = Column(JSON, default=dict)  # 配额配置
    rate_limit = Column(JSON, default=dict)  # 限流配置

    # 回调配置
    callback_url = Column(String(500))  # 回调 URL

    # 统计
    total_calls = Column(Integer, default=0)  # 总调用次数
    total_tokens = Column(Integer, default=0)  # 总 token 使用量

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Application {self.name}>"


class APIKey(Base):
    """
    API Key 表
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    # Key 信息
    key = Column(String(100), unique=True, nullable=False, index=True)  # API Key（哈希存储）
    key_prefix = Column(String(10))  # Key 前缀（用于显示）
    secret = Column(String(255))  # API Secret（加密存储）

    # 权限
    permissions = Column(JSON, default=list)  # 权限列表
    allowed_models = Column(JSON, default=list)  # 允许使用的模型
    allowed_ips = Column(JSON, default=list)  # 允许的 IP 白名单

    # 限流
    rate_limit_qps = Column(Integer, default=100)  # QPS 限制
    rate_limit_daily = Column(Integer, default=100000)  # 日调用量限制

    # 状态
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)

    # 时间
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间
    last_used_at = Column(DateTime(timezone=True), nullable=True)  # 最后使用时间

    # 统计
    total_calls = Column(Integer, default=0)
    today_calls = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<APIKey {self.key_prefix}>"
