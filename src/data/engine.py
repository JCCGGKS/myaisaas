"""数据基础设施层：engine / sessionmaker 初始化 + 建表。

依赖方向：上层（dao/business/api）从这里拿 Session，不直接构造 engine。
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from utils.logging import get_logger

logger = get_logger(__name__)

# SQLite 单连接；PostgreSQL 用标准连接池
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """创建全部表（MVP 用 create_all，后续迁移交给 Alembic）。"""
    from model.base import Base
    import model  # noqa: F401  确保模型注册到 Base

    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已初始化: %s", settings.database_url)


def get_session() -> Generator[Session, None, None]:
    """FastAPI 依赖：请求级 session，自动关闭。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
