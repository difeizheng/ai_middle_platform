# AI 中台系统 - 使用帮助

**版本：** v0.8.0
**最后更新：** 2026 年 3 月 24 日

---

## 快速开始

### 1. 启动服务

```bash
# Docker Compose 启动（推荐）
docker-compose -f deploy/docker-compose.yml up -d

# 查看日志
docker-compose logs -f backend
```

### 2. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端 API | http://localhost:8000 | API 接口 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| 前端 | http://localhost:3000 | Web 控制台 |

### 3. 默认账户

```
用户名：admin
密码：admin123
```

---

## 核心功能

### Phase 1 - 基础平台
- **模型工厂** - 统一接入和管理多模型（OpenAI/vLLM/DeepSeek 等）
- **知识工厂** - 文档解析、向量化、混合检索
- **API 网关** - 认证鉴权、限流熔断、审计日志
- **应用管理** - 应用接入和 API Key 管理

### Phase 2.1 - 智能体工厂
- **单智能体引擎** - 支持 ReAct/Plan-Execute 模式
- **流程引擎** - 多智能体编排和执行
- **工具系统** - 内置工具和扩展机制
- **记忆管理** - 短期/长期记忆支持

### Phase 2.2 - MCP 连接器
- **11 个内置连接器** - MySQL/PostgreSQL/HTTP/Redis/File/Kafka/MongoDB/Elasticsearch/Oracle/SQL Server
- **统一协议** - 标准化的连接器接口

### Phase 2.3 - Skills 市场
- **4 个内置 Skills** - data_analysis/report_generator/code_review/notification
- **版本管理** - Skill 版本控制和回滚
- **评分评论** - 用户对 Skill 进行评分和评论

### Phase 2.4 - 运营监控
- **监控指标** - counter/gauge/histogram 三种指标类型
- **健康检查** - 定期检查服务健康状态
- **告警管理** - 告警规则配置、告警历史

### Phase 4 - 生态建设
- **开发者门户** - API 文档、SDK 下载、开发者指南
- **合作伙伴计划** - 认证级/金牌/白金三级认证
- **行业解决方案** - 解决方案模板、案例库
- **生态联盟** - 成员管理、资源共享、合作机会

### Phase 5.1 - 计费系统（新增）
- **计费策略** - 按 Token/按调用次数/包月
- **账户管理** - 余额管理、充值消费
- **实时计费** - API 调用自动计费
- **统计报表** - 使用趋势、消费分析

---

## API 使用示例

### 认证获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 模型推理

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }' \
  http://localhost:8000/api/v1/inference/chat/completions
```

### 知识库检索

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "knowledge_base_id": "kb-001",
    "query": "如何重置密码",
    "top_k": 5
  }' \
  http://localhost:8000/api/v1/knowledge/search
```

### 智能体执行

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-001",
    "input": "查询上个月的销售数据"
  }' \
  http://localhost:8000/api/v1/agents/execute
```

### Skills 调用

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{"name": "A", "age": 25}, {"name": "B", "age": 30}],
    "operation": "statistic",
    "config": {"fields": ["age"]}
  }' \
  http://localhost:8000/api/v1/skills/skills/data_analysis/execute
```

### 计费相关

```bash
# 获取账户信息
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/billing/account

# 账户充值
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "payment_method": "alipay"}' \
  http://localhost:8000/api/v1/billing/account/recharge

# 获取计费记录
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/billing/account/records?limit=20"

# 获取使用趋势
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/billing/account/usage/trend?days=7"
```

### Phase 5.2 配额管理 API

```bash
# 创建配额
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日模型调用配额",
    "quota_type": "daily_calls",
    "resource_type": "model_call",
    "limit_value": 1000,
    "scope_type": "user",
    "scope_id": "user-123",
    "period_type": "daily",
    "over_limit_action": "reject"
  }' \
  http://localhost:8000/api/v1/quota/quotas

# 获取配额使用情况
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/quota/quotas/usage
```

### Phase 5.3 使用量统计 API

```bash
# 获取实时使用量
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/stats/usage/realtime

# 获取使用趋势
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/trend?days=7&granularity=day"

# 按模型分析使用量
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/breakdown?dimension=model&days=7"

# 获取成本分析
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/cost-analysis?days=7"

# 获取 TOP 模型排行
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/stats/usage/top-resources?days=7&limit=5"
```

---

## 文档导航

| 文档 | 路径 | 说明 |
|------|------|------|
| 架构设计 | `docs/architecture.md` | 技术架构文档 |
| Phase 4 总结 | `docs/PHASE_4_SUMMARY.md` | 生态建设总结 |
| Phase 5 计费 | `docs/PHASE_5_BILLING.md` | 计费系统文档 |
| Phase 5.2 配额 | `docs/PHASE_5_2_QUOTA.md` | 配额管理文档 |
| Phase 5.3 统计 | `docs/PHASE_5_3_USAGE_STATS.md` | 使用量统计文档 |
| Phase 5 规划 | `docs/PHASE_5_PLANNING.md` | Phase 5+ 功能规划 |
| API 示例 | `backend/docs/API_EXAMPLES.md` | API 调用示例 |
| 错误响应 | `backend/docs/ERROR_RESPONSE_FORMAT.md` | 错误响应格式 |
| API Key 加密 | `backend/docs/API_KEY_ENCRYPTION.md` | API Key 加密说明 |

---

## 常见问题

### 1. 如何添加新模型？
在管理控制台或通过 API 创建模型记录，配置模型类型、base_url、api_key 等参数。

### 2. 如何创建知识库？
调用 `POST /api/v1/knowledge` 创建知识库，然后上传文档进行向量化。

### 3. 如何自定义计费策略？
调用 `POST /api/v1/billing/plans` 创建计费方案，支持按 Token、按调用次数、包月等模式。

### 4. 余额不足怎么办？
调用充值接口进行账户充值，或联系管理员调整配额。

### 5. 如何查看 API 调用日志？
调用 `GET /api/v1/logs` 查看 API 调用日志，支持按时间、端点、用户过滤。

---

## 技术支持

- **GitHub**: https://github.com/difeizheng/ai_middle_platform
- **文档**: http://localhost:8000/docs
- **邮件**: admin@example.com

---

*Last updated: 2026-03-24*
