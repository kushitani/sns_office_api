# 概要: Workspace分離・役割制限・別Workspace参照の拒否を検証します。
import pytest
from conftest import create_content, register
from sqlalchemy import select
from sqlalchemy.orm import Session

from sns_office.models.entities import Agent, Role, User, WorkspaceMember


# 未所属Workspaceのリソースを参照・変更できず、一覧にも混入しないことを確認します。
def test_workspace_isolation(client, office):
    content = create_content(client, office)
    headers, _ = register(client, "outsider@example.com")
    ids = [
        ("workspaces", office["workspace"]["id"]),
        ("brands", office["brand"]["id"]),
        ("social-accounts", office["account"]["id"]),
        ("contents", content["id"]),
    ]
    for path, resource_id in ids:
        assert client.get(f"/api/v1/{path}/{resource_id}", headers=headers).status_code == 403
        assert client.get(f"/api/v1/{path}", headers=headers).json()["total"] == 0
    assert (
        client.get(
            "/api/v1/analytics/overview",
            headers=headers,
            params={"brand_id": office["brand"]["id"]},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/contents/{content['id']}",
            headers=headers,
            json={"version": 1, "body": "intrusion"},
        ).status_code
        == 403
    )


# 閲覧可能なメンバーでも、viewer・approverには投稿作成権限がないことを確認します。
@pytest.mark.parametrize("role", [Role.VIEWER, Role.APPROVER])
def test_roles_cannot_edit(client, database, office, role):
    headers, _ = register(client, f"{role}@example.com")
    with Session(database) as db, db.begin():
        user = db.scalar(select(User).where(User.email == f"{role}@example.com"))
        db.add(WorkspaceMember(user_id=user.id, workspace_id=office["workspace"]["id"], role=role))
    assert client.get("/api/v1/brands", headers=headers).json()["total"] == 1
    assert (
        client.post(
            "/api/v1/contents",
            headers=headers,
            json={
                "brand_id": office["brand"]["id"],
                "platform": "X",
                "title": "Forbidden",
            },
        ).status_code
        == 403
    )


# editorは承認依頼を出せても、承認者として決裁できないことを確認します。
def test_editor_cannot_approve(client, database, office):
    content = create_content(client, office)
    headers, _ = register(client, "editor@example.com")
    with Session(database) as db, db.begin():
        user = db.scalar(select(User).where(User.email == "editor@example.com"))
        db.add(
            WorkspaceMember(
                user_id=user.id, workspace_id=office["workspace"]["id"], role=Role.EDITOR
            )
        )
    content = client.post(
        f"/api/v1/contents/{content['id']}/submit-review", headers=headers, json={"version": 1}
    ).json()
    assert (
        client.post(
            f"/api/v1/contents/{content['id']}/approve",
            headers=headers,
            json={"version": content["version"]},
        ).status_code
        == 403
    )


# 両Workspaceに所属していても、別Workspaceの社員を投稿へ紐付けられないことを確認します。
def test_foreign_agent_reference(client, database, office):
    # Even a user who belongs to both workspaces may not cross-link their records.
    workspace = client.post(
        "/api/v1/workspaces", headers=office["headers"], json={"name": "Second"}
    ).json()
    with Session(database) as db:
        agent = db.scalar(select(Agent).where(Agent.workspace_id == workspace["id"]))
        agent_id = agent.id
    assert (
        client.post(
            "/api/v1/contents",
            headers=office["headers"],
            json={
                "brand_id": office["brand"]["id"],
                "platform": "X",
                "title": "Bad reference",
                "assigned_agent_id": agent_id,
            },
        ).status_code
        == 422
    )
