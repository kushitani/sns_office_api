# AI SNS OFFICE Backend API

SNS運用支援SaaSの業務API。Python 3.12+ / FastAPI / PostgreSQL / SQLAlchemy 2 / Alembic / Pydantic 2 / uvを使用するモジュラーモノリスです。AI生成・SNSへの実投稿・決済は含みません。

## 起動

Docker EngineとComposeが必要です。以下はこのバックエンドリポジトリのルートで実行します。

```sh
cp .env.example .env
```

`.env`の`JWT_SECRET`を32文字以上のランダムな値に変更してください。生成例:

```sh
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
docker compose up --build
```

PostgreSQLの正常起動後、`migrate`サービスがマイグレーションを適用し、成功した場合だけAPIが起動します。Seedは自動投入しません。

```sh
docker compose exec api /app/.venv/bin/python -m sns_office.seed
```

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- DBを含むHealth Check: `GET /health`（障害時503）

開発用サンプル: `demo@example.com` / `DemoPassword123!`。環境変数で変更可能です。Seedはdevelopment/test環境でのみ明示実行でき、同じDBへの再実行で重複を作成しません。既存の非デモユーザーとメールが重なる場合は停止します。Seedは一括トランザクションです。サンプルには6役の社員、8投稿、2予約、14日×5媒体の指標、分析レポート、監視イベント、通知、会議、Mock Taskを含みます。

## ローカル開発

Python 3.12+、uv、起動済みのPostgreSQLを用意します。

```sh
uv sync --frozen
cp .env.example .env
# .env の DATABASE_URL / JWT_SECRET を設定
uv run alembic upgrade head
uv run python -m sns_office.seed
uv run uvicorn sns_office.main:app --reload
```

```sh
uv run alembic revision --autogenerate -m describe_change
uv run alembic upgrade head
uv run alembic check
```

`alembic downgrade base`は全業務テーブルを削除するため、破棄できる検証DB以外では実行しないでください。起動時の`create_all`は行いません。

## 環境変数

| 変数 | 用途 / 初期値 |
|---|---|
| `APP_ENV` | development / test / production。初期値development |
| `DATABASE_URL` | `postgresql+psycopg://user:password@host:5432/database` |
| `JWT_SECRET` | 必須・32文字以上。productionでテンプレート値を拒否 |
| `CORS_ORIGINS` | JSON配列。初期値`["http://localhost:5173"]` |
| `ACCESS_TOKEN_MINUTES` | 初期値15、最大60 |
| `REFRESH_TOKEN_DAYS` | 初期値30、最大90 |
| `DEMO_EMAIL` / `DEMO_PASSWORD` | 明示Seed時だけ使用 |
| `POSTGRES_PASSWORD` | Composeの開発用DBパスワード。初期値sns_office |
| `TEST_DATABASE_URL` | テスト用PostgreSQL。未設定なら一時SQLiteを使用 |

`.env`をGitに含めないでください。Compose内のDB接続先は`db`、ホストからの接続先は`localhost`です。Composeは開発用で、APIとDBのポート公開先は127.0.0.1です。本番ではTLS、秘密管理、DBバックアップ、入口での認証レート制限を整備してください。

## アーキテクチャとディレクトリ

```text
Client → FastAPI Router → Application Service → Repository → PostgreSQL
                                ↓
                        Integration Protocol → Adapter

src/sns_office/
  main.py                     アプリ、CORS、統一エラー、Health
  api/dependencies.py         認証、トランザクション、Service注入
  api/v1/routers/             入出力定義とServiceへの委譲
  core/                      設定、Argon2、JWT、例外
  db/                        Sessionと宣言ベース
  models/entities.py         20テーブルとEnum
  schemas/api.py             入力・出力・ページング・OpenAPI契約
  repositories/store.py      SQLAlchemyによるDB操作
  services/                  認証、業務フロー、決定論的集計
  integrations/contracts.py  AI/SNS/通知ProtocolとMock AI
  seed.py                    明示的な開発用Seed
  sample_data.json            既存Frontendから抽出したサンプル
alembic/versions/             固定された初期スキーマ
tests/unit/                  KPI境界値
tests/integration/           API・認可・DB・Seed
docs/                        API対応表、設計判断、検証結果
```

DBセッションはAPI操作単位でcommit/rollbackします。エンドポイントはレスポンス送信前にcommitを完了します。Content/Brandは版番号による楽観ロック、承認・予約は行ロックと有効予約の部分一意インデックスを併用します。SQLiteはローカルテスト用で、本番・開発の既定DBはPostgreSQLです。

## 認証と認可

パスワードはArgon2でハッシュ化します。Access TokenはHS256 JWT（issuer/audience/type/期限を検証）、Refresh Tokenはランダムなopaque tokenです。DBにはSHA-256ハッシュだけを保存します。Refreshごとに旧トークンを失効し、新しいペアを発行します。LogoutとRefreshによる失効は、そのセッションのAccess Tokenにも即時反映されます。他端末のログインセッションは維持します。

```sh
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"DemoPassword123!"}'
```

以降は`Authorization: Bearer <access_token>`を付けます。Refreshは`{"refresh_token":"..."}`をPOSTします。Logoutは同じJSONとAccess Tokenが必要です。失効後は新しいペアで再認証してください。ブラウザの永続ストレージへのトークン保存はFrontend接続時に別途設計します。

Workspace作成者はownerとなり、6役のAgentがIDLEで作られます。未所属Workspaceは403、他ユーザー宛通知は404です。リストは所属Workspace内に絞ります。

| 操作 | owner/admin | editor | approver | viewer |
|---|---|---|---|---|
| 所属Workspace内の参照 | 可 | 可 | 可 | 可 |
| ブランド・投稿編集 / 承認依頼 / 予約 / Task / Report作成 | 可 | 可 | — | — |
| 承認・差戻し | 可 | — | 可 | — |
| Workspace設定 / SNSメタデータ管理 / ブランド削除 | 可 | — | — | — |
| 自分の通知の既読化 | 可 | 可 | 可 | 可 |

メンバー招待・役割変更APIは今回の対象外です。権限は`workspace_members`で保持し、Service層で強制します。

## API一覧

共通prefixは`/api/v1`です。詳細な入力・出力は自動生成OpenAPIで確認できます。

| リソース | API |
|---|---|
| Auth | POST `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; GET `/auth/me` |
| Workspace | GET/POST `/workspaces`; GET/PATCH `/workspaces/{id}` |
| Brand | GET/POST `/brands`; GET/PATCH/DELETE `/brands/{id}` |
| SNS Account | GET/POST `/social-accounts`; GET/PATCH/DELETE `/social-accounts/{id}` |
| Content | GET/POST `/contents`; GET/PATCH/DELETE `/contents/{id}` |
| Approval | POST `/contents/{id}/submit-review`, `/approve`, `/reject`; GET `/contents/{id}/approvals` |
| Schedule | GET/POST `/schedules`; GET/PATCH/DELETE `/schedules/{id}` |
| Calendar | GET `/calendar?brand_id=...&start_date=...&end_date=...&platform=X` |
| Agent | GET `/agents`, `/agents/{id}`, `/agents/{id}/tasks`, `/agents/{id}/messages` |
| Task | GET/POST `/agent-tasks`; GET `/agent-tasks/{id}` |
| Analytics | GET `/analytics/overview`, `/platforms`, `/posts`, `/trends` |
| Report | GET/POST `/reports`; GET `/reports/{id}` |
| Monitoring | GET `/monitoring/events`, `/monitoring/alerts` |
| Notification | GET `/notifications`, `/notifications/{id}`; PATCH `/notifications/{id}/read` |
| Meeting | GET `/meetings`, `/meetings/{id}` |

リストは`{items,total,limit,offset}`形式、limitは1〜100、offsetは0以上です。Contentは`brand_id/platform/status`、Brand/Agent/Task/Schedule/Meeting/Notificationは`workspace_id`、Account/Report/Monitoringは`brand_id`等で絞れます。CalendarとAnalyticsは`brand_id`が必須です。Platform表記は`X / Instagram / Threads / TikTok / YouTube`です。

## 投稿・承認・予約

新規投稿はIDEA/PLANNED/DRAFTで作成できます。手動PATCHはIDEA→PLANNED/DRAFT、PLANNED→DRAFT、FAILED→DRAFTに対応します。GENERATING/POSTING/POSTEDは予約実行等の将来処理用のEnumで、利用者によるPATCHでは設定できません。

Content/BrandのPATCHと承認操作では、取得した`version`をJSONで送ります。競合は409です。

```json
{"version": 1, "body": "更新する本文"}
```

`submit-review`はDRAFT→REVIEW（本文必須）、`approve`はREVIEW→APPROVED、`reject`はREVIEW→DRAFT（reason必須）です。これらも`{"version":2}`等で操作します。承認履歴に対象版、本文ハッシュ、操作者、理由、時刻を保存します。編集・状態変更で版番号が増えます。承認後の編集は承認を失効してREVIEWに戻し、有効予約をCANCELLEDにします。

```json
{
  "content_id": "<approved-content-id>",
  "social_account_id": "<matching-account-id>",
  "scheduled_at": "2030-01-15T18:00:00+09:00",
  "timezone": "Asia/Tokyo"
}
```

予約は現在版が承認済み、同じBrandとPlatformのMOCKアカウント、未来のoffset付き日時が必要です。日時のoffsetが時点を決め、timezoneは表示用IANA名として保持します。DBにはUTCを保存します。1投稿につき有効予約は1件です。変更は日時とtimezoneのみ、DELETEは履歴を残す取消です。取消後はAPPROVEDへ戻ります。予約時刻になっても実投稿はしません。

Calendarの日付範囲はWorkspaceのタイムゾーンで両端の日付を含みます。順序不正と366日を超える差を拒否します。Brand/Account/ContentのDELETEは依存データがある場合409で拒否し、履歴を保護します。

## Analyticsとサンプルの扱い

`brand_id`、`platform`、`start_date`、`end_date`に対応し、日付はWorkspaceローカル日付の包含範囲です。両端指定時は順序と最大366日の差を検証します。未指定の場合は保存済み範囲を集計します。

- Account日次行は`content_id=null`。Overview/Platforms/Trendsで使用します。
- Post日次行は`content_id`あり。Postsで使用し、Account行と足し合わせません。
- Impressions/Reach/Likes/Comments/Shares/Savesは日次増分の合計です。Reachは期間内ユニーク人数ではありません。
- Followersは期間内の各Accountの最新値の合計で、日数分を足しません。
- Engagement Rateは`(likes+comments+shares+saves)/impressions*100`。分母0の場合nullです。
- Postsの順序はimpressions降順、同率はcontent_id昇順です。Trendsは日付昇順です。
- 欠損日のゼロ埋めはしません。出典ID、更新時刻、定義版、タイムゾーン、Sample警告をmetaに含めます。

既存画面の固定KPIをそのまま返す方式ではなく、DBデータからPythonで計算します。AI社員のTaskはMOCKで同期完了し、推論は実行しません。SNS接続状態はMOCK/DISCONNECTEDのみ登録可能で、CONNECTEDを自己申告できません。

## テストと検証

```sh
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

既定は一時SQLiteで、各テストがAlembicを適用し、外部キーを有効化したDBでAPIを検証します。PostgreSQLでの検証には**破棄してよい専用DB**を指定します。テスト終了時にマイグレーションを全解除します。

```sh
TEST_DATABASE_URL=postgresql+psycopg://test:test@localhost:5432/sns_office_test uv run pytest -q
```

GitHub ActionsではPostgreSQL 16を起動し、Migration、モデル差分、全テスト、downgrade/upgrade、Ruffを確認します。ローカルで実行できた範囲と残る制約は[検証記録](docs/verification.md)を参照してください。

## Frontendと今後の拡張

Frontendは変更していません。既存developチェックアウトの型、Store、Mock Data、Routingを確認し、[対応表](docs/frontend-contract.md)に整理しています。現状のFrontendはStore内のMockを使うため、URLを設定するだけでは接続されません。認証・fetch・ページング・フィールド変換を追加する接続作業が別途必要です。

SNS/AI/通知はProtocolを差し替える構成です。MCP Serverは未実装ですが、HTTPに依存しないServiceの認可と業務処理を再利用できます。MCP追加時も認証済みUserを必ず渡し、read scopeと監査を追加してください。ChatGPT月額契約とOpenAI API課金は別であり、任意API実行やScheduled Tasks+MCPによる完全自動運用は前提にしていません。

外部連携、MCP、非同期Worker、OAuth/OIDC、MFA、メンバー管理、入力NGワード判定、媒体制約、メディア保管、週月集計、期間比較、請求、本番監視/バックアップは今後の開発対象です。設計書との差分は[設計判断](docs/architecture.md)を参照してください。
