"""
MongoDB 连接器
"""
from typing import Any, Dict, List, Optional
import asyncio
import json

from .base import MCPConnector, ConnectorConfig, ConnectorStatus, ActionDefinition

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    AsyncIOMotorClient = None

from ...core.logger import get_logger

logger = get_logger(__name__)


class MongoDBConnector(MCPConnector):
    """
    MongoDB 连接器

    支持的操作:
    - find: 查询文档
    - insert_one: 插入单个文档
    - insert_many: 插入多个文档
    - update_one: 更新单个文档
    - update_many: 更新多个文档
    - delete_one: 删除单个文档
    - delete_many: 删除多个文档
    - aggregate: 聚合查询
    - get_collections: 获取所有集合
    - get_indexes: 获取索引
    """

    def __init__(self, config: ConnectorConfig):
        if AsyncIOMotorClient is None:
            raise ImportError("motor is not installed. Please install it: pip install motor")

        super().__init__(config)
        self._client: Optional[AsyncIOMotorClient] = None
        self._db = None
        self._actions = self._register_actions()

    def _register_actions(self) -> List[ActionDefinition]:
        """注册支持的操作"""
        return [
            ActionDefinition(
                name="find",
                description="查询文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询条件"},
                        "projection": {"type": "object", "description": "投影"},
                        "limit": {"type": "integer", "description": "限制数量"},
                        "sort": {"type": "array", "description": "排序"},
                    },
                    "required": ["collection"],
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "object"},
                },
            ),
            ActionDefinition(
                name="insert_one",
                description="插入单个文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "document": {"type": "object", "description": "文档"},
                    },
                    "required": ["collection", "document"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "inserted_id": {"type": "string"},
                    },
                },
            ),
            ActionDefinition(
                name="insert_many",
                description="插入多个文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "documents": {"type": "array", "description": "文档列表"},
                    },
                    "required": ["collection", "documents"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "inserted_ids": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
            ActionDefinition(
                name="update_one",
                description="更新单个文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询条件"},
                        "update": {"type": "object", "description": "更新操作"},
                    },
                    "required": ["collection", "filter", "update"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "matched_count": {"type": "integer"},
                        "modified_count": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="update_many",
                description="更新多个文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询条件"},
                        "update": {"type": "object", "description": "更新操作"},
                    },
                    "required": ["collection", "filter", "update"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "matched_count": {"type": "integer"},
                        "modified_count": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="delete_one",
                description="删除单个文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询条件"},
                    },
                    "required": ["collection", "filter"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "deleted_count": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="delete_many",
                description="删除多个文档",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "filter": {"type": "object", "description": "查询条件"},
                    },
                    "required": ["collection"],
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "deleted_count": {"type": "integer"},
                    },
                },
            ),
            ActionDefinition(
                name="aggregate",
                description="聚合查询",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                        "pipeline": {"type": "array", "description": "聚合管道"},
                    },
                    "required": ["collection", "pipeline"],
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "object"},
                },
            ),
            ActionDefinition(
                name="get_collections",
                description="获取所有集合",
                params_schema={"type": "object"},
                response_schema={
                    "type": "array",
                    "items": {"type": "string"},
                },
            ),
            ActionDefinition(
                name="get_indexes",
                description="获取集合的索引",
                params_schema={
                    "type": "object",
                    "properties": {
                        "collection": {"type": "string", "description": "集合名"},
                    },
                    "required": ["collection"],
                },
                response_schema={
                    "type": "array",
                    "items": {"type": "object"},
                },
            ),
        ]

    async def connect(self) -> bool:
        """建立 MongoDB 连接"""
        try:
            self.status = ConnectorStatus.CONNECTING

            # 构建连接字符串
            if self.config.host:
                host = self.config.host
                port = self.config.port or 27017
                connection_string = f"mongodb://{host}:{port}"
            else:
                connection_string = "mongodb://localhost:27017"

            # 添加认证信息
            if self.config.username and self.config.password:
                # 在连接字符串中插入认证信息
                auth_part = f"{self.config.username}:{self.config.password}@"
                connection_string = connection_string.replace("mongodb://", f"mongodb://{auth_part}")

            # 添加数据库名
            if self.config.database:
                connection_string += f"/{self.config.database}"

            # 添加 SSL 选项
            if self.config.ssl:
                connection_string += "?ssl=true"

            self._client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=self.config.timeout * 1000,
                maxPoolSize=self.config.max_connections,
            )

            # 测试连接
            await self._client.admin.command("ping")

            self._db = self._client[self.config.database or "default"]
            self.status = ConnectorStatus.ACTIVE
            logger.info(f"MongoDB connector '{self.config.name}' connected successfully")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"MongoDB connector '{self.config.name}' connect failed: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开 MongoDB 连接"""
        try:
            self.status = ConnectorStatus.DISCONNECTING

            if self._client:
                self._client.close()
                self._client = None
                self._db = None

            self.status = ConnectorStatus.INACTIVE
            logger.info(f"MongoDB connector '{self.config.name}' disconnected")
            return True

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            logger.error(f"MongoDB connector '{self.config.name}' disconnect failed: {e}")
            return False

    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """执行操作"""
        if self.status != ConnectorStatus.ACTIVE:
            raise RuntimeError("Connector is not connected")

        self._update_last_used()

        try:
            if action == "find":
                return await self._find(params)
            elif action == "insert_one":
                return await self._insert_one(params)
            elif action == "insert_many":
                return await self._insert_many(params)
            elif action == "update_one":
                return await self._update_one(params)
            elif action == "update_many":
                return await self._update_many(params)
            elif action == "delete_one":
                return await self._delete_one(params)
            elif action == "delete_many":
                return await self._delete_many(params)
            elif action == "aggregate":
                return await self._aggregate(params)
            elif action == "get_collections":
                return await self._get_collections()
            elif action == "get_indexes":
                return await self._get_indexes(params)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"MongoDB connector execute '{action}' failed: {e}")
            raise

    async def _find(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询文档"""
        collection_name = params.get("collection")
        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        filter_dict = params.get("filter", {})
        projection = params.get("projection")
        limit = params.get("limit")
        sort = params.get("sort")

        cursor = collection.find(filter_dict, projection)

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        results = await cursor.to_list(length=None)
        # 转换 ObjectId 为字符串
        return [self._doc_to_dict(doc) for doc in results]

    async def _insert_one(self, params: Dict[str, Any]) -> Dict[str, str]:
        """插入单个文档"""
        collection_name = params.get("collection")
        document = params.get("document")

        if not collection_name:
            raise ValueError("Collection name is required")
        if not document:
            raise ValueError("Document is required")

        collection = self._db[collection_name]
        result = await collection.insert_one(document)
        return {"inserted_id": str(result.inserted_id)}

    async def _insert_many(self, params: Dict[str, Any]) -> Dict[str, List[str]]:
        """插入多个文档"""
        collection_name = params.get("collection")
        documents = params.get("documents")

        if not collection_name:
            raise ValueError("Collection name is required")
        if not documents:
            raise ValueError("Documents are required")

        collection = self._db[collection_name]
        result = await collection.insert_many(documents)
        return {"inserted_ids": [str(id) for id in result.inserted_ids]}

    async def _update_one(self, params: Dict[str, Any]) -> Dict[str, int]:
        """更新单个文档"""
        collection_name = params.get("collection")
        filter_dict = params.get("filter", {})
        update = params.get("update", {})

        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        result = await collection.update_one(filter_dict, update)
        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
        }

    async def _update_many(self, params: Dict[str, Any]) -> Dict[str, int]:
        """更新多个文档"""
        collection_name = params.get("collection")
        filter_dict = params.get("filter", {})
        update = params.get("update", {})

        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        result = await collection.update_many(filter_dict, update)
        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
        }

    async def _delete_one(self, params: Dict[str, Any]) -> Dict[str, int]:
        """删除单个文档"""
        collection_name = params.get("collection")
        filter_dict = params.get("filter", {})

        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        result = await collection.delete_one(filter_dict)
        return {"deleted_count": result.deleted_count}

    async def _delete_many(self, params: Dict[str, Any]) -> Dict[str, int]:
        """删除多个文档"""
        collection_name = params.get("collection")
        filter_dict = params.get("filter", {})

        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        result = await collection.delete_many(filter_dict)
        return {"deleted_count": result.deleted_count}

    async def _aggregate(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """聚合查询"""
        collection_name = params.get("collection")
        pipeline = params.get("pipeline", [])

        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return [self._doc_to_dict(doc) for doc in results]

    async def _get_collections(self) -> List[str]:
        """获取所有集合"""
        collections = await self._db.list_collection_names()
        return sorted(collections)

    async def _get_indexes(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取索引"""
        collection_name = params.get("collection")
        if not collection_name:
            raise ValueError("Collection name is required")

        collection = self._db[collection_name]
        indexes = []
        async for index in collection.list_indexes():
            indexes.append({
                "name": index.get("name"),
                "key": index.get("key"),
                "unique": index.get("unique", False),
            })
        return indexes

    def _doc_to_dict(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """将 MongoDB 文档转换为字典（处理 ObjectId）"""
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self.status != ConnectorStatus.ACTIVE or not self._client:
                return False

            # 执行 ping 测试
            await self._client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB connector health check failed: {e}")
            self.status = ConnectorStatus.ERROR
            return False

    def get_actions(self) -> List[Dict[str, Any]]:
        """获取支持的操作列表"""
        return [action.to_dict() for action in self._actions]
