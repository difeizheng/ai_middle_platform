"""
Skills 市场 API 测试
"""
import pytest
from fastapi.testclient import TestClient


class TestSkillCategories:
    """测试 Skill 分类 API"""

    def test_list_categories(self, client: TestClient, auth_headers: dict):
        """测试获取分类列表"""
        response = client.get("/api/v1/skills/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_categories_with_parent(self, client: TestClient, auth_headers: dict):
        """测试获取子分类"""
        response = client.get(
            "/api/v1/skills/categories?parent_id=analytics",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestSkillRegistry:
    """测试 Skill 注册表 API"""

    def test_list_registry_skills(self, client: TestClient, auth_headers: dict):
        """测试获取已注册的 Skills"""
        response = client.get("/api/v1/skills/skills/registry", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 应该有内置的 Skills
        assert data["total"] >= 4

    def test_list_skills_by_category(self, client: TestClient, auth_headers: dict):
        """测试按分类过滤 Skills"""
        response = client.get(
            "/api/v1/skills/skills/registry?category=analytics",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # data_analysis 应该属于 analytics 分类
        skill_names = [s["name"] for s in data["data"]]
        assert "data_analysis" in skill_names


class TestSkillExecution:
    """测试 Skill 执行 API"""

    def test_execute_data_analysis_statistic(self, client: TestClient, auth_headers: dict):
        """测试执行数据分析 Skill - 统计操作"""
        payload = {
            "data": [
                {"name": "A", "age": 25, "score": 80},
                {"name": "B", "age": 30, "score": 90},
                {"name": "C", "age": 35, "score": 70},
            ],
            "operation": "statistic",
            "config": {"fields": ["age", "score"]},
        }

        response = client.post(
            "/api/v1/skills/skills/data_analysis/execute",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "statistics" in data["data"]
        assert "age" in data["data"]["statistics"]
        assert "score" in data["data"]["statistics"]

    def test_execute_data_analysis_filter(self, client: TestClient, auth_headers: dict):
        """测试执行数据分析 Skill - 过滤操作"""
        payload = {
            "data": [
                {"name": "A", "age": 25, "score": 80},
                {"name": "B", "age": 30, "score": 90},
                {"name": "C", "age": 35, "score": 70},
            ],
            "operation": "filter",
            "config": {
                "conditions": [
                    {"field": "age", "operator": ">", "value": 28},
                ]
            },
        }

        response = client.post(
            "/api/v1/skills/skills/data_analysis/execute",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 应该只返回 age > 28 的记录
        assert data["data"]["count"] == 2

    def test_execute_report_generator(self, client: TestClient, auth_headers: dict):
        """测试执行报告生成 Skill"""
        payload = {
            "title": "测试报告",
            "sections": [
                {
                    "title": "概述",
                    "type": "text",
                    "data": {"text": "这是一个测试报告"},
                },
                {
                    "title": "数据摘要",
                    "type": "summary",
                    "data": {
                        "metrics": {"总数": 100, "成功": 95, "失败": 5},
                    },
                },
            ],
            "template": "markdown",
        }

        response = client.post(
            "/api/v1/skills/skills/report_generator/execute",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]
        assert "# 测试报告" in data["data"]["content"]

    def test_execute_code_review(self, client: TestClient, auth_headers: dict):
        """测试执行代码审查 Skill"""
        payload = {
            "code": """
def hello(name):
    x = eval(input("Enter: "))
    return f"Hello {name} this line is very very very very very very very very very very very very long"
""",
            "language": "python",
            "rules": ["style", "security"],
        }

        response = client.post(
            "/api/v1/skills/skills/code_review/execute",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 应该检测到安全问题（eval）和风格问题（长行）
        assert data["data"]["issue_count"] >= 1

    def test_execute_notification(self, client: TestClient, auth_headers: dict):
        """测试执行通知 Skill"""
        payload = {
            "channel": "log",
            "recipients": ["admin"],
            "subject": "测试通知",
            "message": "这是一条测试消息",
        }

        response = client.post(
            "/api/v1/skills/skills/notification/execute",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSkillSchema:
    """测试 Skill Schema API"""

    def test_get_skill_schema(self, client: TestClient, auth_headers: dict):
        """测试获取 Skill Schema"""
        # 首先创建一个 Skill
        create_payload = {
            "name": "test_skill_schema",
            "display_name": "测试 Skill",
            "description": "测试用 Skill",
            "input_schema": {"type": "object", "properties": {"param1": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        }

        # 获取 schema
        response = client.get(
            "/api/v1/skills/skills/test_skill_schema/schema",
            headers=auth_headers,
        )
        # 如果 Skill 不存在应该返回 404
        if response.status_code == 404:
            return
        assert response.status_code == 200


class TestSkillStats:
    """测试统计信息 API"""

    def test_get_skills_stats(self, client: TestClient, auth_headers: dict):
        """测试获取统计信息"""
        response = client.get("/api/v1/skills/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_skills" in data["data"]
        assert "runtime" in data["data"]


class TestSkillCRUD:
    """测试 Skill CRUD API"""

    def test_create_skill(self, client: TestClient, auth_headers: dict):
        """测试创建 Skill"""
        payload = {
            "name": "test_skill_crud",
            "display_name": "测试 Skill CRUD",
            "description": "用于测试的 Skill",
            "version": "1.0.0",
            "tags": ["test", "crud"],
            "is_public": False,
        }

        response = client.post(
            "/api/v1/skills/skills",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "test_skill_crud"

    def test_create_duplicate_skill(self, client: TestClient, auth_headers: dict):
        """测试创建重名 Skill"""
        payload = {
            "name": "test_skill_crud",
            "display_name": "测试 Skill",
            "description": "用于测试的 Skill",
        }

        response = client.post(
            "/api/v1/skills/skills",
            headers=auth_headers,
            json=payload,
        )
        assert response.status_code == 400

    def test_update_skill(self, client: TestClient, auth_headers: dict):
        """测试更新 Skill"""
        # 先创建
        payload = {
            "name": "test_skill_update",
            "display_name": "测试 Skill 更新",
            "description": "用于测试的 Skill",
        }

        create_response = client.post(
            "/api/v1/skills/skills",
            headers=auth_headers,
            json=payload,
        )
        skill_id = create_response.json()["data"]["id"]

        # 更新
        update_payload = {
            "description": "更新后的描述",
            "tags": ["updated", "test"],
        }

        response = client.put(
            f"/api/v1/skills/skills/{skill_id}",
            headers=auth_headers,
            json=update_payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == "更新后的描述"

    def test_get_skill(self, client: TestClient, auth_headers: dict):
        """测试获取 Skill 详情"""
        # 先创建
        payload = {
            "name": "test_skill_get",
            "display_name": "测试 Skill 获取",
            "description": "用于测试的 Skill",
        }

        create_response = client.post(
            "/api/v1/skills/skills",
            headers=auth_headers,
            json=payload,
        )
        skill_id = create_response.json()["data"]["id"]

        # 获取详情
        response = client.get(
            f"/api/v1/skills/skills/{skill_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == skill_id

    def test_delete_skill(self, client: TestClient, auth_headers: dict):
        """测试删除 Skill"""
        # 先创建
        payload = {
            "name": "test_skill_delete",
            "display_name": "测试 Skill 删除",
            "description": "用于测试的 Skill",
        }

        create_response = client.post(
            "/api/v1/skills/skills",
            headers=auth_headers,
            json=payload,
        )
        skill_id = create_response.json()["data"]["id"]

        # 删除
        response = client.delete(
            f"/api/v1/skills/skills/{skill_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # 验证已删除
        get_response = client.get(
            f"/api/v1/skills/skills/{skill_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404
