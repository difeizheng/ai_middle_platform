# API 文档示例

本文档提供 AI 中台系统所有 API 的详细请求和响应示例。

## 目录

- [认证 API](#认证-api)
- [应用管理 API](#应用管理-api)
- [模型管理 API](#模型管理-api)
- [知识管理 API](#知识管理-api)
- [智能体工厂 API](#智能体工厂-api)
- [MCP 连接器 API](#mcp-连接器-api)
- [Skills 市场 API](#skills-市场-api)
- [运营监控 API](#运营监控-api)

---

## 认证 API

### 1. 用户登录

**请求:**

```bash
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=admin&password=admin123
```

**成功响应 (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

**失败响应 (401):**

```json
{
  "code": "UNAUTHORIZED",
  "message": "用户名或密码错误",
  "detail": "请检查您的登录凭证",
  "data": null
}
```

### 2. 获取当前用户信息

**请求:**

```bash
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**成功响应 (200):**

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "管理员",
  "role": "admin",
  "department": "技术部"
}
```

---

## 应用管理 API

### 1. 创建应用

**请求:**

```bash
POST /api/v1/applications
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "name": "智能客服系统",
  "description": "企业智能客服系统",
  "app_type": "web"
}
```

**成功响应 (200):**

```json
{
  "id": 1,
  "name": "智能客服系统",
  "api_key": "sk_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
  "api_secret": "xYz789AbCdEfGhIjKlMnOpQrStUvWxYz",
  "key_prefix": "sk_aBcDeFgH",
  "message": "应用创建成功，请妥善保存 API Key 和 Secret"
}
```

> ⚠️ **注意**: `api_key` 和 `api_secret` 只在创建时返回一次，请妥善保存！

### 2. 获取应用列表

**请求:**

```bash
GET /api/v1/applications?skip=0&limit=20
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "total": 3,
  "applications": [
    {
      "id": 1,
      "name": "智能客服系统",
      "description": "企业智能客服系统",
      "app_type": "web",
      "is_active": true,
      "total_calls": 15000
    },
    {
      "id": 2,
      "name": "数据分析平台",
      "description": "BI 数据分析",
      "app_type": "api",
      "is_active": true,
      "total_calls": 8500
    }
  ]
}
```

### 3. 创建 API Key

**请求:**

```bash
POST /api/v1/applications/1/keys
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "expires_days": 365,
  "permissions": ["model:read", "knowledge:read"],
  "allowed_models": ["gpt-4", "claude-3"]
}
```

**成功响应 (200):**

```json
{
  "id": 5,
  "api_key": "sk_NewKey1234567890abcdefghij",
  "api_secret": "NewSecret987654321zyxwvutsrqpon",
  "key_prefix": "sk_NewKey12",
  "expires_at": "2027-03-24T00:00:00",
  "message": "API Key 创建成功，请妥善保存"
}
```

### 4. 轮换 API Key

**请求:**

```bash
POST /api/v1/applications/keys/5/rotate
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "id": 5,
  "api_key": "sk_RotatedKey098765432abcdefgh",
  "api_secret": "RotatedSecret123456789zyxwvut",
  "key_prefix": "sk_Rotated",
  "message": "API Key 轮换成功，旧 Key 已失效"
}
```

### 5. 吊销 API Key

**请求:**

```bash
POST /api/v1/applications/keys/5/revoke
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "message": "API Key 已吊销"
}
```

---

## 模型管理 API

### 1. 创建模型

**请求:**

```bash
POST /api/v1/models
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "name": "GPT-4",
  "provider": "openai",
  "model_type": "llm",
  "config": {
    "base_url": "https://api.openai.com/v1",
    "max_tokens": 8192,
    "temperature": 0.7
  },
  "api_key": "sk-openai-xxx"
}
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "GPT-4",
    "provider": "openai",
    "model_type": "llm",
    "is_active": true,
    "created_at": "2026-03-24T10:00:00"
  }
}
```

### 2. 获取模型列表

**请求:**

```bash
GET /api/v1/models?model_type=llm&is_active=true
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "GPT-4",
      "provider": "openai",
      "model_type": "llm",
      "is_active": true
    },
    {
      "id": 2,
      "name": "Claude-3-Opus",
      "provider": "anthropic",
      "model_type": "llm",
      "is_active": true
    },
    {
      "id": 3,
      "name": "Qwen-72B",
      "provider": "aliyun",
      "model_type": "llm",
      "is_active": true
    }
  ],
  "total": 3
}
```

### 3. 更新模型

**请求:**

```bash
PUT /api/v1/models/1
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "name": "GPT-4-Turbo",
  "is_active": true,
  "config": {
    "max_tokens": 128000
  }
}
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "GPT-4-Turbo",
    "provider": "openai",
    "model_type": "llm",
    "is_active": true
  }
}
```

---

## 知识管理 API

### 1. 创建知识库

**请求:**

```bash
POST /api/v1/knowledge
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "name": "产品知识库",
  "description": "公司产品相关文档"
}
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "产品知识库",
    "description": "公司产品相关文档",
    "document_count": 0,
    "created_at": "2026-03-24T10:00:00"
  }
}
```

### 2. 上传文档

**请求:**

```bash
POST /api/v1/knowledge/1/documents
Authorization: Bearer $TOKEN
Content-Type: multipart/form-data

file: [二进制文件]
name: "产品手册.pdf"
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "document_id": 1,
    "name": "产品手册.pdf",
    "status": "processing",
    "message": "文档上传成功，正在解析中"
  }
}
```

### 3. 向量检索

**请求:**

```bash
POST /api/v1/knowledge/1/search
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "query": "产品保修政策",
  "top_k": 5,
  "score_threshold": 0.7
}
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "query": "产品保修政策",
    "results": [
      {
        "content": "本产品提供一年质保服务...",
        "score": 0.92,
        "metadata": {
          "source": "产品手册.pdf",
          "page": 15
        }
      },
      {
        "content": "保修范围包括硬件故障...",
        "score": 0.85,
        "metadata": {
          "source": "售后服务.docx",
          "section": "保修条款"
        }
      }
    ]
  }
}
```

---

## 智能体工厂 API

### 1. 创建智能体

**请求:**

```bash
POST /api/v1/agents
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "name": "数据分析助手",
  "description": "用于数据分析的智能体",
  "role": "executor",
  "model_id": 1,
  "config": {
    "temperature": 0.7,
    "max_steps": 10
  },
  "tools": [
    {
      "name": "code_interpreter",
      "config": {}
    },
    {
      "name": "search",
      "config": {
        "engine": "bing"
      }
    }
  ]
}
```

**验证规则:**
- `name`: 1-100 字符，只能包含中文、英文、数字、下划线和连字符
- `description`: 最多 500 字符
- `role`: 必须是 planner | executor | reviewer | summarizer | custom

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "数据分析助手",
    "description": "用于数据分析的智能体",
    "role": "executor",
    "model_id": 1,
    "config": {
      "temperature": 0.7,
      "max_steps": 10
    },
    "tools": [
      {"name": "code_interpreter"},
      {"name": "search"}
    ],
    "created_at": "2026-03-24T10:00:00"
  }
}
```

**错误响应 (422):**

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数格式错误",
  "detail": "参数验证失败，请检查请求数据",
  "data": {
    "errors": [
      {
        "field": "name",
        "message": "String should have at most 100 characters",
        "type": "string_too_long"
      }
    ]
  }
}
```

### 2. 执行智能体任务

**请求:**

```bash
POST /api/v1/agents/1/execute
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "task": "分析 2024 年销售数据，找出增长最快的产品类别",
  "session_id": "session_20240324_001",
  "stream": false,
  "max_steps": 20
}
```

**验证规则:**
- `task`: 1-5000 字符
- `session_id`: 可选
- `stream`: 布尔值，默认 false
- `max_steps`: 1-50，默认 10

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "content": "根据分析，2024 年销售增长最快的产品类别是：\n\n1. **智能穿戴设备**: 同比增长 156%\n2. **智能家居产品**: 同比增长 89%\n3. **新能源汽车配件**: 同比增长 67%\n\n主要增长驱动因素：\n- 消费者健康意识提升\n-  IoT 技术普及\n- 政策支持",
    "status": "success",
    "metadata": {
      "steps_used": 8,
      "tools_called": ["search", "code_interpreter"],
      "execution_time_ms": 3500
    }
  }
}
```

**错误响应 (404):**

```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "智能体不存在",
  "detail": "智能体 ID 999 不存在",
  "data": null
}
```

### 3. 获取智能体列表

**请求:**

```bash
GET /api/v1/agents?skip=0&limit=20&is_active=true
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "数据分析助手",
      "description": "用于数据分析的智能体",
      "role": "executor",
      "model_id": 1,
      "tools": ["code_interpreter", "search"],
      "created_at": "2026-03-24T10:00:00"
    },
    {
      "id": 2,
      "name": "客服机器人",
      "description": "7x24 小时在线客服",
      "role": "executor",
      "model_id": 2,
      "tools": ["knowledge_search"],
      "created_at": "2026-03-23T15:30:00"
    }
  ],
  "total": 2
}
```

---

## MCP 连接器 API

### 1. 创建连接器

**请求:**

```bash
POST /api/v1/mcp/connectors
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "name": "MySQL 生产数据库",
  "connector_type": "mysql",
  "host": "192.168.1.100",
  "port": 3306,
  "username": "ai_user",
  "password": "secure_password",
  "config": {
    "database": "production",
    "charset": "utf8mb4"
  }
}
```

**验证规则:**
- `name`: 1-200 字符
- `connector_type`: mysql | postgresql | http | redis | file | kafka | mongodb
- `host`: 指定类型时必须
- `port`: 1-65535，指定 host 时必须

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "MySQL 生产数据库",
    "connector_type": "mysql",
    "status": "active",
    "created_at": "2026-03-24T10:00:00"
  }
}
```

### 2. 执行连接器操作

**请求:**

```bash
POST /api/v1/mcp/connectors/1/execute
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "action": "query",
  "params": {
    "sql": "SELECT * FROM users WHERE created_at > '2024-01-01'"
  }
}
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "rows": [
      {"id": 1, "name": "张三", "email": "zs@example.com"},
      {"id": 2, "name": "李四", "email": "ls@example.com"}
    ],
    "row_count": 2,
    "execution_time_ms": 45
  }
}
```

**错误响应 (500):**

```json
{
  "code": "MCP_EXECUTION_FAILED",
  "message": "连接器执行失败",
  "detail": "SQL 语法错误：SELECT * FORM...",
  "data": null
}
```

### 3. 获取连接器类型

**请求:**

```bash
GET /api/v1/mcp/types
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": [
    {
      "type": "mysql",
      "name": "MySQL 数据库",
      "description": "MySQL 数据库连接器",
      "actions": ["query", "execute", "get_tables", "describe_table"],
      "config_schema": {
        "host": "string",
        "port": "integer",
        "username": "string",
        "password": "string",
        "database": "string"
      }
    },
    {
      "type": "http",
      "name": "HTTP 连接器",
      "description": "RESTful API 调用连接器",
      "actions": ["get", "post", "put", "delete"],
      "config_schema": {
        "base_url": "string",
        "headers": "object",
        "auth_type": "string"
      }
    }
  ]
}
```

---

## Skills 市场 API

### 1. 获取已注册 Skills

**请求:**

```bash
GET /api/v1/skills/skills/registry
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": [
    {
      "id": "data_analysis",
      "name": "数据分析",
      "description": "数据统计、分组、聚合、过滤",
      "version": "1.0.0",
      "category": "数据处理",
      "author": "AI 中台团队",
      "operations": ["statistic", "group_by", "aggregate", "filter"]
    },
    {
      "id": "report_generator",
      "name": "报告生成",
      "description": "Markdown/JSON/HTML报告生成",
      "version": "1.0.0",
      "category": "文档处理",
      "author": "AI 中台团队",
      "operations": ["generate_markdown", "generate_json", "generate_html"]
    },
    {
      "id": "notification",
      "name": "通知发送",
      "description": "日志/Webhook/Email 通知",
      "version": "1.0.0",
      "category": "消息通知",
      "author": "AI 中台团队",
      "operations": ["send_log", "send_webhook", "send_email"]
    }
  ]
}
```

### 2. 执行 Skill

**请求:**

```bash
POST /api/v1/skills/skills/data_analysis/execute
Authorization: Bearer $TOKEN
Content-Type: application/json

{
  "data": [
    {"name": "张三", "age": 25, "department": "技术部", "salary": 15000},
    {"name": "李四", "age": 30, "department": "技术部", "salary": 20000},
    {"name": "王五", "age": 28, "department": "销售部", "salary": 18000}
  ],
  "operation": "aggregate",
  "config": {
    "group_by": "department",
    "aggregations": [
      {"field": "salary", "function": "avg"},
      {"field": "age", "function": "avg"}
    ]
  }
}
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "operation": "aggregate",
    "result": [
      {
        "department": "技术部",
        "avg_salary": 17500,
        "avg_age": 27.5
      },
      {
        "department": "销售部",
        "avg_salary": 18000,
        "avg_age": 28
      }
    ]
  }
}
```

---

## 运营监控 API

### 1. 获取监控指标概览

**请求:**

```bash
GET /api/v1/monitor/metrics/overview
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "api_calls": {
      "total": 150000,
      "today": 12500,
      "success_rate": 99.8
    },
    "model_usage": {
      "total_tokens": 5000000,
      "today_tokens": 450000
    },
    "agent_executions": {
      "total": 3500,
      "success_rate": 98.5
    },
    "knowledge_base": {
      "total_documents": 1250,
      "total_vectors": 125000
    }
  }
}
```

### 2. 获取服务健康状态

**请求:**

```bash
GET /api/v1/monitor/health/services
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": {
    "services": [
      {
        "name": "database",
        "status": "healthy",
        "response_time_ms": 12,
        "last_check": "2026-03-24T10:30:00"
      },
      {
        "name": "redis",
        "status": "healthy",
        "response_time_ms": 2,
        "last_check": "2026-03-24T10:30:00"
      },
      {
        "name": "embedding",
        "status": "healthy",
        "response_time_ms": 85,
        "last_check": "2026-03-24T10:30:00"
      },
      {
        "name": "llm",
        "status": "healthy",
        "response_time_ms": 1200,
        "last_check": "2026-03-24T10:30:00"
      }
    ],
    "overall_status": "healthy"
  }
}
```

### 3. 获取告警规则列表

**请求:**

```bash
GET /api/v1/monitor/alerts/rules
Authorization: Bearer $TOKEN
```

**成功响应 (200):**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "API 错误率过高",
      "metric_name": "api_error_rate",
      "threshold": 5.0,
      "condition": "gt",
      "notification_channels": ["webhook", "email"],
      "is_active": true
    },
    {
      "id": 2,
      "name": "LLM 响应时间过长",
      "metric_name": "llm_latency",
      "threshold": 5000,
      "condition": "gt",
      "notification_channels": ["webhook"],
      "is_active": true
    }
  ]
}
```

---

## 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "code": "ERROR_CODE",
  "message": "错误消息",
  "detail": "详细错误信息（可选）",
  "data": null
}
```

### 常见错误代码

| 错误代码 | HTTP 状态码 | 说明 |
|---------|------------|------|
| `VALIDATION_ERROR` | 400/422 | 验证错误 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `FORBIDDEN` | 403 | 禁止访问 |
| `NOT_FOUND` | 404 | 资源未找到 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `TOO_MANY_REQUESTS` | 429 | 请求过多 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

### 错误响应示例

**422 参数验证错误:**

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数格式错误",
  "detail": "参数验证失败，请检查请求数据",
  "data": {
    "errors": [
      {
        "field": "name",
        "message": "field required",
        "type": "missing"
      },
      {
        "field": "email",
        "message": "value is not a valid email address",
        "type": "value_error"
      }
    ]
  }
}
```

**401 未授权:**

```json
{
  "code": "UNAUTHORIZED",
  "message": "未授权，请先登录",
  "detail": "Token 已过期",
  "data": null
}
```

**404 资源未找到:**

```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "智能体不存在",
  "detail": "智能体 ID 123 不存在",
  "data": null
}
```
