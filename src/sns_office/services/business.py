# 概要: Workspaceの認可と各業務フローを実装します。将来のMCPからも同じ処理を再利用できます。
import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sns_office.core.exceptions import DomainError
from sns_office.core.security import utcnow
from sns_office.integrations.contracts import MockAIProvider
from sns_office.models.entities import (
    Agent,
    AgentMessage,
    AgentRole,
    AgentStatus,
    AgentTask,
    AnalysisReport,
    AuditLog,
    Brand,
    ConnectionStatus,
    Content,
    ContentApproval,
    ContentSchedule,
    ContentStatus,
    ContentVersion,
    MeetingMessage,
    Metric,
    MonitoringEvent,
    Notification,
    Role,
    SocialAccount,
    TaskStatus,
    User,
    Workspace,
    WorkspaceMember,
)
from sns_office.repositories.store import Repository
from sns_office.schemas.api import ContentOut, MeetingOut

EDIT = {Role.OWNER, Role.ADMIN, Role.EDITOR}
APPROVE = {Role.OWNER, Role.ADMIN, Role.APPROVER}
ADMIN = {Role.OWNER, Role.ADMIN}
CONTENT_FIELDS = (
    "platform",
    "title",
    "body",
    "hashtags",
    "cta",
    "media",
    "purpose",
    "tone",
    "target",
    "instructions",
    "assigned_agent_id",
)


# 承認対象となる投稿内容を取り出し、版履歴とハッシュ計算の共通形式にします。
def content_snapshot(row):
    return {key: getattr(row, key) for key in CONTENT_FIELDS}


# 項目順に依存しないハッシュを生成し、承認した内容と現在の内容を照合可能にします。
def content_hash(row):
    return hashlib.sha256(
        json.dumps(content_snapshot(row), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


# 認証済み利用者を必須とし、認可・状態遷移・履歴保存をまとめて管理します。
class BusinessService:
    """Transport independent application operations; reused by future MCP adapters."""

    # この処理で使用する依存オブジェクトやエラー情報を保持します。
    def __init__(self, db, user, request_id=None, ai_provider=None):
        self.db = db
        self.repo = Repository(db)
        self.user = user
        self.request_id = request_id
        self.ai = ai_provider or MockAIProvider()

    # Workspaceへの所属を確認し、更新時は操作に必要な役割も検証します。
    def access(self, workspace_id, roles=None):
        member = self.repo.one(
            WorkspaceMember,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == self.user.id,
        )
        if member is None:
            raise DomainError(403, "WORKSPACE_ACCESS_DENIED", "Workspace access denied")
        if roles is not None and member.role not in roles:
            raise DomainError(403, "INSUFFICIENT_ROLE", "Role does not allow this operation")
        return member

    # IDから対象を取得します。必要に応じて更新用の行ロックを取得します。
    def get(self, model, resource_id, roles=None, lock=False):
        row = self.repo.get(model, resource_id, lock=lock)
        workspace_id = row.id if model is Workspace else row.workspace_id
        self.access(workspace_id, roles)
        if model is Notification and row.user_id != self.user.id:
            raise DomainError(404, "NOT_FOUND", "Resource not found")
        return row

    # 操作主体・対象・時刻を追跡できる監査レコードを、業務変更と同じDBへ記録します。
    def audit(self, row, action, details=None):
        self.repo.add(
            AuditLog,
            workspace_id=row.id if isinstance(row, Workspace) else row.workspace_id,
            actor_id=self.user.id,
            action=action,
            resource_type=row.__tablename__,
            resource_id=row.id,
            request_id=self.request_id,
            details=details or {},
        )

    # 所属Workspaceの範囲内で検索し、リソースごとの絞り込みとページングを適用します。
    def list(
        self,
        model,
        *,
        workspace_id=None,
        brand_id=None,
        platform=None,
        status=None,
        agent_id=None,
        limit=50,
        offset=0,
    ):
        conditions = []
        if model is Workspace:
            conditions.append(Workspace.id.in_(self.repo.workspace_ids(self.user.id)))
        else:
            conditions.append(model.workspace_id.in_(self.repo.workspace_ids(self.user.id)))
        if workspace_id:
            self.access(workspace_id)
            conditions.append(
                (Workspace.id if model is Workspace else model.workspace_id) == workspace_id
            )
        if brand_id:
            self.get(Brand, brand_id)
            conditions.append(model.brand_id == brand_id)
        if platform:
            conditions.append(model.platform == platform)
        if status:
            conditions.append(model.status == status)
        if agent_id:
            self.get(Agent, agent_id)
            conditions.append(model.agent_id == agent_id)
        if model is Notification:
            conditions.append(Notification.user_id == self.user.id)
        return self.repo.page(model, *conditions, limit=limit, offset=offset)

    # Workspaceとowner所属を作り、6役のAI社員を待機状態で初期化します。
    def create_workspace(self, data):
        row = self.repo.add(Workspace, owner_id=self.user.id, **data.model_dump())
        self.repo.add(WorkspaceMember, workspace_id=row.id, user_id=self.user.id, role=Role.OWNER)
        names = {
            AgentRole.MANAGER: "Alex",
            AgentRole.WRITER: "Mika",
            AgentRole.ANALYST: "Ken",
            AgentRole.DESIGNER: "Rin",
            AgentRole.OPERATOR: "Sora",
            AgentRole.MONITOR: "Nao",
        }
        for role, name in names.items():
            self.repo.add(Agent, workspace_id=row.id, name=name, role=role, status=AgentStatus.IDLE)
        self.audit(row, "workspace.create")
        return row

    # 管理権限を確認してWorkspace設定を変更し、監査履歴を保存します。
    def patch_workspace(self, resource_id, data):
        row = self.get(Workspace, resource_id, ADMIN, lock=True)
        self.apply_patch(row, data)
        self.audit(row, "workspace.update")
        return row

    # Workspaceの編集権限を確認し、ブランド設定を保存します。
    def create_brand(self, data):
        self.access(data.workspace_id, EDIT)
        row = self.repo.add(Brand, **data.model_dump())
        self.audit(row, "brand.create")
        return row

    # 編集権限と最新versionを確認し、競合する設定更新を拒否します。
    def patch_brand(self, resource_id, data):
        row = self.get(Brand, resource_id, EDIT, lock=True)
        self.check_version(row, data.version)
        self.apply_patch(row, data, exclude={"version"})
        self.audit(row, "brand.update", {"version": row.version})
        return row

    # ブランドの管理権限を確認し、実OAuth接続ではないアカウント情報を登録します。
    def create_account(self, data):
        brand = self.get(Brand, data.brand_id, ADMIN)
        row = self.repo.add(SocialAccount, workspace_id=brand.workspace_id, **data.model_dump())
        self.audit(row, "social_account.create")
        return row

    # 管理権限のある利用者だけがアカウントのメタデータを変更できます。
    def patch_account(self, resource_id, data):
        row = self.get(SocialAccount, resource_id, ADMIN, lock=True)
        self.apply_patch(row, data, nullable={"external_account_id"})
        self.audit(row, "social_account.update")
        return row

    # 送信された項目だけを反映し、許可されていないnull指定を拒否します。
    def apply_patch(self, row, data, exclude=None, nullable=None):
        for key, value in data.model_dump(exclude_unset=True, exclude=exclude or set()).items():
            if value is None and key not in (nullable or set()):
                raise DomainError(422, "VALIDATION_ERROR", f"{key} cannot be null")
            setattr(row, key, value)
        self.db.flush()

    # 利用者が確認した版と現在版を比較し、古い内容による上書きを防ぎます。
    def check_version(self, row, version):
        if row.version != version:
            raise DomainError(
                409, "VERSION_CONFLICT", "Resource has changed; reload before editing"
            )

    # 担当AI社員が投稿と同じWorkspaceに属していることを確認します。
    def validate_agent(self, agent_id, workspace_id):
        if agent_id:
            agent = self.get(Agent, agent_id)
            if agent.workspace_id != workspace_id:
                raise DomainError(422, "REFERENCE_MISMATCH", "Agent belongs to another workspace")

    # 投稿内容・版番号・ハッシュ・保存者を履歴として残します。
    def save_version(self, row):
        self.repo.add(
            ContentVersion,
            content_id=row.id,
            version=row.version,
            snapshot=content_snapshot(row),
            content_hash=row.content_hash,
            created_by=self.user.id,
        )

    # ブランドと担当社員の参照を検証し、投稿と初版の履歴を保存します。
    def create_content(self, data):
        brand = self.get(Brand, data.brand_id, EDIT)
        self.validate_agent(data.assigned_agent_id, brand.workspace_id)
        row = Content(workspace_id=brand.workspace_id, created_by=self.user.id, **data.model_dump())
        row.content_hash = content_hash(row)
        self.db.add(row)
        self.db.flush()
        self.save_version(row)
        self.audit(row, "content.create", {"version": row.version})
        return self.content_view(row)

    # 編集権限と版を確認し、承認後の内容変更では承認を失効して有効予約を取り消します。
    def patch_content(self, resource_id, data):
        row = self.get(Content, resource_id, EDIT, lock=True)
        self.check_version(row, data.version)
        if row.status in {ContentStatus.POSTED, ContentStatus.POSTING, ContentStatus.GENERATING}:
            raise DomainError(
                409, "INVALID_STATE_TRANSITION", "Content cannot be edited in this state"
            )
        changes = data.model_dump(exclude_unset=True, exclude={"version"})
        if "assigned_agent_id" in changes:
            self.validate_agent(data.assigned_agent_id, row.workspace_id)
        if "status" in changes:
            allowed = {
                ContentStatus.IDEA: {"PLANNED", "DRAFT"},
                ContentStatus.PLANNED: {"DRAFT"},
                ContentStatus.DRAFT: {"DRAFT"},
                ContentStatus.FAILED: {"DRAFT"},
            }
            if changes["status"] not in allowed.get(row.status, set()):
                raise DomainError(
                    409, "INVALID_STATE_TRANSITION", "Use the workflow action endpoint"
                )
        old_status = row.status
        before = row.content_hash
        for key, value in changes.items():
            if value is None and key != "assigned_agent_id":
                raise DomainError(422, "VALIDATION_ERROR", f"{key} cannot be null")
            setattr(row, key, value)
        row.content_hash = content_hash(row)
        if row.content_hash != before and old_status in {
            ContentStatus.REVIEW,
            ContentStatus.APPROVED,
            ContentStatus.SCHEDULED,
        }:
            self.cancel_active_schedules(row)
            row.status = ContentStatus.REVIEW
            row.approved_version = None
        self.db.flush()
        if changes:
            if not self.repo.one(
                ContentVersion,
                ContentVersion.content_id == row.id,
                ContentVersion.version == row.version,
            ):
                self.save_version(row)
        self.audit(row, "content.update", {"version": row.version, "status": row.status})
        return self.content_view(row)

    # DBの投稿に予約日時・著者名・履歴を補い、画面で利用するレスポンスへ変換します。
    def content_view(self, row):
        result = ContentOut.model_validate(row)
        scheduled = self.repo.one(
            ContentSchedule,
            ContentSchedule.content_id == row.id,
            ContentSchedule.status == "SCHEDULED",
        )
        result.scheduled_at = scheduled.scheduled_at if scheduled else None
        result.author = (
            self.repo.get(Agent, row.assigned_agent_id).name
            if row.assigned_agent_id
            else self.repo.get(User, row.created_by).name
        )
        versions = self.repo.all(ContentVersion, ContentVersion.content_id == row.id)
        approvals = self.repo.all(ContentApproval, ContentApproval.content_id == row.id)
        result.history = [
            f"Version {v.version} saved" for v in sorted(versions, key=lambda v: v.version)
        ]
        result.history += [f"{a.decision}: {a.reason}" for a in approvals]
        return result

    # 認可済み一覧の各投稿へ表示用の派生情報を補います。
    def content_list(self, **filters):
        result = self.list(Content, **filters)
        result["items"] = [self.content_view(row) for row in result["items"]]
        return result

    # 承認依頼・承認・差戻しの許可された遷移を検証し、版と操作者の履歴を残します。
    def transition(self, resource_id, action, data):
        roles = EDIT if action == "submit-review" else APPROVE
        row = self.get(Content, resource_id, roles, lock=True)
        self.check_version(row, data.version)
        source, target = {
            "submit-review": (ContentStatus.DRAFT, ContentStatus.REVIEW),
            "approve": (ContentStatus.REVIEW, ContentStatus.APPROVED),
            "reject": (ContentStatus.REVIEW, ContentStatus.DRAFT),
        }[action]
        if row.status != source:
            raise DomainError(
                409, "INVALID_STATE_TRANSITION", f"Cannot {action} in {row.status} status"
            )
        if action == "submit-review" and not row.body.strip():
            raise DomainError(422, "VALIDATION_ERROR", "Body is required for review")
        if action == "reject" and not data.reason.strip():
            raise DomainError(422, "VALIDATION_ERROR", "A rejection reason is required")
        reviewed_version = row.version
        row.status = target
        row.approved_version = row.version + 1 if action == "approve" else None
        self.db.flush()
        self.repo.add(
            ContentApproval,
            content_id=row.id,
            version=reviewed_version,
            content_hash=row.content_hash,
            actor_id=self.user.id,
            decision=action.upper().replace("-", "_"),
            reason=data.reason,
        )
        self.save_version(row)
        self.audit(row, f"content.{action}", {"version": reviewed_version})
        return self.content_view(row)

    # 内容変更により承認が無効になった投稿の、有効予約を取消状態に変更します。
    def cancel_active_schedules(self, row):
        for schedule in self.repo.all(
            ContentSchedule,
            ContentSchedule.content_id == row.id,
            ContentSchedule.status == "SCHEDULED",
        ):
            schedule.status = "CANCELLED"
            self.audit(schedule, "schedule.cancel")

    # 過去の予約を拒否し、offset付き日時をUTCへ正規化します。
    def schedule_time(self, value):
        if value <= utcnow():
            raise DomainError(422, "INVALID_SCHEDULE_TIME", "Schedule must be in the future")
        return value.astimezone(timezone.utc)

    # 現在版の承認・ブランド・媒体・Mock状態を確認し、重複しない有効予約を作成します。
    def create_schedule(self, data):
        row = self.get(Content, data.content_id, EDIT, lock=True)
        account = self.get(SocialAccount, data.social_account_id)
        if account.brand_id != row.brand_id or account.platform != row.platform:
            raise DomainError(
                422, "REFERENCE_MISMATCH", "Account must match content brand and platform"
            )
        if account.connection_status != ConnectionStatus.MOCK:
            raise DomainError(
                409, "ACCOUNT_NOT_AVAILABLE", "This phase supports MOCK accounts only"
            )
        if row.status != ContentStatus.APPROVED or row.approved_version != row.version:
            raise DomainError(
                409, "CONTENT_NOT_APPROVED", "Current content version must be approved"
            )
        approved_version = row.version
        schedule = self.repo.add(
            ContentSchedule,
            workspace_id=row.workspace_id,
            content_id=row.id,
            social_account_id=account.id,
            scheduled_at=self.schedule_time(data.scheduled_at),
            timezone=data.timezone,
            approved_version=approved_version,
        )
        row.status = ContentStatus.SCHEDULED
        self.db.flush()
        self.save_version(row)
        self.audit(schedule, "schedule.create")
        return schedule

    # Content→Scheduleの順でロックし、取消済み予約の変更を拒否します。
    def patch_schedule(self, resource_id, data):
        schedule = self.get(ContentSchedule, resource_id, EDIT)
        self.get(Content, schedule.content_id, EDIT, lock=True)
        schedule = self.get(ContentSchedule, resource_id, EDIT, lock=True)
        if schedule.status != "SCHEDULED":
            raise DomainError(
                409, "INVALID_STATE_TRANSITION", "Cancelled schedule cannot be edited"
            )
        schedule.scheduled_at = self.schedule_time(data.scheduled_at)
        schedule.timezone = data.timezone
        self.db.flush()
        self.audit(schedule, "schedule.update")
        return schedule

    # 予約履歴を削除せず取消状態にし、投稿を再予約できる承認済み状態へ戻します。
    def cancel_schedule(self, resource_id):
        schedule = self.get(ContentSchedule, resource_id, EDIT)
        row = self.get(Content, schedule.content_id, EDIT, lock=True)
        schedule = self.get(ContentSchedule, resource_id, EDIT, lock=True)
        if schedule.status == "SCHEDULED":
            schedule.status = "CANCELLED"
            row.status = ContentStatus.APPROVED
            row.approved_version = row.version + 1
            self.db.flush()
            self.save_version(row)
            self.audit(schedule, "schedule.cancel")

    # 参照関係や操作権限を確認したうえで、対象の削除を行います。
    def delete(self, model, resource_id):
        roles = ADMIN if model in {Brand, SocialAccount} else EDIT
        row = self.get(model, resource_id, roles, lock=True)
        if model is Brand:
            if any(
                self.repo.one(child, child.brand_id == row.id)
                for child in (
                    Content,
                    SocialAccount,
                    AnalysisReport,
                    Metric,
                    MonitoringEvent,
                )
            ):
                raise DomainError(409, "RESOURCE_IN_USE", "Brand has dependent records")
        elif model is SocialAccount:
            if self.repo.one(
                ContentSchedule, ContentSchedule.social_account_id == row.id
            ) or self.repo.one(Metric, Metric.social_account_id == row.id):
                raise DomainError(409, "RESOURCE_IN_USE", "Account has dependent records")
        elif model is Content:
            if row.status in {ContentStatus.SCHEDULED, ContentStatus.POSTING, ContentStatus.POSTED}:
                raise DomainError(409, "RESOURCE_IN_USE", "Cancel the schedule before deleting")
            if self.repo.one(
                ContentSchedule, ContentSchedule.content_id == row.id
            ) or self.repo.one(Metric, Metric.content_id == row.id):
                raise DomainError(
                    409, "RESOURCE_IN_USE", "Content has retained schedules or metrics"
                )
        self.audit(row, f"{model.__tablename__}.delete")
        self.repo.delete(row)

    # Mock Providerでタスクを実行し、結果と社員状態を保存します。実AI推論は行いません。
    def create_task(self, data):
        agent = self.get(Agent, data.agent_id, EDIT, lock=True)
        if self.ai.mode != "MOCK":
            raise DomainError(409, "PROVIDER_UNAVAILABLE", "Only mock execution is enabled")
        row = self.repo.add(
            AgentTask,
            workspace_id=agent.workspace_id,
            **data.model_dump(),
            status=TaskStatus.RUNNING,
            started_at=utcnow(),
        )
        try:
            row.output = self.ai.execute(data.task_type, data.input)
            row.status = TaskStatus.COMPLETED
            agent.status = AgentStatus.IDLE
            agent.completed += 1
        except Exception:
            row.status = TaskStatus.FAILED
            row.error_message = "Mock provider failed"
            agent.status = AgentStatus.ERROR
        row.completed_at = utcnow()
        agent.task = (
            "Mock task completed" if row.status == TaskStatus.COMPLETED else row.error_message
        )
        self.repo.add(
            AgentMessage,
            workspace_id=agent.workspace_id,
            agent_id=agent.id,
            task_id=row.id,
            message=agent.task,
            source="MOCK",
        )
        self.audit(row, "agent_task.create")
        return row

    # ブランドの編集権限を確認し、人が登録した分析内容と根拠を保存します。
    def create_report(self, data):
        brand = self.get(Brand, data.brand_id, EDIT)
        row = self.repo.add(
            AnalysisReport, workspace_id=brand.workspace_id, **data.model_dump(), source="MANUAL"
        )
        self.audit(row, "report.create")
        return row

    # 本人宛の通知だけを既読にし、他ユーザーの通知操作を防ぎます。
    def read_notification(self, resource_id):
        row = self.get(Notification, resource_id, lock=True)
        row.is_read = True
        self.audit(row, "notification.read")
        return row

    # 会議の基本情報に、発言順で並べたメッセージを補います。
    def meeting_view(self, row):
        result = MeetingOut.model_validate(row)
        result.messages = sorted(
            self.repo.all(MeetingMessage, MeetingMessage.meeting_id == row.id),
            key=lambda message: message.sequence,
        )
        return result

    # 認可されたイベントを取得し、alertsでは警告以上の深刻度に絞ります。
    def monitoring(self, alerts=False, **filters):
        result = self.list(MonitoringEvent, **filters)
        if alerts:
            # Filtering happens before pagination, preserving accurate totals.
            workspace_id = filters.get("workspace_id")
            brand_id = filters.get("brand_id")
            conditions = [
                MonitoringEvent.workspace_id.in_(self.repo.workspace_ids(self.user.id)),
                MonitoringEvent.severity.in_(["WARNING", "ERROR", "CRITICAL"]),
            ]
            if workspace_id:
                conditions.append(MonitoringEvent.workspace_id == workspace_id)
            if brand_id:
                conditions.append(MonitoringEvent.brand_id == brand_id)
            return self.repo.page(
                MonitoringEvent,
                *conditions,
                limit=filters.get("limit", 50),
                offset=filters.get("offset", 0),
            )
        return result

    # Workspaceの日付境界をUTCへ変換し、両端の日付を含む有効予約一覧を取得します。
    def calendar(self, brand_id, start_date, end_date, platform=None, limit=50, offset=0):
        brand = self.get(Brand, brand_id)
        if end_date < start_date or (end_date - start_date).days > 366:
            raise DomainError(
                422, "INVALID_DATE_RANGE", "Range must be ordered and at most 366 days"
            )
        workspace = self.get(Workspace, brand.workspace_id)
        zone = ZoneInfo(workspace.timezone)
        start = datetime.combine(start_date, time.min, zone).astimezone(timezone.utc)
        end = datetime.combine(end_date + timedelta(days=1), time.min, zone).astimezone(
            timezone.utc
        )
        rows, total = self.repo.calendar_rows(
            brand_id, brand.workspace_id, start, end, platform, limit, offset
        )
        from sns_office.schemas.api import ScheduleOut

        items = [
            {
                **ScheduleOut.model_validate(s).model_dump(),
                "title": c.title,
                "platform": c.platform,
                "brand_id": c.brand_id,
                "content_status": c.status,
                "assigned_agent_id": c.assigned_agent_id,
                "purpose": c.purpose,
            }
            for s, c in rows
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    # 投稿の参照権限を確認した後に、承認・差戻し等の履歴をページ単位で返します。
    def approvals(self, content_id, limit=50, offset=0):
        self.get(Content, content_id)
        return self.repo.page(
            ContentApproval, ContentApproval.content_id == content_id, limit=limit, offset=offset
        )
