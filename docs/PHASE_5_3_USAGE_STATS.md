# Phase 5.3 使用量统计增强实现文档

**版本：** v0.8.0
**日期：** 2026 年 3 月 24 日
**状态：** ✅ 已完成

---

## 概述

Phase 5.3 使用量统计增强功能已成功实现，为 AI 中台提供全方位的使用量统计和分析能力，包括实时统计、历史趋势、多维度分析、成本分析和预测分析。

---

## 实现内容

### 1. 服务层

文件位置：`backend/app/services/usage_stats.py`

#### UsageStatsService（使用量统计服务）

| 方法 | 描述 | 返回数据 |
|------|------|---------|
| `get_realtime_usage()` | 获取实时使用量 | 当前小时 cost/tokens/calls |
| `get_usage_trend()` | 获取使用趋势 | 按小时/日/周/月趋势 |
| `get_usage_by_dimension()` | 按维度分析 | 按 model/resource_type/endpoint 分解 |
| `get_cost_analysis()` | 成本分析 | 总成本、平均成本、按资源类型分解 |
| `get_prediction()` | 使用量预测 | 基于历史预测未来用量 |
| `get_top_resources()` | TOP 资源排行 | 按模型使用量排行 |

---

### 2. API 路由

文件位置：`backend/app/api/usage_stats.py`

#### API 端点

```
GET  /api/v1/stats/usage/realtime         # 获取实时使用量
GET  /api/v1/stats/usage/trend            # 获取使用趋势
GET  /api/v1/stats/usage/breakdown        # 按维度分析使用量
GET  /api/v1/stats/usage/cost-analysis    # 成本分析
GET  /api/v1/stats/usage/prediction       # 使用量预测
GET  /api/v1/stats/usage/top-resources    # TOP 资源排行
```

---

## API 调用示例

### 获取实时使用量
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/realtime"
```

响应示例：
```json
{
  "success": true,
  "data": {
    "scope_type": "user",
    "scope_id": "user-123",
    "timestamp": "2026-03-24T10:30:00Z",
    "current_hour": {
      "cost": 1.25,
      "tokens": 15000,
      "calls": 50
    }
  }
}
```

### 获取使用趋势
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/trend?days=7&granularity=day"
```

响应示例：
```json
{
  "success": true,
  "data": {
    "scope_type": "user",
    "scope_id": "user-123",
    "days": 7,
    "granularity": "day",
    "trend": [
      {
        "period": "2026-03-18",
        "total_cost": 5.50,
        "total_tokens": 65000,
        "total_calls": 200
      },
      {
        "period": "2026-03-19",
        "total_cost": 6.20,
        "total_tokens": 72000,
        "total_calls": 220
      }
    ]
  }
}
```

### 按维度分析
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/breakdown?dimension=model&days=7"
```

响应示例：
```json
{
  "success": true,
  "data": {
    "scope_type": "user",
    "scope_id": "user-123",
    "dimension": "model",
    "days": 7,
    "breakdown": [
      {
        "model": "gpt-4",
        "total_cost": 25.00,
        "total_tokens": 150000,
        "total_calls": 500
      },
      {
        "model": "gpt-3.5-turbo",
        "total_cost": 10.00,
        "total_tokens": 200000,
        "total_calls": 800
      }
    ]
  }
}
```

### 成本分析
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/cost-analysis?days=7"
```

响应示例：
```json
{
  "success": true,
  "data": {
    "scope_type": "user",
    "scope_id": "user-123",
    "days": 7,
    "summary": {
      "total_cost": 35.00,
      "total_tokens": 350000,
      "total_calls": 1300,
      "avg_cost_per_call": 0.027,
      "avg_cost_per_token": 0.0001
    },
    "cost_by_resource": {
      "model_call": 30.00,
      "knowledge_base": 3.00,
      "agent": 2.00
    }
  }
}
```

### 使用量预测
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/prediction?predict_days=7"
```

响应示例：
```json
{
  "success": true,
  "data": {
    "scope_type": "user",
    "scope_id": "user-123",
    "prediction": {
      "days": 7,
      "predicted_cost": 35.00,
      "predicted_tokens": 350000,
      "confidence": "medium"
    },
    "based_on_days": 30
  }
}
```

### TOP 资源排行
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/top-resources?days=7&limit=5"
```

响应示例：
```json
{
  "success": true,
  "data": {
    "scope_type": "user",
    "scope_id": "user-123",
    "days": 7,
    "top_models": [
      {
        "model": "gpt-4",
        "total_cost": 25.00,
        "total_tokens": 150000,
        "total_calls": 500
      },
      {
        "model": "qwen-72b",
        "total_cost": 8.00,
        "total_tokens": 180000,
        "total_calls": 600
      }
    ]
  }
}
```

---

## 功能特性

### 1. 实时统计
- 当前小时累计消费
- 当前小时 Token 使用量
- 当前小时调用次数

### 2. 历史趋势
- 支持多种粒度：小时/日/周/月
- 可自定义统计天数（1-90 天）
- 趋势数据包含 cost/tokens/calls

### 3. 多维度分析
- **按模型分析** - 不同模型的使用情况
- **按资源类型** - model_call/knowledge_base/agent/skill
- **按 API 端点** - 不同 API 端点的使用情况

### 4. 成本分析
- 总成本统计
- 平均每次调用成本
- 平均每个 Token 成本
- 按资源类型分解成本

### 5. 预测分析
- 基于过去 30 天数据
- 预测未来 1-30 天用量
- 提供置信度评估

### 6. TOP 排行
- TOP 模型使用排行
- 支持自定义返回数量
- 包含 cost/tokens/calls 指标

---

## 文件清单

### 新增文件
- `backend/app/services/usage_stats.py` - 使用量统计服务
- `backend/app/api/usage_stats.py` - 使用量统计 API 路由
- `docs/PHASE_5_3_USAGE_STATS.md` - 本文档

### 修改文件
- `backend/app/api/router.py` - 注册使用量统计路由

---

## 数据来源

使用量统计基于以下数据表：
- `billing_records` - 计费记录（主要数据源）
- `accounts` - 账户表（关联用户）
- `api_logs` - API 调用日志（可选扩展）
- `quota_usage` - 配额使用量（可选扩展）

---

## 性能优化

### 数据库索引
- `billing_records(created_at)` - 时间范围查询
- `billing_records(account_id)` - 账户关联查询
- `billing_records(resource_type)` - 资源类型分组

### 查询优化
- 使用聚合查询减少数据传输
- 使用窗口函数计算日均值
- 使用 JSON 提取函数解析元数据

### 缓存建议（可扩展）
- 实时使用量可缓存 1 分钟
- 趋势数据可缓存 5 分钟
- 成本分析可缓存 10 分钟

---

## 扩展建议

### 1. 维度扩展
- 按部门/团队统计
- 按项目统计
- 按时间段统计（工作日/周末）

### 2. 可视化增强
- 折线图展示趋势
- 饼图展示占比
- 柱状图展示排行

### 3. 告警集成
- 用量异常检测
- 成本超支预警
- 使用量峰值告警

### 4. 报表导出
- 导出 PDF 报表
- 导出 Excel 表格
- 定时邮件报表

---

## 与配额管理集成

使用量统计可与配额管理协同工作：

1. **配额监控** - 实时显示配额使用百分比
2. **配额预测** - 基于趋势预测何时会用尽配额
3. **配额优化** - 识别哪些配额设置不合理

---

*Phase 5.3 使用量统计增强已完成，可支持全方位使用量分析*
