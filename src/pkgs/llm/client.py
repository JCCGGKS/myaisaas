"""LLM 客户端（OpenAI 兼容接口），可切 Claude / 国产模型。

- `LLMClient`：真实调用 /v1/chat/completions；未配置 api_key 时 `available=False`，
  调用方应走降级逻辑（见 pkgs/llm/parser、pkgs/llm/scorer）。
- `FakeLLM`：测试注入，按 `responder` 返回固定 JSON，不真正联网。
"""
import json

import httpx

from config.settings import settings
from utils.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PARSE = (
    "你是监控雷达助理。把用户的自然语言监控需求解析为 JSON："
    '{"keywords":[str], "sources":[{"type":"rss"|"web", "url"?:str, "query"?:str}], '
    '"filters":{"lang"?:str, "exclude"?:[str]}}。只输出 JSON，不要解释。'
)
SYSTEM_SCORE = (
    "你是事件相关性评判。给定雷达监控目标与一条候选事件，输出 JSON："
    '{"relevance": float(0~1), "summary": str(中文一句话摘要)}。只输出 JSON。'
)


class LLMClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout = timeout or settings.llm_timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, messages: list[dict], json_mode: bool = False) -> str:
        if not self.available:
            raise RuntimeError("LLM 未配置（llm_api_key 为空）")
        payload: dict = {"model": self.model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # 网络/限流等：交给上层降级
            logger.error("LLM 调用失败: %s", exc)
            raise


class FakeLLM:
    """测试用：按 responder(messages, json_mode) 返回内容，不联网。"""

    def __init__(self, responder=None):
        self.responder = responder or (lambda messages, json_mode: json.dumps({"keywords": [], "sources": [], "filters": {}}))
        self.calls: list = []

    @property
    def available(self) -> bool:
        return True

    async def complete(self, messages: list[dict], json_mode: bool = False) -> str:
        self.calls.append((messages, json_mode))
        return self.responder(messages, json_mode)
