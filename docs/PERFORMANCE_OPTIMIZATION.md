# 性能优化指南

## 优化目标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| API 响应时间 (P95) | < 200ms | - |
| 向量检索延迟 | < 50ms | - |
| 文档解析速度 | > 10 页/秒 | - |
| 并发处理能力 | > 1000 QPS | - |
| 数据库连接池利用率 | > 80% | - |

---

## 已实施优化

### 1. 数据库优化

#### 1.1 连接池配置

```python
# backend/app/core/database.py
create_async_engine(
    DATABASE_URL,
    pool_size=20,           # 连接池大小
    max_overflow=40,        # 最大溢出连接数
    pool_pre_ping=True,     # 连接前 ping 测试
    pool_recycle=3600,      # 连接回收时间
    echo=False,             # 关闭 SQL 日志
)
```

**优化效果:**
- 减少连接建立开销
- 避免连接泄漏
- 提高并发处理能力

#### 1.2 索引优化

```sql
-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- API 日志索引
CREATE INDEX idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at DESC);
CREATE INDEX idx_api_logs_trace_id ON api_logs(trace_id);

-- 知识库索引
CREATE INDEX idx_knowledge_bases_owner ON knowledge_bases(owner_id);
CREATE INDEX idx_documents_kb_id ON documents(knowledge_base_id);
CREATE INDEX idx_chunks_doc_id ON chunks(document_id);

-- 复合索引
CREATE INDEX idx_api_logs_user_time ON api_logs(user_id, created_at DESC);
CREATE INDEX idx_chunks_doc_index ON chunks(document_id, chunk_index);
```

#### 1.3 查询优化

```python
# 使用异步查询
async def get_user_by_username(username: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()

# 批量查询使用 join
async def get_user_with_api_keys(user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.api_keys))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()

# 分页查询
async def list_users(page: int = 1, page_size: int = 20) -> List[User]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).limit(page_size).offset(offset)
    )
    return result.scalars().all()
```

### 2. 缓存优化

#### 2.1 Redis 缓存配置

```python
# backend/app/core/config.py
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# 缓存键前缀
CACHE_PREFIX = {
    "user": "ai:user:",
    "token": "ai:token:",
    "rate_limit": "ai:rate:",
    "knowledge": "ai:kb:",
}

# 过期时间
CACHE_TTL = {
    "user_info": 3600,        # 用户信息 1 小时
    "token": 604800,          # Token 7 天
    "rate_limit": 60,         # 限流 1 分钟
    "knowledge": 300,         # 知识检索 5 分钟
}
```

#### 2.2 应用层缓存

```python
from functools import lru_cache
import asyncio

# LRU 缓存（适合配置等不常变数据）
@lru_cache(maxsize=128)
def get_model_config(model_name: str) -> dict:
    return settings.LLM_APIS.get(model_name, {})

# Redis 缓存装饰器
def cache_result(key_prefix: str, ttl: int = 300):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{args[0] if args else ''}"

            # 尝试从 Redis 获取
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入 Redis
            await redis.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            return result
        return wrapper
    return decorator

# 使用示例
@cache_result("ai:kb:search", ttl=300)
async def search_knowledge(kb_id: int, query: str) -> List:
    # ... 搜索逻辑
    pass
```

### 3. API 响应优化

#### 3.1 异步处理

```python
# 使用异步 IO
async def process_document(file_path: str) -> ParseResult:
    # 文件 IO 异步化
    async with aiofiles.open(file_path, 'rb') as f:
        content = await f.read()

    # CPU 密集型任务放线程池
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: parser.parse(file_path)
    )
    return result
```

#### 3.2 流式响应

```python
from fastapi.responses import StreamingResponse

async def generate_stream():
    """流式输出"""
    async for chunk in llm.generate_stream(messages):
        yield f"data: {json.dumps(chunk)}\n\n"

@app.post("/inference/stream")
async def stream_inference():
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )
```

#### 3.3 响应压缩

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 4. 向量检索优化

#### 4.1 索引类型选择

```python
# Milvus 索引配置
index_params = {
    "metric_type": "IP",  # 内积相似度
    "index_type": "IVF_PQ",  # 乘积量化索引
    "params": {"nlist": 1024, "m": 16},
}

# 适合不同场景的索引类型
# IVF_FLAT: 精确搜索，适合小数据量 (<100 万)
# IVF_PQ: 近似搜索，适合中等数据量 (100 万 -1000 万)
# HNSW: 图索引，适合大数据量 (>1000 万)
```

#### 4.2 检索参数优化

```python
search_params = {
    "metric_type": "IP",
    "params": {"nprobe": 10},  # 搜索 10 个聚类
}

# nprobe 越大越准确但越慢
# 推荐值：sqrt(nlist)
```

#### 4.3 混合检索

```python
async def hybrid_search(query: str, top_k: int = 10) -> List:
    """BM25 + 向量检索 + Rerank"""
    # 1. BM25 关键词检索（快速召回）
    bm25_results = await bm25_search(query, top_k=top_k * 2)

    # 2. 向量检索（语义匹配）
    query_vector = await embed(query)
    vector_results = await vector_search(query_vector, top_k=top_k * 2)

    # 3. 结果融合
    merged = fuse_results(bm25_results, vector_results)

    # 4. Rerank 重排序（可选，提升准确率）
    if USE_RERANK:
        merged = await rerank(query, merged, top_k=top_k)

    return merged[:top_k]
```

### 5. 并发控制

#### 5.1 信号量控制

```python
import asyncio

# 限制并发请求数
semaphore = asyncio.Semaphore(100)

async def rate_limited_request(data):
    async with semaphore:
        return await process(data)
```

#### 5.2 批处理

```python
async def batch_process(items: List, batch_size: int = 10):
    """批处理"""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[process(item) for item in batch]
        )
        results.extend(batch_results)
    return results
```

### 6. 监控与告警

#### 6.1 性能监控

```python
from prometheus_client import Histogram, Counter

# 定义指标
REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)

REQUEST_COUNT = Counter(
    'request_count',
    'Request count',
    ['endpoint', 'status']
)

# 使用装饰器记录
def monitor_performance(func):
    @functools.wraps(func)
    async def wrapper(request, *args, **kwargs):
        start_time = time.time()
        try:
            result = await func(request, *args, **kwargs)
            REQUEST_COUNT.labels(
                endpoint=request.url.path,
                status='success'
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                endpoint=request.url.path,
                status='error'
            ).inc()
            raise
        finally:
            latency = time.time() - start_time
            REQUEST_LATENCY.labels(
                endpoint=request.url.path
            ).observe(latency)
    return wrapper
```

#### 6.2 慢查询日志

```python
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine.sync_engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    if total_time > 1.0:  # 超过 1 秒的查询
        logger.warning(f"Slow query: {total_time:.3f}s - {statement}")
```

---

## 性能基准测试

### 测试场景

```bash
# 使用 wrk 进行压力测试
wrk -t12 -c400 -d30s http://localhost:8000/health

# 使用 locust 进行负载测试
locust -f locustfile.py --host=http://localhost:8000
```

### 基准测试脚本

```python
# tests/performance/test_benchmark.py
import pytest
import time
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(2)
    def document_qa(self):
        self.client.post("/api/v1/scenarios/document-qa/query", json={
            "question": "什么是 AI 中台？"
        })

    @task(1)
    def knowledge_search(self):
        self.client.post("/api/v1/knowledge/search", json={
            "query": "测试文档",
            "kb_id": 1
        })
```

---

## 优化检查清单

### 数据库
- [ ] 连接池配置合理
- [ ] 关键字段有索引
- [ ] 查询使用 JOIN 而非 N+1
- [ ] 分页查询避免深分页
- [ ] 慢查询监控告警

### 缓存
- [ ] 热点数据有缓存
- [ ] 缓存过期时间合理
- [ ] 缓存穿透/雪崩防护
- [ ] 缓存一致性保证

### API
- [ ] 使用异步 IO
- [ ] 大响应使用压缩
- [ ] 长任务异步处理
- [ ] 流式输出支持

### 向量检索
- [ ] 索引类型选择合理
- [ ] 检索参数调优
- [ ] 混合检索配置
- [ ] 向量维度优化

### 监控
- [ ] 性能指标采集
- [ ] 慢查询日志
- [ ] 错误率监控
- [ ] 资源使用监控

---

*性能优化是持续过程，需根据实际运行情况不断调整*
