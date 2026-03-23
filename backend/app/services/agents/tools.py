"""
智能体工具注册表和内置工具
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib

from ...core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: str
    inputs: List[Dict]
    outputs: List[Dict]
    config: Dict[str, Any]


class BaseTool(ABC):
    """工具基类"""

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行工具"""
        pass

    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        raise NotImplementedError


class WebSearchTool(BaseTool):
    """网页搜索工具"""

    def __init__(self, search_engine: str = "google", api_key: Optional[str] = None):
        self.search_engine = search_engine
        self.api_key = api_key

    async def execute(self, params: Dict[str, Any]) -> List[Dict]:
        """
        执行网页搜索

        Args:
            params: {
                "query": str,  # 搜索关键词
                "num_results": int,  # 返回数量
            }
        """
        query = params.get("query", "")
        num_results = params.get("num_results", 10)

        if not query:
            return []

        # 简化实现：返回模拟结果
        # 实际应该调用搜索 API
        return [
            {"title": f"搜索结果 {i}", "url": f"https://example.com/{i}", "snippet": f"关于{query}的信息"}
            for i in range(1, min(num_results + 1, 6))
        ]

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="在互联网上搜索信息",
            category="search",
            inputs=[
                {"name": "query", "type": "string", "required": True, "description": "搜索关键词"},
                {"name": "num_results", "type": "number", "required": False, "description": "返回数量", "default": 10},
            ],
            outputs=[{"name": "results", "type": "array", "description": "搜索结果列表"}],
            config={"search_engine": self.search_engine},
        )


class CodeExecutorTool(BaseTool):
    """代码执行工具"""

    def __init__(self, sandbox: str = "local"):
        self.sandbox = sandbox  # local, docker, remote

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行代码

        Args:
            params: {
                "code": str,  # 代码内容
                "language": str,  # 编程语言
                "timeout": int,  # 超时时间（秒）
            }
        """
        code = params.get("code", "")
        language = params.get("language", "python")
        timeout = params.get("timeout", 30)

        if not code:
            return {"error": "代码不能为空"}

        # 简化实现：使用 eval/exec 执行 Python 代码
        # 生产环境应该使用沙箱
        if language == "python":
            try:
                # 捕获输出
                import io
                import sys

                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

                # 执行代码
                exec_globals = {}
                exec(code, exec_globals)

                output = sys.stdout.getvalue()
                sys.stdout = old_stdout

                return {
                    "success": True,
                    "output": output,
                    "variables": {k: v for k, v in exec_globals.items() if not k.startswith("_")},
                }
            except Exception as e:
                sys.stdout = old_stdout
                return {"success": False, "error": str(e)}
        else:
            return {"error": f"不支持的语言：{language}"}

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_executor",
            description="执行代码（支持 Python）",
            category="code",
            inputs=[
                {"name": "code", "type": "string", "required": True, "description": "代码内容"},
                {"name": "language", "type": "string", "required": False, "description": "编程语言", "default": "python"},
                {"name": "timeout", "type": "number", "required": False, "description": "超时时间", "default": 30},
            ],
            outputs=[{"name": "result", "type": "object", "description": "执行结果"}],
            config={"sandbox": self.sandbox},
        )


class CalculatorTool(BaseTool):
    """计算工具"""

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行计算

        Args:
            params: {
                "expression": str,  # 数学表达式
            }
        """
        expression = params.get("expression", "")

        if not expression:
            return {"error": "表达式不能为空"}

        try:
            # 安全计算
            import ast
            import operator

            # 定义支持的操作
            OPERATORS = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }

            def eval_node(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    left = eval_node(node.left)
                    right = eval_node(node.right)
                    return OPERATORS[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = eval_node(node.operand)
                    return OPERATORS[type(node.op)](operand)
                else:
                    raise TypeError(f"Unsupported node type: {type(node)}")

            tree = ast.parse(expression, mode="eval")
            result = eval_node(tree.body)

            return {"result": result, "expression": expression}

        except Exception as e:
            return {"error": str(e)}

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="执行数学计算",
            category="compute",
            inputs=[
                {"name": "expression", "type": "string", "required": True, "description": "数学表达式"},
            ],
            outputs=[{"name": "result", "type": "number", "description": "计算结果"}],
            config={},
        )


class HTTPRequestTool(BaseTool):
    """HTTP 请求工具"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            params: {
                "url": str,
                "method": str,  # GET, POST, PUT, DELETE
                "headers": dict,
                "body": dict,
                "timeout": int,
            }
        """
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body")
        timeout = params.get("timeout", self.timeout)

        if not url:
            return {"error": "URL 不能为空"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    content = await response.text()
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = content

                    return {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "body": data,
                    }

        except Exception as e:
            return {"error": str(e)}

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="http_request",
            description="发送 HTTP 请求",
            category="api",
            inputs=[
                {"name": "url", "type": "string", "required": True, "description": "请求 URL"},
                {"name": "method", "type": "string", "required": False, "description": "请求方法", "default": "GET"},
                {"name": "headers", "type": "object", "required": False, "description": "请求头"},
                {"name": "body", "type": "object", "required": False, "description": "请求体"},
                {"name": "timeout", "type": "number", "required": False, "description": "超时时间", "default": 30},
            ],
            outputs=[{"name": "response", "type": "object", "description": "HTTP 响应"}],
            config={"default_timeout": self.timeout},
        )


class DocumentParserTool(BaseTool):
    """文档解析工具"""

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析文档

        Args:
            params: {
                "file_path": str,
                "file_type": str,  # pdf, docx, xlsx, pptx, txt, md
            }
        """
        file_path = params.get("file_path", "")
        file_type = params.get("file_type", "txt")

        if not file_path:
            return {"error": "文件路径不能为空"}

        try:
            from ...services.parser import DocumentParser

            parser = DocumentParser()
            result = parser.parse(file_path)

            if result.success:
                return {
                    "content": result.content,
                    "page_count": result.page_count,
                    "metadata": result.metadata,
                }
            else:
                return {"error": result.error}

        except Exception as e:
            return {"error": str(e)}

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="document_parser",
            description="解析文档（PDF/Word/Excel/PPT/TXT/MD）",
            category="document",
            inputs=[
                {"name": "file_path", "type": "string", "required": True, "description": "文件路径"},
                {"name": "file_type", "type": "string", "required": False, "description": "文件类型"},
            ],
            outputs=[{"name": "content", "type": "string", "description": "文档内容"}],
            config={},
        )


class ToolRegistry:
    """
    工具注册表
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具"""
        self.register(WebSearchTool())
        self.register(CodeExecutorTool())
        self.register(CalculatorTool())
        self.register(HTTPRequestTool())
        self.register(DocumentParserTool())

    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        """注册工具"""
        tool_name = name or tool.get_definition().name
        self._tools[tool_name] = tool
        logger.info(f"Tool registered: {tool_name}")

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [tool.get_definition().__dict__ for tool in self._tools.values()]

    async def execute(self, name: str, params: Dict[str, Any]) -> Any:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return await tool.execute(params)


# 全局工具注册表实例
_builtin_tools: Optional[ToolRegistry] = None


def get_builtin_tools() -> ToolRegistry:
    """获取内置工具注册表"""
    global _builtin_tools
    if _builtin_tools is None:
        _builtin_tools = ToolRegistry()
    return _builtin_tools


# 便捷函数
def register_tool(tool: BaseTool) -> None:
    """注册工具"""
    get_builtin_tools().register(tool)


def get_tool(name: str) -> Optional[BaseTool]:
    """获取工具"""
    return get_builtin_tools().get(name)


def list_tools() -> List[Dict]:
    """列出所有工具"""
    return get_builtin_tools().list_tools()
