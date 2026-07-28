"""User 模型：身份 + 游客标记。

- is_guest: 游客（未登录）标记
- device_id: 游客设备标识，用于无登录识别
- 渠道绑定已「跟随雷达」，存于 Radar.notify_channels（list[dict]），
  不再在用户级维护（见 AGENTS.md「游客模式与渠道绑定」）。
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from model.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    # 昵称（注册可选，便于展示；不强制唯一）
    name = Column(String(255), nullable=True)
    # 登录凭证：bcrypt 哈希（绝不存明文），约 60 字符
    password = Column(String(255), nullable=True)
    is_guest = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
