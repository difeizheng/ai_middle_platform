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
from app.models.skill import Skill, SkillCategory, SkillVersion, SkillInstallation, SkillReview, SkillRating
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


# ========== Skill 评分和评论 ==========

@router.get("/skills/{skill_id}/reviews")
async def get_skill_reviews(
    skill_id: str,
    sort_by: str = Query("created_at", description="排序字段：created_at, rating"),
    order: str = Query("desc", description="排序方向：asc, desc"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skill 的评论列表"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 查询评论
    query = select(SkillReview).where(
        SkillReview.skill_id == skill_id,
        SkillReview.is_visible == True
    )

    # 排序
    if sort_by == "rating":
        query = query.order_by(SkillReview.rating.desc() if order == "desc" else SkillReview.rating.asc())
    else:
        query = query.order_by(SkillReview.created_at.desc() if order == "desc" else SkillReview.created_at.asc())

    query = query.limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    return {
        "success": True,
        "data": {
            "skill_id": skill_id,
            "reviews": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "rating": r.rating,
                    "title": r.title,
                    "content": r.content,
                    "helpful_count": r.helpful_count,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reviews
            ],
            "average_rating": skill.rating,
            "total_reviews": skill.rating_count,
        },
    }


@router.post("/skills/{skill_id}/reviews")
async def create_skill_review(
    skill_id: str,
    rating: int = Body(..., ge=1, le=5, description="评分 (1-5)"),
    title: str = Body(None, description="评论标题"),
    content: str = Body(None, description="评论内容"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 Skill 评论"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 检查是否已安装
    installation = await db.execute(
        select(SkillInstallation)
        .where(SkillInstallation.skill_id == skill_id)
        .where(SkillInstallation.user_id == current_user.id)
    )
    is_installed = installation.scalar_one_or_none() is not None

    # 检查是否已评论
    existing_review = await db.execute(
        select(SkillReview)
        .where(SkillReview.skill_id == skill_id)
        .where(SkillReview.user_id == current_user.id)
    )
    if existing_review.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经评论过该 Skill",
        )

    # 创建评论
    review = SkillReview(
        skill_id=skill_id,
        user_id=current_user.id,
        rating=rating,
        title=title,
        content=content,
        is_verified_purchase=is_installed,
    )
    db.add(review)

    # 更新 Skill 评分
    await _update_skill_rating(db, skill)

    await db.commit()
    await db.refresh(review)

    return {
        "success": True,
        "data": {
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "content": review.content,
            "is_verified_purchase": review.is_verified_purchase,
        },
    }


@router.put("/reviews/{review_id}")
async def update_skill_review(
    review_id: str,
    rating: int = Body(..., ge=1, le=5, description="评分 (1-5)"),
    title: str = Body(None, description="评论标题"),
    content: str = Body(None, description="评论内容"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新 Skill 评论"""
    result = await db.execute(
        select(SkillReview)
        .where(SkillReview.id == review_id)
        .where(SkillReview.user_id == current_user.id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")

    # 更新字段
    review.rating = rating
    if title is not None:
        review.title = title
    if content is not None:
        review.content = content

    # 更新 Skill 评分
    await _update_skill_rating(db, review.skill)

    await db.commit()
    await db.refresh(review)

    return {
        "success": True,
        "data": {
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "content": review.content,
        },
    }


@router.delete("/reviews/{review_id}")
async def delete_skill_review(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 Skill 评论"""
    result = await db.execute(
        select(SkillReview)
        .where(SkillReview.id == review_id)
        .where(SkillReview.user_id == current_user.id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")

    skill_id = review.skill_id
    await db.delete(review)

    # 更新 Skill 评分
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if skill:
        await _update_skill_rating(db, skill)

    await db.commit()

    return {
        "success": True,
        "message": "评论已删除",
    }


@router.post("/reviews/{review_id}/helpful")
async def mark_review_helpful(
    review_id: str,
    helpful: bool = Body(..., description="是否有用"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记评论是否有用"""
    result = await db.execute(select(SkillReview).where(SkillReview.id == review_id))
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")

    if helpful:
        review.helpful_count += 1
    else:
        review.not_helpful_count += 1

    await db.commit()

    return {
        "success": True,
        "data": {
            "helpful_count": review.helpful_count,
            "not_helpful_count": review.not_helpful_count,
        },
    }


@router.get("/skills/{skill_id}/rating")
async def get_skill_rating(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skill 评分详情"""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 获取评分分布
    rating_distribution = await db.execute(
        select(SkillRating.rating, func.count())
        .where(SkillRating.skill_id == skill_id)
        .group_by(SkillRating.rating)
    )
    distribution = {row[0]: row[1] for row in rating_distribution}

    return {
        "success": True,
        "data": {
            "skill_id": skill_id,
            "average_rating": skill.rating,
            "total_ratings": skill.rating_count,
            "distribution": {
                "5": distribution.get(5, 0),
                "4": distribution.get(4, 0),
                "3": distribution.get(3, 0),
                "2": distribution.get(2, 0),
                "1": distribution.get(1, 0),
            },
        },
    }


@router.post("/skills/{skill_id}/rating")
async def rate_skill(
    skill_id: str,
    rating: int = Body(..., ge=1, le=5, description="评分 (1-5)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对 Skill 进行评分"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 检查是否已评分
    existing = await db.execute(
        select(SkillRating)
        .where(SkillRating.skill_id == skill_id)
        .where(SkillRating.user_id == current_user.id)
    )
    existing_rating = existing.scalar_one_or_none()

    if existing_rating:
        # 更新评分
        existing_rating.rating = rating
    else:
        # 创建新评分
        skill_rating = SkillRating(
            skill_id=skill_id,
            user_id=current_user.id,
            rating=rating,
        )
        db.add(skill_rating)

    # 更新 Skill 评分
    await _update_skill_rating(db, skill)

    await db.commit()

    return {
        "success": True,
        "data": {
            "skill_id": skill_id,
            "rating": rating,
            "average_rating": skill.rating,
        },
    }


async def _update_skill_rating(db: AsyncSession, skill: Skill):
    """更新 Skill 的平均评分"""
    result = await db.execute(
        select(func.avg(SkillRating.rating), func.count(SkillRating.id))
        .where(SkillRating.skill_id == skill.id)
    )
    avg_rating, count = result.first()

    skill.rating = float(avg_rating) if avg_rating else 0.0
    skill.rating_count = count or 0
    await db.commit()


# ========== Skill 版本管理 ==========

@router.get("/skills/{skill_id}/versions")
async def get_skill_versions(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Skill 的所有版本"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

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
            "skill_id": skill_id,
            "current_version": skill.version,
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "changelog": v.changelog,
                    "is_current": v.is_current,
                    "is_deprecated": v.is_deprecated,
                    "implementation_type": v.implementation_type,
                    "created_at": v.created_at.isoformat(),
                }
                for v in versions
            ],
        },
    }


@router.post("/skills/{skill_id}/versions")
async def create_skill_version(
    skill_id: str,
    version: str = Body(..., description="版本号"),
    changelog: str = Body(None, description="变更日志"),
    implementation_type: str = Body("python", description="实现类型：python, http, mcp"),
    implementation_config: Dict[str, Any] = Body(default_factory=dict, description="实现配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的 Skill 版本"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 检查版本号是否已存在
    existing = await db.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id)
        .where(SkillVersion.version == version)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"版本号 {version} 已存在",
        )

    # 将当前版本设置为非当前
    await db.execute(
        SkillVersion.__table__
        .update()
        .where(SkillVersion.skill_id == skill_id)
        .where(SkillVersion.is_current == True)
        .values(is_current=False)
    )

    # 创建新版本
    skill_version = SkillVersion(
        skill_id=skill_id,
        version=version,
        changelog=changelog,
        implementation_type=implementation_type,
        implementation_config=implementation_config,
        is_current=True,
    )
    db.add(skill_version)

    # 更新 Skill 的版本号
    skill.version = version
    skill.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(skill_version)

    return {
        "success": True,
        "data": {
            "id": skill_version.id,
            "version": skill_version.version,
            "changelog": skill_version.changelog,
            "is_current": skill_version.is_current,
        },
    }


@router.post("/skills/{skill_id}/rollback")
async def rollback_skill_version(
    skill_id: str,
    target_version: str = Body(..., description="目标版本号"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """回滚 Skill 到指定版本"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 检查目标版本是否存在
    version_result = await db.execute(
        select(SkillVersion)
        .where(SkillVersion.skill_id == skill_id)
        .where(SkillVersion.version == target_version)
    )
    target_version_obj = version_result.scalar_one_or_none()

    if not target_version_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"版本 {target_version} 不存在",
        )

    if target_version_obj.is_deprecated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"版本 {target_version} 已被废弃，无法回滚",
        )

    # 将当前版本设置为非当前
    await db.execute(
        SkillVersion.__table__
        .update()
        .where(SkillVersion.skill_id == skill_id)
        .where(SkillVersion.is_current == True)
        .values(is_current=False)
    )

    # 将目标版本设置为当前
    target_version_obj.is_current = True
    target_version_obj.updated_at = datetime.utcnow()

    # 更新 Skill 的版本号
    skill.version = target_version
    skill.updated_at = datetime.utcnow()

    # 如果目标版本有不同的配置，更新 Skill
    if target_version_obj.implementation_config:
        skill.config_schema = target_version_obj.implementation_config.get("config_schema", skill.config_schema)
        skill.input_schema = target_version_obj.implementation_config.get("input_schema", skill.input_schema)
        skill.output_schema = target_version_obj.implementation_config.get("output_schema", skill.output_schema)

    await db.commit()

    return {
        "success": True,
        "data": {
            "skill_id": skill_id,
            "previous_version": skill.version,
            "current_version": target_version,
            "message": f"已回滚到版本 {target_version}",
        },
    }


@router.delete("/skills/{skill_id}/versions/{version_id}")
async def delete_skill_version(
    skill_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除/废弃 Skill 版本"""
    # 检查 Skill 是否存在
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill 不存在")

    # 检查版本是否存在
    version_result = await db.execute(
        select(SkillVersion).where(SkillVersion.id == version_id)
    )
    version_obj = version_result.scalar_one_or_none()

    if not version_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版本不存在")

    # 不能删除当前版本
    if version_obj.is_current:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前版本，请先切换到其他版本",
        )

    # 标记为废弃
    version_obj.is_deprecated = True
    await db.commit()

    return {
        "success": True,
        "message": f"版本 {version_obj.version} 已废弃",
    }
