# AI 中台项目记忆

> 最后更新：2026 年 3 月 24 日

---

## 项目背景

**客户：** 湖北省农信社
**项目：** AI 中台解决方案宣讲 PPT
**时间：** 2026 年 3 月

---

## 开发进度

### 当前版本：v0.9.0

### 已完成阶段
- **Phase 1** - 基础平台（模型工厂、知识工厂、API 网关、应用管理）
- **Phase 2.1** - 智能体工厂（单智能体引擎、流程引擎、工具系统、记忆管理）
- **Phase 2.2** - MCP 连接器（11 个内置连接器：MySQL/PostgreSQL/HTTP/Redis/File/Kafka/MongoDB/Elasticsearch/Oracle/SQL Server/Kafka）
- **Phase 2.3** - Skills 市场（4 个内置 Skills：data_analysis/report_generator/code_review/notification）
- **Phase 2.4** - 运营监控（监控指标服务、健康检查器、告警管理、仪表盘、告警通知集成）
- **Phase 3** - 技术债务清理和性能优化（统一错误响应、API Key 加密、输入验证、慢查询优化）
- **Phase 4** - 生态建设（开发者门户、合作伙伴计划、行业解决方案、生态联盟）
- **Phase 5.1** - 计费系统（计费策略、账户管理、实时计费、充值管理）✅
- **Phase 5.2** - 配额管理（多级配额、配额类型、周期管理、超额处理）✅
- **Phase 5.3** - 使用量统计（实时统计、历史趋势、多维度分析、成本分析、预测分析）✅

### 短期任务完成情况（2026-03-24）
- ✅ MCP 连接器扩展：Oracle 连接器、SQL Server 连接器
- ✅ Skills 市场增强：评分和评论系统、版本回滚功能
- ✅ 运营监控增强：告警通知集成（邮件/钉钉/企业微信/Webhook）
- ✅ 支付渠道集成（Phase 5.4）：支付宝/微信/银联支付
- ✅ 账单和发票系统（Phase 5.5）：月度账单、发票管理
- ✅ 告警中心增强（Phase 5.6）：余额/配额/成本预警、多渠道通知

### 技术栈更新
- **后端：** Python 3.10+, FastAPI, SQLAlchemy
- **数据库：** PostgreSQL 15+, Redis 7+
- **向量库：** Milvus 2.3+ / Qdrant
- **AI 框架：** LangChain, vLLM, Transformers
- **前端：** React, TypeScript, Ant Design

---

## 核心产品信息

### AI 中台定位
- **定义：** 企业级 AI 能力的基础设施，将分散的 AI 能力统一纳管、标准化封装、服务化输出
- **比喻：** 像「水电厂」一样即取即用，像「操作系统」一样屏蔽底层，像「数字神经中枢」一样连接业务与智能
- **核心价值：** 一次建设，多次复用；赋能升级，而非推倒重来

### 三个核心理念
1. **能力复用** — 而非重复建设（一个模型，全行共享）
2. **赋能升级** — 而非推倒重来（不重构现有系统，2 周完成对接）
3. **持续运营** — 而非项目交付（AI 中台是产品，需要持续运营）

### 产品架构
- **五层架构：** 基础设施层 → 模型层 → 能力层 → 网关层 → 应用层
- **七大中枢：** 知识中心、智能体中心、MCP 服务、Skills 技能中心、数据接入、模型中心、基础保障

### 核心差异化能力
1. **MCP 协议** — Model Context Protocol，2 周完成系统对接
2. **全链路审计** — AI 黑盒白盒化，每一次交互都可复盘、可定责、可优化
3. **私有化部署** — 数据不出域，满足金融级安全合规
4. **吉量智能助手** — 统一入口，多模态交互

### 效率提升数据（实测）
| 场景 | 提升倍数 |
|------|---------|
| 项目表单和可研报告审查 | 3600 倍 |
| 投资研究报告编制 | 2880 倍 |
| 供应链效能监测简报 | 1000 倍+ |
| 中标通知书生成 | 60-240 倍 |
| 合同内容比对 | 5-15 倍 |
| 立项前置条件审查 | 60 倍 |

---

## PPT 版本记录

### V1 原版（59 页）
- 文件名：`V2 湖北省农信 AI 中台解决方案_20260319.pptx`
- 问题：缺少 AI 中台定义页，逻辑结构不清晰，场景部分过于冗长

### V2 优化版（40 页）
- 文件名：`湖北省农信 AI 中台解决方案（优化版）.pptx`
- 改进：新增「什么是 AI 中台」「三个核心理念」，精简场景部分，增加金句页

### 商务推介版（33 页）
- 文件名：`企业级 AI 中台解决方案商务推介.pptx`
- 用途：通用商务推介，非针对湖北农信

---

## 关键文件路径

| 文件 | 路径 |
|------|------|
| 优化版 PPT | `D:/project_room/workspace2024/nantian/sx-ai/ai_middle_platform/湖北省农信 AI 中台解决方案（优化版）.pptx` |
| 修改意见 | `D:/project_room/workspace2024/nantian/sx-ai/ai_middle_platform/湖北省农信 AI 中台 PPT 修改意见.md` |
| PPT 内容整理 | `D:/project_room/workspace2024/nantian/sx-ai/ai_middle_platform/湖北省农信 AI 中台解决方案_PPT 内容整理.md` |
| 商务推介 PPT 规划 | `D:/project_room/workspace2024/nantian/sx-ai/ai_middle_platform/AI 中台商务推介 PPT 规划与大纲.md` |

---

## PPT 优化原则（通用）

1. **先认知对齐，再讲细节** — 先回答「是什么」，再讲「架构/功能/场景」
2. **逻辑顺序：** 是什么 → 为什么 → 怎么做 → 效果如何
3. **场景精简** — 精选 3-5 个核心场景，其他用总览表带过
4. **金句强化记忆** — 在关键节点设置金句页
5. **客户视角** — 多讲「你能得到什么价值」，少讲「我们有什么功能」

---

## 客户反馈记录

**部门老大意见：**
> "我感觉还可以优化一下，这个是用于湖北农信 AI 中台交流，AI 中台是什么，我们的理解，这个我觉得要加一下，然后才是架构、功能、赋能、实际落地场景等这些介绍"

**分析结论：** 老大的感觉是对的，核心问题是缺少「AI 中台是什么」的定义页和「我们的理解」理念页。

---

## 演讲建议

- **总时长：** 25-35 分钟 + Q&A
- **节奏分配：**
  - 认知对齐：3 分钟
  - 为什么需要：5 分钟
  - 整体架构：8 分钟
  - 核心能力：8 分钟
  - 落地场景：8 分钟
  - 总结与展望：5 分钟

---

*此记忆文件用于记录 AI 中台项目的关键信息，便于后续参考和延续工作。*

---

## Phase 4 生态建设（2026-03-24 完成）

### 开发者门户
- API 文档中心：`/api/v1/developer/docs/*`
- SDK 下载：Python/JavaScript/Go SDK
- 开发者指南：快速开始、认证鉴权、核心功能使用
- 示例代码：模型推理、知识检索、智能体工作流、Skills 使用

### 合作伙伴计划
- 合作伙伴管理：`/api/v1/partners/*`
- 认证体系：认证级/金牌/白金三级
- 合作伙伴申请和审核流程
- 合作伙伴权益管理
- 合作伙伴活动管理

### 行业解决方案
- 解决方案管理：`/api/v1/solutions/*`
- 解决方案分类和模板
- 解决方案案例库
- 行业最佳实践文档

### 生态联盟
- 联盟成员管理：`/api/v1/alliance/*`
- 资源共享平台：文档/模板/视频/数据集
- 合作机会对接：项目合作/联合研发/人才培训
- 联盟活动管理：生态大会/研讨会/训练营

### 新增数据模型
- `Partner` - 合作伙伴
- `PartnerApplication` - 合作伙伴申请
- `PartnerBenefit` - 合作伙伴权益
- `PartnerActivity` - 合作伙伴活动
- `Solution` - 行业解决方案
- `SolutionCategory` - 解决方案分类
- `SolutionCase` - 解决方案案例
- `SolutionTemplate` - 解决方案模板

### 新增 API 路由
- `/api/v1/developer/*` - 开发者门户
- `/api/v1/partners/*` - 合作伙伴计划
- `/api/v1/solutions/*` - 行业解决方案
- `/api/v1/alliance/*` - 生态联盟

---

## Phase 5 计费系统实现（2026-03-24 完成）

### 计费系统架构
- **计费模式** - 支持按 Token/按调用次数/包月包年
- **账户管理** - 余额管理、充值消费、账户统计
- **实时计费** - API 调用自动扣费、余额预警
- **统计报表** - 使用趋势、消费分析、多维统计

### 新增数据模型
- `BillingPlan` - 计费策略表（支持 token/call/subscription 三种计费类型）
- `Account` - 账户表（余额、累计充值、累计消费）
- `BillingRecord` - 计费记录表（充值/消费/退款/调整）
- `RechargeOrder` - 充值订单表（订单号、支付状态、交易 ID）
- `BillingStats` - 计费统计表（按天统计消费、分资源类型统计）

### 新增服务层
- `BillingService` - 计费方案管理、费用计算
- `AccountService` - 账户管理、充值、消费、退款
- `RechargeOrderService` - 订单管理
- `BillingIntegration` - API 调用实时计费集成

### 新增 API 路由
- `/api/v1/billing/plans` - 计费方案管理（CRUD）
- `/api/v1/billing/account` - 当前用户账户管理
- `/api/v1/billing/account/recharge` - 账户充值
- `/api/v1/billing/account/records` - 计费记录查询
- `/api/v1/billing/account/stats` - 账户统计信息
- `/api/v1/billing/account/usage/trend` - 使用趋势
- `/api/v1/billing/admin/*` - 管理员功能

### 实时计费集成
- 已集成到 `/api/v1/inference/chat/completions`
- 已集成到 `/api/v1/inference/embeddings`
- 已集成到 `/api/v1/inference/generate`

### 新增文件
- `backend/app/models/billing.py` - 计费数据模型
- `backend/app/services/billing.py` - 计费服务层
- `backend/app/services/billing_integration.py` - 实时计费集成
- `backend/app/api/billing.py` - 计费 API 路由
- `docs/PHASE_5_BILLING.md` - 计费系统实现文档
- `docs/PHASE_5_PLANNING.md` - Phase 5+ 功能规划
- `HELP.md` - 系统使用帮助

### 数据库变更
- 更新 `deploy/init.sql` 新增 5 个计费表
- 表名：`billing_plans`, `accounts`, `billing_records`, `recharge_orders`, `billing_stats`

### 技术要点
- 使用 Decimal 保证金额精度
- 支持多模型价格系数配置（model_pricing 字段）
- 支持配额限制和超额费率（overage_rate）
- 余额预警机制（low_balance_warning）
- 计费失败不阻断 API 调用（仅记录日志）
- 余额不足返回 402 错误

---

## Phase 5.2 配额管理实现（2026-03-24 完成）

### 配额系统架构
- **多级配额** - 用户级/应用级/APIKey 级配额
- **配额类型** - QPS/日调用量/Token 用量/并发数
- **周期管理** - hourly/daily/weekly/monthly/none
- **超额处理** - reject/allow/log 三种策略

### 新增数据模型
- `Quota` - 配额定义表（类型、限制、周期、层级）
- `QuotaUsage` - 配额使用量表（周期统计、超额记录）
- `QuotaCheckLog` - 配额检查日志表

### 新增服务层
- `QuotaService` - 配额管理、配额检查、使用量更新
- `QuotaCheckMiddleware` - 配额检查中间件（自动拦截）

### 新增 API 路由
- `/api/v1/quota/quotas` - 配额管理（CRUD）
- `/api/v1/quota/quotas/check` - 配额检查
- `/api/v1/quota/quotas/usage/update` - 更新使用量
- `/api/v1/quota/quotas/usage` - 获取使用情况
- `/api/v1/quota/quotas/usage/stats` - 使用统计
- `/api/v1/quota/quotas/{id}/reset` - 重置配额

### 新增文件
- `backend/app/models/quota.py` - 配额数据模型
- `backend/app/services/quota.py` - 配额服务层
- `backend/app/api/quota.py` - 配额 API 路由
- `backend/app/middleware/quota_check.py` - 配额检查中间件
- `docs/PHASE_5_2_QUOTA.md` - 配额实现文档

### 数据库变更
- 更新 `deploy/init.sql` 新增 3 个配额表
- 表名：`quotas`, `quota_usage`, `quota_check_logs`

### 技术要点
- 支持配额继承（父子配额）
- 支持多种周期类型和自定义重置时间
- 配额检查失败返回 429 错误
- 中间件自动拦截和更新配额

### 待实现功能
- 配额模板 - 预定义配额模板
- 配额交易 - 配额转赠和购买
- 配额告警 - 用量阈值告警

---

## Phase 5.3 使用量统计实现（2026-03-24 完成）

### 统计系统架构
- **实时统计** - 当前小时调用量、Token 使用量
- **历史趋势** - 小时/日/周/月趋势分析
- **多维度分析** - 按模型/资源类型/API 端点分解
- **成本分析** - 总成本、平均成本、资源类型分解
- **预测分析** - 基于历史预测未来用量

### 新增服务层
- `UsageStatsService` - 使用量统计服务

### 新增 API 路由
- `/api/v1/stats/usage/realtime` - 实时使用量
- `/api/v1/stats/usage/trend` - 使用趋势
- `/api/v1/stats/usage/breakdown` - 多维度分析
- `/api/v1/stats/usage/cost-analysis` - 成本分析
- `/api/v1/stats/usage/prediction` - 使用量预测
- `/api/v1/stats/usage/top-resources` - TOP 资源排行

### 新增文件
- `backend/app/services/usage_stats.py` - 使用量统计服务
- `backend/app/api/usage_stats.py` - 使用量统计 API 路由
- `docs/PHASE_5_3_USAGE_STATS.md` - 使用量统计文档

### 技术要点
- 基于 billing_records 表聚合统计
- 支持多种粒度（hour/day/week/month）
- 使用窗口函数计算日均值
- JSON 提取函数解析元数据

---

## Phase 5.4 支付渠道集成（2026-03-24 完成）

### 支付系统架构
- **多渠道支持** - 支付宝/微信/银联
- **订单管理** - 支付订单、退款管理
- **回调处理** - 自动回调验证和订单更新
- **安全管理** - 签名验证、回调日志

### 新增数据模型
- `PaymentChannel` - 支付渠道配置表
- `PaymentOrder` - 支付订单表
- `PaymentRefund` - 支付退款表
- `PaymentCallbackLog` - 支付回调日志表

### 新增服务层
- `PaymentService` - 支付渠道管理
- `PaymentManager` - 支付订单管理、回调处理
- `AlipayService/WechatPayService/UnionPayService` - 渠道特定服务

### 新增 API 路由
- `/api/v1/payment/channels` - 支付渠道管理
- `/api/v1/payment/create` - 创建支付订单
- `/api/v1/payment/orders` - 订单列表
- `/api/v1/payment/callback/*` - 支付回调
- `/api/v1/payment/refund` - 退款管理

### 新增文件
- `backend/app/models/payment.py` - 支付数据模型
- `backend/app/services/payment.py` - 支付服务层
- `backend/app/api/payment.py` - 支付 API 路由
- `docs/PHASE_5_4_PAYMENT.md` - 支付渠道实现文档

### 数据库变更
- 更新 `deploy/init.sql` 新增 4 个支付表
- 表名：`payment_channels`, `payment_orders`, `payment_refunds`, `payment_callback_logs`

---

## Phase 5.5 账单和发票系统（2026-03-24 完成）

### 账单发票架构
- **月度账单** - 自动生成、状态管理、邮件通知
- **发票管理** - 发票申请、审核、开具、交付
- **账单邮件** - 自动发送、打开追踪

### 新增数据模型
- `MonthlyBill` - 月度账单表
- `Invoice` - 发票表
- `InvoiceApplication` - 发票申请表
- `BillEmailLog` - 账单邮件日志表

### 新增服务层
- `MonthlyBillService` - 月度账单管理
- `InvoiceService` - 发票管理
- `BillEmailService` - 账单邮件发送
- `BillingInvoiceManager` - 账单发票统一管理

### 新增 API 路由
- `/api/v1/bills/monthly/*` - 月度账单管理
- `/api/v1/bills/invoices/*` - 发票管理
- `/api/v1/bills/invoices/applications/*` - 发票申请

### 新增文件
- `backend/app/models/billing_invoice.py` - 账单发票数据模型
- `backend/app/services/billing_invoice.py` - 账单发票服务层
- `backend/app/api/billing_invoice.py` - 账单发票 API 路由
- `backend/app/services/email.py` - SMTP 邮件服务
- `docs/PHASE_5_5_BILLING_INVOICE.md` - 账单发票实现文档

### 数据库变更
- 更新 `deploy/init.sql` 新增 4 个账单发票表
- 表名：`monthly_bills`, `invoices`, `invoice_applications`, `bill_email_logs`

---

## Phase 5.6 告警中心增强（2026-03-24 完成）

### 告警系统架构
- **预警类型** - 余额预警/配额预警/成本预警
- **通知渠道** - 邮件/短信/Webhook/Slack
- **订阅管理** - 用户订阅、自定义阈值
- **自动检查** - 定时检查、自动通知

### 新增数据模型
- `AlertChannel` - 告警通知渠道配置
- `AlertSubscription` - 告警订阅表
- `WarningAlert` - 预警记录表
- `AlertTemplate` - 告警模板表

### 新增服务层
- `AlertChannelService` - 渠道管理
- `AlertSubscriptionService` - 订阅管理
- `WarningAlertService` - 预警检查与通知
- `AlertTemplateService` - 模板管理

### 新增 API 路由
- `/api/v1/alert/channels` - 告警渠道管理
- `/api/v1/alert/subscriptions` - 告警订阅
- `/api/v1/alert/warnings` - 预警记录
- `/api/v1/alert/templates` - 告警模板
- `/api/v1/alert/stats` - 告警统计

### 新增文件
- `backend/app/models/alert.py` - 告警数据模型
- `backend/app/services/alert.py` - 告警服务层
- `backend/app/api/alert.py` - 告警 API 路由
- `backend/app/services/alert_service.py` - 告警检查服务（更新）
- `docs/PHASE_5_6_ALERT.md` - 告警中心实现文档
- `frontend/src/pages/AlertManagement.tsx` - 告警管理前端页面

### 配置项
- `BALANCE_WARNING_THRESHOLD = 100.0` - 余额预警阈值
- `QUOTA_WARNING_THRESHOLD = 0.8` - 配额预警阈值
- SMTP 邮件配置

### 前端功能
- 预警记录列表和详情
- 告警渠道管理
- 告警订阅管理
- 统计仪表盘
- 手动触发检查

---

## 待实现功能


## Phase 5 商业化运营 - 文件清单（v1.0.0）

### 数据模型（15 个类）
- `backend/app/models/billing.py` - BillingPlan, Account, BillingRecord, RechargeOrder, BillingStats
- `backend/app/models/quota.py` - Quota, QuotaUsage, QuotaCheckLog
- `backend/app/models/payment.py` - PaymentChannel, PaymentOrder, PaymentRefund, PaymentCallbackLog
- `backend/app/models/billing_invoice.py` - MonthlyBill, Invoice, InvoiceApplication, BillEmailLog
- `backend/app/models/alert.py` - AlertChannel, AlertSubscription, WarningAlert, AlertTemplate

### 服务层（12 个类）
- `backend/app/services/billing.py` - BillingService, AccountService, RechargeOrderService
- `backend/app/services/billing_integration.py` - BillingIntegration
- `backend/app/services/quota.py` - QuotaService
- `backend/app/services/usage_stats.py` - UsageStatsService
- `backend/app/services/payment.py` - PaymentService, PaymentManager, AlipayService, WechatPayService, UnionPayService
- `backend/app/services/billing_invoice.py` - MonthlyBillService, InvoiceService, BillEmailService, BillingInvoiceManager
- `backend/app/services/alert.py` - AlertChannelService, AlertSubscriptionService, WarningAlertService, AlertTemplateService
- `backend/app/services/email.py` - EmailService
- `backend/app/services/alert_service.py` - AlertService（更新）

### API 路由（40+ 端点）
- `backend/app/api/billing.py` - 计费系统 API
- `backend/app/api/quota.py` - 配额管理 API
- `backend/app/api/usage_stats.py` - 使用量统计 API
- `backend/app/api/payment.py` - 支付渠道 API
- `backend/app/api/billing_invoice.py` - 账单和发票 API
- `backend/app/api/alert.py` - 告警中心 API
- `backend/app/middleware/quota_check.py` - 配额检查中间件

### 前端页面
- `frontend/src/pages/BillingManagement.tsx` - 计费管理
- `frontend/src/pages/QuotaManagement.tsx` - 配额管理
- `frontend/src/pages/AlertManagement.tsx` - 告警中心管理

### 文档
- `docs/PHASE_5_BILLING.md` - 计费系统实现文档
- `docs/PHASE_5_2_QUOTA.md` - 配额管理实现文档
- `docs/PHASE_5_3_USAGE_STATS.md` - 使用量统计实现文档
- `docs/PHASE_5_4_PAYMENT.md` - 支付渠道实现文档
- `docs/PHASE_5_5_BILLING_INVOICE.md` - 账单发票实现文档
- `docs/PHASE_5_6_ALERT.md` - 告警中心实现文档
- `docs/PHASE_5_COMMERCIALIZATION_SUMMARY.md` - Phase 5 总结文档
- `CHANGELOG_v0.9.0.md` - v0.9.0 变更日志

---

## 版本记录

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v1.0.0 | 2026-03-24 | Phase 5 完成：计费/配额/统计/支付/账单发票/告警中心 |
| v0.9.0 | 2026-03-24 | Phase 5.2 配额管理、Phase 5.3 使用量统计 |
| v0.8.0 | 2026-03-24 | Phase 5.1 计费系统 |
| v0.7.0 | 2026-03-24 | Phase 4 生态建设 |
| v0.6.0 | 2026-03-24 | Phase 3 技术债务清理 |
