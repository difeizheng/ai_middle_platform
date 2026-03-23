"""
集成测试
"""
import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """测试根路径"""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AI 中台系统"
        assert "version" in data
        assert data["description"] == "企业级 AI 中台系统"
        assert data["docs"] == "/docs"


class TestAPI_docs:
    """API 文档测试"""

    @pytest.mark.asyncio
    async def test_openapi_json(self, client: AsyncClient):
        """测试 OpenAPI 文档"""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "AI 中台系统"

    @pytest.mark.asyncio
    async def test_docs_endpoint(self, client: AsyncClient):
        """测试 Swagger 文档"""
        response = await client.get("/docs")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_endpoint(self, client: AsyncClient):
        """测试 ReDoc 文档"""
        response = await client.get("/redoc")

        assert response.status_code == 200


class TestMiddleware:
    """中间件测试"""

    @pytest.mark.asyncio
    async def test_request_logging(self, client: AsyncClient):
        """测试请求日志中间件"""
        response = await client.get("/health")

        assert response.status_code == 200
        # 响应头应该包含处理时间
        assert "X-Process-Time" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_propagation(self, client: AsyncClient):
        """测试请求 ID 传递"""
        test_request_id = "test-12345"
        response = await client.get(
            "/health",
            headers={"X-Request-ID": test_request_id},
        )

        assert response.status_code == 200
        # 响应头应该包含请求 ID
        assert "X-Request-ID" in response.headers


class TestCORS:
    """CORS 测试"""

    @pytest.mark.asyncio
    async def test_cors_headers(self, client: AsyncClient):
        """测试 CORS 头"""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS 预检请求应该成功
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_404_handler(self, client: AsyncClient):
        """测试 404 处理"""
        response = await client.get("/nonexistent-endpoint")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """测试方法不允许"""
        response = await client.post("/health")

        # POST 到 health 端点应该返回 405 或其他错误
        assert response.status_code in [405, 404]


class TestAuthIntegration:
    """认证集成测试"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_auth(self, client: AsyncClient):
        """测试受保护端点无需认证"""
        response = await client.get("/api/v1/users")

        # 应该返回 401 或 403
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """测试无效 token"""
        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code in [401, 403]
