# 概要: 接続エンジンを再利用し、API操作単位のトランザクションを管理します。
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sns_office.core.config import get_settings


# 接続プールを持つエンジンを再利用し、利用前に接続の生存確認を行います。
@lru_cache
def engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


# 処理成功時はcommit、例外時はrollbackし、最後にDBセッションを閉じます。
def get_db():
    with sessionmaker(engine(), expire_on_commit=False)() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
