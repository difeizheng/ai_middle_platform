"""
智能体记忆管理
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import uuid

from ...core.logger import get_logger

logger = get_logger(__name__)


class MemoryType(Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"  # 短期记忆
    LONG_TERM = "long_term"    # 长期记忆
    EPISODIC = "episodic"      # 情景记忆
    SEMANTIC = "semantic"      # 语义记忆


@dataclass
class Memory:
    """记忆对象"""
    id: str
    agent_id: int
    session_id: str
    memory_type: MemoryType
    content: str
    embedding: Optional[List[float]] = None
    importance: int = 1  # 1-5
    access_count: int = 0
    created_at: float = 0
    last_accessed_at: float = 0
    expires_at: Optional[float] = None


class AgentMemoryManager:
    """
    智能体记忆管理器

    功能:
    - 短期记忆：最近对话历史
    - 长期记忆：持久化存储
    - 记忆检索：基于向量相似度
    - 记忆遗忘：基于重要性和时间
    """

    def __init__(
        self,
        agent_id: int,
        short_term_capacity: int = 10,
        long_term_capacity: int = 1000,
    ):
        self.agent_id = agent_id
        self.short_term_capacity = short_term_capacity
        self.long_term_capacity = long_term_capacity

        # 短期记忆（内存中）
        self.short_term_memories: List[Memory] = []

        # 长期记忆（持久化）
        self.long_term_memories: List[Memory] = []

    def add_short_term(
        self,
        content: str,
        session_id: Optional[str] = None,
    ) -> Memory:
        """
        添加短期记忆

        Args:
            content: 记忆内容
            session_id: 会话 ID

        Returns:
            Memory 记忆对象
        """
        memory = Memory(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            session_id=session_id or str(uuid.uuid4()),
            memory_type=MemoryType.SHORT_TERM,
            content=content,
            created_at=time.time(),
            last_accessed_at=time.time(),
        )

        self.short_term_memories.append(memory)

        # 限制容量
        if len(self.short_term_memories) > self.short_term_capacity:
            self.short_term_memories = self.short_term_memories[-self.short_term_capacity:]

        logger.debug(f"Added short-term memory: {memory.id}")
        return memory

    def add_long_term(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: int = 3,
        embedding: Optional[List[float]] = None,
        session_id: Optional[str] = None,
    ) -> Memory:
        """
        添加长期记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性评分 1-5
            embedding: 向量表示
            session_id: 会话 ID

        Returns:
            Memory 记忆对象
        """
        memory = Memory(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            session_id=session_id or str(uuid.uuid4()),
            memory_type=memory_type,
            content=content,
            embedding=embedding,
            importance=importance,
            created_at=time.time(),
            last_accessed_at=time.time(),
        )

        self.long_term_memories.append(memory)

        # 限制容量
        if len(self.long_term_memories) > self.long_term_capacity:
            self._forget_long_term_memories()

        logger.debug(f"Added long-term memory: {memory.id}")
        return memory

    def get_recent_memories(
        self,
        limit: int = 5,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Memory]:
        """
        获取最近的记忆

        Args:
            limit: 数量限制
            memory_type: 记忆类型

        Returns:
            List[Memory] 记忆列表
        """
        memories = []

        if memory_type is None or memory_type == MemoryType.SHORT_TERM:
            memories.extend(self.short_term_memories)

        if memory_type is None or memory_type == MemoryType.LONG_TERM:
            memories.extend(self.long_term_memories)

        # 按最后访问时间排序
        memories.sort(key=lambda m: m.last_accessed_at, reverse=True)

        return memories[:limit]

    def search_memories(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 5,
        min_importance: int = 1,
    ) -> List[Memory]:
        """
        搜索记忆

        Args:
            query: 搜索查询
            query_embedding: 查询向量
            limit: 返回数量
            min_importance: 最小重要性

        Returns:
            List[Memory] 匹配的记忆列表
        """
        # 过滤
        candidates = [
            m for m in self.long_term_memories
            if m.importance >= min_importance
        ]

        # 如果有向量，计算相似度
        if query_embedding:
            candidates = self._rank_by_similarity(candidates, query_embedding)

        # 更新时间
        for memory in candidates[:limit]:
            memory.access_count += 1
            memory.last_accessed_at = time.time()

        return candidates[:limit]

    def _rank_by_similarity(
        self,
        memories: List[Memory],
        query_embedding: List[float],
    ) -> List[Memory]:
        """按向量相似度排序"""
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            if not a or not b:
                return 0.0

            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5

            if norm_a == 0 or norm_b == 0:
                return 0.0

            return dot_product / (norm_a * norm_b)

        # 计算相似度
        scored = []
        for memory in memories:
            if memory.embedding:
                score = cosine_similarity(memory.embedding, query_embedding)
                scored.append((score, memory))
            else:
                scored.append((0.0, memory))

        # 按相似度排序
        scored.sort(key=lambda x: x[0], reverse=True)

        return [m for _, m in scored]

    def _forget_long_term_memories(self) -> None:
        """遗忘长期记忆（基于重要性和时间）"""
        current_time = time.time()

        # 计算遗忘分数
        def forgetting_score(memory: Memory) -> float:
            # 时间衰减
            age = current_time - memory.created_at
            time_decay = age / (3600 * 24)  # 天数

            # 使用频率
            frequency = memory.access_count / (time_decay + 1)

            # 综合分数（越低越容易被遗忘）
            return memory.importance * 0.5 + frequency * 0.3 - time_decay * 0.2

        # 排序并移除
        self.long_term_memories.sort(key=forgetting_score, reverse=True)
        self.long_term_memories = self.long_term_memories[:self.long_term_capacity]

        logger.info(f"Forget long-term memories, remaining: {len(self.long_term_memories)}")

    def clear_session(self, session_id: str) -> int:
        """
        清除会话记忆

        Args:
            session_id: 会话 ID

        Returns:
            清除的记忆数量
        """
        before = len(self.short_term_memories) + len(self.long_term_memories)

        self.short_term_memories = [
            m for m in self.short_term_memories if m.session_id != session_id
        ]
        self.long_term_memories = [
            m for m in self.long_term_memories if m.session_id != session_id
        ]

        after = len(self.short_term_memories) + len(self.long_term_memories)
        return before - after

    def get_summary(self) -> Dict[str, Any]:
        """获取记忆摘要"""
        return {
            "agent_id": self.agent_id,
            "short_term_count": len(self.short_term_memories),
            "long_term_count": len(self.long_term_memories),
            "total_count": len(self.short_term_memories) + len(self.long_term_memories),
            "memory_types": {
                "short_term": len([m for m in self.short_term_memories]),
                "episodic": len([m for m in self.long_term_memories if m.memory_type == MemoryType.EPISODIC]),
                "semantic": len([m for m in self.long_term_memories if m.memory_type == MemoryType.SEMANTIC]),
            },
        }

    def export_memories(self) -> List[Dict]:
        """导出记忆"""
        memories = self.short_term_memories + self.long_term_memories
        return [
            {
                "id": m.id,
                "agent_id": m.agent_id,
                "session_id": m.session_id,
                "memory_type": m.memory_type.value,
                "content": m.content,
                "importance": m.importance,
                "access_count": m.access_count,
                "created_at": m.created_at,
                "last_accessed_at": m.last_accessed_at,
            }
            for m in memories
        ]

    def import_memories(self, memories: List[Dict]) -> int:
        """导入记忆"""
        count = 0
        for m in memories:
            memory = Memory(
                id=m.get("id", str(uuid.uuid4())),
                agent_id=self.agent_id,
                session_id=m.get("session_id", ""),
                memory_type=MemoryType(m.get("memory_type", "episodic")),
                content=m.get("content", ""),
                importance=m.get("importance", 1),
                access_count=m.get("access_count", 0),
                created_at=m.get("created_at", time.time()),
                last_accessed_at=m.get("last_accessed_at", time.time()),
            )

            if memory.memory_type == MemoryType.SHORT_TERM:
                self.short_term_memories.append(memory)
            else:
                self.long_term_memories.append(memory)

            count += 1

        return count
