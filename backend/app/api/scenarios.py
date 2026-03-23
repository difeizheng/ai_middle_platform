"""
试点场景 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from ..core.database import get_db
from ..models.user import User
from ..auth.dependencies import get_current_user
from ..api.middleware import verify_api_key, rate_limit, audit_log_middleware

router = APIRouter()


# ========== 制度文档问答 ==========

@router.post("/document-qa/query")
@rate_limit(max_requests=60, window=60)
async def document_qa_query(
    question: str,
    kb_id: Optional[int] = None,
    top_k: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    制度文档问答

    Args:
        question: 问题
        kb_id: 知识库 ID
        top_k: 检索数量
    """
    from ..services.scenarios.document_qa import get_qa_service

    try:
        qa_service = get_qa_service()
        await qa_service.initialize()

        result = await qa_service.chat(
            question=question,
            kb_id=kb_id,
            top_k=top_k,
        )

        return {
            "success": True,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"问答失败：{str(e)}",
        )


@router.post("/document-qa/chat")
async def document_qa_chat(
    session_id: Optional[str] = None,
    question: str = None,
    kb_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    文档问答聊天（多轮对话）
    """
    from ..services.scenarios.document_qa import get_qa_service

    if not session_id:
        session_id = str(uuid.uuid4())

    try:
        qa_service = get_qa_service()
        await qa_service.initialize()

        result = await qa_service.chat(
            question=question,
            kb_id=kb_id,
        )

        return {
            "success": True,
            "session_id": session_id,
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天失败：{str(e)}",
        )


# ========== 合同文本比对 ==========

@router.post("/contract/compare")
async def contract_compare(
    text1: str,  # 原合同
    text2: str,  # 比对合同
    compare_type: str = "full",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    合同文本比对

    Args:
        text1: 原合同文本
        text2: 比对合同文本
        compare_type: 比对类型 (full, clause, risk)
    """
    from ..services.scenarios.contract_compare import get_compare_service

    try:
        from ..services.scenarios.contract_compare import CompareRequest
        compare_service = get_compare_service()

        request = CompareRequest(
            text1=text1,
            text2=text2,
            compare_type=compare_type,
        )

        response = compare_service.compare(request)

        return {
            "success": True,
            "data": {
                "similarity": response.similarity,
                "diff_count": len(response.diffs),
                "diffs": [
                    {
                        "position": d.position,
                        "type": d.diff_type,
                        "severity": d.severity,
                    }
                    for d in response.diffs[:20]  # 限制返回数量
                ],
                "risk_clauses": response.risk_clauses[:10],
                "summary": response.summary,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"比对失败：{str(e)}",
        )


# ========== 智能客服 ==========

@router.post("/customer-service/chat")
async def customer_service_chat(
    message: str,
    session_id: Optional[str] = None,
    kb_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    智能客服聊天

    Args:
        message: 用户消息
        session_id: 会话 ID
        kb_id: 知识库 ID
    """
    from ..services.scenarios.smart 客服 import get_customer_service

    try:
        customer_service = get_customer_service()

        if not session_id:
            session_id = customer_service.create_session()

        result = await customer_service.chat(
            session_id=session_id,
            message=message,
            kb_id=kb_id,
        )

        return {
            "success": True,
            "session_id": result["session_id"],
            "response": result["response"],
            "intent": result["intent"],
            "suggestions": result["suggestions"],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天失败：{str(e)}",
        )


@router.post("/customer-service/session/create")
async def create_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建客服会话"""
    from ..services.scenarios.smart 客服 import get_customer_service

    customer_service = get_customer_service()
    session_id = customer_service.create_session(
        user_id=str(current_user.id)
    )

    return {
        "success": True,
        "session_id": session_id,
    }


# ========== 报告生成 ==========

@router.post("/report/generate")
async def generate_report(
    report_type: str,  # analysis, meeting, weekly, monthly
    title: str,
    data: dict,
    format: str = "markdown",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成报告

    Args:
        report_type: 报告类型
        title: 报告标题
        data: 报告数据
        format: 输出格式
    """
    from ..services.scenarios.report_generate import get_report_service

    try:
        from ..services.scenarios.report_generate import ReportRequest
        report_service = get_report_service()
        await report_service.initialize()

        request = ReportRequest(
            report_type=report_type,
            title=title,
            data=data,
            format=format,
        )

        response = await report_service.generate(request)

        return {
            "success": True,
            "data": {
                "report_id": response.report_id,
                "title": response.title,
                "content": response.content,
                "format": response.format,
                "sections": response.sections,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报告生成失败：{str(e)}",
        )


@router.post("/report/meeting-summary")
async def generate_meeting_summary(
    title: str,
    transcript: str,
    date: Optional[str] = None,
    attendees: List[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成会议纪要

    Args:
        title: 会议标题
        transcript: 会议记录
        date: 会议日期
        attendees: 参会人员
    """
    from ..services.scenarios.report_generate import get_report_service

    try:
        report_service = get_report_service()
        await report_service.initialize()

        response = await report_service.generate_meeting_summary(
            title=title,
            transcript=transcript,
            date=date,
            attendees=attendees,
        )

        return {
            "success": True,
            "data": {
                "report_id": response.report_id,
                "title": response.title,
                "content": response.content,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"会议纪要生成失败：{str(e)}",
        )


# ========== 场景列表 ==========

@router.get("/scenarios")
async def list_scenarios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取可用场景列表"""
    return {
        "success": True,
        "scenarios": [
            {
                "id": "document-qa",
                "name": "制度文档问答",
                "description": "基于 RAG 的智能问答系统",
                "endpoint": "/api/v1/scenarios/document-qa/query",
            },
            {
                "id": "contract-compare",
                "name": "合同文本比对",
                "description": "对比合同差异，识别风险条款",
                "endpoint": "/api/v1/scenarios/contract/compare",
            },
            {
                "id": "customer-service",
                "name": "智能客服",
                "description": "多轮对话、意图识别、知识检索",
                "endpoint": "/api/v1/scenarios/customer-service/chat",
            },
            {
                "id": "report-generate",
                "name": "报告生成",
                "description": "自动生成数据分析报告、会议纪要",
                "endpoint": "/api/v1/scenarios/report/generate",
            },
        ],
    }
