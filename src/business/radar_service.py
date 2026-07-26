"""雷达业务：创建（含游客限额）/ 列表。

MVP 暂不调用 LLM 解析自然语言（结构化参数留空），专注打通游客闭环。
"""
from data.engine import Session
from dao.radar_dao import count_by_owner, create, list_by_owner
from config.settings import settings
from model.user import User
from utils.exceptions import AppError, LimitExceededError
from utils.logging import get_logger

logger = get_logger(__name__)


def create_radar(db: Session, user: User, raw_query: str, notify_channel: str = ""):
    raw_query = (raw_query or "").strip()
    if not raw_query:
        raise AppError("监控目标不能为空", status_code=422, code="invalid_input")

    if user.is_guest and count_by_owner(db, user.id) >= settings.guest_radar_limit:
        raise LimitExceededError("游客最多创建 1 个雷达，登录解锁更多")

    radar = create(db, user.id, raw_query, notify_channel)
    logger.info("雷达创建成功 user_id=%s radar_id=%s", user.id, radar.id)
    return radar


def list_radars(db: Session, user: User):
    return list_by_owner(db, user.id)
