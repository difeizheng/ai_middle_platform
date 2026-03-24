"""
Locust 压力测试脚本

使用方法:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

访问 http://localhost:8089 启动测试
"""
from locust import HttpUser, task, between, events
import random
import json
import time


class AIPlatformUser(HttpUser):
    """AI 中台平台用户"""

    wait_time = between(1, 3)  # 请求间隔 1-3 秒
    token = None

    def on_start(self):
        """用户开始时的初始化 - 登录获取 Token"""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin",
                "password": "admin123",
                "grant_type": "password",
            }
        )
        if response.status_code == 200:
            AIPlatformUser.token = response.json().get("access_token")
        else:
            AIPlatformUser.token = None

    @task(10)
    def test_model_inference(self):
        """模型推理接口（高频率）"""
        if not AIPlatformUser.token:
            return

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
            headers={"Authorization": f"Bearer {AIPlatformUser.token}"},
            name="/api/v1/inference/chat/completions",
        )

    @task(5)
    def test_knowledge_search(self):
        """知识检索接口（中频率）"""
        if not AIPlatformUser.token:
            return

        self.client.post(
            "/api/v1/knowledge/1/search",
            json={
                "query": "产品保修政策",
                "top_k": 5,
                "score_threshold": 0.7,
            },
            headers={"Authorization": f"Bearer {AIPlatformUser.token}"},
            name="/api/v1/knowledge/search",
        )

    @task(3)
    def test_agent_execute(self):
        """智能体执行接口（低频率）"""
        if not AIPlatformUser.token:
            return

        self.client.post(
            "/api/v1/agents/1/execute",
            json={
                "task": "分析销售数据，找出增长最快的产品",
                "session_id": f"session_{random.randint(1, 1000)}",
                "stream": False,
                "max_steps": 10,
            },
            headers={"Authorization": f"Bearer {AIPlatformUser.token}"},
            name="/api/v1/agents/execute",
        )

    @task(2)
    def test_application_list(self):
        """应用列表接口（低频）"""
        if not AIPlatformUser.token:
            return

        self.client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {AIPlatformUser.token}"},
            name="/api/v1/applications",
        )

    @task(1)
    def test_health_check(self):
        """健康检查接口（最低频）"""
        self.client.get("/health", name="/health")


class StressUser(HttpUser):
    """压力测试用户 - 更高并发"""

    wait_time = between(0.1, 0.5)  # 请求间隔 0.1-0.5 秒
    token = None

    def on_start(self):
        """登录获取 Token"""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "test_user",
                "password": "test1234",
                "grant_type": "password",
            }
        )
        if response.status_code == 200:
            StressUser.token = response.json().get("access_token")

    @task
    def inference_stress(self):
        """推理接口压力测试"""
        if not StressUser.token:
            return

        self.client.post(
            "/api/v1/inference/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 50,
            },
            headers={"Authorization": f"Bearer {StressUser.token}"},
            name="/api/v1/inference/stress",
        )


# 事件处理器
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行"""
    print("=" * 50)
    print("压力测试开始")
    print(f"目标主机：{environment.host}")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时执行"""
    print("=" * 50)
    print("压力测试结束")
    stats = environment.stats

    # 打印汇总
    print("\n=== 性能汇总 ===")
    print(f"总请求数：{stats.total.num_requests}")
    print(f"失败请求数：{stats.total.num_failures}")
    print(f"错误率：{stats.total.fail_ratio * 100:.2f}%")
    print(f"平均响应时间：{stats.total.avg_response_time:.2f}ms")
    print(f"P95 响应时间：{stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 响应时间：{stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"QPS: {stats.total.current_rps:.2f}")
    print("=" * 50)
