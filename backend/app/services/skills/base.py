"""
Skills 市场核心服务
"""
from typing import Dict, Any, List, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from dataclasses import dataclass
import importlib
import asyncio

from ...core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillDefinition:
    """Skill 定义"""
    name: str
    description: str
    category: str
    version: str
    author: str
    inputs: List[Dict]
    outputs: List[Dict]
    config_schema: Dict[str, Any]
    tags: List[str]


class BaseSkill(ABC):
    """
    Skill 基类

    所有 Skill 必须实现以下接口:
    - execute(): 执行 Skill
    - get_definition(): 获取 Skill 定义
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._execution_count = 0

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Any:
        """
        执行 Skill

        Args:
            params: 执行参数

        Returns:
            执行结果
        """
        pass

    def get_definition(self) -> SkillDefinition:
        """获取 Skill 定义"""
        raise NotImplementedError

    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置 Schema"""
        return self.get_definition().config_schema

    def get_input_schema(self) -> Dict[str, Any]:
        """获取输入 Schema"""
        return {"type": "object", "properties": {i["name"]: i for i in self.get_definition().inputs}}

    def get_output_schema(self) -> Dict[str, Any]:
        """获取输出 Schema"""
        return {"type": "object", "properties": {o["name"]: o for o in self.get_definition().outputs}}

    @property
    def execution_count(self) -> int:
        """获取执行次数"""
        return self._execution_count

    def _increment_execution_count(self):
        """增加执行次数"""
        self._execution_count += 1

    async def validate_input(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证输入参数

        Returns:
            (是否有效，错误消息)
        """
        input_schema = self.get_input_schema()
        required_inputs = [i["name"] for i in self.get_definition().inputs if i.get("required", False)]

        for required in required_inputs:
            if required not in params:
                return False, f"缺少必需参数：{required}"

        return True, None


class PythonSkill(BaseSkill):
    """
    Python 实现的 Skill

    通过指定模块路径动态加载 Skill 实现
    """

    def __init__(self, module_path: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.module_path = module_path
        self._skill_instance = None
        self._load_skill()

    def _load_skill(self):
        """动态加载 Skill 模块"""
        try:
            module = importlib.import_module(self.module_path)
            if hasattr(module, "Skill"):
                self._skill_instance = module.Skill(config=self.config)
                logger.info(f"Skill loaded from {self.module_path}")
            else:
                logger.error(f"Skill class not found in {self.module_path}")
        except Exception as e:
            logger.error(f"Failed to load skill from {self.module_path}: {e}")
            raise

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行 Skill"""
        if not self._skill_instance:
            raise RuntimeError("Skill not loaded")

        self._increment_execution_count()
        return await self._skill_instance.execute(params)

    def get_definition(self) -> SkillDefinition:
        """获取 Skill 定义"""
        if self._skill_instance and hasattr(self._skill_instance, "get_definition"):
            return self._skill_instance.get_definition()
        raise NotImplementedError


class HTTPSkill(BaseSkill):
    """
    HTTP 服务实现的 Skill

    通过 HTTP 调用外部服务执行 Skill
    """

    def __init__(self, endpoint_url: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.endpoint_url = endpoint_url
        self.timeout = config.get("timeout", 30) if config else 30

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行 Skill"""
        import aiohttp

        self._increment_execution_count()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.endpoint_url,
                    json={"params": params, "config": self.config},
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        raise RuntimeError(f"HTTP Skill execution failed: {error}")
            except asyncio.TimeoutError:
                raise RuntimeError(f"HTTP Skill execution timed out after {self.timeout}s")


class MCPSkill(BaseSkill):
    """
    MCP 连接器实现的 Skill

    通过 MCP 连接器执行 Skill
    """

    def __init__(self, connector_id: str, action: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.connector_id = connector_id
        self.action = action

    async def execute(self, params: Dict[str, Any]) -> Any:
        """执行 Skill"""
        from ..mcp.registry import get_registry

        self._increment_execution_count()

        registry = get_registry()
        connector = registry.get_connector(self.connector_id)

        if not connector:
            raise RuntimeError(f"Connector not found: {self.connector_id}")

        return await connector.execute(self.action, params)


class SkillRegistry:
    """
    Skill 注册表

    功能:
    - Skill 注册/注销
    - Skill 查找
    - Skill 执行
    """

    _instance: Optional["SkillRegistry"] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._skill_metadata = {}
        return cls._instance

    def register(
        self,
        name: str,
        skill: BaseSkill,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        注册 Skill

        Args:
            name: Skill 名称
            skill: Skill 实例
            metadata: 元数据（分类、标签等）
        """
        self._skills[name] = skill
        self._skill_metadata[name] = metadata or {}
        logger.info(f"Skill registered: {name}")

    def unregister(self, name: str) -> bool:
        """注销 Skill"""
        if name in self._skills:
            del self._skills[name]
            del self._skill_metadata[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseSkill]:
        """获取 Skill"""
        return self._skills.get(name)

    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有 Skills

        Args:
            category: 可选的分类过滤

        Returns:
            Skill 信息列表
        """
        skills = []
        for name, skill in self._skills.items():
            metadata = self._skill_metadata.get(name, {})
            if category and metadata.get("category") != category:
                continue

            try:
                definition = skill.get_definition()
                skills.append({
                    "name": name,
                    "definition": definition.__dict__ if hasattr(definition, "__dict__") else {},
                    "metadata": metadata,
                    "execution_count": skill.execution_count,
                })
            except Exception as e:
                logger.error(f"Error getting skill definition for {name}: {e}")
                skills.append({
                    "name": name,
                    "definition": {},
                    "metadata": metadata,
                    "execution_count": skill.execution_count,
                })

        return skills

    async def execute(self, name: str, params: Dict[str, Any]) -> Any:
        """
        执行 Skill

        Args:
            name: Skill 名称
            params: 执行参数

        Returns:
            执行结果
        """
        skill = self.get(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")

        # 验证输入
        is_valid, error_msg = await skill.validate_input(params)
        if not is_valid:
            raise ValueError(error_msg)

        return await skill.execute(params)

    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计"""
        total_executions = sum(s.execution_count for s in self._skills.values())
        return {
            "total_skills": len(self._skills),
            "total_executions": total_executions,
            "skills": list(self._skills.keys()),
        }


# 全局注册表实例
registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    """获取全局注册表"""
    return registry


def auto_register_builtin_skills() -> None:
    """
    自动注册所有内置 Skills

    在应用启动时调用此函数
    """
    # 延迟导入内置 Skills
    from .builtin_skills import register_builtin_skills

    register_builtin_skills(registry)
    logger.info("All built-in skills registered")
