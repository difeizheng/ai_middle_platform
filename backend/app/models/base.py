"""
数据模型基类
"""
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

# 创建基类
Base = declarative_base()


class TimestampMixin:
    """时间戳混合类，提供 created_at 和 updated_at 字段"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
