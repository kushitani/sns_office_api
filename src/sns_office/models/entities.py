# 概要: 認証・Workspace・投稿・分析などの永続化モデルと状態Enumを定義します。
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from sns_office.db.base import Base, Record


# Platformの許可値を定義し、不正な状態・役割の保存を防ぎます。
class Platform(StrEnum):
    X = "X"
    INSTAGRAM = "Instagram"
    THREADS = "Threads"
    TIKTOK = "TikTok"
    YOUTUBE = "YouTube"


# ContentStatusの許可値を定義し、不正な状態・役割の保存を防ぎます。
class ContentStatus(StrEnum):
    IDEA = "IDEA"
    PLANNED = "PLANNED"
    GENERATING = "GENERATING"
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    POSTING = "POSTING"
    POSTED = "POSTED"
    FAILED = "FAILED"


# Roleの許可値を定義し、不正な状態・役割の保存を防ぎます。
class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    APPROVER = "approver"
    VIEWER = "viewer"


# AgentRoleの許可値を定義し、不正な状態・役割の保存を防ぎます。
class AgentRole(StrEnum):
    MANAGER = "MANAGER"
    WRITER = "WRITER"
    ANALYST = "ANALYST"
    DESIGNER = "DESIGNER"
    OPERATOR = "OPERATOR"
    MONITOR = "MONITOR"


# AgentStatusの許可値を定義し、不正な状態・役割の保存を防ぎます。
class AgentStatus(StrEnum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    WRITING = "WRITING"
    ANALYZING = "ANALYZING"
    POSTING = "POSTING"
    MONITORING = "MONITORING"
    MEETING = "MEETING"
    ERROR = "ERROR"


# TaskStatusの許可値を定義し、不正な状態・役割の保存を防ぎます。
class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ConnectionStatusの許可値を定義し、不正な状態・役割の保存を防ぎます。
class ConnectionStatus(StrEnum):
    MOCK = "MOCK"
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"


# EnumをDBのCHECK制約として保存し、PostgreSQLとテスト用SQLiteの定義を揃えます。
def enum_column(enum):
    return Enum(
        enum,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda cls: [v.value for v in cls],
    )


# ユーザー情報とパスワードハッシュを保存します。平文パスワードは保持しません。
class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)


# ログインセッションごとのトークンハッシュ・期限・失効日時を管理します。
class RefreshToken(Record, Base):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


# データ分離の単位となる組織と、その表示タイムゾーンを管理します。
class Workspace(Record, Base):
    __tablename__ = "workspaces"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(100), default="Asia/Tokyo")
    week_start_day: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("week_start_day BETWEEN 0 AND 6"),)


# ユーザーの所属とWorkspace内の役割を管理し、認可の根拠にします。
class WorkspaceMember(Record, Base):
    __tablename__ = "workspace_members"
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[Role] = mapped_column(enum_column(Role))
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)


# Workspaceに属する業務レコードへ共通の所属カラムを付与します。
class TenantRecord(Record):
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)


# 投稿制作の前提となるブランド方針・ターゲット・禁止語・ガイドラインを保持します。
class Brand(TenantRecord, Base):
    __tablename__ = "brands"
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(200), default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    brand_tone: Mapped[str] = mapped_column(Text, default="")
    ng_words: Mapped[list] = mapped_column(JSON, default=list)
    sns_goals: Mapped[dict] = mapped_column(JSON, default=dict)
    brand_guidelines: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


# SNSアカウントのメタデータと接続状態を管理します。認証トークンは保持しません。
class SocialAccount(TenantRecord, Base):
    __tablename__ = "social_accounts"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    platform: Mapped[Platform] = mapped_column(enum_column(Platform))
    name: Mapped[str] = mapped_column(String(200))
    external_account_id: Mapped[str | None] = mapped_column(String(200))
    connection_status: Mapped[ConnectionStatus] = mapped_column(enum_column(ConnectionStatus))
    followers: Mapped[int] = mapped_column(Integer, default=0)
    last_sync: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("brand_id", "platform", "name"),
        CheckConstraint("followers >= 0"),
    )


# Workspace内のAI社員の役割・状態・画面表示用情報を保存します。
class Agent(TenantRecord, Base):
    __tablename__ = "agents"
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[AgentRole] = mapped_column(enum_column(AgentRole))
    status: Mapped[AgentStatus] = mapped_column(enum_column(AgentStatus), default=AgentStatus.IDLE)
    color: Mapped[str] = mapped_column(String(20), default="#639bbc")
    task: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=1)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    history: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("workspace_id", "role"),)


# 投稿内容・業務状態・版番号・承認版を管理する中心モデルです。
class Content(TenantRecord, Base):
    __tablename__ = "contents"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    platform: Mapped[Platform] = mapped_column(enum_column(Platform))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    cta: Mapped[str] = mapped_column(Text, default="")
    media: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[ContentStatus] = mapped_column(enum_column(ContentStatus), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assigned_agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"))
    purpose: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(Text, default="")
    target: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    content_hash: Mapped[str] = mapped_column(String(64))
    approved_version: Mapped[int | None] = mapped_column(Integer)
    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (Index("ix_contents_workspace_brand", "workspace_id", "brand_id"),)


# 投稿の版ごとの内容を保存し、承認時点の内容へ遡れるようにします。
class ContentVersion(Record, Base):
    __tablename__ = "content_versions"
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("content_id", "version"),)


# 誰がどの版を承認・差戻ししたかをハッシュとともに記録します。
class ContentApproval(Record, Base):
    __tablename__ = "content_approvals"
    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text, default="")


# 投稿予約と取消履歴を保持します。有効予約の重複は部分一意制約で防ぎます。
class ContentSchedule(TenantRecord, Base):
    __tablename__ = "content_schedules"
    content_id: Mapped[str] = mapped_column(ForeignKey("contents.id"), index=True)
    social_account_id: Mapped[str] = mapped_column(ForeignKey("social_accounts.id"))
    scheduled_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    approved_version: Mapped[int] = mapped_column(Integer)
    execution_mode: Mapped[str] = mapped_column(String(20), default="MOCK")
    __table_args__ = (
        Index(
            "uq_active_content_schedule",
            "content_id",
            unique=True,
            postgresql_where=(status == "SCHEDULED"),
            sqlite_where=(status == "SCHEDULED"),
        ),
        CheckConstraint("status IN ('SCHEDULED', 'CANCELLED')"),
    )


# AI社員への依頼・実行モード・入力・結果・完了状態を追跡します。
class AgentTask(TenantRecord, Base):
    __tablename__ = "agent_tasks"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(100))
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[TaskStatus] = mapped_column(enum_column(TaskStatus))
    execution_mode: Mapped[str] = mapped_column(String(20), default="MOCK")
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


# AI社員が返すメッセージと、関連するタスクや出典を保存します。
class AgentMessage(TenantRecord, Base):
    __tablename__ = "agent_messages"
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("agent_tasks.id"))
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="SAMPLE")


# Account日次値とPost日次値を区別して保持し、分析時の二重計上を防ぎます。
class Metric(TenantRecord, Base):
    """Daily increments; followers is an end-of-day account snapshot (not additive)."""

    __tablename__ = "metrics"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    social_account_id: Mapped[str] = mapped_column(ForeignKey("social_accounts.id"), index=True)
    content_id: Mapped[str | None] = mapped_column(ForeignKey("contents.id"))
    platform: Mapped[Platform] = mapped_column(enum_column(Platform))
    measured_on: Mapped[object] = mapped_column(Date, index=True)
    followers: Mapped[int | None] = mapped_column(Integer)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(20), default="SAMPLE")
    __table_args__ = (
        Index(
            "uq_post_metric_day",
            "content_id",
            "measured_on",
            unique=True,
            postgresql_where=content_id.is_not(None),
            sqlite_where=content_id.is_not(None),
        ),
        Index(
            "uq_account_metric_day",
            "social_account_id",
            "measured_on",
            unique=True,
            postgresql_where=content_id.is_(None),
            sqlite_where=content_id.is_(None),
        ),
        CheckConstraint(
            "impressions >= 0 AND reach >= 0 AND likes >= 0 AND comments >= 0 "
            "AND shares >= 0 AND saves >= 0 AND (followers IS NULL OR followers >= 0)"
        ),
    )


# 分析の要約・仮説・提案・次の行動と根拠を構造化して保存します。
class AnalysisReport(TenantRecord, Base):
    __tablename__ = "analysis_reports"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    good_points: Mapped[list] = mapped_column(JSON, default=list)
    problems: Mapped[list] = mapped_column(JSON, default=list)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    hypotheses: Mapped[list] = mapped_column(JSON, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    next_actions: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(30), default="MANUAL")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)


# 監視イベントの種別・深刻度・説明と出典を保存します。
class MonitoringEvent(TenantRecord, Base):
    __tablename__ = "monitoring_events"
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(30))
    link: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(20), default="SAMPLE")


# ユーザーごとの通知と既読状態を管理します。
class Notification(TenantRecord, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    link: Mapped[str] = mapped_column(String(500), default="")


# 会議の参加者・決定事項・アクション項目を保存します。
class Meeting(TenantRecord, Base):
    __tablename__ = "meetings"
    meeting_type: Mapped[str] = mapped_column(String(50))
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    participants: Mapped[list] = mapped_column(JSON, default=list)
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    action_items: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), default="SAMPLE")


# 会議内の発言を社員と発言順に紐付けます。
class MeetingMessage(Record, Base):
    __tablename__ = "meeting_messages"
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    message: Mapped[str] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("meeting_id", "sequence"),)


# 操作主体・対象・request_idを記録します。公開APIから更新・削除はできません。
class AuditLog(Record, Base):
    __tablename__ = "audit_logs"
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(36))
    request_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
