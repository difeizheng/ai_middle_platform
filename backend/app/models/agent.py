"""
智能体工厂数据模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.sql import func
from ..core.database import Base


class Agent(Base):
    """
    智能体表
    """
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="智能体名称")
    description = Column(Text, comment="智能体描述")
    role = Column(String(100), comment="角色：planner, executor, reviewer, summarizer")
    model_id = Column(Integer, ForeignKey("models.id"), comment="绑定的模型 ID")

    # 智能体配置
    config = Column(JSON, default=dict, comment="智能体配置")
    """
    配置结构:
    {
        "temperature": 0.7,
        "max_tokens": 4096,
        "system_prompt": "你是一个专业的助手",
        "memory_enabled": true,
        "memory_type": "short_term",  # short_term, long_term, hybrid
        "reflection_enabled": false,
    }
    """

    # 绑定的工具
    tools = Column(JSON, default=list, comment="绑定工具列表")
    """
    工具列表结构:
    [
        {"id": "web_search", "name": "网页搜索", "config": {}},
        {"id": "code_executor", "name": "代码执行", "config": {}},
    ]
    """

    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建者 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class AgentFlow(Base):
    """
    智能体流程表（可视化编排的工作流）
    """
    __tablename__ = "agent_flows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="流程名称")
    description = Column(Text, comment="流程描述")
    version = Column(String(50), default="1.0.0", comment="版本号")

    # 流程定义
    nodes = Column(JSON, default=list, comment="节点定义")
    """
    节点结构:
    [
        {
            "id": "node_1",
            "type": "input",  # input, output, agent, tool, condition, loop
            "position": {"x": 100, "y": 200},
            "data": {
                "label": "用户输入",
                "agent_id": 1,  # agent 类型节点需要
                "tool_id": "web_search",  # tool 类型节点需要
                "condition": "xxx",  # condition 类型节点需要
            },
            "inputs": [{"name": "input", "type": "string"}],
            "outputs": [{"name": "output", "type": "string"}],
        }
    ]
    """

    edges = Column(JSON, default=list, comment="连接关系")
    """
    连接结构:
    [
        {
            "id": "edge_1",
            "source": "node_1",
            "target": "node_2",
            "sourceHandle": "output",
            "targetHandle": "input",
            "label": "传递数据",
        }
    ]
    """

    # 流程变量
    variables = Column(JSON, default=list, comment="流程变量定义")
    """
    变量结构:
    [
        {"name": "query", "type": "string", "default": "", "description": "搜索关键词"},
        {"name": "max_results", "type": "number", "default": 10},
    ]
    """

    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_template = Column(Boolean, default=False, comment="是否为模板")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建者 ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AgentExecution(Base):
    """
    智能体执行历史表
    """
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("agent_flows.id"), comment="流程 ID")
    agent_id = Column(Integer, ForeignKey("agents.id"), comment="智能体 ID（单智能体执行时）")

    # 执行信息
    status = Column(String(50), default="running", comment="状态：running, success, failed, cancelled")
    input_data = Column(JSON, default=dict, comment="输入数据")
    output_data = Column(JSON, default=dict, comment="输出数据")

    # 执行日志
    logs = Column(JSON, default=list, comment="执行日志")
    """
    日志结构:
    [
        {
            "timestamp": "2026-03-24T10:00:00",
            "node_id": "node_1",
            "level": "info",
            "message": "节点执行开始",
            "data": {},
        }
    ]
    """

    # 时间信息
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime(timezone=True), comment="开始时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")
    duration_ms = Column(Integer, comment="执行时长（毫秒）")

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentMemory(Base):
    """
    智能体记忆表（长期记忆）
    """
    __tablename__ = "agent_memories"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), comment="智能体 ID")
    session_id = Column(String(100), comment="会话 ID")

    # 记忆内容
    memory_type = Column(String(50), comment="记忆类型：short_term, long_term, episodic, semantic")
    content = Column(Text, comment="记忆内容")

    # 向量化（用于检索）
    embedding = Column(JSON, comment="向量表示")

    # 元数据
    importance = Column(Integer, default=1, comment="重要性评分 1-5")
    access_count = Column(Integer, default=0, comment="访问次数")
    last_accessed_at = Column(DateTime(timezone=True), comment="最后访问时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), comment="过期时间")


class AgentTool(Base):
    """
    智能体工具注册表
    """
    __tablename__ = "agent_tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, comment="工具名称")
    description = Column(Text, comment="工具描述")
    category = Column(String(100), comment="分类：search, compute, code, document, api, custom")

    # 工具实现
    tool_type = Column(String(50), comment="工具类型：builtin, api, code, script")
    config = Column(JSON, default=dict, comment="工具配置")
    """
    配置结构:
    {
        "endpoint": "https://api.example.com/search",  # API 类型
        "method": "POST",
        "code": "def execute(params): ...",  # code 类型
        "script_path": "/path/to/script.py",  # script 类型
    }
    """

    # 输入输出定义
    inputs = Column(JSON, default=list, comment="输入定义（JSON Schema）")
    outputs = Column(JSON, default=list, comment="输出定义（JSON Schema）")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_builtin = Column(Boolean, default=False, comment="是否为内置工具")
    author = Column(String(200), comment="作者")
    version = Column(String(50), default="1.0.0", comment="版本号")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
