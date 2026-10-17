# 概要: 業務APIのURL・入力・応答型を定義します。認可と状態変更の判断はServiceが担当します。
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from sns_office.api.dependencies import Service
from sns_office.models import entities as m
from sns_office.schemas import api as s
from sns_office.services.analytics import AnalyticsService

router = APIRouter()
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


# Workspaceの一覧取得をServiceへ委譲します。
@router.get("/workspaces", response_model=s.Page[s.WorkspaceOut], tags=["workspaces"])
def list_workspaces(service: Service, limit: Limit = 50, offset: Offset = 0):
    result = service.list(m.Workspace, limit=limit, offset=offset)
    return result


# Workspaceの詳細取得をServiceへ委譲します。
@router.get("/workspaces/{resource_id}", response_model=s.WorkspaceOut, tags=["workspaces"])
def get_workspaces(resource_id: str, service: Service):
    row = service.get(m.Workspace, resource_id)
    return row


# Workspaceの新規作成をServiceへ委譲します。
@router.post("/workspaces", response_model=s.WorkspaceOut, status_code=201, tags=["workspaces"])
def create_workspaces(data: s.WorkspaceCreate, service: Service):
    return service.create_workspace(data)


# Workspaceの部分更新をServiceへ委譲します。
@router.patch("/workspaces/{resource_id}", response_model=s.WorkspaceOut, tags=["workspaces"])
def patch_workspaces(resource_id: str, data: s.WorkspacePatch, service: Service):
    return service.patch_workspace(resource_id, data)


# ブランドの一覧取得をServiceへ委譲します。
@router.get("/brands", response_model=s.Page[s.BrandOut], tags=["brands"])
def list_brands(
    service: Service, limit: Limit = 50, offset: Offset = 0, workspace_id: str | None = None
):
    result = service.list(m.Brand, limit=limit, offset=offset, workspace_id=workspace_id)
    return result


# ブランドの詳細取得をServiceへ委譲します。
@router.get("/brands/{resource_id}", response_model=s.BrandOut, tags=["brands"])
def get_brands(resource_id: str, service: Service):
    row = service.get(m.Brand, resource_id)
    return row


# ブランドの新規作成をServiceへ委譲します。
@router.post("/brands", response_model=s.BrandOut, status_code=201, tags=["brands"])
def create_brands(data: s.BrandCreate, service: Service):
    return service.create_brand(data)


# ブランドの部分更新をServiceへ委譲します。
@router.patch("/brands/{resource_id}", response_model=s.BrandOut, tags=["brands"])
def patch_brands(resource_id: str, data: s.BrandPatch, service: Service):
    return service.patch_brand(resource_id, data)


# ブランドの削除・取消をServiceへ委譲します。
@router.delete("/brands/{resource_id}", status_code=204, tags=["brands"])
def delete_brands(resource_id: str, service: Service):
    service.delete(m.Brand, resource_id)


# SNSアカウントの一覧取得をServiceへ委譲します。
@router.get("/social-accounts", response_model=s.Page[s.AccountOut], tags=["social-accounts"])
def list_social_accounts(
    service: Service,
    limit: Limit = 50,
    offset: Offset = 0,
    brand_id: str | None = None,
    platform: m.Platform | None = None,
):
    result = service.list(
        m.SocialAccount, limit=limit, offset=offset, brand_id=brand_id, platform=platform
    )
    return result


# SNSアカウントの詳細取得をServiceへ委譲します。
@router.get("/social-accounts/{resource_id}", response_model=s.AccountOut, tags=["social-accounts"])
def get_social_accounts(resource_id: str, service: Service):
    row = service.get(m.SocialAccount, resource_id)
    return row


# SNSアカウントの新規作成をServiceへ委譲します。
@router.post(
    "/social-accounts", response_model=s.AccountOut, status_code=201, tags=["social-accounts"]
)
def create_social_accounts(data: s.AccountCreate, service: Service):
    return service.create_account(data)


# SNSアカウントの部分更新をServiceへ委譲します。
@router.patch(
    "/social-accounts/{resource_id}", response_model=s.AccountOut, tags=["social-accounts"]
)
def patch_social_accounts(resource_id: str, data: s.AccountPatch, service: Service):
    return service.patch_account(resource_id, data)


# SNSアカウントの削除・取消をServiceへ委譲します。
@router.delete("/social-accounts/{resource_id}", status_code=204, tags=["social-accounts"])
def delete_social_accounts(resource_id: str, service: Service):
    service.delete(m.SocialAccount, resource_id)


# 投稿の一覧取得をServiceへ委譲します。
@router.get("/contents", response_model=s.Page[s.ContentOut], tags=["contents"])
def list_contents(
    service: Service,
    limit: Limit = 50,
    offset: Offset = 0,
    brand_id: str | None = None,
    platform: m.Platform | None = None,
    status: m.ContentStatus | None = None,
):
    result = service.content_list(
        limit=limit, offset=offset, brand_id=brand_id, platform=platform, status=status
    )
    return result


# 投稿の詳細取得をServiceへ委譲します。
@router.get("/contents/{resource_id}", response_model=s.ContentOut, tags=["contents"])
def get_contents(resource_id: str, service: Service):
    row = service.get(m.Content, resource_id)
    return service.content_view(row)


# 投稿の新規作成をServiceへ委譲します。
@router.post("/contents", response_model=s.ContentOut, status_code=201, tags=["contents"])
def create_contents(data: s.ContentCreate, service: Service):
    return service.create_content(data)


# 投稿の部分更新をServiceへ委譲します。
@router.patch("/contents/{resource_id}", response_model=s.ContentOut, tags=["contents"])
def patch_contents(resource_id: str, data: s.ContentPatch, service: Service):
    return service.patch_content(resource_id, data)


# 投稿の削除・取消をServiceへ委譲します。
@router.delete("/contents/{resource_id}", status_code=204, tags=["contents"])
def delete_contents(resource_id: str, service: Service):
    service.delete(m.Content, resource_id)


# 予約の一覧取得をServiceへ委譲します。
@router.get("/schedules", response_model=s.Page[s.ScheduleOut], tags=["schedules"])
def list_schedules(
    service: Service, limit: Limit = 50, offset: Offset = 0, workspace_id: str | None = None
):
    result = service.list(m.ContentSchedule, limit=limit, offset=offset, workspace_id=workspace_id)
    return result


# 予約の詳細取得をServiceへ委譲します。
@router.get("/schedules/{resource_id}", response_model=s.ScheduleOut, tags=["schedules"])
def get_schedules(resource_id: str, service: Service):
    row = service.get(m.ContentSchedule, resource_id)
    return row


# 予約の新規作成をServiceへ委譲します。
@router.post("/schedules", response_model=s.ScheduleOut, status_code=201, tags=["schedules"])
def create_schedules(data: s.ScheduleCreate, service: Service):
    return service.create_schedule(data)


# 予約の部分更新をServiceへ委譲します。
@router.patch("/schedules/{resource_id}", response_model=s.ScheduleOut, tags=["schedules"])
def patch_schedules(resource_id: str, data: s.SchedulePatch, service: Service):
    return service.patch_schedule(resource_id, data)


# 予約の削除・取消をServiceへ委譲します。
@router.delete("/schedules/{resource_id}", status_code=204, tags=["schedules"])
def delete_schedules(resource_id: str, service: Service):
    service.cancel_schedule(resource_id)


# AI社員の一覧取得をServiceへ委譲します。
@router.get("/agents", response_model=s.Page[s.AgentOut], tags=["agents"])
def list_agents(
    service: Service, limit: Limit = 50, offset: Offset = 0, workspace_id: str | None = None
):
    result = service.list(m.Agent, limit=limit, offset=offset, workspace_id=workspace_id)
    return result


# AI社員の詳細取得をServiceへ委譲します。
@router.get("/agents/{resource_id}", response_model=s.AgentOut, tags=["agents"])
def get_agents(resource_id: str, service: Service):
    row = service.get(m.Agent, resource_id)
    return row


# AIタスクの一覧取得をServiceへ委譲します。
@router.get("/agent-tasks", response_model=s.Page[s.TaskOut], tags=["agent-tasks"])
def list_agent_tasks(
    service: Service, limit: Limit = 50, offset: Offset = 0, workspace_id: str | None = None
):
    result = service.list(m.AgentTask, limit=limit, offset=offset, workspace_id=workspace_id)
    return result


# AIタスクの詳細取得をServiceへ委譲します。
@router.get("/agent-tasks/{resource_id}", response_model=s.TaskOut, tags=["agent-tasks"])
def get_agent_tasks(resource_id: str, service: Service):
    row = service.get(m.AgentTask, resource_id)
    return row


# AIタスクの新規作成をServiceへ委譲します。
@router.post("/agent-tasks", response_model=s.TaskOut, status_code=201, tags=["agent-tasks"])
def create_agent_tasks(data: s.TaskCreate, service: Service):
    return service.create_task(data)


# 分析レポートの一覧取得をServiceへ委譲します。
@router.get("/reports", response_model=s.Page[s.ReportOut], tags=["reports"])
def list_reports(
    service: Service, limit: Limit = 50, offset: Offset = 0, brand_id: str | None = None
):
    result = service.list(m.AnalysisReport, limit=limit, offset=offset, brand_id=brand_id)
    return result


# 分析レポートの詳細取得をServiceへ委譲します。
@router.get("/reports/{resource_id}", response_model=s.ReportOut, tags=["reports"])
def get_reports(resource_id: str, service: Service):
    row = service.get(m.AnalysisReport, resource_id)
    return row


# 分析レポートの新規作成をServiceへ委譲します。
@router.post("/reports", response_model=s.ReportOut, status_code=201, tags=["reports"])
def create_reports(data: s.ReportCreate, service: Service):
    return service.create_report(data)


# 通知の一覧取得をServiceへ委譲します。
@router.get("/notifications", response_model=s.Page[s.NotificationOut], tags=["notifications"])
def list_notifications(
    service: Service, limit: Limit = 50, offset: Offset = 0, workspace_id: str | None = None
):
    result = service.list(m.Notification, limit=limit, offset=offset, workspace_id=workspace_id)
    return result


# 通知の詳細取得をServiceへ委譲します。
@router.get(
    "/notifications/{resource_id}", response_model=s.NotificationOut, tags=["notifications"]
)
def get_notifications(resource_id: str, service: Service):
    row = service.get(m.Notification, resource_id)
    return row


# 会議の一覧取得をServiceへ委譲します。
@router.get("/meetings", response_model=s.Page[s.MeetingOut], tags=["meetings"])
def list_meetings(
    service: Service, limit: Limit = 50, offset: Offset = 0, workspace_id: str | None = None
):
    result = service.list(m.Meeting, limit=limit, offset=offset, workspace_id=workspace_id)
    result["items"] = [service.meeting_view(row) for row in result["items"]]
    return result


# 会議の詳細取得をServiceへ委譲します。
@router.get("/meetings/{resource_id}", response_model=s.MeetingOut, tags=["meetings"])
def get_meetings(resource_id: str, service: Service):
    row = service.get(m.Meeting, resource_id)
    return service.meeting_view(row)


# 投稿の承認依頼をServiceへ委譲します。
@router.post("/contents/{content_id}/submit-review", response_model=s.ContentOut, tags=["Approval"])
def submit_review(content_id: str, data: s.Decision, service: Service):
    return service.transition(content_id, "submit-review", data)


# 版を指定した承認をServiceへ委譲します。
@router.post("/contents/{content_id}/approve", response_model=s.ContentOut, tags=["Approval"])
def approve(content_id: str, data: s.Decision, service: Service):
    return service.transition(content_id, "approve", data)


# 理由付きの差戻しをServiceへ委譲します。
@router.post("/contents/{content_id}/reject", response_model=s.ContentOut, tags=["Approval"])
def reject(content_id: str, data: s.Decision, service: Service):
    return service.transition(content_id, "reject", data)


# 投稿の参照権限を確認した後に、承認・差戻し等の履歴をページ単位で返します。
@router.get(
    "/contents/{content_id}/approvals", response_model=s.Page[s.ApprovalOut], tags=["Approval"]
)
def approvals(content_id: str, service: Service, limit: Limit = 50, offset: Offset = 0):
    return service.approvals(content_id, limit, offset)


# 対象社員への参照権限を確認したタスク一覧を取得します。
@router.get("/agents/{agent_id}/tasks", response_model=s.Page[s.TaskOut], tags=["agents"])
def agent_tasks(agent_id: str, service: Service, limit: Limit = 50, offset: Offset = 0):
    return service.list(m.AgentTask, agent_id=agent_id, limit=limit, offset=offset)


# 対象社員への参照権限を確認したメッセージ一覧を取得します。
@router.get("/agents/{agent_id}/messages", response_model=s.Page[s.MessageOut], tags=["agents"])
def agent_messages(agent_id: str, service: Service, limit: Limit = 50, offset: Offset = 0):
    return service.list(m.AgentMessage, agent_id=agent_id, limit=limit, offset=offset)


# 本人宛の通知だけを既読にし、他ユーザーの通知操作を防ぎます。
@router.patch(
    "/notifications/{resource_id}/read", response_model=s.NotificationOut, tags=["notifications"]
)
def read_notification(resource_id: str, service: Service):
    return service.read_notification(resource_id)


# Workspaceの日付境界をUTCへ変換し、両端の日付を含む有効予約一覧を取得します。
@router.get("/calendar", response_model=s.Page[s.CalendarEvent], tags=["Calendar"])
def calendar(
    service: Service,
    brand_id: str,
    start_date: date,
    end_date: date,
    platform: m.Platform | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    return service.calendar(brand_id, start_date, end_date, platform, limit, offset)


# 認証済み利用者の権限を引き継いで、指定条件の分析結果を取得します。
@router.get("/analytics/overview", response_model=s.Overview, tags=["Analytics"])
def analytics_overview(
    service: Service,
    brand_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    platform: m.Platform | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    analytics = AnalyticsService(service.db, service.user, service.request_id)
    filters = dict(brand_id=brand_id, start_date=start_date, end_date=end_date, platform=platform)
    return analytics.overview(**filters)


# 認証済み利用者の権限を引き継いで、指定条件の分析結果を取得します。
@router.get("/analytics/platforms", response_model=s.AnalyticsGroups, tags=["Analytics"])
def analytics_platforms(
    service: Service,
    brand_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    platform: m.Platform | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    analytics = AnalyticsService(service.db, service.user, service.request_id)
    filters = dict(brand_id=brand_id, start_date=start_date, end_date=end_date, platform=platform)
    return analytics.groups("platform", limit=limit, offset=offset, **filters)


# 認証済み利用者の権限を引き継いで、指定条件の分析結果を取得します。
@router.get("/analytics/posts", response_model=s.AnalyticsGroups, tags=["Analytics"])
def analytics_posts(
    service: Service,
    brand_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    platform: m.Platform | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    analytics = AnalyticsService(service.db, service.user, service.request_id)
    filters = dict(brand_id=brand_id, start_date=start_date, end_date=end_date, platform=platform)
    return analytics.groups("content_id", limit=limit, offset=offset, **filters)


# 認証済み利用者の権限を引き継いで、指定条件の分析結果を取得します。
@router.get("/analytics/trends", response_model=s.AnalyticsGroups, tags=["Analytics"])
def analytics_trends(
    service: Service,
    brand_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    platform: m.Platform | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    analytics = AnalyticsService(service.db, service.user, service.request_id)
    filters = dict(brand_id=brand_id, start_date=start_date, end_date=end_date, platform=platform)
    return analytics.groups("measured_on", limit=limit, offset=offset, **filters)


# Workspaceの範囲内で監視イベントまたは警告を取得します。
@router.get("/monitoring/events", response_model=s.Page[s.MonitoringOut], tags=["Monitoring"])
def monitoring_events(
    service: Service,
    workspace_id: str | None = None,
    brand_id: str | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    return service.monitoring(
        alerts=False, workspace_id=workspace_id, brand_id=brand_id, limit=limit, offset=offset
    )


# Workspaceの範囲内で監視イベントまたは警告を取得します。
@router.get("/monitoring/alerts", response_model=s.Page[s.MonitoringOut], tags=["Monitoring"])
def monitoring_alerts(
    service: Service,
    workspace_id: str | None = None,
    brand_id: str | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    return service.monitoring(
        alerts=True, workspace_id=workspace_id, brand_id=brand_id, limit=limit, offset=offset
    )
