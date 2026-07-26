"""模型包：导入子模块以注册表到 Base.metadata。"""
from model.base import Base  # noqa: F401
from model.user import User  # noqa: F401
from model.radar import Radar  # noqa: F401
from model.event import Event  # noqa: F401
from model.notification import Notification  # noqa: F401
