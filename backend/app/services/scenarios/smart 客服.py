"""
场景 3: 智能客服服务
多轮对话、意图识别、知识检索
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from ...core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    """聊天会话"""
    session_id: str
    user_id: Optional[str]
    messages: List[ChatMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class SmartCustomerService:
    """
    智能客服服务

    功能:
    1. 多轮对话管理
    2. 意图识别
    3. 知识检索
    4. 人工转接
    """

    def __init__(self):
        # 会话存储
        self.sessions: Dict[str, ChatSession] = {}

        # 意图分类
        self.intents = {
            "greeting": ["你好", "您好", "hello", "hi", "早上好", "下午好"],
            "goodbye": ["再见", "拜拜", "下次聊", "先这样"],
            "thanks": ["谢谢", "感谢", "太感谢了"],
            "complaint": ["投诉", "举报", "不满", "失望"],
            "human": ["转人工", "人工客服", "找人工", "客服"],
        }

        # 常见问题答案
        self.faq = {
            "greeting": "您好！我是 AI 客服助手，很高兴为您服务。请问有什么可以帮您？",
            "goodbye": "感谢您的咨询，祝您生活愉快！如有其他问题，随时联系我们。",
            "thanks": "不客气！如果还有其他问题，请随时告诉我。",
            "default": "抱歉，我没有理解您的问题。您可以尝试换个方式提问，或者输入'转人工'获取人工服务。",
        }

    def create_session(self, user_id: str = None) -> str:
        """创建新会话"""
        import uuid
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        self.sessions[session_id] = ChatSession(
            session_id=session_id,
            user_id=user_id,
        )

        logger.info(f"创建新会话：{session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str):
        """添加消息到会话"""
        session = self.sessions.get(session_id)
        if session:
            session.messages.append(ChatMessage(role=role, content=content))
            session.updated_at = datetime.now()

    async def chat(
        self,
        session_id: str,
        message: str,
        kb_id: int = None,
    ) -> Dict[str, Any]:
        """
        聊天接口

        Args:
            session_id: 会话 ID
            message: 用户消息
            kb_id: 知识库 ID

        Returns:
            响应
        """
        # 获取或创建会话
        session = self.get_session(session_id)
        if not session:
            session_id = self.create_session()
            session = self.get_session(session_id)

        # 添加用户消息
        self.add_message(session_id, "user", message)

        # 意图识别
        intent = self._recognize_intent(message)

        # 根据意图处理
        if intent == "human":
            # 转人工
            response = await self._transfer_to_human(session_id)
        elif intent in self.faq:
            # 常见问题
            response = self.faq[intent]
        elif intent == "complaint":
            # 投诉处理
            response = await self._handle_complaint(session_id, message)
        else:
            # 知识检索问答
            response = await self._qa_response(session_id, message, kb_id)

        # 添加助手回复
        self.add_message(session_id, "assistant", response)

        return {
            "session_id": session_id,
            "response": response,
            "intent": intent,
            "suggestions": self._get_suggestions(intent),
        }

    def _recognize_intent(self, message: str) -> str:
        """意图识别"""
        message_lower = message.lower()

        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent

        return "unknown"

    async def _transfer_to_human(self, session_id: str) -> str:
        """转人工客服"""
        # 记录转人工请求
        session = self.get_session(session_id)
        logger.info(f"用户 {session.user_id} 请求转人工客服")

        # 实际实现应该通知人工客服系统
        return "好的，正在为您转接人工客服，请稍候。当前排队人数：0 人，预计等待时间：1 分钟。"

    async def _handle_complaint(self, session_id: str, message: str) -> str:
        """处理投诉"""
        session = self.get_session(session_id)

        # 记录投诉
        logger.warning(f"收到用户投诉：{message[:100]}...")

        return "非常抱歉给您带来不好的体验。我们已经记录您的反馈，客服人员会在 24 小时内与您联系处理。请问还有其他可以帮您的吗？"

    async def _qa_response(
        self,
        session_id: str,
        message: str,
        kb_id: int = None,
    ) -> str:
        """知识检索问答"""
        # 使用文档问答服务
        from .document_qa import get_qa_service

        try:
            qa_service = get_qa_service()
            result = await qa_service.chat(
                question=message,
                kb_id=kb_id,
                history=[
                    {"role": m.role, "content": m.content}
                    for m in self.get_session(session_id).messages[:-1]
                ],
            )
            return result["answer"]
        except Exception as e:
            logger.error(f"知识检索失败：{e}")
            return self.faq["default"]

    def _get_suggestions(self, intent: str) -> List[str]:
        """获取建议问题"""
        suggestions_map = {
            "greeting": ["产品介绍", "服务时间", "联系方式"],
            "unknown": ["如何注册", "产品价格", "售后服务"],
            "complaint": ["投诉进度查询", "退款申请", "问题升级"],
        }
        return suggestions_map.get(intent, ["查看更多帮助"])


# 全局服务实例
_customer_service: Optional[SmartCustomerService] = None


def get_customer_service() -> SmartCustomerService:
    """获取客服服务实例"""
    global _customer_service
    if _customer_service is None:
        _customer_service = SmartCustomerService()
    return _customer_service
