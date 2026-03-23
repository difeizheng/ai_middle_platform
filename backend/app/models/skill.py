"""
Skills 市场数据模型
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, Float, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_skill_id() -> str:
    """生成 Skill ID"""
    return f"skill_{uuid.uuid4().hex[:12]}"


class SkillCategory(Base):
    """Skill 分类表"""
    __tablename__ = "skill_categories"

    id = Column(String(32), primary_key=True, default=lambda: f"cat_{uuid.uuid4().hex[:8]}")
    name = Column(String(64), nullable=False, unique=True, comment="分类名称")
    description = Column(Text, comment="分类描述")
    parent_id = Column(String(32), ForeignKey("skill_categories.id"), comment="父分类 ID")
    icon = Column(String(256), comment="分类图标")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系
    children = relationship("SkillCategory", remote_side=[id], backref="parent")
    skills = relationship("Skill", back_populates="category")


class Skill(Base):
    """
    Skill 定义表

    Skill 是可复用的能力单元，类似 MCP 连接器但更面向业务场景
    每个 Skill 可以有多个版本
    """
    __tablename__ = "skills"

    id = Column(String(32), primary_key=True, default=generate_skill_id)
    name = Column(String(128), nullable=False, comment="Skill 名称")
    display_name = Column(String(128), comment="显示名称")
    description = Column(Text, comment="Skill 描述")
    category_id = Column(String(32), ForeignKey("skill_categories.id"), comment="分类 ID")
    version = Column(String(32), default="1.0.0", comment="版本号")
    author = Column(String(64), comment="作者")
    email = Column(String(128), comment="联系邮箱")
    repository = Column(String(256), comment="代码仓库地址")
    license = Column(String(64), default="MIT", comment="许可证")
    tags = Column(JSON, default=list, comment="标签列表")

    # Skill 配置
    entry_point = Column(String(256), comment="入口点（模块路径或 URL）")
    config_schema = Column(JSON, default=dict, comment="配置 Schema（JSON Schema 格式）")
    input_schema = Column(JSON, default=dict, comment="输入 Schema")
    output_schema = Column(JSON, default=dict, comment="输出 Schema")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_public = Column(Boolean, default=False, comment="是否公开")
    is_verified = Column(Boolean, default=False, comment="是否已验证")
    download_count = Column(Integer, default=0, comment="下载/调用次数")
    rating = Column(Float, default=0.0, comment="评分")
    rating_count = Column(Integer, default=0, comment="评分数量")

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    published_at = Column(DateTime, comment="发布时间")

    # 关系
    category = relationship("SkillCategory", back_populates="skills")
    versions = relationship("SkillVersion", back_populates="skill", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("idx_skills_category", "category_id"),
        Index("idx_skills_name", "name"),
        Index("idx_skills_is_public", "is_public"),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category_id": self.category_id,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "is_active": self.is_active,
            "is_public": self.is_public,
            "is_verified": self.is_verified,
            "download_count": self.download_count,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SkillVersion(Base):
    """
    Skill 版本表

    支持一个 Skill 有多个版本
    """
    __tablename__ = "skill_versions"

    id = Column(String(32), primary_key=True, default=lambda: f"sv_{uuid.uuid4().hex[:8]}")
    skill_id = Column(String(32), ForeignKey("skills.id"), nullable=False, comment="Skill ID")
    version = Column(String(32), nullable=False, comment="版本号")
    changelog = Column(Text, comment="变更日志")

    # 实现细节
    implementation_type = Column(String(32), default="python", comment="实现类型：python, http, mcp")
    implementation_config = Column(JSON, default=dict, comment="实现配置")

    # 状态
    is_current = Column(Boolean, default=False, comment="是否是当前版本")
    is_deprecated = Column(Boolean, default=False, comment="是否已废弃")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系
    skill = relationship("Skill", back_populates="versions")

    # 索引
    __table_args__ = (
        Index("idx_skill_versions_skill_id", "skill_id"),
        Index("idx_skill_versions_version", "version"),
    )


class SkillInstallation(Base):
    """
    Skill 安装记录表

    记录哪些应用/用户安装了某个 Skill
    """
    __tablename__ = "skill_installations"

    id = Column(String(32), primary_key=True, default=lambda: f"si_{uuid.uuid4().hex[:8]}")
    skill_id = Column(String(32), ForeignKey("skills.id"), nullable=False, comment="Skill ID")
    user_id = Column(String(32), ForeignKey("users.id"), comment="用户 ID")
    app_id = Column(String(32), ForeignKey("applications.id"), comment="应用 ID")

    # 配置
    config = Column(JSON, default=dict, comment="用户自定义配置")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 元数据
    installed_at = Column(DateTime, default=datetime.utcnow, comment="安装时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系
    skill = relationship("Skill")

    # 索引
    __table_args__ = (
        Index("idx_skill_installations_user", "user_id"),
        Index("idx_skill_installations_app", "app_id"),
        Index("idx_skill_installations_skill", "skill_id"),
    )
