# 架构设计文档

> AI 中台系统技术架构设计

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                           应用层                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 信贷系统 │ │ 风险系统 │ │ OA 办公   │ │ 客服系统 │ │ 自研应用 │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                           API 网关层                                 │
│         统一入口 / 认证鉴权 / 限流熔断 / 监控告警 / 计费统计          │
├─────────────────────────────────────────────────────────────────────┤
│                           AI 中台核心层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │  智能体工厂  │ │  模型工厂   │ │  知识工厂   │                   │
│  │  Agent      │ │  Model      │ │  Knowledge  │                   │
│  │  Studio     │ │  Studio     │ │  Studio     │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ Skills 市场  │ │ MCP 连接器   │ │  运营监控   │                   │
│  │  Marketplace│ │  Connector  │ │  Monitor    │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
├─────────────────────────────────────────────────────────────────────┤
│                           数据层                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ 向量库   │ │ 关系库   │ │ 对象存储 │ │ 缓存层   │              │
│  │ Milvus   │ │ MySQL/PG │ │   MinIO  │ │  Redis   │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、模块设计

### 2.1 模型工厂（Model Studio）

```
┌─────────────────────────────────────────────────────────────┐
│                    模型工厂                                  │
├─────────────────────────────────────────────────────────────┤
│  1. 模型接入层                                               │
│     • 适配器模式：统一接口封装不同模型                      │
│     • 支持：OpenAI/vLLM/DeepSeek/智谱等                     │
│                                                             │
│  2. 模型管理层                                               │
│     • 模型注册、配置、版本管理                               │
│     • 模型仓库、转换、量化                                   │
│                                                             │
│  3. 模型服务层                                               │
│     • 统一推理接口、智能路由、负载均衡                       │
│     • A/B 测试、灰度发布                                     │
│                                                             │
│  4. 模型优化层                                               │
│     • 微调训练、RLHF 对齐、持续学习                           │
│     • 效果监控、延迟优化                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 知识工厂（Knowledge Studio）

```
┌─────────────────────────────────────────────────────────────┐
│                    知识工厂                                  │
├─────────────────────────────────────────────────────────────┤
│  知识处理 Pipeline:                                          │
│  采集 → 清洗 → 分片 → 增强 → 向量化 → 入库                   │
│                                                             │
│  核心模块：                                                  │
│  • 文档解析：PDF/Word/Excel/PPT/TXT/Markdown                │
│  • 智能分片：按语义切分，非固定长度                          │
│  • 向量化：Embedding 模型生成向量                            │
│  • 混合检索：BM25 + Vector + Rerank                         │
│  • 知识管理：权限、版本、增量更新                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 API 网关

```
┌─────────────────────────────────────────────────────────────┐
│                    API 网关                                  │
├─────────────────────────────────────────────────────────────┤
│  请求处理链路：                                              │
│  Client → LB → 网关 → 认证 → 限流 → 路由 → 后端             │
│                                                             │
│  核心功能：                                                  │
│  • 认证鉴权：JWT/OAuth2、API Key                            │
│  • 限流熔断：Token Bucket、Circuit Breaker                  │
│  • 路由转发：负载均衡、故障转移                              │
│  • 协议转换：REST/gRPC/WebSocket                            │
│  • 监控统计：实时指标、调用追踪                              │
│  • 审计日志：全链路记录、可追溯                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、数据库设计

### 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型表
CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    model_type VARCHAR(20) NOT NULL,
    provider VARCHAR(50),
    base_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识库表
CREATE TABLE knowledge_bases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    collection_name VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 应用表
CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Key 表
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES applications(id),
    key VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 日志表
CREATE TABLE api_logs (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(64),
    request_id VARCHAR(64) UNIQUE,
    user_id INTEGER REFERENCES users(id),
    endpoint VARCHAR(200),
    latency_ms FLOAT,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 四、安全设计

### 四层防御体系

| 层级 | 措施 |
|------|------|
| **L1 物理安全** | 机房准入、监控、灾备 |
| **L2 网络安全** | 防火墙、WAF、DDoS 防护、零信任 |
| **L3 数据安全** | 传输加密、存储加密、敏感脱敏 |
| **L4 AI 安全** | Prompt 注入检测、输出审核、越狱防护 |

### 权限模型

- **RBAC**：基于角色的访问控制
- **ABAC**：基于属性的访问控制（时间、地点、IP）
- **数据权限**：部门级、项目级、行级/列级

---

## 五、监控与可观测性

### 监控指标

| 指标类型 | 具体指标 |
|---------|---------|
| **性能指标** | QPS、延迟 (P50/P95/P99)、错误率 |
| **资源指标** | CPU、内存、GPU 利用率、磁盘 IO |
| **业务指标** | 调用量、Token 使用量、活跃用户 |
| **模型指标** | 各模型调用量、延迟分布、成功率 |

### 日志体系

- **访问日志**：所有 API 请求记录
- **审计日志**：用户操作记录
- **错误日志**：异常堆栈信息
- **性能日志**：慢查询、慢调用

---

## 六、部署架构

### 开发环境

```yaml
services:
  backend: 1 实例
  frontend: 1 实例
  postgres: 1 实例
  redis: 1 实例
  milvus: 1 实例（standalone）
```

### 生产环境

```yaml
services:
  backend: 3-5 实例（HA）
  frontend: 2-3 实例（HA）
  postgres: 主从复制 + 读写分离
  redis: 哨兵模式
  milvus: 集群模式（4+ 节点）
```

---

## 七、扩展性设计

### 水平扩展

- **无状态服务**：支持快速扩缩容
- **分片策略**：知识库、日志分表分库
- **负载均衡**：Round Robin、Least Connection

### 插件机制

- **模型插件**：快速接入新模型
- **连接器插件**：对接外部系统
- **Skills 插件**：开发者贡献技能

---

*本文档将持续更新，反映最新的架构设计*
