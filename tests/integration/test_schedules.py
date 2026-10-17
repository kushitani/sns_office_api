# 概要: 承認済み投稿の予約・変更・取消と日時・媒体の検証を行います。
from datetime import timedelta

from conftest import approve_content, create_content

from sns_office.core.security import utcnow


# この試験で使用するデータの準備、または独立した実行処理をまとめます。
def schedule_payload(office, content, **changes):
    return {
        "content_id": content["id"],
        "social_account_id": office["account"]["id"],
        "scheduled_at": (utcnow() + timedelta(days=2)).isoformat(),
        "timezone": "Asia/Tokyo",
        **changes,
    }


# 未承認予約の拒否から予約作成・変更・取消・再予約までの状態整合性を確認します。
def test_schedule_lifecycle(client, office):
    headers = office["headers"]
    content = create_content(client, office)
    payload = schedule_payload(office, content)
    assert client.post("/api/v1/schedules", headers=headers, json=payload).status_code == 409
    content = approve_content(client, office, content)
    created = client.post("/api/v1/schedules", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    schedule = created.json()
    assert schedule["execution_mode"] == "MOCK"
    assert client.post("/api/v1/schedules", headers=headers, json=payload).status_code == 409
    url = f"/api/v1/schedules/{schedule['id']}"
    changed = client.patch(
        url,
        headers=headers,
        json={
            "scheduled_at": (utcnow() + timedelta(days=3)).isoformat(),
            "timezone": "America/New_York",
        },
    )
    assert changed.status_code == 200, changed.text
    day = (utcnow() + timedelta(days=3)).date()
    events = client.get(
        "/api/v1/calendar",
        headers=headers,
        params={
            "brand_id": office["brand"]["id"],
            "start_date": (day - timedelta(days=1)).isoformat(),
            "end_date": (day + timedelta(days=1)).isoformat(),
        },
    ).json()
    assert events["total"] == 1
    assert events["items"][0]["title"] == content["title"]
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).json()["status"] == "CANCELLED"
    current = client.get(f"/api/v1/contents/{content['id']}", headers=headers).json()
    assert current["status"] == "APPROVED"
    assert current["approved_version"] == current["version"]
    assert client.post("/api/v1/schedules", headers=headers, json=payload).status_code == 201


# 予約済み投稿を編集すると再審査へ戻り、有効予約も取消になることを確認します。
def test_content_edit_cancels_schedule(client, office):
    headers = office["headers"]
    content = approve_content(client, office, create_content(client, office))
    schedule = client.post(
        "/api/v1/schedules", headers=headers, json=schedule_payload(office, content)
    ).json()
    url = f"/api/v1/contents/{content['id']}"
    content = client.get(url, headers=headers).json()
    changed = client.patch(
        url, headers=headers, json={"version": content["version"], "body": "New"}
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "REVIEW"
    assert (
        client.get(f"/api/v1/schedules/{schedule['id']}", headers=headers).json()["status"]
        == "CANCELLED"
    )


# 過去時刻・offsetなし日時・無効TZ・媒体不一致の予約を拒否することを確認します。
def test_schedule_validation(client, office):
    content = approve_content(client, office, create_content(client, office))
    for change in [
        {"scheduled_at": (utcnow() - timedelta(days=1)).isoformat()},
        {"scheduled_at": "2030-01-01T12:00:00"},
        {"timezone": "Invalid/Zone"},
    ]:
        assert (
            client.post(
                "/api/v1/schedules",
                headers=office["headers"],
                json=schedule_payload(office, content, **change),
            ).status_code
            == 422
        )
    other = client.post(
        "/api/v1/social-accounts",
        headers=office["headers"],
        json={
            "brand_id": office["brand"]["id"],
            "platform": "Instagram",
            "name": "@other",
        },
    ).json()
    assert (
        client.post(
            "/api/v1/schedules",
            headers=office["headers"],
            json=schedule_payload(
                office,
                content,
                social_account_id=other["id"],
            ),
        ).status_code
        == 422
    )
