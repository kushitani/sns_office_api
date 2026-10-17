# 概要: PostgreSQLで同時更新を実行し、トークン更新と有効予約の重複を防げるか確認します。
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from conftest import approve_content, create_content
from sqlalchemy.orm import Session

from sns_office.core.exceptions import DomainError
from sns_office.core.security import utcnow
from sns_office.models.entities import User
from sns_office.schemas.api import ScheduleCreate
from sns_office.services.auth import AuthService
from sns_office.services.business import BusinessService


# 同じRefresh Tokenを同時更新し、片方だけが成功して他方が401になることを確認します。
def test_refresh_rotation_is_atomic(client, database, office):
    if database.dialect.name != "postgresql":
        pytest.skip("Row-lock concurrency requires PostgreSQL")
    barrier = Barrier(2)

    # この試験で使用するデータの準備、または独立した実行処理をまとめます。
    def rotate():
        with Session(database) as db:
            barrier.wait(timeout=10)
            try:
                AuthService(db).refresh(office["tokens"]["refresh_token"])
                db.commit()
                return 200
            except DomainError as exc:
                db.rollback()
                return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: rotate(), range(2))) == [200, 401]


# 同じ投稿へ同時予約し、有効予約が1件だけ作成されることを確認します。
def test_simultaneous_schedules_have_one_winner(client, database, office):
    if database.dialect.name != "postgresql":
        pytest.skip("Row-lock concurrency requires PostgreSQL")
    content = approve_content(client, office, create_content(client, office))
    user_id = client.get("/api/v1/auth/me", headers=office["headers"]).json()["id"]
    barrier = Barrier(2)
    payload = ScheduleCreate(
        content_id=content["id"],
        social_account_id=office["account"]["id"],
        scheduled_at=utcnow() + timedelta(days=1),
    )

    # この試験で使用するデータの準備、または独立した実行処理をまとめます。
    def schedule():
        with Session(database) as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                BusinessService(db, user).create_schedule(payload)
                db.commit()
                return 201
            except DomainError as exc:
                db.rollback()
                return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: schedule(), range(2))) == [201, 409]
