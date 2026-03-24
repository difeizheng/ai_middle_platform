# 慢查询分析与优化方案

## 当前数据库配置

### 连接池配置
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,              # 连接池大小
    max_overflow=40,           # 最大溢出连接数
    pool_pre_ping=True,        # 连接前检测
    pool_recycle=3600,         # 连接回收时间
    pool_timeout=30,           # 获取连接超时
    pool_use_lifo=True,        # LIFO 模式
)
```

## 慢查询日志配置

### 1. PostgreSQL 慢查询日志

在 PostgreSQL 配置文件中添加：

```sql
-- postgresql.conf
log_min_duration_statement = 100    # 记录超过 100ms 的查询
log_checkpoints = on                # 记录检查点
log_lock_waits = on                 # 记录锁等待
log_temp_files = 0                  # 记录临时文件使用
log_statement = 'ddl'               # 记录 DDL 语句
```

### 2. SQLAlchemy 慢查询回调

```python
import logging
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger("sqlalchemy")

def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.1:  # 超过 100ms
        logger.warning(f"Slow query ({total:.3f}s): {statement}")

engine = create_async_engine(...)
event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
event.listen(engine.sync_engine, "after_cursor_execute", after_cursor_execute)
```

## 常见慢查询及优化方案

### 1. 缺少索引

**问题查询:**
```python
# 查询用户 - 缺少 username 索引
result = await db.execute(
    select(User).where(User.username == username)
)
```

**优化方案:**
```python
# 添加索引
CREATE INDEX idx_users_username ON users(username);

# 或使用 SQLAlchemy
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, unique=True)  # 添加索引
    email = Column(String, index=True)
```

### 2. N+1 查询问题

**问题代码:**
```python
# 查询应用列表
apps = await db.execute(select(Application))
for app in apps:
    # N+1 问题：每个应用都查询一次 API Key
    keys = await db.execute(
        select(APIKey).where(APIKey.app_id == app.id)
    )
```

**优化方案:**
```python
# 使用 joinedload 预加载
from sqlalchemy.orm import joinedload

apps = await db.execute(
    select(Application).options(
        joinedload(Application.api_keys)
    )
)
```

### 3. 大表全表扫描

**问题查询:**
```python
# API 日志表 - 没有时间范围索引
logs = await db.execute(
    select(APILog).where(
        APILog.created_at >= start_time,
        APILog.created_at <= end_time
    )
)
```

**优化方案:**
```python
# 添加复合索引
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at);
CREATE INDEX idx_api_logs_user_time ON api_logs(user_id, created_at);

# 添加分页限制
logs = await db.execute(
    select(APILog)
    .where(APILog.created_at >= start_time, APILog.created_at <= end_time)
    .order_by(APILog.created_at.desc())
    .limit(100)
)
```

### 4.  inefficient JOIN

**问题查询:**
```python
# 多表 JOIN 缺少关联索引
query = """
    SELECT a.*, u.username, COUNT(k.id) as knowledge_count
    FROM applications a
    JOIN users u ON a.owner_id = u.id
    LEFT JOIN knowledge_bases k ON k.owner_id = u.id
    GROUP BY a.id, u.username
"""
```

**优化方案:**
```python
# 添加外键索引
CREATE INDEX idx_applications_owner_id ON applications(owner_id);
CREATE INDEX idx_knowledge_bases_owner_id ON knowledge_bases(owner_id);

# 使用物化视图缓存聚合结果
CREATE MATERIALIZED VIEW app_stats AS
SELECT
    a.id,
    a.name,
    COUNT(k.id) as knowledge_count,
    SUM(COALESCE(k.document_count, 0)) as total_documents
FROM applications a
LEFT JOIN knowledge_bases k ON k.owner_id = a.owner_id
GROUP BY a.id, a.name;

-- 定期刷新
REFRESH MATERIALIZED VIEW app_stats;
```

## 推荐的数据库索引

### users 表
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### applications 表
```sql
CREATE INDEX idx_applications_owner_id ON applications(owner_id);
CREATE INDEX idx_applications_is_active ON applications(is_active);
CREATE INDEX idx_applications_created_at ON applications(created_at);
```

### api_keys 表
```sql
CREATE INDEX idx_api_keys_app_id ON api_keys(app_id);
CREATE INDEX idx_api_keys_key ON api_keys(key);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX idx_api_keys_last_used ON api_keys(last_used_at);
```

### agent_executions 表
```sql
CREATE INDEX idx_agent_executions_agent_id ON agent_executions(agent_id);
CREATE INDEX idx_agent_executions_status ON agent_executions(status);
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at);
```

### api_logs 表
```sql
CREATE INDEX idx_api_logs_user_id ON api_logs(user_id);
CREATE INDEX idx_api_logs_created_at ON api_logs(created_at);
CREATE INDEX idx_api_logs_level ON api_logs(level);
CREATE INDEX idx_api_logs_path ON api_logs(path);
```

## 查询优化最佳实践

### 1. 使用 EXPLAIN 分析查询
```sql
-- 分析查询计划
EXPLAIN ANALYZE SELECT * FROM users WHERE username = 'admin';

-- 查看是否使用索引
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM api_logs WHERE created_at > NOW() - INTERVAL '1 day';
```

### 2. 避免 SELECT *
```python
# 不推荐
users = await db.execute(select(User))

# 推荐：只选择需要的字段
users = await db.execute(
    select(User.id, User.username, User.email)
)
```

### 3. 使用批量操作
```python
# 不推荐：逐条插入
for item in items:
    db.add(Item(**item))
    await db.commit()

# 推荐：批量插入
db.bulk_insert_mappings(Item, items)
await db.commit()
```

### 4. 合理使用连接池
```python
# 监控连接池状态
pool_status = engine.pool.status()
logger.info(f"Pool size: {engine.pool.size()}, checked_out: {engine.pool.checkedout()}")
```

## 性能监控脚本

```python
# app/services/db_profiler.py
import time
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

class DatabaseProfiler:
    """数据库性能分析器"""

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold  # 慢查询阈值（秒）
        self.slow_queries = []

    def register(self, engine: AsyncEngine):
        """注册到引擎"""
        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())

        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            start_time = conn.info['query_start_time'].pop(-1)
            duration = time.time() - start_time

            if duration > self.threshold:
                self.slow_queries.append({
                    'statement': statement,
                    'duration': duration,
                    'timestamp': time.time(),
                })

    def get_slow_queries(self, limit: int = 100):
        """获取慢查询列表"""
        return sorted(self.slow_queries, key=lambda x: x['duration'])[-limit:]

    def clear(self):
        """清空记录"""
        self.slow_queries.clear()

# 使用示例
profiler = DatabaseProfiler(threshold=0.1)
profiler.register(engine)
```

## 优化检查清单

- [ ] 所有 WHERE 子句字段都有索引
- [ ] 所有 JOIN 关联字段都有索引
- [ ] 所有 ORDER BY 字段都有索引
- [ ] 复合查询使用复合索引
- [ ] 大表查询有分页限制
- [ ] 避免 N+1 查询
- [ ] 使用连接池预 ping
- [ ] 定期 VACUUM ANALYZE
- [ ] 监控慢查询日志
- [ ] 定期更新统计信息
