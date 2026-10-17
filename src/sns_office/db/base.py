# 概要: SQLAlchemyの宣言ベースと、ID・作成日時・更新日時の共通カラムを定義します。
import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sns_office.core.security import utcnow


# 全モデルのテーブル定義を集約する、SQLAlchemyの共通宣言ベースです。
class Base(DeclarativeBase):
    pass


# UUIDと日時カラムを各モデルで再利用するMixinです。
class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
