# 概要: SQLAlchemyによる検索・保存・削除を集約します。利用者の権限判断はServiceで行います。
from sqlalchemy import func, select

from sns_office.core.exceptions import DomainError
from sns_office.models.entities import WorkspaceMember


# DB操作の共通窓口です。認可済みの条件をServiceから受け取ります。
class Repository:
    # この処理で使用する依存オブジェクトやエラー情報を保持します。
    def __init__(self, db):
        self.db = db

    # IDから対象を取得します。必要に応じて更新用の行ロックを取得します。
    def get(self, model, resource_id, *, lock=False):
        statement = select(model).where(model.id == resource_id)
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        result = self.db.scalar(statement)
        if result is None:
            raise DomainError(404, "NOT_FOUND", "Resource not found")
        return result

    # 指定条件に一致する1件を取得し、見つからない場合はNoneを返します。
    def one(self, model, *conditions, lock=False):
        statement = select(model).where(*conditions)
        if lock:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    # レコードを追加してflushします。トランザクションの確定は呼び出し元に任せます。
    def add(self, model, **values):
        row = model(**values)
        self.db.add(row)
        self.db.flush()
        return row

    # 参照関係や操作権限を確認したうえで、対象の削除を行います。
    def delete(self, row):
        self.db.delete(row)
        self.db.flush()

    # 総件数と指定ページを返します。同日時の行もIDで順序を安定させます。
    def page(self, model, *conditions, limit=50, offset=0):
        statement = select(model).where(*conditions)
        total = self.db.scalar(select(func.count()).select_from(statement.subquery()))
        rows = self.db.scalars(
            statement.order_by(model.created_at, model.id).offset(offset).limit(limit)
        ).all()
        return {"items": rows, "total": total, "limit": limit, "offset": offset}

    # 条件に一致する行を内部処理用に取得します。公開一覧のページングとは使い分けます。
    def all(self, model, *conditions):
        return self.db.scalars(select(model).where(*conditions).order_by(model.id)).all()

    # 利用者が所属するWorkspaceを副問い合わせとして返し、一覧の範囲を制限します。
    def workspace_ids(self, user_id):
        return select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)

    # 有効予約と投稿情報を結合し、日時範囲・媒体で絞ったカレンダー用データを返します。
    def calendar_rows(self, brand_id, workspace_id, start, end, platform, limit, offset):
        from sns_office.models.entities import Content, ContentSchedule

        statement = (
            select(ContentSchedule, Content)
            .join(Content, ContentSchedule.content_id == Content.id)
            .where(
                Content.brand_id == brand_id,
                ContentSchedule.workspace_id == workspace_id,
                ContentSchedule.status == "SCHEDULED",
                ContentSchedule.scheduled_at >= start,
                ContentSchedule.scheduled_at < end,
            )
        )
        if platform:
            statement = statement.where(Content.platform == platform)
        total = self.db.scalar(select(func.count()).select_from(statement.subquery()))
        rows = self.db.execute(
            statement.order_by(ContentSchedule.scheduled_at, ContentSchedule.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return rows, total
