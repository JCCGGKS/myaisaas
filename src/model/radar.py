"""Radar 模型：监控目标 = 原始描述 + 结构化参数；有状态、增量盯防。

- raw_query：用户原始自然语言
- keywords / sources / filters：LLM 解析后的结构化参数
- notify_channels：本雷达绑定的推送渠道（多通道，list[str]）
- scan_state：增量游标（各数据源的 last_seen），避免重复抓取
- status：active / paused / error（业务开关 active 与 status 解耦）
- last_scan_at / last_error：监控运行诊断
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.types import JSON

from model.base import Base


class Radar(Base):
    __tablename__ = "radars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 不使用外键约束；owner_id 仅作逻辑关联（自增主键 id 已存在）
    owner_id = Column(Integer, index=True, nullable=False)
    raw_query = Column(Text, nullable=False)  # 用户原始自然语言
    # LLM 解析后的结构化参数
    keywords = Column(JSON, default=list, nullable=False)
    sources = Column(JSON, default=list, nullable=False)
    filters = Column(JSON, default=dict, nullable=False)
    # 多通道：本雷达绑定的推送渠道类型列表
    notify_channels = Column(JSON, default=list, nullable=False)
    # 监控增量游标：{ "<source_id>": "<last_seen_token>" }
    scan_state = Column(JSON, default=dict, nullable=False)
    status = Column(String(16), default="active", nullable=False)  # active | paused | error
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # 软删除标记：非空即已删除
    created_at = Column(DateTime(timezone=True), server_default=func.now())
