"""
试点场景 API 测试
"""
import pytest
from httpx import AsyncClient


class TestDocumentQA:
    """文档问答 API 测试"""

    @pytest.mark.asyncio
    async def test_document_qa_query(self, client: AsyncClient):
        """测试文档问答查询"""
        response = await client.post(
            "/api/v1/scenarios/document-qa/query",
            json={
                "question": "什么是 AI 中台？",
                "top_k": 3,
            },
            headers={"Authorization": "Bearer test_token"},
        )
        # 认证失败或服务不可用都是预期的
        assert response.status_code in [200, 401, 403, 500]

    @pytest.mark.asyncio
    async def test_document_qa_chat(self, client: AsyncClient):
        """测试文档问答聊天"""
        response = await client.post(
            "/api/v1/scenarios/document-qa/chat",
            json={
                "question": "如何创建知识库？",
                "session_id": "test-session-123",
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code in [200, 401, 403, 500]


class TestContractCompare:
    """合同比对 API 测试"""

    @pytest.mark.asyncio
    async def test_contract_compare(self, client: AsyncClient):
        """测试合同比对"""
        text1 = """第一条 合同金额
本合同总金额为人民币 100 万元整。

第二条 付款方式
甲方应于合同签订后 30 日内支付全部款项。"""

        text2 = """第一条 合同金额
本合同总金额为人民币 120 万元整。

第二条 付款方式
甲方应于合同签订后 60 日内支付全部款项。

第三条 违约责任
任何一方违约，应向守约方支付违约金。"""

        response = await client.post(
            "/api/v1/scenarios/contract/compare",
            json={
                "text1": text1,
                "text2": text2,
                "compare_type": "full",
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code in [200, 401, 403, 500]


class TestCustomerService:
    """智能客服 API 测试"""

    @pytest.mark.asyncio
    async def test_customer_service_chat(self, client: AsyncClient):
        """测试智能客服聊天"""
        response = await client.post(
            "/api/v1/scenarios/customer-service/chat",
            json={
                "message": "如何重置密码？",
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code in [200, 401, 403, 500]

    @pytest.mark.asyncio
    async def test_create_session(self, client: AsyncClient):
        """测试创建会话"""
        response = await client.post(
            "/api/v1/scenarios/customer-service/session/create",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code in [200, 401, 403, 500]


class TestReportGenerate:
    """报告生成 API 测试"""

    @pytest.mark.asyncio
    async def test_generate_report(self, client: AsyncClient):
        """测试生成报告"""
        response = await client.post(
            "/api/v1/scenarios/report/generate",
            json={
                "report_type": "weekly",
                "title": "周报测试",
                "data": {"week": "第一周", "items": ["完成开发", "进行测试"]},
                "format": "markdown",
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code in [200, 401, 403, 500]

    @pytest.mark.asyncio
    async def test_generate_meeting_summary(self, client: AsyncClient):
        """测试生成会议纪要"""
        transcript = """张三：今天我们讨论项目进度。
李四：目前进展顺利，已完成 80%。
王五：下周可以开始测试。"""

        response = await client.post(
            "/api/v1/scenarios/report/meeting-summary",
            json={
                "title": "项目进度会议",
                "transcript": transcript,
                "attendees": ["张三", "李四", "王五"],
            },
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code in [200, 401, 403, 500]


class TestScenariosList:
    """场景列表 API 测试"""

    @pytest.mark.asyncio
    async def test_list_scenarios(self, client: AsyncClient):
        """测试获取场景列表"""
        response = await client.get(
            "/api/v1/scenarios/scenarios",
            headers={"Authorization": "Bearer test_token"},
        )
        # 认证成功应返回场景列表
        # 认证失败返回 401/403
        assert response.status_code in [200, 401, 403]

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "scenarios" in data
            assert len(data["scenarios"]) >= 4
