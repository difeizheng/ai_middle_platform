"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class User(Base):
    """
    用户表
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)

    # 用户信息
    full_name = Column(String(100))
    phone = Column(String(20))
    department = Column(String(100))  # 部门

    # 角色和权限
    role = Column(String(20), default="user")  # admin, operator, developer, user
    permissions = Column(JSON, default=list)  # 权限列表

    # 状态
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"
