# 概要: 投稿の作成・編集・削除、承認と不正遷移の拒否を検証します。
from conftest import approve_content, create_content


# 投稿CRUDと版番号の更新、古い版による上書き拒否を確認します。
def test_content_crud_versions(client, office):
    headers = office["headers"]
    content = create_content(client, office)
    url = f"/api/v1/contents/{content['id']}"
    response = client.patch(url, headers=headers, json={"title": "Updated", "version": 1})
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2
    assert (
        client.patch(url, headers=headers, json={"title": "stale", "version": 1}).status_code == 409
    )
    assert client.get(url, headers=headers).json()["title"] == "Updated"
    assert client.get("/api/v1/contents?limit=1", headers=headers).json()["total"] == 1
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404


# 不正遷移の拒否、承認履歴、内容変更による承認失効、理由付き差戻しを確認します。
def test_approval_workflow(client, office):
    content = create_content(client, office)
    url = f"/api/v1/contents/{content['id']}"
    headers = office["headers"]
    invalid = client.post(url + "/approve", headers=headers, json={"version": 1})
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    content = approve_content(client, office, content)
    history = client.get(url + "/approvals", headers=headers).json()["items"]
    assert len(history) == 2
    assert all(item["actor_id"] for item in history)
    changed = client.patch(
        url, headers=headers, json={"body": "Changed", "version": content["version"]}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "REVIEW"
    assert changed.json()["approved_version"] is None
    version = changed.json()["version"]
    assert (
        client.post(url + "/reject", headers=headers, json={"version": version}).status_code == 422
    )
    rejected = client.post(
        url + "/reject", headers=headers, json={"version": version, "reason": "Revise"}
    )
    assert rejected.json()["status"] == "DRAFT"


# 作成・編集で状態を直接指定して承認手順を飛ばせないことを確認します。
def test_cannot_bypass_approval(client, office):
    content = create_content(client, office)
    assert (
        client.patch(
            f"/api/v1/contents/{content['id']}",
            headers=office["headers"],
            json={"version": 1, "status": "APPROVED"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/contents",
            headers=office["headers"],
            json={
                "brand_id": office["brand"]["id"],
                "platform": "X",
                "title": "Bad",
                "status": "POSTED",
            },
        ).status_code
        == 422
    )


# 本文が空白だけの投稿は承認依頼を受け付けないことを確認します。
def test_empty_body_review_rejected(client, office):
    content = create_content(client, office, body=" ")
    assert (
        client.post(
            f"/api/v1/contents/{content['id']}/submit-review",
            headers=office["headers"],
            json={"version": 1},
        ).status_code
        == 422
    )
