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
_connect_args = {"check_same_thread": False} if settings.database.url.startswith("sqlite") else {}
engine = create_engine(settings.database.url, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """创建全部表（MVP 用 create_all，后续迁移交给 Alembic）。

    对 SQLite 等不支持「自动追加列」的引擎，create_all 不会给已存在的表补列，
    这里额外做一次「补齐缺失列」，保证模型演进时既有数据不被清空。
    """
    from model.base import Base
    import model  # noqa: F401  确保模型注册到 Base

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    logger.info("数据库表已初始化: %s", settings.database.url)


def _add_missing_columns() -> None:
    """为已存在的表补齐模型里新增、但库里还没有的列（MVP 轻量迁移）。"""
    from sqlalchemy import inspect, text

    from model.base import Base
    import model  # noqa: F401  确保模型注册到 Base

    inspector = inspect(engine)
    for table in Base.metadata.tables.values():
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            # 简单列（可空）直接 ALTER ADD；SQLite 对可空列支持良好
            col_type = col.type.compile(dialect=engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"))
            logger.info("补齐缺失列 %s.%s (%s)", table.name, col.name, col_type)


def get_session() -> Generator[Session, None, None]:
    """FastAPI 依赖：请求级 session，自动关闭。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
