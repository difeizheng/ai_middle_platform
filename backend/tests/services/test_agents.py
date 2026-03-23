"""
智能体工厂测试
"""
import pytest
from app.services.agents.engine import AgentEngine, AgentContext, AgentStatus
from app.services.agents.memory import AgentMemoryManager, MemoryType
from app.services.agents.tools import ToolRegistry, WebSearchTool, CalculatorTool


class TestAgentEngine:
    """智能体引擎测试"""

    @pytest.fixture
    def agent_engine(self):
        """创建智能体引擎实例"""
        return AgentEngine(
            agent_id=1,
            name="Test Agent",
            role="executor",
            config={
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            tools=[],
        )

    def test_agent_initialization(self, agent_engine):
        """测试智能体初始化"""
        assert agent_engine.agent_id == 1
        assert agent_engine.name == "Test Agent"
        assert agent_engine.role == "executor"
        assert agent_engine.temperature == 0.7

    def test_agent_status(self, agent_engine):
        """测试智能体状态"""
        status = agent_engine.get_status()
        assert "agent_id" in status
        assert "name" in status
        assert "status" in status

    def test_agent_context(self):
        """测试上下文"""
        context = AgentContext(
            session_id="test-session",
            task="测试任务",
        )
        assert context.session_id == "test-session"
        assert context.task == "测试任务"
        assert len(context.history) == 0

    @pytest.mark.asyncio
    async def test_build_prompt(self, agent_engine):
        """测试 Prompt 构建"""
        context = AgentContext(
            session_id="test-session",
            task="测试任务",
        )
        prompt = await agent_engine._build_prompt("测试任务", context)

        assert len(prompt) > 0
        assert prompt[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_execute_placeholder(self, agent_engine):
        """测试执行（占位测试）"""
        # 注意：实际执行需要 LLM 服务
        # 这里只测试基本流程
        assert agent_engine is not None


class TestAgentMemory:
    """记忆管理测试"""

    @pytest.fixture
    def memory_manager(self):
        """创建记忆管理器实例"""
        return AgentMemoryManager(
            agent_id=1,
            short_term_capacity=5,
            long_term_capacity=10,
        )

    def test_add_short_term(self, memory_manager):
        """测试添加短期记忆"""
        memory = memory_manager.add_short_term("测试记忆 1")

        assert memory.agent_id == 1
        assert memory.memory_type == MemoryType.SHORT_TERM
        assert "测试记忆 1" in memory.content
        assert len(memory_manager.short_term_memories) == 1

    def test_add_long_term(self, memory_manager):
        """测试添加长期记忆"""
        memory = memory_manager.add_long_term(
            "测试记忆 2",
            memory_type=MemoryType.EPISODIC,
            importance=4,
        )

        assert memory.agent_id == 1
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.importance == 4
        assert len(memory_manager.long_term_memories) == 1

    def test_short_term_capacity(self, memory_manager):
        """测试短期记忆容量限制"""
        for i in range(10):
            memory_manager.add_short_term(f"记忆{i}")

        assert len(memory_manager.short_term_memories) == 5

    def test_get_recent_memories(self, memory_manager):
        """测试获取最近记忆"""
        memory_manager.add_short_term("记忆 1")
        memory_manager.add_short_term("记忆 2")
        memory_manager.add_long_term("记忆 3")

        memories = memory_manager.get_recent_memories(limit=5)
        assert len(memories) == 3

    def test_clear_session(self, memory_manager):
        """测试清除会话"""
        session_id = "test-session"
        memory_manager.add_short_term("记忆 1", session_id)
        memory_manager.add_short_term("记忆 2", session_id)

        count = memory_manager.clear_session(session_id)
        assert count == 2
        assert len(memory_manager.short_term_memories) == 0

    def test_memory_summary(self, memory_manager):
        """测试记忆摘要"""
        memory_manager.add_short_term("记忆 1")
        memory_manager.add_long_term("记忆 2", MemoryType.EPISODIC)

        summary = memory_manager.get_summary()
        assert summary["short_term_count"] == 1
        assert summary["long_term_count"] == 1


class TestToolRegistry:
    """工具注册表测试"""

    @pytest.fixture
    def tool_registry(self):
        """创建工具注册表实例"""
        return ToolRegistry()

    def test_builtin_tools_registered(self, tool_registry):
        """测试内置工具已注册"""
        tools = tool_registry.list_tools()
        assert len(tools) >= 5

        tool_names = [t["name"] for t in tools]
        assert "web_search" in tool_names
        assert "calculator" in tool_names
        assert "code_executor" in tool_names
        assert "http_request" in tool_names
        assert "document_parser" in tool_names

    def test_get_tool(self, tool_registry):
        """测试获取工具"""
        tool = tool_registry.get("calculator")
        assert tool is not None

    def test_get_nonexistent_tool(self, tool_registry):
        """测试获取不存在的工具"""
        tool = tool_registry.get("nonexistent")
        assert tool is None

    @pytest.mark.asyncio
    async def test_calculator_execute(self, tool_registry):
        """测试计算器工具"""
        result = await tool_registry.execute(
            "calculator",
            {"expression": "2 + 3 * 4"}
        )
        assert result["result"] == 14

    @pytest.mark.asyncio
    async def test_calculator_invalid_expression(self, tool_registry):
        """测试无效表达式"""
        result = await tool_registry.execute(
            "calculator",
            {"expression": "invalid"}
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_web_search_execute(self, tool_registry):
        """测试搜索工具"""
        result = await tool_registry.execute(
            "web_search",
            {"query": "AI 技术", "num_results": 5}
        )
        assert isinstance(result, list)
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_http_request_execute(self, tool_registry):
        """测试 HTTP 请求工具"""
        result = await tool_registry.execute(
            "http_request",
            {"url": "https://httpbin.org/get", "method": "GET"}
        )
        # 可能成功或失败（网络问题）
        assert "status_code" in result or "error" in result


class TestFlowEngine:
    """流程引擎测试"""

    @pytest.fixture
    def simple_flow(self):
        """创建简单流程"""
        from app.services.agents.flow_engine import FlowEngine

        nodes = [
            {"id": "input_1", "type": "input", "data": {"output_name": "query"}},
            {"id": "transform_1", "type": "transform", "data": {"transform": "处理：{input}"}},
            {"id": "output_1", "type": "output"},
        ]

        edges = [
            {"source": "input_1", "target": "transform_1"},
            {"source": "transform_1", "target": "output_1"},
        ]

        return FlowEngine(
            flow_id=1,
            name="测试流程",
            nodes=nodes,
            edges=edges,
        )

    def test_flow_initialization(self, simple_flow):
        """测试流程初始化"""
        assert simple_flow.flow_id == 1
        assert simple_flow.name == "测试流程"
        assert len(simple_flow.nodes) == 3

    def test_topological_sort(self, simple_flow):
        """测试拓扑排序"""
        order = simple_flow._topological_sort()
        assert len(order) == 3
        assert order[0] == "input_1"
        assert order[-1] == "output_1"

    @pytest.mark.asyncio
    async def test_flow_execute(self, simple_flow):
        """测试流程执行"""
        result = await simple_flow.execute({"input": "测试数据"})

        assert result.flow_id == 1
        assert result.status.value == "completed"

    def test_flow_definition(self, simple_flow):
        """测试获取流程定义"""
        definition = simple_flow.get_flow_definition()
        assert definition["flow_id"] == 1
        assert definition["name"] == "测试流程"
        assert len(definition["nodes"]) == 3
        assert len(definition["edges"]) == 2
