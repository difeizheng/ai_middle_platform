# Phase 5 计费系统实现文档

**版本：** v0.8.0
**日期：** 2026 年 3 月 24 日
**状态：** ✅ 已完成

---

## 概述

Phase 5 计费系统已成功实现，为 AI 中台提供完整的商业化运营能力，包括计费策略管理、账户管理、实时计费、充值管理和统计报表功能。

---

## 实现内容

### 1. 数据模型

文件位置：`backend/app/models/billing.py`

#### BillingPlan（计费策略）
- 支持多种计费类型：token/call/subscription
- 支持按模型设置价格系数
- 支持配额限制和超额费率

#### Account（账户）
- 余额管理
- 累计充值/消费统计
- 计费方案绑定
- 余额预警配置

#### BillingRecord（计费记录）
- 充值/消费/退款/调整记录
- 余额快照（操作前后）
- 资源使用详情（tokens、调用次数）

#### RechargeOrder（充值订单）
- 订单号生成
- 支付状态管理
- 优惠和赠送

#### BillingStats（计费统计）
- 按天统计消费
- 分资源类型统计

---

### 2. 服务层

文件位置：`backend/app/services/billing.py`

#### BillingService（计费服务）
- `get_plan()` - 获取计费方案
- `list_plans()` - 获取计费方案列表
- `create_plan()` - 创建计费方案
- `update_plan()` - 更新计费方案
- `delete_plan()` - 删除计费方案
- `calculate_cost()` - 计算费用

#### AccountService（账户服务）
- `get_account()` - 获取账户
- `get_account_by_user_id()` - 通过用户 ID 获取账户
- `create_account()` - 创建账户
- `get_or_create_account()` - 获取或创建账户
- `recharge()` - 账户充值
- `consume()` - 账户消费
- `refund()` - 账户退款
- `get_billing_records()` - 获取计费记录
- `get_stats()` - 获取统计信息

#### RechargeOrderService（充值订单服务）
- `create_order()` - 创建充值订单
- `get_order()` - 获取订单
- `get_order_by_no()` - 通过订单号获取
- `mark_as_paid()` - 标记为已支付
- `list_orders()` - 获取订单列表

---

### 3. 实时计费集成

文件位置：`backend/app/services/billing_integration.py`

#### BillingIntegration
- `charge_for_api_call()` - 为 API 调用计费
- `check_balance()` - 检查账户余额

#### 便捷函数
- `charge_api_call()` - 直接在 API 中调用的计费函数

---

### 4. API 路由

文件位置：`backend/app/api/billing.py`

#### 计费方案管理
```
GET    /api/v1/billing/plans              # 获取计费方案列表
GET    /api/v1/billing/plans/{plan_id}    # 获取计费方案详情
POST   /api/v1/billing/plans              # 创建计费方案
PUT    /api/v1/billing/plans/{plan_id}    # 更新计费方案
DELETE /api/v1/billing/plans/{plan_id}    # 删除计费方案
```

#### 账户管理
```
GET    /api/v1/billing/account            # 获取当前用户账户
GET    /api/v1/billing/accounts/{id}      # 获取账户详情
POST   /api/v1/billing/accounts           # 创建账户
PUT    /api/v1/billing/account/plan       # 更新计费方案
```

#### 充值管理
```
POST   /api/v1/billing/account/recharge   # 账户充值
GET    /api/v1/billing/account/recharge/orders  # 获取充值订单
```

#### 计费记录
```
GET    /api/v1/billing/account/records    # 获取计费记录
```

#### 统计信息
```
GET    /api/v1/billing/account/stats      # 获取账户统计
GET    /api/v1/billing/account/usage/trend  # 获取使用趋势
```

#### 管理员功能
```
GET    /api/v1/billing/admin/accounts     # 获取所有账户
GET    /api/v1/billing/admin/stats/overview  # 获取计费概览
```

---

### 5. 数据库迁移

文件位置：`deploy/init.sql`

新增 5 个表：
- `billing_plans` - 计费策略表
- `accounts` - 账户表
- `billing_records` - 计费记录表
- `recharge_orders` - 充值订单表
- `billing_stats` - 计费统计表

---

### 6. 实时计费集成

文件位置：`backend/app/api/inference.py`

已在以下 API 中集成实时计费：
- `POST /api/v1/inference/chat/completions` - 聊天补全
- `POST /api/v1/inference/embeddings` - 文本向量化
- `POST /api/v1/inference/generate` - 文本生成

---

## API 调用示例

### 创建计费方案
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "按量付费",
    "billing_type": "token",
    "price_per_1k_tokens": 0.008,
    "price_per_call": 0,
    "monthly_fee": 0,
    "quota_limit": 0,
    "overage_rate": 1,
    "model_pricing": {
      "gpt-4": 2.0,
      "gpt-3.5-turbo": 1.0
    },
    "is_default": true
  }' \
  http://localhost:8000/api/v1/billing/plans
```

### 账户充值
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "payment_method": "alipay"}' \
  http://localhost:8000/api/v1/billing/account/recharge
```

### 获取账户信息
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/billing/account
```

### 获取计费记录
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/billing/account/records?record_type=consume&limit=20"
```

### 获取使用趋势
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/billing/account/usage/trend?days=7"
```

---

## 计费逻辑说明

### 计费流程
1. API 请求到达
2. 获取用户账户（自动创建如果不存在）
3. 获取账户的计费方案
4. 根据使用量（tokens/调用次数）计算费用
5. 从账户扣费
6. 创建计费记录
7. 检查余额预警

### 费用计算公式
```
基础费用 = (tokens_used / 1000) * price_per_1k_tokens
或
基础费用 = call_count * price_per_call

模型系数 = model_pricing[model_name] 或 1.0

最终费用 = 基础费用 * 模型系数 * overage_rate
```

### 余额不足处理
- 扣费前检查余额
- 余额不足返回 402 错误
- 计费失败不阻断 API 调用（仅记录日志）

---

## 配置说明

### 默认计费方案
系统支持设置一个默认计费方案，新用户自动应用。

### 模型价格系数
通过 `model_pricing` 字段为不同模型设置价格系数：
```json
{
  "gpt-4": 2.0,
  "gpt-3.5-turbo": 1.0,
  "qwen-72b": 0.5,
  "chatglm3-6b": 0.3
}
```

### 余额预警
- 默认预警阈值：100 元
- 可在账户设置中修改
- 预警信息记录到日志

---

## 后续扩展建议

### 1. 支付集成
- 接入支付宝/微信支付
- 接入银联支付
- 自动回调处理

### 2. 配额管理
- 实现周期性配额重置
- 配额超限处理
- 配额交易功能

### 3. 账单系统
- 月度账单生成
- 账单导出（PDF/Excel）
- 发票管理

### 4. 成本分析
- 按项目/部门统计
- 成本预测
- 异常消费检测

### 5. 促销功能
- 优惠券
- 充值活动
- 积分系统

---

## 文件清单

### 新增文件
- `backend/app/models/billing.py` - 计费数据模型
- `backend/app/services/billing.py` - 计费服务层
- `backend/app/services/billing_integration.py` - 实时计费集成
- `backend/app/api/billing.py` - 计费 API 路由
- `docs/PHASE_5_BILLING.md` - 本文档

### 修改文件
- `backend/app/models/__init__.py` - 导入计费模型
- `backend/app/api/router.py` - 注册计费路由
- `backend/app/api/inference.py` - 集成实时计费
- `deploy/init.sql` - 添加计费表结构

---

## 测试建议

### 单元测试
1. 计费方案 CRUD
2. 账户充值/消费逻辑
3. 费用计算准确性
4. 余额检查

### 集成测试
1. API 调用触发计费
2. 扣费后余额更新
3. 计费记录生成
4. 余额不足处理

### 压力测试
1. 高并发计费场景
2. 账户并发修改
3. 数据库锁性能

---

## 已知限制

1. **暂不支持周期性计费** - 如月费自动扣除
2. **暂不支持配额重置** - 需要手动实现
3. **暂不支持退款流程** - 仅支持手动调整
4. **支付仅为模拟** - 需要接入真实支付

---

## 下一步计划

1. **Phase 5.2 配额管理** - 细粒度配额控制
2. **Phase 5.3 使用量统计增强** - 多维度分析
3. **Phase 5.4 支付集成** - 真实支付渠道
4. **Phase 5.5 账单系统** - 月度账单和发票

---

*Phase 5 计费系统核心功能已完成，可支持基础商业化运营*
