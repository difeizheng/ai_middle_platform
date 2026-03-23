"""
MCP 连接器注册表
"""
from typing import Dict, Any, Optional, List, Type
from .base import MCPConnector, ConnectorConfig, ConnectorStatus

from ...core.logger import get_logger

logger = get_logger(__name__)


class ConnectorRegistry:
    """
    MCP 连接器注册表

    功能:
    - 连接器类型注册
    - 连接器实例管理
    - 连接器查找
    """

    _instance: Optional["ConnectorRegistry"] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connector_types = {}
            cls._instance._connectors = {}
        return cls._instance

    def register_type(
        self,
        name: str,
        connector_class: Type[MCPConnector],
    ) -> None:
        """
        注册连接器类型

        Args:
            name: 类型名称
            connector_class: 连接器类
        """
        self._connector_types[name] = connector_class
        logger.info(f"Connector type registered: {name}")

    def unregister_type(self, name: str) -> bool:
        """
        注销连接器类型

        Args:
            name: 类型名称

        Returns:
            bool: 是否成功
        """
        if name in self._connector_types:
            del self._connector_types[name]
            return True
        return False

    def get_connector_type(self, name: str) -> Optional[Type[MCPConnector]]:
        """
        获取连接器类型

        Args:
            name: 类型名称

        Returns:
            连接器类
        """
        return self._connector_types.get(name)

    def list_connector_types(self) -> List[str]:
        """
        列出所有注册的连接器类型

        Returns:
            类型名称列表
        """
        return list(self._connector_types.keys())

    def create_connector(
        self,
        instance_id: str,
        connector_type: str,
        config: ConnectorConfig,
    ) -> Optional[MCPConnector]:
        """
        创建连接器实例

        Args:
            instance_id: 实例 ID
            connector_type: 连接器类型
            config: 连接器配置

        Returns:
            连接器实例
        """
        connector_class = self.get_connector_type(connector_type)
        if not connector_class:
            logger.error(f"Connector type not found: {connector_type}")
            return None

        connector = connector_class(config)
        self._connectors[instance_id] = connector
        logger.info(f"Connector instance created: {instance_id} ({connector_type})")
        return connector

    def get_connector(self, instance_id: str) -> Optional[MCPConnector]:
        """
        获取连接器实例

        Args:
            instance_id: 实例 ID

        Returns:
            连接器实例
        """
        return self._connectors.get(instance_id)

    def remove_connector(self, instance_id: str) -> bool:
        """
        移除连接器实例

        Args:
            instance_id: 实例 ID

        Returns:
            bool: 是否成功
        """
        if instance_id in self._connectors:
            del self._connectors[instance_id]
            logger.info(f"Connector instance removed: {instance_id}")
            return True
        return False

    def list_connectors(self) -> List[Dict[str, Any]]:
        """
        列出所有连接器实例

        Returns:
            连接器状态列表
        """
        return [
            connector.get_status()
            for connector in self._connectors.values()
        ]

    async def connect_all(self) -> Dict[str, bool]:
        """
        连接所有连接器

        Returns:
            连接结果字典
        """
        results = {}
        for instance_id, connector in self._connectors.items():
            try:
                success = await connector.connect()
                results[instance_id] = success
            except Exception as e:
                logger.error(f"Failed to connect {instance_id}: {e}")
                results[instance_id] = False
        return results

    async def disconnect_all(self) -> Dict[str, bool]:
        """
        断开所有连接器

        Returns:
            断开结果字典
        """
        results = {}
        for instance_id, connector in self._connectors.items():
            try:
                success = await connector.disconnect()
                results[instance_id] = success
            except Exception as e:
                logger.error(f"Failed to disconnect {instance_id}: {e}")
                results[instance_id] = False
        return results

    async def health_check_all(self) -> Dict[str, bool]:
        """
        检查所有连接器健康状态

        Returns:
            健康状态字典
        """
        results = {}
        for instance_id, connector in self._connectors.items():
            try:
                healthy = await connector.health_check()
                results[instance_id] = healthy
            except Exception as e:
                logger.error(f"Health check failed for {instance_id}: {e}")
                results[instance_id] = False
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计"""
        return {
            "connector_types": len(self._connector_types),
            "connector_instances": len(self._connectors),
            "types": list(self._connector_types.keys()),
        }


# 全局注册表实例
registry = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    """获取全局注册表"""
    return registry


def auto_register_types() -> None:
    """
    自动注册所有内置连接器类型

    在应用启动时调用此函数
    """
    # 延迟导入，避免循环依赖
    from .mysql import MySQLConnector
    from .postgresql import PostgreSQLConnector
    from .http import HTTPConnector
    from .redis import RedisConnector
    from .file import FileConnector
    from .kafka import KafkaConnector
    from .mongodb import MongoDBConnector

    # 注册所有内置连接器
    registry.register_type("mysql", MySQLConnector)
    registry.register_type("postgresql", PostgreSQLConnector)
    registry.register_type("http", HTTPConnector)
    registry.register_type("redis", RedisConnector)
    registry.register_type("file", FileConnector)
    registry.register_type("kafka", KafkaConnector)
    registry.register_type("mongodb", MongoDBConnector)

    logger.info("All built-in connector types registered")
