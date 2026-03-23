"""
MCP 连接器基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import json
import time

from ...core.logger import get_logger

logger = get_logger(__name__)


class ConnectorType(Enum):
    """连接器类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    HTTP = "http"
    REDIS = "redis"
    FILE = "file"
    KAFKA = "kafka"
    MONGODB = "mongodb"
    ELASTICSEARCH = "elasticsearch"
    CUSTOM = "custom"


class ConnectorStatus(Enum):
    """连接器状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"


@dataclass
class ConnectorConfig:
    """连接器配置"""
    name: str
    connector_type: ConnectorType
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    ssl: bool = False
    timeout: int = 30
    max_connections: int = 10
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorConfig":
        """从字典创建配置"""
        return cls(
            name=data.get("name", "default"),
            connector_type=ConnectorType(data.get("type", "custom")),
            host=data.get("host"),
            port=data.get("port"),
            username=data.get("username"),
            password=data.get("password"),
            database=data.get("database"),
            ssl=data.get("ssl", False),
            timeout=data.get("timeout", 30),
            max_connections=data.get("max_connections", 10),
            extra=data.get("extra", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含密码）"""
        return {
            "name": self.name,
            "type": self.connector_type.value,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "database": self.database,
            "ssl": self.ssl,
            "timeout": self.timeout,
            "max_connections": self.max_connections,
            "extra": self.extra,
        }


class MCPConnector(ABC):
    """
    MCP 连接器基类

    所有连接器必须实现以下接口:
    - connect(): 建立连接
    - disconnect(): 断开连接
    - execute(): 执行操作
    - health_check(): 健康检查
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.status = ConnectorStatus.INACTIVE
        self._connection = None
        self._created_at = time.time()
        self._last_used_at = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立连接

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开连接

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Any:
        """
        执行操作

        Args:
            action: 操作名称
            params: 操作参数

        Returns:
            操作结果
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 是否健康
        """
        pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()

    def get_status(self) -> Dict[str, Any]:
        """获取连接器状态"""
        return {
            "name": self.config.name,
            "type": self.config.connector_type.value,
            "status": self.status.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "created_at": self._created_at,
            "last_used_at": self._last_used_at,
        }

    def _update_last_used(self):
        """更新最后使用时间"""
        self._last_used_at = time.time()


class ActionDefinition:
    """操作定义"""

    def __init__(
        self,
        name: str,
        description: str,
        params_schema: Dict[str, Any],
        response_schema: Dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.params_schema = params_schema
        self.response_schema = response_schema

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "params_schema": self.params_schema,
            "response_schema": self.response_schema,
        }
