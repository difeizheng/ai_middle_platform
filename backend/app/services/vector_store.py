"""
向量数据库服务
支持 Milvus、Qdrant
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


@dataclass
class SearchQuery:
    """搜索查询"""
    query: str
    top_k: int = 5
    filter_expr: Optional[str] = None


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    vector_id: str


class VectorStoreService:
    """
    向量存储服务
    """

    def __init__(
        self,
        db_type: str = None,
        collection_name: str = None,
    ):
        """
        Args:
            db_type: 向量库类型 (milvus, qdrant)
            collection_name: 集合名称
        """
        self.db_type = db_type or settings.VECTOR_DB_TYPE
        self.collection_name = collection_name or settings.MILVUS_COLLECTION
        self._client = None
        self._is_connected = False

    async def connect(self):
        """连接到向量数据库"""
        if self._is_connected:
            return

        try:
            if self.db_type == "milvus":
                await self._connect_milvus()
            elif self.db_type == "qdrant":
                await self._connect_qdrant()
            else:
                logger.warning(f"不支持的向量库类型：{self.db_type}")
        except Exception as e:
            logger.error(f"连接向量数据库失败：{e}")
            self._is_connected = False

    async def _connect_milvus(self):
        """连接 Milvus"""
        try:
            from pymilvus import connections, Collection

            # 同步连接（Milvus  SDK 主要是同步的）
            connections.connect(
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )

            # 检查集合是否存在
            from pymilvus import has_collection, Collection

            if not has_collection(self.collection_name):
                # 创建集合
                await self._create_milvus_collection()

            self._client = Collection(self.collection_name)
            self._is_connected = True
            logger.info(f"成功连接到 Milvus 集合：{self.collection_name}")

        except ImportError:
            logger.warning("pymilvus 未安装，Milvus 功能不可用")
            self._is_connected = False
        except Exception as e:
            logger.error(f"连接 Milvus 失败：{e}")
            self._is_connected = False

    async def _create_milvus_collection(self):
        """创建 Milvus 集合"""
        from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection

        connections.connect(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]

        schema = CollectionSchema(fields=fields, description="Knowledge Base Collection")
        collection = Collection(name=self.collection_name, schema=schema)

        # 创建索引
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 8, "efConstruction": 200},
        }
        collection.create_index(field_name="vector", index_params=index_params)

        logger.info(f"创建 Milvus 集合：{self.collection_name}")

    async def _connect_qdrant(self):
        """连接 Qdrant"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

            # 检查集合是否存在
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # 创建集合
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"创建 Qdrant 集合：{self.collection_name}")

            self._is_connected = True
            logger.info(f"成功连接到 Qdrant 集合：{self.collection_name}")

        except ImportError:
            logger.warning("qdrant-client 未安装，Qdrant 功能不可用")
            self._is_connected = False
        except Exception as e:
            logger.error(f"连接 Qdrant 失败：{e}")
            self._is_connected = False

    async def upsert(
        self,
        vectors: List[List[float]],
        ids: List[str],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> bool:
        """
        插入或更新向量

        Args:
            vectors: 向量列表
            ids: ID 列表
            contents: 内容列表
            metadatas: 元数据列表

        Returns:
            是否成功
        """
        if not self._is_connected:
            await self.connect()

        if not self._is_connected:
            logger.warning("向量数据库未连接，使用本地存储")
            return False

        try:
            if self.db_type == "milvus":
                return await self._upsert_milvus(vectors, ids, contents, metadatas)
            elif self.db_type == "qdrant":
                return await self._upsert_qdrant(vectors, ids, contents, metadatas)
        except Exception as e:
            logger.error(f"插入向量失败：{e}")
            return False

        return False

    async def _upsert_milvus(
        self,
        vectors: List[List[float]],
        ids: List[str],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> bool:
        """插入到 Milvus"""
        from pymilvus import utility

        entities = [
            {"id": ids[i], "vector": vectors[i], "content": contents[i], "metadata": metadatas[i]}
            for i in range(len(ids))
        ]

        self._client.insert(entities)
        self._client.flush()

        logger.info(f"插入 {len(ids)} 条向量到 Milvus")
        return True

    async def _upsert_qdrant(
        self,
        vectors: List[List[float]],
        ids: List[str],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> bool:
        """插入到 Qdrant"""
        from qdrant_client.http.models import PointStruct

        points = [
            PointStruct(
                id=i,  # Qdrant 使用整数 ID
                vector=vectors[i],
                payload={
                    "content": contents[i],
                    "metadata": metadatas[i],
                    "original_id": ids[i],
                },
            )
            for i in range(len(ids))
        ]

        self._client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.info(f"插入 {len(ids)} 条向量到 Qdrant")
        return True

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        向量搜索

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            搜索结果列表
        """
        if not self._is_connected:
            await self.connect()

        if not self._is_connected:
            logger.warning("向量数据库未连接，返回空结果")
            return []

        try:
            if self.db_type == "milvus":
                return await self._search_milvus(query_vector, top_k, filter_expr)
            elif self.db_type == "qdrant":
                return await self._search_qdrant(query_vector, top_k, filter_expr)
        except Exception as e:
            logger.error(f"搜索失败：{e}")
            return []

        return []

    async def _search_milvus(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """在 Milvus 中搜索"""
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 100},
        }

        results = self._client.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["content", "metadata"],
        )

        search_results = []
        if results and len(results) > 0:
            for hit in results[0]:
                search_results.append(SearchResult(
                    id=hit.entity.get("id", ""),
                    content=hit.entity.get("content", ""),
                    score=hit.score,
                    metadata=hit.entity.get("metadata", {}),
                    vector_id=hit.entity.get("id", ""),
                ))

        return search_results

    async def _search_qdrant(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """在 Qdrant 中搜索"""
        from qdrant_client.http.models import Filter

        scroll_filter = None
        if filter_expr:
            # 简化处理，实际需要解析 filter_expr
            pass

        results, _ = self._client.scroll(
            collection_name=self.collection_name,
            query_filter=scroll_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

        search_results = []
        for point in results:
            payload = point.payload or {}
            search_results.append(SearchResult(
                id=payload.get("original_id", str(point.id)),
                content=payload.get("content", ""),
                score=0.0,  # Qdrant scroll 不返回分数
                metadata=payload.get("metadata", {}),
                vector_id=str(point.id),
            ))

        return search_results

    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        if not self._is_connected:
            return False

        try:
            if self.db_type == "milvus":
                expr = f"id in {ids}"
                self._client.delete(expr=expr)
                self._client.flush()
            elif self.db_type == "qdrant":
                self._client.delete(
                    collection_name=self.collection_name,
                    points_selector=ids,
                )
            logger.info(f"删除 {len(ids)} 条向量")
            return True
        except Exception as e:
            logger.error(f"删除向量失败：{e}")
            return False

    async def close(self):
        """关闭连接"""
        if self._client:
            if self.db_type == "milvus":
                from pymilvus import connections
                connections.disconnect("default")
            elif self.db_type == "qdrant":
                self._client.close()
        self._is_connected = False
        logger.info("向量数据库连接已关闭")


# 全局服务实例
_vector_store_service: Optional[VectorStoreService] = None


def get_vector_store_service(collection_name: str = None) -> VectorStoreService:
    """获取向量存储服务实例"""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService(collection_name=collection_name)
    return _vector_store_service
