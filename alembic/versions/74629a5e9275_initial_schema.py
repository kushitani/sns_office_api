# 概要: 初期リビジョンです。20テーブルと業務制約を作成し、解除する手順を固定しています。
"""initial_schema"""

import sqlalchemy as sa

from alembic import op

revision = "74629a5e9275"
down_revision = None
branch_labels = None
depends_on = None


# このリビジョンで必要なテーブル・制約・インデックスを作成します。
def upgrade():
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_table(
        "workspaces",
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("week_start_day", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("week_start_day BETWEEN 0 AND 6"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspaces_owner_id"), "workspaces", ["owner_id"], unique=False)
    op.create_table(
        "agents",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "MANAGER",
                "WRITER",
                "ANALYST",
                "DESIGNER",
                "OPERATOR",
                "MONITOR",
                name="agentrole",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "IDLE",
                "THINKING",
                "WRITING",
                "ANALYZING",
                "POSTING",
                "MONITORING",
                "MEETING",
                "ERROR",
                name="agentstatus",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("color", sa.String(length=20), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "role"),
    )
    op.create_index(op.f("ix_agents_workspace_id"), "agents", ["workspace_id"], unique=False)
    op.create_table(
        "audit_logs",
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_workspace_id"), "audit_logs", ["workspace_id"], unique=False
    )
    op.create_table(
        "brands",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("industry", sa.String(length=200), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("brand_tone", sa.Text(), nullable=False),
        sa.Column("ng_words", sa.JSON(), nullable=False),
        sa.Column("sns_goals", sa.JSON(), nullable=False),
        sa.Column("brand_guidelines", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_brands_workspace_id"), "brands", ["workspace_id"], unique=False)
    op.create_table(
        "meetings",
        sa.Column("meeting_type", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("participants", sa.JSON(), nullable=False),
        sa.Column("decisions", sa.JSON(), nullable=False),
        sa.Column("action_items", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meetings_workspace_id"), "meetings", ["workspace_id"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_notifications_workspace_id"), "notifications", ["workspace_id"], unique=False
    )
    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "owner",
                "admin",
                "editor",
                "approver",
                "viewer",
                name="role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id"),
    )
    op.create_index(
        op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_workspace_members_workspace_id"),
        "workspace_members",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "agent_tasks",
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="taskstatus",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("execution_mode", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_tasks_agent_id"), "agent_tasks", ["agent_id"], unique=False)
    op.create_index(
        op.f("ix_agent_tasks_workspace_id"), "agent_tasks", ["workspace_id"], unique=False
    )
    op.create_table(
        "analysis_reports",
        sa.Column("brand_id", sa.String(length=36), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("good_points", sa.JSON(), nullable=False),
        sa.Column("problems", sa.JSON(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("hypotheses", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("next_actions", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analysis_reports_brand_id"), "analysis_reports", ["brand_id"], unique=False
    )
    op.create_index(
        op.f("ix_analysis_reports_workspace_id"), "analysis_reports", ["workspace_id"], unique=False
    )
    op.create_table(
        "contents",
        sa.Column("brand_id", sa.String(length=36), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "X",
                "Instagram",
                "Threads",
                "TikTok",
                "YouTube",
                name="platform",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=False),
        sa.Column("cta", sa.Text(), nullable=False),
        sa.Column("media", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "IDEA",
                "PLANNED",
                "GENERATING",
                "DRAFT",
                "REVIEW",
                "APPROVED",
                "SCHEDULED",
                "POSTING",
                "POSTED",
                "FAILED",
                name="contentstatus",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("assigned_agent_id", sa.String(length=36), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("tone", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("approved_version", sa.Integer(), nullable=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contents_brand_id"), "contents", ["brand_id"], unique=False)
    op.create_index(op.f("ix_contents_status"), "contents", ["status"], unique=False)
    op.create_index(
        "ix_contents_workspace_brand", "contents", ["workspace_id", "brand_id"], unique=False
    )
    op.create_index(op.f("ix_contents_workspace_id"), "contents", ["workspace_id"], unique=False)
    op.create_table(
        "meeting_messages",
        sa.Column("meeting_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_id", "sequence"),
    )
    op.create_index(
        op.f("ix_meeting_messages_meeting_id"), "meeting_messages", ["meeting_id"], unique=False
    )
    op.create_table(
        "monitoring_events",
        sa.Column("brand_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_monitoring_events_brand_id"), "monitoring_events", ["brand_id"], unique=False
    )
    op.create_index(
        op.f("ix_monitoring_events_workspace_id"),
        "monitoring_events",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "social_accounts",
        sa.Column("brand_id", sa.String(length=36), nullable=False),
        sa.Column(
            "platform",
            sa.Enum(
                "X",
                "Instagram",
                "Threads",
                "TikTok",
                "YouTube",
                name="platform",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("external_account_id", sa.String(length=200), nullable=True),
        sa.Column(
            "connection_status",
            sa.Enum(
                "MOCK",
                "DISCONNECTED",
                "CONNECTED",
                "REAUTH_REQUIRED",
                name="connectionstatus",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("followers", sa.Integer(), nullable=False),
        sa.Column("last_sync", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("followers >= 0"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "platform", "name"),
    )
    op.create_index(
        op.f("ix_social_accounts_brand_id"), "social_accounts", ["brand_id"], unique=False
    )
    op.create_index(
        op.f("ix_social_accounts_workspace_id"), "social_accounts", ["workspace_id"], unique=False
    )
    op.create_table(
        "agent_messages",
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_messages_agent_id"), "agent_messages", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_messages_workspace_id"), "agent_messages", ["workspace_id"], unique=False
    )
    op.create_table(
        "content_approvals",
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_approvals_content_id"), "content_approvals", ["content_id"], unique=False
    )
    op.create_table(
        "content_schedules",
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("social_account_id", sa.String(length=36), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("approved_version", sa.Integer(), nullable=False),
        sa.Column("execution_mode", sa.String(length=20), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('SCHEDULED', 'CANCELLED')"),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"]),
        sa.ForeignKeyConstraint(["social_account_id"], ["social_accounts.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_content_schedules_content_id"), "content_schedules", ["content_id"], unique=False
    )
    op.create_index(
        op.f("ix_content_schedules_scheduled_at"),
        "content_schedules",
        ["scheduled_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_content_schedules_workspace_id"),
        "content_schedules",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "uq_active_content_schedule",
        "content_schedules",
        ["content_id"],
        unique=True,
        postgresql_where=sa.text("status = 'SCHEDULED'"),
        sqlite_where=sa.text("status = 'SCHEDULED'"),
    )
    op.create_table(
        "content_versions",
        sa.Column("content_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id", "version"),
    )
    op.create_index(
        op.f("ix_content_versions_content_id"), "content_versions", ["content_id"], unique=False
    )
    op.create_table(
        "metrics",
        sa.Column("brand_id", sa.String(length=36), nullable=False),
        sa.Column("social_account_id", sa.String(length=36), nullable=False),
        sa.Column("content_id", sa.String(length=36), nullable=True),
        sa.Column(
            "platform",
            sa.Enum(
                "X",
                "Instagram",
                "Threads",
                "TikTok",
                "YouTube",
                name="platform",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("measured_on", sa.Date(), nullable=False),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("saves", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "impressions >= 0 AND reach >= 0 AND likes >= 0 AND comments >= 0 "
            "AND shares >= 0 AND saves >= 0 AND (followers IS NULL OR followers >= 0)"
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"]),
        sa.ForeignKeyConstraint(["social_account_id"], ["social_accounts.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_metrics_brand_id"), "metrics", ["brand_id"], unique=False)
    op.create_index(op.f("ix_metrics_measured_on"), "metrics", ["measured_on"], unique=False)
    op.create_index(
        op.f("ix_metrics_social_account_id"), "metrics", ["social_account_id"], unique=False
    )
    op.create_index(op.f("ix_metrics_workspace_id"), "metrics", ["workspace_id"], unique=False)
    op.create_index(
        "uq_account_metric_day",
        "metrics",
        ["social_account_id", "measured_on"],
        unique=True,
        postgresql_where=sa.text("content_id IS NULL"),
        sqlite_where=sa.text("content_id IS NULL"),
    )
    op.create_index(
        "uq_post_metric_day",
        "metrics",
        ["content_id", "measured_on"],
        unique=True,
        postgresql_where=sa.text("content_id IS NOT NULL"),
        sqlite_where=sa.text("content_id IS NOT NULL"),
    )


# このリビジョンのスキーマを解除します。検証DB以外ではデータ消失に注意してください。
def downgrade():
    op.drop_index(
        "uq_post_metric_day",
        table_name="metrics",
        postgresql_where=sa.text("content_id IS NOT NULL"),
        sqlite_where=sa.text("content_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_account_metric_day",
        table_name="metrics",
        postgresql_where=sa.text("content_id IS NULL"),
        sqlite_where=sa.text("content_id IS NULL"),
    )
    op.drop_index(op.f("ix_metrics_workspace_id"), table_name="metrics")
    op.drop_index(op.f("ix_metrics_social_account_id"), table_name="metrics")
    op.drop_index(op.f("ix_metrics_measured_on"), table_name="metrics")
    op.drop_index(op.f("ix_metrics_brand_id"), table_name="metrics")
    op.drop_table("metrics")
    op.drop_index(op.f("ix_content_versions_content_id"), table_name="content_versions")
    op.drop_table("content_versions")
    op.drop_index(
        "uq_active_content_schedule",
        table_name="content_schedules",
        postgresql_where=sa.text("status = 'SCHEDULED'"),
        sqlite_where=sa.text("status = 'SCHEDULED'"),
    )
    op.drop_index(op.f("ix_content_schedules_workspace_id"), table_name="content_schedules")
    op.drop_index(op.f("ix_content_schedules_scheduled_at"), table_name="content_schedules")
    op.drop_index(op.f("ix_content_schedules_content_id"), table_name="content_schedules")
    op.drop_table("content_schedules")
    op.drop_index(op.f("ix_content_approvals_content_id"), table_name="content_approvals")
    op.drop_table("content_approvals")
    op.drop_index(op.f("ix_agent_messages_workspace_id"), table_name="agent_messages")
    op.drop_index(op.f("ix_agent_messages_agent_id"), table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index(op.f("ix_social_accounts_workspace_id"), table_name="social_accounts")
    op.drop_index(op.f("ix_social_accounts_brand_id"), table_name="social_accounts")
    op.drop_table("social_accounts")
    op.drop_index(op.f("ix_monitoring_events_workspace_id"), table_name="monitoring_events")
    op.drop_index(op.f("ix_monitoring_events_brand_id"), table_name="monitoring_events")
    op.drop_table("monitoring_events")
    op.drop_index(op.f("ix_meeting_messages_meeting_id"), table_name="meeting_messages")
    op.drop_table("meeting_messages")
    op.drop_index(op.f("ix_contents_workspace_id"), table_name="contents")
    op.drop_index("ix_contents_workspace_brand", table_name="contents")
    op.drop_index(op.f("ix_contents_status"), table_name="contents")
    op.drop_index(op.f("ix_contents_brand_id"), table_name="contents")
    op.drop_table("contents")
    op.drop_index(op.f("ix_analysis_reports_workspace_id"), table_name="analysis_reports")
    op.drop_index(op.f("ix_analysis_reports_brand_id"), table_name="analysis_reports")
    op.drop_table("analysis_reports")
    op.drop_index(op.f("ix_agent_tasks_workspace_id"), table_name="agent_tasks")
    op.drop_index(op.f("ix_agent_tasks_agent_id"), table_name="agent_tasks")
    op.drop_table("agent_tasks")
    op.drop_index(op.f("ix_workspace_members_workspace_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_user_id"), table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index(op.f("ix_notifications_workspace_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_meetings_workspace_id"), table_name="meetings")
    op.drop_table("meetings")
    op.drop_index(op.f("ix_brands_workspace_id"), table_name="brands")
    op.drop_table("brands")
    op.drop_index(op.f("ix_audit_logs_workspace_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_agents_workspace_id"), table_name="agents")
    op.drop_table("agents")
    op.drop_index(op.f("ix_workspaces_owner_id"), table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
