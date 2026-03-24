# Phase 5.2 配额管理功能实现文档

**版本：** v0.8.0
**日期：** 2026 年 3 月 24 日
**状态：** ✅ 已完成

---

## 概述

Phase 5.2 配额管理功能已成功实现，为 AI 中台提供细粒度的资源配额控制能力，支持多级配额、多种配额类型和灵活的周期管理。

---

## 实现内容

### 1. 数据模型

文件位置：`backend/app/models/quota.py`

#### Quota（配额定义）
```python
class Quota(Base, TimestampMixin):
    """配额定义表"""
    __tablename__ = "quotas"

    # 基本字段
    id, name, description
    quota_type        # qps/daily_calls/token_usage/concurrent
    resource_type     # model_call/knowledge_base/agent/skill/all
    limit_value       # 限制值
    unit              # calls/tokens/second

    # 周期管理
    period_type       # hourly/daily/weekly/monthly/none
    reset_time        # 重置时间，如 "00:00"

    # 配额层级
    scope_type        # user/app/api_key
    scope_id          # 对应的 user_id/app_id/api_key_id

    # 继承关系
    parent_quota_id   # 父配额 ID
    is_inherited      # 是否从上级继承

    # 超额处理
    over_limit_action # reject/allow/log
    over_limit_rate   # 超额费率系数
```

#### QuotaUsage（配额使用量）
```python
class QuotaUsage(Base, TimestampMixin):
    """配额使用量表"""
    __tablename__ = "quota_usage"

    quota_id, scope_type, scope_id
    period_start, period_end  # 统计周期
    used_value, limit_value, remaining_value
    exceeded_value  # 超额记录
```

#### QuotaCheckLog（配额检查日志）
```python
class QuotaCheckLog(Base, TimestampMixin):
    """配额检查日志表"""
    __tablename__ = "quota_check_logs"

    # 记录每次配额检查的详情
    check_type, resource_type, requested_amount
    is_allowed, reject_reason
```

---

### 2. 服务层

文件位置：`backend/app/services/quota.py`

#### QuotaService（配额服务）

| 方法 | 描述 |
|------|------|
| `get_quota(quota_id)` | 获取配额定义 |
| `list_quotas(...)` | 获取配额列表 |
| `create_quota(...)` | 创建配额定义 |
| `update_quota(quota_id, **kwargs)` | 更新配额定义 |
| `delete_quota(quota_id)` | 删除配额定义 |
| `get_or_create_usage(...)` | 获取或创建使用记录 |
| `check_quota(...)` | 检查配额是否充足 |
| `update_quota_usage(...)` | 更新配额使用量 |
| `get_usage_stats(...)` | 获取使用统计 |

#### 核心逻辑

**配额检查流程：**
1. 获取所有适用的配额（按 scope_type、scope_id、resource_type 过滤）
2. 计算当前周期（根据 period_type 和 reset_time）
3. 获取或创建使用记录
4. 检查剩余额度
5. 根据 over_limit_action 处理超额情况

**周期计算支持：**
- `hourly` - 每小时重置
- `daily` - 每天重置（支持自定义 reset_time）
- `weekly` - 每周重置（周一零点）
- `monthly` - 每月重置（1 号零点）
- `none` - 不重置（永久配额）

---

### 3. API 路由

文件位置：`backend/app/api/quota.py`

#### 配额定义管理
```
GET    /api/v1/quota/quotas              # 获取配额列表
GET    /api/v1/quota/quotas/{quota_id}   # 获取配额详情
POST   /api/v1/quota/quotas              # 创建配额
PUT    /api/v1/quota/quotas/{quota_id}   # 更新配额
DELETE /api/v1/quota/quotas/{quota_id}   # 删除配额
```

#### 配额检查
```
POST   /api/v1/quota/quotas/check        # 检查配额是否充足
POST   /api/v1/quota/quotas/usage/update # 更新配额使用量
```

#### 使用统计
```
GET    /api/v1/quota/quotas/usage        # 获取当前使用情况
GET    /api/v1/quota/quotas/usage/stats  # 获取使用统计
```

#### 配额重置
```
POST   /api/v1/quota/quotas/{quota_id}/reset  # 重置配额（管理员）
```

---

### 4. 中间件

文件位置：`backend/app/middleware/quota_check.py`

#### QuotaCheckMiddleware（配额检查中间件）

自动在以下端点进行配额检查：
- `/api/v1/inference/chat/completions` → `model_call`
- `/api/v1/inference/embeddings` → `model_call`
- `/api/v1/inference/generate` → `model_call`
- `/api/v1/knowledge/search` → `knowledge_base`
- `/api/v1/agents/execute` → `agent`
- `/api/v1/skills/skills/*` → `skill`

#### 功能特性
- **预检查** - 请求执行前检查配额
- **后更新** - 请求成功后更新使用量
- **失败不阻断** - 配额检查失败仅记录日志，不阻断请求
- **灵活配置** - 支持启用/禁用和排除路径配置

#### 装饰器方式
```python
@app.post("/some/endpoint")
@check_quota(resource_type="model_call", amount=1)
async def some_endpoint(...):
    ...
```

---

### 5. 数据库迁移

文件位置：`deploy/init.sql`

新增 3 个表：
- `quotas` - 配额定义表
- `quota_usage` - 配额使用量表
- `quota_check_logs` - 配额检查日志表

索引：
- `idx_quotas_name` - 按名称查询
- `idx_quotas_type` - 按类型查询
- `idx_quotas_scope` - 按层级查询
- `idx_quotas_resource` - 按资源类型查询
- `idx_quota_usage_quota` - 按配额 ID 查询
- `idx_quota_usage_scope` - 按层级查询
- `idx_quota_usage_period` - 按周期查询
- `idx_quota_usage_unique` - 唯一索引（防止重复记录）

---

## API 调用示例

### 创建配额
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日模型调用配额",
    "quota_type": "daily_calls",
    "resource_type": "model_call",
    "limit_value": 1000,
    "scope_type": "user",
    "scope_id": "user-123",
    "unit": "calls",
    "period_type": "daily",
    "reset_time": "00:00",
    "over_limit_action": "reject"
  }' \
  http://localhost:8000/api/v1/quota/quotas
```

### 检查配额
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "user",
    "scope_id": "user-123",
    "resource_type": "model_call",
    "requested_amount": 1
  }' \
  http://localhost:8000/api/v1/quota/quotas/check
```

### 获取使用情况
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/quota/quotas/usage
```

### 重置配额
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scope_id": "user-123"}' \
  http://localhost:8000/api/v1/quota/quotas/user-123/reset
```

---

## 配额类型说明

| 类型 | 描述 | 单位 | 典型场景 |
|------|------|------|---------|
| `qps` | 每秒请求数 | requests/s | API 限流 |
| `daily_calls` | 日调用次数 | calls | 每日用量限制 |
| `token_usage` | Token 用量 | tokens | Token 消耗限制 |
| `concurrent` | 并发数 | connections | 并发连接限制 |

---

## 配额层级说明

| 层级 | scope_type | scope_id | 说明 |
|------|-----------|----------|------|
| 用户级 | `user` | user_id | 绑定到具体用户 |
| 应用级 | `app` | app_id | 绑定到应用 |
| APIKey 级 | `api_key` | api_key_id | 绑定到具体 API Key |

---

## 超额处理策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `reject` | 拒绝请求，返回 429 错误 | 严格限制 |
| `allow` | 允许超额使用 | 弹性场景 |
| `log` | 记录日志但允许使用 | 监控场景 |

---

## 配额继承机制

- 子配额可以继承父配额的设置
- `is_inherited=True` 表示从父配额继承
- 支持多级继承结构
- 配额检查时会聚合所有适用的配额

---

## 文件清单

### 新增文件
- `backend/app/models/quota.py` - 配额数据模型
- `backend/app/services/quota.py` - 配额服务层
- `backend/app/api/quota.py` - 配额 API 路由
- `backend/app/middleware/quota_check.py` - 配额检查中间件
- `docs/PHASE_5_2_QUOTA.md` - 本文档

### 修改文件
- `backend/app/models/__init__.py` - 导入配额模型
- `backend/app/api/router.py` - 注册配额路由
- `backend/app/main.py` - 注册配额中间件
- `deploy/init.sql` - 添加配额表结构

---

## 测试建议

### 单元测试
1. 配额 CRUD 操作
2. 周期计算逻辑
3. 配额检查逻辑
4. 使用量更新逻辑

### 集成测试
1. 中间件自动检查
2. 配额不足返回 429
3. 配额重置功能
4. 多层级配额聚合

### 压力测试
1. 高并发配额检查
2. 配额并发更新
3. 周期边界场景

---

## 与计费系统集成

配额管理可与计费系统协同工作：

1. **配额 + 计费** - 配额限制用量，计费系统扣费
2. **超额费率** - 超额部分按 `over_limit_rate` 系数计费
3. **独立使用** - 两者也可独立使用

---

## 后续优化建议

1. **配额模板** - 预定义配额模板，快速应用
2. **配额交易** - 支持配额转赠和购买
3. **智能预测** - 基于历史用量预测配额需求
4. **自动调整** - 根据使用情况自动调整配额
5. **配额告警** - 用量达到阈值时告警通知

---

*Phase 5.2 配额管理功能已完成，可支持细粒度资源配额控制*
