"""
账单和发票 API 路由
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional, Dict, Any, List

from ..core.database import get_db
from ..services.billing_invoice import MonthlyBillService, InvoiceService, BillEmailService, BillingInvoiceManager
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..models.billing import Account
from ..models.billing_invoice import MonthlyBill, Invoice, InvoiceApplication
from ..utils.permissions import verify_admin_user  # 权限检查

router = APIRouter(prefix="/api/v1/bills", tags=["账单管理"])


# ==================== 月度账单管理 ====================

@router.get("/monthly", response_model=Dict[str, Any])
def list_monthly_bills(
    billing_month: Optional[str] = Query(None, description="账单月份：YYYY-MM"),
    status: Optional[str] = Query(None, description="账单状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取月度账单列表"""
    # 获取用户账户
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        return {
            "success": False,
            "message": "请先创建账户",
        }

    bill_service = MonthlyBillService(db)
    result = bill_service.list_bills(
        user_id=current_user.id,
        account_id=account.id,
        billing_month=billing_month,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "success": True,
        "data": result,
    }


@router.get("/monthly/{bill_id}", response_model=Dict[str, Any])
def get_monthly_bill(
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取账单详情"""
    bill_service = MonthlyBillService(db)
    bill = bill_service.get_bill(bill_id)

    if not bill:
        return {
            "success": False,
            "message": "账单不存在",
        }

    if bill.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权查看该账单",
        }

    return {
        "success": True,
        "data": bill.to_dict(),
    }


@router.get("/monthly/query/{bill_no}", response_model=Dict[str, Any])
def query_monthly_bill(
    bill_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据账单号查询账单"""
    bill_service = MonthlyBillService(db)
    bill = bill_service.get_bill_by_no(bill_no)

    if not bill:
        return {
            "success": False,
            "message": "账单不存在",
        }

    if bill.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权查看该账单",
        }

    return {
        "success": True,
        "data": bill.to_dict(),
    }


@router.post("/monthly/{bill_id}/pay", response_model=Dict[str, Any])
def pay_bill(
    bill_id: str,
    payment_method: str = Body(..., description="支付方式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """支付账单"""
    bill_service = MonthlyBillService(db)
    bill = bill_service.get_bill(bill_id)

    if not bill:
        return {
            "success": False,
            "message": "账单不存在",
        }

    if bill.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权操作该账单",
        }

    if bill.status != "unpaid":
        return {
            "success": False,
            "message": "账单状态不允许支付",
        }

    bill = bill_service.mark_as_paid(bill_id, payment_method)

    return {
        "success": True,
        "message": "账单支付成功",
        "data": bill.to_dict(),
    }


@router.post("/monthly/generate", response_model=Dict[str, Any])
def generate_monthly_bill(
    year: int = Body(..., ge=2020, le=2100),
    month: int = Body(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """生成月度账单（管理员）"""
    # 获取用户账户
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        return {
            "success": False,
            "message": "请先创建账户",
        }

    bill_service = MonthlyBillService(db)

    try:
        bill = bill_service.generate_monthly_bill(
            user_id=current_user.id,
            account_id=account.id,
            year=year,
            month=month,
        )
        return {
            "success": True,
            "message": "账单生成成功",
            "data": bill.to_dict(),
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/monthly/update-overdue", response_model=Dict[str, Any])
def update_overdue_bills(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """更新逾期账单（管理员）"""
    bill_service = MonthlyBillService(db)
    count = bill_service.update_overdue_bills()

    return {
        "success": True,
        "message": f"已更新 {count} 个逾期账单",
    }


@router.post("/monthly/send-email", response_model=Dict[str, Any])
def send_bill_email(
    bill_id: str = Body(..., description="账单 ID"),
    recipient_email: Optional[str] = Body(None, description="收件人邮箱"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送账单邮件"""
    bill_service = MonthlyBillService(db)
    bill = bill_service.get_bill(bill_id)

    if not bill:
        return {
            "success": False,
            "message": "账单不存在",
        }

    if bill.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权操作该账单",
        }

    # 使用用户邮箱或指定邮箱
    if not recipient_email:
        recipient_email = current_user.email

    if not recipient_email:
        return {
            "success": False,
            "message": "请先设置邮箱地址",
        }

    email_service = BillEmailService(db)
    email_log = email_service.send_bill_email(bill, recipient_email)

    return {
        "success": True,
        "message": "账单邮件已发送",
        "data": email_log.to_dict(),
    }


# ==================== 发票管理 ====================

@router.get("/invoices", response_model=Dict[str, Any])
def list_invoices(
    invoice_type: Optional[str] = Query(None, description="发票类型：electronic/paper"),
    status: Optional[str] = Query(None, description="发票状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取发票列表"""
    invoice_service = InvoiceService(db)
    result = invoice_service.list_invoices(
        user_id=current_user.id,
        invoice_type=invoice_type,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "success": True,
        "data": result,
    }


@router.get("/invoices/{invoice_id}", response_model=Dict[str, Any])
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取发票详情"""
    invoice_service = InvoiceService(db)
    invoice = invoice_service.get_invoice(invoice_id)

    if not invoice:
        return {
            "success": False,
            "message": "发票不存在",
        }

    if invoice.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权查看该发票",
        }

    return {
        "success": True,
        "data": invoice.to_dict(),
    }


@router.post("/invoices/request", response_model=Dict[str, Any])
def request_invoice(
    invoice_type: str = Body(..., description="发票类型：electronic/paper"),
    amount: Decimal = Body(..., description="开票金额", gt=0),
    title: str = Body(..., description="发票抬头"),
    tax_id: str = Body(..., description="纳税人识别号"),
    bill_ids: List[str] = Body([], description="关联账单 ID 列表"),
    receiver_name: str = Body(..., description="收票人姓名"),
    receiver_email: str = Body(..., description="收票邮箱"),
    receiver_phone: str = Body("", description="收票电话"),
    receiver_address: Optional[str] = Body(None, description="收票地址"),
    company_address: Optional[str] = Body(None, description="公司地址"),
    company_phone: Optional[str] = Body(None, description="公司电话"),
    bank_name: Optional[str] = Body(None, description="开户行"),
    bank_account: Optional[str] = Body(None, description="银行账号"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """申请开票"""
    # 获取用户账户
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        return {
            "success": False,
            "message": "请先创建账户",
        }

    invoice_service = InvoiceService(db)

    application = invoice_service.create_invoice_application(
        user_id=current_user.id,
        account_id=account.id,
        invoice_type=invoice_type,
        amount=amount,
        title=title,
        tax_id=tax_id,
        bill_ids=bill_ids,
        receiver_name=receiver_name,
        receiver_email=receiver_email,
        receiver_phone=receiver_phone,
        receiver_address=receiver_address,
    )

    return {
        "success": True,
        "message": "发票申请已提交",
        "data": application.to_dict(),
    }


@router.get("/invoices/applications", response_model=Dict[str, Any])
def list_invoice_applications(
    audit_status: Optional[str] = Query(None, description="审核状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取发票申请列表"""
    invoice_service = InvoiceService(db)
    result = invoice_service.list_applications(
        user_id=current_user.id,
        audit_status=audit_status,
        page=page,
        page_size=page_size,
    )

    return {
        "success": True,
        "data": result,
    }


@router.get("/invoices/applications/{application_id}", response_model=Dict[str, Any])
def get_invoice_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取发票申请详情"""
    invoice_service = InvoiceService(db)
    application = invoice_service.get_application(application_id)

    if not application:
        return {
            "success": False,
            "message": "发票申请不存在",
        }

    if application.user_id != current_user.id:
        return {
            "success": False,
            "message": "无权查看该申请",
        }

    return {
        "success": True,
        "data": application.to_dict(),
    }


# ==================== 管理员接口 ====================

@router.post("/invoices/applications/{application_id}/audit", response_model=Dict[str, Any])
def audit_invoice_application(
    application_id: str,
    approved: bool = Body(..., description="是否批准"),
    remark: str = Body("", description="审核备注"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """审核发票申请（管理员）"""
    invoice_service = InvoiceService(db)

    try:
        application = invoice_service.audit_application(
            application_id=application_id,
            auditor_id=current_user.id,
            approved=approved,
            remark=remark,
        )
        return {
            "success": True,
            "message": "审核成功",
            "data": application.to_dict(),
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/invoices/{invoice_id}/issue", response_model=Dict[str, Any])
def issue_invoice(
    invoice_id: str,
    file_url: str = Body(..., description="发票文件 URL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """开具发票（管理员）"""
    invoice_service = InvoiceService(db)

    try:
        invoice = invoice_service.mark_invoice_issued(invoice_id, file_url)
        return {
            "success": True,
            "message": "发票已开具",
            "data": invoice.to_dict(),
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/invoices/{invoice_id}/deliver", response_model=Dict[str, Any])
def deliver_invoice(
    invoice_id: str,
    express_company: Optional[str] = Body(None, description="快递公司"),
    express_number: Optional[str] = Body(None, description="快递单号"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """交付发票（管理员）"""
    invoice_service = InvoiceService(db)

    try:
        invoice = invoice_service.mark_invoice_delivered(
            invoice_id,
            express_company=express_company,
            express_number=express_number,
        )
        return {
            "success": True,
            "message": "发票已交付",
            "data": invoice.to_dict(),
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/monthly/generate-all", response_model=Dict[str, Any])
def generate_all_monthly_bills(
    year: int = Body(..., ge=2020, le=2100),
    month: int = Body(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """批量生成所有用户的月度账单（管理员）"""
    manager = BillingInvoiceManager(db)
    result = manager.generate_all_monthly_bills(year, month)

    return {
        "success": True,
        "message": f"生成成功：{result['success_count']} 个，失败：{result['error_count']} 个",
        "data": result,
    }


@router.post("/monthly/send-emails", response_model=Dict[str, Any])
def send_monthly_bill_emails(
    billing_month: str = Body(..., description="账单月份：YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin_user),  # 管理员权限检查
):
    """批量发送账单邮件（管理员）"""
    manager = BillingInvoiceManager(db)
    result = manager.send_bill_emails(billing_month)

    return {
        "success": True,
        "message": f"发送成功：{result['success_count']} 个，失败：{result['error_count']} 个",
        "data": result,
    }
