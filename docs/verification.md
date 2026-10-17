# 実装・検証記録

## 実装結果

指定のバックエンド専用リポジトリに、FastAPIの業務APIを実装しました。`/api/v1`配下55操作＋`GET /health`の計56操作、40パスです。API一覧・起動手順・環境変数・DB操作は[README](../README.md)、20テーブルと設計判断は[アーキテクチャ](architecture.md)、画面との対応は[Frontend契約](frontend-contract.md)に記載しています。

認証、Workspace、Brand、SNS Accountメタデータ、Content CRUD、承認・差戻し、予約保存・変更・取消、Calendar、Agent、Mock Task、Analytics、Report、Monitoring、Notification、Meetingを実装しています。

## 実行した検証

| 検証 | 結果 |
|---|---|
| Python | 3.12.1で実行 |
| `pytest -q` / 一時SQLite | 24 passed / 2 skipped。行ロックの同時実行試験2件だけPostgreSQL専用 |
| `pytest -q` / PostgreSQL 16.2 | **26 passed**。スキップなし |
| `ruff check .` | 成功 |
| `ruff format --check .` | 成功 |
| Pythonコンパイル確認 | 成功 |
| Alembic upgrade / downgrade / 再upgrade | 一時PostgreSQLで成功 |
| Alembic check | PostgreSQLとSQLiteでモデル差分なし |
| PostgreSQL向けDDL生成 | 成功 |
| 明示Seed実行2回 | PostgreSQLで初回created=true、2回目created=false。テストで全テーブルの件数不変を確認 |
| OpenAPI / Swagger UI | TestClientでJSONと/docsの200を確認。Bearer認証とPydanticレスポンス定義あり |
| Health | TestClientからDBへのSELECT 1を確認 |
| Compose | YAMLの構文とdb/migrate/api定義を確認。実ビルド・実起動は未検証 |
| Frontend | 作業前後で変更なし |

PostgreSQLの検証には一時ディレクトリに配置した検証専用バイナリを使用し、終了時にDBプロセスを停止しています。この補助環境はアプリの依存関係には含めていません。通常起動にはComposeのPostgreSQL 16を使用します。ローカルにDockerコマンドがないため`docker compose up --build`は実行していません。

テスト依存のStarletteからhttpx版TestClientに関する非推奨警告が1件あります。テスト失敗はありません。将来のテストクライアント更新時に追従してください。

## テスト対象

- 登録、重複メール、ログイン、未認証・誤パスワード、改ざん/期限切れJWT、Tokenの非平文保存。
- Refreshのrotation、旧Refresh/Access失効、Logout後のRefresh/Access拒否。
- Workspace越境拒否、所属していても権限不足の場合の書き込み拒否、editorによる承認拒否。
- 別WorkspaceのAgent参照の拒否、本人以外の通知の参照・既読化拒否。
- 投稿CRUD、version競合、不正状態遷移、本文なしの承認依頼拒否、承認履歴、差戻し理由。
- 承認を飛ばすPATCHの拒否、承認後の編集による承認失効、予約の自動取消。
- 未承認予約の拒否、日時/タイムゾーン検証、媒体不一致拒否、予約変更・取消・再予約、Calendar。
- Analyticsの日付・SNSフィルタ、期間末Followers、反応率、0分母・欠損、日次推移、Sample投稿の8.4%検算。
- 全Sampleリソースの一覧/詳細取得、Mock Task完了、ページング上限、統一エラー、OpenAPI。
- Seed再実行と本番ガード。
- PostgreSQLでの同一Refresh Tokenの同時更新（成功1件・401が1件）。
- PostgreSQLでの同一投稿への同時予約（成功1件・409が1件）。

## Frontendの対応状況

参照したローカルFrontendはdevelop、commit `239e64106ac2e43477ce3e4be490d1c916dd07d4`です。依頼で指定されたリポジトリのチェックアウトであることをoriginで確認しました。リモートdevelopの最新コミットとの同期は行っていません。

画面が必要とする投稿、社員、アカウント、通知、会議、主要KPIをAPIから取得可能です。現状のFrontendはAPI通信を行わないため、ブラウザ画面をBackendへ接続するE2E試験は行っていません。`posts/contents`、camelCase/snake_case、hashtags、role、ID、接続状態、Analytics配列とオブジェクトの差は対応表に明示しています。カテゴリ・時間帯別チャートや前期比の固定値は専用API未実装です。

## 対象外・残る開発課題

今回の指定に従い、OpenAI API、ChatGPT自動問い合わせ、画像生成、SNS OAuth、実投稿・自動予約実行、実SNS監視・指標収集、本番決済、MCP Serverは実装していません。Mock予約はDB保存のみ、AI Taskは実推論せず同期的にMock完了します。

次の段階では、Dockerのある環境でComposeを実起動し、Frontendの認証・API通信・フィールド変換を接続してください。その後、委任認証、実SNS Adapter、永続Queue/Worker、冪等性、媒体ルール、メディア保存、週/月集計・期間比較、運用監視・バックアップを追加します。CIにはPostgreSQL 16でのMigration・モデル差分・テスト・Ruff検証を定義していますが、GitHub上の実行結果は今回確認していません。

MCP連携の準備として、HTTPに依存しない認可付きService、AI/SNS/通知Protocol、分析出典と定義版を用意しました。MCP公開時にはユーザー委任認証・scope・読み取り監査・ツール契約試験が必要です。ChatGPTの月額契約とAPI課金を混同せず、Scheduled TasksとMCPによる完全自動運用も保証していません。
