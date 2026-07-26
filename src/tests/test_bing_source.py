"""Bing 网页搜索源测试：默认源切换 + HTML 解析 + 可达性。"""
import urllib.parse

from business.monitor.sources import (
    BingWebSource,
    build_source,
    default_news_source,
    is_fetchable,
)
from business.monitor.sources.bing import BingWebSource as _B


def test_default_news_source_is_bing():
    spec = default_news_source("英伟达 财报 股价")
    assert spec["type"] == "bing"
    assert "bing.com/search" in spec["url"]
    assert "q=" in spec["url"]


def test_bing_is_fetchable():
    assert is_fetchable({"type": "bing", "url": "https://www.bing.com/search?q=x"})
    # 无 url 的 bing 不可抓（会回落到默认源）
    assert not is_fetchable({"type": "bing", "url": ""})


def test_build_source_bing():
    src = build_source({"type": "bing", "query": "OpenAI", "url": "https://www.bing.com/search?q=OpenAI"})
    assert isinstance(src, BingWebSource)
    assert src.source_id() == "bing:OpenAI"


def test_bing_parse_extracts_items():
    html = """
    <li class="b_algo"><h2><a href="https://example.com/a">示例标题一</a></h2>
      <p class="b_lineclamp2">这是摘要&ensp;&#0183;&ensp;包含要点。</p></li>
    <li class="b_algo"><h2><a href="https://example.com/b">示例标题二</a></h2>
      <p>第二段摘要</p></li>
    """
    items = _B(url="https://www.bing.com/search?q=x", query="x")._parse(html)
    assert len(items) == 2
    assert items[0].title == "示例标题一"
    assert items[0].url == "https://example.com/a"
    # HTML 实体被解码、空白被规整
    assert "示例标题一" in items[0].title
    assert "要点" in items[0].content and "&ensp;" not in items[0].content


def test_bing_decode_redirect():
    # Bing 跳转链接中的 u=a1<base64url> 应解出真实 URL
    real = "https://www.nvidia.com/"
    import base64

    enc = "a1" + base64.urlsafe_b64encode(real.encode()).decode()
    hop = f"https://www.bing.com/ck/a?u={enc}"
    assert _B._decode_redirect(hop) == real
    # 非跳转链接原样返回
    assert _B._decode_redirect("https://example.com/x") == "https://example.com/x"
