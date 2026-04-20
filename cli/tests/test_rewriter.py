import pytest
from aigc_reducer.rewriter import Rewriter, list_styles


class TestRewriter:
    def setup_method(self):
        self.rewriter = Rewriter("学术人文化")

    def test_list_styles_returns_all_5(self):
        styles = list_styles()
        assert len(styles) == 5
        assert "口语化" in styles
        assert "文言文化" in styles
        assert "中英混杂化" in styles
        assert "学术人文化" in styles
        assert "粗犷草稿风" in styles

    def test_unknown_style_raises(self):
        with pytest.raises(ValueError, match="未知风格"):
            Rewriter("不存在的风格")

    def test_rewrite_returns_same_length(self):
        from aigc_reducer.parser import Paragraph
        paragraphs = [
            Paragraph(text="这是第一段。", index=0),
            Paragraph(text="这是第二段。", index=1),
        ]
        results = self.rewriter.rewrite_all(paragraphs)
        assert len(results) == 2
