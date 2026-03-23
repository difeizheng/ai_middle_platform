"""
场景 1: 制度文档问答服务
基于 RAG 的智能问答系统
"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ...core.logger import get_logger
from ...core.config import settings

logger = get_logger(__name__)


@dataclass
class QARequest:
    """问答请求"""
    question: str
    kb_id: Optional[int] = None
    top_k: int = 5
    history: List[Dict[str, str]] = None


@dataclass
class QAResponse:
    """问答响应"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    latency_ms: float


class DocumentQAService:
    """
    制度文档问答服务

    功能:
    1. 接收用户问题
    2. 从知识库检索相关内容
    3. 调用 LLM 生成答案
    4. 返回答案和来源
    """

    def __init__(self):
        self.embedding_service = None
        self.vector_store = None
        self.llm_service = None

    async def initialize(self):
        """初始化服务"""
        from ..embedding import EmbeddingService
        from ..vector_store import VectorStoreService
        from ..llm import LLMService

        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.llm_service = LLMService()

        await self.vector_store.connect()

    async def query(self, request: QARequest) -> QAResponse:
        """
        执行问答查询

        Args:
            request: 问答请求

        Returns:
            QAResponse: 问答响应
        """
        import time
        start_time = time.time()

        try:
            # Step 1: 问题向量化
            query_vector = await self._embed_question(request.question)

            # Step 2: 向量检索
            search_results = await self._search_knowledge(
                query_vector,
                top_k=request.top_k,
            )

            # Step 3: 构建上下文
            context = self._build_context(search_results)

            # Step 4: 调用 LLM 生成答案
            answer = await self._generate_answer(
                question=request.question,
                context=context,
                history=request.history,
            )

            # Step 5: 构建响应
            latency_ms = (time.time() - start_time) * 1000

            logger.info(f"问答查询完成：{request.question[:50]}... 延迟：{latency_ms:.2f}ms")

            return QAResponse(
                answer=answer,
                sources=[{"content": r.content, "score": r.score} for r in search_results],
                confidence=self._calculate_confidence(search_results),
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"问答查询失败：{e}")
            raise

    async def _embed_question(self, question: str) -> List[float]:
        """问题向量化"""
        result = await self.embedding_service.embed(question)
        return result.embedding

    async def _search_knowledge(
        self,
        query_vector: List[float],
        top_k: int,
    ):
        """从知识库检索"""
        return await self.vector_store.search(query_vector, top_k=top_k)

    def _build_context(self, search_results) -> str:
        """构建上下文"""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"[相关知识 {i}]\n{result.content}")

        return "\n\n".join(context_parts)

    async def _generate_answer(
        self,
        question: str,
        context: str,
        history: List[Dict[str, str]] = None,
    ) -> str:
        """调用 LLM 生成答案"""
        # 构建提示词
        system_prompt = """你是一个专业的制度文档问答助手。请根据提供的上下文信息，准确回答用户的问题。

要求：
1. 答案必须基于提供的上下文，不要编造信息
2. 如果上下文中没有相关信息，请如实告知
3. 回答要简洁明了，重点突出
4. 必要时可以引用原文"""

        user_prompt = f"""上下文信息：
{context}

用户问题：{question}"""

        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_prompt})

        # 调用 LLM
        response = await self.llm_service.chat(messages)
        return response.content

    def _calculate_confidence(self, search_results) -> float:
        """计算置信度"""
        if not search_results:
            return 0.0

        # 基于检索结果的相似度分数计算置信度
        max_score = max(r.score for r in search_results)
        avg_score = sum(r.score for r in search_results) / len(search_results)

        # 简单加权
        confidence = 0.6 * max_score + 0.4 * avg_score
        return min(confidence, 1.0)

    async def chat(
        self,
        question: str,
        kb_id: int = None,
        history: List[Dict[str, str]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        简化的聊天接口

        Args:
            question: 用户问题
            kb_id: 知识库 ID
            history: 历史对话
            top_k: 检索数量

        Returns:
            包含答案的字典
        """
        request = QARequest(
            question=question,
            kb_id=kb_id,
            top_k=top_k,
            history=history or [],
        )

        response = await self.query(request)

        return {
            "answer": response.answer,
            "sources": response.sources,
            "confidence": response.confidence,
            "latency_ms": response.latency_ms,
        }


# 全局服务实例
_qa_service: Optional[DocumentQAService] = None


def get_qa_service() -> DocumentQAService:
    """获取问答服务实例"""
    global _qa_service
    if _qa_service is None:
        _qa_service = DocumentQAService()
    return _qa_service
