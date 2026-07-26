"""Notification 模型：已推送记录，防重发。"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from model.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True, nullable=False)
    channel = Column(String(32), nullable=False)
    recipient = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
