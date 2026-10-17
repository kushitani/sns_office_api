# 概要: APIの入力検証・レスポンス・ページング形式をPydanticモデルで定義します。
from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from sns_office.models.entities import (
    AgentRole,
    AgentStatus,
    ConnectionStatus,
    ContentStatus,
    Platform,
    TaskStatus,
)

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
Text = Annotated[str, StringConstraints(max_length=20000)]
ID = Annotated[str, StringConstraints(min_length=1, max_length=36)]
T = TypeVar("T")


# Inputの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Outputの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Recordの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class RecordOut(Output):
    id: str
    created_at: datetime
    updated_at: datetime


# Tenantの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class TenantOut(RecordOut):
    workspace_id: str


# Pageの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# ErrorBodyの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: str | None = None


# ErrorResponseの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class ErrorResponse(BaseModel):
    error: ErrorBody


# Registerの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Register(Input):
    email: EmailStr
    name: Name
    password: str = Field(min_length=12, max_length=128)


# Loginの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Login(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# Refreshの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Refresh(Input):
    refresh_token: str = Field(min_length=32, max_length=200)


# Tokenの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# Userの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class UserOut(RecordOut):
    email: EmailStr
    name: str


# TimezoneInputの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class TimezoneInput(Input):
    timezone: str = "Asia/Tokyo"

    # 実在するIANAタイムゾーン名かを検証します。
    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown IANA timezone") from None
        return value


# Workspaceの新規作成に必要な入力と値域を定義します。
class WorkspaceCreate(TimezoneInput):
    name: Name
    week_start_day: int = Field(default=0, ge=0, le=6)


# Workspaceの部分更新入力です。未送信項目と明示的なnullを区別します。
class WorkspacePatch(TimezoneInput):
    name: Name | None = None
    week_start_day: int | None = Field(default=None, ge=0, le=6)


# Workspaceの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class WorkspaceOut(RecordOut):
    owner_id: str
    name: str
    timezone: str
    week_start_day: int


# BrandFieldsの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class BrandFields(Input):
    name: Name
    description: Text = ""
    industry: str = Field(default="", max_length=200)
    target_audience: Text = ""
    brand_tone: Text = ""
    ng_words: list[str] = Field(default_factory=list, max_length=100)
    sns_goals: dict = Field(default_factory=dict)
    brand_guidelines: dict = Field(default_factory=dict)


# Brandの新規作成に必要な入力と値域を定義します。
class BrandCreate(BrandFields):
    workspace_id: ID


# Brandの部分更新入力です。未送信項目と明示的なnullを区別します。
class BrandPatch(Input):
    version: int = Field(ge=1)
    name: Name | None = None
    description: Text | None = None
    industry: str | None = Field(default=None, max_length=200)
    target_audience: Text | None = None
    brand_tone: Text | None = None
    ng_words: list[str] | None = Field(default=None, max_length=100)
    sns_goals: dict | None = None
    brand_guidelines: dict | None = None


# Brandの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class BrandOut(TenantOut, BrandFields):
    version: int


# Accountの新規作成に必要な入力と値域を定義します。
class AccountCreate(Input):
    brand_id: ID
    platform: Platform
    name: str = Field(min_length=1, max_length=200)
    external_account_id: str | None = Field(default=None, max_length=200)
    connection_status: Literal["MOCK", "DISCONNECTED"] = "MOCK"
    followers: int = Field(default=0, ge=0)


# Accountの部分更新入力です。未送信項目と明示的なnullを区別します。
class AccountPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    external_account_id: str | None = Field(default=None, max_length=200)
    connection_status: Literal["MOCK", "DISCONNECTED"] | None = None
    followers: int | None = Field(default=None, ge=0)


# Accountの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class AccountOut(TenantOut):
    brand_id: str
    platform: Platform
    name: str
    external_account_id: str | None
    connection_status: ConnectionStatus
    followers: int
    last_sync: datetime | None


# ContentFieldsの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class ContentFields(Input):
    platform: Platform
    title: Title
    body: Text = ""
    hashtags: list[str] = Field(default_factory=list, max_length=100)
    cta: Text = ""
    media: list[dict] = Field(default_factory=list, max_length=20)
    assigned_agent_id: ID | None = None
    purpose: Text = ""
    tone: Text = ""
    target: Text = ""
    instructions: Text = ""


# Contentの新規作成に必要な入力と値域を定義します。
class ContentCreate(ContentFields):
    brand_id: ID
    status: Literal["IDEA", "PLANNED", "DRAFT"] = "DRAFT"


# Contentの部分更新入力です。未送信項目と明示的なnullを区別します。
class ContentPatch(Input):
    version: int = Field(ge=1)
    platform: Platform | None = None
    title: Title | None = None
    body: Text | None = None
    hashtags: list[str] | None = Field(default=None, max_length=100)
    cta: Text | None = None
    media: list[dict] | None = Field(default=None, max_length=20)
    assigned_agent_id: ID | None = None
    purpose: Text | None = None
    tone: Text | None = None
    target: Text | None = None
    instructions: Text | None = None
    status: Literal["IDEA", "PLANNED", "DRAFT"] | None = None


# Contentの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class ContentOut(TenantOut, ContentFields):
    brand_id: str
    created_by: str
    status: ContentStatus
    version: int
    approved_version: int | None
    content_hash: str
    scheduled_at: datetime | None = None
    author: str = ""
    history: list[str] = Field(default_factory=list)


# Decisionの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Decision(Input):
    version: int = Field(ge=1)
    reason: Text = ""


# Approvalの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class ApprovalOut(RecordOut):
    content_id: str
    version: int
    content_hash: str
    actor_id: str
    decision: str
    reason: str


# Scheduleの新規作成に必要な入力と値域を定義します。
class ScheduleCreate(TimezoneInput):
    content_id: ID
    social_account_id: ID
    scheduled_at: AwareDatetime


# Scheduleの部分更新入力です。未送信項目と明示的なnullを区別します。
class SchedulePatch(TimezoneInput):
    scheduled_at: AwareDatetime


# Scheduleの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class ScheduleOut(TenantOut):
    content_id: str
    social_account_id: str
    scheduled_at: datetime
    timezone: str
    status: Literal["SCHEDULED", "CANCELLED"]
    approved_version: int
    execution_mode: Literal["MOCK"]


# CalendarEventの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class CalendarEvent(ScheduleOut):
    title: str
    platform: Platform
    brand_id: str
    content_status: ContentStatus
    assigned_agent_id: str | None
    purpose: str


# Agentの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class AgentOut(TenantOut):
    name: str
    role: AgentRole
    status: AgentStatus
    color: str
    task: str
    progress: int
    total: int
    completed: int
    history: list[str]


# Taskの新規作成に必要な入力と値域を定義します。
class TaskCreate(Input):
    agent_id: ID
    task_type: Name
    input: dict = Field(default_factory=dict)
    execution_mode: Literal["MOCK"] = "MOCK"


# Taskの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class TaskOut(TenantOut):
    agent_id: str
    task_type: str
    input: dict
    output: dict | None
    status: TaskStatus
    execution_mode: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


# Messageの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class MessageOut(TenantOut):
    agent_id: str
    task_id: str | None
    message: str
    source: str


# Reportの新規作成に必要な入力と値域を定義します。
class ReportCreate(Input):
    brand_id: ID
    summary: Text
    good_points: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence: dict = Field(default_factory=dict)


# Reportの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class ReportOut(TenantOut, ReportCreate):
    source: str


# Monitoringの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class MonitoringOut(TenantOut):
    brand_id: str
    type: str
    title: str
    message: str
    severity: str
    link: str
    source: str


# Notificationの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class NotificationOut(TenantOut):
    user_id: str
    type: str
    title: str
    message: str
    is_read: bool
    link: str


# MeetingMessageの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class MeetingMessageOut(RecordOut):
    meeting_id: str
    agent_id: str
    message: str
    sequence: int


# Meetingの公開レスポンスを定義し、内部カラムの意図しない露出を防ぎます。
class MeetingOut(TenantOut):
    meeting_type: str
    started_at: datetime
    completed_at: datetime | None
    participants: list[str]
    decisions: list[str]
    action_items: list[str]
    source: str
    messages: list[MeetingMessageOut] = Field(default_factory=list)


# KPIの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class KPI(BaseModel):
    followers: int | None
    impressions: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float | None


# AnalyticsMetaの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class AnalyticsMeta(BaseModel):
    brand_id: str
    start_date: date | None
    end_date: date | None
    platform: Platform | None
    timezone: str
    metric_definition_version: str = "daily-v1"
    source: str = "SAMPLE"
    source_ids: list[str]
    data_freshness: datetime | None
    warnings: list[str]


# Overviewの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class Overview(BaseModel):
    metrics: KPI
    meta: AnalyticsMeta


# MetricGroupの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class MetricGroup(KPI):
    platform: Platform | None = None
    content_id: str | None = None
    measured_on: date | None = None


# AnalyticsGroupsの入出力契約を定義します。OpenAPIのスキーマ生成にも使用します。
class AnalyticsGroups(BaseModel):
    items: list[MetricGroup]
    total: int
    limit: int
    offset: int
    meta: AnalyticsMeta
