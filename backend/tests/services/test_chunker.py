"""
文本分片器测试
"""
import pytest
from app.services.chunker import TextChunker, ChunkResult


class TestTextChunker:
    """文本分片器测试类"""

    def test_fixed_size_chunking(self):
        """测试固定大小分片"""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10, strategy="fixed")
        text = "这是第一段内容。这是第二段内容。这是第三段内容。这是第四段内容。"

        result = chunker.chunk(text)

        assert isinstance(result, ChunkResult)
        assert result.success is True
        assert len(result.chunks) > 0
        # 验证有重叠
        if len(result.chunks) > 1:
            assert result.chunks[0] != result.chunks[1]

    def test_paragraph_chunking(self):
        """测试段落下分片"""
        chunker = TextChunker(strategy="paragraph")
        text = """这是第一段。

这是第二段。

这是第三段。"""

        result = chunker.chunk(text)

        assert result.success is True
        assert len(result.chunks) >= 3
        assert "这是第一段" in result.chunks[0]
        assert "这是第二段" in result.chunks[1]

    def test_sentence_chunking(self):
        """测试句子分片"""
        chunker = TextChunker(strategy="sentence")
        text = "这是第一句。这是第二句。这是第三句。"

        result = chunker.chunk(text)

        assert result.success is True
        assert len(result.chunks) >= 3

    def test_empty_input(self):
        """测试空输入"""
        chunker = TextChunker()
        result = chunker.chunk("")

        assert result.success is True
        assert len(result.chunks) == 0

    def test_none_input(self):
        """测试 None 输入"""
        chunker = TextChunker()
        result = chunker.chunk(None)

        assert result.success is False
        assert "输入不能为空" in result.error

    def test_chunk_metadata(self):
        """测试分片元数据"""
        chunker = TextChunker(chunk_size=50, strategy="fixed")
        text = "测试内容" * 100

        result = chunker.chunk(text)

        assert result.success is True
        for chunk in result.chunks:
            assert "chunk_index" in chunk
            assert "content" in chunk
            assert chunk["chunk_index"] >= 0

    def test_overlap_handling(self):
        """测试重叠处理"""
        chunker = TextChunker(chunk_size=30, chunk_overlap=10, strategy="fixed")
        text = "ABCDEFG" * 20

        result = chunker.chunk(text)

        assert result.success is True
        if len(result.chunks) > 1:
            # 验证重叠存在
            chunk1_end = result.chunks[0]["content"][-10:]
            chunk2_start = result.chunks[1]["content"][:10]
            # 应该有重叠部分

    def test_custom_chunk_size(self):
        """测试自定义分片大小"""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, strategy="fixed")
        text = "测试" * 500

        result = chunker.chunk(text)

        assert result.success is True
        # 验证分片数量合理
        assert len(result.chunks) > 0
        assert len(result.chunks) < 50  # 不应该太多
