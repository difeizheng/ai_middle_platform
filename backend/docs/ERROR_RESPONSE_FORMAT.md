# 统一错误响应格式

本文档说明 AI 中台系统的统一错误响应格式和使用方法。

## 错误响应格式

所有 API 错误响应遵循统一格式：

```json
{
  "code": "ERROR_CODE",
  "message": "错误消息",
  "detail": "详细错误信息（可选）",
  "data": null
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 错误代码，用于程序化判断 |
| `message` | string | 错误消息，用于用户展示 |
| `detail` | string | 详细错误信息，用于调试 |
| `data` | object | 附加数据（可选） |

## 错误代码分类

### 通用错误 (1000-1999)

| 错误代码 | HTTP 状态码 | 说明 |
|---------|------------|------|
| `SUCCESS` | 200 | 成功 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `VALIDATION_ERROR` | 400/422 | 验证错误 |
| `NOT_FOUND` | 404 | 资源未找到 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `FORBIDDEN` | 403 | 禁止访问 |
| `CONFLICT` | 409 | 资源冲突 |
| `TOO_MANY_REQUESTS` | 429 | 请求过多 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

### 认证相关 (2000-2999)

| 错误代码 | 说明 |
|---------|------|
| `INVALID_CREDENTIALS` | 凭证无效 |
| `TOKEN_EXPIRED` | Token 过期 |
| `TOKEN_INVALID` | Token 无效 |
| `API_KEY_INVALID` | API Key 无效 |
| `API_KEY_INACTIVE` | API Key 未激活 |

### 资源相关 (3000-3999)

| 错误代码 | 说明 |
|---------|------|
| `RESOURCE_NOT_FOUND` | 资源不存在 |
| `RESOURCE_ALREADY_EXISTS` | 资源已存在 |
| `RESOURCE_CONFLICT` | 资源冲突 |

### 业务相关 (4000-4999)

| 错误代码 | 说明 |
|---------|------|
| `INVALID_OPERATION` | 无效操作 |
| `INVALID_STATE` | 无效状态 |
| `DEPENDENCY_ERROR` | 依赖错误 |
| `TIMEOUT_ERROR` | 超时错误 |

### 模块错误代码

| 错误代码前缀 | 模块 |
|------------|------|
| `MCP_*` (5000-5999) | MCP 连接器 |
| `SKILL_*` (6000-6999) | Skills 市场 |
| `AGENT_*` (7000-7999) | 智能体工厂 |
| `KNOWLEDGE_*` (8000-8999) | 知识工厂 |
| `MODEL_*` (9000-9999) | 模型工厂 |

## 使用方法

### 1. 导入异常类

```python
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    TooManyRequestsError,
    ServiceUnavailableError,
)
```

### 2. 抛出异常

```python
# 验证错误
raise ValidationError(detail="字段 'name' 是必填的")

# 资源未找到
raise NotFoundError(resource="用户", detail=f"用户 ID {user_id} 不存在")

# 未授权
raise UnauthorizedError(message="Token 已过期", detail="请重新登录")

# 禁止访问
raise ForbiddenError(message="无权访问该资源")

# 资源冲突
raise ConflictError(message="用户名已存在")

# 请求过多
raise TooManyRequestsError(detail="请稍后重试")

# 服务不可用
raise ServiceUnavailableError(message="系统维护中")
```

### 3. 自定义 AppException

```python
from app.core.exceptions import AppException, status

class CustomError(AppException):
    def __init__(self, detail: str = None):
        super().__init__(
            code="CUSTOM_ERROR",
            message="自定义错误消息",
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

# 使用
raise CustomError(detail="具体原因")
```

## 示例

### 成功响应

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "示例"
  }
}
```

### 错误响应

#### 401 未授权

```json
{
  "code": "UNAUTHORIZED",
  "message": "未授权，请先登录",
  "detail": "Token 已过期",
  "data": null
}
```

#### 404 资源未找到

```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "用户不存在",
  "detail": "用户 ID 123 不存在",
  "data": null
}
```

#### 422 参数验证错误

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数格式错误",
  "detail": "参数验证失败，请检查请求数据",
  "data": {
    "errors": [
      {
        "field": "body.name",
        "message": "field required",
        "type": "missing"
      }
    ]
  }
}
```

#### 500 服务器内部错误

```json
{
  "code": "INTERNAL_ERROR",
  "message": "服务器内部错误，请稍后重试",
  "detail": "具体错误信息...",
  "data": null
}
```

## 迁移指南

### 从 HTTPException 迁移

**之前:**

```python
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="用户不存在"
)
```

**现在:**

```python
from app.core.exceptions import NotFoundError

raise NotFoundError(resource="用户", detail=f"用户 ID {user_id} 不存在")
```

### 优势

1. **统一格式**: 所有错误响应格式一致
2. **类型安全**: 使用预定义的异常类
3. **易于维护**: 集中管理错误代码
4. **更好的文档**: Swagger 自动生成错误响应示例

## 异常处理器注册

异常处理器已在 `main.py` 中自动注册：

```python
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
```

## 响应头

错误响应会包含以下响应头：

- `X-Error-Code`: 错误代码（与 body 中的 code 一致）
- `X-Request-ID`: 请求 ID（用于日志追踪）
