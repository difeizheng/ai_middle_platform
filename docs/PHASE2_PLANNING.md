# Phase 2 规划方案

> Phase 2 重点：智能体工厂、MCP 连接器、Skills 市场
> 预计周期：2026 年 4 月 - 2026 年 6 月

---

## 一、Phase 2 目标

### 核心目标
1. **智能体工厂**：支持可视化编排的多智能体协作系统
2. **MCP 连接器**：对接外部系统和服务的通用连接器
3. **Skills 市场**：开发者生态和技能共享平台

### 关键指标
- 智能体编排效率提升 50%
- 外部系统对接时间缩短 70%
- Skills 市场入驻技能 > 100 个

---

## 二、智能体工厂设计

### 2.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      智能体工厂                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │  可视化编排层                                        │   │
│  │  • 拖拽式流程设计                                    │   │
│  │  • 节点类型：输入/输出/处理/判断/循环               │   │
│  │  • 连线绑定、参数传递                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  智能体核心层                                        │   │
│  │  • 单智能体：专注单一任务                            │   │
│  │  • 多智能体：协作完成复杂任务                        │   │
│  │  • 角色定义：规划者、执行者、审核者、总结者          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  工具集成层                                          │   │
│  │  • 内置工具：搜索、计算、代码执行、文档解析          │   │
│  │  • 外部 API：第三方服务调用                          │   │
│  │  • 自定义工具：用户扩展                              │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  运行时引擎                                          │   │
│  │  • 流程执行、状态管理、错误恢复                      │   │
│  │  • 并发控制、资源调度、性能监控                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据模型

```python
# 智能体表
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    role VARCHAR(100),  # 规划者、执行者、审核者、总结者
    model_id INTEGER REFERENCES models(id),
    config JSONB,  # 智能体配置
    tools JSONB,   # 绑定工具列表
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 智能体流程表
CREATE TABLE agent_flows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    nodes JSONB,   # 节点定义
    edges JSONB,   # 连接关系
    variables JSONB,  # 流程变量
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# 智能体执行历史
CREATE TABLE agent_executions (
    id SERIAL PRIMARY KEY,
    flow_id INTEGER REFERENCES agent_flows(id),
    status VARCHAR(50),  # running, success, failed
    input JSONB,
    output JSONB,
    logs JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 2.3 核心功能

#### 单智能体能力
- 基于 LLM 的任务执行
- 工具调用能力
- 记忆管理（短期/长期）
- 反思与改进

#### 多智能体协作
- 任务分解与分配
- 智能体间通信
- 结果汇总与审核
- 冲突解决机制

#### 可视化编排
- 流程设计器（前端组件）
- 节点库（内置 + 自定义）
- 流程模板市场
- 版本管理与发布

### 2.4 技术选型

| 模块 | 技术选型 | 备选方案 |
|------|---------|---------|
| 前端编排 | React Flow | GoJS, JointJS |
| 流程引擎 | 自研 | LangGraph, AutoGen |
| 智能体框架 | 自研 + LangChain | AutoGen, CrewAI |
| 状态存储 | Redis + PostgreSQL | MongoDB |
| 消息队列 | Redis Stream | RabbitMQ, Kafka |

---

## 三、MCP 连接器设计

### 3.1 MCP 协议

Model Context Protocol (MCP) 是一个开放的连接器协议标准，用于 AI 系统与外部服务的对接。

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP 连接器架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌─────────────┐ │
│  │  AI 中台核心   │    │  MCP Server   │    │  外部服务   │ │
│  │               │◄──►│               │◄──►│             │ │
│  │  • 智能体     │    │  • 协议转换   │    │  • 数据库   │ │
│  │  • 工作流     │    │  • 认证管理   │    │  • API 服务  │ │
│  │  • Skills    │    │  • 限流熔断   │    │  • 文件系统 │ │
│  └───────────────┘    └───────────────┘    └─────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 连接器类型

#### 内置连接器
| 连接器 | 功能 | 状态 |
|--------|------|------|
| MySQL | MySQL 数据库连接 | Phase 2 |
| PostgreSQL | PostgreSQL 数据库连接 | Phase 2 |
| HTTP | RESTful API 调用 | Phase 2 |
| File | 本地/网络文件系统 | Phase 2 |
| Redis | Redis 缓存服务 | Phase 2 |
| Kafka | 消息队列服务 | Phase 3 |

#### 扩展连接器
- 企业系统：SAP、Oracle、用友、金蝶
- 云服务：阿里云、腾讯云、AWS
- 办公软件：钉钉、企业微信、飞书
- 数据库：MongoDB、Elasticsearch

### 3.3 连接器开发框架

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class MCPConnector(ABC):
    """MCP 连接器基类"""

    @abstractmethod
    async def connect(self, config: Dict[str, Any]) -> bool:
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


# 连接器注册表
CONNECTOR_REGISTRY = {}

def register_connector(name: str):
    """连接器注册装饰器"""
    def decorator(cls):
        CONNECTOR_REGISTRY[name] = cls
        return cls
    return decorator

# 使用示例
@register_connector("mysql")
class MySQLConnector(MCPConnector):
    async def connect(self, config):
        # MySQL 连接逻辑
        pass
```

### 3.4 连接器管理

```python
# 连接器配置表
CREATE TABLE mcp_connectors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(100) NOT NULL,  # mysql, postgres, http, etc.
    config JSONB NOT NULL,       # 连接配置
    credentials JSONB,           # 认证信息（加密存储）
    status VARCHAR(50),          # active, inactive, error
    health_check_interval INT,   # 健康检查间隔（秒）
    last_health_check TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 四、Skills 市场设计

### 4.1 Skills 概念

Skill 是 AI 中台的能力单元，可以是：
- 一个 API 接口封装
- 一段代码逻辑
- 一个工具函数
- 一个智能体工作流

### 4.2 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Skills 市场                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Skill 管理                                          │   │
│  │  • Skill 上传、审核、发布、下架                      │   │
│  │  • 版本管理、变更日志                                │   │
│  │  • 分类标签、搜索发现                                │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Skill 运行                                          │   │
│  │  • 动态加载、沙箱执行                                │   │
│  │  • 权限控制、资源隔离                                │   │
│  │  • 调用统计、计费管理                                │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  开发者生态                                          │   │
│  │  • 开发者入驻、认证管理                              │   │
│  │  • 收益分成、激励计划                                │   │
│  │  • 文档中心、技术支持                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Skill 接口定义

```python
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class SkillInput(BaseModel):
    """Skill 输入定义"""
    name: str
    description: str
    type: str  # string, number, object, array
    required: bool = True
    default: Any = None
    schema: Dict  # JSON Schema

class SkillOutput(BaseModel):
    """Skill 输出定义"""
    name: str
    description: str
    type: str
    schema: Dict

class SkillMeta(BaseModel):
    """Skill 元数据"""
    id: str
    name: str
    description: str
    version: str
    author: str
    category: str
    tags: List[str]
    inputs: List[SkillInput]
    outputs: List[SkillOutput]
    icon: Optional[str] = None

class Skill(ABC):
    """Skill 基类"""

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Skill"""
        pass

    def get_meta(self) -> SkillMeta:
        """获取元数据"""
        pass
```

### 4.4 Skill 示例

```python
@register_skill("web_search")
class WebSearchSkill(Skill):
    """网页搜索 Skill"""

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("query", "")
        num_results = inputs.get("num_results", 10)

        # 调用搜索引擎 API
        results = await self.search_engine.search(query, num_results)

        return {
            "results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in results
            ]
        }

    def get_meta(self) -> SkillMeta:
        return SkillMeta(
            id="web_search",
            name="网页搜索",
            description="在互联网上搜索信息",
            version="1.0.0",
            author="AI 中台团队",
            category="搜索",
            tags=["搜索", "互联网", "信息检索"],
            inputs=[
                SkillInput(name="query", description="搜索关键词", type="string"),
                SkillInput(name="num_results", description="返回数量", type="number", default=10),
            ],
            outputs=[
                SkillOutput(name="results", description="搜索结果列表", type="array"),
            ],
        )
```

### 4.5 Skill 市场功能

#### 核心功能
- Skill 浏览与搜索
- Skill 详情与文档
- 一键安装/启用
- 用户评价与反馈
- 下载量/使用量统计

#### 开发者功能
- 开发者入驻申请
- Skill 上传与管理
- 数据统计与分析
- 收益管理
- 技术支持工单

---

## 五、开发计划

### Phase 2.1（4 月）- 智能体工厂基础

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W1 | 智能体架构设计、数据模型 | 设计文档 |
| W2 | 单智能体实现、工具调用 | 核心代码 |
| W3 | 多智能体协作框架 | 协作引擎 |
| W4 | 可视化编排器（基础版） | 前端组件 |

### Phase 2.2（5 月）- MCP 连接器

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W1 | MCP 协议定义、连接器框架 | 设计文档 |
| W2 | 内置连接器（MySQL/HTTP/File） | 连接器代码 |
| W3 | 连接器管理界面 | 管理后台 |
| W4 | 连接器市场（预览版） | 市场页面 |

### Phase 2.3（6 月）- Skills 市场

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W1 | Skills 架构设计、接口定义 | 设计文档 |
| W2 | 内置 Skills 开发（10+） | Skills 代码 |
| W3 | Skills 市场前端 | 市场页面 |
| W4 | 开发者入驻流程、文档 | 开发者中心 |

---

## 六、技术债务清理

### Phase 1 遗留问题
- [ ] 完善 API 文档示例
- [ ] 统一错误响应格式
- [ ] API Key 加密存储
- [ ] 完善输入验证

### 性能优化
- [ ] 慢查询分析与优化
- [ ] 缓存命中率提升
- [ ] 向量检索性能调优
- [ ] 并发压力测试

---

*Phase 2 规划方案将持续更新*
