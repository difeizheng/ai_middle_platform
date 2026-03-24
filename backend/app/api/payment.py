"""
支付渠道 API 路由
"""
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional, Dict, Any, List

from ..core.database import get_db
from ..services.payment import PaymentManager, PaymentService
from ..models.payment import PaymentChannel, PaymentOrder, PaymentRefund, PaymentCallbackLog
from ..auth.jwt import get_current_user
from ..models.user import User
from ..models.billing import Account
from ..core.exceptions import create_error_response
from ..utils.permissions import verify_admin_user  # 管理员权限检查

router = APIRouter(prefix="/api/v1/payment", tags=["支付管理"])


# ==================== 支付渠道管理 ====================

@router.get("/channels", response_model=Dict[str, Any])
def list_payment_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有启用的支付渠道列表"""
    payment_service = PaymentService(db)
    channels = payment_service.list_channels()
    return {
        "success": True,
        "data": [channel.to_dict() for channel in channels],
    }


@router.get("/channels/default", response_model=Dict[str, Any])
def get_default_channel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取默认支付渠道"""
    payment_service = PaymentService(db)
    channel = payment_service.get_default_channel()
    if not channel:
        return {
            "success": False,
            "message": "请先配置支付渠道",
        }
    return {
        "success": True,
        "data": channel.to_dict(),
    }


# ==================== 支付订单管理 ====================

@router.post("/create", response_model=Dict[str, Any])
def create_payment_order(
    amount: Decimal = Body(..., description="充值金额", gt=0),
    channel_id: Optional[str] = Body(None, description="支付渠道 ID"),
    payment_method: str = Body("web", description="支付方式：web/app/h5"),
    subject: str = Body("AI 中台充值", description="订单标题"),
    body: str = Body("", description="订单描述"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """创建支付订单"""
    # 获取或创建账户
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        account = Account(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            balance=0,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    # 获取客户端 IP
    client_ip = request.client.host if request else None

    # 创建支付订单
    payment_manager = PaymentManager(db)
    order = payment_manager.create_payment_order(
        user_id=current_user.id,
        account_id=account.id,
        amount=amount,
        channel_id=channel_id,
        subject=subject,
        body=body,
        payment_method=payment_method,
        client_ip=client_ip,
    )

    return {
        "success": True,
        "message": "订单创建成功",
        "data": {
            "order_no": order.order_no,
            "amount": float(order.amount),
            "channel": order.channel.to_dict() if order.channel else None,
            "pay_url": order.pay_url,
            "qr_code": order.qr_code,
            "app_param": order.app_param,
            "expires_at": order.expires_at.isoformat() if order.expires_at else None,
        },
    }


@router.get("/orders", response_model=Dict[str, Any])
def list_payment_orders(
    channel_id: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取订单列表"""
    payment_manager = PaymentManager(db)
    result = payment_manager.list_orders(
        user_id=current_user.id,
        channel_id=channel_id,
        payment_status=payment_status,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "data": result,
    }


@router.get("/orders/{order_id}", response_model=Dict[str, Any])
def get_payment_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取订单详情"""
    payment_manager = PaymentManager(db)
    order = payment_manager.get_order(order_id=order_id)
    if not order:
        return {
            "success": False,
            "message": "订单不存在",
        }
    return {
        "success": True,
        "data": order.to_dict(),
    }


@router.get("/orders/query/{order_no}", response_model=Dict[str, Any])
def query_payment_order(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据订单号查询订单"""
    payment_manager = PaymentManager(db)
    order = payment_manager.get_order(order_no=order_no)
    if not order:
        return {
            "success": False,
            "message": "订单不存在",
        }
    return {
        "success": True,
        "data": order.to_dict(),
    }


# ==================== 支付回调处理 ====================

@router.post("/callback/alipay")
async def alipay_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """支付宝支付回调"""
    # 获取回调数据
    callback_data = {}
    content_type = request.headers.get("Content-Type", "")

    if "application/json" in content_type:
        callback_data = await request.json()
    else:
        form_data = await request.form()
        callback_data = dict(form_data)

    # 获取客户端 IP
    client_ip = request.client.host

    # 处理回调
    payment_manager = PaymentManager(db)
    result = payment_manager.process_callback(
        channel_name="alipay",
        callback_data=callback_data,
        client_ip=client_ip,
    )

    # 返回成功响应（支付宝要求返回 success）
    return PlainTextResponse(content="success")


@router.post("/callback/wechat")
async def wechat_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """微信支付回调"""
    callback_data = await request.json()
    client_ip = request.client.host

    payment_manager = PaymentManager(db)
    result = payment_manager.process_callback(
        channel_name="wechat",
        callback_data=callback_data,
        client_ip=client_ip,
    )

    # 返回成功响应
    return {"code": "SUCCESS", "message": "OK"}


@router.post("/callback/unionpay")
async def unionpay_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """银联支付回调"""
    callback_data = {}
    form_data = await request.form()
    callback_data = dict(form_data)
    client_ip = request.client.host

    payment_manager = PaymentManager(db)
    result = payment_manager.process_callback(
        channel_name="unionpay",
        callback_data=callback_data,
        client_ip=client_ip,
    )

    # 返回成功响应
    return PlainTextResponse(content="success")


# ==================== 退款管理 ====================

@router.post("/refund", response_model=Dict[str, Any])
def refund_payment(
    order_id: str = Body(..., description="订单 ID"),
    refund_amount: Decimal = Body(..., description="退款金额", gt=0),
    reason: str = Body(..., description="退款原因"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """申请退款"""
    payment_manager = PaymentManager(db)

    # 验证订单属于当前用户
    order = payment_manager.get_order(order_id=order_id)
    if not order:
        return {
            "success": False,
            "message": "订单不存在",
        }
    if order.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权操作该订单",
        }

    refund = payment_manager.refund_payment(
        order_id=order_id,
        refund_amount=refund_amount,
        reason=reason,
        operator_id=current_user.id,
    )

    return {
        "success": True,
        "message": "退款申请成功",
        "data": refund.to_dict(),
    }


@router.get("/refunds", response_model=Dict[str, Any])
def list_refunds(
    order_id: Optional[str] = Query(None),
    refund_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取退款记录列表"""
    query = db.query(PaymentRefund).filter(PaymentRefund.user_id == current_user.id)

    if order_id:
        query = query.filter(PaymentRefund.order_id == order_id)
    if refund_status:
        query = query.filter(PaymentRefund.refund_status == refund_status)

    total = query.count()
    refunds = query.order_by(
        PaymentRefund.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "success": True,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [refund.to_dict() for refund in refunds],
        },
    }


# ==================== 管理员接口 ====================

@router.post("/channels", response_model=Dict[str, Any])
def create_payment_channel(
    channel_name: str = Body(..., description="渠道名称：alipay/wechat/unionpay"),
    channel_type: str = Body(..., description="渠道类型"),
    display_name: str = Body("", description="显示名称"),
    app_id: str = Body("", description="应用 ID"),
    merchant_id: str = Body("", description="商户 ID"),
    api_key: str = Body("", description="API Key"),
    api_secret: str = Body("", description="API 密钥"),
    config: Dict[str, Any] = Body({}, description="额外配置"),
    is_active: bool = Body(True, description="是否启用"),
    is_default: bool = Body(False, description="是否默认渠道"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """创建支付渠道（管理员）"""
    payment_service = PaymentService(db)
    channel = payment_service.create_channel({
        "channel_name": channel_name,
        "channel_type": channel_type,
        "display_name": display_name,
        "app_id": app_id,
        "merchant_id": merchant_id,
        "api_key": api_key,
        "api_secret": api_secret,
        "config": json.dumps(config),
        "is_active": is_active,
        "is_default": is_default,
    })

    return {
        "success": True,
        "message": "支付渠道创建成功",
        "data": channel.to_dict(),
    }


@router.put("/channels/{channel_id}", response_model=Dict[str, Any])
def update_payment_channel(
    channel_id: str,
    display_name: Optional[str] = Body(None),
    app_id: Optional[str] = Body(None),
    merchant_id: Optional[str] = Body(None),
    api_key: Optional[str] = Body(None),
    api_secret: Optional[str] = Body(None),
    config: Optional[Dict[str, Any]] = Body(None),
    is_active: Optional[bool] = Body(None),
    is_default: Optional[bool] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """更新支付渠道（管理员）"""
    payment_service = PaymentService(db)

    update_data = {}
    for key, value in locals().items():
        if key not in ["channel_id", "db", "current_user"] and value is not None:
            update_data[key] = value

    if config:
        update_data["config"] = json.dumps(config)

    channel = payment_service.update_channel(channel_id, update_data)

    return {
        "success": True,
        "message": "支付渠道更新成功",
        "data": channel.to_dict(),
    }


@router.delete("/channels/{channel_id}", response_model=Dict[str, Any])
def delete_payment_channel(
    channel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """删除支付渠道（管理员）"""
    payment_service = PaymentService(db)
    payment_service.delete_channel(channel_id)

    return {
        "success": True,
        "message": "支付渠道已删除",
    }
