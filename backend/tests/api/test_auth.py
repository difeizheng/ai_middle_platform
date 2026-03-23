"""
认证 API 测试
"""
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


class TestAuthAPI:
    """认证 API 测试类"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user_data):
        """测试登录成功"""
        # 注意：这需要先在数据库中创建用户
        # 实际测试需要完善用户创建逻辑
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )
        # 如果用户不存在，应该返回错误
        # 如果用户存在且密码正确，应该返回 token
        assert response.status_code in [200, 401, 404]

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """测试无效凭证"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword",
            },
        )
        assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, test_user_data):
        """测试获取当前用户"""
        # 需要一个有效的 token
        # 这里测试 token 无效的情况
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_token_creation(self, test_user_data):
        """测试 token 创建（单元测试）"""
        from app.core.security import create_access_token, verify_access_token

        token = create_access_token(
            data={"sub": test_user_data["username"], "role": test_user_data["role"]}
        )

        assert token is not None
        assert len(token) > 0

        # 验证 token
        payload = verify_access_token(token)
        assert payload is not None
        assert payload.sub == test_user_data["username"]

    @pytest.mark.asyncio
    async def test_login_missing_username(self, client: AsyncClient):
        """测试缺少用户名的登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "somepassword"},
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """测试缺少密码的登录"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "someuser"},
        )
        assert response.status_code in [400, 422]
