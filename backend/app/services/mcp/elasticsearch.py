"""
Elasticsearch 连接器
"""
from typing import Any, Dict, List, Optional
import json

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

from ...core.logger import get_logger

logger = get_logger(__name__)


class ElasticsearchConnector(MCPConnector):
    """
    Elasticsearch 连接器

    支持的操作:
    - search: 搜索文档
    - index: 索引文档
    - delete: 删除文档
    - count: 统计文档数
    - health: 集群健康检查
    """

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="search",
                description="搜索文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "索引名称"},
                        "query": {"type": "object", "description": "搜索查询"},
                        "size": {"type": "number", "description": "返回数量", "default": 10},
                        "from": {"type": "number", "description": "偏移量", "default": 0},
                    },
                    "required": ["index", "query"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "hits": {"type": "array", "description": "命中结果"},
                        "total": {"type": "number", "description": "总数"},
                    },
                },
            ),
            ActionDefinition(
                name="index",
                description="索引文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "索引名称"},
                        "document": {"type": "object", "description": "文档内容"},
                        "id": {"type": "string", "description": "文档 ID"},
                    },
                    "required": ["index", "document"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "文档 ID"},
                        "result": {"type": "string", "description": "操作结果"},
                    },
                },
            ),
            ActionDefinition(
                name="delete",
                description="删除文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "索引名称"},
                        "id": {"type": "string", "description": "文档 ID"},
                    },
                    "required": ["index", "id"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "string", "description": "操作结果"},
                    },
                },
            ),
            ActionDefinition(
                name="count",
                description="统计文档数",
                params_schema={
                    "type": "object",
                    "properties": {
                        "index": {"type": "string", "description": "索引名称"},
                        "query": {"type": "object", "description": "过滤查询"},
                    },
                    "required": ["index"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "count": {"type": "number", "description": "文档数量"},
                    },
                },
            ),
        ]

    async def connect(self) -> bool:
        """连接到 Elasticsearch"""
        try:
            from elasticsearch import AsyncElasticsearch

            # 构建连接 URL
            scheme = "https" if self.config.ssl else "http"
            hosts = []

            if self.config.host and self.config.port:
                hosts.append(f"{scheme}://{self.config.host}:{self.config.port}")
            else:
                hosts.append(self.config.extra.get("host_url", "http://localhost:9200"))

            # 创建客户端
            self._client = AsyncElasticsearch(
                hosts=hosts,
                basic_auth=(
                    (self.config.username, self.config.password)
                    if self.config.username
                    else None
                ),
                request_timeout=self.config.timeout,
                verify_certs=self.config.ssl,
            )

            # 测试连接
            await self._client.info()
            self.status = ConnectorStatus.ACTIVE
            logger.info(f"Elasticsearch connected: {hosts}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect Elasticsearch: {e}")
            self.status = ConnectorStatus.ERROR
            return False

    async def disconnect(self) -> bool:
        """断开连接"""
        try:
            if self._client:
                await self._client.close()
                self._client = None
            self.status = ConnectorStatus.INACTIVE
            logger.info("Elasticsearch disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting Elasticsearch: {e}")
            return False

    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Any:
        """执行操作"""
        if self.status != ConnectorStatus.ACTIVE:
            raise RuntimeError("Elasticsearch not connected")

        self._update_last_used()

        try:
            if action == "search":
                return await self._search(params)
            elif action == "index":
                return await self._index(params)
            elif action == "delete":
                return await self._delete(params)
            elif action == "count":
                return await self._count(params)
            else:
                raise ValueError(f"Unsupported action: {action}")
        except Exception as e:
            logger.error(f"Elasticsearch action {action} failed: {e}")
            raise

    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """搜索文档"""
        index = params.get("index")
        query = params.get("query", {"match_all": {}})
        size = params.get("size", 10)
        from_ = params.get("from", 0)

        response = await self._client.search(
            index=index,
            body={"query": query, "size": size, "from": from_},
        )

        hits = []
        for hit in response["hits"]["hits"]:
            hits.append({
                "id": hit["_id"],
                "score": hit["_score"],
                "source": hit["_source"],
            })

        return {
            "hits": hits,
            "total": response["hits"]["total"]["value"],
        }

    async def _index(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """索引文档"""
        index = params.get("index")
        document = params.get("document")
        doc_id = params.get("id")

        response = await self._client.index(
            index=index,
            id=doc_id,
            body=document,
        )

        return {
            "id": response["_id"],
            "result": response["result"],
        }

    async def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除文档"""
        index = params.get("index")
        doc_id = params.get("id")

        response = await self._client.delete(
            index=index,
            id=doc_id,
        )

        return {
            "result": response["result"],
        }

    async def _count(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """统计文档数"""
        index = params.get("index")
        query = params.get("query")

        body = {"query": query} if query else {}
        response = await self._client.count(index=index, body=body)

        return {"count": response["count"]}

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._client:
                return False
            response = await self._client.cluster.health()
            status = response.get("status", "unknown")
            return status in ("green", "yellow")
        except Exception:
            return False

    def get_actions(self) -> List[Dict[str, Any]]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
