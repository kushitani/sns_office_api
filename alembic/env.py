# 概要: DBスキーマをモデル定義と整合させるAlembic実行設定です。
from sqlalchemy import create_engine

from alembic import context
from sns_office.core.config import get_settings
from sns_office.db.base import Base
from sns_office.models import entities  # noqa: F401

target_metadata = Base.metadata


# 接続実行とSQL出力の両モードに対応してAlembicマイグレーションを実行します。
def run():
    url = get_settings().database_url
    if context.is_offline_mode():
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        with create_engine(url).connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()


run()
