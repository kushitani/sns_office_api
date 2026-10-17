# 概要: 日付・媒体フィルタと、粒度を区別したKPI集計を検証します。
from datetime import date, timedelta

from sqlalchemy.orm import Session

from sns_office.models.entities import Metric


# 期間・SNSで絞った集計と、Followersの最新値・反応率・時系列の計算を確認します。
def test_analytics_filters_and_grains(client, database, office):
    today = date(2026, 10, 14)
    with Session(database) as db, db.begin():
        for i in range(2):
            db.add(
                Metric(
                    workspace_id=office["workspace"]["id"],
                    brand_id=office["brand"]["id"],
                    social_account_id=office["account"]["id"],
                    platform="X",
                    measured_on=today + timedelta(days=i),
                    followers=100 + i * 10,
                    impressions=1000,
                    reach=700,
                    likes=50,
                    comments=10,
                    shares=20,
                    saves=20,
                )
            )
    headers = office["headers"]
    params = {"brand_id": office["brand"]["id"]}
    result = client.get("/api/v1/analytics/overview", headers=headers, params=params).json()
    assert result["metrics"]["followers"] == 110
    assert result["metrics"]["impressions"] == 2000
    assert result["metrics"]["engagement_rate"] == 10.0
    params["start_date"] = "2026-10-15"
    assert (
        client.get("/api/v1/analytics/overview", headers=headers, params=params).json()["metrics"][
            "impressions"
        ]
        == 1000
    )
    params["platform"] = "Instagram"
    empty = client.get("/api/v1/analytics/overview", headers=headers, params=params).json()
    assert empty["metrics"]["engagement_rate"] is None
    assert empty["metrics"]["followers"] is None
    params["platform"] = "X"
    params["end_date"] = "2026-10-14"
    assert (
        client.get("/api/v1/analytics/overview", headers=headers, params=params).status_code == 422
    )
    params = {"brand_id": office["brand"]["id"]}
    trend = client.get("/api/v1/analytics/trends", headers=headers, params=params).json()
    assert len(trend["items"]) == 2
    assert trend["items"][0]["measured_on"] == "2026-10-14"
    platforms = client.get("/api/v1/analytics/platforms", headers=headers, params=params).json()
    assert platforms["items"][0]["platform"] == "X"
    assert platforms["items"][0]["followers"] == 110
