# 概要: 認証・トークン失効・不正JWT・秘密情報の扱いを検証します。
from conftest import register


# 登録・ログイン後のToken更新とLogoutを通し、旧Tokenや失効セッションが拒否されることを確認します。
def test_auth_rotation_logout(client):
    headers, tokens = register(client)
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert "password_hash" not in me.json()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "owner@example.com",
                "password": "wrong",
            },
        ).status_code
        == 401
    )
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login.status_code == 200
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        ).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    tokens = rotated.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers=headers,
            json={
                "refresh_token": tokens["refresh_token"],
            },
        ).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        ).status_code
        == 401
    )


# 大文字小文字を正規化したメールの重複拒否と、入力エラーで秘密値を返さないことを確認します。
def test_duplicate_and_validation(client):
    register(client)
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "OWNER@example.com",
                "name": "Owner",
                "password": "StrongPassword123!",
            },
        ).status_code
        == 409
    )
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid",
            "name": " ",
            "password": "short",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert not any("input" in item for item in response.json()["error"]["details"]["fields"])
    assert response.headers["x-request-id"]


# Refresh Tokenが平文ではなく64文字のハッシュとしてDBに保存されることを確認します。
def test_refresh_tokens_are_hashed(client, database):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from sns_office.models.entities import RefreshToken

    _, tokens = register(client)
    with Session(database) as db:
        row = db.scalar(select(RefreshToken))
        assert row.token_hash != tokens["refresh_token"]
        assert len(row.token_hash) == 64


# 署名の異なるJWTと期限切れJWTのどちらも認証エラーになることを確認します。
def test_invalid_jwt_rejected(client):
    from datetime import timedelta

    import jwt

    from sns_office.core.config import get_settings
    from sns_office.core.security import utcnow

    _, tokens = register(client)
    claims = jwt.decode(tokens["access_token"], options={"verify_signature": False})
    invalid_tokens = [jwt.encode(claims, "wrong-secret-000000000000000000000", algorithm="HS256")]
    claims["exp"] = utcnow() - timedelta(seconds=1)
    invalid_tokens.append(jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256"))
    for token in invalid_tokens:
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHENTICATED"
