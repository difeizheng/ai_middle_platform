# Phase 5.4 支付渠道集成实现文档

**版本：** v0.9.0
**日期：** 2026 年 3 月 24 日
**状态：** ✅ 已完成

---

## 概述

Phase 5.4 支付渠道集成已成功实现，为 AI 中台提供完整的支付能力，支持支付宝、微信支付、银联支付等多种支付渠道。

---

## 实现内容

### 1. 数据模型

文件位置：`backend/app/models/payment.py`

#### PaymentChannel（支付渠道配置）
```python
class PaymentChannel(Base):
    """支付渠道配置表"""
    __tablename__ = "payment_channels"

    # 基本字段
    id, channel_name, channel_type
    display_name, description, icon_url

    # 认证配置（加密存储）
    app_id, merchant_id, api_key, api_secret
    public_key, private_key

    # 配置项
    config  # JSON 格式额外配置

    # 渠道状态
    is_active, is_default, support_refund

    # 限额配置
    min_amount, max_amount, daily_limit

    # 费率配置
    fee_rate  # 0.006 = 0.6%
```

#### PaymentOrder（支付订单）
```python
class PaymentOrder(Base):
    """支付订单表"""
    __tablename__ = "payment_orders"

    # 订单号
    order_no, transaction_id  # 渠道交易 ID

    # 关联信息
    account_id, user_id, channel_id

    # 订单金额
    amount, actual_amount, fee_amount

    # 支付信息
    payment_method, payment_status, payment_time

    # 渠道回调数据
    callback_data, callback_time

    # 订单描述
    subject, body, attach

    # 支付凭证
    pay_url, qr_code, app_param

    # 退款信息
    refund_amount, refund_time, refund_reason
```

#### PaymentRefund（支付退款）
```python
class PaymentRefund(Base):
    """支付退款表"""
    __tablename__ = "payment_refunds"

    # 退款单号
    refund_no, refund_transaction_id

    # 关联订单
    order_id, account_id, user_id, channel_id

    # 退款金额
    refund_amount, refund_fee

    # 退款状态
    refund_status, refund_time

    # 退款原因
    reason, description
```

#### PaymentCallbackLog（支付回调日志）
```python
class PaymentCallbackLog(Base):
    """支付回调日志表"""
    __tablename__ = "payment_callback_logs"

    # 回调数据
    order_no, channel_id
    raw_data, parsed_data

    # 验证结果
    signature_valid, verification_result

    # 处理结果
    is_processed, process_result, error_message
```

---

### 2. 服务层

文件位置：`backend/app/services/payment.py`

#### PaymentService（支付渠道服务）
| 方法 | 描述 |
|------|------|
| `get_channel(channel_id)` | 获取支付渠道 |
| `get_channel_by_name(channel_name)` | 根据名称获取渠道 |
| `get_default_channel()` | 获取默认渠道 |
| `list_channels()` | 获取所有启用渠道 |
| `create_channel(data)` | 创建支付渠道 |
| `update_channel(channel_id, data)` | 更新支付渠道 |
| `delete_channel(channel_id)` | 删除支付渠道 |
| `validate_amount(channel, amount)` | 验证金额限额 |
| `check_daily_limit(channel, user_id, amount)` | 检查日限额 |

#### AlipayService（支付宝支付服务）
| 方法 | 描述 |
|------|------|
| `create_order(order_data)` | 创建支付宝订单 |
| `verify_callback(data)` | 验证回调签名 |
| `process_refund(order, amount, reason)` | 处理退款 |

#### WechatPayService（微信支付服务）
| 方法 | 描述 |
|------|------|
| `create_order(order_data)` | 创建微信支付订单 |
| `verify_callback(data)` | 验证回调签名 |
| `process_refund(order, amount, reason)` | 处理退款 |

#### UnionPayService（银联支付服务）
| 方法 | 描述 |
|------|------|
| `create_order(order_data)` | 创建银联支付订单 |
| `verify_callback(data)` | 验证回调签名 |
| `process_refund(order, amount, reason)` | 处理退款 |

#### PaymentManager（支付管理器）
| 方法 | 描述 |
|------|------|
| `create_payment_order(...)` | 创建支付订单 |
| `process_callback(...)` | 处理支付回调 |
| `refund_payment(...)` | 处理退款 |
| `get_order(...)` | 获取订单 |
| `list_orders(...)` | 获取订单列表 |

---

### 3. API 路由

文件位置：`backend/app/api/payment.py`

#### 支付渠道管理
```
GET    /api/v1/payment/channels          # 获取支付渠道列表
GET    /api/v1/payment/channels/default  # 获取默认渠道
POST   /api/v1/payment/channels          # 创建渠道（管理员）
PUT    /api/v1/payment/channels/{id}     # 更新渠道（管理员）
DELETE /api/v1/payment/channels/{id}     # 删除渠道（管理员）
```

#### 支付订单管理
```
POST   /api/v1/payment/create            # 创建支付订单
GET    /api/v1/payment/orders            # 获取订单列表
GET    /api/v1/payment/orders/{id}       # 获取订单详情
GET    /api/v1/payment/orders/query/{no} # 根据订单号查询
```

#### 支付回调处理
```
POST   /api/v1/payment/callback/alipay   # 支付宝回调
POST   /api/v1/payment/callback/wechat   # 微信支付回调
POST   /api/v1/payment/callback/unionpay # 银联支付回调
```

#### 退款管理
```
POST   /api/v1/payment/refund            # 申请退款
GET    /api/v1/payment/refunds           # 获取退款记录
```

---

### 4. 数据库迁移

文件位置：`deploy/init.sql`

新增 4 个表：
- `payment_channels` - 支付渠道配置表
- `payment_orders` - 支付订单表
- `payment_refunds` - 支付退款表
- `payment_callback_logs` - 支付回调日志表

索引：
- `idx_payment_channels_name` - 按渠道名称查询
- `idx_payment_channels_active` - 按状态查询
- `idx_payment_orders_order_no` - 按订单号查询
- `idx_payment_orders_transaction` - 按交易 ID 查询
- `idx_payment_orders_account` - 按账户查询
- `idx_payment_orders_user` - 按用户查询
- `idx_payment_orders_status` - 按状态查询
- `idx_payment_refunds_refund_no` - 按退款单号查询
- `idx_payment_refunds_order` - 按订单查询
- `idx_payment_refunds_status` - 按状态查询
- `idx_payment_callback_logs_order` - 按订单号查询
- `idx_payment_callback_logs_channel` - 按渠道查询

---

## 支付渠道配置说明

### 支付宝配置
```json
{
    "channel_name": "alipay",
    "channel_type": "alipay",
    "display_name": "支付宝支付",
    "app_id": "你的支付宝应用 ID",
    "api_secret": "支付宝应用私钥",
    "public_key": "支付宝公钥",
    "config": {
        "notify_url": "https://your-domain.com/api/v1/payment/callback/alipay",
        "return_url": "https://your-domain.com/payment/success"
    }
}
```

### 微信支付配置
```json
{
    "channel_name": "wechat",
    "channel_type": "wechat",
    "display_name": "微信支付",
    "app_id": "你的微信应用 ID",
    "merchant_id": "你的商户号",
    "api_secret": "微信支付 API v3 密钥",
    "private_key": "商户私钥",
    "config": {
        "notify_url": "https://your-domain.com/api/v1/payment/callback/wechat"
    }
}
```

### 银联支付配置
```json
{
    "channel_name": "unionpay",
    "channel_type": "unionpay",
    "display_name": "银联支付",
    "merchant_id": "你的商户号",
    "api_secret": "银联签名私钥",
    "config": {
        "notify_url": "https://your-domain.com/api/v1/payment/callback/unionpay",
        "return_url": "https://your-domain.com/payment/success"
    }
}
```

---

## API 调用示例

### 创建支付订单
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100.00,
    "channel_id": "channel-xxx",
    "payment_method": "web",
    "subject": "AI 中台充值"
  }' \
  http://localhost:8000/api/v1/payment/create
```

响应：
```json
{
  "success": true,
  "message": "订单创建成功",
  "data": {
    "order_no": "ALI20260324120000123456",
    "amount": 100.00,
    "channel": {...},
    "pay_url": "https://openapi.alipay.com/gateway.do?...",
    "qr_code": null,
    "expires_at": "2026-03-24T12:30:00"
  }
}
```

### 查询订单
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/payment/orders/query/ALI20260324120000123456
```

### 申请退款
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order-xxx",
    "refund_amount": 50.00,
    "reason": "用户申请退款"
  }' \
  http://localhost:8000/api/v1/payment/refund
```

---

## 支付流程

### 1. 创建订单流程
```
用户 -> 前端 -> API POST /api/v1/payment/create
  -> PaymentManager.create_payment_order()
  -> 根据渠道调用对应的支付服务
  -> AlipayService/WechatPayService/UnionPayService.create_order()
  -> 返回支付链接/二维码
  -> 用户完成支付
```

### 2. 支付回调流程
```
支付渠道 -> POST /api/v1/payment/callback/{channel}
  -> 验证签名
  -> 更新订单状态
  -> 更新账户余额
  -> 创建充值订单记录
  -> 返回成功响应
```

### 3. 退款流程
```
用户/管理员 -> API POST /api/v1/payment/refund
  -> PaymentManager.refund_payment()
  -> 调用渠道退款 API
  -> 更新订单状态
  -> 扣减账户余额
  -> 创建退款记录
```

---

## 安全考虑

### 1. 签名验证
- 所有支付回调都进行签名验证
- 使用渠道提供的公钥/证书验证回调真实性

### 2. 密钥管理
- API 密钥和私钥加密存储
- 使用环境变量或密钥管理系统存储敏感信息

### 3. 防重放攻击
- 回调处理时检查订单状态
- 使用渠道提供的 notify_id 去重

### 4. 金额安全
- 使用 Decimal 类型保证金额精度
- 验证金额在限额范围内
- 检查日累计支付限额

---

## 文件清单

### 新增文件
- `backend/app/models/payment.py` - 支付数据模型
- `backend/app/services/payment.py` - 支付服务层
- `backend/app/api/payment.py` - 支付 API 路由
- `docs/PHASE_5_4_PAYMENT.md` - 本文档

### 修改文件
- `backend/app/models/__init__.py` - 导入支付模型
- `backend/app/api/router.py` - 注册支付路由
- `deploy/init.sql` - 添加支付表结构

---

## 测试建议

### 单元测试
1. 支付渠道 CRUD 操作
2. 订单创建逻辑
3. 签名验证逻辑
4. 退款处理逻辑

### 集成测试
1. 创建订单并跳转支付
2. 模拟支付回调处理
3. 退款流程测试
4. 余额更新验证

### 沙箱测试
1. 支付宝沙箱环境测试
2. 微信支付沙箱测试
3. 银联测试环境测试

---

## 后续优化建议

1. **支付渠道扩展** - 支持更多支付渠道（QQ 支付、京东支付等）
2. **自动对账** - 与支付渠道账单自动对账
3. **支付分析** - 支付成功率、转化率分析
4. **优惠活动** - 支持优惠券、折扣活动
5. **订阅支付** - 支持周期性自动扣费
6. **分账功能** - 支持多方分账

---

*Phase 5.4 支付渠道集成已完成，可支持基础支付场景*
