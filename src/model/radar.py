"""Radar 模型：监控目标 = 原始描述 + 结构化参数；有状态、增量盯防。"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON

from model.base import Base


class Radar(Base):
    __tablename__ = "radars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    raw_query = Column(Text, nullable=False)  # 用户原始自然语言
    # LLM 解析后的结构化参数（MVP 暂留空，后续监控循环填充）
    keywords = Column(JSON, default=list, nullable=False)
    sources = Column(JSON, default=list, nullable=False)
    filters = Column(JSON, default=dict, nullable=False)
    notify_channel = Column(String(32), default="", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
