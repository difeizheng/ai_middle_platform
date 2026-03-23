# AI 中台系统

> 企业级 AI 能力基础设施 - 构建可持续的 AI 能力体系

**版本：** v0.5.0
**日期：** 2026 年 3 月 23 日

---

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 启动所有服务
docker-compose -f deploy/docker-compose.yml up -d

# 查看日志
docker-compose logs -f backend
```

### 方式二：本地开发

```bash
# 启动后端
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# 启动前端
cd frontend
npm install
npm run dev
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 前端 | http://localhost:3000 |

### 默认账户

```
用户名：admin
密码：admin123
```

---

## 项目结构

```
.
├── backend/              # 后端服务
│   ├── app/
│   │   ├── api/         # API 路由
│   │   │   ├── skills.py    # Skills 市场 API (Phase 2.3)
│   │   │   ├── mcp.py       # MCP 连接器 API (Phase 2.2)
│   │   │   └── agents.py    # 智能体工厂 API (Phase 2.1)
│   │   ├── auth/        # 认证授权
│   │   ├── core/        # 核心配置
│   │   ├── models/      # 数据模型
│   │   │   ├── skill.py     # Skills 模型
│   │   │   └── agent.py     # 智能体模型
│   │   ├── services/    # 服务层
│   │   │   ├── skills/      # Skills 服务
│   │   │   ├── mcp/         # MCP 连接器
│   │   │   └── agents/      # 智能体服务
│   │   └── main.py      # 入口文件
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/             # 前端应用
│   ├── src/
│   │   ├── pages/       # 页面组件
│   │   ├── store/       # 状态管理
│   │   └── utils/       # 工具函数
│   └── package.json
├── deploy/               # 部署配置
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   └── init.sql
└── docs/                 # 文档
    ├── architecture.md
    ├── DEV_LOG.md
    └── PHASE_*.md       # 各阶段开发总结
```

---

## 核心功能

### Phase 1 - 基础平台（已完成）

- **模型工厂** - 统一接入和管理多模型（OpenAI/vLLM/DeepSeek 等）
- **知识工厂** - 文档解析、向量化、混合检索
- **API 网关** - 认证鉴权、限流熔断、审计日志
- **应用管理** - 应用接入和 API Key 管理
- **日志审计** - 全链路日志和统计

### Phase 2.1 - 智能体工厂（已完成）

- **单智能体引擎** - 支持 ReAct/Plan-Execute 模式
- **流程引擎** - 多智能体编排和执行
- **工具系统** - 内置工具和扩展机制
- **记忆管理** - 短期/长期记忆支持

### Phase 2.2 - MCP 连接器（已完成）

- **7 个内置连接器** - MySQL/PostgreSQL/HTTP/Redis/File/Kafka/MongoDB
- **统一协议** - 标准化的连接器接口
- **加密服务** - Fernet+PBKDF2 敏感数据保护

### Phase 2.3 - Skills 市场（已完成）

- **Skill 注册表** - Skill 的注册、查询、执行
- **4 个内置 Skills**：
  - `data_analysis` - 数据分析（统计/分组/聚合/过滤）
  - `report_generator` - 报告生成（Markdown/JSON/HTML）
  - `code_review` - 代码审查（风格/安全/性能）
  - `notification` - 通知发送（日志/Webhook/Email）
- **三种实现方式** - Python/HTTP/MCP 连接器
- **版本管理** - Skill 版本控制和回滚
- **智能体集成** - 智能体可调用 Skills 市场中的技能

### Phase 2.4 - 运营监控（已完成）

- **监控指标服务** - MetricCollector 支持 counter/gauge/histogram 三种指标类型
- **健康检查器** - 定期检查 database/redis/embedding/llm 服务健康状态
- **告警管理** - 告警规则配置、告警历史、告警确认
- **仪表盘** - 可配置的监控仪表盘和数据可视化
- **监控 API** - `/metrics/*`, `/health/*`, `/alerts/*`, `/dashboards/*`

---

## 技术栈

| 层次 | 技术 |
|------|------|
| **后端** | Python 3.10+, FastAPI, SQLAlchemy |
| **前端** | React, TypeScript, Ant Design |
| **数据库** | PostgreSQL 15+, Redis 7+ |
| **向量库** | Milvus 2.3+ / Qdrant |
| **AI 框架** | LangChain, vLLM, Transformers |
| **部署** | Docker, Docker Compose, Kubernetes |

---

## API 示例

### Skills 市场 API

```bash
# 获取已注册的 Skills
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/skills/skills/registry

# 执行数据分析 Skill
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{"name": "A", "age": 25}, {"name": "B", "age": 30}],
    "operation": "statistic",
    "config": {"fields": ["age"]}
  }' \
  http://localhost:8000/api/v1/skills/skills/data_analysis/execute
```

### MCP 连接器 API

```bash
# 获取连接器类型
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/mcp/types

# 执行连接器操作
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "query", "params": {"sql": "SELECT * FROM users"}}' \
  http://localhost:8000/api/v1/mcp/connectors/{id}/execute
```

### 运营监控 API

```bash
# 获取监控指标概览
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitor/metrics/overview

# 获取实时指标
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitor/metrics/realtime

# 获取服务健康状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitor/health/services

# 获取告警规则列表
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/monitor/alerts/rules
```

---

## 开发阶段

| 阶段 | 状态 | 描述 |
|------|------|------|
| Phase 1 | ✅ 完成 | 模型工厂、知识工厂、API 网关 |
| Phase 2.1 | ✅ 完成 | 智能体工厂 |
| Phase 2.2 | ✅ 完成 | MCP 连接器 |
| Phase 2.3 | ✅ 完成 | Skills 市场 |
| Phase 2.4 | ✅ 完成 | 运营监控 |

---

## 文档

- [架构设计文档](docs/architecture.md)
- [开发日志](docs/DEV_LOG.md)
- [Phase 2.3 Skills 市场总结](PHASE_2_3_SUMMARY.md)
- [Phase 2.2 MCP 连接器总结](docs/PHASE_2_MCP_SUMMARY.md)
- [Phase 2.1 智能体工厂总结](docs/PHASE_2_AGENT_FACTORY_SUMMARY.md)

---

## License

MIT License
