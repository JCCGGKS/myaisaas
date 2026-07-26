"""删除雷达测试：归属校验 + 软删除语义（保留事件/通知，仅 active 置 False）。"""
from fastapi.testclient import TestClient

from main import app
from sqlalchemy import select

from dao.radar_dao import get as get_radar, list_by_owner, get_active
from data.engine import SessionLocal
from model.event import Event


def _make_radar(client: TestClient, q="雷达 D"):
    r = client.post("/api/radars", json={"raw_query": q})
    return r.json()["id"]


def test_delete_radar_soft_deletes(client: TestClient):
    rid = _make_radar(client)
    # 灌入一条命中关键词的事件（标题含「雷达 D」，与雷达关键词匹配，过阈值落库），验证软删后事件保留
    client.post(
        "/api/ingest/webhook",
        json={"radar_id": rid, "items": [{"title": "雷达 D 待删事件", "url": "http://x", "content": "c"}]},
    )
    db = SessionLocal()
    assert db.scalars(select(Event).where(Event.radar_id == rid)).first() is not None
    owner_id = get_radar(db, rid).owner_id
    # 软删前：列表与监控调度都能见到该雷达
    assert any(r.id == rid for r in list_by_owner(db, owner_id))
    assert any(r.id == rid for r in get_active(db))
    db.close()

    r = client.delete(f"/api/radars/{rid}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    db = SessionLocal()
    # 雷达行仍在，但 deleted_at 已写入（软删标记）
    radar = get_radar(db, rid)
    assert radar is not None
    assert radar.deleted_at is not None
    # 事件被保留（软删不级联物理删），支持误删恢复与审计
    assert db.scalars(select(Event).where(Event.radar_id == rid)).first() is not None
    # 列表与监控调度均按 active 过滤，软删后不可见 / 不再扫描
    assert all(r.id != rid for r in list_by_owner(db, owner_id))
    assert all(r.id != rid for r in get_active(db))
    db.close()


def test_delete_other_users_radar_forbidden(client: TestClient):
    rid = _make_radar(client)  # 属于当前游客会话
    # 用另一个全新游客会话尝试删除 → 非本人，应 404
    fresh = TestClient(app)
    r = fresh.delete(f"/api/radars/{rid}")
    assert r.status_code == 404

    # 原主仍能删除
    assert client.delete(f"/api/radars/{rid}").status_code == 200


def test_delete_nonexistent_returns_404(client: TestClient):
    r = client.delete("/api/radars/999999")
    assert r.status_code == 404
