"""
智能体引擎 - 单智能体执行核心
"""
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import json

from ...core.logger import get_logger

logger = get_logger(__name__)


class AgentStatus(Enum):
    """智能体状态"""
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    MEMORY_READING = "memory_reading"
    MEMORY_WRITING = "memory_writing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentContext:
    """智能体上下文"""
    session_id: str
    task: str
    history: List[Dict[str, str]] = field(default_factory=list)
    memory: List[str] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """智能体响应"""
    content: str
    status: AgentStatus
    tool_calls: List[Dict] = field(default_factory=list)
    memory_updates: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentEngine:
    """
    智能体执行引擎

    功能:
    - 基于 LLM 的任务执行
    - 工具调用管理
    - 记忆管理
    - 反思能力
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        role: str,
        config: Dict[str, Any],
        tools: List[Dict],
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.config = config
        self.tools = tools
        self.status = AgentStatus.IDLE

        # 从配置中提取参数
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt", "")
        self.memory_enabled = config.get("memory_enabled", False)
        self.reflection_enabled = config.get("reflection_enabled", False)

    async def execute(
        self,
        task: str,
        context: Optional[AgentContext] = None,
        stream: bool = False,
    ) -> AgentResponse:
        """
        执行智能体任务

        Args:
            task: 任务描述
            context: 执行上下文
            stream: 是否流式输出

        Returns:
            AgentResponse 智能体响应
        """
        self.status = AgentStatus.THINKING

        if context is None:
            context = AgentContext(
                session_id=str(uuid.uuid4()),
                task=task,
            )

        try:
            # 1. 读取记忆（如果启用）
            if self.memory_enabled:
                self.status = AgentStatus.MEMORY_READING
                await self._read_memory(context)

            # 2. 构建 Prompt
            prompt = await self._build_prompt(task, context)

            # 3. 调用 LLM
            self.status = AgentStatus.THINKING
            llm_response = await self._call_llm(prompt, stream)

            # 4. 解析响应
            response = await self._parse_response(llm_response, context)

            # 5. 执行工具调用（如果有）
            if response.tool_calls:
                self.status = AgentStatus.TOOL_CALLING
                tool_results = await self._execute_tools(response.tool_calls)
                response.tool_results = tool_results

                # 递归调用（多轮工具使用）
                if self._should_continue(response):
                    return await self.execute(task, context, stream)

            # 6. 写入记忆（如果启用）
            if self.memory_enabled:
                self.status = AgentStatus.MEMORY_WRITING
                await self._write_memory(context, response)

            # 7. 反思（如果启用）
            if self.reflection_enabled:
                self.status = AgentStatus.REFLECTING
                reflection = await self._reflect(context, response)
                response.metadata["reflection"] = reflection

            self.status = AgentStatus.COMPLETED
            return response

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent execution error: {e}", exc_info=True)
            return AgentResponse(
                content=f"执行失败：{str(e)}",
                status=AgentStatus.ERROR,
            )

    async def execute_stream(
        self,
        task: str,
        context: Optional[AgentContext] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体任务

        Args:
            task: 任务描述
            context: 执行上下文

        Yields:
            流式输出的文本片段
        """
        response = await self.execute(task, context, stream=True)

        if hasattr(response, "stream"):
            async for chunk in response.stream:
                yield chunk
        else:
            yield response.content

    async def _read_memory(self, context: AgentContext) -> None:
        """读取相关记忆"""
        # 从向量存储中检索与当前任务相关的记忆
        # 这里使用缓存服务或向量存储服务
        from ...services.cache import cache_service

        # 检索最近 N 条记忆
        memory_key = f"ai:agent:memory:{self.agent_id}:{context.session_id}"
        memories = await cache_service.get(memory_key)
        if memories:
            context.memory = memories[:5]  # 限制记忆数量

    async def _write_memory(
        self,
        context: AgentContext,
        response: AgentResponse,
    ) -> None:
        """写入记忆"""
        from ...services.cache import cache_service

        memory_key = f"ai:agent:memory:{self.agent_id}:{context.session_id}"
        memories = context.memory + [response.content]

        # 限制记忆长度
        if len(memories) > 10:
            memories = memories[-10:]

        await cache_service.set(memory_key, memories, expire=3600 * 24)  # 24 小时

    async def _build_prompt(self, task: str, context: AgentContext) -> List[Dict]:
        """构建 Prompt"""
        # 角色定义
        role_map = {
            "planner": "你是一个任务规划专家，擅长分解复杂任务并制定执行计划。",
            "executor": "你是一个高效的执行者，擅长调用工具完成任务。",
            "reviewer": "你是一个严格的审核者，擅长检查和改进输出质量。",
            "summarizer": "你是一个优秀的总结者，擅长从大量信息中提取关键点。",
        }

        system_content = role_map.get(self.role, "你是一个专业的 AI 助手。")
        if self.system_prompt:
            system_content = f"{system_content}\n\n{self.system_prompt}"

        # 构建消息
        messages = [
            {"role": "system", "content": system_content},
        ]

        # 添加记忆
        if context.memory:
            memory_content = "\n".join([f"- {m}" for m in context.memory])
            messages.append({
                "role": "system",
                "content": f"相关记忆:\n{memory_content}",
            })

        # 添加工具描述
        if self.tools:
            tool_desc = json.dumps(
                [{"name": t.get("name"), "description": t.get("description")} for t in self.tools],
                ensure_ascii=False,
                indent=2,
            )
            messages.append({
                "role": "system",
                "content": f"可用工具:\n{tool_desc}",
            })

        # 添加历史对话
        messages.extend(context.history)

        # 添加当前任务
        messages.append({"role": "user", "content": task})

        return messages

    async def _call_llm(
        self,
        messages: List[Dict],
        stream: bool = False,
    ) -> Any:
        """调用 LLM"""
        from ...services.llm import LLMService

        llm_service = LLMService()
        return await llm_service.chat(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=stream,
        )

    async def _parse_response(self, llm_response: Any, context: AgentContext) -> AgentResponse:
        """解析 LLM 响应"""
        # 简单实现，实际应该解析 tool_calls 等
        content = llm_response.get("content", "") if isinstance(llm_response, dict) else str(llm_response)

        return AgentResponse(
            content=content,
            status=self.status,
        )

    async def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """执行工具调用"""
        from .tools import ToolRegistry

        registry = ToolRegistry()
        results = []

        for call in tool_calls:
            tool_name = call.get("tool_name")
            params = call.get("params", {})

            try:
                result = await registry.execute(tool_name, params)
                results.append({
                    "tool_name": tool_name,
                    "params": params,
                    "result": result,
                    "success": True,
                })
            except Exception as e:
                results.append({
                    "tool_name": tool_name,
                    "params": params,
                    "error": str(e),
                    "success": False,
                })

        return results

    def _should_continue(self, response: AgentResponse) -> bool:
        """判断是否需要继续执行（多轮工具使用）"""
        # 如果有新的 tool_calls，继续执行
        return len(response.tool_calls) > 0

    async def _reflect(
        self,
        context: AgentContext,
        response: AgentResponse,
    ) -> Dict[str, Any]:
        """反思：评估执行质量和改进建议"""
        # 调用 LLM 进行反思
        reflection_prompt = f"""
请评估以下任务执行的质量:

任务：{context.task}
响应：{response.content}

请从以下方面评估:
1. 是否完整回答了问题？
2. 信息是否准确？
3. 是否有改进空间？

评估:
"""
        # 简化实现
        return {
            "quality_score": 4,
            "suggestions": ["可以增加更多示例"],
        }

    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
        }
