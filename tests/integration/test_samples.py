# 概要: Seedの再実行、各Sample API、通知分離とOpenAPIを検証します。
import pytest
from conftest import register
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sns_office.models.entities import Notification, User
from sns_office.seed import seed


# Seed再実行で件数が増えず、サンプルAPIとMock Taskが利用できることを確認します。
def test_seed_idempotent_and_all_read_apis(client, database):
    from sns_office.db.base import Base

    with Session(database) as db, db.begin():
        first = seed(db)
        counts = {
            name: db.scalar(select(func.count()).select_from(table))
            for name, table in Base.metadata.tables.items()
        }
        second = seed(db)
        assert first["created"] and not second["created"]
        assert counts == {
            name: db.scalar(select(func.count()).select_from(table))
            for name, table in Base.metadata.tables.items()
        }
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "demo@example.com",
            "password": "DemoPassword123!",
        },
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    for path in [
        "workspaces",
        "brands",
        "social-accounts",
        "contents",
        "schedules",
        "agents",
        "agent-tasks",
        "reports",
        "monitoring/events",
        "monitoring/alerts",
        "notifications",
        "meetings",
    ]:
        result = client.get(f"/api/v1/{path}", headers=headers)
        assert result.status_code == 200, (path, result.text)
        assert result.json()["total"] > 0
        if path in {"reports", "meetings", "agent-tasks", "agents"}:
            resource_id = result.json()["items"][0]["id"]
            assert client.get(f"/api/v1/{path}/{resource_id}", headers=headers).status_code == 200
    for path in ["overview", "platforms", "posts", "trends"]:
        response = client.get(
            f"/api/v1/analytics/{path}", headers=headers, params={"brand_id": first["brand_id"]}
        )
        assert response.status_code == 200, response.text
        if path == "posts":
            assert response.json()["items"][0]["engagement_rate"] == 8.4
    agent = client.get("/api/v1/agents", headers=headers).json()["items"][0]
    for path in ["tasks", "messages"]:
        assert (
            client.get(f"/api/v1/agents/{agent['id']}/{path}", headers=headers).status_code == 200
        )
    task = client.post(
        "/api/v1/agent-tasks",
        headers=headers,
        json={
            "agent_id": agent["id"],
            "task_type": "WRITE_DRAFT",
            "input": {"brief": "sample"},
        },
    )
    assert task.status_code == 201, task.text
    assert task.json()["output"]["mock"] is True
    assert task.json()["status"] == "COMPLETED"


# 同じWorkspaceのメンバーでも、本人以外の通知を読めず既読化できないことを確認します。
def test_notification_user_isolation(client, database, office):
    headers, _ = register(client, "other@example.com")
    with Session(database) as db, db.begin():
        from sns_office.models.entities import WorkspaceMember

        owner = db.scalar(select(User).where(User.email == "owner@example.com"))
        other = db.scalar(select(User).where(User.email == "other@example.com"))
        db.add(
            WorkspaceMember(workspace_id=office["workspace"]["id"], user_id=other.id, role="viewer")
        )
        notice = Notification(
            workspace_id=office["workspace"]["id"],
            user_id=owner.id,
            type="REVIEW",
            title="Private",
            message="Owner only",
        )
        db.add(notice)
        db.flush()
        notice_id = notice.id
    assert client.get("/api/v1/notifications", headers=headers).json()["total"] == 0
    assert (
        client.patch(f"/api/v1/notifications/{notice_id}/read", headers=headers).status_code == 404
    )
    result = client.patch(f"/api/v1/notifications/{notice_id}/read", headers=office["headers"])
    assert result.json()["is_read"] is True


# 本番環境ではSeedが拒否され、デモユーザーを自動作成しないことを確認します。
def test_seed_production_guard(database, monkeypatch):
    from sns_office.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    with Session(database) as db:
        with pytest.raises(RuntimeError, match="development/test"):
            seed(db)
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()


# 一覧件数の上限とoffsetを検証し、Mockを実接続済みとして登録できないことを確認します。
def test_pagination_and_mock_connection(client, office):
    headers = office["headers"]
    assert client.get("/api/v1/agents?limit=2&offset=2", headers=headers).json()["total"] == 6
    assert len(client.get("/api/v1/agents?limit=2&offset=2", headers=headers).json()["items"]) == 2
    assert client.get("/api/v1/agents?limit=101", headers=headers).status_code == 422
    assert client.get("/api/v1/agents?offset=-1", headers=headers).status_code == 422
    assert (
        client.post(
            "/api/v1/social-accounts",
            headers=headers,
            json={
                "brand_id": office["brand"]["id"],
                "platform": "X",
                "name": "bad",
                "connection_status": "CONNECTED",
            },
        ).status_code
        == 422
    )


# OpenAPI・Swagger・共通エラー形式と、DBを含むHealth Checkを確認します。
def test_openapi(client):
    spec = client.get("/openapi.json").json()
    assert len(spec["paths"]) >= 39
    assert spec["components"]["securitySchemes"]["HTTPBearer"]
    assert "ContentOut" in spec["components"]["schemas"]
    assert client.get("/docs").status_code == 200
    assert client.get("/missing").json()["error"]["code"] == "HTTP_ERROR"
    assert client.get("/health").json()["database"] == "ok"


# Sampleの各リソース・分析・CalendarでもWorkspace越境参照が拒否されることを確認します。
def test_seed_resources_reject_outsider(client, database):
    with Session(database) as db, db.begin():
        seeded = seed(db)
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "demo@example.com",
            "password": "DemoPassword123!",
        },
    ).json()
    owner = {"Authorization": f"Bearer {login['access_token']}"}
    outsider, _ = register(client, "unrelated@example.com")
    for path in ["agents", "agent-tasks", "reports", "meetings", "schedules", "notifications"]:
        resource_id = client.get(f"/api/v1/{path}", headers=owner).json()["items"][0]["id"]
        assert client.get(f"/api/v1/{path}/{resource_id}", headers=outsider).status_code == 403
        assert client.get(f"/api/v1/{path}", headers=outsider).json()["total"] == 0
    for path in [
        "monitoring/events",
        "monitoring/alerts",
        "analytics/overview",
        "analytics/platforms",
        "analytics/posts",
        "analytics/trends",
    ]:
        assert (
            client.get(
                f"/api/v1/{path}", headers=outsider, params={"brand_id": seeded["brand_id"]}
            ).status_code
            == 403
        )
    assert (
        client.get(
            "/api/v1/calendar",
            headers=outsider,
            params={
                "brand_id": seeded["brand_id"],
                "start_date": "2026-10-01",
                "end_date": "2026-10-31",
            },
        ).status_code
        == 403
    )
