# 输入验证实现文档

## 概述

本文档说明 AI 中台系统的输入验证实现和使用方法。

## 实现原理

### 1. Pydantic V2 验证

项目使用 Pydantic V2 进行输入验证，提供以下特性：

- **类型检查**: 自动类型转换和验证
- **字段验证**: min_length, max_length, regex, ge, le 等
- **自定义验证器**: field_validator, model_validator
- **嵌套模型**: 支持复杂的嵌套数据结构

### 2. 验证层次

```
┌─────────────────────────────────────────────────────────────┐
│                    输入验证层次                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: HTTP 层                                           │
│  - Content-Type 检查                                        │
│  - 请求大小限制                                             │
│                                                             │
│  Layer 2: FastAPI 层                                        │
│  - Pydantic 模型验证                                        │
│  - 路径参数验证                                             │
│  - 查询参数验证                                             │
│                                                             │
│  Layer 3: 业务逻辑层                                        │
│  - 业务规则验证                                             │
│  - 权限检查                                                 │
│  - 状态检查                                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 文件结构

```
backend/app/
└── schemas/
    └── __init__.py    # 所有 Pydantic schemas（新增）
```

## 验证器类型

### 1. 字段验证器 (Field Validator)

```python
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="邮箱地址")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("用户名只能包含英文、数字和下划线")
        return v
```

### 2. 模型验证器 (Model Validator)

```python
from pydantic import model_validator

class MCPConnectorCreate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None

    @model_validator(mode='after')
    def validate_connection(self):
        if self.host and not self.port:
            raise ValueError("指定主机地址时必须指定端口")
        return self
```

### 3. 通用验证函数

```python
from app.schemas import validate_name, validate_description

class AgentCreate(BaseModel):
    name: str = Field(..., description="智能体名称")
    description: Optional[str] = Field(None, description="描述")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)  # 验证名称格式
```

## Schemas 分类

### 用户相关

| Schema | 说明 | 验证规则 |
|--------|------|----------|
| `UserCreate` | 用户创建 | 用户名 3-50 字符，密码 8+ 字符含大小写和数字 |
| `UserUpdate` | 用户更新 | 邮箱格式验证 |
| `UserResponse` | 用户响应 | - |

### 应用相关

| Schema | 说明 | 验证规则 |
|--------|------|----------|
| `ApplicationCreate` | 应用创建 | 名称 1-200 字符，类型限制 |
| `ApplicationUpdate` | 应用更新 | 可选字段验证 |
| `APIKeyCreate` | API Key 创建 | 过期天数 1-3650 |

### 模型相关

| Schema | 说明 | 验证规则 |
|--------|------|----------|
| `ModelCreate` | 模型创建 | 名称 1-100 字符，类型限制 |
| `ModelUpdate` | 模型更新 | 可选字段验证 |

### 智能体相关

| Schema | 说明 | 验证规则 |
|--------|------|----------|
| `AgentCreate` | 智能体创建 | 名称 1-100 字符，角色限制 |
| `AgentUpdate` | 智能体更新 | 可选字段验证 |
| `AgentExecuteRequest` | 执行请求 | 任务 1-5000 字符，max_steps 1-50 |

### 推理相关

| Schema | 说明 | 验证规则 |
|--------|------|----------|
| `ChatCompletionRequest` | 聊天请求 | messages 非空，temperature 0-2 |
| `InferenceRequest` | 推理请求 | prompt 1-50000 字符 |

## 使用示例

### 1. 创建智能体

**请求:**

```bash
curl -X POST "http://localhost:8000/api/v1/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "数据分析助手",
    "description": "用于数据分析的智能体",
    "role": "executor",
    "model_id": 1,
    "config": {"temperature": 0.7},
    "tools": []
  }'
```

**验证规则:**
- `name`: 1-100 字符，只能包含中文、英文、数字、下划线和连字符
- `description`: 最多 500 字符
- `role`: 必须是 planner | executor | reviewer | summarizer | custom

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
curl -X POST "http://localhost:8000/api/v1/agents/1/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "分析销售数据",
    "session_id": "session_123",
    "stream": false,
    "max_steps": 20
  }'
```

**验证规则:**
- `task`: 1-5000 字符
- `session_id`: 可选
- `stream`: 布尔值，默认 false
- `max_steps`: 1-50，默认 10

### 3. 创建用户

**请求:**

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "password": "SecurePass123"
  }'
```

**验证规则:**
- `username`: 3-50 字符，只能包含英文、数字和下划线
- `email`: 有效的邮箱格式
- `password`: 8+ 字符，必须包含大写字母、小写字母和数字

## 最佳实践

### 1. 使用 Schema 类

```python
# 推荐：使用 Schema 类
from app.schemas import AgentCreate

@router.post("/agents")
async def create_agent(agent_data: AgentCreate, ...):
    # agent_data 已经过验证
    pass

# 不推荐：使用 Body 参数
@router.post("/agents")
async def create_agent(
    name: str = Body(...),
    description: str = Body(None),
    ...
):
    # 需要手动验证每个字段
    pass
```

### 2. 提供详细的错误消息

```python
@field_validator('password')
@classmethod
def validate_password(cls, v):
    if len(v) < 8:
        raise ValueError("密码长度不能少于 8 个字符")
    if not re.search(r'[A-Z]', v):
        raise ValueError("密码必须包含至少一个大写字母")
    if not re.search(r'\d', v):
        raise ValueError("密码必须包含至少一个数字")
    return v
```

### 3. 使用可选字段

```python
class UserUpdate(BaseModel):
    """用户更新 - 所有字段可选"""
    email: Optional[str] = None
    full_name: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:  # 处理 None 值
            return v
        # ... 验证逻辑
```

### 4. 复用验证逻辑

```python
# 通用验证函数
def validate_name(value: str) -> str:
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_-]+$', value):
        raise ValueError("名称只能包含中文、英文、数字、下划线和连字符")
    return validate_string_length(value, min_len=1, max_len=100)

# 在多个 Schema 中复用
class AgentCreate(BaseModel):
    name: str = Field(..., description="智能体名称")
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)

class ApplicationCreate(BaseModel):
    name: str = Field(..., description="应用名称")
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)
```

## 错误处理

### 1. 验证错误格式

所有验证错误遵循统一格式：

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数格式错误",
  "detail": "参数验证失败，请检查请求数据",
  "data": {
    "errors": [
      {
        "field": "field.path",
        "message": "错误消息",
        "type": "错误类型"
      }
    ]
  }
}
```

### 2. 自定义错误消息

```python
from app.core.exceptions import ValidationError

# 抛出自定义验证错误
if not is_valid:
    raise ValidationError(
        detail="字段验证失败",
        data={"field": "name", "reason": "名称已存在"}
    )
```

## 性能考虑

### 1. 验证开销

- Pydantic V2 使用 Rust 内核 (pydantic-core)，性能优秀
- 复杂嵌套模型验证通常在 1ms 以内
- 正则表达式验证可能较慢，避免过于复杂的模式

### 2. 验证缓存

```python
# Schema 类在模块加载时编译，无需额外缓存
from app.schemas import AgentCreate  # 编译一次，重复使用
```

## API 文档集成

Schemas 自动集成到 Swagger/OpenAPI 文档中：

- 请求参数说明
- 参数类型和格式
- 必填/可选标记
- 示例值

访问 `/docs` 查看完整的 API 文档。
