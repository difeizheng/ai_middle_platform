"""
实时计费集成服务
用于在 API 调用时进行实时计费
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
import logging

from .billing import BillingService, AccountService
from ..models.billing import BillingPlan

logger = logging.getLogger(__name__)


class BillingIntegration:
    """实时计费集成类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.billing_service = BillingService(db)
        self.account_service = AccountService(db)

    async def charge_for_api_call(
        self,
        user_id: str,
        model_name: str,
        tokens_used: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        call_count: int = 1,
        resource_type: str = "model_call",
        resource_id: Optional[str] = None,
        api_log_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        为 API 调用计费

        Args:
            user_id: 用户 ID
            model_name: 模型名称
            tokens_used: 总 token 使用量
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            call_count: 调用次数
            resource_type: 资源类型
            resource_id: 资源 ID
            api_log_id: API 日志 ID

        Returns:
            计费结果信息
        """
        try:
            # 获取或创建账户
            account = await self.account_service.get_or_create_account(user_id)

            # 获取账户的计费方案
            plan = None
            if account.billing_plan_id:
                plan = await self.billing_service.get_plan(account.billing_plan_id)

            # 如果没有计费方案，使用默认方案
            if not plan:
                default_plans = await self.billing_service.list_plans(is_default=True)
                if default_plans:
                    plan = default_plans[0]

            # 如果没有可用方案，免费使用
            if not plan:
                logger.warning(f"No billing plan found for user {user_id}, using free tier")
                return {
                    "charged": False,
                    "amount": 0,
                    "reason": "No billing plan configured",
                }

            # 计算费用
            cost = await self.billing_service.calculate_cost(
                plan=plan,
                tokens_used=tokens_used,
                call_count=call_count,
                model_name=model_name,
            )

            # 如果费用为 0，不计费
            if cost <= 0:
                return {
                    "charged": False,
                    "amount": 0,
                    "reason": "Free tier or zero cost",
                }

            # 执行扣费
            description = f"{resource_type} - {model_name} - {tokens_used} tokens"
            updated_account, record = await self.account_service.consume(
                account_id=account.id,
                amount=float(cost),
                resource_type=resource_type,
                resource_id=resource_id,
                tokens_used=tokens_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                call_count=call_count,
                api_log_id=api_log_id,
                description=description,
            )

            # 检查是否需要余额预警
            warning_message = None
            if account.is_warning_enabled and updated_account.balance < account.low_balance_warning:
                warning_message = (
                    f"余额不足警告：当前余额 {float(updated_account.balance):.2f}，"
                    f"低于预警阈值 {float(account.low_balance_warning):.2f}"
                )
                logger.warning(warning_message)

            return {
                "charged": True,
                "amount": float(cost),
                "balance": float(updated_account.balance),
                "tokens_used": tokens_used,
                "model_name": model_name,
                "warning": warning_message,
            }

        except Exception as e:
            logger.error(f"Billing error for user {user_id}: {e}")
            # 计费失败不阻断 API 调用，只记录日志
            return {
                "charged": False,
                "amount": 0,
                "error": str(e),
            }

    async def check_balance(
        self,
        user_id: str,
        required_amount: float = 0,
    ) -> Dict[str, Any]:
        """
        检查账户余额

        Args:
            user_id: 用户 ID
            required_amount: 需要的金额

        Returns:
            余额检查结果
        """
        try:
            account = await self.account_service.get_or_create_account(user_id)

            has_sufficient_balance = account.balance >= required_amount

            return {
                "account_id": account.id,
                "balance": float(account.balance),
                "currency": account.currency,
                "status": account.status,
                "has_sufficient_balance": has_sufficient_balance,
                "required_amount": required_amount,
                "shortfall": max(0, required_amount - float(account.balance)),
            }
        except Exception as e:
            logger.error(f"Balance check error for user {user_id}: {e}")
            return {
                "error": str(e),
                "has_sufficient_balance": False,
            }


# 全局实例（用于简单集成）
_billing_instances: Dict[int, BillingIntegration] = {}


def get_billing_integration(db: AsyncSession) -> BillingIntegration:
    """获取计费集成实例"""
    db_id = id(db)
    if db_id not in _billing_instances:
        _billing_instances[db_id] = BillingIntegration(db)
    return _billing_instances[db_id]


async def charge_api_call(
    db: AsyncSession,
    user_id: str,
    model_name: str,
    tokens_used: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Dict[str, Any]:
    """
    简便的计费函数，可直接在 API 中调用

    Usage:
        result = await charge_api_call(
            db=db,
            user_id=current_user.id,
            model_name="gpt-3.5-turbo",
            tokens_used=total_tokens,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )
    """
    integration = get_billing_integration(db)
    return await integration.charge_for_api_call(
        user_id=user_id,
        model_name=model_name,
        tokens_used=tokens_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
