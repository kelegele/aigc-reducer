"""LLM 客户端 — 基于 LiteLLM 统一接口，支持所有主流供应商。

支持的供应商（通过 model 参数切换）：
  - deepseek/deepseek-chat
  - qwen/qwen-plus, qwen/qwen-max（通义千问）
  - zhipu/glm-4, zhipu/glm-4-flash（智谱）
  - openai/gpt-4o, openai/gpt-4o-mini
  - anthropic/claude-sonnet-4-6, anthropic/claude-3-5-sonnet
  - together_ai/*（聚合多模型平台）

环境变量：
  LLM_MODEL        — 模型标识，格式为 "供应商/模型名"（必需）
  LLM_API_KEY      — API 密钥（必需，不同供应商 key 不同）
  LLM_BASE_URL     — 自定义 API 端点（可选，部分供应商需要）

使用示例：
  export LLM_MODEL=deepseek/deepseek-chat
  export LLM_API_KEY=sk-xxx
  # 调用即可

  export LLM_MODEL=qwen/qwen-plus
  export LLM_API_KEY=sk-xxx
  # 通义千问，API key 从阿里云获取

  export LLM_MODEL=zhipu/glm-4
  export LLM_API_KEY=xxx
  # 智谱，API key 从智谱开放平台获取
"""

import logging
import os
import time

from litellm import completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一个专业的学术论文改写助手。"
    "请严格按照用户要求的风格改写文本，保持学术严谨性和核心内容不变。"
    "只输出改写后的文本，不要添加任何解释。"
)


# 供应商默认 base_url（可通过 LLM_BASE_URL 覆盖）
PROVIDER_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}


class LLMClient:
    """统一的 LLM 客户端，基于 LiteLLM 支持所有主流供应商。"""

    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url

    @property
    def model(self) -> str:
        """当前使用的模型标识。"""
        return self._model

    @classmethod
    def from_env(cls) -> "LLMClient":
        """从环境变量创建客户端。

        必需环境变量：
          LLM_MODEL    — 模型标识，格式 "供应商/模型名"
          LLM_API_KEY  — API 密钥
        可选：
          LLM_BASE_URL — 自定义 API 端点，不配置则根据供应商默认值
        """
        model = os.environ.get("LLM_MODEL")
        if not model:
            raise ValueError(
                "缺少 LLM_MODEL 环境变量。\n"
                "设置示例：\n"
                '  export LLM_MODEL=deepseek/deepseek-chat\n'
                '  export LLM_MODEL=qwen/qwen-plus\n'
                '  export LLM_MODEL=zhipu/glm-4'
            )

        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise ValueError("缺少 LLM_API_KEY 环境变量")

        # 优先用环境变量，否则根据供应商前缀匹配默认 URL
        base_url = os.environ.get("LLM_BASE_URL")
        if not base_url:
            provider = model.split("/")[0].lower()
            base_url = PROVIDER_BASE_URLS.get(provider)

        return cls(model=model, api_key=api_key, base_url=base_url)

    def chat(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        """发送对话请求，返回响应文本。"""
        kwargs = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
        }

        if self._api_key:
            kwargs["api_key"] = self._api_key

        if self._base_url:
            kwargs["api_base"] = self._base_url

        t0 = time.time()
        prompt_len = len(prompt)
        try:
            response = completion(**kwargs)
            result = response.choices[0].message.content.strip()
            elapsed = time.time() - t0
            usage = getattr(response, "usage", None)
            usage_info = ""
            if usage:
                usage_info = f" in={usage.prompt_tokens} out={usage.completion_tokens}"
            logger.info(
                "[LLM] model=%s prompt=%d chars%s result=%d chars elapsed=%.1fs",
                self._model, prompt_len, usage_info, len(result), elapsed,
            )
            return result
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(
                "[LLM] model=%s prompt=%d chars FAILED after %.1fs: %s",
                self._model, prompt_len, elapsed, e,
            )
            raise
