import pytest
from unittest.mock import MagicMock
from aigc_reducer_core.llm_client import LLMClient


@pytest.fixture
def mock_llm_client():
    client = MagicMock(spec=LLMClient)
    client.chat.return_value = "这是 mock 的改写结果文本。"
    return client
