# 向量检索性能调优方案

## 当前配置

### Milvus 配置
```python
# 向量库类型
VECTOR_DB_TYPE = "milvus"

# Milvus 连接
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION = "knowledge_base"

# 向量维度
EMBEDDING_DIM = 1024  # bge-large-zh-v1.5
```

## 性能优化方案

### 1. 索引优化

#### Milvus 索引类型对比

| 索引类型 | 适用场景 | 检索速度 | 内存占用 | 构建速度 |
|---------|---------|---------|---------|---------|
| FLAT | 小数据集 (<10K) | 慢 | 低 | 快 |
| IVF_FLAT | 通用场景 | 中 | 中 | 中 |
| IVF_SQ8 | 大数据集 | 中 | 低 | 中 |
| HNSW | 高召回率要求 | 快 | 高 | 慢 |
| ANNOY | 内存受限 | 中 | 低 | 快 |

#### 推荐配置

```python
# 创建索引
def create_index(collection_name: str, dim: int = 1024):
    from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, connections

    connections.connect(host="localhost", port="19530")

    # 创建集合
    schema = CollectionSchema([
        FieldSchema("id", DataType.VARCHAR, max_length=100, is_primary=True),
        FieldSchema("vector", DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema("content", DataType.VARCHAR, max_length=10000),
        FieldSchema("metadata", DataType.JSON),
    ])

    collection = Collection(collection_name, schema)

    # 创建索引 - IVF_FLAT (推荐)
    index_params = {
        "metric_type": "COSINE",  # 余弦相似度
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024},  # 聚类中心数
    }
    collection.create_index("vector", index_params)

    # 加载到内存
    collection.load()

    return collection
```

### 2. 检索参数优化

```python
class VectorStoreService:
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_expr: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        向量检索

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_expr: 过滤表达式

        Returns:
            搜索结果列表
        """
        # 搜索参数优化
        search_params = {
            "metric_type": "COSINE",
            "params": {
                "nprobe": 64,  # 搜索的聚类中心数 (nlist 的 1/16 到 1/8)
            },
        }

        # 执行搜索
        results = self._client.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["content", "metadata"],
        )

        return self._parse_results(results)
```

### 3. 缓存优化

```python
class VectorSearchCache:
    """向量检索缓存"""

    def __init__(self):
        self.redis = cache_service.redis
        self.ttl = 300  # 5 分钟
        self.max_cache_size = 10000

    def _make_cache_key(self, query_vector_hash: str, top_k: int) -> str:
        """生成缓存键"""
        return f"vector:search:{query_vector_hash}:{top_k}"

    async def get_or_search(
        self,
        query_vector: List[float],
        search_func: Callable,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        带缓存的向量检索

        Args:
            query_vector: 查询向量
            search_func: 搜索函数
            top_k: 返回数量

        Returns:
            搜索结果
        """
        # 生成向量哈希
        vector_hash = hashlib.md5(
            json.dumps(query_vector).encode()
        ).hexdigest()[:16]

        cache_key = self._make_cache_key(vector_hash, top_k)

        # 尝试缓存
        cached = await cache_service.get(cache_key)
        if cached:
            return cached

        # 执行搜索
        results = await search_func(query_vector, top_k)

        # 存入缓存
        await cache_service.set(cache_key, results, expire=self.ttl)

        return results

# 使用示例
search_cache = VectorSearchCache()

async def search_with_cache(query: str, top_k: int = 5) -> List[SearchResult]:
    # 生成向量
    query_vector = await embedding_service.encode(query)

    # 带缓存的搜索
    return await search_cache.get_or_search(
        query_vector,
        vector_store_service.search,
        top_k,
    )
```

### 4. 批量检索优化

```python
class VectorStoreService:
    async def batch_search(
        self,
        query_vectors: List[List[float]],
        top_k: int = 5,
        batch_size: int = 10,
    ) -> List[List[SearchResult]]:
        """
        批量向量检索

        Args:
            query_vectors: 查询向量列表
            top_k: 返回数量
            batch_size: 批次大小

        Returns:
            搜索结果列表（每个查询对应一个结果列表）
        """
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 64},
        }

        all_results = []

        # 分批处理
        for i in range(0, len(query_vectors), batch_size):
            batch_vectors = query_vectors[i:i + batch_size]

            results = self._client.search(
                data=batch_vectors,
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["content", "metadata"],
            )

            all_results.extend([
                self._parse_results(batch_result)
                for batch_result in results
            ])

        return all_results
```

### 5. 混合检索（向量 + 关键词）

```python
class HybridSearch:
    """混合检索：向量检索 + BM25 关键词检索"""

    def __init__(self, vector_weight: float = 0.7):
        self.vector_weight = vector_weight
        self.keyword_weight = 1 - vector_weight

    async def search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        混合检索

        Args:
            query: 查询文本
            query_vector: 查询向量
            top_k: 返回数量

        Returns:
            搜索结果
        """
        # 1. 向量检索
        vector_results = await vector_store.search(query_vector, top_k * 2)

        # 2. 关键词检索 (BM25)
        keyword_results = await self._bm25_search(query, top_k * 2)

        # 3. 融合结果 (RRF - Reciprocal Rank Fusion)
        fused_results = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            top_k,
        )

        return fused_results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """RRF 融合算法"""
        scores = {}

        # 向量检索得分
        for i, result in enumerate(vector_results):
            scores[result.id] = scores.get(result.id, 0) + (
                self.vector_weight / (i + 1)
            )

        # 关键词检索得分
        for i, result in enumerate(keyword_results):
            scores[result.id] = scores.get(result.id, 0) + (
                self.keyword_weight / (i + 1)
            )

        # 排序返回 top_k
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            next(r for r in vector_results + keyword_results if r.id == id)
            for id in sorted_ids[:top_k]
        ]
```

### 6. 异步检索

```python
import aiohttp
import asyncio

class AsyncVectorSearch:
    """异步向量检索"""

    def __init__(self, max_concurrency: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def search_with_retry(
        self,
        query_vector: List[float],
        top_k: int = 5,
        max_retries: int = 3,
    ) -> List[SearchResult]:
        """带重试的异步检索"""
        for attempt in range(max_retries):
            try:
                async with self.semaphore:
                    return await vector_store.search(query_vector, top_k)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避

    async def parallel_search(
        self,
        queries: List[Tuple[str, List[float]]],
        top_k: int = 5,
    ) -> List[SearchResult]:
        """并行检索多个查询"""
        tasks = [
            self.search_with_retry(vector, top_k)
            for _, vector in queries
        ]
        return await asyncio.gather(*tasks)
```

### 7. 性能监控

```python
class VectorSearchProfiler:
    """向量检索性能分析"""

    def __init__(self):
        self.latencies = []
        self.recalls = []

    async def profile_search(
        self,
        query_vectors: List[List[float]],
        top_k: int = 5,
    ) -> dict:
        """分析检索性能"""
        results = []
        latencies = []

        for vector in query_vectors:
            start_time = time.time()
            result = await vector_store.search(vector, top_k)
            latency = (time.time() - start_time) * 1000  # ms

            results.append(result)
            latencies.append(latency)

        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "p50_latency_ms": sorted(latencies)[len(latencies) // 2],
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)],
            "qps": len(query_vectors) / (sum(latencies) / 1000),
        }

# 使用示例
profiler = VectorSearchProfiler()

# 生成测试向量
test_vectors = [
    [random.random() for _ in range(1024)]
    for _ in range(100)
]

# 分析性能
stats = await profiler.profile_search(test_vectors, top_k=5)
print(f"平均延迟：{stats['avg_latency_ms']:.2f}ms")
print(f"QPS: {stats['qps']:.2f}")
```

## 性能优化检查清单

- [ ] 使用合适的索引类型（IVF_FLAT / HNSW）
- [ ] 设置合理的 nlist 值（数据量的平方根）
- [ ] 调整 nprobe 参数平衡速度和准确率
- [ ] 使用缓存减少重复检索
- [ ] 批量检索减少网络开销
- [ ] 异步检索提高并发
- [ ] 混合检索提高召回率
- [ ] 监控延迟和 QPS

## 目标性能指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 平均检索延迟 | - | < 50ms |
| P95 延迟 | - | < 100ms |
| QPS | - | > 100 |
| 缓存命中率 | - | > 60% |
