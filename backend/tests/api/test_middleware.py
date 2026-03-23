"""
限流器测试
"""
import pytest
import time
from app.api.middleware import RateLimiter


class TestRateLimiter:
    """限流器测试类"""

    @pytest.fixture
    def rate_limiter(self):
        """创建限流器实例"""
        return RateLimiter(max_requests=5, window=60)

    def test_consume_within_limit(self, rate_limiter):
        """测试在限制内的请求"""
        # 前 5 个请求应该成功
        for i in range(5):
            assert rate_limiter.consume("test_key") is True

    def test_consume_exceeds_limit(self, rate_limiter):
        """测试超出限制的请求"""
        # 先用完配额
        for i in range(5):
            rate_limiter.consume("test_key")

        # 第 6 个请求应该失败
        assert rate_limiter.consume("test_key") is False

    def test_different_keys(self, rate_limiter):
        """测试不同的键独立计数"""
        # key1 用完配额
        for i in range(5):
            rate_limiter.consume("key1")

        # key2 应该仍然可以使用
        assert rate_limiter.consume("key2") is True

    def test_window_reset(self):
        """测试时间窗口重置（简化测试）"""
        # 使用较小的窗口进行测试
        limiter = RateLimiter(max_requests=2, window=1)

        # 用完配额
        assert limiter.consume("test") is True
        assert limiter.consume("test") is True
        assert limiter.consume("test") is False

        # 等待窗口重置
        time.sleep(1.1)

        # 应该又可以请求
        assert limiter.consume("test") is True

    def test_consume_with_tokens(self, rate_limiter):
        """测试多 token 消耗"""
        # 消耗 3 个 token
        assert rate_limiter.consume("test", tokens=3) is True

        # 再消耗 3 个 token 应该失败（只剩 2 个）
        assert rate_limiter.consume("test", tokens=3) is False

        # 消耗 2 个 token 应该成功
        assert rate_limiter.consume("test", tokens=2) is True

    def test_invalid_key(self, rate_limiter):
        """测试无效的键"""
        with pytest.raises((KeyError, TypeError)):
            rate_limiter.consume(None)

    def test_rate_limiter_state(self, rate_limiter):
        """测试限流器状态"""
        # 初始状态
        assert rate_limiter.consume("test") is True

        # 检查内部状态（如果可访问）
        if hasattr(rate_limiter, 'buckets'):
            assert "test" in rate_limiter.buckets
