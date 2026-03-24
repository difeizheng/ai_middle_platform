"""
计费系统数据模型
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Float, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime

from ..core.database import Base


class BillingPlan(Base):
    """计费策略表"""
    __tablename__ = "billing_plans"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # 计费方案名称
    billing_type = Column(String(20), nullable=False)  # 计费类型：token/call/subscription
    description = Column(Text)  # 方案描述

    # 定价配置
    price_per_1k_tokens = Column(DECIMAL(10, 4), default=0)  # 每 1000 tokens 价格
    price_per_call = Column(DECIMAL(10, 4), default=0)  # 每次调用价格
    monthly_fee = Column(DECIMAL(10, 2), default=0)  # 月费
    quota_limit = Column(Integer, default=0)  # 配额限制（调用次数或 token 数）
    overage_rate = Column(DECIMAL(10, 4), default=1)  # 超额费率系数

    # 模型价格系数（JSON 格式，针对不同模型设置不同价格系数）
    model_pricing = Column(Text, default='{}')  # {"gpt-4": 2.0, "gpt-3.5-turbo": 1.0}

    is_active = Column(Boolean, default=True)  # 是否生效
    is_default = Column(Boolean, default=False)  # 是否默认方案
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "name": self.name,
            "billing_type": self.billing_type,
            "description": self.description,
            "price_per_1k_tokens": float(self.price_per_1k_tokens) if self.price_per_1k_tokens else 0,
            "price_per_call": float(self.price_per_call) if self.price_per_call else 0,
            "monthly_fee": float(self.monthly_fee) if self.monthly_fee else 0,
            "quota_limit": self.quota_limit,
            "overage_rate": float(self.overage_rate) if self.overage_rate else 1,
            "model_pricing": json.loads(self.model_pricing) if self.model_pricing else {},
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Account(Base):
    """账户表"""
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)  # 关联用户
    balance = Column(DECIMAL(10, 2), default=0)  # 账户余额
    total_recharge = Column(DECIMAL(10, 2), default=0)  # 累计充值
    total_consumption = Column(DECIMAL(10, 2), default=0)  # 累计消费
    currency = Column(String(10), default="CNY")  # 货币类型
    status = Column(String(20), default="active")  # 账户状态：active/frozen/closed
    billing_plan_id = Column(String(36), ForeignKey("billing_plans.id"))  # 当前计费方案

    # 预警配置
    low_balance_warning = Column(DECIMAL(10, 2), default=100)  # 余额预警阈值
    is_warning_enabled = Column(Boolean, default=True)  # 是否启用预警

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    user = relationship("User", backref="accounts")
    billing_plan = relationship("BillingPlan", backref="accounts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "balance": float(self.balance) if self.balance else 0,
            "total_recharge": float(self.total_recharge) if self.total_recharge else 0,
            "total_consumption": float(self.total_consumption) if self.total_consumption else 0,
            "currency": self.currency,
            "status": self.status,
            "billing_plan_id": self.billing_plan_id,
            "low_balance_warning": float(self.low_balance_warning) if self.low_balance_warning else 100,
            "is_warning_enabled": self.is_warning_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BillingRecord(Base):
    """计费记录表"""
    __tablename__ = "billing_records"

    id = Column(String(36), primary_key=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    record_type = Column(String(20), nullable=False)  # charge(充值)/consume(消费)/refund(退款)/adjust(调整)
    amount = Column(DECIMAL(10, 4), nullable=False)  # 金额（正数）

    # 余额快照
    balance_before = Column(DECIMAL(10, 2), nullable=False)  # 操作前余额
    balance_after = Column(DECIMAL(10, 2), nullable=False)  # 操作后余额

    # 资源信息
    resource_type = Column(String(20))  # model_call/knowledge_base/agent/api_call
    resource_id = Column(String(36))  # 资源 ID（如模型 ID、应用 ID 等）

    # 使用量详情
    tokens_used = Column(Integer, default=0)  # 使用的 token 数
    input_tokens = Column(Integer, default=0)  # 输入 token 数
    output_tokens = Column(Integer, default=0)  # 输出 token 数
    call_count = Column(Integer, default=0)  # 调用次数

    # 关联信息
    order_id = Column(String(36))  # 关联订单 ID（充值时）
    api_log_id = Column(String(36))  # 关联 API 日志 ID（消费时）

    description = Column(Text)  # 描述
    extra_data = Column(Text, default='{}')  # 额外元数据（JSON 格式）

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    account = relationship("Account", backref="billing_records")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "account_id": self.account_id,
            "record_type": self.record_type,
            "amount": float(self.amount) if self.amount else 0,
            "balance_before": float(self.balance_before) if self.balance_before else 0,
            "balance_after": float(self.balance_after) if self.balance_after else 0,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "tokens_used": self.tokens_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "call_count": self.call_count,
            "order_id": self.order_id,
            "api_log_id": self.api_log_id,
            "description": self.description,
            "extra_data": json.loads(self.extra_data) if self.extra_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RechargeOrder(Base):
    """充值订单表"""
    __tablename__ = "recharge_orders"

    id = Column(String(36), primary_key=True, index=True)
    order_no = Column(String(64), unique=True, nullable=False)  # 订单号
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    amount = Column(DECIMAL(10, 2), nullable=False)  # 充值金额
    actual_amount = Column(DECIMAL(10, 2))  # 实际到账金额（可能有优惠）

    payment_method = Column(String(20))  # 支付方式：alipay/wechat/bank/transfer
    payment_status = Column(String(20), default="pending")  # pending/success/failed/refunded
    transaction_id = Column(String(100))  # 第三方交易 ID

    # 优惠信息
    discount_rate = Column(DECIMAL(5, 4), default=1)  # 折扣率
    bonus_amount = Column(DECIMAL(10, 2), default=0)  # 赠送金额

    description = Column(Text)  # 订单描述
    client_ip = Column(String(50))  # 客户端 IP

    paid_at = Column(DateTime)  # 支付时间
    expires_at = Column(DateTime)  # 过期时间

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    account = relationship("Account", backref="recharge_orders")
    user = relationship("User", backref="recharge_orders")

    def to_dict(self):
        return {
            "id": self.id,
            "order_no": self.order_no,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "amount": float(self.amount) if self.amount else 0,
            "actual_amount": float(self.actual_amount) if self.actual_amount else 0,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "transaction_id": self.transaction_id,
            "discount_rate": float(self.discount_rate) if self.discount_rate else 1,
            "bonus_amount": float(self.bonus_amount) if self.bonus_amount else 0,
            "description": self.description,
            "client_ip": self.client_ip,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BillingStats(Base):
    """计费统计表（用于快速查询）"""
    __tablename__ = "billing_stats"

    id = Column(String(36), primary_key=True, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    stat_date = Column(DateTime, nullable=False, index=True)  # 统计日期（天）

    # 消费统计
    total_consumption = Column(DECIMAL(10, 2), default=0)  # 总消费金额
    total_tokens = Column(Integer, default=0)  # 总 token 使用量
    total_calls = Column(Integer, default=0)  # 总调用次数

    # 资源类型细分
    model_call_consumption = Column(DECIMAL(10, 2), default=0)  # 模型调用消费
    knowledge_base_consumption = Column(DECIMAL(10, 2), default=0)  # 知识库消费
    agent_consumption = Column(DECIMAL(10, 2), default=0)  # 智能体消费

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    account = relationship("Account", backref="billing_stats")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "stat_date": self.stat_date.isoformat() if self.stat_date else None,
            "total_consumption": float(self.total_consumption) if self.total_consumption else 0,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "model_call_consumption": float(self.model_call_consumption) if self.model_call_consumption else 0,
            "knowledge_base_consumption": float(self.knowledge_base_consumption) if self.knowledge_base_consumption else 0,
            "agent_consumption": float(self.agent_consumption) if self.agent_consumption else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
