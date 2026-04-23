import pytest
from aigc_reducer_core.rewriter import Rewriter, list_styles


class TestRewriter:
    def setup_method(self, mock_llm_client):
        self.rewriter = Rewriter("学术人文化", llm_client=mock_llm_client)

    def test_list_styles_returns_all_5(self):
        styles = list_styles()
        assert len(styles) == 5
        assert "口语化" in styles
        assert "文言文化" in styles
        assert "中英混杂化" in styles
        assert "学术人文化" in styles
        assert "粗犷草稿风" in styles

    def test_unknown_style_raises(self, mock_llm_client):
        with pytest.raises(ValueError, match="未知风格"):
            Rewriter("不存在的风格", llm_client=mock_llm_client)

    def test_rewrite_returns_same_length(self):
        from aigc_reducer_core.parser import Paragraph
        paragraphs = [
            Paragraph(text="这是第一段。", index=0),
            Paragraph(text="这是第二段。", index=1),
        ]
        results = self.rewriter.rewrite_all(paragraphs)
        assert len(results) == 2
