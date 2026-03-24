"""
计费服务层
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import uuid
import json

from ..models.billing import BillingPlan, Account, BillingRecord, RechargeOrder, BillingStats
from ..models.user import User
from ..core.exceptions import AppException


class BillingService:
    """计费服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_plan(self, plan_id: str) -> Optional[BillingPlan]:
        """获取计费方案"""
        result = await self.db.execute(
            select(BillingPlan).where(BillingPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def list_plans(
        self,
        is_active: Optional[bool] = None,
        billing_type: Optional[str] = None,
    ) -> List[BillingPlan]:
        """获取计费方案列表"""
        query = select(BillingPlan)

        if is_active is not None:
            query = query.where(BillingPlan.is_active == is_active)
        if billing_type:
            query = query.where(BillingPlan.billing_type == billing_type)

        query = query.order_by(BillingPlan.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_plan(
        self,
        name: str,
        billing_type: str,
        description: Optional[str] = None,
        price_per_1k_tokens: float = 0,
        price_per_call: float = 0,
        monthly_fee: float = 0,
        quota_limit: int = 0,
        overage_rate: float = 1,
        model_pricing: Optional[Dict[str, float]] = None,
        is_default: bool = False,
    ) -> BillingPlan:
        """创建计费方案"""
        # 如果设置为默认方案，先将其他方案设为非默认
        if is_default:
            await self.db.execute(
                BillingPlan.__table__.update()
                .where(BillingPlan.is_default == True)
                .values(is_default=False)
            )

        plan = BillingPlan(
            id=str(uuid.uuid4()),
            name=name,
            billing_type=billing_type,
            description=description,
            price_per_1k_tokens=Decimal(str(price_per_1k_tokens)),
            price_per_call=Decimal(str(price_per_call)),
            monthly_fee=Decimal(str(monthly_fee)),
            quota_limit=quota_limit,
            overage_rate=Decimal(str(overage_rate)),
            model_pricing=json.dumps(model_pricing or {}),
            is_default=is_default,
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def update_plan(
        self,
        plan_id: str,
        **kwargs,
    ) -> Optional[BillingPlan]:
        """更新计费方案"""
        result = await self.db.execute(
            select(BillingPlan).where(BillingPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            return None

        # 如果设置为默认方案，先将其他方案设为非默认
        if kwargs.get("is_default") and not plan.is_default:
            await self.db.execute(
                BillingPlan.__table__.update()
                .where(BillingPlan.id != plan_id)
                .where(BillingPlan.is_default == True)
                .values(is_default=False)
            )

        # 更新允许修改的字段
        allowed_fields = [
            "name", "billing_type", "description",
            "price_per_1k_tokens", "price_per_call", "monthly_fee",
            "quota_limit", "overage_rate", "model_pricing",
            "is_active", "is_default",
        ]
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(plan, field):
                if field == "model_pricing" and isinstance(value, dict):
                    value = json.dumps(value)
                elif field in ["price_per_1k_tokens", "price_per_call", "monthly_fee", "overage_rate"]:
                    value = Decimal(str(value))
                setattr(plan, field, value)

        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def delete_plan(self, plan_id: str) -> bool:
        """删除计费方案"""
        result = await self.db.execute(
            select(BillingPlan).where(BillingPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()

        if not plan:
            return False

        # 检查是否有账户正在使用此方案
        account_result = await self.db.execute(
            select(Account).where(Account.billing_plan_id == plan_id).limit(1)
        )
        if account_result.scalar_one_or_none():
            raise AppException("该计费方案正在被账户使用，无法删除")

        await self.db.delete(plan)
        await self.db.commit()
        return True

    async def calculate_cost(
        self,
        plan: BillingPlan,
        tokens_used: int = 0,
        call_count: int = 1,
        model_name: Optional[str] = None,
    ) -> Decimal:
        """计算费用"""
        # 获取模型价格系数
        model_pricing = json.loads(plan.model_pricing) if plan.model_pricing else {}
        model_multiplier = model_pricing.get(model_name, 1.0) if model_name else 1.0

        cost = Decimal("0")

        # 按 Token 计费
        if plan.billing_type == "token" and tokens_used > 0:
            price = plan.price_per_1k_tokens * Decimal(tokens_used) / Decimal(1000)
            cost += price * Decimal(str(model_multiplier))

        # 按调用次数计费
        elif plan.billing_type == "call":
            price = plan.price_per_call * Decimal(call_count)
            cost += price * Decimal(str(model_multiplier))

        # 应用超额费率
        if plan.quota_limit > 0:
            # TODO: 需要查询当前周期已使用量来计算是否超额
            pass

        cost = cost * plan.overage_rate
        return cost.quantize(Decimal("0.0001"))


class AccountService:
    """账户服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        result = await self.db.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_account_by_user_id(self, user_id: str) -> Optional[Account]:
        """通过用户 ID 获取账户"""
        result = await self.db.execute(
            select(Account).where(Account.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_account(
        self,
        user_id: str,
        billing_plan_id: Optional[str] = None,
        initial_balance: float = 0,
    ) -> Account:
        """创建账户"""
        # 检查用户是否已有账户
        existing = await self.get_account_by_user_id(user_id)
        if existing:
            raise AppException("该用户已存在账户")

        account = Account(
            id=str(uuid.uuid4()),
            user_id=user_id,
            balance=Decimal(str(initial_balance)),
            billing_plan_id=billing_plan_id,
        )
        self.db.add(account)

        # 如果有初始充值，创建计费记录
        if initial_balance > 0:
            record = BillingRecord(
                id=str(uuid.uuid4()),
                account_id=account.id,
                record_type="charge",
                amount=Decimal(str(initial_balance)),
                balance_before=Decimal("0"),
                balance_after=Decimal(str(initial_balance)),
                description="初始充值",
            )
            self.db.add(record)
            account.total_recharge = Decimal(str(initial_balance))

        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_or_create_account(self, user_id: str) -> Account:
        """获取或创建账户"""
        account = await self.get_account_by_user_id(user_id)
        if account:
            return account
        return await self.create_account(user_id)

    async def recharge(
        self,
        account_id: str,
        amount: float,
        order_id: Optional[str] = None,
        description: str = "充值",
    ) -> Tuple[Account, BillingRecord]:
        """账户充值"""
        account = await self.get_account(account_id)
        if not account:
            raise AppException("账户不存在")

        if amount <= 0:
            raise AppException("充值金额必须大于 0")

        amount_decimal = Decimal(str(amount))
        balance_before = account.balance
        balance_after = balance_before + amount_decimal

        # 创建计费记录
        record = BillingRecord(
            id=str(uuid.uuid4()),
            account_id=account_id,
            record_type="charge",
            amount=amount_decimal,
            balance_before=balance_before,
            balance_after=balance_after,
            order_id=order_id,
            description=description,
        )
        self.db.add(record)

        # 更新账户余额
        account.balance = balance_after
        account.total_recharge = account.total_recharge + amount_decimal

        await self.db.commit()
        await self.db.refresh(account)
        await self.db.refresh(record)
        return account, record

    async def consume(
        self,
        account_id: str,
        amount: float,
        resource_type: str,
        resource_id: Optional[str] = None,
        tokens_used: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        call_count: int = 1,
        api_log_id: Optional[str] = None,
        description: str = "消费",
    ) -> Tuple[Account, BillingRecord]:
        """账户消费"""
        account = await self.get_account(account_id)
        if not account:
            raise AppException("账户不存在")

        amount_decimal = Decimal(str(amount))

        # 检查余额是否充足
        if account.balance < amount_decimal:
            raise AppException(
                f"余额不足，当前余额：{float(account.balance):.2f}，需要：{float(amount):.2f}",
                status_code=402,
            )

        balance_before = account.balance
        balance_after = balance_before - amount_decimal

        # 创建计费记录
        record = BillingRecord(
            id=str(uuid.uuid4()),
            account_id=account_id,
            record_type="consume",
            amount=amount_decimal,
            balance_before=balance_before,
            balance_after=balance_after,
            resource_type=resource_type,
            resource_id=resource_id,
            tokens_used=tokens_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            call_count=call_count,
            api_log_id=api_log_id,
            description=description,
        )
        self.db.add(record)

        # 更新账户余额
        account.balance = balance_after
        account.total_consumption = account.total_consumption + amount_decimal

        await self.db.commit()
        await self.db.refresh(account)
        await self.db.refresh(record)
        return account, record

    async def refund(
        self,
        account_id: str,
        amount: float,
        description: str = "退款",
    ) -> Tuple[Account, BillingRecord]:
        """账户退款"""
        account = await self.get_account(account_id)
        if not account:
            raise AppException("账户不存在")

        amount_decimal = Decimal(str(amount))
        balance_before = account.balance
        balance_after = balance_before + amount_decimal

        # 创建计费记录
        record = BillingRecord(
            id=str(uuid.uuid4()),
            account_id=account_id,
            record_type="refund",
            amount=amount_decimal,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
        )
        self.db.add(record)

        # 更新账户余额
        account.balance = balance_after

        await self.db.commit()
        await self.db.refresh(account)
        await self.db.refresh(record)
        return account, record

    async def get_billing_records(
        self,
        account_id: str,
        record_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[BillingRecord]:
        """获取计费记录列表"""
        query = select(BillingRecord).where(BillingRecord.account_id == account_id)

        if record_type:
            query = query.where(BillingRecord.record_type == record_type)
        if start_date:
            query = query.where(BillingRecord.created_at >= start_date)
        if end_date:
            query = query.where(BillingRecord.created_at <= end_date)

        query = query.order_by(BillingRecord.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_stats(
        self,
        account_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """获取账户统计信息"""
        end_date = datetime.utcnow()
        start_date = datetime.utcnow()

        # 查询总记录数
        total_records_result = await self.db.execute(
            select(func.count()).select_from(BillingRecord)
            .where(BillingRecord.account_id == account_id)
        )
        total_records = total_records_result.scalar()

        # 查询今日消费
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await self.db.execute(
            select(func.sum(BillingRecord.amount))
            .where(BillingRecord.account_id == account_id)
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= today_start)
        )
        today_consumption = today_result.scalar() or 0

        # 查询本月消费
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_result = await self.db.execute(
            select(func.sum(BillingRecord.amount))
            .where(BillingRecord.account_id == account_id)
            .where(BillingRecord.record_type == "consume")
            .where(BillingRecord.created_at >= month_start)
        )
        month_consumption = month_result.scalar() or 0

        # 查询 Token 使用统计
        tokens_result = await self.db.execute(
            select(
                func.sum(BillingRecord.tokens_used),
                func.sum(BillingRecord.input_tokens),
                func.sum(BillingRecord.output_tokens),
                func.sum(BillingRecord.call_count),
            )
            .where(BillingRecord.account_id == account_id)
            .where(BillingRecord.created_at >= start_date)
        )
        tokens_stats = tokens_result.first() or (0, 0, 0, 0)

        return {
            "total_records": total_records,
            "today_consumption": float(today_consumption),
            "month_consumption": float(month_consumption),
            "period_days": days,
            "total_tokens": tokens_stats[0] or 0,
            "input_tokens": tokens_stats[1] or 0,
            "output_tokens": tokens_stats[2] or 0,
            "total_calls": tokens_stats[3] or 0,
        }


class RechargeOrderService:
    """充值订单服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(
        self,
        account_id: str,
        user_id: str,
        amount: float,
        payment_method: str,
        description: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> RechargeOrder:
        """创建充值订单"""
        # 生成订单号
        order_no = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

        order = RechargeOrder(
            id=str(uuid.uuid4()),
            order_no=order_no,
            account_id=account_id,
            user_id=user_id,
            amount=Decimal(str(amount)),
            payment_method=payment_method,
            description=description,
            client_ip=client_ip,
            expires_at=datetime.now().replace(hour=23, minute=59, second=59),
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_order(self, order_id: str) -> Optional[RechargeOrder]:
        """获取订单"""
        result = await self.db.execute(
            select(RechargeOrder).where(RechargeOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_order_by_no(self, order_no: str) -> Optional[RechargeOrder]:
        """通过订单号获取订单"""
        result = await self.db.execute(
            select(RechargeOrder).where(RechargeOrder.order_no == order_no)
        )
        return result.scalar_one_or_none()

    async def mark_as_paid(
        self,
        order_id: str,
        transaction_id: str,
    ) -> Optional[RechargeOrder]:
        """标记订单为已支付"""
        result = await self.db.execute(
            select(RechargeOrder).where(RechargeOrder.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            return None

        if order.payment_status != "pending":
            raise AppException(f"订单状态不正确：{order.payment_status}")

        order.payment_status = "success"
        order.transaction_id = transaction_id
        order.paid_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def list_orders(
        self,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        payment_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[RechargeOrder]:
        """获取订单列表"""
        query = select(RechargeOrder)

        if user_id:
            query = query.where(RechargeOrder.user_id == user_id)
        if account_id:
            query = query.where(RechargeOrder.account_id == account_id)
        if payment_status:
            query = query.where(RechargeOrder.payment_status == payment_status)

        query = query.order_by(RechargeOrder.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
