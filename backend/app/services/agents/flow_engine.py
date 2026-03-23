"""
流程引擎 - 多智能体协作和工作流执行
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ...core.logger import get_logger

logger = get_logger(__name__)


class FlowStatus(Enum):
    """流程状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(Enum):
    """节点类型"""
    INPUT = "input"
    OUTPUT = "output"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    TRANSFORM = "transform"


@dataclass
class NodeContext:
    """节点执行上下文"""
    node_id: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class FlowExecutionResult:
    """流程执行结果"""
    flow_id: int
    execution_id: str
    status: FlowStatus
    outputs: Dict[str, Any]
    logs: List[Dict]
    duration_ms: int
    error_message: Optional[str] = None


class FlowEngine:
    """
    流程执行引擎

    功能:
    - 解析流程定义（节点和边）
    - 按拓扑顺序执行节点
    - 处理条件分支和循环
    - 支持并行执行
    - 错误处理和恢复
    """

    def __init__(
        self,
        flow_id: int,
        name: str,
        nodes: List[Dict],
        edges: List[Dict],
        variables: List[Dict] = None,
    ):
        self.flow_id = flow_id
        self.name = name
        self.nodes = nodes
        self.edges = edges
        self.variables = variables or []

        # 构建节点图
        self.node_map = {node["id"]: node for node in nodes}
        self.adjacency = self._build_adjacency()

    def _build_adjacency(self) -> Dict[str, List[Dict]]:
        """构建邻接表"""
        adj = {node["id"]: [] for node in self.nodes}

        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]
            if source in adj:
                adj[source].append({
                    "target": target,
                    "edge": edge,
                })

        return adj

    async def execute(
        self,
        inputs: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
    ) -> FlowExecutionResult:
        """
        执行流程

        Args:
            inputs: 输入数据
            variables: 流程变量

        Returns:
            FlowExecutionResult 执行结果
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Flow execution started: {execution_id}")

        # 初始化节点上下文
        node_contexts = {
            node["id"]: NodeContext(node_id=node["id"])
            for node in self.nodes
        }

        # 初始化流程变量
        flow_vars = self._init_variables(variables)
        flow_vars.update(inputs)

        # 执行日志
        logs = []

        try:
            # 拓扑排序确定执行顺序
            execution_order = self._topological_sort()

            # 按顺序执行节点
            for node_id in execution_order:
                node = self.node_map[node_id]
                context = node_contexts[node_id]

                # 收集上游输出作为输入
                context.inputs = self._collect_inputs(node_id, node_contexts)
                context.inputs.update(flow_vars)

                # 执行节点
                logs.append({
                    "timestamp": time.time(),
                    "node_id": node_id,
                    "event": "node_start",
                    "node_type": node["type"],
                })

                context.start_time = time.time()
                context.status = "running"

                result = await self._execute_node(node, context)

                context.outputs = result
                context.status = "completed"
                context.end_time = time.time()

                logs.append({
                    "timestamp": time.time(),
                    "node_id": node_id,
                    "event": "node_completed",
                    "duration_ms": (context.end_time - context.start_time) * 1000,
                })

                # 处理条件分支
                if node["type"] == "condition":
                    branch = self._evaluate_condition(result, node)
                    if branch:
                        # 跳过不需要的分支
                        self._skip_branch(node_id, branch, node_contexts)

            # 收集最终输出
            outputs = self._collect_outputs(node_contexts)

            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            logger.info(f"Flow execution completed: {execution_id} in {duration_ms}ms")

            return FlowExecutionResult(
                flow_id=self.flow_id,
                execution_id=execution_id,
                status=FlowStatus.COMPLETED,
                outputs=outputs,
                logs=logs,
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Flow execution failed: {e}", exc_info=True)
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            return FlowExecutionResult(
                flow_id=self.flow_id,
                execution_id=execution_id,
                status=FlowStatus.FAILED,
                outputs={},
                logs=logs,
                duration_ms=duration_ms,
                error_message=str(e),
            )

    async def _execute_node(
        self,
        node: Dict,
        context: NodeContext,
    ) -> Dict[str, Any]:
        """执行单个节点"""
        node_type = node["type"]
        node_data = node.get("data", {})

        if node_type == "input":
            return self._execute_input(node, context)

        elif node_type == "output":
            return self._execute_output(node, context)

        elif node_type == "agent":
            return await self._execute_agent(node, context)

        elif node_type == "tool":
            return await self._execute_tool(node, context)

        elif node_type == "condition":
            return self._execute_condition(node, context)

        elif node_type == "loop":
            return await self._execute_loop(node, context)

        elif node_type == "parallel":
            return await self._execute_parallel(node, context)

        elif node_type == "transform":
            return self._execute_transform(node, context)

        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def _execute_input(self, node: Dict, context: NodeContext) -> Dict:
        """输入节点"""
        output_name = node.get("data", {}).get("output_name", "output")
        return {output_name: context.inputs.get("input", "")}

    def _execute_output(self, node: Dict, context: NodeContext) -> Dict:
        """输出节点"""
        # 输出节点通常不产生新输出，只是标记流程结束
        return {"final": context.inputs}

    async def _execute_agent(self, node: Dict, context: NodeContext) -> Dict:
        """智能体节点"""
        from .engine import AgentEngine

        agent_id = node.get("data", {}).get("agent_id")
        if not agent_id:
            raise ValueError(f"Agent node {node['id']} missing agent_id")

        # 从数据库加载智能体配置（简化实现）
        agent_config = {
            "agent_id": agent_id,
            "name": f"Agent-{agent_id}",
            "role": "executor",
            "config": {},
            "tools": [],
        }

        engine = AgentEngine(**agent_config)

        # 获取输入
        task = context.inputs.get("input", str(context.inputs))

        # 执行智能体
        response = await engine.execute(task)

        return {"output": response.content, "metadata": response.metadata}

    async def _execute_tool(self, node: Dict, context: NodeContext) -> Dict:
        """工具节点"""
        from .tools import ToolRegistry

        tool_id = node.get("data", {}).get("tool_id")
        if not tool_id:
            raise ValueError(f"Tool node {node['id']} missing tool_id")

        registry = ToolRegistry()

        # 获取输入作为工具参数
        params = context.inputs.get("params", context.inputs)

        # 执行工具
        result = await registry.execute(tool_id, params)

        return {"result": result}

    def _execute_condition(self, node: Dict, context: NodeContext) -> Dict:
        """条件节点"""
        condition = node.get("data", {}).get("condition", "")
        result = self._evaluate_condition_str(condition, context.inputs)

        return {"condition_result": result, "branch": "true" if result else "false"}

    async def _execute_loop(self, node: Dict, context: NodeContext) -> Dict:
        """循环节点"""
        # 简化实现：执行一次
        # 实际应该根据循环条件多次执行
        return {"iteration": 1, "output": context.inputs}

    async def _execute_parallel(self, node: Dict, context: NodeContext) -> Dict:
        """并行节点"""
        # 并行执行多个子流程
        tasks = node.get("data", {}).get("tasks", [])

        results = await asyncio.gather(
            *[self._execute_task(task, context) for task in tasks]
        )

        return {"results": results}

    def _execute_transform(self, node: Dict, context: NodeContext) -> Dict:
        """转换节点"""
        transform = node.get("data", {}).get("transform", "")

        # 简单变量替换
        output = transform
        for key, value in context.inputs.items():
            output = output.replace(f"{{{key}}}", str(value))

        return {"output": output}

    async def _execute_task(self, task: Dict, context: NodeContext) -> Any:
        """执行子任务"""
        # 简化实现
        return {"task": task, "input": context.inputs}

    def _collect_inputs(
        self,
        node_id: str,
        contexts: Dict[str, NodeContext],
    ) -> Dict[str, Any]:
        """收集上游节点的输出作为输入"""
        inputs = {}

        for edge in self.edges:
            if edge["target"] == node_id:
                source_id = edge["source"]
                if source_id in contexts:
                    source_outputs = contexts[source_id].outputs
                    handle = edge.get("sourceHandle", "output")
                    if handle in source_outputs:
                        inputs[handle] = source_outputs[handle]

        return inputs

    def _collect_outputs(
        self,
        contexts: Dict[str, NodeContext],
    ) -> Dict[str, Any]:
        """收集最终输出"""
        outputs = {}

        for node_id, context in contexts.items():
            if context.status == "completed":
                node = self.node_map.get(node_id)
                if node and node["type"] == "output":
                    outputs[node_id] = context.outputs

        return outputs

    def _topological_sort(self) -> List[str]:
        """拓扑排序确定执行顺序"""
        # 计算入度
        in_degree = {node["id"]: 0 for node in self.nodes}

        for edge in self.edges:
            target = edge["target"]
            if target in in_degree:
                in_degree[target] += 1

        # Kahn 算法
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for neighbor in self.adjacency.get(node_id, []):
                target = neighbor["target"]
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)

        if len(result) != len(self.nodes):
            raise ValueError("Graph has cycles")

        return result

    def _init_variables(self, variables: Optional[Dict]) -> Dict[str, Any]:
        """初始化流程变量"""
        flow_vars = {}

        for var_def in self.variables:
            name = var_def.get("name")
            default = var_def.get("default")
            flow_vars[name] = default

        if variables:
            flow_vars.update(variables)

        return flow_vars

    def _evaluate_condition_str(self, condition: str, context: Dict) -> bool:
        """评估条件字符串"""
        # 安全地评估条件表达式
        # 简化实现：支持简单比较
        try:
            # 替换变量
            for key, value in context.items():
                condition = condition.replace(f"{{{key}}}", repr(value))

            # 安全评估
            return eval(condition, {"__builtins__": {}}, {})
        except Exception:
            return False

    def _evaluate_condition(self, result: Dict, node: Dict) -> Optional[str]:
        """评估条件结果"""
        condition_result = result.get("condition_result", False)
        return "true" if condition_result else "false"

    def _skip_branch(
        self,
        node_id: str,
        branch: str,
        contexts: Dict[str, NodeContext],
    ) -> None:
        """跳过不需要的分支"""
        # 标记不需要的分支节点为 skipped
        # 简化实现
        pass

    def get_flow_definition(self) -> Dict[str, Any]:
        """获取流程定义"""
        return {
            "flow_id": self.flow_id,
            "name": self.name,
            "nodes": self.nodes,
            "edges": self.edges,
            "variables": self.variables,
        }
