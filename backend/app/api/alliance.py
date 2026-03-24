"""
生态联盟 API 路由
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

router = APIRouter()


# ========== 联盟成员管理 ==========

@router.get("/alliance/members")
async def list_alliance_members(
    member_type: Optional[str] = Query(None, description="成员类型"),
    industry: Optional[str] = Query(None, description="所属行业"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取生态联盟成员列表"""
    # 暂时返回静态数据
    members = [
        {
            "id": "1",
            "name": "智能科技有限公司",
            "member_type": "enterprise",
            "industry": "制造业",
            "join_date": "2025-01-15",
            "status": "active",
            "level": "gold",
            "contribution_score": 850,
        },
        {
            "id": "2",
            "name": "数据科技有限公司",
            "member_type": "enterprise",
            "industry": "金融业",
            "join_date": "2025-02-20",
            "status": "active",
            "level": "platinum",
            "contribution_score": 920,
        },
        {
            "id": "3",
            "name": "张三",
            "member_type": "individual",
            "industry": "互联网",
            "join_date": "2025-03-10",
            "status": "active",
            "level": "silver",
            "contribution_score": 450,
        },
        {
            "id": "4",
            "name": "创新研究院",
            "member_type": "research",
            "industry": "科研机构",
            "join_date": "2025-01-05",
            "status": "active",
            "level": "gold",
            "contribution_score": 780,
        },
    ]

    if member_type:
        members = [m for m in members if m["member_type"] == member_type]
    if industry:
        members = [m for m in members if m["industry"] == industry]
    if status:
        members = [m for m in members if m["status"] == status]

    total = len(members)
    paginated = members[offset:offset + limit]

    return {
        "success": True,
        "data": paginated,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/alliance/members/{member_id}")
async def get_alliance_member(
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取生态联盟成员详情"""
    # 返回静态详情数据
    member = {
        "id": member_id,
        "name": "智能科技有限公司",
        "member_type": "enterprise",
        "industry": "制造业",
        "join_date": "2025-01-15",
        "status": "active",
        "level": "gold",
        "contribution_score": 850,
        "description": "专注于智能制造和工业互联网解决方案",
        "website": "https://example.com",
        "location": "北京市海淀区",
        "contact": {
            "person": "李四",
            "email": "contact@example.com",
            "phone": "010-12345678",
        },
        "capabilities": [
            "智能制造",
            "工业互联网",
            "AI 质检",
            "预测性维护",
        ],
        "achievements": [
            "2025 年度最佳合作伙伴",
            "智能制造示范项目",
        ],
        "collaboration_cases": [
            {
                "title": "某汽车工厂智能质检项目",
                "description": "利用 AI 视觉技术实现汽车零部件自动质检",
                "value": "500 万",
            },
        ],
    }

    return {
        "success": True,
        "data": member,
    }


@router.post("/alliance/members/join")
async def join_alliance(
    name: str = Body(..., description="成员名称"),
    member_type: str = Body(..., description="成员类型：enterprise, individual, research"),
    industry: str = Body(None, description="所属行业"),
    description: str = Body(None, description="描述"),
    website: str = Body(None, description="网站"),
    location: str = Body(None, description="所在地区"),
    contact_person: str = Body(..., description="联系人"),
    contact_email: str = Body(..., description="联系邮箱"),
    contact_phone: str = Body(None, description="联系电话"),
    capabilities: List[str] = Body(default_factory=list, description="能力列表"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """申请加入生态联盟"""
    # 实际应保存到数据库
    return {
        "success": True,
        "data": {
            "message": "申请已提交，审核通过后将成为联盟成员",
            "application_id": str(uuid.uuid4()),
        },
    }


# ========== 资源共享平台 ==========

@router.get("/alliance/resources")
async def list_alliance_resources(
    resource_type: Optional[str] = Query(None, description="资源类型"),
    industry: Optional[str] = Query(None, description="所属行业"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取联盟资源列表"""
    resources = [
        {
            "id": "1",
            "title": "AI 中台部署文档",
            "resource_type": "document",
            "provider": "智能科技有限公司",
            "industry": "制造业",
            "description": "详细的 AI 中台部署指南和最佳实践",
            "download_count": 1250,
            "rating": 4.8,
            "is_free": True,
        },
        {
            "id": "2",
            "title": "金融行业解决方案模板",
            "resource_type": "template",
            "provider": "数据科技有限公司",
            "industry": "金融业",
            "description": "适用于金融行业的中台解决方案模板",
            "download_count": 890,
            "rating": 4.9,
            "is_free": False,
            "price": 999,
        },
        {
            "id": "3",
            "title": "智能客服培训视频",
            "resource_type": "video",
            "provider": "创新研究院",
            "industry": "互联网",
            "description": "智能客服系统搭建和培训视频课程",
            "download_count": 2100,
            "rating": 4.7,
            "is_free": True,
        },
        {
            "id": "4",
            "title": "工业质检数据集",
            "resource_type": "dataset",
            "provider": "智能科技有限公司",
            "industry": "制造业",
            "description": "包含 10 万 + 工业质检图片的数据集",
            "download_count": 560,
            "rating": 4.6,
            "is_free": False,
            "price": 1999,
        },
    ]

    if resource_type:
        resources = [r for r in resources if r["resource_type"] == resource_type]
    if industry:
        resources = [r for r in resources if r["industry"] == industry]
    if search:
        resources = [r for r in resources if search.lower() in r["title"].lower() or search.lower() in r["description"].lower()]

    total = len(resources)
    paginated = resources[offset:offset + limit]

    return {
        "success": True,
        "data": paginated,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/alliance/resources/{resource_id}")
async def get_alliance_resource(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取联盟资源详情"""
    resource = {
        "id": resource_id,
        "title": "AI 中台部署文档",
        "resource_type": "document",
        "provider": "智能科技有限公司",
        "provider_id": "1",
        "industry": "制造业",
        "description": "详细的 AI 中台部署指南和最佳实践",
        "content": """
# AI 中台部署文档

## 1. 环境准备

- Docker 20.10+
- Docker Compose 2.0+
- 内存：16GB+
- 存储：100GB+

## 2. 快速部署

```bash
docker-compose -f deploy/docker-compose.yml up -d
```

## 3. 配置说明

...
        """,
        "download_count": 1250,
        "rating": 4.8,
        "rating_count": 156,
        "is_free": True,
        "tags": ["AI 中台", "部署", "Docker", "最佳实践"],
        "created_at": "2025-01-15T10:00:00",
        "updated_at": "2025-03-20T15:30:00",
    }

    return {
        "success": True,
        "data": resource,
    }


@router.post("/alliance/resources")
async def create_alliance_resource(
    title: str = Body(..., description="资源标题"),
    resource_type: str = Body(..., description="资源类型"),
    description: str = Body(..., description="资源描述"),
    industry: str = Body(None, description="所属行业"),
    content: str = Body(None, description="资源内容"),
    is_free: bool = Body(True, description="是否免费"),
    price: float = Body(None, description="价格"),
    tags: List[str] = Body(default_factory=list, description="标签列表"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建联盟资源"""
    return {
        "success": True,
        "data": {
            "id": str(uuid.uuid4()),
            "title": title,
            "resource_type": resource_type,
            "provider": current_user.username,
            "status": "pending_review",
            "message": "资源已提交，审核通过后将展示在资源平台",
        },
    }


# ========== 合作机会 ==========

@router.get("/alliance/opportunities")
async def list_alliance_opportunities(
    opportunity_type: Optional[str] = Query(None, description="机会类型"),
    industry: Optional[str] = Query(None, description="所属行业"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合作机会列表"""
    opportunities = [
        {
            "id": "1",
            "title": "智能制造项目合作",
            "opportunity_type": "project",
            "publisher": "智能科技有限公司",
            "industry": "制造业",
            "description": "寻找智能制造领域的合作伙伴，共同开发 AI 质检系统",
            "budget": "500-1000 万",
            "deadline": "2025-06-30",
            "status": "open",
            "responses": 12,
        },
        {
            "id": "2",
            "title": "金融行业 AI 应用联合研发",
            "opportunity_type": "research",
            "publisher": "数据科技有限公司",
            "industry": "金融业",
            "description": "联合研发金融行业 AI 风控和营销应用",
            "budget": "面议",
            "deadline": "2025-05-15",
            "status": "open",
            "responses": 8,
        },
        {
            "id": "3",
            "title": "AI 人才培训合作",
            "opportunity_type": "training",
            "publisher": "创新研究院",
            "industry": "教育",
            "description": "开展 AI 人才培训合作，提供课程和实训",
            "budget": "100-200 万",
            "deadline": "2025-04-30",
            "status": "open",
            "responses": 15,
        },
    ]

    if opportunity_type:
        opportunities = [o for o in opportunities if o["opportunity_type"] == opportunity_type]
    if industry:
        opportunities = [o for o in opportunities if o["industry"] == industry]
    if status:
        opportunities = [o for o in opportunities if o["status"] == status]

    total = len(opportunities)
    paginated = opportunities[offset:offset + limit]

    return {
        "success": True,
        "data": paginated,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("/alliance/opportunities")
async def create_alliance_opportunity(
    title: str = Body(..., description="机会标题"),
    opportunity_type: str = Body(..., description="机会类型"),
    description: str = Body(..., description="机会描述"),
    industry: str = Body(None, description="所属行业"),
    budget: str = Body(None, description="预算范围"),
    deadline: str = Body(None, description="截止日期"),
    requirements: List[str] = Body(default_factory=list, description="合作要求"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布合作机会"""
    return {
        "success": True,
        "data": {
            "id": str(uuid.uuid4()),
            "title": title,
            "publisher": current_user.username,
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
        },
    }


# ========== 联盟活动 ==========

@router.get("/alliance/events")
async def list_alliance_events(
    event_type: Optional[str] = Query(None, description="活动类型"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取联盟活动列表"""
    events = [
        {
            "id": "1",
            "title": "2025 AI 中台生态大会",
            "event_type": "conference",
            "start_time": "2025-06-15T09:00:00",
            "end_time": "2025-06-16T18:00:00",
            "location": "北京国际会议中心",
            "online_url": None,
            "description": "年度 AI 中台生态大会，邀请行业专家和合作伙伴分享最佳实践",
            "organizer": "AI 中台团队",
            "max_participants": 500,
            "registered": 320,
            "status": "upcoming",
        },
        {
            "id": "2",
            "title": "智能制造技术研讨会",
            "event_type": "webinar",
            "start_time": "2025-04-20T14:00:00",
            "end_time": "2025-04-20T16:00:00",
            "location": None,
            "online_url": "https://meeting.example.com/123",
            "description": "探讨智能制造领域的 AI 应用和创新实践",
            "organizer": "智能科技有限公司",
            "max_participants": 200,
            "registered": 156,
            "status": "upcoming",
        },
        {
            "id": "3",
            "title": "AI 开发者训练营",
            "event_type": "training",
            "start_time": "2025-05-10T09:00:00",
            "end_time": "2025-05-12T18:00:00",
            "location": "上海张江高科技园区",
            "online_url": None,
            "description": "为期 3 天的 AI 开发者实战训练营",
            "organizer": "创新研究院",
            "max_participants": 50,
            "registered": 48,
            "status": "upcoming",
        },
    ]

    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    if status:
        events = [e for e in events if e["status"] == status]

    total = len(events)
    paginated = events[offset:offset + limit]

    return {
        "success": True,
        "data": paginated,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/alliance/events/{event_id}")
async def get_alliance_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取联盟活动详情"""
    event = {
        "id": event_id,
        "title": "2025 AI 中台生态大会",
        "event_type": "conference",
        "start_time": "2025-06-15T09:00:00",
        "end_time": "2025-06-16T18:00:00",
        "location": "北京国际会议中心",
        "online_url": None,
        "description": "年度 AI 中台生态大会，邀请行业专家和合作伙伴分享最佳实践",
        "agenda": [
            {"time": "09:00-09:30", "item": "签到入场"},
            {"time": "09:30-10:30", "item": "开幕式和主题演讲"},
            {"time": "10:30-12:00", "item": "技术分论坛"},
            {"time": "14:00-17:00", "item": "合作伙伴案例分享"},
            {"time": "17:00-18:00", "item": "颁奖晚宴"},
        ],
        "speakers": [
            {"name": "张三", "title": "AI 中台首席架构师", "topic": "AI 中台架构演进"},
            {"name": "李四", "title": "智能科技有限公司 CTO", "topic": "智能制造实践"},
        ],
        "organizer": "AI 中台团队",
        "max_participants": 500,
        "registered": 320,
        "status": "upcoming",
        "registration_url": "https://events.example.com/register/1",
    }

    return {
        "success": True,
        "data": event,
    }


@router.post("/alliance/events/{event_id}/register")
async def register_alliance_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """报名参加联盟活动"""
    return {
        "success": True,
        "data": {
            "message": "报名成功",
            "event_id": event_id,
            "registration_id": str(uuid.uuid4()),
        },
    }


# ========== 联盟统计 ==========

@router.get("/alliance/stats")
async def get_alliance_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取生态联盟统计信息"""
    return {
        "success": True,
        "data": {
            "total_members": 156,
            "member_breakdown": {
                "enterprise": 89,
                "individual": 52,
                "research": 15,
            },
            "industry_breakdown": {
                "制造业": 45,
                "金融业": 38,
                "互联网": 32,
                "医疗": 18,
                "其他": 23,
            },
            "total_resources": 423,
            "total_opportunities": 67,
            "total_events": 24,
            "total_collaboration_value": "2.5 亿",
        },
    }
