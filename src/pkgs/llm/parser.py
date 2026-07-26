"""自然语言 → 结构化雷达参数（LLM 解析 + 降级）。"""
import json
import re

from pkgs.llm.client import SYSTEM_PARSE
from utils.logging import get_logger

logger = get_logger(__name__)


def _fallback_parse(text: str) -> dict:
    """无 LLM 时：按标点粗分关键词，默认走 web 源。"""
    keywords = [k.strip() for k in re.split(r"[\s,，。、；;]+", text) if k.strip()]
    return {"keywords": keywords[:10], "sources": [{"type": "web", "query": text}], "filters": {}}


async def parse_query(text: str, llm=None) -> dict:
    """把用户自然语言解析为 {keywords, sources, filters}。llm=None 时降级。"""
    if llm is None or not getattr(llm, "available", True):
        return _fallback_parse(text)
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PARSE},
            {"role": "user", "content": text},
        ]
        content = await llm.complete(messages, json_mode=True)
        data = json.loads(content)
        return {
            "keywords": list(data.get("keywords") or []),
            "sources": list(data.get("sources") or [{"type": "web", "query": text}]),
            "filters": dict(data.get("filters") or {}),
        }
    except Exception as exc:
        logger.warning("LLM 解析失败，降级为关键词: %s", exc)
        return _fallback_parse(text)
