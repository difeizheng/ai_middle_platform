"""
支付渠道系统数据模型
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Float, DECIMAL, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..core.database import Base


class PaymentChannelType(str, enum.Enum):
    """支付渠道类型"""
    ALIPAY = "alipay"  # 支付宝
    WECHAT = "wechat"  # 微信支付
    UNIONPAY = "unionpay"  # 银联支付
    BANK_TRANSFER = "bank_transfer"  # 银行转账


class PaymentStatus(str, enum.Enum):
    """支付状态"""
    PENDING = "pending"  # 待支付
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"  # 支付成功
    FAILED = "failed"  # 支付失败
    REFUNDED = "refunded"  # 已退款
    CLOSED = "closed"  # 已关闭


class PaymentChannel(Base):
    """支付渠道配置表"""
    __tablename__ = "payment_channels"

    id = Column(String(36), primary_key=True, index=True)
    channel_name = Column(String(50), nullable=False, unique=True)  # 渠道名称：alipay/wechat/unionpay
    channel_type = Column(String(20), nullable=False)  # 渠道类型

    # 渠道配置信息
    display_name = Column(String(100))  # 显示名称
    description = Column(Text)  # 渠道描述
    icon_url = Column(String(255))  # 图标 URL

    # 认证配置（加密存储）
    app_id = Column(String(100))  # 应用 ID
    merchant_id = Column(String(100))  # 商户 ID
    api_key = Column(String(255))  # API Key（加密存储）
    api_secret = Column(String(500))  # API 密钥（加密存储）
    public_key = Column(Text)  # 公钥
    private_key = Column(Text)  # 私钥

    # 配置项
    config = Column(Text, default='{}')  # 额外配置（JSON 格式）

    # 渠道状态
    is_active = Column(Boolean, default=True)  # 是否启用
    is_default = Column(Boolean, default=False)  # 是否默认渠道
    support_refund = Column(Boolean, default=True)  # 是否支持退款

    # 限额配置
    min_amount = Column(DECIMAL(10, 2), default=0)  # 最小支付金额
    max_amount = Column(DECIMAL(10, 2), default=999999)  # 最大支付金额
    daily_limit = Column(DECIMAL(12, 2), default=999999)  # 单日支付限额

    # 费率配置
    fee_rate = Column(DECIMAL(5, 4), default=0)  # 渠道费率（0.006 = 0.6%）

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "channel_name": self.channel_name,
            "channel_type": self.channel_type,
            "display_name": self.display_name,
            "description": self.description,
            "icon_url": self.icon_url,
            "app_id": self.app_id,
            "merchant_id": self.merchant_id,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "support_refund": self.support_refund,
            "min_amount": float(self.min_amount) if self.min_amount else 0,
            "max_amount": float(self.max_amount) if self.max_amount else 999999,
            "daily_limit": float(self.daily_limit) if self.daily_limit else 999999,
            "fee_rate": float(self.fee_rate) if self.fee_rate else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentOrder(Base):
    """支付订单表"""
    __tablename__ = "payment_orders"

    id = Column(String(36), primary_key=True, index=True)
    order_no = Column(String(64), unique=True, nullable=False, index=True)  # 平台订单号
    transaction_id = Column(String(100), index=True)  # 支付渠道交易 ID

    # 关联信息
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    channel_id = Column(String(36), ForeignKey("payment_channels.id"), nullable=False)

    # 订单金额
    amount = Column(DECIMAL(10, 2), nullable=False)  # 订单金额
    actual_amount = Column(DECIMAL(10, 2))  # 实际支付金额（可能有优惠）
    fee_amount = Column(DECIMAL(10, 4), default=0)  # 渠道手续费

    # 支付信息
    payment_method = Column(String(20))  # 支付方式：app/web/h5/mini_program
    payment_status = Column(String(20), default="pending", index=True)  # 支付状态
    payment_time = Column(DateTime)  # 支付时间

    # 渠道回调数据
    callback_data = Column(Text, default='{}')  # 渠道回调原始数据（JSON）
    callback_time = Column(DateTime)  # 回调时间

    # 订单描述
    subject = Column(String(255))  # 订单标题
    body = Column(Text)  # 订单描述
    attach = Column(String(255))  # 附加数据

    # 客户端信息
    client_ip = Column(String(50))  # 客户端 IP
    user_agent = Column(String(500))  # User-Agent

    # 支付凭证
    pay_url = Column(String(500))  # 支付链接（H5/扫码）
    qr_code = Column(String(500))  # 二维码链接
    app_param = Column(Text)  # APP 支付参数（JSON）

    # 超时配置
    expires_at = Column(DateTime)  # 订单过期时间
    timeout_expression = Column(String(10))  # 超时时间配置

    # 退款信息
    refund_amount = Column(DECIMAL(10, 2), default=0)  # 退款金额
    refund_time = Column(DateTime)  # 退款时间
    refund_reason = Column(String(255))  # 退款原因

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    account = relationship("Account", backref="payment_orders")
    user = relationship("User", backref="payment_orders")
    channel = relationship("PaymentChannel", backref="orders")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "order_no": self.order_no,
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "amount": float(self.amount) if self.amount else 0,
            "actual_amount": float(self.actual_amount) if self.actual_amount else 0,
            "fee_amount": float(self.fee_amount) if self.fee_amount else 0,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "payment_time": self.payment_time.isoformat() if self.payment_time else None,
            "subject": self.subject,
            "body": self.body,
            "attach": self.attach,
            "client_ip": self.client_ip,
            "pay_url": self.pay_url,
            "qr_code": self.qr_code,
            "app_param": json.loads(self.app_param) if self.app_param else {},
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "refund_amount": float(self.refund_amount) if self.refund_amount else 0,
            "refund_time": self.refund_time.isoformat() if self.refund_time else None,
            "refund_reason": self.refund_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentRefund(Base):
    """支付退款表"""
    __tablename__ = "payment_refunds"

    id = Column(String(36), primary_key=True, index=True)
    refund_no = Column(String(64), unique=True, nullable=False, index=True)  # 退款单号
    refund_transaction_id = Column(String(100))  # 渠道退款交易 ID

    # 关联订单
    order_id = Column(String(36), ForeignKey("payment_orders.id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    channel_id = Column(String(36), ForeignKey("payment_channels.id"), nullable=False)

    # 退款金额
    refund_amount = Column(DECIMAL(10, 2), nullable=False)  # 退款金额
    refund_fee = Column(DECIMAL(10, 4), default=0)  # 退款手续费

    # 退款状态
    refund_status = Column(String(20), default="pending", index=True)  # pending/processing/success/failed
    refund_time = Column(DateTime)  # 退款成功时间

    # 退款原因
    reason = Column(String(255), nullable=False)  # 退款原因
    description = Column(Text)  # 详细描述

    # 渠道回调数据
    callback_data = Column(Text, default='{}')  # 渠道回调数据

    # 操作信息
    operator_id = Column(String(36))  # 操作人 ID
    operator_comment = Column(String(255))  # 操作人备注

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    order = relationship("PaymentOrder", backref="refunds")
    account = relationship("Account", backref="payment_refunds")
    user = relationship("User", backref="payment_refunds")
    channel = relationship("PaymentChannel", backref="refunds")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "refund_no": self.refund_no,
            "refund_transaction_id": self.refund_transaction_id,
            "order_id": self.order_id,
            "account_id": self.account_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "refund_amount": float(self.refund_amount) if self.refund_amount else 0,
            "refund_fee": float(self.refund_fee) if self.refund_fee else 0,
            "refund_status": self.refund_status,
            "refund_time": self.refund_time.isoformat() if self.refund_time else None,
            "reason": self.reason,
            "description": self.description,
            "operator_id": self.operator_id,
            "operator_comment": self.operator_comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentCallbackLog(Base):
    """支付回调日志表"""
    __tablename__ = "payment_callback_logs"

    id = Column(String(36), primary_key=True, index=True)
    order_no = Column(String(64), nullable=False, index=True)  # 订单号
    channel_id = Column(String(36), ForeignKey("payment_channels.id"), nullable=False)

    # 回调数据
    raw_data = Column(Text, nullable=False)  # 原始回调数据
    parsed_data = Column(Text, default='{}')  # 解析后的数据

    # 验证结果
    signature_valid = Column(Boolean)  # 签名验证结果
    verification_result = Column(Text)  # 验证详情

    # 处理结果
    is_processed = Column(Boolean, default=False)  # 是否已处理
    process_result = Column(String(20))  # success/failed
    error_message = Column(Text)  # 错误信息

    # 通知信息
    notify_id = Column(String(100))  # 渠道通知 ID
    notify_time = Column(DateTime)  # 通知时间
    notify_type = Column(String(20))  # 通知类型

    client_ip = Column(String(50))  # 回调 IP

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    channel = relationship("PaymentChannel", backref="callback_logs")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "order_no": self.order_no,
            "channel_id": self.channel_id,
            "raw_data": self.raw_data,
            "parsed_data": json.loads(self.parsed_data) if self.parsed_data else {},
            "signature_valid": self.signature_valid,
            "verification_result": self.verification_result,
            "is_processed": self.is_processed,
            "process_result": self.process_result,
            "error_message": self.error_message,
            "notify_id": self.notify_id,
            "notify_time": self.notify_time.isoformat() if self.notify_time else None,
            "notify_type": self.notify_type,
            "client_ip": self.client_ip,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
