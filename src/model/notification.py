"""Notification 模型：已推送记录，防重发。"""
from sqlalchemy import Column, DateTime, Integer, String, func

from model.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 不使用外键约束；event_id 仅作逻辑关联（自增主键 id 已存在）
    event_id = Column(Integer, index=True, nullable=False)
    channel = Column(String(32), nullable=False)
    recipient = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
