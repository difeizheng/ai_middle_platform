"""
邮件服务模块
提供 SMTP 邮件发送功能
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务类"""

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        use_tls: bool = True,
    ):
        """
        初始化邮件服务

        Args:
            smtp_server: SMTP 服务器地址
            smtp_port: SMTP 端口
            username: SMTP 用户名
            password: SMTP 密码
            from_email: 发件人邮箱
            from_name: 发件人名称
            use_tls: 是否使用 TLS 加密
        """
        self.smtp_server = smtp_server or settings.SMTP_SERVER
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USERNAME
        self.password = password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.SMTP_FROM_EMAIL
        self.from_name = from_name or settings.SMTP_FROM_NAME
        self.use_tls = use_tls

    def send_email(
        self,
        to: str,
        subject: str,
        content: str,
        html: bool = False,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        发送邮件

        Args:
            to: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            html: 是否为 HTML 邮件
            attachments: 附件文件路径列表
            cc: 抄送邮箱列表
            bcc: 密送邮箱列表

        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to
            msg['Subject'] = subject

            # 添加抄送
            if cc:
                msg['Cc'] = ', '.join(cc)

            # 添加邮件内容
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(content, content_type, 'utf-8'))

            # 添加附件
            if attachments:
                for file_path in attachments:
                    self._add_attachment(msg, file_path)

            # 构建收件人列表
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # 发送邮件
            self._send_message(msg, recipients)

            logger.info(f"邮件发送成功：{to}, 主题：{subject}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败：{to}, 主题：{subject}, 错误：{str(e)}")
            return False

    def _add_attachment(self, msg: MIMEMultipart, file_path: str) -> None:
        """添加附件"""
        try:
            with open(file_path, 'rb') as f:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)

                # 获取文件名
                filename = file_path.split('/')[-1].split('\\')[-1]
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(attachment)
        except Exception as e:
            logger.error(f"添加附件失败：{file_path}, 错误：{str(e)}")
            raise

    def _send_message(self, msg: MIMEMultipart, recipients: List[str]) -> None:
        """发送邮件"""
        if self.use_tls:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

        try:
            server.login(self.username, self.password)
            server.send_message(msg, self.from_email, recipients)
        finally:
            server.quit()

    def send_template_email(
        self,
        to: str,
        template: str,
        subject: str,
        context: Dict[str, Any],
        attachments: Optional[List[str]] = None,
    ) -> bool:
        """
        发送模板邮件

        Args:
            to: 收件人邮箱
            template: 邮件模板内容（包含 {key} 占位符）
            subject: 邮件主题
            context: 模板上下文数据
            attachments: 附件列表

        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 替换模板变量
            content = template
            for key, value in context.items():
                content = content.replace(f'{{{key}}}', str(value))

            return self.send_email(
                to=to,
                subject=subject,
                content=content,
                html=True,
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"发送模板邮件失败：{to}, 错误：{str(e)}")
            return False

    def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        template: str,
    ) -> Dict[str, int]:
        """
        批量发送邮件

        Args:
            recipients: 收件人列表，每项包含 {email, context}
            subject: 邮件主题
            template: 邮件模板

        Returns:
            Dict: {success: 成功数，failed: 失败数}
        """
        success = 0
        failed = 0

        for recipient in recipients:
            email = recipient.get('email')
            context = recipient.get('context', {})

            if not email:
                failed += 1
                continue

            if self.send_template_email(email, template, subject, context):
                success += 1
            else:
                failed += 1

        return {'success': success, 'failed': failed}


# 邮件模板
EMAIL_TEMPLATES = {
    'bill_notification': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1890ff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f5f5f5; }
        .bill-info { background: white; padding: 15px; margin: 10px 0; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .button { display: inline-block; padding: 10px 20px; background: #1890ff; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI 中台 - 月度账单通知</h1>
        </div>
        <div class="content">
            <p>尊敬的 {user_name}：</p>
            <p>您好！您 {billing_month} 月份的账单已生成，详情如下：</p>

            <div class="bill-info">
                <p><strong>账单月份：</strong> {billing_month}</p>
                <p><strong>账单总额：</strong> <span style="color: #f5222d; font-size: 18px;">¥{total_amount}</span></p>
                <p><strong>已支付金额：</strong> ¥{paid_amount}</p>
                <p><strong>未支付金额：</strong> ¥{unpaid_amount}</p>
                <p><strong>支付截止日：</strong> {payment_deadline}</p>
            </div>

            <p>请及时登录 AI 中台系统查看并支付账单。</p>
            <p style="text-align: center; margin: 20px 0;">
                <a href="{system_url}" class="button">查看账单</a>
            </p>

            <p>如有任何疑问，请联系客服：{support_email}</p>
        </div>
        <div class="footer">
            <p>此致 敬礼</p>
            <p>AI 中台团队</p>
            <p>{current_date}</p>
        </div>
    </div>
</body>
</html>
""",

    'invoice_notification': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #52c41a; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f5f5f5; }
        .invoice-info { background: white; padding: 15px; margin: 10px 0; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI 中台 - 发票开具通知</h1>
        </div>
        <div class="content">
            <p>尊敬的 {user_name}：</p>
            <p>您好！您申请的发票已开具完成，详情如下：</p>

            <div class="invoice-info">
                <p><strong>发票号码：</strong> {invoice_no}</p>
                <p><strong>发票代码：</strong> {invoice_code}</p>
                <p><strong>发票抬头：</strong> {invoice_title}</p>
                <p><strong>发票金额：</strong> ¥{invoice_amount}</p>
                <p><strong>发票类型：</strong> {invoice_type}</p>
            </div>

            {download_link_html}

            <p>电子发票已发送至您的邮箱：{receiver_email}</p>
            <p>如需纸质发票，我们将在 3 个工作日内寄出。</p>
        </div>
        <div class="footer">
            <p>AI 中台团队</p>
            <p>{current_date}</p>
        </div>
    </div>
</body>
</html>
""",

    'balance_warning': """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #faad14; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f5f5f5; }
        .warning-info { background: white; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #faad14; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .button { display: inline-block; padding: 10px 20px; background: #1890ff; color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ 余额预警通知</h1>
        </div>
        <div class="content">
            <p>尊敬的 {user_name}：</p>
            <p>您好！您的账户余额已低于预警阈值，请及时充值。</p>

            <div class="warning-info">
                <p><strong>当前余额：</strong> <span style="color: #f5222d; font-size: 18px;">¥{current_balance}</span></p>
                <p><strong>预警阈值：</strong> ¥{warning_threshold}</p>
                <p><strong>差额：</strong> ¥{shortage}</p>
            </div>

            <p>为避免影响您的业务使用，请尽快完成充值。</p>
            <p style="text-align: center; margin: 20px 0;">
                <a href="{system_url}/billing" class="button">立即充值</a>
            </p>
        </div>
        <div class="footer">
            <p>AI 中台团队</p>
            <p>{current_date}</p>
        </div>
    </div>
</body>
</html>
""",
}


# 全局邮件服务实例
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """获取邮件服务实例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def send_bill_email(
    to: str,
    user_name: str,
    billing_month: str,
    total_amount: float,
    paid_amount: float,
    unpaid_amount: float,
    payment_deadline: str,
    system_url: str = "http://localhost:3000",
    support_email: str = "support@ai-middle-platform.com",
) -> bool:
    """
    发送账单通知邮件

    Args:
        to: 收件人邮箱
        user_name: 用户名称
        billing_month: 账单月份
        total_amount: 账单总额
        paid_amount: 已支付金额
        unpaid_amount: 未支付金额
        payment_deadline: 支付截止日
        system_url: 系统 URL
        support_email: 客服邮箱

    Returns:
        bool: 发送结果
    """
    email_service = get_email_service()

    context = {
        'user_name': user_name,
        'billing_month': billing_month,
        'total_amount': f'{total_amount:.2f}',
        'paid_amount': f'{paid_amount:.2f}',
        'unpaid_amount': f'{unpaid_amount:.2f}',
        'payment_deadline': payment_deadline,
        'system_url': system_url,
        'support_email': support_email,
        'current_date': datetime.now().strftime('%Y-%m-%d'),
    }

    return email_service.send_template_email(
        to=to,
        template=EMAIL_TEMPLATES['bill_notification'],
        subject=f"AI 中台 {billing_month} 月份账单通知",
        context=context,
    )


def send_invoice_email(
    to: str,
    user_name: str,
    invoice_no: str,
    invoice_code: str,
    invoice_title: str,
    invoice_amount: float,
    invoice_type: str,
    receiver_email: str,
    download_url: Optional[str] = None,
) -> bool:
    """
    发送发票通知邮件

    Args:
        to: 收件人邮箱
        user_name: 用户名称
        invoice_no: 发票号码
        invoice_code: 发票代码
        invoice_title: 发票抬头
        invoice_amount: 发票金额
        invoice_type: 发票类型
        receiver_email: 收票邮箱
        download_url: 下载链接

    Returns:
        bool: 发送结果
    """
    email_service = get_email_service()

    download_link_html = ''
    if download_url:
        download_link_html = f'''
        <p style="text-align: center; margin: 20px 0;">
            <a href="{download_url}" class="button">下载发票</a>
        </p>
        '''

    context = {
        'user_name': user_name,
        'invoice_no': invoice_no,
        'invoice_code': invoice_code,
        'invoice_title': invoice_title,
        'invoice_amount': f'{invoice_amount:.2f}',
        'invoice_type': '电子发票' if invoice_type == 'electronic' else '纸质发票',
        'receiver_email': receiver_email,
        'download_link_html': download_link_html,
        'current_date': datetime.now().strftime('%Y-%m-%d'),
    }

    return email_service.send_template_email(
        to=to,
        template=EMAIL_TEMPLATES['invoice_notification'],
        subject=f"AI 中台 - 发票开具通知 ({invoice_no})",
        context=context,
    )


def send_balance_warning_email(
    to: str,
    user_name: str,
    current_balance: float,
    warning_threshold: float,
    system_url: str = "http://localhost:3000/billing",
) -> bool:
    """
    发送余额预警邮件

    Args:
        to: 收件人邮箱
        user_name: 用户名称
        current_balance: 当前余额
        warning_threshold: 预警阈值
        system_url: 系统 URL

    Returns:
        bool: 发送结果
    """
    email_service = get_email_service()
    shortage = warning_threshold - current_balance

    context = {
        'user_name': user_name,
        'current_balance': f'{current_balance:.2f}',
        'warning_threshold': f'{warning_threshold:.2f}',
        'shortage': f'{shortage:.2f}',
        'system_url': system_url,
        'current_date': datetime.now().strftime('%Y-%m-%d'),
    }

    return email_service.send_template_email(
        to=to,
        template=EMAIL_TEMPLATES['balance_warning'],
        subject="⚠️ AI 中台 - 余额预警通知",
        context=context,
    )
