# tests/test_parser.py
import pytest
from aigc_reducer.parser import parse_document, Paragraph


class TestMarkdownParser:
    def test_parse_markdown_file(self, tmp_path):
        content = "# 标题\n\n这是第一段。\n\n这是第二段。\n"
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        paragraphs = parse_document(str(md_file))

        assert len(paragraphs) == 2
        assert paragraphs[0].text == "这是第一段。"
        assert paragraphs[1].text == "这是第二段。"

    def test_parse_markdown_skips_heading(self, tmp_path):
        content = "## 方法\n\n我们采用了以下方法。\n\n## 结果\n\n结果显示如下。"
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        paragraphs = parse_document(str(md_file))

        assert len(paragraphs) == 2
        assert all(not p.is_heading for p in paragraphs)

    def test_parse_markdown_preserves_formatting(self, tmp_path):
        content = "这是一个包含 **加粗** 和 *斜体* 的段落。\n\n公式 $E=mc^2$ 很重要。"
        md_file = tmp_path / "test.md"
        md_file.write_text(content, encoding="utf-8")

        paragraphs = parse_document(str(md_file))

        assert "**加粗**" in paragraphs[0].text
        assert "*斜体*" in paragraphs[0].text
        assert "$E=mc^2$" in paragraphs[1].text
