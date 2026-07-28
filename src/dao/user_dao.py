"""User 数据访问：按 device_id 取/建游客；按 id 取登录用户。"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
    """无则建、有则取。返回游客用户（is_guest=True）。

    注意：首次访问的游客常伴随多个并行请求（/api/radars、/api/auth/me 等同框触发），
    若用「先查后插」在并发下会竞态：都查到 None 后都 INSERT，后者撞 UNIQUE(device_id)。
    故插入冲突时回退为「按 device_id 重新读取」，由先成功的那个请求落库，保证幂等。
    """
    user = get_by_device_id(db, device_id)
    if user is not None:
        return user
    try:
        return create_guest(db, device_id)
    except IntegrityError:
        db.rollback()
        logger.warning("游客创建竞态命中（device_id 已存在），回退读取 device_id=%s", device_id)
        user = get_by_device_id(db, device_id)
        if user is None:
            raise
        return user
