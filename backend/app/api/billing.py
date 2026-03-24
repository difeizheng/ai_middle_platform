"""
计费系统 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.models.billing import BillingPlan, Account, BillingRecord, RechargeOrder
from app.services.billing import BillingService, AccountService, RechargeOrderService
from app.utils.permissions import verify_admin_user  # 管理员权限检查

router = APIRouter()


# ========== 计费方案管理 ==========

@router.get("/plans")
async def list_billing_plans(
    is_active: Optional[bool] = Query(True, description="是否生效"),
    billing_type: Optional[str] = Query(None, description="计费类型"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取计费方案列表"""
    service = BillingService(db)
    plans = await service.list_plans(is_active=is_active, billing_type=billing_type)

    return {
        "success": True,
        "data": [plan.to_dict() for plan in plans],
    }


@router.get("/plans/{plan_id}")
async def get_billing_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取计费方案详情"""
    service = BillingService(db)
    plan = await service.get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="计费方案不存在",
        )

    return {
        "success": True,
        "data": plan.to_dict(),
    }


@router.post("/plans")
async def create_billing_plan(
    name: str = Body(..., description="计费方案名称"),
    billing_type: str = Body(..., description="计费类型：token/call/subscription"),
    description: str = Body(None, description="方案描述"),
    price_per_1k_tokens: float = Body(0, description="每 1000 tokens 价格"),
    price_per_call: float = Body(0, description="每次调用价格"),
    monthly_fee: float = Body(0, description="月费"),
    quota_limit: int = Body(0, description="配额限制"),
    overage_rate: float = Body(1, description="超额费率系数"),
    model_pricing: Dict[str, float] = Body(default_factory=dict, description="模型价格系数"),
    is_default: bool = Body(False, description="是否默认方案"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建计费方案"""
    service = BillingService(db)

    # 检查名称是否已存在
    existing_plans = await service.list_plans()
    for plan in existing_plans:
        if plan.name == name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"计费方案名称已存在：{name}",
            )

    plan = await service.create_plan(
        name=name,
        billing_type=billing_type,
        description=description,
        price_per_1k_tokens=price_per_1k_tokens,
        price_per_call=price_per_call,
        monthly_fee=monthly_fee,
        quota_limit=quota_limit,
        overage_rate=overage_rate,
        model_pricing=model_pricing,
        is_default=is_default,
    )

    return {
        "success": True,
        "data": plan.to_dict(),
    }


@router.put("/plans/{plan_id}")
async def update_billing_plan(
    plan_id: str,
    name: Optional[str] = Body(None, description="计费方案名称"),
    description: Optional[str] = Body(None, description="方案描述"),
    price_per_1k_tokens: Optional[float] = Body(None, description="每 1000 tokens 价格"),
    price_per_call: Optional[float] = Body(None, description="每次调用价格"),
    monthly_fee: Optional[float] = Body(None, description="月费"),
    quota_limit: Optional[int] = Body(None, description="配额限制"),
    overage_rate: Optional[float] = Body(None, description="超额费率系数"),
    model_pricing: Optional[Dict[str, float]] = Body(None, description="模型价格系数"),
    is_active: Optional[bool] = Body(None, description="是否生效"),
    is_default: Optional[bool] = Body(None, description="是否默认方案"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新计费方案"""
    service = BillingService(db)

    update_data = {
        k: v for k, v in {
            "name": name,
            "description": description,
            "price_per_1k_tokens": price_per_1k_tokens,
            "price_per_call": price_per_call,
            "monthly_fee": monthly_fee,
            "quota_limit": quota_limit,
            "overage_rate": overage_rate,
            "model_pricing": model_pricing,
            "is_active": is_active,
            "is_default": is_default,
        }.items() if v is not None
    }

    plan = await service.update_plan(plan_id, **update_data)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="计费方案不存在",
        )

    return {
        "success": True,
        "data": plan.to_dict(),
    }


@router.delete("/plans/{plan_id}")
async def delete_billing_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除计费方案"""
    service = BillingService(db)
    success = await service.delete_plan(plan_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="计费方案不存在",
        )

    return {
        "success": True,
        "message": "计费方案已删除",
    }


# ========== 账户管理 ==========

@router.get("/account")
async def get_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户账户信息"""
    service = AccountService(db)
    account = await service.get_or_create_account(current_user.id)

    # 获取计费方案信息
    billing_plan = None
    if account.billing_plan_id:
        billing_service = BillingService(db)
        billing_plan_obj = await billing_service.get_plan(account.billing_plan_id)
        if billing_plan_obj:
            billing_plan = billing_plan_obj.to_dict()

    return {
        "success": True,
        "data": {
            **account.to_dict(),
            "billing_plan": billing_plan,
        },
    }


@router.get("/accounts/{account_id}")
async def get_account_by_id(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取账户信息（管理员）"""
    service = AccountService(db)
    account = await service.get_account(account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在",
        )

    return {
        "success": True,
        "data": account.to_dict(),
    }


@router.post("/accounts")
async def create_account(
    billing_plan_id: Optional[str] = Body(None, description="计费方案 ID"),
    initial_balance: float = Body(0, description="初始余额"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建账户"""
    service = AccountService(db)

    try:
        account = await service.create_account(
            user_id=current_user.id,
            billing_plan_id=billing_plan_id,
            initial_balance=initial_balance,
        )
        return {
            "success": True,
            "data": account.to_dict(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/account/plan")
async def update_account_plan(
    billing_plan_id: str = Body(..., description="计费方案 ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新账户计费方案"""
    service = AccountService(db)
    account = await service.get_or_create_account(current_user.id)

    # 验证计费方案是否存在
    billing_service = BillingService(db)
    plan = await billing_service.get_plan(billing_plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="计费方案不存在",
        )

    account.billing_plan_id = billing_plan_id
    await db.commit()
    await db.refresh(account)

    return {
        "success": True,
        "data": account.to_dict(),
    }


# ========== 充值管理 ==========

@router.post("/account/recharge")
async def recharge_account(
    amount: float = Body(..., gt=0, description="充值金额"),
    payment_method: str = Body("transfer", description="支付方式：alipay/wechat/bank/transfer"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """账户充值"""
    account_service = AccountService(db)
    account = await account_service.get_or_create_account(current_user.id)

    # 创建充值订单
    order_service = RechargeOrderService(db)
    order = await order_service.create_order(
        account_id=account.id,
        user_id=current_user.id,
        amount=amount,
        payment_method=payment_method,
        description="账户充值",
    )

    # 模拟支付成功（实际应调用支付接口）
    # 这里直接完成充值
    await order_service.mark_as_paid(order.id, transaction_id=f"SIMULATED_{order.order_no}")
    updated_account, record = await account_service.recharge(
        account_id=account.id,
        amount=amount,
        order_id=order.id,
        description=f"充值 - {order.order_no}",
    )

    return {
        "success": True,
        "data": {
            "account": updated_account.to_dict(),
            "order": order.to_dict(),
            "record": record.to_dict(),
        },
    }


@router.get("/account/recharge/orders")
async def list_recharge_orders(
    payment_status: Optional[str] = Query(None, description="支付状态"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取充值订单列表"""
    account_service = AccountService(db)
    account = await account_service.get_or_create_account(current_user.id)

    order_service = RechargeOrderService(db)
    orders = await order_service.list_orders(
        user_id=current_user.id,
        payment_status=payment_status,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": [order.to_dict() for order in orders],
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
    }


# ========== 计费记录 ==========

@router.get("/account/records")
async def list_billing_records(
    record_type: Optional[str] = Query(None, description="记录类型：charge/consume/refund"),
    start_date: Optional[str] = Query(None, description="开始日期 (ISO 格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO 格式)"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取计费记录列表"""
    account_service = AccountService(db)
    account = await account_service.get_or_create_account(current_user.id)

    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="开始日期格式不正确，请使用 ISO 格式",
            )
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="结束日期格式不正确，请使用 ISO 格式",
            )

    records = await account_service.get_billing_records(
        account_id=account.id,
        record_type=record_type,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": [record.to_dict() for record in records],
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
    }


# ========== 统计信息 ==========

@router.get("/account/stats")
async def get_account_stats(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取账户统计信息"""
    account_service = AccountService(db)
    account = await account_service.get_or_create_account(current_user.id)

    stats = await account_service.get_stats(
        account_id=account.id,
        days=days,
    )

    return {
        "success": True,
        "data": stats,
    }


@router.get("/account/usage/trend")
async def get_usage_trend(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取使用趋势"""
    from sqlalchemy import select, func
    from datetime import timedelta

    account_service = AccountService(db)
    account = await account_service.get_or_create_account(current_user.id)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 按天统计消费
    result = await db.execute(
        select(
            func.date(BillingRecord.created_at).label("stat_date"),
            func.sum(BillingRecord.amount).label("total_amount"),
            func.sum(BillingRecord.tokens_used).label("total_tokens"),
            func.sum(BillingRecord.call_count).label("total_calls"),
        )
        .where(BillingRecord.account_id == account.id)
        .where(BillingRecord.record_type == "consume")
        .where(BillingRecord.created_at >= start_date)
        .group_by(func.date(BillingRecord.created_at))
        .order_by(func.date(BillingRecord.created_at))
    )

    trend_data = [
        {
            "date": row[0].isoformat() if row[0] else None,
            "total_amount": float(row[1]) if row[1] else 0,
            "total_tokens": row[2] or 0,
            "total_calls": row[3] or 0,
        }
        for row in result.fetchall()
    ]

    return {
        "success": True,
        "data": {
            "days": days,
            "trend": trend_data,
        },
    }


# ========== 管理员功能 ==========

@router.get("/admin/accounts")
async def list_all_accounts(
    status: Optional[str] = Query(None, description="账户状态"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
    db: AsyncSession = Depends(get_db),
):
    """获取所有账户列表（管理员）"""
    query = select(Account)

    if status:
        query = query.where(Account.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    accounts = result.scalars().all()

    # 获取总数
    count_query = select(func.count()).select_from(Account)
    if status:
        count_query = count_query.where(Account.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "success": True,
        "data": [acc.to_dict() for acc in accounts],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/admin/stats/overview")
async def get_billing_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取计费概览（管理员）"""
    # 总收入统计
    total_recharge_result = await db.execute(
        select(func.sum(Account.total_recharge))
    )
    total_recharge = total_recharge_result.scalar() or 0

    # 总消费统计
    total_consumption_result = await db.execute(
        select(func.sum(Account.total_consumption))
    )
    total_consumption = total_consumption_result.scalar() or 0

    # 活跃账户数
    active_accounts_result = await db.execute(
        select(func.count())
        .select_from(Account)
        .where(Account.status == "active")
    )
    active_accounts = active_accounts_result.scalar() or 0

    # 今日收入
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_recharge_result = await db.execute(
        select(func.sum(BillingRecord.amount))
        .where(BillingRecord.record_type == "charge")
        .where(BillingRecord.created_at >= today_start)
    )
    today_recharge = today_recharge_result.scalar() or 0

    return {
        "success": True,
        "data": {
            "total_recharge": float(total_recharge),
            "total_consumption": float(total_consumption),
            "active_accounts": active_accounts,
            "today_recharge": float(today_recharge),
        },
    }
