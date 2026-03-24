"""
账单和发票服务层
"""
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract

from ..models.billing_invoice import MonthlyBill, BillStatus, Invoice, InvoiceType, InvoiceStatus, InvoiceApplication, BillEmailLog
from ..models.billing import Account, BillingRecord, BillingStats
from ..models.user import User
from ..core.exceptions import BusinessException, NotFoundError


class MonthlyBillService:
    """月度账单服务类"""

    def __init__(self, db: Session):
        self.db = db

    def generate_monthly_bill(
        self,
        user_id: str,
        account_id: str,
        year: int,
        month: int,
    ) -> MonthlyBill:
        """生成月度账单"""
        # 检查是否已存在账单
        billing_month = f"{year}-{month:02d}"
        existing = self.db.query(MonthlyBill).filter(
            MonthlyBill.user_id == user_id,
            MonthlyBill.billing_month == billing_month
        ).first()

        if existing:
            raise BusinessException(f"{billing_month} 月份账单已存在")

        # 计算账单周期
        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            period_end = datetime(year, month + 1, 1) - timedelta(seconds=1)

        # 统计消费记录
        stats = self._calculate_consumption_stats(account_id, period_start, period_end)

        # 创建账单
        bill = MonthlyBill(
            id=str(uuid.uuid4()),
            bill_no=self._generate_bill_no(billing_month, user_id),
            account_id=account_id,
            user_id=user_id,
            billing_month=billing_month,
            period_start=period_start,
            period_end=period_end,
            total_amount=stats["total_amount"],
            model_call_amount=stats["model_call_amount"],
            knowledge_base_amount=stats["knowledge_base_amount"],
            agent_amount=stats["agent_amount"],
            skill_amount=stats["skill_amount"],
            total_tokens=stats["total_tokens"],
            total_calls=stats["total_calls"],
            status=BillStatus.UNPAID.value,
            payment_deadline=datetime(year, month, 25),  # 次月 25 日为支付截止日
            bill_data=json.dumps(stats["details"]),
        )

        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)

        return bill

    def _calculate_consumption_stats(
        self,
        account_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Any]:
        """计算消费统计"""
        # 查询计费记录
        records = self.db.query(BillingRecord).filter(
            BillingRecord.account_id == account_id,
            BillingRecord.record_type == "consume",
            BillingRecord.created_at >= period_start,
            BillingRecord.created_at <= period_end,
        ).all()

        total_amount = Decimal(0)
        model_call_amount = Decimal(0)
        knowledge_base_amount = Decimal(0)
        agent_amount = Decimal(0)
        skill_amount = Decimal(0)
        total_tokens = 0
        total_calls = 0
        details = []

        for record in records:
            amount = Decimal(str(record.amount)) if record.amount else Decimal(0)
            total_amount += amount

            # 按资源类型分类
            if record.resource_type == "model_call":
                model_call_amount += amount
            elif record.resource_type == "knowledge_base":
                knowledge_base_amount += amount
            elif record.resource_type == "agent":
                agent_amount += amount
            elif record.resource_type == "skill":
                skill_amount += amount

            # 统计使用量
            total_tokens += record.tokens_used if record.tokens_used else 0
            total_calls += record.call_count if record.call_count else 0

            # 记录详情
            details.append({
                "id": record.id,
                "type": record.resource_type,
                "amount": float(amount),
                "tokens": record.tokens_used,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            })

        return {
            "total_amount": float(total_amount),
            "model_call_amount": float(model_call_amount),
            "knowledge_base_amount": float(knowledge_base_amount),
            "agent_amount": float(agent_amount),
            "skill_amount": float(skill_amount),
            "total_tokens": total_tokens,
            "total_calls": total_calls,
            "details": details,
        }

    def get_bill(self, bill_id: str) -> Optional[MonthlyBill]:
        """获取账单"""
        return self.db.query(MonthlyBill).filter(MonthlyBill.id == bill_id).first()

    def get_bill_by_no(self, bill_no: str) -> Optional[MonthlyBill]:
        """根据账单号获取账单"""
        return self.db.query(MonthlyBill).filter(MonthlyBill.bill_no == bill_no).first()

    def list_bills(
        self,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        billing_month: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取账单列表"""
        query = self.db.query(MonthlyBill)

        if user_id:
            query = query.filter(MonthlyBill.user_id == user_id)
        if account_id:
            query = query.filter(MonthlyBill.account_id == account_id)
        if billing_month:
            query = query.filter(MonthlyBill.billing_month == billing_month)
        if status:
            query = query.filter(MonthlyBill.status == status)

        total = query.count()
        bills = query.order_by(
            MonthlyBill.billing_month.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [bill.to_dict() for bill in bills],
        }

    def mark_as_paid(self, bill_id: str, payment_method: str) -> MonthlyBill:
        """标记账单为已支付"""
        bill = self.get_bill(bill_id)
        if not bill:
            raise NotFoundError("账单不存在")

        bill.status = BillStatus.PAID.value
        bill.paid_amount = bill.unpaid_amount
        bill.unpaid_amount = Decimal(0)
        bill.paid_at = datetime.utcnow()
        bill.payment_method = payment_method

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def update_overdue_bills(self) -> int:
        """更新逾期账单"""
        now = datetime.utcnow()
        updated = self.db.query(MonthlyBill).filter(
            MonthlyBill.status == BillStatus.UNPAID.value,
            MonthlyBill.payment_deadline < now
        ).update({
            "status": BillStatus.OVERDUE.value,
            "updated_at": now
        })
        self.db.commit()
        return updated

    def _generate_bill_no(self, billing_month: str, user_id: str) -> str:
        """生成账单号"""
        date_str = billing_month.replace("-", "")
        random_str = uuid.uuid4().hex[:8].upper()
        return f"BILL{date_str}{random_str}"


class InvoiceService:
    """发票服务类"""

    def __init__(self, db: Session):
        self.db = db

    def create_invoice_application(
        self,
        user_id: str,
        account_id: str,
        invoice_type: str,
        amount: Decimal,
        title: str,
        tax_id: str,
        bill_ids: List[str],
        receiver_name: str,
        receiver_email: str,
        receiver_phone: str,
        receiver_address: Optional[str] = None,
    ) -> InvoiceApplication:
        """创建发票申请"""
        application = InvoiceApplication(
            id=str(uuid.uuid4()),
            application_no=self._generate_application_no(),
            account_id=account_id,
            user_id=user_id,
            invoice_type=invoice_type,
            amount=amount,
            title=title,
            tax_id=tax_id,
            receiver_name=receiver_name,
            receiver_email=receiver_email,
            receiver_phone=receiver_phone,
            receiver_address=receiver_address,
            bill_ids=json.dumps(bill_ids),
        )

        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def get_application(self, application_id: str) -> Optional[InvoiceApplication]:
        """获取发票申请"""
        return self.db.query(InvoiceApplication).filter(
            InvoiceApplication.id == application_id
        ).first()

    def list_applications(
        self,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        audit_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取发票申请列表"""
        query = self.db.query(InvoiceApplication)

        if user_id:
            query = query.filter(InvoiceApplication.user_id == user_id)
        if account_id:
            query = query.filter(InvoiceApplication.account_id == account_id)
        if audit_status:
            query = query.filter(InvoiceApplication.audit_status == audit_status)

        total = query.count()
        applications = query.order_by(
            InvoiceApplication.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [app.to_dict() for app in applications],
        }

    def audit_application(
        self,
        application_id: str,
        auditor_id: str,
        approved: bool,
        remark: str = "",
    ) -> InvoiceApplication:
        """审核发票申请"""
        application = self.get_application(application_id)
        if not application:
            raise NotFoundError("发票申请不存在")

        application.audit_status = "approved" if approved else "rejected"
        application.auditor_id = auditor_id
        application.audit_time = datetime.utcnow()
        application.audit_remark = remark

        if approved:
            application.status = "processing"
            # 创建发票记录
            self._create_invoice(application)
        else:
            application.status = "cancelled"

        self.db.commit()
        self.db.refresh(application)
        return application

    def _create_invoice(self, application: InvoiceApplication) -> Invoice:
        """创建发票"""
        invoice = Invoice(
            id=str(uuid.uuid4()),
            invoice_no=self._generate_invoice_no(),
            invoice_code=self._generate_invoice_code(),
            account_id=application.account_id,
            user_id=application.user_id,
            invoice_type=application.invoice_type,
            status=InvoiceStatus.PROCESSING.value,
            title=application.title,
            tax_id=application.tax_id,
            amount=application.amount,
            tax_amount=application.amount * Decimal(str(application.tax_rate)),
            receiver_name=application.receiver_name,
            receiver_email=application.receiver_email,
            receiver_phone=application.receiver_phone,
            receiver_address=application.receiver_address,
            application_time=application.created_at,
        )

        self.db.add(invoice)
        self.db.commit()
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """获取发票"""
        return self.db.query(Invoice).filter(Invoice.id == invoice_id).first()

    def list_invoices(
        self,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
        invoice_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """获取发票列表"""
        query = self.db.query(Invoice)

        if user_id:
            query = query.filter(Invoice.user_id == user_id)
        if account_id:
            query = query.filter(Invoice.account_id == account_id)
        if invoice_type:
            query = query.filter(Invoice.invoice_type == invoice_type)
        if status:
            query = query.filter(Invoice.status == status)

        total = query.count()
        invoices = query.order_by(
            Invoice.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [invoice.to_dict() for invoice in invoices],
        }

    def mark_invoice_issued(self, invoice_id: str, file_url: str) -> Invoice:
        """标记发票已开具"""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise NotFoundError("发票不存在")

        invoice.status = InvoiceStatus.ISSUED.value
        invoice.invoice_file_url = file_url
        invoice.issued_time = datetime.utcnow()

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def mark_invoice_delivered(
        self,
        invoice_id: str,
        express_company: Optional[str] = None,
        express_number: Optional[str] = None,
    ) -> Invoice:
        """标记发票已交付"""
        invoice = self.get_invoice(invoice_id)
        if not invoice:
            raise NotFoundError("发票不存在")

        invoice.status = InvoiceStatus.DELIVERED.value
        invoice.delivered_time = datetime.utcnow()

        if express_company:
            invoice.express_company = express_company
        if express_number:
            invoice.express_number = express_number

        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def _generate_application_no(self) -> str:
        """生成申请单号"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return f"INV{date_str}{uuid.uuid4().hex[:10].upper()}"

    def _generate_invoice_no(self) -> str:
        """生成发票号码"""
        return f"F{uuid.uuid4().hex[:12].upper()}"

    def _generate_invoice_code(self) -> str:
        """生成发票代码"""
        return f"FC{uuid.uuid4().hex[:10].upper()}"


class BillEmailService:
    """账单邮件服务类"""

    def __init__(self, db: Session):
        self.db = db

    def send_bill_email(
        self,
        bill: MonthlyBill,
        recipient_email: str,
    ) -> BillEmailLog:
        """发送账单邮件"""
        # 创建邮件日志
        email_log = BillEmailLog(
            id=str(uuid.uuid4()),
            bill_id=bill.id,
            user_id=bill.user_id,
            recipient_email=recipient_email,
            email_subject=f"AI 中台 {bill.billing_month} 月份账单",
            email_content=self._generate_email_content(bill),
            send_status="pending",
        )

        self.db.add(email_log)

        # 调用邮件发送服务
        from .email import send_bill_email as send_bill_email_service

        # 获取用户信息
        from ..models.user import User
        user = self.db.query(User).filter(User.id == bill.user_id).first()
        user_name = user.full_name or user.username if user else "用户"

        try:
            # 使用 HTML 模板发送邮件
            success = send_bill_email_service(
                to=recipient_email,
                user_name=user_name,
                billing_month=bill.billing_month,
                total_amount=float(bill.total_amount),
                paid_amount=float(bill.paid_amount),
                unpaid_amount=float(bill.unpaid_amount),
                payment_deadline=bill.payment_deadline.strftime('%Y-%m-%d') if bill.payment_deadline else "",
            )

            if success:
                email_log.send_status = "success"
                email_log.send_time = datetime.utcnow()
            else:
                email_log.send_status = "failed"
                email_log.error_message = "邮件发送失败"
        except Exception as e:
            email_log.send_status = "failed"
            email_log.error_message = str(e)

        self.db.commit()
        self.db.refresh(email_log)

        # 更新账单的邮件发送状态
        bill.email_sent = True
        bill.email_sent_at = datetime.utcnow()
        self.db.commit()

        return email_log

    def _generate_email_content(self, bill: MonthlyBill) -> str:
        """生成邮件内容"""
        import json
        bill_data = json.loads(bill.bill_data) if bill.bill_data else {}

        content = f"""
尊敬的 AI 中台用户：

您好！您 {bill.billing_month} 月份的账单已生成，详情如下：

【账单概要】
- 账单月份：{bill.billing_month}
- 账单总额：¥{float(bill.total_amount):.2f}
- 已支付金额：¥{float(bill.paid_amount):.2f}
- 未支付金额：¥{float(bill.unpaid_amount):.2f}
- 支付截止日：{bill.payment_deadline.strftime('%Y-%m-%d') if bill.payment_deadline else 'N/A'}

【消费明细】
- 模型调用：¥{float(bill.model_call_amount):.2f}
- 知识库：¥{float(bill.knowledge_base_amount):.2f}
- 智能体：¥{float(bill.agent_amount):.2f}
- Skill：¥{float(bill.skill_amount):.2f}

【使用量统计】
- 总 Token 使用量：{bill.total_tokens:,}
- 总调用次数：{bill.total_calls:,}

详细账单请查看附件或登录 AI 中台系统查看。

如有任何疑问，请联系客服：support@ai-middle-platform.com

此致
敬礼

AI 中台团队
"""
        return content

    def _send_email(self, to: str, subject: str, content: str) -> bool:
        """发送邮件（占位实现）"""
        # 实际实现需要使用 SMTP 或第三方邮件服务
        # import smtplib
        # from email.mime.text import MIMEText
        # ...
        return True


class BillingInvoiceManager:
    """账单和发票管理器"""

    def __init__(self, db: Session):
        self.db = db
        self.bill_service = MonthlyBillService(db)
        self.invoice_service = InvoiceService(db)
        self.email_service = BillEmailService(db)

    def generate_all_monthly_bills(self, year: int, month: int) -> Dict[str, Any]:
        """生成所有用户的月度账单"""
        # 获取所有账户
        accounts = self.db.query(Account).all()

        success_count = 0
        error_count = 0
        errors = []

        for account in accounts:
            try:
                self.bill_service.generate_monthly_bill(
                    user_id=account.user_id,
                    account_id=account.id,
                    year=year,
                    month=month,
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    "user_id": account.user_id,
                    "error": str(e),
                })

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
        }

    def send_bill_emails(self, billing_month: str) -> Dict[str, Any]:
        """批量发送账单邮件"""
        # 获取指定月份的所有账单
        bills = self.db.query(MonthlyBill).filter(
            MonthlyBill.billing_month == billing_month,
            MonthlyBill.email_sent == False,
        ).all()

        success_count = 0
        error_count = 0

        for bill in bills:
            # 获取用户邮箱
            user = self.db.query(User).filter(User.id == bill.user_id).first()
            if user and user.email:
                try:
                    self.email_service.send_bill_email(bill, user.email)
                    success_count += 1
                except Exception:
                    error_count += 1

        return {
            "success_count": success_count,
            "error_count": error_count,
        }
