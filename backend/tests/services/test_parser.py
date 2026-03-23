"""
文档解析器测试
"""
import pytest
import os
from io import BytesIO
from app.services.parser import DocumentParser, ParseResult


class TestDocumentParser:
    """文档解析器测试类"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return DocumentParser()

    def test_supported_formats(self, parser):
        """测试支持的格式"""
        assert ".pdf" in parser.supported_formats
        assert ".docx" in parser.supported_formats
        assert ".xlsx" in parser.supported_formats
        assert ".pptx" in parser.supported_formats
        assert ".txt" in parser.supported_formats
        assert ".md" in parser.supported_formats

    def test_parse_txt(self, parser, tmp_path):
        """测试 TXT 文件解析"""
        # 创建测试文件
        txt_file = tmp_path / "test.txt"
        content = "这是测试内容\n第二行内容\n第三行内容"
        txt_file.write_text(content, encoding="utf-8")

        # 解析文件
        result = parser.parse(str(txt_file))

        assert isinstance(result, ParseResult)
        assert result.success is True
        assert "这是测试内容" in result.content
        assert result.page_count == 1
        assert result.metadata["file_type"] == "txt"

    def test_parse_md(self, parser, tmp_path):
        """测试 Markdown 文件解析"""
        md_file = tmp_path / "test.md"
        content = "# 测试标题\n\n这是测试内容\n\n## 子标题\n\n更多内容"
        md_file.write_text(content, encoding="utf-8")

        result = parser.parse(str(md_file))

        assert result.success is True
        assert "# 测试标题" in result.content
        assert result.metadata["file_type"] == "md"

    def test_parse_unsupported_format(self, parser, tmp_path):
        """测试不支持的格式"""
        # 创建不支持的文件
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("test", encoding="utf-8")

        result = parser.parse(str(unsupported_file))

        assert result.success is False
        assert "不支持" in result.error

    def test_parse_nonexistent_file(self, parser):
        """测试不存在的文件"""
        result = parser.parse("/nonexistent/path/file.txt")

        assert result.success is False
        assert "不存在" in result.error or "not found" in result.error.lower()

    def test_parse_pdf_placeholder(self, parser, tmp_path):
        """测试 PDF 文件解析（占位测试）"""
        # 注意：实际测试需要真实的 PDF 文件
        # 这里验证解析器是否能正确识别 PDF 格式
        assert ".pdf" in parser.supported_formats
        # 实际 PDF 解析需要 pypdf 库

    def test_parse_docx_placeholder(self, parser, tmp_path):
        """测试 Word 文件解析（占位测试）"""
        # 注意：实际测试需要真实的 DOCX 文件
        assert ".docx" in parser.supported_formats
        # 实际 Word 解析需要 python-docx 库

    def test_get_file_info(self, parser, tmp_path):
        """测试获取文件信息"""
        txt_file = tmp_path / "test.txt"
        content = "测试内容"
        txt_file.write_text(content, encoding="utf-8")

        info = parser.get_file_info(str(txt_file))

        assert info["file_name"] == "test.txt"
        assert info["file_size"] > 0
        assert info["file_type"] == "txt"
