"""测试 fixtures：每个用例前清空数据，提供 FastAPI TestClient（自动处理游客 cookie）。"""
import pytest
from fastapi.testclient import TestClient

from config.settings import settings
from data.engine import SessionLocal, init_db
from main import app
from model.event import Event
from model.notification import Notification
from model.radar import Radar
from model.user import User

# 测试环境不自动启动监控调度，避免后台任务干扰用例
settings.monitor_autostart = False


@pytest.fixture(autouse=True)
def clean_db():
    # 用例开始前确保表存在并清空（游客以 cookie 区分，库需干净）
    init_db()
    db = SessionLocal()
    db.query(Notification).delete()
    db.query(Event).delete()
    db.query(Radar).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
