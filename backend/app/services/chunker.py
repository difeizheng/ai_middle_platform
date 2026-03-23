"""
文本分片服务
支持多种分片策略：固定长度、按段落、按句子、语义分片
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass

from ..core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """分片数据"""
    content: str
    start_pos: int
    end_pos: int
    chunk_index: int
    metadata: Dict[str, Any]


class TextChunker:
    """
    文本分片器
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        strategy: str = "semantic",
    ):
        """
        Args:
            chunk_size: 分片大小（字符数）
            chunk_overlap: 分片重叠（字符数）
            strategy: 分片策略 (fixed, paragraph, sentence, semantic)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        将文本分片

        Args:
            text: 待分片的文本
            metadata: 元数据

        Returns:
            分片列表
        """
        metadata = metadata or {}

        if self.strategy == "fixed":
            chunks = self._chunk_fixed(text, metadata)
        elif self.strategy == "paragraph":
            chunks = self._chunk_paragraph(text, metadata)
        elif self.strategy == "sentence":
            chunks = self._chunk_sentence(text, metadata)
        elif self.strategy == "semantic":
            chunks = self._chunk_semantic(text, metadata)
        else:
            chunks = self._chunk_fixed(text, metadata)

        logger.info(f"文本分片完成：{len(text)} 字符 -> {len(chunks)} 个分片")

        return chunks

    def _chunk_fixed(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """固定长度分片"""
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_content = text[start:end]

            chunks.append(Chunk(
                content=chunk_content,
                start_pos=start,
                end_pos=end,
                chunk_index=index,
                metadata={
                    **metadata,
                    "strategy": "fixed",
                    "chunk_size": len(chunk_content),
                },
            ))

            start = end - self.chunk_overlap
            index += 1

        return chunks

    def _chunk_paragraph(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """按段落分片"""
        # 按空行分割段落
        paragraphs = re.split(r"\n\s*\n", text)

        chunks = []
        current_content = ""
        current_start = 0
        index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_start = text.find(para, current_start)

            if len(current_content) + len(para) > self.chunk_size:
                # 当前分片已满，创建新分片
                if current_content:
                    chunks.append(Chunk(
                        content=current_content,
                        start_pos=current_start,
                        end_pos=current_start + len(current_content),
                        chunk_index=index,
                        metadata={**metadata, "strategy": "paragraph"},
                    ))
                    index += 1

                current_content = para
                current_start = para_start
            else:
                if current_content:
                    current_content += "\n\n" + para
                else:
                    current_content = para
                    current_start = para_start

        # 添加最后一个分片
        if current_content:
            chunks.append(Chunk(
                content=current_content,
                start_pos=current_start,
                end_pos=current_start + len(current_content),
                chunk_index=index,
                metadata={**metadata, "strategy": "paragraph"},
            ))

        return chunks

    def _chunk_sentence(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """按句子分片"""
        # 中文句子分割
        sentences = re.split(r"([。！？!?；;])", text)

        chunks = []
        current_content = ""
        current_start = 0
        index = 0
        pos = 0

        for sentence in sentences:
            if not sentence.strip():
                pos += len(sentence)
                continue

            if len(current_content) + len(sentence) > self.chunk_size:
                if current_content:
                    chunks.append(Chunk(
                        content=current_content,
                        start_pos=current_start,
                        end_pos=current_start + len(current_content),
                        chunk_index=index,
                        metadata={**metadata, "strategy": "sentence"},
                    ))
                    index += 1

                current_content = sentence
                current_start = pos
            else:
                current_content += sentence

            pos += len(sentence)

        if current_content:
            chunks.append(Chunk(
                content=current_content,
                start_pos=current_start,
                end_pos=current_start + len(current_content),
                chunk_index=index,
                metadata={**metadata, "strategy": "sentence"},
            ))

        return chunks

    def _chunk_semantic(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """
        语义分片（简化版）
        结合段落和句子分割，尽量保持语义完整性
        """
        # 先按段落分割
        paragraphs = re.split(r"\n\s*\n", text)

        chunks = []
        current_content = ""
        current_start = 0
        index = 0
        pos = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                pos += len(para)
                continue

            # 如果段落本身就很长，需要进一步按句子分割
            if len(para) > self.chunk_size:
                # 先保存当前累积的内容
                if current_content:
                    chunks.append(Chunk(
                        content=current_content,
                        start_pos=current_start,
                        end_pos=current_start + len(current_content),
                        chunk_index=index,
                        metadata={**metadata, "strategy": "semantic"},
                    ))
                    index += 1
                    current_content = ""

                # 对长段落进行句子分割
                sub_chunks = self._chunk_sentence(para, {**metadata, "source": "paragraph"})
                for sub_chunk in sub_chunks:
                    chunks.append(Chunk(
                        content=sub_chunk.content,
                        start_pos=pos + sub_chunk.start_pos,
                        end_pos=pos + sub_chunk.end_pos,
                        chunk_index=index,
                        metadata={**metadata, "strategy": "semantic", "sub_chunk": True},
                    ))
                    index += 1
            else:
                # 段落长度适中，直接累积
                if current_content:
                    current_content += "\n\n" + para
                else:
                    current_content = para
                    current_start = pos

                # 检查是否超过阈值
                if len(current_content) >= self.chunk_size * 0.8:
                    chunks.append(Chunk(
                        content=current_content,
                        start_pos=current_start,
                        end_pos=current_start + len(current_content),
                        chunk_index=index,
                        metadata={**metadata, "strategy": "semantic"},
                    ))
                    index += 1
                    current_content = ""

            pos += len(para)

        # 添加最后一个分片
        if current_content:
            chunks.append(Chunk(
                content=current_content,
                start_pos=current_start,
                end_pos=current_start + len(current_content),
                chunk_index=index,
                metadata={**metadata, "strategy": "semantic"},
            ))

        return chunks

    def chunk_to_dict(self, chunk: Chunk) -> Dict[str, Any]:
        """将分片转换为字典"""
        return {
            "content": chunk.content,
            "start_pos": chunk.start_pos,
            "end_pos": chunk.end_pos,
            "chunk_index": chunk.chunk_index,
            "metadata": chunk.metadata,
        }
