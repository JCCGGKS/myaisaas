"""Event 模型：命中的候选事件（标题、来源、相关性分、摘要）。

- dedup_key：雷达内唯一指纹（来源归一化），用于去重，避免同一事件重复推送
- pushed_channels：已推送到的渠道列表（配合 Notification 防重发）
- is_read：前端已读状态（可选）
"""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.types import JSON

from model.base import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("radar_id", "dedup_key", name="uq_event_radar_dedup"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    radar_id = Column(Integer, ForeignKey("radars.id"), index=True, nullable=False)
    dedup_key = Column(String(128), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    source_url = Column(String(1024), nullable=True)
    relevance_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    pushed = Column(DateTime(timezone=True), nullable=True)  # 首次推送时间
    pushed_channels = Column(JSON, default=list, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
