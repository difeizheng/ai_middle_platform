"""
合作伙伴计划 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.partner import Partner, PartnerApplication, PartnerBenefit, PartnerActivity

router = APIRouter()


# ========== 合作伙伴管理 ==========

@router.get("/partners")
async def list_partners(
    level: Optional[str] = Query(None, description="合作伙伴级别"),
    industry: Optional[str] = Query(None, description="所属行业"),
    is_verified: Optional[bool] = Query(None, description="是否已验证"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合作伙伴列表"""
    query = select(Partner).where(Partner.status == "approved")

    if level:
        query = query.where(Partner.level == level)
    if industry:
        query = query.where(Partner.industry == industry)
    if is_verified is not None:
        query = query.where(Partner.is_verified == is_verified)
    if search:
        query = query.where(
            (Partner.name.ilike(f"%{search}%")) |
            (Partner.company_name.ilike(f"%{search}%"))
        )

    # 总数查询
    count_query = select(func.count()).select_from(Partner)
    if level:
        count_query = count_query.where(Partner.level == level)
    if industry:
        count_query = count_query.where(Partner.industry == industry)
    if is_verified is not None:
        count_query = count_query.where(Partner.is_verified == is_verified)
    if search:
        count_query = count_query.where(
            (Partner.name.ilike(f"%{search}%")) |
            (Partner.company_name.ilike(f"%{search}%"))
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 执行查询
    result = await db.execute(query.offset(offset).limit(limit))
    partners = result.scalars().all()

    return {
        "success": True,
        "data": [p.to_dict() for p in partners],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/partners/{partner_id}")
async def get_partner(
    partner_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合作伙伴详情"""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合作伙伴不存在",
        )

    return {
        "success": True,
        "data": partner.to_dict(),
    }


@router.post("/partners")
async def create_partner(
    name: str = Body(..., description="合作伙伴名称"),
    description: str = Body(None, description="合作伙伴描述"),
    level: str = Body("certified", description="认证级别：certified, gold, platinum"),
    company_name: str = Body(..., description="公司名称"),
    company_website: str = Body(None, description="公司网站"),
    contact_person: str = Body(..., description="联系人"),
    contact_email: str = Body(..., description="联系邮箱"),
    contact_phone: str = Body(None, description="联系电话"),
    logo_url: str = Body(None, description="公司 Logo URL"),
    industry: str = Body(None, description="所属行业"),
    location: str = Body(None, description="所在地区"),
    benefits: Dict[str, Any] = Body(default_factory=dict, description="享有的权益"),
    capabilities: Dict[str, Any] = Body(default_factory=dict, description="能力描述"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建合作伙伴"""
    # 检查名称是否已存在
    result = await db.execute(
        select(Partner).where(Partner.name == name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"合作伙伴名称已存在：{name}",
        )

    partner = Partner(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        level=level,
        status="approved",
        company_name=company_name,
        company_website=company_website,
        contact_person=contact_person,
        contact_email=contact_email,
        contact_phone=contact_phone,
        logo_url=logo_url,
        industry=industry,
        location=location,
        benefits=str(benefits),
        capabilities=str(capabilities),
        is_verified=True,
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)

    return {
        "success": True,
        "data": partner.to_dict(),
    }


@router.put("/partners/{partner_id}")
async def update_partner(
    partner_id: str,
    name: Optional[str] = Body(None, description="合作伙伴名称"),
    description: Optional[str] = Body(None, description="合作伙伴描述"),
    level: Optional[str] = Body(None, description="认证级别"),
    company_name: Optional[str] = Body(None, description="公司名称"),
    company_website: Optional[str] = Body(None, description="公司网站"),
    contact_person: Optional[str] = Body(None, description="联系人"),
    contact_email: Optional[str] = Body(None, description="联系邮箱"),
    contact_phone: Optional[str] = Body(None, description="联系电话"),
    logo_url: Optional[str] = Body(None, description="公司 Logo URL"),
    industry: Optional[str] = Body(None, description="所属行业"),
    location: Optional[str] = Body(None, description="所在地区"),
    is_verified: Optional[bool] = Body(None, description="是否已验证"),
    is_featured: Optional[bool] = Body(None, description="是否推荐"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新合作伙伴"""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合作伙伴不存在",
        )

    # 更新字段
    if name is not None:
        partner.name = name
    if description is not None:
        partner.description = description
    if level is not None:
        partner.level = level
    if company_name is not None:
        partner.company_name = company_name
    if company_website is not None:
        partner.company_website = company_website
    if contact_person is not None:
        partner.contact_person = contact_person
    if contact_email is not None:
        partner.contact_email = contact_email
    if contact_phone is not None:
        partner.contact_phone = contact_phone
    if logo_url is not None:
        partner.logo_url = logo_url
    if industry is not None:
        partner.industry = industry
    if location is not None:
        partner.location = location
    if is_verified is not None:
        partner.is_verified = is_verified
    if is_featured is not None:
        partner.is_featured = is_featured

    await db.commit()
    await db.refresh(partner)

    return {
        "success": True,
        "data": partner.to_dict(),
    }


@router.delete("/partners/{partner_id}")
async def delete_partner(
    partner_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除合作伙伴"""
    result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = result.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合作伙伴不存在",
        )

    await db.delete(partner)
    await db.commit()

    return {
        "success": True,
        "message": "合作伙伴已删除",
    }


# ========== 合作伙伴申请 ==========

@router.get("/partners/applications")
async def list_partner_applications(
    status: Optional[str] = Query(None, description="申请状态"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合作伙伴申请列表"""
    query = select(PartnerApplication)

    if status:
        query = query.where(PartnerApplication.status == status)

    # 总数查询
    count_query = select(func.count()).select_from(PartnerApplication)
    if status:
        count_query = count_query.where(PartnerApplication.status == status)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 执行查询
    result = await db.execute(query.offset(offset).limit(limit))
    applications = result.scalars().all()

    return {
        "success": True,
        "data": [app.to_dict() for app in applications],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("/partners/applications")
async def create_partner_application(
    company_name: str = Body(..., description="公司名称"),
    company_website: str = Body(None, description="公司网站"),
    company_size: str = Body(None, description="公司规模"),
    industry: str = Body(None, description="所属行业"),
    contact_person: str = Body(..., description="联系人"),
    contact_email: str = Body(..., description="联系邮箱"),
    contact_phone: str = Body(None, description="联系电话"),
    business_license: str = Body(None, description="营业执照 URL"),
    application_reason: str = Body(..., description="申请原因"),
    capabilities: Dict[str, Any] = Body(default_factory=dict, description="能力描述"),
    expected_level: str = Body("certified", description="期望级别"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交合作伙伴申请"""
    application = PartnerApplication(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        company_name=company_name,
        company_website=company_website,
        company_size=company_size,
        industry=industry,
        contact_person=contact_person,
        contact_email=contact_email,
        contact_phone=contact_phone,
        business_license=business_license,
        application_reason=application_reason,
        capabilities=str(capabilities),
        expected_level=expected_level,
        status="pending",
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    return {
        "success": True,
        "data": application.to_dict(),
    }


@router.post("/partners/applications/{application_id}/review")
async def review_partner_application(
    application_id: str,
    status: str = Body(..., description="审核状态：approved, rejected"),
    review_comment: str = Body(None, description="审核意见"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """审核合作伙伴申请"""
    result = await db.execute(
        select(PartnerApplication).where(PartnerApplication.id == application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="申请不存在",
        )

    application.status = status
    application.review_comment = review_comment
    application.reviewer_id = current_user.id
    application.reviewed_at = datetime.utcnow()

    # 如果审核通过，创建合作伙伴记录
    if status == "approved":
        partner = Partner(
            id=str(uuid.uuid4()),
            name=application.company_name,
            description=application.application_reason,
            level=application.expected_level,
            status="approved",
            company_name=application.company_name,
            company_website=application.company_website,
            contact_person=application.contact_person,
            contact_email=application.contact_email,
            contact_phone=application.contact_phone,
            industry=application.industry,
            capabilities=application.capabilities,
            is_verified=False,  # 新合作伙伴需要验证
        )
        db.add(partner)

    await db.commit()

    return {
        "success": True,
        "data": application.to_dict(),
    }


# ========== 合作伙伴权益 ==========

@router.get("/partners/benefits")
async def list_partner_benefits(
    level: Optional[str] = Query(None, description="合作伙伴级别"),
    benefit_type: Optional[str] = Query(None, description="权益类型"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合作伙伴权益列表"""
    query = select(PartnerBenefit).where(PartnerBenefit.is_active == True)

    if level:
        query = query.where(PartnerBenefit.level == level)
    if benefit_type:
        query = query.where(PartnerBenefit.benefit_type == benefit_type)

    result = await db.execute(query)
    benefits = result.scalars().all()

    return {
        "success": True,
        "data": [b.to_dict() for b in benefits],
    }


@router.post("/partners/benefits")
async def create_partner_benefit(
    name: str = Body(..., description="权益名称"),
    description: str = Body(None, description="权益描述"),
    level: str = Body(..., description="适用级别"),
    benefit_type: str = Body(None, description="权益类型"),
    quota: int = Body(None, description="配额限制"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建合作伙伴权益"""
    benefit = PartnerBenefit(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        level=level,
        benefit_type=benefit_type,
        quota=quota,
        is_active=True,
    )
    db.add(benefit)
    await db.commit()
    await db.refresh(benefit)

    return {
        "success": True,
        "data": benefit.to_dict(),
    }


# ========== 合作伙伴活动 ==========

@router.get("/partners/activities")
async def list_partner_activities(
    activity_type: Optional[str] = Query(None, description="活动类型"),
    status: Optional[str] = Query(None, description="活动状态"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合作伙伴活动列表"""
    query = select(PartnerActivity)

    if activity_type:
        query = query.where(PartnerActivity.activity_type == activity_type)
    if status:
        query = query.where(PartnerActivity.status == status)

    result = await db.execute(query)
    activities = result.scalars().all()

    return {
        "success": True,
        "data": [a.to_dict() for a in activities],
    }


@router.post("/partners/activities")
async def create_partner_activity(
    title: str = Body(..., description="活动标题"),
    description: str = Body(None, description="活动描述"),
    activity_type: str = Body(None, description="活动类型"),
    start_time: datetime = Body(None, description="开始时间"),
    end_time: datetime = Body(None, description="结束时间"),
    location: str = Body(None, description="活动地点"),
    online_url: str = Body(None, description="线上链接"),
    max_participants: int = Body(None, description="最大参与人数"),
    organizer_id: str = Body(None, description="主办方 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建合作伙伴活动"""
    activity = PartnerActivity(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        activity_type=activity_type,
        start_time=start_time,
        end_time=end_time,
        location=location,
        online_url=online_url,
        max_participants=max_participants,
        organizer_id=organizer_id,
        status="draft",
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)

    return {
        "success": True,
        "data": activity.to_dict(),
    }
