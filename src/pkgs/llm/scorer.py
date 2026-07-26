"""候选事件相关性/重要性打分 + 摘要（LLM + 降级）。"""
import json

from config.settings import settings
from pkgs.llm.client import SYSTEM_SCORE
from utils.logging import get_logger

logger = get_logger(__name__)


def _fallback_score(item, radar) -> tuple[float, str]:
    """无 LLM 时：雷达关键词与事件文本的命中比例。"""
    keywords = [str(k) for k in (radar.keywords or [])]
    text = f"{getattr(item, 'title', '')} {getattr(item, 'content', '') or ''}"
    if not keywords:
        return 0.5, getattr(item, "title", "")
    hit = sum(1 for k in keywords if k and k in text)
    rel = min(1.0, hit / len(keywords))
    return rel, getattr(item, "title", "")


async def score(item, radar, llm=None) -> tuple[float, str]:
    """返回 (relevance: float 0~1, summary: str)。llm=None 时降级。"""
    if llm is None or not getattr(llm, "available", True):
        return _fallback_score(item, radar)
    try:
        ctx = f"监控目标：{radar.raw_query}\n关键词：{radar.keywords}\n过滤：{radar.filters}"
        messages = [
            {"role": "system", "content": SYSTEM_SCORE},
            {"role": "user", "content": f"{ctx}\n\n候选事件：\n标题：{getattr(item, 'title', '')}\n内容：{getattr(item, 'content', '') or ''}"},
        ]
        content = await llm.complete(messages, json_mode=True)
        data = json.loads(content)
        rel = float(data.get("relevance", 0.0))
        rel = max(0.0, min(1.0, rel))
        return rel, data.get("summary", getattr(item, "title", ""))
    except Exception as exc:
        logger.warning("LLM 打分失败，降级关键词匹配: %s", exc)
        return _fallback_score(item, radar)
