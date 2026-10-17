# 概要: 開発・テスト環境向けのサンプルを明示投入します。起動時には実行しません。
"""Explicit development-only, transactional, repeatable sample data installation."""

import json
import uuid
from datetime import date, timedelta
from importlib.resources import files

from sqlalchemy.orm import Session

from sns_office.core.config import get_settings
from sns_office.core.security import password_hash, utcnow
from sns_office.db.session import engine
from sns_office.models.entities import (
    Agent,
    AgentMessage,
    AgentRole,
    AnalysisReport,
    Brand,
    Content,
    ContentApproval,
    ContentSchedule,
    Meeting,
    MeetingMessage,
    Metric,
    MonitoringEvent,
    Notification,
    SocialAccount,
    User,
    Workspace,
)
from sns_office.repositories.store import Repository
from sns_office.schemas.api import WorkspaceCreate
from sns_office.services.business import BusinessService, content_hash

NAMESPACE = uuid.UUID("f71eb07b-2f09-4104-aa7f-de6730601397")


# 同じサンプル識別子から同じUUIDを作り、Seedの再実行を追跡しやすくします。
def sample_id(key):
    return str(uuid.uuid5(NAMESPACE, key))


# 本番実行を拒否し、既存のデモ環境がある場合は重複作成を避けます。
def seed(db: Session):
    settings = get_settings()
    if settings.app_env not in {"development", "test"}:
        raise RuntimeError("Seed is allowed only in development/test environments")
    repo = Repository(db)
    user_id = sample_id("demo-user")
    existing = repo.one(User, User.email == settings.demo_email.lower())
    if existing and existing.id != user_id:
        raise RuntimeError("Demo email is already owned by a non-demo user")
    user = repo.one(User, User.id == user_id)
    if user is None:
        user = repo.add(
            User,
            id=user_id,
            name="Demo Owner",
            email=settings.demo_email.lower(),
            password_hash=password_hash.hash(settings.demo_password),
        )
    workspace = repo.one(Workspace, Workspace.owner_id == user_id, Workspace.name == "Demo Office")
    if workspace:
        return {"user_id": user.id, "workspace_id": workspace.id, "created": False}
    svc = BusinessService(db, user, "development-seed")
    workspace = svc.create_workspace(WorkspaceCreate(name="Demo Office"))
    brand = repo.add(
        Brand,
        workspace_id=workspace.id,
        name="Studio Note",
        description="毎日の仕事に、小さな発見を。",
        industry="ライフスタイル",
        target_audience="20〜30代の働く人",
        brand_tone="親しみやすい",
        ng_words=["絶対", "必ず儲かる"],
        sns_goals={"engagement": "向上"},
        brand_guidelines={"mode": "Manual", "ai": False, "notifications": True},
    )
    samples = json.loads(files("sns_office").joinpath("sample_data.json").read_text())
    agents = {
        agent.role.value: agent for agent in repo.all(Agent, Agent.workspace_id == workspace.id)
    }
    agent_keys = {}
    for sample in samples["agents"]:
        agent = agents[sample["role"].upper()]
        agent_keys[sample["id"]] = agent.id
        for key in ("color", "task", "progress", "total", "completed", "history"):
            setattr(agent, key, sample[key])
        # Samples describe historic demonstrations; no actual work is running.
        agent.status = "IDLE"
        repo.add(
            AgentMessage,
            workspace_id=workspace.id,
            agent_id=agent.id,
            message=f"Sample history: {sample['task']}",
            source="SAMPLE",
        )
    agent_keys["nao"] = agents[AgentRole.MONITOR].id
    accounts = {}
    for i, platform in enumerate(["X", "Instagram", "Threads", "TikTok", "YouTube"]):
        accounts[platform] = repo.add(
            SocialAccount,
            workspace_id=workspace.id,
            brand_id=brand.id,
            platform=platform,
            name="@studio_note",
            connection_status="MOCK" if i < 3 else "DISCONNECTED",
            followers=[12840, 6820, 3210, 1520, 502][i],
        )
    posts = []
    for i, (title, platform, status, original_time, performance) in enumerate(samples["posts"]):
        content = Content(
            id=sample_id(f"post-{i + 1}"),
            workspace_id=workspace.id,
            brand_id=brand.id,
            platform=platform,
            status=status,
            title=title,
            body=f"{title}\n\n毎日の仕事に、小さな発見を。あなたの「あるある」もコメントで教えてください。",
            hashtags=["#働くを楽しむ", "#チームの日常"],
            cta="保存して、明日の仕事に。",
            media=[],
            created_by=user.id,
            assigned_agent_id=agent_keys["mika"],
            purpose="エンゲージメント向上",
            tone="親しみやすい",
            target="20〜30代の働く人",
            instructions="",
            approved_version=1 if status in {"APPROVED", "SCHEDULED"} else None,
        )
        content.content_hash = content_hash(content)
        db.add(content)
        db.flush()
        svc.save_version(content)
        if status in {"APPROVED", "SCHEDULED"}:
            repo.add(
                ContentApproval,
                content_id=content.id,
                version=content.version,
                content_hash=content.content_hash,
                actor_id=user.id,
                decision="APPROVE",
                reason="SAMPLE: approved fixture",
            )
        if status == "SCHEDULED":
            repo.add(
                ContentSchedule,
                workspace_id=workspace.id,
                content_id=content.id,
                social_account_id=accounts[platform].id,
                scheduled_at=utcnow() + timedelta(days=i + 1),
                timezone="Asia/Tokyo",
                status="SCHEDULED",
                approved_version=1,
                execution_mode="MOCK",
            )
        posts.append(content)
    # Daily account totals and post drilldowns are distinct grains; never summed together.
    for day in range(14):
        for i, account in enumerate(accounts.values()):
            repo.add(
                Metric,
                workspace_id=workspace.id,
                brand_id=brand.id,
                social_account_id=account.id,
                platform=account.platform,
                measured_on=date.today() - timedelta(days=13 - day),
                followers=account.followers - (13 - day) * 5,
                impressions=1000 + day * 100 + i * 50,
                reach=700 + day * 50,
                likes=50 + day,
                comments=3,
                shares=5,
                saves=8,
            )
    post = posts[2]
    repo.add(
        Metric,
        workspace_id=workspace.id,
        brand_id=brand.id,
        social_account_id=accounts[post.platform].id,
        platform=post.platform,
        content_id=post.id,
        measured_on=date.today(),
        impressions=10000,
        reach=7000,
        likes=700,
        comments=40,
        shares=40,
        saves=60,
    )
    repo.add(
        AnalysisReport,
        workspace_id=workspace.id,
        brand_id=brand.id,
        summary="サンプル分析：共感を生む投稿を比較しましょう。",
        good_points=["「チームの朝」投稿の反応率は8.4%です。"],
        problems=["Sample dataは実際のSNS実績ではありません。"],
        findings=["投稿別とアカウント別の集計粒度を分けています。"],
        hypotheses=["日常のストーリーが反応につながった可能性。因果は未確認です。"],
        recommendations=["テーマと配信時間を比較してください。"],
        next_actions=["投稿案を作成し、人が承認して予約する。"],
        source="SAMPLE",
        evidence={"content_ids": [post.id], "metric_definition_version": "daily-v1"},
    )
    for sample in samples["notifications"]:
        link = sample["link"]
        for i in range(1, 9):
            link = link.replace(f"post-{i}", sample_id(f"post-{i}"))
        repo.add(
            Notification,
            workspace_id=workspace.id,
            user_id=user.id,
            type=sample["type"],
            title=sample["title"],
            message=sample["detail"],
            is_read=sample["read"],
            link=link,
        )
    for kind, severity, title in [
        ("TREND", "INFO", "急上昇投稿"),
        ("ERROR", "ERROR", "Mockの投稿失敗"),
        ("WARNING", "WARNING", "未接続アカウント"),
        ("SUCCESS", "INFO", "サンプルの投稿状態"),
    ]:
        repo.add(
            MonitoringEvent,
            workspace_id=workspace.id,
            brand_id=brand.id,
            type=kind,
            severity=severity,
            title=title,
            message="Sample event; no live SNS monitoring",
            source="SAMPLE",
        )
    meeting = repo.add(
        Meeting,
        workspace_id=workspace.id,
        meeting_type="WEEKLY",
        started_at=utcnow() - timedelta(hours=1),
        completed_at=utcnow(),
        participants=list(agent_keys.values()),
        source="SAMPLE",
        decisions=["共感をテーマに3件の投稿案を作成"],
        action_items=["ユーザーが内容を確認し承認後に予約"],
    )
    for i, message in enumerate(samples["meeting"]):
        repo.add(
            MeetingMessage,
            meeting_id=meeting.id,
            agent_id=agent_keys[message["agent"]],
            message=message["text"],
            sequence=i,
        )
    from sns_office.schemas.api import TaskCreate

    svc.create_task(TaskCreate(agent_id=agent_keys["mika"], task_type="SAMPLE_DRAFT", input={}))
    svc.audit(workspace, "seed.install")
    db.flush()
    return {"user_id": user.id, "workspace_id": workspace.id, "brand_id": brand.id, "created": True}


# 明示的な起動時だけSeedを1トランザクションで投入します。
def main():
    with Session(engine()) as db, db.begin():
        result = seed(db)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
