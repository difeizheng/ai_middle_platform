"""
账单和发票系统数据模型
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Float, DECIMAL, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..core.database import Base


class BillStatus(str, enum.Enum):
    """账单状态"""
    UNPAID = "unpaid"  # 未支付
    PAID = "paid"  # 已支付
    OVERDUE = "overdue"  # 逾期未付
    CANCELLED = "cancelled"  # 已取消


class InvoiceType(str, enum.Enum):
    """发票类型"""
    ELECTRONIC = "electronic"  # 电子发票
    PAPER = "paper"  # 纸质发票


class InvoiceStatus(str, enum.Enum):
    """发票状态"""
    PENDING = "pending"  # 待开具
    PROCESSING = "processing"  # 开具中
    ISSUED = "issued"  # 已开具
    DELIVERED = "delivered"  # 已交付
    REJECTED = "rejected"  # 已拒绝


class MonthlyBill(Base):
    """月度账单表"""
    __tablename__ = "monthly_bills"

    id = Column(String(36), primary_key=True, index=True)
    bill_no = Column(String(64), unique=True, nullable=False, index=True)  # 账单号

    # 关联信息
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 账单周期
    billing_month = Column(String(7), nullable=False, index=True)  # 账单月份：2026-03
    period_start = Column(DateTime, nullable=False)  # 周期开始
    period_end = Column(DateTime, nullable=False)  # 周期结束

    # 金额信息
    total_amount = Column(DECIMAL(10, 2), nullable=False)  # 账单总额
    paid_amount = Column(DECIMAL(10, 2), default=0)  # 已支付金额
    unpaid_amount = Column(DECIMAL(10, 2), default=0)  # 未支付金额
    discount_amount = Column(DECIMAL(10, 2), default=0)  # 优惠金额
    refund_amount = Column(DECIMAL(10, 2), default=0)  # 退款金额

    # 消费明细汇总
    model_call_amount = Column(DECIMAL(10, 2), default=0)  # 模型调用费用
    knowledge_base_amount = Column(DECIMAL(10, 2), default=0)  # 知识库费用
    agent_amount = Column(DECIMAL(10, 2), default=0)  # 智能体费用
    skill_amount = Column(DECIMAL(10, 2), default=0)  # Skill 费用

    # 使用量统计
    total_tokens = Column(Integer, default=0)  # 总 Token 使用量
    total_calls = Column(Integer, default=0)  # 总调用次数
    total_storage_gb = Column(DECIMAL(10, 2), default=0)  # 总存储量 (GB)

    # 账单状态
    status = Column(String(20), default="unpaid", index=True)  # unpaid/paid/overdue/cancelled

    # 支付信息
    payment_deadline = Column(DateTime)  # 支付截止日期
    paid_at = Column(DateTime)  # 支付时间
    payment_method = Column(String(20))  # 支付方式

    # 账单文件
    bill_file_url = Column(String(500))  # 账单文件 URL（PDF/Excel）
    bill_data = Column(Text, default='{}')  # 账单明细数据（JSON 格式）

    # 通知信息
    email_sent = Column(Boolean, default=False)  # 是否已发送邮件
    email_sent_at = Column(DateTime)  # 邮件发送时间

    # 备注
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    account = relationship("Account", backref="monthly_bills")
    user = relationship("User", backref="monthly_bills")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "bill_no": self.bill_no,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "billing_month": self.billing_month,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_amount": float(self.total_amount) if self.total_amount else 0,
            "paid_amount": float(self.paid_amount) if self.paid_amount else 0,
            "unpaid_amount": float(self.unpaid_amount) if self.unpaid_amount else 0,
            "discount_amount": float(self.discount_amount) if self.discount_amount else 0,
            "refund_amount": float(self.refund_amount) if self.refund_amount else 0,
            "model_call_amount": float(self.model_call_amount) if self.model_call_amount else 0,
            "knowledge_base_amount": float(self.knowledge_base_amount) if self.knowledge_base_amount else 0,
            "agent_amount": float(self.agent_amount) if self.agent_amount else 0,
            "skill_amount": float(self.skill_amount) if self.skill_amount else 0,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "total_storage_gb": float(self.total_storage_gb) if self.total_storage_gb else 0,
            "status": self.status,
            "payment_deadline": self.payment_deadline.isoformat() if self.payment_deadline else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "payment_method": self.payment_method,
            "bill_file_url": self.bill_file_url,
            "email_sent": self.email_sent,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Invoice(Base):
    """发票表"""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, index=True)
    invoice_no = Column(String(64), unique=True, index=True)  # 发票号码
    invoice_code = Column(String(64))  # 发票代码

    # 关联信息
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    bill_id = Column(String(36), ForeignKey("monthly_bills.id"), index=True)  # 关联账单

    # 发票类型
    invoice_type = Column(String(20), default="electronic")  # electronic/paper
    status = Column(String(20), default="pending", index=True)  # pending/processing/issued/delivered/rejected

    # 发票抬头信息
    title = Column(String(200), nullable=False)  # 发票抬头
    tax_id = Column(String(50))  # 纳税人识别号
    company_address = Column(String(200))  # 公司地址
    company_phone = Column(String(50))  # 公司电话
    bank_name = Column(String(100))  # 开户行
    bank_account = Column(String(50))  # 银行账号

    # 发票金额
    amount = Column(DECIMAL(10, 2), nullable=False)  # 开票金额
    tax_rate = Column(DECIMAL(5, 4), default=0.03)  # 税率
    tax_amount = Column(DECIMAL(10, 2), default=0)  # 税额

    # 收票信息
    receiver_name = Column(String(100))  # 收票人姓名
    receiver_email = Column(String(100))  # 收票邮箱（电子发票）
    receiver_phone = Column(String(20))  # 收票电话
    receiver_address = Column(String(200))  # 收票地址（纸质发票）
    receiver_zip = Column(String(10))  # 邮编

    # 发票文件
    invoice_file_url = Column(String(500))  # 发票文件 URL（PDF）
    invoice_download_code = Column(String(32))  # 下载验证码

    # 物流信息（纸质发票）
    express_company = Column(String(50))  # 快递公司
    express_number = Column(String(100))  # 快递单号
    express_status = Column(String(20))  # 快递状态

    # 申请信息
    application_time = Column(DateTime, default=datetime.utcnow)  # 申请时间
    issued_time = Column(DateTime)  # 开具时间
    delivered_time = Column(DateTime)  # 交付时间

    # 拒绝信息
    reject_reason = Column(String(500))  # 拒绝原因

    # 备注
    remark = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    account = relationship("Account", backref="invoices")
    user = relationship("User", backref="invoices")
    bill = relationship("MonthlyBill", backref="invoices")

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_no": self.invoice_no,
            "invoice_code": self.invoice_code,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "bill_id": self.bill_id,
            "invoice_type": self.invoice_type,
            "status": self.status,
            "title": self.title,
            "tax_id": self.tax_id,
            "amount": float(self.amount) if self.amount else 0,
            "tax_rate": float(self.tax_rate) if self.tax_rate else 0.03,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0,
            "receiver_name": self.receiver_name,
            "receiver_email": self.receiver_email,
            "receiver_phone": self.receiver_phone,
            "receiver_address": self.receiver_address,
            "invoice_file_url": self.invoice_file_url,
            "express_company": self.express_company,
            "express_number": self.express_number,
            "application_time": self.application_time.isoformat() if self.application_time else None,
            "issued_time": self.issued_time.isoformat() if self.issued_time else None,
            "delivered_time": self.delivered_time.isoformat() if self.delivered_time else None,
            "reject_reason": self.reject_reason,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InvoiceApplication(Base):
    """发票申请表"""
    __tablename__ = "invoice_applications"

    id = Column(String(36), primary_key=True, index=True)
    application_no = Column(String(64), unique=True, nullable=False)  # 申请单号

    # 关联信息
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 申请信息
    invoice_type = Column(String(20), nullable=False)  # electronic/paper
    amount = Column(DECIMAL(10, 2), nullable=False)  # 申请开票金额

    # 抬头信息
    title = Column(String(200), nullable=False)
    tax_id = Column(String(50))
    company_address = Column(String(200))
    company_phone = Column(String(50))
    bank_name = Column(String(100))
    bank_account = Column(String(50))

    # 收票信息
    receiver_name = Column(String(100))
    receiver_email = Column(String(100))
    receiver_phone = Column(String(20))
    receiver_address = Column(String(200))
    receiver_zip = Column(String(10))

    # 关联账单（可多张）
    bill_ids = Column(Text, default='[]')  # 账单 ID 列表（JSON）

    # 审核状态
    audit_status = Column(String(20), default="pending")  # pending/approved/rejected
    auditor_id = Column(String(36))  # 审核人 ID
    audit_time = Column(DateTime)  # 审核时间
    audit_remark = Column(String(500))  # 审核备注

    # 申请状态
    status = Column(String(20), default="pending")  # pending/processing/completed/cancelled

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    account = relationship("Account", backref="invoice_applications")
    user = relationship("User", backref="invoice_applications")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "application_no": self.application_no,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "invoice_type": self.invoice_type,
            "amount": float(self.amount) if self.amount else 0,
            "title": self.title,
            "tax_id": self.tax_id,
            "receiver_name": self.receiver_name,
            "receiver_email": self.receiver_email,
            "receiver_phone": self.receiver_phone,
            "receiver_address": self.receiver_address,
            "bill_ids": json.loads(self.bill_ids) if self.bill_ids else [],
            "audit_status": self.audit_status,
            "auditor_id": self.auditor_id,
            "audit_time": self.audit_time.isoformat() if self.audit_time else None,
            "audit_remark": self.audit_remark,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BillEmailLog(Base):
    """账单邮件发送日志表"""
    __tablename__ = "bill_email_logs"

    id = Column(String(36), primary_key=True, index=True)
    bill_id = Column(String(36), ForeignKey("monthly_bills.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 邮件信息
    recipient_email = Column(String(100), nullable=False)
    email_subject = Column(String(200))
    email_content = Column(Text)

    # 发送状态
    send_status = Column(String(20), default="pending")  # pending/success/failed
    send_time = Column(DateTime)  # 发送时间
    error_message = Column(Text)  # 错误信息

    # 打开追踪
    is_opened = Column(Boolean, default=False)  # 是否已打开
    opened_at = Column(DateTime)  # 打开时间

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    bill = relationship("MonthlyBill", backref="email_logs")
    user = relationship("User", backref="bill_email_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "bill_id": self.bill_id,
            "user_id": self.user_id,
            "recipient_email": self.recipient_email,
            "email_subject": self.email_subject,
            "send_status": self.send_status,
            "send_time": self.send_time.isoformat() if self.send_time else None,
            "error_message": self.error_message,
            "is_opened": self.is_opened,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
