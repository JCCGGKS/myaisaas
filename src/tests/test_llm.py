"""pkgs/llm 单元测试：解析 / 打分 / 降级（FakeLLM 注入，不联网）。"""
import asyncio

from pkgs.llm.client import FakeLLM
from pkgs.llm.parser import parse_query
from pkgs.llm.scorer import score


class _Item:
    def __init__(self, title, content=""):
        self.title = title
        self.content = content


class _Radar:
    def __init__(self, keywords, raw_query="", filters=None):
        self.keywords = keywords
        self.raw_query = raw_query
        self.filters = filters or {}


def test_parse_fallback_no_llm():
    r = asyncio.run(parse_query("LISA 演唱会与新歌动态", llm=None))
    assert "LISA" in r["keywords"]
    assert r["sources"][0]["type"] == "web"
    assert r["filters"] == {}


def test_parse_with_llm():
    fake = FakeLLM(
        responder=lambda m, j: '{"keywords":["A","B"],"sources":[{"type":"rss","url":"http://x"}],"filters":{"lang":"zh"}}'
    )
    r = asyncio.run(parse_query("anything", llm=fake))
    assert r["keywords"] == ["A", "B"]
    assert r["sources"][0]["type"] == "rss"
    assert r["filters"] == {"lang": "zh"}


def test_score_fallback_keyword_hit():
    radar = _Radar(keywords=["LISA"])
    rel, summ = asyncio.run(score(_Item("LISA 演唱会官宣"), radar, llm=None))
    assert rel == 1.0


def test_score_fallback_no_keywords():
    radar = _Radar(keywords=[])
    rel, summ = asyncio.run(score(_Item("随便"), radar, llm=None))
    assert rel == 0.5  # 无关键词时给中性分，交由阈值判断


def test_score_with_llm():
    fake = FakeLLM(responder=lambda m, j: '{"relevance":0.8,"summary":"摘要"}')
    radar = _Radar(keywords=[])
    rel, summ = asyncio.run(score(_Item("t"), radar, llm=fake))
    assert rel == 0.8 and summ == "摘要"
