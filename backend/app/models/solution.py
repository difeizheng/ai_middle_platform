"""
行业解决方案数据模型
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class Solution(Base):
    """行业解决方案表"""
    __tablename__ = "solutions"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # 解决方案名称
    display_name = Column(String(200))  # 显示名称
    description = Column(Text)  # 解决方案描述
    industry = Column(String(100), index=True)  # 所属行业
    scenario = Column(String(200))  # 应用场景
    level = Column(String(50), default="standard")  # 方案级别：standard, advanced, enterprise
    status = Column(String(50), default="draft")  # 状态：draft, published, archived

    # 方案内容
    architecture = Column(Text)  # 架构图/描述（JSON 格式）
    components = Column(Text)  # 组件列表（JSON 格式）
    features = Column(Text)  # 功能特性（JSON 格式）
    deployment_guide = Column(Text)  # 部署指南
    config_template = Column(Text)  # 配置模板（JSON 格式）

    # 统计信息
    view_count = Column(Integer, default=0)  # 浏览次数
    install_count = Column(Integer, default=0)  # 安装次数
    rating = Column(Float, default=0.0)  # 评分
    rating_count = Column(Integer, default=0)  # 评分数量

    # 作者信息
    author_id = Column(String(36), ForeignKey("users.id"))  # 作者
    author_name = Column(String(100))  # 作者名称

    # 标签和分类
    tags = Column(Text)  # 标签列表（JSON 格式）
    category_id = Column(String(36), ForeignKey("solution_categories.id"))  # 分类

    is_public = Column(Boolean, default=False)  # 是否公开
    is_featured = Column(Boolean, default=False)  # 是否推荐
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "industry": self.industry,
            "scenario": self.scenario,
            "level": self.level,
            "status": self.status,
            "components": json.loads(self.components) if self.components else [],
            "features": json.loads(self.features) if self.features else [],
            "tags": json.loads(self.tags) if self.tags else [],
            "view_count": self.view_count,
            "install_count": self.install_count,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "author_name": self.author_name,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SolutionCategory(Base):
    """解决方案分类表"""
    __tablename__ = "solution_categories"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # 分类名称
    display_name = Column(String(200))  # 显示名称
    description = Column(Text)  # 分类描述
    icon = Column(String(500))  # 分类图标
    parent_id = Column(String(36), ForeignKey("solution_categories.id"))  # 父分类
    sort_order = Column(Integer, default=0)  # 排序
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SolutionCase(Base):
    """解决方案案例表"""
    __tablename__ = "solution_cases"

    id = Column(String(36), primary_key=True, index=True)
    solution_id = Column(String(36), ForeignKey("solutions.id"), nullable=False)
    title = Column(String(200), nullable=False)  # 案例标题
    customer_name = Column(String(200))  # 客户名称
    customer_logo = Column(String(500))  # 客户 Logo
    industry = Column(String(100))  # 客户行业
    challenge = Column(Text)  # 面临的挑战
    solution_overview = Column(Text)  # 解决方案概述
    implementation = Column(Text)  # 实施过程（JSON 格式）
    results = Column(Text)  # 实施效果（JSON 格式）
    testimonial = Column(Text)  # 客户评价
    is_featured = Column(Boolean, default=False)  # 是否推荐
    view_count = Column(Integer, default=0)  # 浏览次数
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "solution_id": self.solution_id,
            "title": self.title,
            "customer_name": self.customer_name,
            "customer_logo": self.customer_logo,
            "industry": self.industry,
            "challenge": self.challenge,
            "solution_overview": self.solution_overview,
            "implementation": json.loads(self.implementation) if self.implementation else {},
            "results": json.loads(self.results) if self.results else {},
            "testimonial": self.testimonial,
            "is_featured": self.is_featured,
            "view_count": self.view_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SolutionTemplate(Base):
    """解决方案模板表"""
    __tablename__ = "solution_templates"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 模板名称
    description = Column(Text)  # 模板描述
    template_type = Column(String(50))  # 模板类型：configuration, workflow, integration
    content = Column(Text, nullable=False)  # 模板内容（JSON 格式）
    variables = Column(Text)  # 变量定义（JSON 格式）
    version = Column(String(20), default="1.0.0")  # 版本号
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type,
            "content": json.loads(self.content) if self.content else {},
            "variables": json.loads(self.variables) if self.variables else {},
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
