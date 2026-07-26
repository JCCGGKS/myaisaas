"""User 模型：身份 + 游客标记 + 渠道绑定（渠道无关）。

- is_guest: 游客（未登录）标记
- device_id: 游客设备标识，用于无登录识别
- channel_bindings: 通用渠道绑定列表（替代单一 telegram_chat_id）
- 登录用户可同时绑定多个渠道（见 AGENTS.md「游客模式与渠道绑定」）
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.types import JSON

from model.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    # 登录凭证：bcrypt 哈希（绝不存明文），约 60 字符
    password = Column(String(255), nullable=True)
    is_guest = Column(Boolean, default=True, nullable=False)
    # 渠道无关绑定：[{channel_type, recipient, verified}]
    channel_bindings = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
