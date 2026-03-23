"""
Kafka 连接器
"""
from typing import Any, Dict, List, Optional
import asyncio
import json

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.errors import KafkaError
except ImportError:
    AIOKafkaProducer = None
    AIOKafkaConsumer = None

from ...core.logger import get_logger

logger = get_logger(__name__)


class KafkaConnector(MCPConnector):
    """
    Kafka 连接器

    支持的操作:
    - produce: 发送消息到 Kafka
    - consume: 从 Kafka 消费消息
    - get_topics: 获取所有主题
    - get_topic_info: 获取主题信息
    - create_topic: 创建主题
    """

    def __init__(self, config: ConnectorConfig):
        if AIOKafkaProducer is None:
            raise ImportError("aiokafka is not installed. Please install it: pip install aiokafka")

        super().__init__(config)
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="produce",
                description="发送消息到 Kafka",
                params_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "主题名"},
                        "message": {"type": "string", "description": "消息内容"},
                        "key": {"type": "string", "description": "消息键"},
                        "partition": {"type": "integer", "description": "分区"},
                        "headers": {"type": "object", "description": "消息头"},
                    },
                    "required": ["topic", "message"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "partition": {"type": "integer"},
                        "offset": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="consume",
                description="从 Kafka 消费消息",
                params_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "主题名"},
                        "timeout": {"type": "integer", "description": "超时时间（毫秒）"},
                        "max_messages": {"type": "integer", "description": "最大消息数"},
                        "group_id": {"type": "string", "description": "消费者组 ID"},
                        "auto_offset_reset": {
                            "type": "string",
                            "enum": ["earliest", "latest"],
                            "description": "偏移量重置策略",
                        },
                    },
                    "required": ["topic"],
                },
                response_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "partition": {"type": "integer"},
                            "offset": {"type": "integer"},
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                },
            ),
            ActionDefinition(
                name="get_topics",
                description="获取所有主题",
                params_schema={"type": "object"},
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
            ActionDefinition(
                name="get_topic_info",
                description="获取主题信息",
                params_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "主题名"},
                    },
                    "required": ["topic"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "partitions": {"type": "integer"},
                        "replication_factor": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="create_topic",
                description="创建主题",
                params_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "主题名"},
                        "partitions": {"type": "integer", "description": "分区数"},
                        "replication_factor": {"type": "integer", "description": "副本数"},
                    },
                    "required": ["topic"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                    },
                },
            ),
        ]

    async def connect(self) -> bool:
        """建立 Kafka 连接"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 解析 bootstrap_servers
            if self.config.host:
                port = self.config.port or 9092
                bootstrap_servers = [f"{self.config.host}:{port}"]
            else:
                bootstrap_servers = ["localhost:9092"]

            # 额外的 Kafka 配置
            extra_config = self.config.extra or {}

            # 创建生产者
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                client_id=self.config.name,
                acks="all",
                retries=3,
                request_timeout_ms=self.config.timeout * 1000,
                **extra_config,
            )
            await self._producer.start()

            self.status = ConnectorStatus.ACTIVE
            logger.info(f"Kafka connector '{self.config.name}' connected successfully")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"Kafka connector '{self.config.name}' connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开 Kafka 连接"""
        try:
            self.status = ConnectorStatus.DISCONNECTING

            if self._producer:
                await self._producer.stop()
                self._producer = None

            if self._consumer:
                await self._consumer.stop()
                self._consumer = None

            self.status = ConnectorStatus.INACTIVE
            logger.info(f"Kafka connector '{self.config.name}' disconnected")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"Kafka connector '{self.config.name}' disconnect failed: {e}")
            return False

    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """执行操作"""
        if self.status != ConnectorStatus.ACTIVE:
            raise RuntimeError("Connector is not connected")

        self._update_last_used()

        try:
            if action == "produce":
                return await self._produce(params)
            elif action == "consume":
                return await self._consume(params)
            elif action == "get_topics":
                return await self._get_topics()
            elif action == "get_topic_info":
                return await self._get_topic_info(params)
            elif action == "create_topic":
                return await self._create_topic(params)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Kafka connector execute '{action}' failed: {e}")
            raise

    async def _produce(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息"""
        topic = params.get("topic")
        message = params.get("message")
        key = params.get("key")
        partition = params.get("partition")
        headers = params.get("headers")

        if not topic:
            raise ValueError("Topic is required")
        if not message:
            raise ValueError("Message is required")

        # 转换消息为字节
        if isinstance(message, dict):
            value = json.dumps(message).encode("utf-8")
        elif isinstance(message, str):
            value = message.encode("utf-8")
        else:
            value = message

        # 转换 key 为字节
        key_bytes = key.encode("utf-8") if key else None

        # 转换 headers
        headers_list = None
        if headers:
            headers_list = [(k, v.encode("utf-8") if isinstance(v, str) else v) for k, v in headers.items()]

        # 发送消息
        metadata = await self._producer.send(
            topic,
            value=value,
            key=key_bytes,
            partition=partition,
            headers=headers_list,
        )

        return {
            "topic": metadata.topic,
            "partition": metadata.partition,
            "offset": metadata.offset,
        }

    async def _consume(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """消费消息"""
        topic = params.get("topic")
        timeout = params.get("timeout", 5000)
        max_messages = params.get("max_messages", 10)
        group_id = params.get("group_id", f"{self.config.name}-consumer")
        auto_offset_reset = params.get("auto_offset_reset", "earliest")

        if not topic:
            raise ValueError("Topic is required")

        messages = []

        # 创建临时消费者
        if self.config.host:
            port = self.config.port or 9092
            bootstrap_servers = [f"{self.config.host}:{port}"]
        else:
            bootstrap_servers = ["localhost:9092"]

        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            consumer_timeout_ms=timeout,
            max_poll_records=max_messages,
        )

        try:
            await consumer.start()
            async for msg in consumer:
                messages.append({
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": msg.key.decode("utf-8") if msg.key else None,
                    "value": msg.value.decode("utf-8"),
                    "timestamp": msg.timestamp,
                })
                if len(messages) >= max_messages:
                    break
        except Exception as e:
            logger.error(f"Kafka consume error: {e}")
            raise
        finally:
            await consumer.stop()

        return messages

    async def _get_topics(self) -> List[str]:
        """获取所有主题"""
        # 通过 producer 的客户端获取主题列表
        client = self._producer._client
        await client.cluster.request_update()
        topics = list(client.cluster.topics())
        return sorted(topics)

    async def _get_topic_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取主题信息"""
        topic = params.get("topic")
        if not topic:
            raise ValueError("Topic is required")

        client = self._producer._client
        await client.cluster.request_update()

        partitions = client.cluster.partitions_for_topic(topic)
        partition_count = len(partitions) if partitions else 0

        # 获取副本数（从第一个分区的副本中获取）
        replication_factor = 0
        if partitions:
            partition_id = list(partitions)[0]
            partition_info = client.cluster.partition_metadata.get(topic, {}).get(partition_id, {})
            replicas = partition_info.get("replicas", [])
            replication_factor = len(replicas)

        return {
            "name": topic,
            "partitions": partition_count,
            "replication_factor": replication_factor,
        }

    async def _create_topic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建主题"""
        # 注意：aiokafka 不直接支持创建主题
        # 这里返回一个提示，实际创建需要通过 Kafka Admin API
        topic = params.get("topic")
        partitions = params.get("partitions", 1)
        replication_factor = params.get("replication_factor", 1)

        if not topic:
            raise ValueError("Topic is required")

        logger.info(f"Topic creation requested: {topic} (partitions={partitions}, replication={replication_factor})")

        # 由于 aiokafka 限制，这里只记录请求
        # 实际主题创建需要使用 kafka-python 或其他 Admin 工具
        return {
            "success": True,
            "message": f"Topic creation request logged. Please use Kafka Admin API to create topic: {topic}",
        }

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self.status != ConnectorStatus.ACTIVE or not self._producer:
                return False

            # 尝试获取主题列表来测试连接
            client = self._producer._client
            await client.cluster.request_update()
            return True
        except Exception as e:
            logger.error(f"Kafka connector health check failed: {e}")
            self.status = ConnectorStatus.ERROR
            return False

    def get_actions(self) -> List[Dict[str, Any]]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
