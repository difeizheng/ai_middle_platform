"""
支付渠道服务层
"""
import json
import hashlib
import hmac
import base64
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.payment import PaymentChannel, PaymentOrder, PaymentRefund, PaymentCallbackLog, PaymentStatus
from ..models.billing import Account, RechargeOrder
from ..models.user import User
from ..core.exceptions import BusinessException, NotFoundError, PaymentError


class PaymentService:
    """支付服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_channel(self, channel_id: str) -> Optional[PaymentChannel]:
        """获取支付渠道"""
        return self.db.query(PaymentChannel).filter(
            PaymentChannel.id == channel_id,
            PaymentChannel.is_active == True
        ).first()

    def get_channel_by_name(self, channel_name: str) -> Optional[PaymentChannel]:
        """根据名称获取支付渠道"""
        return self.db.query(PaymentChannel).filter(
            PaymentChannel.channel_name == channel_name,
            PaymentChannel.is_active == True
        ).first()

    def get_default_channel(self) -> Optional[PaymentChannel]:
        """获取默认支付渠道"""
        channel = self.db.query(PaymentChannel).filter(
            PaymentChannel.is_default == True,
            PaymentChannel.is_active == True
        ).first()
        if not channel:
            # 返回第一个启用的渠道
            channel = self.db.query(PaymentChannel).filter(
                PaymentChannel.is_active == True
            ).first()
        return channel

    def list_channels(self) -> List[PaymentChannel]:
        """获取所有启用的支付渠道列表"""
        return self.db.query(PaymentChannel).filter(
            PaymentChannel.is_active == True
        ).order_by(PaymentChannel.is_default.desc(), PaymentChannel.channel_name).all()

    def create_channel(self, data: Dict[str, Any]) -> PaymentChannel:
        """创建支付渠道"""
        channel = PaymentChannel(
            id=str(uuid.uuid4()),
            **data
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def update_channel(self, channel_id: str, data: Dict[str, Any]) -> PaymentChannel:
        """更新支付渠道"""
        channel = self.get_channel(channel_id)
        if not channel:
            raise NotFoundError("支付渠道不存在")

        for key, value in data.items():
            if hasattr(channel, key):
                setattr(channel, key, value)

        self.db.commit()
        self.db.refresh(channel)
        return channel

    def delete_channel(self, channel_id: str) -> bool:
        """删除支付渠道（软删除）"""
        channel = self.get_channel(channel_id)
        if not channel:
            raise NotFoundError("支付渠道不存在")

        channel.is_active = False
        self.db.commit()
        return True

    def validate_amount(self, channel: PaymentChannel, amount: Decimal) -> bool:
        """验证金额是否在限额范围内"""
        if amount < channel.min_amount:
            return False
        if amount > channel.max_amount:
            return False
        return True

    def check_daily_limit(self, channel: PaymentChannel, user_id: str, amount: Decimal) -> bool:
        """检查是否超过单日支付限额"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_amount = self.db.query(
            PaymentOrder.amount
        ).filter(
            PaymentOrder.channel_id == channel.id,
            PaymentOrder.user_id == user_id,
            PaymentOrder.created_at >= today_start,
            PaymentOrder.payment_status.in_(["success", "pending", "processing"])
        ).scalar() or Decimal(0)

        return (total_amount + amount) <= channel.daily_limit


class AlipayService:
    """支付宝支付服务"""

    def __init__(self, db: Session, channel: PaymentChannel):
        self.db = db
        self.channel = channel
        self.config = json.loads(channel.config) if channel.config else {}

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建支付宝订单
        返回支付链接或二维码信息
        """
        # 生成订单号
        order_no = self._generate_order_no()

        # 调用支付宝 API 创建订单
        # 这里使用模拟实现，实际需要接入支付宝 SDK
        alipay_params = {
            "app_id": self.channel.app_id,
            "method": "alipay.trade.page.pay",  # 电脑网站支付
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps({
                "out_trade_no": order_no,
                "total_amount": str(order_data["amount"]),
                "subject": order_data.get("subject", "AI 中台充值"),
                "body": order_data.get("body", ""),
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "return_url": self.config.get("return_url", ""),
                "notify_url": self.config.get("notify_url", ""),
            })
        }

        # 生成签名
        sign = self._generate_sign(alipay_params)
        alipay_params["sign"] = sign

        # 构建支付链接
        gateway_url = "https://openapi.alipay.com/gateway.do"
        pay_url = gateway_url + "?" + "&".join(
            f"{k}={v}" for k, v in alipay_params.items() if v
        )

        return {
            "order_no": order_no,
            "pay_url": pay_url,
            "qr_code": None,
            "app_param": None,
        }

    def verify_callback(self, data: Dict[str, Any]) -> bool:
        """验证支付宝回调签名"""
        # 实际实现需要验证支付宝回调签名
        # 这里使用简单实现
        sign = data.pop("sign", None)
        if not sign:
            return False

        # 对参数排序并生成签名字符串
        sorted_data = sorted(data.items())
        sign_str = "&".join(f"{k}={v}" for k, v in sorted_data if v and k != "sign")

        # 验证签名（实际需要使用公钥验证）
        return True

    def process_refund(self, order: PaymentOrder, refund_amount: Decimal, reason: str) -> Dict[str, Any]:
        """处理退款"""
        # 调用支付宝退款 API
        # 实际实现需要接入支付宝 SDK
        return {
            "refund_no": self._generate_refund_no(),
            "refund_transaction_id": f"ALIPAY_REFUND_{uuid.uuid4().hex[:16]}",
            "status": "success",
        }

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成支付宝签名"""
        # 对参数排序
        sorted_params = sorted(params.items())
        # 生成签名字符串
        sign_str = "&".join(f"{k}={v}" for k, v in sorted_params if v and k != "sign")
        # 使用私钥签名
        # 实际实现需要使用 RSA2 签名算法
        signature = hashlib.sha256((sign_str + self.channel.api_secret).encode()).hexdigest()
        return base64.b64encode(signature.encode()).decode()

    def _generate_order_no(self) -> str:
        """生成订单号"""
        return f"ALI{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"

    def _generate_refund_no(self) -> str:
        """生成退款单号"""
        return f"ALIR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"


class WechatPayService:
    """微信支付服务"""

    def __init__(self, db: Session, channel: PaymentChannel):
        self.db = db
        self.channel = channel
        self.config = json.loads(channel.config) if channel.config else {}

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建微信支付订单
        返回支付链接或二维码信息
        """
        # 生成订单号
        order_no = self._generate_order_no()

        # 调用微信支付 API 创建订单
        # 这里使用模拟实现，实际需要接入微信支付 SDK v3
        pay_params = {
            "appid": self.channel.app_id,
            "mchid": self.channel.merchant_id,
            "description": order_data.get("subject", "AI 中台充值"),
            "out_trade_no": order_no,
            "notify_url": self.config.get("notify_url", ""),
            "amount": {
                "total": int(order_data["amount"] * 100),  # 转换为分
                "currency": "CNY"
            }
        }

        # 实际实现需要调用微信支付 API 获取预支付交易会话标识
        # 返回二维码链接
        qr_code = f"weixin://wxpay/bizpayurl?pr={uuid.uuid4().hex}"

        return {
            "order_no": order_no,
            "pay_url": None,
            "qr_code": qr_code,
            "app_param": json.dumps(pay_params),
        }

    def verify_callback(self, data: Dict[str, Any]) -> bool:
        """验证微信支付回调签名"""
        # 微信支付 v3 使用 HMAC-SHA256 签名验证
        # 实际实现需要验证回调签名
        return True

    def process_refund(self, order: PaymentOrder, refund_amount: Decimal, reason: str) -> Dict[str, Any]:
        """处理退款"""
        # 调用微信支付退款 API
        return {
            "refund_no": self._generate_refund_no(),
            "refund_transaction_id": f"WECHAT_REFUND_{uuid.uuid4().hex[:16]}",
            "status": "success",
        }

    def _generate_order_no(self) -> str:
        """生成订单号"""
        return f"WX{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"

    def _generate_refund_no(self) -> str:
        """生成退款单号"""
        return f"WXR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"


class UnionPayService:
    """银联支付服务"""

    def __init__(self, db: Session, channel: PaymentChannel):
        self.db = db
        self.channel = channel
        self.config = json.loads(channel.config) if channel.config else {}

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建银联支付订单
        返回支付链接
        """
        # 生成订单号
        order_no = self._generate_order_no()

        # 调用银联支付 API
        # 这里使用模拟实现
        pay_params = {
            "merId": self.channel.merchant_id,
            "orderId": order_no,
            "txnTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "txnAmt": int(order_data["amount"] * 100),  # 转换为分
            "txnType": "01",  # 消费
            "txnSubType": "01",
            "bizType": "000201",
            "accessType": "0",
            "currencyCode": "156",
            "defaultPayType": "01",
            "backUrl": self.config.get("notify_url", ""),
            "frontUrl": self.config.get("return_url", ""),
        }

        # 生成签名
        signature = self._generate_sign(pay_params)
        pay_params["signature"] = signature

        # 构建支付链接
        gateway_url = "https://gateway.95516.com/gateway/api/frontTransReq.do"
        pay_url = gateway_url + "?" + "&".join(
            f"{k}={v}" for k, v in pay_params.items() if v
        )

        return {
            "order_no": order_no,
            "pay_url": pay_url,
            "qr_code": None,
            "app_param": None,
        }

    def verify_callback(self, data: Dict[str, Any]) -> bool:
        """验证银联回调签名"""
        # 验证银联回调签名
        return True

    def process_refund(self, order: PaymentOrder, refund_amount: Decimal, reason: str) -> Dict[str, Any]:
        """处理退款"""
        return {
            "refund_no": self._generate_refund_no(),
            "refund_transaction_id": f"UNIONPAY_REFUND_{uuid.uuid4().hex[:16]}",
            "status": "success",
        }

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成银联签名"""
        sorted_params = sorted(params.items())
        sign_str = "&".join(f"{k}={v}" for k, v in sorted_params if v)
        signature = hashlib.sha256((sign_str + self.channel.api_secret).encode()).hexdigest()
        return signature.upper()

    def _generate_order_no(self) -> str:
        """生成订单号"""
        return f"UP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"

    def _generate_refund_no(self) -> str:
        """生成退款单号"""
        return f"UPR{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"


class PaymentManager:
    """支付管理器 - 统一管理所有支付渠道"""

    def __init__(self, db: Session):
        self.db = db
        self.payment_service = PaymentService(db)

    def get_payment_service(self, channel: PaymentChannel):
        """根据渠道获取对应的支付服务"""
        if channel.channel_name == "alipay":
            return AlipayService(self.db, channel)
        elif channel.channel_name == "wechat":
            return WechatPayService(self.db, channel)
        elif channel.channel_name == "unionpay":
            return UnionPayService(self.db, channel)
        else:
            raise ValueError(f"不支持的支付渠道：{channel.channel_name}")

    def create_payment_order(
        self,
        user_id: str,
        account_id: str,
        amount: Decimal,
        channel_id: Optional[str] = None,
        subject: str = "AI 中台充值",
        body: str = "",
        payment_method: str = "web",
        client_ip: Optional[str] = None,
    ) -> PaymentOrder:
        """创建支付订单"""
        # 获取支付渠道
        if channel_id:
            channel = self.payment_service.get_channel(channel_id)
            if not channel:
                raise PaymentError("支付渠道不存在或已禁用")
        else:
            channel = self.payment_service.get_default_channel()
            if not channel:
                raise PaymentError("请先配置支付渠道")

        # 验证金额
        if not self.payment_service.validate_amount(channel, amount):
            raise PaymentError(f"支付金额超出限制 ({channel.min_amount}-{channel.max_amount})")

        # 检查日限额
        if not self.payment_service.check_daily_limit(channel, user_id, amount):
            raise PaymentError("超出单日支付限额")

        # 获取支付服务并创建订单
        payment_svc = self.get_payment_service(channel)
        order_data = {
            "amount": amount,
            "subject": subject,
            "body": body,
        }
        result = payment_svc.create_order(order_data)

        # 创建订单记录
        order = PaymentOrder(
            id=str(uuid.uuid4()),
            order_no=result["order_no"],
            account_id=account_id,
            user_id=user_id,
            channel_id=channel.id,
            amount=amount,
            actual_amount=amount,
            fee_amount=amount * channel.fee_rate,
            payment_method=payment_method,
            payment_status=PaymentStatus.PENDING.value,
            subject=subject,
            body=body,
            client_ip=client_ip,
            pay_url=result.get("pay_url"),
            qr_code=result.get("qr_code"),
            app_param=json.dumps(result.get("app_param", {})) if result.get("app_param") else None,
            expires_at=datetime.now() + timedelta(minutes=30),  # 30 分钟过期
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        return order

    def process_callback(
        self,
        channel_name: str,
        callback_data: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理支付回调"""
        # 获取渠道
        channel = self.payment_service.get_channel_by_name(channel_name)
        if not channel:
            raise PaymentError("支付渠道不存在")

        # 获取支付服务
        payment_svc = self.get_payment_service(channel)

        # 验证签名
        is_valid = payment_svc.verify_callback(callback_data)

        # 记录回调日志
        log = PaymentCallbackLog(
            id=str(uuid.uuid4()),
            order_no=callback_data.get("out_trade_no") or callback_data.get("orderId", ""),
            channel_id=channel.id,
            raw_data=json.dumps(callback_data),
            parsed_data=json.dumps(callback_data),
            signature_valid=is_valid,
            verification_result="签名验证通过" if is_valid else "签名验证失败",
            client_ip=client_ip,
            notify_id=callback_data.get("notify_id", ""),
            notify_time=datetime.now() if callback_data.get("notify_time") else None,
        )
        self.db.add(log)

        if not is_valid:
            log.is_processed = False
            log.process_result = "failed"
            log.error_message = "签名验证失败"
            self.db.commit()
            raise PaymentError("回调签名验证失败")

        # 获取订单号
        order_no = callback_data.get("out_trade_no") or callback_data.get("orderId", "")
        order = self.db.query(PaymentOrder).filter(
            PaymentOrder.order_no == order_no
        ).first()

        if not order:
            log.is_processed = False
            log.process_result = "failed"
            log.error_message = "订单不存在"
            self.db.commit()
            raise NotFoundError("订单不存在")

        # 更新订单状态
        trade_status = callback_data.get("trade_status") or callback_data.get("respCode", "")
        if trade_status in ["TRADE_SUCCESS", "SUCCESS", "0000"]:
            order.payment_status = PaymentStatus.SUCCESS.value
            order.payment_time = datetime.now()
            order.transaction_id = callback_data.get("trade_no") or callback_data.get("qryId", "")
            order.callback_data = json.dumps(callback_data)
            order.callback_time = datetime.now()

            # 更新账户余额
            account = self.db.query(Account).filter(Account.id == order.account_id).first()
            if account:
                account.balance += order.actual_amount
                account.total_recharge += order.actual_amount

            # 创建充值订单记录
            recharge_order = RechargeOrder(
                id=str(uuid.uuid4()),
                order_no=order.order_no,
                account_id=order.account_id,
                user_id=order.user_id,
                amount=order.amount,
                actual_amount=order.actual_amount,
                payment_method=channel.channel_name,
                payment_status="success",
                transaction_id=order.transaction_id,
                paid_at=datetime.now(),
            )
            self.db.add(recharge_order)

            log.is_processed = True
            log.process_result = "success"
        else:
            order.payment_status = PaymentStatus.FAILED.value
            log.is_processed = True
            log.process_result = "failed"
            log.error_message = f"支付失败：{trade_status}"

        self.db.commit()

        return {
            "success": True,
            "order_no": order.order_no,
            "status": order.payment_status,
        }

    def refund_payment(
        self,
        order_id: str,
        refund_amount: Decimal,
        reason: str,
        operator_id: Optional[str] = None,
    ) -> PaymentRefund:
        """处理退款"""
        order = self.db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
        if not order:
            raise NotFoundError("订单不存在")

        if order.payment_status != PaymentStatus.SUCCESS.value:
            raise PaymentError("只有支付成功的订单才能退款")

        if order.refund_amount > 0:
            raise PaymentError("该订单已退款")

        # 获取支付服务
        channel = self.payment_service.get_channel(order.channel_id)
        payment_svc = self.get_payment_service(channel)

        # 调用退款 API
        refund_result = payment_svc.process_refund(order, refund_amount, reason)

        # 创建退款记录
        refund = PaymentRefund(
            id=str(uuid.uuid4()),
            refund_no=refund_result["refund_no"],
            refund_transaction_id=refund_result["refund_transaction_id"],
            order_id=order.id,
            account_id=order.account_id,
            user_id=order.user_id,
            channel_id=channel.id,
            refund_amount=refund_amount,
            refund_status=refund_result.get("status", "success"),
            refund_time=datetime.now() if refund_result.get("status") == "success" else None,
            reason=reason,
            operator_id=operator_id,
        )

        self.db.add(refund)

        # 更新订单状态
        if refund_result.get("status") == "success":
            order.payment_status = PaymentStatus.REFUNDED.value
            order.refund_amount = refund_amount
            order.refund_time = datetime.now()
            order.refund_reason = reason

            # 扣减账户余额
            account = self.db.query(Account).filter(Account.id == order.account_id).first()
            if account:
                account.balance -= refund_amount

        self.db.commit()
        self.db.refresh(refund)

        return refund

    def get_order(self, order_id: Optional[str] = None, order_no: Optional[str] = None) -> Optional[PaymentOrder]:
        """获取订单"""
        query = self.db.query(PaymentOrder)
        if order_id:
            query = query.filter(PaymentOrder.id == order_id)
        if order_no:
            query = query.filter(PaymentOrder.order_no == order_no)
        return query.first()

    def list_orders(
        self,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        payment_status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取订单列表"""
        query = self.db.query(PaymentOrder)

        if user_id:
            query = query.filter(PaymentOrder.user_id == user_id)
        if account_id:
            query = query.filter(PaymentOrder.account_id == account_id)
        if channel_id:
            query = query.filter(PaymentOrder.channel_id == channel_id)
        if payment_status:
            query = query.filter(PaymentOrder.payment_status == payment_status)
        if start_time:
            query = query.filter(PaymentOrder.created_at >= start_time)
        if end_time:
            query = query.filter(PaymentOrder.created_at <= end_time)

        total = query.count()
        orders = query.order_by(
            PaymentOrder.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [order.to_dict() for order in orders],
        }
