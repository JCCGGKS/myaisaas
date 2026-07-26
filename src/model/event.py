"""Event 模型：命中的候选事件（标题、来源、相关性分、摘要）。"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from model.base import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    radar_id = Column(Integer, ForeignKey("radars.id"), index=True, nullable=False)
    title = Column(String(512), nullable=False)
    source_url = Column(String(1024), nullable=True)
    relevance_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    pushed = Column(DateTime(timezone=True), nullable=True)  # 已推送时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
