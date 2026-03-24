# 并发压力测试方案

## 测试工具

### 1. Locust (推荐)

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between
import random
import json

class AIPlatformUser(HttpUser):
    """AI 中台平台用户"""

    wait_time = between(1, 3)  # 请求间隔 1-3 秒

    def on_start(self):
        """用户开始时的初始化"""
        # 登录获取 Token
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin",
                "password": "admin123",
                "grant_type": "password",
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(10)
    def test_model_inference(self):
        """模型推理接口（高频率）"""
        self.client.post(
            "/api/v1/inference/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "你好，请介绍一下自己"}
                ],
                "temperature": 0.7,
                "max_tokens": 100,
            },
            headers=self.headers,
        )

    @task(5)
    def test_knowledge_search(self):
        """知识检索接口（中频率）"""
        self.client.post(
            "/api/v1/knowledge/1/search",
            json={
                "query": "产品保修政策",
                "top_k": 5,
                "score_threshold": 0.7,
            },
            headers=self.headers,
        )

    @task(3)
    def test_agent_execute(self):
        """智能体执行接口（低频率）"""
        self.client.post(
            "/api/v1/agents/1/execute",
            json={
                "task": "分析销售数据，找出增长最快的产品",
                "session_id": f"session_{random.randint(1, 1000)}",
                "stream": False,
                "max_steps": 10,
            },
            headers=self.headers,
        )

    @task(2)
    def test_application_list(self):
        """应用列表接口（低频）"""
        self.client.get(
            "/api/v1/applications",
            headers=self.headers,
        )

    @task(1)
    def test_health_check(self):
        """健康检查接口（最低频）"""
        self.client.get("/health")


class StressUser(HttpUser):
    """压力测试用户 - 更高并发"""

    wait_time = between(0.1, 0.5)  # 请求间隔 0.1-0.5 秒

    def on_start(self):
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "test_user",
                "password": "test1234",
                "grant_type": "password",
            }
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task
    def inference_stress(self):
        """推理接口压力测试"""
        self.client.post(
            "/api/v1/inference/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 50,
            },
            headers=self.headers,
        )
```

### 运行 Locust 测试

```bash
# 启动 Locust (Web UI)
cd backend
locust -f tests/load/locustfile.py --host=http://localhost:8000

# 访问 http://localhost:8089 启动测试

# 或命令行模式
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --html=report.html
```

### 2. wrk (HTTP 基准测试)

```bash
# 安装
# macOS: brew install wrk
# Linux: apt-get install wrk

# 简单 GET 请求测试
wrk -t12 -c400 -d30s http://localhost:8000/health

# POST 请求测试（带 Body）
wrk -t12 -c100 -d30s -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  --data='{"query": "test", "top_k": 5}' \
  http://localhost:8000/api/v1/knowledge/1/search

# 使用 Lua 脚本
wrk -t4 -c100 -d60s -s tests/load/api_test.lua http://localhost:8000
```

### 3. Lua 测试脚本

```lua
-- tests/load/api_test.lua
wrk.method = "POST"
wrk.body = json.encode({
    query = "产品保修政策",
    top_k = 5,
    score_threshold = 0.7
})
wrk.headers["Content-Type"] = "application/json"
wrk.headers["Authorization"] = "Bearer " .. TOKEN

function init(url)
    -- 初始化 Token
    TOKEN = os.getenv("API_TOKEN") or "default_token"
end

function response()
    -- 响应处理
    if wrk.status ~= 200 then
        print("Error: " .. wrk.status)
    end
end
```

## 测试场景

### 场景 1: 正常负载测试

```bash
# 模拟 100 个并发用户，持续 10 分钟
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 5 \
  --run-time 10m \
  --headless
```

**预期指标:**
- P95 延迟 < 200ms
- 错误率 < 0.1%
- QPS > 50

### 场景 2: 峰值负载测试

```bash
# 模拟 500 个并发用户，持续 5 分钟
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 500 \
  --spawn-rate 50 \
  --run-time 5m \
  --headless
```

**预期指标:**
- P95 延迟 < 500ms
- 错误率 < 1%
- 系统不崩溃

### 场景 3: 压力极限测试

```bash
# 持续增加用户直到系统崩溃
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 1000 \
  --spawn-rate 100 \
  --run-time 10m \
  --headless
```

**目标:**
- 找出系统瓶颈
- 确定最大 QPS
- 记录崩溃点

### 场景 4: 长时间稳定性测试

```bash
# 200 用户持续 1 小时
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 200 \
  --spawn-rate 20 \
  --run-time 1h \
  --headless
```

**目标:**
- 检查内存泄漏
- 检查连接池耗尽
- 验证系统稳定性

## 测试报告

### Locust HTML 报告

```bash
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 200 \
  --spawn-rate 20 \
  --run-time 5m \
  --headless \
  --html=load_test_report.html
```

### 自定义报告脚本

```python
# tests/load/generate_report.py
import json
from datetime import datetime

def generate_report(locust_stats: dict) -> str:
    """生成测试报告"""

    report = f"""
# 并发压力测试报告

## 测试信息
- 测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 测试工具：Locust
- 并发用户数：{locust_stats['user_count']}
- 测试时长：{locust_stats['duration']}

## 性能指标

### 响应时间
| 指标 | 值 |
|------|-----|
| 平均响应时间 | {locust_stats['avg_response_time']:.2f}ms |
| P50 响应时间 | {locust_stats['median_response_time']:.2f}ms |
| P95 响应时间 | {locust_stats['p95_response_time']:.2f}ms |
| P99 响应时间 | {locust_stats['p99_response_time']:.2f}ms |

### 吞吐量
| 指标 | 值 |
|------|-----|
| 平均 QPS | {locust_stats['current_rps']:.2f} |
| 峰值 QPS | {locust_stats['max_rps']:.2f} |

### 错误率
| 指标 | 值 |
|------|-----|
| 总请求数 | {locust_stats['total_requests']} |
| 失败请求数 | {locust_stats['failures']} |
| 错误率 | {locust_stats['failure_rate']:.4f}% |

## 接口性能排名

### Top 5 慢接口
"""

    # 添加慢接口排名
    sorted_endpoints = sorted(
        locust_stats['endpoints'],
        key=lambda x: x['avg_response_time'],
        reverse=True
    )[:5]

    for i, endpoint in enumerate(sorted_endpoints, 1):
        report += f"\n{i}. {endpoint['name']}: {endpoint['avg_response_time']:.2f}ms"

    return report
```

## 性能目标

| 指标 | 目标值 | 容忍值 |
|------|--------|--------|
| 平均响应时间 | < 100ms | < 200ms |
| P95 响应时间 | < 300ms | < 500ms |
| P99 响应时间 | < 500ms | < 1000ms |
| QPS | > 100 | > 50 |
| 错误率 | < 0.1% | < 1% |
| CPU 使用率 | < 70% | < 85% |
| 内存使用率 | < 70% | < 85% |

## 监控指标

### 系统资源监控

```python
# tests/load/monitor.py
import psutil
import time

class SystemMonitor:
    """系统资源监控"""

    def __init__(self):
        self.metrics = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }

    def start(self, interval: int = 5):
        """开始监控"""
        while True:
            self.metrics['cpu'].append(psutil.cpu_percent())
            self.metrics['memory'].append(psutil.virtual_memory().percent)
            self.metrics['disk'].append(psutil.disk_usage('/').percent)
            time.sleep(interval)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'cpu_avg': sum(self.metrics['cpu']) / len(self.metrics['cpu']),
            'cpu_max': max(self.metrics['cpu']),
            'memory_avg': sum(self.metrics['memory']) / len(self.metrics['memory']),
            'memory_max': max(self.metrics['memory']),
        }
```

## 优化建议

基于测试结果，可能的优化方向：

1. **数据库优化**
   - 添加索引
   - 优化慢查询
   - 调整连接池大小

2. **缓存优化**
   - 增加缓存覆盖率
   - 调整缓存过期时间
   - 使用本地缓存

3. **应用优化**
   - 异步处理
   - 批量操作
   - 限流降级

4. **架构优化**
   - 水平扩展
   - 负载均衡
   - 读写分离
