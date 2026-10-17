# 概要: DBの日次指標からKPIを集計します。数値計算にはLLMや外部サービスを使用しません。
from collections import defaultdict

from sns_office.core.exceptions import DomainError
from sns_office.models.entities import Brand, Metric, Workspace
from sns_office.schemas.api import AnalyticsMeta
from sns_office.services.business import BusinessService

COUNTERS = ("impressions", "reach", "likes", "comments", "shares", "saves")


# 日次増分を合算します。Followersは各アカウントの期間内最新値、反応率は加重計算です。
def aggregate(rows):
    totals = {name: sum(getattr(row, name) for row in rows) for name in COUNTERS}
    latest = {}
    for row in rows:
        if row.content_id is None and row.followers is not None:
            old = latest.get(row.social_account_id)
            if old is None or row.measured_on > old.measured_on:
                latest[row.social_account_id] = row
    totals["followers"] = sum(row.followers for row in latest.values()) if latest else None
    engagements = sum(totals[key] for key in ("likes", "comments", "shares", "saves"))
    totals["engagement_rate"] = (
        round(engagements / totals["impressions"] * 100, 4) if totals["impressions"] else None
    )
    return totals


# 共通のWorkspace認可を再利用し、分析用の検索・集計結果を提供します。
class AnalyticsService(BusinessService):
    # ブランドの認可と日付範囲を検証し、指標と出典・鮮度・注意事項を取得します。
    def query(self, brand_id, start_date=None, end_date=None, platform=None):
        brand = self.get(Brand, brand_id)
        if (
            start_date
            and end_date
            and (end_date < start_date or (end_date - start_date).days > 366)
        ):
            raise DomainError(
                422, "INVALID_DATE_RANGE", "Range must be ordered and at most 366 days"
            )
        conditions = [Metric.brand_id == brand.id, Metric.workspace_id == brand.workspace_id]
        if start_date:
            conditions.append(Metric.measured_on >= start_date)
        if end_date:
            conditions.append(Metric.measured_on <= end_date)
        if platform:
            conditions.append(Metric.platform == platform)
        rows = self.repo.all(Metric, *conditions)
        workspace = self.get(Workspace, brand.workspace_id)
        meta = AnalyticsMeta(
            brand_id=brand_id,
            start_date=start_date,
            end_date=end_date,
            platform=platform,
            timezone=workspace.timezone,
            source_ids=[row.id for row in rows],
            data_freshness=max((row.updated_at for row in rows), default=None),
            warnings=[
                "Sample data; no live SNS collection",
                "Missing days are not filled with zero",
            ],
        )
        return rows, meta

    # Account粒度の行だけを集計し、Post粒度との二重計上を防ぎます。
    def overview(self, **filters):
        rows, meta = self.query(**filters)
        # Account daily increments are authoritative for overview; post rows are drilldowns.
        return {"metrics": aggregate([row for row in rows if row.content_id is None]), "meta": meta}

    # 媒体・投稿・日付ごとに粒度を選んで集計し、安定した順序でページングします。
    def groups(self, dimension, limit=50, offset=0, **filters):
        rows, meta = self.query(**filters)
        groups = defaultdict(list)
        for row in rows:
            if dimension == "content_id" and row.content_id is None:
                continue
            if dimension != "content_id" and row.content_id is not None:
                continue
            groups[getattr(row, dimension)].append(row)
        items = [
            {dimension: key, **aggregate(values)}
            for key, values in sorted(groups.items(), key=lambda pair: str(pair[0]))
        ]
        if dimension == "content_id":
            items.sort(key=lambda item: (-item["impressions"], item["content_id"]))
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "meta": meta,
        }
