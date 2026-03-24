# API Key 加密存储实现文档

## 概述

本文档说明 API Key 的加密存储实现和使用方法。

## 实现原理

### 1. 双重保护机制

API Key 使用双重保护机制：

- **API Key**: 使用 SHA-256 哈希存储（用于快速查询和验证）
- **API Secret**: 使用 Fernet 加密存储（用于身份验证）

```
┌─────────────────────────────────────────────────────────────┐
│                    API Key 存储方案                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  用户生成：sk_xxxxxxxxxxxxxxxxxxxx                         │
│       │                                                     │
│       ├──→ SHA-256 哈希 ──→ 存储到 DB (key 字段)           │
│       │                                                     │
│       └──→ Secret 生成 ──→ Fernet 加密 ──→ 存储到 DB       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. 加密流程

```python
# 1. 生成 API Key 和 Secret
api_key, api_secret = generate_api_key()

# 2. 哈希 API Key（用于存储和查询）
hashed_key = hash_api_key(api_key)

# 3. 加密 API Secret（用于存储）
encrypted_secret = encryption_service.encrypt(api_secret)

# 4. 存储到数据库
db_api_key = APIKey(
    key=hashed_key,           # 哈希存储
    secret=encrypted_secret,   # 加密存储
    key_prefix=api_key[:12],   # 前缀用于显示
)
```

### 3. 验证流程

```python
# 1. 用户提供 API Key
user_api_key = "sk_xxx..."

# 2. 哈希后查询数据库
hashed_key = hash_api_key(user_api_key)
api_key_obj = db.query(APIKey).filter(APIKey.key == hashed_key).first()

# 3. 验证成功则返回（无需解密 Secret）
if api_key_obj and api_key_obj.is_active:
    return api_key_obj
```

## 文件结构

```
backend/app/
├── services/
│   ├── encryption.py         # 加密服务（Fernet）
│   ├── key_manager.py        # 密钥管理服务
│   └── api_key_manager.py    # API Key 管理服务（新增）
└── api/
    └── applications.py       # 应用管理 API（已更新）
```

## API 使用

### 创建应用（自动生成 API Key）

```bash
curl -X POST "http://localhost:8000/api/v1/applications" \
  -H "Authorization: Bearer $TOKEN" \
  -d "name=MyApp&description=测试应用"
```

响应：

```json
{
  "id": 1,
  "name": "MyApp",
  "api_key": "sk_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
  "api_secret": "xYz789AbCdEfGhIjKlMnOpQrStUvWxYz",
  "key_prefix": "sk_aBcDeFgH",
  "message": "应用创建成功，请妥善保存 API Key 和 Secret"
}
```

**注意**: `api_key` 和 `api_secret` 只在创建时返回一次，请妥善保存！

### 创建新的 API Key

```bash
curl -X POST "http://localhost:8000/api/v1/applications/1/keys" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"expires_days": 365}'
```

### 轮换 API Key

```bash
curl -X POST "http://localhost:8000/api/v1/applications/keys/1/rotate" \
  -H "Authorization: Bearer $TOKEN"
```

### 吊销 API Key

```bash
curl -X POST "http://localhost:8000/api/v1/applications/keys/1/revoke" \
  -H "Authorization: Bearer $TOKEN"
```

### 删除 API Key

```bash
curl -X DELETE "http://localhost:8000/api/v1/applications/keys/1" \
  -H "Authorization: Bearer $TOKEN"
```

## 安全特性

### 1. 加密算法

- **Fernet**: 基于 AES-128-CBC 的对称加密
- **SHA-256**: 密码学哈希函数

### 2. 密钥管理

- 加密密钥通过密钥管理器统一管理
- 支持密钥轮换
- 密钥存储文件权限设置为 0600（仅所有者可读写）

### 3. 访问控制

- API Key 验证包含：
  - 激活状态检查
  - 吊销状态检查
  - 过期时间检查
  - IP 白名单检查（可选）
  - 权限检查（可选）

## 数据库模型

```python
class APIKey(Base):
    id = Column(Integer, primary_key=True)
    app_id = Column(Integer, ForeignKey("applications.id"))

    # Key 信息（加密存储）
    key = Column(String(100), unique=True)  # SHA-256 哈希
    key_prefix = Column(String(10))  # 前缀用于显示
    secret = Column(String(255))  # Fernet 加密

    # 权限和限制
    permissions = Column(JSON)
    allowed_models = Column(JSON)
    allowed_ips = Column(JSON)

    # 状态
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime)

    # 统计
    total_calls = Column(Integer, default=0)
    last_used_at = Column(DateTime)
```

## 最佳实践

### 1. API Key 保存

- ✅ 创建后立即保存到安全位置
- ✅ 使用环境变量或密钥管理服务存储
- ❌ 不要提交到版本控制系统
- ❌ 不要硬编码到代码中

### 2. API Key 使用

- ✅ 通过请求头传递：`Authorization: Bearer sk_xxx`
- ✅ 定期轮换（建议每 90 天）
- ✅ 为不同环境使用不同的 Key
- ❌ 不要在 URL 中传递 API Key

### 3. API Key 泄漏处理

1. 立即吊销泄漏的 Key
2. 创建新的 API Key
3. 更新所有使用该 Key 的应用
4. 检查审计日志，确认是否有未授权访问

## 环境变量配置

```bash
# 加密密钥（32 字节 URL-safe base64 编码）
ENCRYPTION_KEY=your-32-byte-encryption-key-here

# 密钥存储文件路径
KEY_STORAGE_PATH=~/.ai_middle_platform/keys.json
```

## 代码示例

### Python SDK 使用示例

```python
import requests

API_KEY = "sk_xxx"
API_SECRET = "xxx"

headers = {
    "X-API-Key": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
}

# 调用模型 API
response = requests.post(
    "http://localhost:8000/api/v1/inference/chat",
    headers=headers,
    json={"messages": [{"role": "user", "content": "Hello"}]}
)

print(response.json())
```

### 验证 API Key

```python
from app.services.api_key_manager import verify_api_key

async def check_api_key(db: AsyncSession, api_key: str):
    """验证 API Key"""
    key_obj = await verify_api_key(db, api_key)

    if not key_obj:
        raise UnauthorizedError(message="无效的 API Key")

    return key_obj
```

## 审计日志

所有 API Key 操作都会记录审计日志：

- Key 创建时间
- Key 最后使用时间
- Key 轮换记录
- Key 吊销/删除记录

可以通过 `/api/v1/logs` 端点查询审计日志。
