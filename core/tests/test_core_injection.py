# tests/test_core_injection.py — 核心注入、取消机制、数据加载等测试
import os
import threading

import pytest
from unittest.mock import MagicMock

from aigc_reducer_core import CancelledError
from aigc_reducer_core.llm_client import LLMClient
from aigc_reducer_core.parser import Paragraph
from aigc_reducer_core.rewriter import Rewriter
from aigc_reducer_core.styles.base import RewriteStyle
from aigc_reducer_core.styles import AcademicHumanisticStyle
from aigc_reducer_core.detector import AIGCDetector
from aigc_reducer_core.detectors import ConnectorDetector


class TestLLMClientInjection:
    """RewriteStyle 使用注入的 LLM client 而非 from_env()。"""

    def test_llm_client_injection(self, mock_llm_client):
        style = AcademicHumanisticStyle(llm_client=mock_llm_client)
        # 调用改写，应该走 mock 而非真实的 from_env()
        result = style.rewrite_paragraph("这是测试文本。", {})
        assert result == "这是 mock 的改写结果文本。"
        mock_llm_client.chat.assert_called_once()

    def test_llm_client_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "test/model")
        monkeypatch.setenv("LLM_API_KEY", "sk-test-key")

        client = LLMClient.from_env()
        assert client.model == "test/model"

    def test_llm_client_model_property(self):
        client = LLMClient(model="test/model", api_key="sk-test")
        assert client.model == "test/model"


class TestConnectorDetectorDataPath:
    """ConnectorDetector 能正常加载数据文件。"""

    def test_connector_detector_data_path(self):
        # 应该能正常初始化，不抛异常
        detector = ConnectorDetector()
        assert detector._data is not None
        assert "connectors" in detector._data


class TestDetectorCancel:
    """设置 cancel_event 后 AIGCDetector.analyze_all 在检查点中断。"""

    def test_detector_cancel(self):
        cancel_event = threading.Event()
        cancel_event.set()  # 预先设置为取消状态

        detector = AIGCDetector(cancel_event=cancel_event)
        paragraphs = [
            Paragraph(text="这是测试段落。", index=0),
            Paragraph(text="这是第二段。", index=1),
        ]

        with pytest.raises(CancelledError, match="检测已取消"):
            detector.analyze_all(paragraphs)


class TestRewriterCancel:
    """设置 cancel_event 后 Rewriter.rewrite_all 在检查点中断。"""

    def test_rewriter_cancel(self, mock_llm_client):
        cancel_event = threading.Event()
        cancel_event.set()  # 预先设置为取消状态

        rewriter = Rewriter("学术人文化", llm_client=mock_llm_client, cancel_event=cancel_event)
        paragraphs = [
            Paragraph(text="这是测试段落。", index=0),
            Paragraph(text="这是第二段。", index=1),
        ]

        with pytest.raises(CancelledError, match="改写已取消"):
            rewriter.rewrite_all(paragraphs)
