"""User 数据访问：按 device_id 取/建游客；按 id 取登录用户。"""
from sqlalchemy import select

from data.engine import Session
from model.user import User
from utils.logging import get_logger

logger = get_logger(__name__)


def get_by_device_id(db: Session, device_id: str) -> User | None:
    return db.scalar(select(User).where(User.device_id == device_id))


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_guest(db: Session, device_id: str) -> User:
    user = User(device_id=device_id, is_guest=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("创建游客用户 device_id=%s user_id=%s", device_id, user.id)
    return user


def upsert_guest(db: Session, device_id: str) -> User:
    """无则建、有则取。返回游客用户（is_guest=True）。"""
    user = get_by_device_id(db, device_id)
    if user is None:
        user = create_guest(db, device_id)
    return user
