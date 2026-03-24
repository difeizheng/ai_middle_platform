# Phase 5.5 账单和发票系统实现文档

**版本：** v0.9.0
**日期：** 2026 年 3 月 24 日
**状态：** ✅ 已完成

---

## 概述

Phase 5.5 账单和发票系统已成功实现，为 AI 中台提供完整的账单管理和发票处理能力，包括月度账单生成、发票申请、发票开具和邮件推送等功能。

---

## 实现内容

### 1. 数据模型

文件位置：`backend/app/models/billing_invoice.py`

#### MonthlyBill（月度账单）
```python
class MonthlyBill(Base):
    """月度账单表"""
    __tablename__ = "monthly_bills"

    # 账单号
    id, bill_no

    # 关联信息
    account_id, user_id

    # 账单周期
    billing_month  # YYYY-MM
    period_start, period_end

    # 金额信息
    total_amount, paid_amount, unpaid_amount
    discount_amount, refund_amount

    # 消费明细汇总
    model_call_amount, knowledge_base_amount
    agent_amount, skill_amount

    # 使用量统计
    total_tokens, total_calls, total_storage_gb

    # 账单状态
    status  # unpaid/paid/overdue/cancelled

    # 支付信息
    payment_deadline, paid_at, payment_method

    # 账单文件
    bill_file_url, bill_data (JSON)

    # 通知信息
    email_sent, email_sent_at
```

#### Invoice（发票）
```python
class Invoice(Base):
    """发票表"""
    __tablename__ = "invoices"

    # 发票号码
    id, invoice_no, invoice_code

    # 关联信息
    account_id, user_id, bill_id

    # 发票类型
    invoice_type  # electronic/paper
    status  # pending/processing/issued/delivered/rejected

    # 发票抬头信息
    title, tax_id, company_address, company_phone
    bank_name, bank_account

    # 发票金额
    amount, tax_rate, tax_amount

    # 收票信息
    receiver_name, receiver_email, receiver_phone
    receiver_address, receiver_zip

    # 发票文件
    invoice_file_url, invoice_download_code

    # 物流信息（纸质发票）
    express_company, express_number, express_status

    # 时间信息
    application_time, issued_time, delivered_time
```

#### InvoiceApplication（发票申请）
```python
class InvoiceApplication(Base):
    """发票申请表"""
    __tablename__ = "invoice_applications"

    # 申请单号
    id, application_no

    # 关联信息
    account_id, user_id

    # 申请信息
    invoice_type, amount

    # 抬头信息
    title, tax_id, company_address, company_phone
    bank_name, bank_account

    # 收票信息
    receiver_name, receiver_email, receiver_phone
    receiver_address, receiver_zip

    # 关联账单（可多张）
    bill_ids  # JSON 数组

    # 审核状态
    audit_status, auditor_id, audit_time, audit_remark
    status
```

#### BillEmailLog（账单邮件日志）
```python
class BillEmailLog(Base):
    """账单邮件日志表"""
    __tablename__ = "bill_email_logs"

    id, bill_id, user_id
    recipient_email, email_subject, email_content
    send_status, send_time, error_message
    is_opened, opened_at
```

---

### 2. 服务层

文件位置：`backend/app/services/billing_invoice.py`

#### MonthlyBillService（月度账单服务）
| 方法 | 描述 |
|------|------|
| `generate_monthly_bill(user_id, account_id, year, month)` | 生成月度账单 |
| `get_bill(bill_id)` | 获取账单 |
| `get_bill_by_no(bill_no)` | 根据账单号获取 |
| `list_bills(...)` | 获取账单列表 |
| `mark_as_paid(bill_id, payment_method)` | 标记为已支付 |
| `update_overdue_bills()` | 更新逾期账单 |
| `_calculate_consumption_stats(...)` | 计算消费统计 |

#### InvoiceService（发票服务）
| 方法 | 描述 |
|------|------|
| `create_invoice_application(...)` | 创建发票申请 |
| `get_application(application_id)` | 获取发票申请 |
| `list_applications(...)` | 获取申请列表 |
| `audit_application(application_id, auditor_id, approved, remark)` | 审核发票申请 |
| `_create_invoice(application)` | 创建发票记录 |
| `get_invoice(invoice_id)` | 获取发票 |
| `list_invoices(...)` | 获取发票列表 |
| `mark_invoice_issued(invoice_id, file_url)` | 标记发票已开具 |
| `mark_invoice_delivered(invoice_id, ...)` | 标记发票已交付 |

#### BillEmailService（账单邮件服务）
| 方法 | 描述 |
|------|------|
| `send_bill_email(bill, recipient_email)` | 发送账单邮件 |
| `_generate_email_content(bill)` | 生成邮件内容 |
| `_send_email(to, subject, content)` | 发送邮件（需集成 SMTP） |

#### BillingInvoiceManager（账单和发票管理器）
| 方法 | 描述 |
|------|------|
| `generate_all_monthly_bills(year, month)` | 批量生成所有用户账单 |
| `send_bill_emails(billing_month)` | 批量发送账单邮件 |

---

### 3. API 路由

文件位置：`backend/app/api/billing_invoice.py`

#### 月度账单管理
```
GET    /api/v1/bills/monthly                 # 获取月度账单列表
GET    /api/v1/bills/monthly/{bill_id}       # 获取账单详情
GET    /api/v1/bills/monthly/query/{bill_no} # 根据账单号查询
POST   /api/v1/bills/monthly/{bill_id}/pay   # 支付账单
POST   /api/v1/bills/monthly/generate        # 生成月度账单
POST   /api/v1/bills/monthly/update-overdue  # 更新逾期账单
POST   /api/v1/bills/monthly/send-email      # 发送账单邮件
POST   /api/v1/bills/monthly/generate-all    # 批量生成账单（管理员）
POST   /api/v1/bills/monthly/send-emails     # 批量发送邮件（管理员）
```

#### 发票管理
```
GET    /api/v1/bills/invoices                # 获取发票列表
GET    /api/v1/bills/invoices/{invoice_id}   # 获取发票详情
POST   /api/v1/bills/invoices/request        # 申请开票
GET    /api/v1/bills/invoices/applications   # 获取发票申请列表
GET    /api/v1/bills/invoices/applications/{id}  # 获取申请详情
POST   /api/v1/bills/invoices/applications/{id}/audit  # 审核申请（管理员）
POST   /api/v1/bills/invoices/{invoice_id}/issue     # 开具发票（管理员）
POST   /api/v1/bills/invoices/{invoice_id}/deliver   # 交付发票（管理员）
```

---

### 4. 数据库迁移

文件位置：`deploy/init.sql`

新增 4 个表：
- `monthly_bills` - 月度账单表
- `invoices` - 发票表
- `invoice_applications` - 发票申请表
- `bill_email_logs` - 账单邮件日志表

索引：
- `idx_monthly_bills_bill_no` - 按账单号查询
- `idx_monthly_bills_account` - 按账户查询
- `idx_monthly_bills_user` - 按用户查询
- `idx_monthly_bills_month` - 按月份查询
- `idx_monthly_bills_status` - 按状态查询
- `idx_invoices_invoice_no` - 按发票号码查询
- `idx_invoices_account` - 按账户查询
- `idx_invoices_status` - 按状态查询
- `idx_invoice_applications_app_no` - 按申请单号查询
- `idx_invoice_applications_audit` - 按审核状态查询
- `idx_bill_email_logs_bill` - 按账单 ID 查询
- `idx_bill_email_logs_status` - 按发送状态查询

---

## API 调用示例

### 获取月度账单列表
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/bills/monthly?billing_month=2026-03&page=1&page_size=20"
```

响应：
```json
{
  "success": true,
  "data": {
    "total": 3,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "bill_no": "BILL202603A1B2C3D4",
        "billing_month": "2026-03",
        "total_amount": 520.00,
        "paid_amount": 0,
        "unpaid_amount": 520.00,
        "status": "unpaid",
        "payment_deadline": "2026-03-25T00:00:00",
        "model_call_amount": 500.00,
        "knowledge_base_amount": 20.00,
        "total_tokens": 125000,
        "total_calls": 1500
      }
    ]
  }
}
```

### 支付账单
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_method": "alipay"}' \
  http://localhost:8000/api/v1/bills/monthly/BILL202603A1B2C3D4/pay
```

### 申请开票
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_type": "electronic",
    "amount": 520.00,
    "title": "XX 科技有限公司",
    "tax_id": "91110108MA00000000",
    "bill_ids": ["BILL202603A1B2C3D4"],
    "receiver_name": "张三",
    "receiver_email": "zhangsan@example.com",
    "receiver_phone": "13800138000"
  }' \
  http://localhost:8000/api/v1/bills/invoices/request
```

### 审核发票申请（管理员）
```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "remark": "审核通过"}' \
  http://localhost:8000/api/v1/bills/invoices/applications/APP20260324123456/audit
```

### 发送账单邮件
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bill_id": "BILL202603A1B2C3D4"}' \
  http://localhost:8000/api/v1/bills/monthly/send-email
```

---

## 账单生成流程

### 1. 月度账单生成
```
定时器/管理员触发
  -> BillingInvoiceManager.generate_all_monthly_bills(year, month)
  -> 遍历所有账户
  -> MonthlyBillService.generate_monthly_bill(user_id, account_id, year, month)
  -> 计算消费统计 (_calculate_consumption_stats)
  -> 创建账单记录
  -> 设置支付截止日（次月 25 日）
```

### 2. 账单邮件推送
```
定时器/管理员触发
  -> BillingInvoiceManager.send_bill_emails(billing_month)
  -> 获取未发送邮件的账单
  -> BillEmailService.send_bill_email(bill, email)
  -> 生成邮件内容
  -> 调用邮件服务发送
  -> 记录邮件日志
  -> 更新账单 email_sent 状态
```

### 3. 发票申请流程
```
用户申请开票
  -> POST /api/v1/bills/invoices/request
  -> InvoiceService.create_invoice_application()
  -> 创建申请记录 (audit_status=pending)

管理员审核
  -> POST /api/v1/bills/invoices/applications/{id}/audit
  -> InvoiceService.audit_application()
  -> 如果批准：创建发票记录 (Invoice)
  -> 更新申请状态
```

### 4. 发票开具流程
```
管理员开具发票
  -> POST /api/v1/bills/invoices/{id}/issue
  -> InvoiceService.mark_invoice_issued()
  -> 设置发票文件 URL
  -> 更新状态为 issued

纸质发票邮寄
  -> POST /api/v1/bills/invoices/{id}/deliver
  -> InvoiceService.mark_invoice_delivered()
  -> 记录快递信息
  -> 更新状态为 delivered
```

---

## 发票类型说明

| 类型 | 描述 | 交付方式 |
|------|------|---------|
| `electronic` | 电子发票 | 邮件发送 PDF 文件 |
| `paper` | 纸质发票 | 快递邮寄 |

---

## 账单状态说明

| 状态 | 描述 | 说明 |
|------|------|------|
| `unpaid` | 未支付 | 账单已生成，待支付 |
| `paid` | 已支付 | 账单已全额支付 |
| `overdue` | 逾期未付 | 超过支付截止日未支付 |
| `cancelled` | 已取消 | 账单已取消 |

---

## 发票状态说明

| 状态 | 描述 | 说明 |
|------|------|------|
| `pending` | 待开具 | 发票申请已提交 |
| `processing` | 开具中 | 发票正在开具 |
| `issued` | 已开具 | 发票已开具 |
| `delivered` | 已交付 | 发票已交付给用户 |
| `rejected` | 已拒绝 | 发票申请被拒绝 |

---

## 文件清单

### 新增文件
- `backend/app/models/billing_invoice.py` - 账单和发票数据模型
- `backend/app/services/billing_invoice.py` - 账单和发票服务层
- `backend/app/api/billing_invoice.py` - 账单和发票 API 路由
- `docs/PHASE_5_5_BILLING_INVOICE.md` - 本文档

### 修改文件
- `backend/app/models/__init__.py` - 导入账单和发票模型
- `backend/app/api/router.py` - 注册账单和发票路由
- `deploy/init.sql` - 添加账单和发票表结构

---

## 邮件集成说明

### SMTP 配置示例
```python
# 需要在配置中添加邮件服务配置
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "noreply@example.com"
SMTP_PASSWORD = "your_password"
SMTP_FROM = "AI 中台 <noreply@example.com>"
```

### 邮件发送实现
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to, subject, content, attachments=None):
    msg = MIMEMultipart()
    msg['From'] = SMTP_FROM
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'plain', 'utf-8'))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()
```

---

## 测试建议

### 单元测试
1. 账单生成逻辑
2. 消费统计计算
3. 发票申请创建
4. 发票状态流转
5. 邮件内容生成

### 集成测试
1. 账单生成到邮件发送全流程
2. 发票申请到开具全流程
3. 逾期账单更新
4. 账单支付状态更新

### 定时任务测试
1. 每月初自动生成上月账单
2. 每日检查逾期账单
3. 每周批量发送账单邮件

---

## 后续优化建议

1. **自动支付** - 支持绑定支付渠道自动扣款
2. **账单分期** - 支持大额账单分期支付
3. **发票自动化** - 对接税务系统自动开具发票
4. **账单分析** - 提供消费趋势分析和预算建议
5. **优惠管理** - 支持优惠券、折扣码
6. **多币种** - 支持多币种账单
7. **账单推送** - 支持短信、微信等多渠道推送

---

*Phase 5.5 账单和发票系统已完成，可支持基础账单管理和发票处理能力*
