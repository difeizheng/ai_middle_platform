"""
Skills 市场 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.skill import Skill, SkillCategory, SkillVersion, SkillInstallation
from app.services.skills import get_registry, BaseSkill
from app.api.middleware import rate_limit

router = APIRouter()


# ========== Skill 分类管理 ==========

@router.get("/categories")
async def list_skill_categories(
    parent_id: Optional[str] = Query(None, description="父分类 ID"),
    current_user: User = Depends(get_current_user),
):
    """获取 Skill 分类列表"""
    # 暂时返回静态分类数据
    # 实际应该从数据库读取
    categories = [
        {"id": "analytics", "name": "数据分析", "description": "数据分析与统计", "parent_id": None},
        {"id": "document", "name": "文档处理", "description": "文档生成与解析", "parent_id": None},
        {"id": "development", "name": "开发工具", "description": "代码相关工具", "parent_id": None},
        {"id": "communication", "name": "通信通知", "description": "消息通知服务", "parent_id": None},
        {"id": "integration", "name": "系统集成", "description": "外部系统集成", "parent_id": None},
        {"id": "ai_service", "name": "AI 服务", "description": "AI 模型调用", "parent_id": None},
    ]

    if parent_id:
        categories = [c for c in categories if c.get("parent_id") == parent_id]

    return {
        "success": True,
        "data": categories,
    }


@router.post("/categories")
async def create_skill_category(
    name: str = Body(..., description="分类名称"),
    description: str = Body(None, description="分类描述"),
    parent_id: str = Body(None, description="父分类 ID"),
    icon: str = Body(None, description="分类图标"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 Skill 分类"""
    # 检查名称是否已存在
    result = await db.execute(
        select(SkillCategory).where(SkillCategory.name == name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分类名称已存在：{name}",
        )

    category = SkillCategory(
        name=name,
        description=description,
        parent_id=parent_id,
        icon=icon,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return {
        "success": True,
        "data": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "parent_id": category.parent_id,
        },
    }


# ========== Skill 管理 ==========

@router.get("/skills")
async def list_skills(
    category_id: Optional[str] = Query(None, description="分类 ID"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    tags: Optional[str] = Query(None, description="标签过滤（逗号分隔）"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skills 列表"""
    # 构建查询
    query = select(Skill)

    if category_id:
        query = query.where(Skill.category_id == category_id)
    if is_public is not None:
        query = query.where(Skill.is_public == is_public)
    if search:
        query = query.where(Skill.name.ilike(f"%{search}%"))

    # 执行查询
    result = await db.execute(query.offset(offset).limit(limit))
    skills = result.scalars().all()

    # 获取总数
    count_query = select(func.count()).select_from(Skill)
    if category_id:
        count_query = count_query.where(Skill.category_id == category_id)
    if is_public is not None:
        count_query = count_query.where(Skill.is_public == is_public)
    if search:
        count_query = count_query.where(Skill.name.ilike(f"%{search}%"))

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "success": True,
        "data": [skill.to_dict() for skill in skills],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/skills/registry")
async def list_registry_skills(
    category: Optional[str] = Query(None, description="分类过滤"),
    current_user: User = Depends(get_current_user),
):
    """获取已注册的 Skills（运行中）"""
    registry = get_registry()
    skills = registry.list_skills(category)

    return {
        "success": True,
        "data": skills,
        "total": len(skills),
    }


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skill 详情"""
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill 不存在",
        )

    # 获取版本信息
    versions_result = await db.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.created_at.desc())
    )
    versions = versions_result.scalars().all()

    return {
        "success": True,
        "data": {
            **skill.to_dict(),
            "versions": [
                {
                    "version": v.version,
                    "changelog": v.changelog,
                    "is_current": v.is_current,
                    "is_deprecated": v.is_deprecated,
                }
                for v in versions
            ],
        },
    }


@router.post("/skills")
async def create_skill(
    name: str = Body(..., description="Skill 名称"),
    display_name: str = Body(None, description="显示名称"),
    description: str = Body(..., description="Skill 描述"),
    category_id: str = Body(None, description="分类 ID"),
    version: str = Body("1.0.0", description="版本号"),
    author: str = Body(None, description="作者"),
    tags: List[str] = Body(default_factory=list, description="标签列表"),
    entry_point: str = Body(None, description="入口点（模块路径）"),
    implementation_type: str = Body("python", description="实现类型：python, http, mcp"),
    implementation_config: Dict[str, Any] = Body(default_factory=dict, description="实现配置"),
    config_schema: Dict[str, Any] = Body(default_factory=dict, description="配置 Schema"),
    input_schema: Dict[str, Any] = Body(default_factory=dict, description="输入 Schema"),
    output_schema: Dict[str, Any] = Body(default_factory=dict, description="输出 Schema"),
    is_public: bool = Body(False, description="是否公开"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 Skill"""
    # 检查名称是否已存在
    result = await db.execute(
        select(Skill).where(Skill.name == name)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill 名称已存在：{name}",
        )

    # 创建 Skill
    skill = Skill(
        name=name,
        display_name=display_name or name,
        description=description,
        category_id=category_id,
        version=version,
        author=author or current_user.username,
        tags=tags,
        entry_point=entry_point,
        config_schema=config_schema,
        input_schema=input_schema,
        output_schema=output_schema,
        is_public=is_public,
    )
    db.add(skill)

    # 创建版本记录
    skill_version = SkillVersion(
        skill_id=skill.id,  # 使用 skill.id 而不是 skill_id
        version=version,
        implementation_type=implementation_type,
        implementation_config=implementation_config,
        is_current=True,
    )
    db.add(skill_version)

    await db.commit()
    await db.refresh(skill)

    # 如果是 Python 实现，尝试注册到运行时注册表
    if implementation_type == "python" and entry_point:
        try:
            from ...services.skills import PythonSkill
            skill_instance = PythonSkill(entry_point, implementation_config)
            registry = get_registry()
            registry.register(name, skill_instance, {"category": category_id, "skill_id": skill.id})
        except Exception as e:
            # 注册失败不影响 Skill 创建，只记录日志
            logger = __import__("logging").getLogger(__name__)
            logger.warning(f"Failed to register skill {name} to runtime registry: {e}")

    return {
        "success": True,
        "data": skill.to_dict(),
    }


@router.put("/skills/{skill_id}")
async def update_skill(
    skill_id: str,
    display_name: Optional[str] = Body(None, description="显示名称"),
    description: Optional[str] = Body(None, description="Skill 描述"),
    tags: Optional[List[str]] = Body(None, description="标签列表"),
    is_public: Optional[bool] = Body(None, description="是否公开"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新 Skill"""
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill 不存在",
        )

    # 更新字段
    if display_name is not None:
        skill.display_name = display_name
    if description is not None:
        skill.description = description
    if tags is not None:
        skill.tags = tags
    if is_public is not None:
        skill.is_public = is_public

    await db.commit()
    await db.refresh(skill)

    return {
        "success": True,
        "data": skill.to_dict(),
    }


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 Skill"""
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill 不存在",
        )

    # 从注册表中移除
    registry = get_registry()
    registry.unregister(skill.name)

    # 删除数据库记录
    await db.delete(skill)
    await db.commit()

    return {
        "success": True,
        "message": "Skill 已删除",
    }


# ========== Skill 执行 ==========

@router.post("/skills/{skill_id}/execute")
@rate_limit(max_requests=50, window=60)
async def execute_skill(
    skill_id: str,
    params: Dict[str, Any] = Body(default_factory=dict, description="执行参数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """执行 Skill"""
    # 从数据库获取 Skill 信息
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        # 尝试从名称查找
        registry = get_registry()
        skill_instance = registry.get(skill_id)
        if not skill_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill 不存在",
            )
    else:
        # 从注册表获取实例
        registry = get_registry()
        skill_instance = registry.get(skill.name)
        if not skill_instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Skill {skill.name} 未注册到运行时",
            )

    try:
        # 执行 Skill
        result = await skill_instance.execute(params)

        # 更新调用次数
        skill.download_count += 1
        await db.commit()

        return {
            "success": True,
            "data": result,
            "skill_id": skill_id,
            "execution_count": skill_instance.execution_count,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败：{str(e)}",
        )


@router.get("/skills/{skill_id}/schema")
async def get_skill_schema(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skill 的 Schema 定义"""
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill 不存在",
        )

    return {
        "success": True,
        "data": {
            "config_schema": skill.config_schema,
            "input_schema": skill.input_schema,
            "output_schema": skill.output_schema,
        },
    }


# ========== Skill 安装管理 ==========

@router.get("/installations")
async def list_installations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的 Skill 安装列表"""
    result = await db.execute(
        select(SkillInstallation)
        .where(SkillInstallation.user_id == current_user.id)
        .where(SkillInstallation.is_active == True)
    )
    installations = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": inst.id,
                "skill_id": inst.skill_id,
                "config": inst.config,
                "installed_at": inst.installed_at.isoformat(),
            }
            for inst in installations
        ],
    }


@router.post("/installations")
async def install_skill(
    skill_id: str = Body(..., description="Skill ID"),
    config: Dict[str, Any] = Body(default_factory=dict, description="安装配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """安装 Skill"""
    # 检查 Skill 是否存在
    result = await db.execute(
        select(Skill).where(Skill.id == skill_id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill 不存在",
        )

    # 检查是否已安装
    existing = await db.execute(
        select(SkillInstallation)
        .where(SkillInstallation.skill_id == skill_id)
        .where(SkillInstallation.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该 Skill 已安装",
        )

    # 创建安装记录
    installation = SkillInstallation(
        skill_id=skill_id,
        user_id=current_user.id,
        config=config,
    )
    db.add(installation)

    # 如果是 Python 实现且未注册，尝试注册
    if skill.entry_point:
        registry = get_registry()
        if not registry.get(skill.name):
            try:
                from ...services.skills import PythonSkill
                skill_instance = PythonSkill(skill.entry_point, {**skill.config_schema, **config})
                registry.register(skill.name, skill_instance, {"category": skill.category_id})
            except Exception as e:
                pass  # 注册失败不影响安装

    await db.commit()
    await db.refresh(installation)

    return {
        "success": True,
        "data": {
            "id": installation.id,
            "skill_id": skill_id,
            "installed_at": installation.installed_at.isoformat(),
        },
    }


@router.delete("/installations/{installation_id}")
async def uninstall_skill(
    installation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """卸载 Skill"""
    result = await db.execute(
        select(SkillInstallation)
        .where(SkillInstallation.id == installation_id)
        .where(SkillInstallation.user_id == current_user.id)
    )
    installation = result.scalar_one_or_none()

    if not installation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="安装记录不存在",
        )

    await db.delete(installation)
    await db.commit()

    return {
        "success": True,
        "message": "Skill 已卸载",
    }


# ========== 统计信息 ==========

@router.get("/stats")
async def get_skills_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skills 市场统计信息"""
    # 数据库统计
    total_skills = await db.execute(select(func.count()).select_from(Skill))
    total_count = total_skills.scalar()

    public_skills = await db.execute(
        select(func.count()).select_from(Skill).where(Skill.is_public == True)
    )
    public_count = public_skills.scalar()

    # 分类统计
    category_stats = await db.execute(
        select(Skill.category_id, func.count())
        .group_by(Skill.category_id)
    )
    category_breakdown = {row[0]: row[1] for row in category_stats}

    # 运行时统计
    registry = get_registry()
    runtime_stats = registry.get_stats()

    return {
        "success": True,
        "data": {
            "total_skills": total_count,
            "public_skills": public_count,
            "category_breakdown": category_breakdown,
            "runtime": runtime_stats,
        },
    }
