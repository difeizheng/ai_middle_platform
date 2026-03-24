# Phase 5.6 告警中心增强

**完成日期**: 2026-03-24
**状态**: ✅ 已完成

## 概述

告警中心增强功能提供了完整的余额、配额、成本预警系统，支持多种通知渠道和灵活的订阅管理。

## 功能特性

### 1. 预警类型

| 预警类型 | 说明 | 触发条件 |
|---------|------|---------|
| 余额预警 (balance) | 账户余额低于阈值 | balance < BALANCE_WARNING_THRESHOLD (默认 100 CNY) |
| 配额预警 (quota) | 配额使用率达到阈值 | usage_rate >= QUOTA_WARNING_THRESHOLD (默认 80%) |
| 成本预警 (cost) | 月度消费超出预算 | month_consumption >= budget * 0.8 |

### 2. 严重级别

| 级别 | 说明 | 颜色 |
|------|------|------|
| info | 提示信息 | 蓝色 |
| warning | 警告 | 橙色 |
| error | 错误 | 红色 |
| critical | 严重 | 紫色 |

### 3. 预警状态

| 状态 | 说明 |
|------|------|
| pending | 待处理 |
| sent | 已通知 |
| acknowledged | 已确认 |
| resolved | 已解决 |

### 4. 通知渠道

支持多种通知渠道类型：
- **Email**: 邮件通知
- **SMS**: 短信通知
- **Webhook**: HTTP Webhook
- **Slack**: Slack 消息

## 架构设计

### 数据模型

```
alert_channels         - 告警通知渠道配置
alert_subscriptions    - 用户告警订阅
warning_alerts         - 预警记录
alert_templates        - 告警模板
```

### 服务层

```
AlertChannelService      - 告警渠道管理
AlertSubscriptionService - 告警订阅管理
WarningAlertService      - 预警检查与通知
AlertTemplateService     - 告警模板管理
```

## API 接口

### 告警渠道管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/alert/channels | 获取渠道列表 | 登录用户 |
| GET | /api/v1/alert/channels/{id} | 获取渠道详情 | 登录用户 |
| POST | /api/v1/alert/channels | 创建渠道 | 管理员 |
| PUT | /api/v1/alert/channels/{id} | 更新渠道 | 管理员 |
| DELETE | /api/v1/alert/channels/{id} | 删除渠道 | 管理员 |

### 告警订阅管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/alert/subscriptions | 获取订阅列表 | 登录用户 |
| GET | /api/v1/alert/subscriptions/{id} | 获取订阅详情 | 登录用户 |
| POST | /api/v1/alert/subscriptions | 创建订阅 | 登录用户 |
| PUT | /api/v1/alert/subscriptions/{id} | 更新订阅 | 登录用户 |
| DELETE | /api/v1/alert/subscriptions/{id} | 删除订阅 | 登录用户 |

### 预警记录管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/alert/warnings | 获取预警列表 | 登录用户 |
| GET | /api/v1/alert/warnings/{id} | 获取预警详情 | 登录用户 |
| POST | /api/v1/alert/warnings/{id}/acknowledge | 确认预警 | 登录用户 |
| POST | /api/v1/alert/warnings/{id}/resolve | 解决预警 | 登录用户 |
| POST | /api/v1/alert/check | 运行预警检查 | 管理员 |

### 告警模板管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/alert/templates | 获取模板列表 | 登录用户 |
| GET | /api/v1/alert/templates/{id} | 获取模板详情 | 登录用户 |
| POST | /api/v1/alert/templates | 创建模板 | 管理员 |
| PUT | /api/v1/alert/templates/{id} | 更新模板 | 管理员 |
| DELETE | /api/v1/alert/templates/{id} | 删除模板 | 管理员 |

### 统计信息

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/alert/stats | 获取告警统计（7 天内） |

## 配置项

### 环境变量配置

```python
# 告警阈值配置
BALANCE_WARNING_THRESHOLD = 100.0  # 余额预警阈值（CNY）
QUOTA_WARNING_THRESHOLD = 0.8      # 配额预警阈值（80%）

# SMTP 邮件配置
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USERNAME = ""
SMTP_PASSWORD = ""
SMTP_FROM_EMAIL = "noreply@example.com"
SMTP_FROM_NAME = "AI 中台"
```

## 使用示例

### 1. 创建邮件通知渠道

```bash
curl -X POST http://localhost:8000/api/v1/alert/channels \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "admin-email",
    "channel_type": "email",
    "display_name": "管理员邮箱",
    "config": {"recipient_email": "admin@example.com"},
    "is_active": true
  }'
```

### 2. 创建余额预警订阅

```bash
curl -X POST http://localhost:8000/api/v1/alert/subscriptions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "balance",
    "channel_ids": [1],
    "custom_threshold": 50.0
  }'
```

### 3. 手动触发预警检查

```bash
curl -X POST http://localhost:8000/api/v1/alert/check \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"check_type": "all"}'
```

### 4. 查询预警记录

```bash
curl -X GET "http://localhost:8000/api/v1/alert/warnings?status=pending&limit=20" \
  -H "Authorization: Bearer <token>"
```

## 自动预警检查

系统每隔 60 秒自动执行一次预警检查（可通过配置修改）：

```python
# backend/app/main.py
# 启动告警检查器
await start_alert_service(interval=60)
```

预警检查包括：
1. 余额预警检查 - 检查所有账户余额
2. 配额预警检查 - 检查当前周期配额使用率
3. 成本预警检查 - 检查月度消费

## 通知邮件模板

预警邮件采用 HTML 格式，包含：
- 预警类型和严重级别
- 资源信息
- 当前值和阈值
- 发生时间
- 预警消息详情

## 前端功能

告警中心管理页面 (`/alerts`) 提供：

1. **统计仪表盘**
   - 总预警数
   - 待处理/已确认/已解决统计

2. **预警记录管理**
   - 列表展示和筛选
   - 详情查看
   - 确认/解决操作
   - 日期范围过滤

3. **通知渠道管理**
   - 渠道列表
   - 新增/编辑渠道

4. **告警订阅管理**
   - 订阅列表
   - 启用/禁用切换
   - 自定义阈值配置

## 文件清单

### 后端文件

| 文件 | 说明 |
|------|------|
| `backend/app/models/alert.py` | 告警数据模型 |
| `backend/app/services/alert.py` | 告警服务层 |
| `backend/app/api/alert.py` | 告警 API 路由 |
| `backend/app/services/alert_service.py` | 告警检查服务（已更新） |
| `backend/app/api/router.py` | 路由注册（已更新） |

### 前端文件

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/AlertManagement.tsx` | 告警中心管理页面 |
| `frontend/src/pages/Layout.tsx` | 菜单更新 |
| `frontend/src/App.tsx` | 路由更新 |

### 数据库文件

| 文件 | 说明 |
|------|------|
| `deploy/init.sql` | 数据库表结构（已更新） |

## 数据库表

### alert_channels
```sql
- id: 渠道 ID
- name: 渠道名称
- channel_type: 渠道类型 (email/sms/webhook/slack)
- display_name: 显示名称
- config: 渠道配置 (JSON)
- is_active: 是否启用
```

### alert_subscriptions
```sql
- id: 订阅 ID
- user_id: 用户 ID
- alert_type: 告警类型 (balance/quota/cost)
- resource_type: 资源类型
- resource_id: 资源 ID
- channel_ids: 通知渠道 ID 列表
- is_enabled: 是否启用
- custom_threshold: 自定义阈值
```

### warning_alerts
```sql
- id: 预警 ID
- alert_type: 预警类型
- alert_subtype: 预警子类型
- resource_type: 资源类型
- resource_id: 资源 ID
- user_id: 用户 ID
- current_value: 当前值
- threshold_value: 阈值
- unit: 单位
- severity: 严重级别
- status: 状态
- message: 预警消息
- notified_channels: 已通知渠道
- notified_at: 通知时间
```

### alert_templates
```sql
- id: 模板 ID
- name: 模板名称
- template_type: 模板类型
- subject_template: 主题模板
- content_template: 内容模板
- alert_types: 适用的告警类型
- is_active: 是否启用
- is_default: 是否默认模板
```

## 集成说明

### 与计费系统集成

预警检查服务会定期检查账户余额和消费情况：
- 余额低于 `BALANCE_WARNING_THRESHOLD` 触发预警
- 月度消费达到预算 80% 触发预警

### 与配额集成

预警检查服务会检查配额使用率：
- 使用率达到 80% 触发警告级别预警
- 使用率达到或超过 100% 触发严重级别预警

### 与邮件集成

预警通知使用已有的邮件服务：
- `backend/app/services/email.py` 提供邮件发送功能
- 支持 HTML 格式邮件
- 支持附件（可选）

## 后续优化建议

1. **通知渠道扩展**: 支持更多第三方通知服务（钉钉、企业微信等）
2. **告警聚合**: 相同类型的告警进行聚合，避免重复通知
3. **告警升级**: 长时间未处理的告警自动升级严重级别
4. **告警静默**: 支持设置免打扰时段
5. **告警分析**: 提供告警趋势分析和报表功能
