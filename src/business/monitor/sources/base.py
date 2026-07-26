"""数据源连接器基类与原始条目。

- RawItem：抓取/接收得到的原始候选条目（尚未打分/去重）。
- Source：各数据源实现 fetch(state) → list[RawItem]；支持注入 Fake 便于测试。
- make_dedup_key：由 source_id + url/title 生成雷达内唯一指纹。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib


@dataclass
class RawItem:
    title: str
    url: str | None
    content: str
    source_id: str  # 数据源实例唯一标识，如 "rss:https://..."


class Source(ABC):
    source_type: str = "base"

    @abstractmethod
    async def fetch(self, state: dict | None = None) -> list[RawItem]:
        ...

    def source_id(self) -> str:
        return self.source_type


def make_dedup_key(source_id: str, url: str | None, title: str) -> str:
    raw = f"{source_id}|{url or ''}|{title or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32]
