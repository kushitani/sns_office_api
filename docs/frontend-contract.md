# Frontend / API / DB 対応

確認対象は隣接する`sns_office_front`の`develop`チェックアウトです。originは依頼で指定された`kushitani/sns_office_front`です。リモートの最新状態との同期は行っていません。`src/main.tsx`、`src/types/index.ts`、`src/data/*.ts`、`src/state/Store.tsx`、各画面を参照し、Frontendは編集していません。

現在のStoreはReact stateとローカルMockで動作し、HTTP通信層がありません。以下はAPIから画面用データへ変換するための契約で、Frontend側の接続実装は今回の対象外です。APIはsnake_case、日時はISO 8601、IDはUUID、一覧は`items/total/limit/offset`です。

| Frontend Data / 画面 | API（prefix `/api/v1`） | Database | 変換・差分 |
|---|---|---|---|
| `agents` / Office・Employees | `/agents`, `/agents/{id}/tasks`, `/messages` | agents, agent_tasks, agent_messages | roleはAPIで大文字Enum、画面でManager等へ変換。APIは6役、Mockは5役。COMPLETEDはTask状態として管理し、AgentはIDLEへ戻る |
| `posts` / Posts・Editor | `/contents`, `/{id}/submit-review`, `/approve`, `/reject` | contents, content_versions, content_approvals | `posts`というFrontend名に対しAPI・DBは`contents`。hashtagsは画面の文字列⇔APIの文字列配列。`scheduledAt`←`scheduled_at`。APIのauthor/historyは表示用派生値 |
| CalendarのPost情報 | `/calendar?brand_id&start_date&end_date&platform` | content_schedules + contents | schedule IDとcontent_idを区別。title/platform/purpose/担当Agentを返す。日時変更は`PATCH /schedules/{id}`へ |
| `socialAccounts` / Accounts | `/social-accounts` | social_accounts | `connected` booleanではなく`connection_status`。MOCKは本番接続済みとして表示しない。followers/name/platform対応。`lastSync`←`last_sync`、実同期なしなのでnull |
| `metrics` / Dashboard | `/analytics/overview?brand_id` | metrics（Account日次） | 表示用文字列タプルから数値オブジェクトへ。百分率のengagement_rateは5.24等。画面が必要なら表示フォーマットを付ける。前期比固定文字列は返さない |
| `trend` | `/analytics/trends?brand_id` | metrics | 数値配列から日付とKPIを持つitemsへ。欠測日は存在しない。曜日/時刻境界はWorkspace TZ |
| `performance` | `/analytics/platforms?brand_id` | metrics | 媒体単位の実数集計。Mockの84等の見た目用スコアは返さない |
| 投稿別実績 | `/analytics/posts?brand_id` | metrics（Content日次） | `performance`表示はengagement_rateから生成。データがない投稿に架空の実績を付けない |
| `categories` / `hours` | 今回は専用集計APIなし | 将来拡張 | Mockのカテゴリ別・時間帯別棒グラフは未接続。保存済みContentとMetricから定義を決めて実装する |
| `report` / AnalysisReport | `/reports`, `/reports/{id}` | analysis_reports | タプル配列をsummary/good_points/problems/findings/hypotheses/recommendations/next_actionsへ。sample/manualをsourceで識別 |
| `notifications` / Notice | `/notifications`, `/{id}/read` | notifications | `detail`←`message`、`read`←`is_read`。title/type/link対応。ユーザー本人宛だけを返す |
| `monitoring` | `/monitoring/events`, `/monitoring/alerts` | monitoring_events | タプルからtype/title/message/link/severity/sourceを持つオブジェクトへ。alertsはWARNING/ERROR/CRITICAL |
| `meeting` | `/meetings`, `/meetings/{id}` | meetings, meeting_messages | 発言の`agent`←`agent_id`、`text`←`message`、sequence順。参加者・決定・アクションも保持 |
| `brand` / Settings | `/brands`, `/workspaces` | brands, workspaces | `profile`←description、`target`←target_audience、`tone`←brand_tone、`ngWords`⇔ng_words配列、`goal`⇔sns_goals構造。`ai/notifications`はbrand_guidelinesに保存可能な設定値で、AI実行ONを意味しない |

## 状態とID

Frontend PostStatusは`IDEA/DRAFT/REVIEW/APPROVED/SCHEDULED/POSTED/FAILED`です。APIはこれに`PLANNED/GENERATING/POSTING`を加えたEnumです。接続時には未対応状態の表示を追加する必要があります。今回は実生成・実投稿へ進むAPIを公開していません。

`post-1`、`alex`等のMock IDとDB IDは一致しません。Seedの投稿は固定UUID、AgentはWorkspaceに固有のUUIDです。通知リンクはSeed時にDB投稿IDへ置換します。API取得後のIDを画面遷移と更新に使用してください。

Seedは既存の投稿タイトル・本文形式・通知・会議発言・社員名を参照しています。予約日付は過去の固定日付を流用せず、Seed実行時から未来へずらします。Agentは過去のMock作業を実行中と誤表示しないためIDLEから始め、過去履歴を残します。指標は検算できる日次サンプルから集計するため、Frontendの固定KPIと一致しません。

## 接続手順

1. `/auth/login`でトークンペアを取得し、`/auth/me`と`/workspaces`で利用者・Workspaceを特定する。
2. `/brands`で対象Brandを選択し、必要な各APIへbrand_id/workspace_idを送る。
3. 一覧のitemsと上表の変換結果をStoreに格納する。limit/offsetで追加ページを読む。
4. 編集前に最新versionを読み、PATCHまたは承認操作へ送る。409時は再取得し、編集を確認する。
5. 承認済みContentと対応するMOCK AccountでScheduleを作成し、Calendarを再取得する。
6. 401時はRefreshを1回だけ行い、古いトークンペアを置換する。失敗したらログインに戻る。

開発時の許可originは`http://localhost:5173`です。変更時は`CORS_ORIGINS`をJSON配列で設定してください。APIのベースURLは`http://localhost:8000/api/v1`です。Frontendに設定変数や認証画面を追加する作業は含めていません。
