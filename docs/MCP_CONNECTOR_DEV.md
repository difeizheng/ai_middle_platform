# MCP 连接器开发文档

> Phase 2.2 - MCP 连接器开发
> 日期：2026 年 3 月 24 日

---

## 一、开发概览

### 1.1 完成模块

| 模块 | 文件 | 状态 |
|------|------|------|
| 连接器基类 | `services/mcp/base.py` | 完成 |
| 连接器注册表 | `services/mcp/registry.py` | 完成 |
| MySQL 连接器 | `services/mcp/mysql.py` | 完成 |
| PostgreSQL 连接器 | `services/mcp/postgresql.py` | 完成 |
| HTTP 连接器 | `services/mcp/http.py` | 完成 |
| Redis 连接器 | `services/mcp/redis.py` | 完成 |
| 文件连接器 | `services/mcp/file.py` | 完成 |
| Kafka 连接器 | `services/mcp/kafka.py` | 完成 |
| MongoDB 连接器 | `services/mcp/mongodb.py` | 完成 |
| 加密服务 | `services/encryption.py` | 完成 |
| API 路由 | `api/mcp.py` | 完成 |
| 数据库迁移 | `deploy/migrations/mcp_connectors.sql` | 完成 |

### 1.2 核心功能

#### 连接器基类
- 统一接口定义
- 配置管理
- 状态管理
- 操作定义（JSON Schema）

#### 连接器注册表
- 连接器类型注册
- 连接器实例管理
- 批量操作（连接、断开、健康检查）

#### 内置连接器（7 个）
- **MySQL**: 数据库查询、表结构获取
- **PostgreSQL**: 数据库查询、schema 管理
- **HTTP**: REST API 调用
- **Redis**: 缓存操作
- **File**: 文件读写、目录管理
- **Kafka**: 消息队列生产/消费
- **MongoDB**: 文档数据库操作

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP 连接器 API                            │
├─────────────────────────────────────────────────────────────┤
│  /api/v1/mcp/types              # 连接器类型                │
│  /api/v1/mcp/connectors         # 连接器实例管理            │
│  /api/v1/mcp/connectors/{id}/execute  # 执行操作           │
├─────────────────────────────────────────────────────────────┤
│  ConnectorRegistry  # 连接器注册表                          │
│  ├─ MySQL Connector                                           │
│  ├─ PostgreSQL Connector                                      │
│  ├─ HTTP Connector                                            │
│  ├─ Redis Connector                                           │
│  ├─ File Connector                                            │
│  ├─ Kafka Connector                                           │
│  └─ MongoDB Connector                                         │
├─────────────────────────────────────────────────────────────┤
│  MCPConnector (Base Class)                                │
│  ├─ connect()                                                 │
│  ├─ disconnect()                                              │
│  ├─ execute()                                                 │
│  └─ health_check()                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 MCP 协议

MCP (Model Context Protocol) 连接器协议定义：

```python
class MCPConnector(ABC):
    """MCP 连接器基类"""

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict) -> Any:
        """执行操作"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
```

---

## 三、API 接口

### 3.1 连接器类型管理

```
GET /api/v1/mcp/types          # 获取支持的连接器类型
```

### 3.2 连接器实例管理

```
GET    /api/v1/mcp/connectors            # 获取所有连接器
POST   /api/v1/mcp/connectors            # 创建连接器
GET    /api/v1/mcp/connectors/{id}       # 获取连接器详情
DELETE /api/v1/mcp/connectors/{id}       # 删除连接器
```

### 3.3 连接器操作

```
POST /api/v1/mcp/connectors/{id}/connect     # 连接
POST /api/v1/mcp/connectors/{id}/disconnect  # 断开
POST /api/v1/mcp/connectors/{id}/health      # 健康检查
POST /api/v1/mcp/connectors/{id}/execute     # 执行操作
GET  /api/v1/mcp/connectors/{id}/actions     # 支持的操作列表
```

### 3.4 批量操作

```
POST /api/v1/mcp/connectors/connect-all      # 连接所有
POST /api/v1/mcp/connectors/disconnect-all   # 断开所有
GET  /api/v1/mcp/connectors/health-all       # 健康检查所有
GET  /api/v1/mcp/stats                       # 统计信息
```

---

## 四、使用示例

### 4.1 创建 MySQL 连接器

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/v1/mcp/connectors",
    json={
        "name": "生产 MySQL",
        "connector_type": "mysql",
        "host": "db.example.com",
        "port": 3306,
        "username": "app_user",
        "password": "secret_password",
        "database": "production_db",
    }
)

instance_id = response.json()["data"]["instance_id"]
```

### 4.2 连接并执行查询

```python
# 连接
httpx.post(f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/connect")

# 执行查询
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "query",
        "params": {
            "sql": "SELECT * FROM users WHERE id = ?",
            "params": [123]
        }
    }
)

results = response.json()["data"]
```

### 4.3 使用 Redis 连接器

```python
# 创建 Redis 连接器
response = httpx.post(
    "http://localhost:8000/api/v1/mcp/connectors",
    json={
        "name": "缓存 Redis",
        "connector_type": "redis",
        "host": "redis.example.com",
        "port": 6379,
    }
)

instance_id = response.json()["data"]["instance_id"]

# 设置键值
httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "set",
        "params": {
            "key": "user:123",
            "value": {"name": "张三", "email": "zhangsan@example.com"},
            "expire": 3600  # 1 小时过期
        }
    }
)

# 获取键值
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "get",
        "params": {"key": "user:123"}
    }
)

value = response.json()["data"]
```

### 4.4 使用 HTTP 连接器

```python
# 创建 HTTP 连接器
response = httpx.post(
    "http://localhost:8000/api/v1/mcp/connectors",
    json={
        "name": "天气 API",
        "connector_type": "http",
        "host": "api.weather.com",
        "port": 443,
    }
)

instance_id = response.json()["data"]["instance_id"]

# 发送 GET 请求
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "get",
        "params": {
            "url": "https://api.weather.com/v1/current",
            "params": {"location": "beijing"}
        }
    }
)

weather = response.json()["data"]
```

### 4.5 使用文件连接器

```python
# 创建文件连接器
response = httpx.post(
    "http://localhost:8000/api/v1/mcp/connectors",
    json={
        "name": "数据文件",
        "connector_type": "file",
        "extra": {"base_path": "/data"}
    }
)

instance_id = response.json()["data"]["instance_id"]

# 写入文件
httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "write",
        "params": {
            "path": "output/result.txt",
            "content": "Hello, World!"
        }
    }
)

# 读取文件
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "read",
        "params": {"path": "output/result.txt"}
    }
)

content = response.json()["data"]
```

### 4.6 使用 MongoDB 连接器

```python
# 创建 MongoDB 连接器
response = httpx.post(
    "http://localhost:8000/api/v1/mcp/connectors",
    json={
        "name": "文档数据库",
        "connector_type": "mongodb",
        "host": "localhost",
        "port": 27017,
        "database": "mydb"
    }
)

instance_id = response.json()["data"]["instance_id"]

# 插入文档
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "insert_one",
        "params": {
            "collection": "users",
            "document": {"name": "张三", "email": "zhangsan@example.com"}
        }
    }
)

# 查询文档
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "find",
        "params": {
            "collection": "users",
            "filter": {"name": "张三"}
        }
    }
)

user = response.json()["data"]
```

### 4.7 使用 Kafka 连接器

```python
# 创建 Kafka 连接器
response = httpx.post(
    "http://localhost:8000/api/v1/mcp/connectors",
    json={
        "name": "消息队列",
        "connector_type": "kafka",
        "host": "localhost",
        "port": 9092
    }
)

instance_id = response.json()["data"]["instance_id"]

# 发送消息
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "produce",
        "params": {
            "topic": "my-topic",
            "message": "Hello, Kafka!",
            "key": "user-123"
        }
    }
)

# 消费消息
response = httpx.post(
    f"http://localhost:8000/api/v1/mcp/connectors/{instance_id}/execute",
    json={
        "action": "consume",
        "params": {
            "topic": "my-topic",
            "timeout": 5000,
            "max_messages": 10
        }
    }
)

messages = response.json()["data"]
```

---

## 五、扩展开发

### 5.1 添加自定义连接器

```python
from app.services.mcp.base import MCPConnector, ConnectorConfig, ConnectorStatus
from app.services.mcp.registry import get_registry

class KafkaConnector(MCPConnector):
    """Kafka 消息队列连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._consumer = None
        self._producer = None

    async def connect(self) -> bool:
        """建立 Kafka 连接"""
        # 实现连接逻辑
        self.status = ConnectorStatus.ACTIVE
        return True

    async def disconnect(self) -> bool:
        """断开连接"""
        self.status = ConnectorStatus.INACTIVE
        return True

    async def execute(self, action: str, params: Dict) -> Any:
        """执行操作"""
        if action == "produce":
            return await self._produce(params)
        elif action == "consume":
            return await self._consume(params)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def health_check(self) -> bool:
        """健康检查"""
        return self.status == ConnectorStatus.ACTIVE

# 注册连接器
registry = get_registry()
registry.register_type("kafka", KafkaConnector)
```

### 5.2 定义操作 Schema

```python
from app.services.mcp.base import ActionDefinition

def _register_actions(self) -> List[ActionDefinition]:
    return [
        ActionDefinition(
            name="produce",
            description="发送消息到 Kafka",
            params_schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "message": {"type": "string"},
                    "key": {"type": "string"},
                },
                "required": ["topic", "message"],
            },
            response_schema={
                "type": "object",
                "properties": {
                    "offset": {"type": "integer"},
                    "partition": {"type": "integer"},
                },
            },
        ),
    ]
```

---

## 六、数据库表结构

### 6.1 mcp_connectors 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| name | VARCHAR(200) | 连接器名称（唯一） |
| connector_type | VARCHAR(50) | 连接器类型 |
| host | VARCHAR(500) | 主机地址 |
| port | INTEGER | 端口 |
| username | VARCHAR(200) | 用户名 |
| password | VARCHAR(500) | 密码（加密） |
| database | VARCHAR(200) | 数据库名 |
| config_json | JSONB | 额外配置 |
| status | VARCHAR(50) | 状态 |
| health_check_interval | INTEGER | 健康检查间隔 |

### 6.2 mcp_connector_logs 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| connector_id | INTEGER | 连接器 ID |
| action | VARCHAR(100) | 操作名称 |
| params | JSONB | 操作参数 |
| result | JSONB | 操作结果 |
| error_message | TEXT | 错误信息 |
| duration_ms | INTEGER | 执行时长 |

---

## 七、安全考虑

### 7.1 密码加密

连接器密码应使用加密存储：

```python
from cryptography.fernet import Fernet

# 加密
def encrypt_password(password: str, key: bytes) -> str:
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

# 解密
def decrypt_password(encrypted: str, key: bytes) -> str:
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

### 7.2 路径安全（文件连接器）

文件连接器实现了路径沙箱：

```python
def _resolve_path(self, path: str) -> Path:
    """解析路径（防止目录遍历攻击）"""
    file_path = Path(path)
    full_path = (self.base_path / file_path).resolve()

    # 确保路径在 base_path 内
    full_path.relative_to(self.base_path.resolve())
    return full_path
```

---

## 八、下一步计划

### Phase 2.2 收尾
- [x] 核心连接器开发（7 个）
- [x] API 路由开发
- [x] 单元测试编写
- [x] 密码加密服务
- [ ] 集成测试

### Phase 2.3 Skills 市场
- [ ] Skill 接口定义
- [ ] 内置 Skills（10+）
- [ ] 市场前端
- [ ] 开发者入驻

### 待扩展连接器
- [ ] Elasticsearch 连接器
- [ ] Oracle 连接器
- [ ] SQL Server 连接器

---

*MCP 连接器核心开发完成，进入 Skills 市场开发阶段*
