"""
合作伙伴数据模型
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class Partner(Base):
    """合作伙伴表"""
    __tablename__ = "partners"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # 合作伙伴名称
    description = Column(Text)  # 合作伙伴描述
    level = Column(String(50), default="certified")  # 认证级别：certified, gold, platinum
    status = Column(String(50), default="pending")  # 状态：pending, approved, rejected
    company_name = Column(String(200))  # 公司名称
    company_website = Column(String(500))  # 公司网站
    contact_person = Column(String(100))  # 联系人
    contact_email = Column(String(200))  # 联系邮箱
    contact_phone = Column(String(50))  # 联系电话
    logo_url = Column(String(500))  # 公司 Logo URL
    industry = Column(String(100))  # 所属行业
    location = Column(String(200))  # 所在地区
    certification_date = Column(DateTime)  # 认证日期
    expiration_date = Column(DateTime)  # 到期日期
    benefits = Column(Text)  # 享有的权益（JSON 格式）
    capabilities = Column(Text)  # 能力描述（JSON 格式）
    success_cases = Column(Text)  # 成功案例（JSON 格式）
    rating = Column(Float, default=0.0)  # 评分
    rating_count = Column(Integer, default=0)  # 评分数量
    is_verified = Column(Boolean, default=False)  # 是否已验证
    is_featured = Column(Boolean, default=False)  # 是否推荐
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "status": self.status,
            "company_name": self.company_name,
            "company_website": self.company_website,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "logo_url": self.logo_url,
            "industry": self.industry,
            "location": self.location,
            "certification_date": self.certification_date.isoformat() if self.certification_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "is_verified": self.is_verified,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PartnerApplication(Base):
    """合作伙伴申请表"""
    __tablename__ = "partner_applications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    company_name = Column(String(200), nullable=False)
    company_website = Column(String(500))
    company_size = Column(String(50))  # 公司规模
    industry = Column(String(100))  # 所属行业
    contact_person = Column(String(100), nullable=False)
    contact_email = Column(String(200), nullable=False)
    contact_phone = Column(String(50))
    business_license = Column(String(500))  # 营业执照 URL
    application_reason = Column(Text)  # 申请原因
    capabilities = Column(Text)  # 能力描述（JSON）
    expected_level = Column(String(50), default="certified")  # 期望级别
    status = Column(String(50), default="pending")  # pending, approved, rejected
    review_comment = Column(Text)  # 审核意见
    reviewer_id = Column(String(36), ForeignKey("users.id"))  # 审核人
    reviewed_at = Column(DateTime)  # 审核时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "company_website": self.company_website,
            "company_size": self.company_size,
            "industry": self.industry,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "business_license": self.business_license,
            "application_reason": self.application_reason,
            "capabilities": self.capabilities,
            "expected_level": self.expected_level,
            "status": self.status,
            "review_comment": self.review_comment,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PartnerBenefit(Base):
    """合作伙伴权益表"""
    __tablename__ = "partner_benefits"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # 权益名称
    description = Column(Text)  # 权益描述
    level = Column(String(50), nullable=False)  # 适用级别
    benefit_type = Column(String(50))  # 权益类型：technical, marketing, sales, support
    quota = Column(Integer)  # 配额限制
    is_active = Column(Boolean, default=True)  # 是否生效
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "benefit_type": self.benefit_type,
            "quota": self.quota,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PartnerActivity(Base):
    """合作伙伴活动表"""
    __tablename__ = "partner_activities"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(200), nullable=False)  # 活动标题
    description = Column(Text)  # 活动描述
    activity_type = Column(String(50))  # 活动类型：webinar, workshop, conference, training
    start_time = Column(DateTime)  # 开始时间
    end_time = Column(DateTime)  # 结束时间
    location = Column(String(200))  # 活动地点
    online_url = Column(String(500))  # 线上链接
    max_participants = Column(Integer)  # 最大参与人数
    organizer_id = Column(String(36), ForeignKey("partners.id"))  # 主办方
    status = Column(String(50), default="draft")  # draft, published, ended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "activity_type": self.activity_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "online_url": self.online_url,
            "max_participants": self.max_participants,
            "organizer_id": self.organizer_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
