# 設計判断と対象範囲

## 参照と優先順位

要件定義書v0.1、基本設計書v0.1、既存Frontend developを確認しました。今回の開発依頼で明示されたAPI名・対象範囲を採用し、基本設計書のCore/AI境界、Workspace分離、RBAC、UTC保存、承認版管理、承認失効を取り込みました。

| 設計ID / 領域 | 今回の対応 |
|---|---|
| ARC-002/003, OV-008 | 単一FastAPIアプリ＋PostgreSQL。Router→Service→Repository。デプロイを分割する必要が生じた段階で境界を分離 |
| NFR-001/002, DB-002 | Argon2とJWT/Refresh Token。ユーザーとWorkspace所属・役割を保持。OIDC/MFA/招待管理は将来 |
| FUN-003/004, STM-001〜005/009 | 状態Enum、専用承認操作、対象version/hash/actor、編集時の承認失効と予約取消 |
| API-POST-003, API-BRD-002 | Content/Brandの入力versionを必須化。SQLAlchemyのversion条件UPDATEで競合拒否。If-Match形式は未対応 |
| DB-001〜015 | 今回指定の20テーブルへ整理。posts→contents、memberships→workspace_members、approvals→content_approvals |
| FUN-007, OV-007 | Pythonで決定論的な日次集計。出典・定義・欠損警告を返す |
| NFR-005, FUN-010 | 変更操作をaudit_logsへ記録。ユーザー・対象・時刻・request_idを保存。本文・パスワード・tokenは監査詳細へ含めない |
| ARC-006, MCP-001〜017 | MCPサーバは今回対象外。Serviceを再利用できる構成、Analyticsの出典メタデータ、外部連携Protocolを準備 |
| JOB/SNS/API-SNS/API-JOB | 実投稿・実収集・Worker/OAuth/再試行/実連携は今回対象外。予約レコードの保存・変更・取消のみ |

## データ構成（20テーブル）

| 分類 | テーブル |
|---|---|
| 認証 | users, refresh_tokens |
| 組織 | workspaces, workspace_members |
| ブランド・SNS | brands, social_accounts |
| 投稿 | contents, content_versions, content_approvals, content_schedules |
| 社員 | agents, agent_tasks, agent_messages |
| 分析 | metrics, analysis_reports |
| 運用 | monitoring_events, notifications |
| 会議 | meetings, meeting_messages |
| 監査 | audit_logs |

IDはUUID文字列、時刻はtimezone付きUTCです。APIから作る業務レコードにはWorkspaceを明示し、Brand/Content/Agent等の参照先との整合性をServiceで検証します。FK・Unique・Enum CHECK・値域CHECK・検索IndexをDBに定義します。Workspace所属は`workspace_id/user_id`一意、Agent役割はWorkspaceごとに一意、VersionはContentごとに一意、有効予約はContentごとに部分一意です。

承認・VersionはContentの子として外部キー削除連鎖します。Schedule・Metric等の業務参照があるBrand/Account/Contentは削除を拒否し、履歴を保護します。監査ログには更新・削除APIを提供しません。本番の改ざん耐性にはDB権限の分離や外部ログ保管を追加してください。

## 承認版と排他制御

Contentのversionは本文と状態変更の双方で増加します。Reviewを承認した履歴は確認対象のReview版を指し、approved_versionは承認操作後の版を指します。双方の本文hashは一致します。Scheduleは承認済み版を保持します。予約後の内容変更はReviewへ戻し、承認マーカーをクリアし、ScheduleをCANCELLEDにします。

承認・編集・予約はContentを行ロックします。予約変更・取消もContent→Scheduleの順でロックし、編集と予約操作のロック順を揃えます。SQLAlchemyのversion条件とDBの部分一意制約で競合を拒否します。SQLiteでは行ロックがないため、同時実行の判断にはPostgreSQLテストを使用します。

Refresh Tokenはハッシュで検索し、行ロックして失効させてから新しいペアを発行します。各Access Tokenにはsession IDがあり、APIごとにDBの失効状態を確認します。すべての業務変更と監査レコードを同じトランザクションで確定します。

## 拡張境界と保留事項

AIProvider / SNSProvider / NotificationProviderはProtocolです。MockAIProviderだけを実装し、機能を本番AIと誤認しない出力を返します。AgentTaskは今回同期的にMock完了するため、永続Queueと長時間Workerは未実装です。

基本設計書より今回の対象範囲を小さくしています。content_plans、brand_guidelines独立テーブル、media_assets、metric_aggregates、jobs/job_runs、mcp_clientsは作らず、BrandのJSON項目や日次Metric等で今回の要件を満たします。mediaはメタデータ配列のみで、アップロード機能はありません。

API-POST-002のIdempotency-Key、期間比較、週/月粒度、カテゴリ・時間帯分析、リアルタイム配信、NGワード検査、媒体文字数ルール、監視の自動検知、通知の自動配信は将来追加です。今回のcreate操作には再送による重複作成防止を保証しません。有効予約の重複はDB制約で拒否します。

MCPではBusinessService/AnalyticsServiceを利用し、Userを必須化して既存の認可を通します。読み取りスコープ、委任認証、MCP用監査、応答サイズ制御、ツール契約テストが必要です。将来の書き込みは権限・承認・確認・冪等性を追加した後に公開します。ChatGPT契約やScheduled Tasksの有無によってCoreの動作を変えません。
