# 概要: テスト用の共通DB・クライアント・業務データを準備します。
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-0000000000000000000000000")
os.environ.setdefault("APP_ENV", "test")

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from sns_office.db.session import get_db  # noqa: E402
from sns_office.main import app  # noqa: E402


# 破棄可能なDBへMigrationを適用し、試験後はスキーマを解除します。
@pytest.fixture
def database(tmp_path, monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("DATABASE_URL", url)
    from sns_office.core.config import get_settings
    from sns_office.db.session import engine

    get_settings.cache_clear()
    engine.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    db_engine = create_engine(url)
    if url.startswith("sqlite"):
        # この試験で使用するデータの準備、または独立した実行処理をまとめます。
        @event.listens_for(db_engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    yield db_engine
    db_engine.dispose()
    engine().dispose()
    engine.cache_clear()
    command.downgrade(Config("alembic.ini"), "base")
    get_settings.cache_clear()


# APIのDB依存をテスト用Sessionへ差し替え、実際のHTTP入出力を検証します。
@pytest.fixture
def client(database):
    # この試験で使用するデータの準備、または独立した実行処理をまとめます。
    def db_session():
        with Session(database, expire_on_commit=False) as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# この試験で使用するデータの準備、または独立した実行処理をまとめます。
def register(client, email="owner@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "name": "Owner",
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return headers, tokens


# 認証済みowner・Workspace・Brand・Mock Accountを試験用に準備します。
@pytest.fixture
def office(client):
    headers, tokens = register(client)
    workspace = client.post("/api/v1/workspaces", headers=headers, json={"name": "Office"}).json()
    brand = client.post(
        "/api/v1/brands",
        headers=headers,
        json={
            "name": "Brand",
            "workspace_id": workspace["id"],
        },
    ).json()
    account = client.post(
        "/api/v1/social-accounts",
        headers=headers,
        json={
            "brand_id": brand["id"],
            "platform": "X",
            "name": "@example",
        },
    ).json()
    assert "id" in account, account
    return {
        "headers": headers,
        "tokens": tokens,
        "workspace": workspace,
        "brand": brand,
        "account": account,
    }


# この試験で使用するデータの準備、または独立した実行処理をまとめます。
def create_content(client, office, **values):
    response = client.post(
        "/api/v1/contents",
        headers=office["headers"],
        json={
            "brand_id": office["brand"]["id"],
            "platform": "X",
            "title": "Post",
            "body": "A post ready for review",
            **values,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# この試験で使用するデータの準備、または独立した実行処理をまとめます。
def approve_content(client, office, content):
    for action in ["submit-review", "approve"]:
        response = client.post(
            f"/api/v1/contents/{content['id']}/{action}",
            headers=office["headers"],
            json={"version": content["version"]},
        )
        assert response.status_code == 200, response.text
        content = response.json()
    assert content["approved_version"] == content["version"]
    return content
