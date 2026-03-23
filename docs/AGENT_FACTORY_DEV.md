# 智能体工厂开发文档

> Phase 2.1 - 智能体工厂基础开发
> 日期：2026 年 3 月 24 日

---

## 一、开发概览

### 1.1 完成模块

| 模块 | 文件 | 状态 |
|------|------|------|
| 数据模型 | `models/agent.py` | 完成 |
| 智能体引擎 | `services/agents/engine.py` | 完成 |
| 流程引擎 | `services/agents/flow_engine.py` | 完成 |
| 工具系统 | `services/agents/tools.py` | 完成 |
| 记忆管理 | `services/agents/memory.py` | 完成 |
| API 路由 | `api/agents.py` | 完成 |
| 数据库迁移 | `deploy/migrations/agent_factory.sql` | 完成 |

### 1.2 核心功能

#### 智能体引擎 (Agent Engine)
- 单智能体任务执行
- 工具调用管理
- 记忆读写
- 反思能力
- 流式输出支持

#### 流程引擎 (Flow Engine)
- 流程定义解析（节点 + 边）
- 拓扑排序执行
- 条件分支处理
- 循环节点支持
- 并行执行
- 错误恢复

#### 工具系统 (Tool System)
- 工具注册表
- 内置工具（5 个）：
  - `web_search` - 网页搜索
  - `code_executor` - 代码执行
  - `calculator` - 数学计算
  - `http_request` - HTTP 请求
  - `document_parser` - 文档解析
- 自定义工具扩展

#### 记忆管理 (Memory Manager)
- 短期记忆（内存）
- 长期记忆（持久化）
- 记忆检索（向量相似度）
- 记忆遗忘（基于重要性和时间）

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      智能体工厂 API                          │
├─────────────────────────────────────────────────────────────┤
│  /api/v1/agents/               # 智能体管理                  │
│  /api/v1/flows/                # 流程管理                    │
│  /api/v1/tools/                # 工具管理                    │
│  /api/v1/executions/           # 执行历史                    │
├─────────────────────────────────────────────────────────────┤
│  AgentEngine    # 智能体引擎                                 │
│  FlowEngine     # 流程引擎                                   │
│  ToolRegistry   # 工具注册表                                 │
│  MemoryManager  # 记忆管理器                                 │
├─────────────────────────────────────────────────────────────┤
│  models/agent.py  # 数据模型                                 │
│  - Agent        # 智能体表                                   │
│  - AgentFlow    # 流程表                                     │
│  - AgentExecution # 执行历史表                               │
│  - AgentMemory  # 记忆表                                     │
│  - AgentTool    # 工具表                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 智能体角色

| 角色 | 职责 | 适用场景 |
|------|------|---------|
| planner | 任务规划专家 | 复杂任务分解 |
| executor | 高效执行者 | 工具调用、任务执行 |
| reviewer | 严格审核者 | 质量检查、错误发现 |
| summarizer | 优秀总结者 | 信息提取、文档总结 |

---

## 三、API 接口

### 3.1 智能体管理

```
GET    /api/v1/agents           # 获取智能体列表
POST   /api/v1/agents           # 创建智能体
GET    /api/v1/agents/{id}      # 获取智能体详情
PUT    /api/v1/agents/{id}      # 更新智能体
DELETE /api/v1/agents/{id}      # 删除智能体
POST   /api/v1/agents/{id}/execute  # 执行智能体任务
```

### 3.2 流程管理

```
GET    /api/v1/flows            # 获取流程列表
POST   /api/v1/flows            # 创建流程
GET    /api/v1/flows/{id}       # 获取流程详情
POST   /api/v1/flows/{id}/execute   # 执行流程
```

### 3.3 工具管理

```
GET    /api/v1/tools            # 获取工具列表
POST   /api/v1/tools/execute    # 执行工具
```

### 3.4 执行历史

```
GET    /api/v1/executions       # 获取执行历史
```

---

## 四、使用示例

### 4.1 创建智能体

```python
import httpx

response = httpx.post("http://localhost:8000/api/v1/agents", json={
    "name": "我的助手",
    "description": "一个多功能 AI 助手",
    "role": "executor",
    "config": {
        "temperature": 0.7,
        "max_tokens": 4096,
        "memory_enabled": True,
    },
    "tools": [
        {"id": "web_search", "name": "网页搜索"},
        {"id": "calculator", "name": "计算器"},
    ],
})

agent_id = response.json()["data"]["id"]
```

### 4.2 执行智能体任务

```python
response = httpx.post(
    f"http://localhost:8000/api/v1/agents/{agent_id}/execute",
    json={
        "task": "搜索最新的 AI 技术新闻并总结",
        "session_id": "session-123",
    }
)

result = response.json()["data"]["content"]
```

### 4.3 创建流程

```python
# 定义节点
nodes = [
    {
        "id": "input_1",
        "type": "input",
        "data": {"label": "用户输入"},
    },
    {
        "id": "agent_1",
        "type": "agent",
        "data": {"label": "搜索", "agent_id": 2},
    },
    {
        "id": "output_1",
        "type": "output",
        "data": {"label": "输出"},
    },
]

# 定义连接
edges = [
    {"source": "input_1", "target": "agent_1"},
    {"source": "agent_1", "target": "output_1"},
]

response = httpx.post("http://localhost:8000/api/v1/flows", json={
    "name": "搜索流程",
    "nodes": nodes,
    "edges": edges,
})

flow_id = response.json()["data"]["id"]
```

### 4.4 执行流程

```python
response = httpx.post(
    f"http://localhost:8000/api/v1/flows/{flow_id}/execute",
    json={
        "inputs": {"input": "查询 AI 技术新闻"},
    }
)

result = response.json()["data"]
```

---

## 五、数据库表结构

### 5.1 核心表

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| agents | 智能体表 | id, name, role, config, tools |
| agent_flows | 流程表 | id, nodes, edges, variables |
| agent_executions | 执行历史 | id, status, input_data, output_data |
| agent_memories | 记忆表 | id, agent_id, content, embedding |
| agent_tools | 工具表 | id, name, category, config |

### 5.2 索引

```sql
-- 智能体表
CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_role ON agents(role);

-- 流程表
CREATE INDEX idx_agent_flows_name ON agent_flows(name);

-- 执行历史
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at DESC);

-- 记忆表
CREATE INDEX idx_agent_memories_agent_id ON agent_memories(agent_id);
```

---

## 六、扩展开发

### 6.1 添加自定义工具

```python
from app.services.agents.tools import BaseTool, ToolDefinition

class MyCustomTool(BaseTool):
    async def execute(self, params: Dict[str, Any]) -> Any:
        # 实现工具逻辑
        result = await self.do_something(params)
        return result

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_custom_tool",
            description="我的自定义工具",
            category="custom",
            inputs=[...],
            outputs=[...],
            config={},
        )

# 注册工具
from app.services.agents.tools import register_tool
register_tool(MyCustomTool())
```

### 6.2 添加自定义节点类型

```python
# 在 FlowEngine 中添加新的节点类型
async def _execute_custom_node(self, node: Dict, context: NodeContext) -> Dict:
    # 实现自定义节点逻辑
    pass

# 在_execute_node 方法中注册
elif node_type == "custom":
    return await self._execute_custom_node(node, context)
```

---

## 七、下一步计划

### Phase 2.1 收尾
- [x] 核心模块开发
- [ ] 单元测试编写
- [ ] 集成测试
- [ ] 性能优化

### Phase 2.2 MCP 连接器
- [ ] MCP 协议定义
- [ ] 连接器框架
- [ ] 内置连接器（MySQL/HTTP/File）

### Phase 2.3 Skills 市场
- [ ] Skill 接口定义
- [ ] 内置 Skills
- [ ] 市场前端

---

*智能体工厂基础开发完成，进入测试阶段*
