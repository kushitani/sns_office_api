# 概要: 集計値が空の場合や分母0の場合に、欠損を適切に扱うか確認します。
from datetime import date
from types import SimpleNamespace

from sns_office.services.analytics import aggregate


# この試験で使用するデータの準備、または独立した実行処理をまとめます。
def metric(**changes):
    return SimpleNamespace(
        impressions=0,
        reach=0,
        likes=0,
        comments=0,
        shares=0,
        saves=0,
        content_id=None,
        followers=None,
        social_account_id="a",
        measured_on=date(2026, 10, 14),
        **changes,
    )


# 空集計のFollowersや表示数0の反応率を、架空の数値でなくNoneとして扱うことを確認します。
def test_empty_and_zero_denominator():
    assert aggregate([])["followers"] is None
    assert aggregate([metric()])["engagement_rate"] is None
