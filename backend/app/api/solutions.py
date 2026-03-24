"""
行业解决方案 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.solution import Solution, SolutionCategory, SolutionCase, SolutionTemplate

router = APIRouter()


# ========== 解决方案分类 ==========

@router.get("/solutions/categories")
async def list_solution_categories(
    parent_id: Optional[str] = Query(None, description="父分类 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解决方案分类列表"""
    query = select(SolutionCategory).where(SolutionCategory.is_active == True)

    if parent_id:
        query = query.where(SolutionCategory.parent_id == parent_id)
    else:
        # 只返回顶级分类
        query = query.where(SolutionCategory.parent_id.is_(None))

    query = query.order_by(SolutionCategory.sort_order)
    result = await db.execute(query)
    categories = result.scalars().all()

    return {
        "success": True,
        "data": [c.to_dict() for c in categories],
    }


@router.post("/solutions/categories")
async def create_solution_category(
    name: str = Body(..., description="分类名称"),
    display_name: str = Body(None, description="显示名称"),
    description: str = Body(None, description="分类描述"),
    icon: str = Body(None, description="分类图标"),
    parent_id: str = Body(None, description="父分类 ID"),
    sort_order: int = Body(0, description="排序"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建解决方案分类"""
    # 检查名称是否已存在
    result = await db.execute(
        select(SolutionCategory).where(SolutionCategory.name == name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分类名称已存在：{name}",
        )

    category = SolutionCategory(
        id=str(uuid.uuid4()),
        name=name,
        display_name=display_name or name,
        description=description,
        icon=icon,
        parent_id=parent_id,
        sort_order=sort_order,
        is_active=True,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return {
        "success": True,
        "data": category.to_dict(),
    }


# ========== 解决方案管理 ==========

@router.get("/solutions")
async def list_solutions(
    industry: Optional[str] = Query(None, description="所属行业"),
    scenario: Optional[str] = Query(None, description="应用场景"),
    level: Optional[str] = Query(None, description="方案级别"),
    category_id: Optional[str] = Query(None, description="分类 ID"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解决方案列表"""
    query = select(Solution).where(Solution.status == "published")

    if industry:
        query = query.where(Solution.industry == industry)
    if scenario:
        query = query.where(Solution.scenario == scenario)
    if level:
        query = query.where(Solution.level == level)
    if category_id:
        query = query.where(Solution.category_id == category_id)
    if is_public is not None:
        query = query.where(Solution.is_public == is_public)
    if search:
        query = query.where(
            (Solution.name.ilike(f"%{search}%")) |
            (Solution.description.ilike(f"%{search}%"))
        )

    # 总数查询
    count_query = select(func.count()).select_from(Solution)
    if industry:
        count_query = count_query.where(Solution.industry == industry)
    if scenario:
        count_query = count_query.where(Solution.scenario == scenario)
    if level:
        count_query = count_query.where(Solution.level == level)
    if category_id:
        count_query = count_query.where(Solution.category_id == category_id)
    if is_public is not None:
        count_query = count_query.where(Solution.is_public == is_public)
    if search:
        count_query = count_query.where(
            (Solution.name.ilike(f"%{search}%")) |
            (Solution.description.ilike(f"%{search}%"))
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 执行查询
    result = await db.execute(query.offset(offset).limit(limit))
    solutions = result.scalars().all()

    # 增加浏览次数
    for solution in solutions:
        solution.view_count += 1
    await db.commit()

    return {
        "success": True,
        "data": [s.to_dict() for s in solutions],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/solutions/{solution_id}")
async def get_solution(
    solution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解决方案详情"""
    result = await db.execute(
        select(Solution).where(Solution.id == solution_id)
    )
    solution = result.scalar_one_or_none()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解决方案不存在",
        )

    # 增加浏览次数
    solution.view_count += 1
    await db.commit()
    await db.refresh(solution)

    return {
        "success": True,
        "data": solution.to_dict(),
    }


@router.post("/solutions")
async def create_solution(
    name: str = Body(..., description="解决方案名称"),
    display_name: str = Body(None, description="显示名称"),
    description: str = Body(..., description="解决方案描述"),
    industry: str = Body(..., description="所属行业"),
    scenario: str = Body(None, description="应用场景"),
    level: str = Body("standard", description="方案级别"),
    architecture: Dict[str, Any] = Body(default_factory=dict, description="架构描述"),
    components: List[Dict[str, Any]] = Body(default_factory=list, description="组件列表"),
    features: List[str] = Body(default_factory=list, description="功能特性"),
    deployment_guide: str = Body(None, description="部署指南"),
    config_template: Dict[str, Any] = Body(default_factory=dict, description="配置模板"),
    tags: List[str] = Body(default_factory=list, description="标签列表"),
    category_id: str = Body(None, description="分类 ID"),
    is_public: bool = Body(False, description="是否公开"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建解决方案"""
    # 检查名称是否已存在
    result = await db.execute(
        select(Solution).where(Solution.name == name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解决方案名称已存在：{name}",
        )

    solution = Solution(
        id=str(uuid.uuid4()),
        name=name,
        display_name=display_name or name,
        description=description,
        industry=industry,
        scenario=scenario,
        level=level,
        status="draft",
        architecture=str(architecture),
        components=str(components),
        features=str(features),
        deployment_guide=deployment_guide,
        config_template=str(config_template),
        tags=str(tags),
        category_id=category_id,
        author_id=current_user.id,
        author_name=current_user.username,
        is_public=is_public,
    )
    db.add(solution)
    await db.commit()
    await db.refresh(solution)

    return {
        "success": True,
        "data": solution.to_dict(),
    }


@router.put("/solutions/{solution_id}")
async def update_solution(
    solution_id: str,
    display_name: Optional[str] = Body(None, description="显示名称"),
    description: Optional[str] = Body(None, description="解决方案描述"),
    level: Optional[str] = Body(None, description="方案级别"),
    architecture: Optional[Dict[str, Any]] = Body(None, description="架构描述"),
    components: Optional[List[Dict[str, Any]]] = Body(None, description="组件列表"),
    features: Optional[List[str]] = Body(None, description="功能特性"),
    deployment_guide: Optional[str] = Body(None, description="部署指南"),
    config_template: Optional[Dict[str, Any]] = Body(None, description="配置模板"),
    tags: Optional[List[str]] = Body(None, description="标签列表"),
    is_public: Optional[bool] = Body(None, description="是否公开"),
    is_featured: Optional[bool] = Body(None, description="是否推荐"),
    status: Optional[str] = Body(None, description="状态"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新解决方案"""
    result = await db.execute(
        select(Solution).where(Solution.id == solution_id)
    )
    solution = result.scalar_one_or_none()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解决方案不存在",
        )

    # 更新字段
    if display_name is not None:
        solution.display_name = display_name
    if description is not None:
        solution.description = description
    if level is not None:
        solution.level = level
    if architecture is not None:
        solution.architecture = str(architecture)
    if components is not None:
        solution.components = str(components)
    if features is not None:
        solution.features = str(features)
    if deployment_guide is not None:
        solution.deployment_guide = deployment_guide
    if config_template is not None:
        solution.config_template = str(config_template)
    if tags is not None:
        solution.tags = str(tags)
    if is_public is not None:
        solution.is_public = is_public
    if is_featured is not None:
        solution.is_featured = is_featured
    if status is not None:
        solution.status = status

    await db.commit()
    await db.refresh(solution)

    return {
        "success": True,
        "data": solution.to_dict(),
    }


@router.delete("/solutions/{solution_id}")
async def delete_solution(
    solution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除解决方案"""
    result = await db.execute(
        select(Solution).where(Solution.id == solution_id)
    )
    solution = result.scalar_one_or_none()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解决方案不存在",
        )

    await db.delete(solution)
    await db.commit()

    return {
        "success": True,
        "message": "解决方案已删除",
    }


@router.post("/solutions/{solution_id}/publish")
async def publish_solution(
    solution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布解决方案"""
    result = await db.execute(
        select(Solution).where(Solution.id == solution_id)
    )
    solution = result.scalar_one_or_none()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解决方案不存在",
        )

    solution.status = "published"
    solution.is_public = True
    await db.commit()

    return {
        "success": True,
        "data": solution.to_dict(),
    }


# ========== 解决方案案例 ==========

@router.get("/solutions/{solution_id}/cases")
async def list_solution_cases(
    solution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解决方案案例列表"""
    result = await db.execute(
        select(Solution).where(Solution.id == solution_id)
    )
    solution = result.scalar_one_or_none()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解决方案不存在",
        )

    result = await db.execute(
        select(SolutionCase)
        .where(SolutionCase.solution_id == solution_id)
        .order_by(SolutionCase.is_featured.desc(), SolutionCase.view_count.desc())
    )
    cases = result.scalars().all()

    return {
        "success": True,
        "data": [c.to_dict() for c in cases],
    }


@router.post("/solutions/{solution_id}/cases")
async def create_solution_case(
    solution_id: str,
    title: str = Body(..., description="案例标题"),
    customer_name: str = Body(None, description="客户名称"),
    customer_logo: str = Body(None, description="客户 Logo"),
    industry: str = Body(None, description="客户行业"),
    challenge: str = Body(None, description="面临的挑战"),
    solution_overview: str = Body(None, description="解决方案概述"),
    implementation: Dict[str, Any] = Body(default_factory=dict, description="实施过程"),
    results: Dict[str, Any] = Body(default_factory=dict, description="实施效果"),
    testimonial: str = Body(None, description="客户评价"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建解决方案案例"""
    # 检查解决方案是否存在
    result = await db.execute(
        select(Solution).where(Solution.id == solution_id)
    )
    solution = result.scalar_one_or_none()

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="解决方案不存在",
        )

    case = SolutionCase(
        id=str(uuid.uuid4()),
        solution_id=solution_id,
        title=title,
        customer_name=customer_name,
        customer_logo=customer_logo,
        industry=industry,
        challenge=challenge,
        solution_overview=solution_overview,
        implementation=str(implementation),
        results=str(results),
        testimonial=testimonial,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    return {
        "success": True,
        "data": case.to_dict(),
    }


# ========== 解决方案模板 ==========

@router.get("/solutions/templates")
async def list_solution_templates(
    template_type: Optional[str] = Query(None, description="模板类型"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解决方案模板列表"""
    query = select(SolutionTemplate).where(SolutionTemplate.is_active == True)

    if template_type:
        query = query.where(SolutionTemplate.template_type == template_type)

    result = await db.execute(query)
    templates = result.scalars().all()

    return {
        "success": True,
        "data": [t.to_dict() for t in templates],
    }


@router.post("/solutions/templates")
async def create_solution_template(
    name: str = Body(..., description="模板名称"),
    description: str = Body(None, description="模板描述"),
    template_type: str = Body(None, description="模板类型"),
    content: Dict[str, Any] = Body(..., description="模板内容"),
    variables: Dict[str, Any] = Body(default_factory=dict, description="变量定义"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建解决方案模板"""
    template = SolutionTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        template_type=template_type,
        content=str(content),
        variables=str(variables),
        is_active=True,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "success": True,
        "data": template.to_dict(),
    }


# ========== 解决方案统计 ==========

@router.get("/solutions/stats")
async def get_solutions_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取解决方案统计信息"""
    # 总数统计
    total_result = await db.execute(
        select(func.count()).select_from(Solution)
        .where(Solution.status == "published")
    )
    total = total_result.scalar()

    # 行业分布
    industry_result = await db.execute(
        select(Solution.industry, func.count())
        .where(Solution.status == "published")
        .group_by(Solution.industry)
    )
    industry_breakdown = {row[0]: row[1] for row in industry_result}

    # 级别分布
    level_result = await db.execute(
        select(Solution.level, func.count())
        .where(Solution.status == "published")
        .group_by(Solution.level)
    )
    level_breakdown = {row[0]: row[1] for row in level_result}

    # 热门解决方案
    popular_result = await db.execute(
        select(Solution)
        .where(Solution.status == "published")
        .order_by(Solution.view_count.desc())
        .limit(5)
    )
    popular_solutions = [s.to_dict() for s in popular_result.scalars().all()]

    return {
        "success": True,
        "data": {
            "total": total,
            "industry_breakdown": industry_breakdown,
            "level_breakdown": level_breakdown,
            "popular_solutions": popular_solutions,
        },
    }
