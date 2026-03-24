"""
开发者门户 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.api.middleware import rate_limit

router = APIRouter()


# ========== 开发者文档 ==========

@router.get("/docs/overview")
async def get_developer_overview(
    current_user: User = Depends(get_current_user),
):
    """获取开发者门户概览"""
    return {
        "success": True,
        "data": {
            "title": "AI 中台开发者门户",
            "description": "提供完整的 API 文档、SDK 下载、开发者指南和示例代码",
            "sections": [
                {
                    "id": "quickstart",
                    "name": "快速开始",
                    "description": "5 分钟快速接入 AI 中台",
                    "url": "/api/v1/developer/docs/quickstart",
                },
                {
                    "id": "api",
                    "name": "API 文档",
                    "description": "完整的 API 接口文档",
                    "url": "/docs",
                },
                {
                    "id": "sdks",
                    "name": "SDK 下载",
                    "description": "多语言 SDK 和代码示例",
                    "url": "/api/v1/developer/sdks",
                },
                {
                    "id": "guides",
                    "name": "开发者指南",
                    "description": "详细的开发教程和最佳实践",
                    "url": "/api/v1/developer/guides",
                },
                {
                    "id": "examples",
                    "name": "示例代码",
                    "description": "各场景示例代码",
                    "url": "/api/v1/developer/examples",
                },
            ],
            "stats": {
                "total_apis": 50,
                "total_sdks": 3,
                "total_guides": 12,
                "total_examples": 24,
            },
        },
    }


@router.get("/docs/quickstart")
async def get_quickstart_guide(
    current_user: User = Depends(get_current_user),
):
    """获取快速开始指南"""
    return {
        "success": True,
        "data": {
            "title": "快速开始 - 5 分钟接入 AI 中台",
            "steps": [
                {
                    "step": 1,
                    "title": "创建应用",
                    "description": "在管理控制台创建应用，获取 API Key",
                    "code": """# 使用 Python SDK 创建应用
from ai_middle_platform import Client

client = Client(base_url="http://localhost:8000")
client.authenticate("admin", "admin123")

app = client.applications.create(
    name="My AI App",
    description="我的 AI 应用"
)
print(f"API Key: {app.api_key}")""",
                },
                {
                    "step": 2,
                    "title": "调用模型推理 API",
                    "description": "使用 API Key 调用模型推理接口",
                    "code": """import requests

response = requests.post(
    "http://localhost:8000/api/v1/inference/chat",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello"}]
    }
)
print(response.json())""",
                },
                {
                    "step": 3,
                    "title": "使用智能体工厂",
                    "description": "创建和运行智能体",
                    "code": """from ai_middle_platform.agents import Agent

agent = Agent.create(
    name="CustomerService",
    model="gpt-4",
    tools=["knowledge_base", "database"]
)

response = agent.run("查询上个月的销售数据")
print(response)""",
                },
                {
                    "step": 4,
                    "title": "集成 Skills 市场",
                    "description": "使用 Skills 市场中的技能",
                    "code": """from ai_middle_platform.skills import SkillClient

skills = SkillClient()
skills.install("data_analysis")

result = skills.execute(
    "data_analysis",
    data=[{"name": "A", "age": 25}],
    operation="statistic"
)
print(result)""",
                },
            ],
            "links": {
                "api_docs": "/docs",
                "sdk_download": "/api/v1/developer/sdks",
                "examples": "/api/v1/developer/examples",
            },
        },
    }


# ========== SDK 下载 ==========

@router.get("/sdks")
async def list_sdks(
    language: Optional[str] = Query(None, description="编程语言过滤"),
    current_user: User = Depends(get_current_user),
):
    """获取 SDK 列表"""
    sdks = [
        {
            "name": "ai-middle-platform-sdk",
            "language": "python",
            "version": "0.6.0",
            "description": "AI 中台 Python SDK",
            "install_command": "pip install ai-middle-platform-sdk",
            "download_url": "https://pypi.org/project/ai-middle-platform-sdk/",
            "github_url": "https://github.com/difeizheng/ai_middle_platform_sdk",
            "documentation": "/api/v1/developer/docs/sdk-python",
        },
        {
            "name": "@ai-middle-platform/sdk",
            "language": "javascript",
            "version": "0.6.0",
            "description": "AI 中台 JavaScript/TypeScript SDK",
            "install_command": "npm install @ai-middle-platform/sdk",
            "download_url": "https://www.npmjs.com/package/@ai-middle-platform/sdk",
            "github_url": "https://github.com/difeizheng/ai_middle_platform_js_sdk",
            "documentation": "/api/v1/developer/docs/sdk-js",
        },
        {
            "name": "ai-middle-platform-go",
            "language": "go",
            "version": "0.6.0",
            "description": "AI 中台 Go SDK",
            "install_command": "go get github.com/difeizheng/ai_middle_platform_go",
            "download_url": "https://pkg.go.dev/github.com/difeizheng/ai_middle_platform_go",
            "github_url": "https://github.com/difeizheng/ai_middle_platform_go",
            "documentation": "/api/v1/developer/docs/sdk-go",
        },
    ]

    if language:
        sdks = [s for s in sdks if s["language"] == language]

    return {
        "success": True,
        "data": sdks,
    }


@router.get("/docs/sdk-{lang}")
async def get_sdk_docs(
    lang: str,
    current_user: User = Depends(get_current_user),
):
    """获取特定 SDK 的文档"""
    docs = {
        "python": {
            "title": "Python SDK 文档",
            "version": "0.6.0",
            "sections": [
                {"name": "安装", "content": "pip install ai-middle-platform-sdk"},
                {"name": "初始化", "content": """from ai_middle_platform import Client

client = Client(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)"""},
                {"name": "模型推理", "content": """response = client.inference.chat(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response)"""},
                {"name": "智能体调用", "content": """agent = client.agents.get("agent-id")
response = agent.run("查询数据")
print(response)"""},
                {"name": "Skills 使用", "content": """result = client.skills.execute(
    skill_id="data_analysis",
    params={"data": [...], "operation": "statistic"}
)"""},
            ],
        },
        "js": {
            "title": "JavaScript SDK 文档",
            "version": "0.6.0",
            "sections": [
                {"name": "安装", "content": "npm install @ai-middle-platform/sdk"},
                {"name": "初始化", "content": """import { AIClient } from '@ai-middle-platform/sdk';

const client = new AIClient({
  baseURL: 'http://localhost:8000',
  apiKey: 'your-api-key'
});"""},
                {"name": "模型推理", "content": """const response = await client.inference.chat({
  model: 'gpt-3.5-turbo',
  messages: [{ role: 'user', content: 'Hello' }]
});
console.log(response);"""},
            ],
        },
        "go": {
            "title": "Go SDK 文档",
            "version": "0.6.0",
            "sections": [
                {"name": "安装", "content": "go get github.com/difeizheng/ai_middle_platform_go"},
                {"name": "初始化", "content": """import "github.com/difeizheng/ai_middle_platform_go"

client := NewClient(Config{
    BaseURL: "http://localhost:8000",
    APIKey:  "your-api-key",
})"""},
            ],
        },
    }

    if lang not in docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"不支持的语言：{lang}",
        )

    return {
        "success": True,
        "data": docs[lang],
    }


# ========== 开发者指南 ==========

@router.get("/guides")
async def list_guides(
    category: Optional[str] = Query(None, description="分类过滤"),
    current_user: User = Depends(get_current_user),
):
    """获取开发者指南列表"""
    guides = [
        {
            "id": "getting-started",
            "title": "入门指南",
            "category": "基础",
            "description": "快速了解 AI 中台的核心功能",
            "read_time": 10,
            "url": "/api/v1/developer/guides/getting-started",
        },
        {
            "id": "authentication",
            "title": "认证与鉴权",
            "category": "基础",
            "description": "了解 API 认证和鉴权机制",
            "read_time": 8,
            "url": "/api/v1/developer/guides/authentication",
        },
        {
            "id": "model-factory",
            "title": "模型工厂使用指南",
            "category": "核心功能",
            "description": "使用模型工厂管理 AI 模型",
            "read_time": 15,
            "url": "/api/v1/developer/guides/model-factory",
        },
        {
            "id": "agent-factory",
            "title": "智能体工厂开发指南",
            "category": "核心功能",
            "description": "创建和部署 AI 智能体",
            "read_time": 20,
            "url": "/api/v1/developer/guides/agent-factory",
        },
        {
            "id": "skills-market",
            "title": "Skills 市场开发指南",
            "category": "核心功能",
            "description": "开发和使用 Skills",
            "read_time": 18,
            "url": "/api/v1/developer/guides/skills-market",
        },
        {
            "id": "mcp-connectors",
            "title": "MCP 连接器开发指南",
            "category": "核心功能",
            "description": "开发自定义 MCP 连接器",
            "read_time": 25,
            "url": "/api/v1/developer/guides/mcp-connectors",
        },
        {
            "id": "best-practices",
            "title": "最佳实践",
            "category": "进阶",
            "description": "生产环境部署最佳实践",
            "read_time": 30,
            "url": "/api/v1/developer/guides/best-practices",
        },
        {
            "id": "performance-tuning",
            "title": "性能调优指南",
            "category": "进阶",
            "description": "系统性能优化和调优",
            "read_time": 25,
            "url": "/api/v1/developer/guides/performance-tuning",
        },
    ]

    if category:
        guides = [g for g in guides if g["category"] == category]

    return {
        "success": True,
        "data": guides,
    }


@router.get("/guides/{guide_id}")
async def get_guide(
    guide_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取开发者指南详情"""
    guides = {
        "getting-started": {
            "id": "getting-started",
            "title": "入门指南",
            "category": "基础",
            "content": """## AI 中台简介

AI 中台是企业级 AI 能力基础设施，提供统一的 AI 模型管理、开发、部署和服务能力。

### 核心功能

1. **模型工厂** - 统一接入和管理多模型（OpenAI/vLLM/DeepSeek 等）
2. **知识工厂** - 文档解析、向量化、混合检索
3. **智能体工厂** - 单智能体引擎、流程引擎、工具系统
4. **MCP 连接器** - 统一连接器协议
5. **Skills 市场** - Skill 注册、查询、执行
6. **运营监控** - 监控指标、健康检查、告警管理

### 架构设计

```
┌─────────────────────────────────────────────────┐
│              前端应用 (React)                     │
├─────────────────────────────────────────────────┤
│              API 网关 (FastAPI)                   │
├────────────┬────────────┬────────────────────────┤
│  模型工厂   │  知识工厂   │      智能体工厂         │
├────────────┴────────────┴────────────────────────┤
│         MCP 连接器        │      Skills 市场        │
├─────────────────────────────────────────────────┤
│    PostgreSQL    │    Redis    │    Milvus       │
└─────────────────────────────────────────────────┘
```
""",
        },
        "authentication": {
            "id": "authentication",
            "title": "认证与鉴权",
            "category": "基础",
            "content": """## 认证机制

AI 中台使用 API Key 进行认证。

### 获取 API Key

1. 登录管理控制台
2. 进入「应用管理」
3. 创建新应用或选择已有应用
4. 复制 API Key

### 使用 API Key

在所有 API 请求的 Header 中添加：

```
Authorization: Bearer YOUR_API_KEY
```

### 认证示例

```python
import requests

api_key = "your-api-key"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(
    "http://localhost:8000/api/v1/models",
    headers=headers
)
```

### 安全建议

- 不要在客户端代码中硬编码 API Key
- 定期轮换 API Key
- 为不同环境使用不同的 API Key
- 设置合适的配额限制
""",
        },
    }

    if guide_id not in guides:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"指南不存在：{guide_id}",
        )

    return {
        "success": True,
        "data": guides[guide_id],
    }


# ========== 示例代码 ==========

@router.get("/examples")
async def list_examples(
    category: Optional[str] = Query(None, description="分类过滤"),
    current_user: User = Depends(get_current_user),
):
    """获取示例代码列表"""
    examples = [
        {
            "id": "chat-completion",
            "title": "对话补全示例",
            "category": "模型推理",
            "difficulty": "简单",
            "description": "使用大语言模型进行对话",
            "url": "/api/v1/developer/examples/chat-completion",
        },
        {
            "id": "knowledge-search",
            "title": "知识库检索示例",
            "category": "知识工厂",
            "difficulty": "中等",
            "description": "使用向量检索查询知识库",
            "url": "/api/v1/developer/examples/knowledge-search",
        },
        {
            "id": "agent-workflow",
            "title": "智能体工作流示例",
            "category": "智能体工厂",
            "difficulty": "复杂",
            "description": "多智能体协作完成复杂任务",
            "url": "/api/v1/developer/examples/agent-workflow",
        },
        {
            "id": "skill-data-analysis",
            "title": "数据分析 Skill 示例",
            "category": "Skills 市场",
            "difficulty": "中等",
            "description": "使用数据分析 Skill 处理数据",
            "url": "/api/v1/developer/examples/skill-data-analysis",
        },
        {
            "id": "mcp-mysql",
            "title": "MySQL 连接器示例",
            "category": "MCP 连接器",
            "difficulty": "中等",
            "description": "使用 MCP 连接器查询 MySQL 数据库",
            "url": "/api/v1/developer/examples/mcp-mysql",
        },
    ]

    if category:
        examples = [e for e in examples if e["category"] == category]

    return {
        "success": True,
        "data": examples,
    }


@router.get("/examples/{example_id}")
async def get_example(
    example_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取示例代码详情"""
    examples = {
        "chat-completion": {
            "id": "chat-completion",
            "title": "对话补全示例",
            "category": "模型推理",
            "difficulty": "简单",
            "description": "使用大语言模型进行对话",
            "code": """# Python 示例
from ai_middle_platform import Client

client = Client(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# 简单对话
response = client.inference.chat(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手"},
        {"role": "user", "content": "你好，请介绍一下自己"}
    ]
)

print(response["choices"][0]["message"]["content"])

# 流式对话
for chunk in client.inference.chat_stream(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "写一首诗"}]
):
    print(chunk, end="")
""",
        },
        "knowledge-search": {
            "id": "knowledge-search",
            "title": "知识库检索示例",
            "category": "知识工厂",
            "difficulty": "中等",
            "code": """# 上传文档到知识库
from ai_middle_platform import Client

client = Client(api_key="your-api-key")

# 上传文档
doc = client.knowledge.upload_document(
    knowledge_base_id="kb-001",
    file_path="./document.pdf",
    metadata={"source": "manual"}
)

# 向量检索
results = client.knowledge.search(
    knowledge_base_id="kb-001",
    query="如何重置密码",
    top_k=5
)

for result in results:
    print(f"分数：{result.score}")
    print(f"内容：{result.content}")
""",
        },
        "agent-workflow": {
            "id": "agent-workflow",
            "title": "智能体工作流示例",
            "category": "智能体工厂",
            "difficulty": "复杂",
            "code": """# 多智能体协作示例
from ai_middle_platform.agents import Agent, Workflow

# 创建专业智能体
researcher = Agent.create(
    name="Researcher",
    role="研究分析师",
    tools=["web_search", "knowledge_base"]
)

writer = Agent.create(
    name="Writer",
    role="内容撰写",
    tools=["report_generator"]
)

reviewer = Agent.create(
    name="Reviewer",
    role="质量审核",
    tools=["code_review", "fact_check"]
)

# 创建工作流
workflow = Workflow.create(
    name="Research Workflow",
    agents=[researcher, writer, reviewer],
    steps=[
        {"agent": "researcher", "task": "收集信息"},
        {"agent": "writer", "task": "撰写报告"},
        {"agent": "reviewer", "task": "审核报告"},
    ]
)

# 执行工作流
result = workflow.run("撰写 AI 行业发展分析报告")
print(result)
""",
        },
    }

    if example_id not in examples:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"示例不存在：{example_id}",
        )

    return {
        "success": True,
        "data": examples[example_id],
    }
