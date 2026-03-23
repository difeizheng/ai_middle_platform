"""
Redis 连接器
"""
from typing import Any, Dict, List, Optional
import json

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class RedisConnector(MCPConnector):
    """
    Redis 连接器

    支持的操作:
    - get: 获取键值
    - set: 设置键值
    - delete: 删除键
    - exists: 检查键是否存在
    - keys: 获取匹配的键列表
    - hget: 获取哈希字段
    - hset: 设置哈希字段
    - lpush: 列表左推入
    - rpop: 列表右弹出
    - publish: 发布消息
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._redis = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="get",
                description="获取键值",
                params_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"},
                    },
                    "required": ["key"],
                },
                response_schema={"type": ["string", "null"]},
            ),
            ActionDefinition(
                name="set",
                description="设置键值",
                params_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"},
                        "value": {"type": "string", "description": "值"},
                        "expire": {"type": "number", "description": "过期时间（秒）"},
                    },
                    "required": ["key", "value"],
                },
                response_schema={"type": "boolean"},
            ),
            ActionDefinition(
                name="delete",
                description="删除键",
                params_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"},
                    },
                    "required": ["key"],
                },
                response_schema={"type": "integer"},
            ),
            ActionDefinition(
                name="hget",
                description="获取哈希字段",
                params_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "哈希键名"},
                        "field": {"type": "string", "description": "字段名"},
                    },
                    "required": ["key", "field"],
                },
                response_schema={"type": ["string", "null"]},
            ),
            ActionDefinition(
                name="hset",
                description="设置哈希字段",
                params_schema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "哈希键名"},
                        "field": {"type": "string", "description": "字段名"},
                        "value": {"type": "string", "description": "值"},
                    },
                    "required": ["key", "field", "value"],
                },
                response_schema={"type": "integer"},
            ),
        ]

    async def connect(self) -> bool:
        """建立 Redis 连接"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 导入 redis.asyncio
            import redis.asyncio as redis

            # 创建连接
            self._redis = redis.Redis(
                host=self.config.host or "localhost",
                port=self.config.port or 6379,
                password=self.config.password,
                db=int(self.config.database) if self.config.database else 0,
                decode_responses=True,
                socket_connect_timeout=self.config.timeout,
                socket_timeout=self.config.timeout,
            )

            # 测试连接
            await self._redis.ping()

            self.status = ConnectorStatus.ACTIVE
            logger.info(f"Redis connector connected: {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"Redis connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开 Redis 连接"""
        try:
            self.status = ConnectorStatus.DISCONNECTING

            if self._redis:
                await self._redis.close()
                self._redis = None

            self.status = ConnectorStatus.INACTIVE
            logger.info("Redis connector disconnected")
            return True

        except Exception as e:
            logger.error(f"Redis disconnect error: {e}")
            return False

    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Any:
        """执行操作"""
        self._update_last_used()

        if action == "get":
            return await self._get(params.get("key"))
        elif action == "set":
            return await self._set(
                params.get("key"),
                params.get("value"),
                params.get("expire"),
            )
        elif action == "delete":
            return await self._delete(params.get("key"))
        elif action == "hget":
            return await self._hget(params.get("key"), params.get("field"))
        elif action == "hset":
            return await self._hset(
                params.get("key"),
                params.get("field"),
                params.get("value"),
            )
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _get(self, key: str) -> Optional[str]:
        """获取键值"""
        if not self._redis:
            raise RuntimeError("Connector not connected")

        value = await self._redis.get(key)
        # 尝试解析 JSON
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return None

    async def _set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
    ) -> bool:
        """设置键值"""
        if not self._redis:
            raise RuntimeError("Connector not connected")

        # 序列化值
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        else:
            value = str(value)

        if expire:
            return await self._redis.setex(key, expire, value)
        else:
            return await self._redis.set(key, value)

    async def _delete(self, key: str) -> int:
        """删除键"""
        if not self._redis:
            raise RuntimeError("Connector not connected")

        return await self._redis.delete(key)

    async def _hget(self, key: str, field: str) -> Optional[str]:
        """获取哈希字段"""
        if not self._redis:
            raise RuntimeError("Connector not connected")

        return await self._redis.hget(key, field)

    async def _hset(self, key: str, field: str, value: Any) -> int:
        """设置哈希字段"""
        if not self._redis:
            raise RuntimeError("Connector not connected")

        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        else:
            value = str(value)

        return await self._redis.hset(key, field, value)

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._redis:
                return False

            result = await self._redis.ping()
            return result is True or result == b"OK" or result == "OK"

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def get_actions(self) -> List[Dict]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
