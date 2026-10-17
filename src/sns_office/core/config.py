# 概要: 環境変数と.envから設定を読み込み、秘密鍵や有効期限の値域を検証します。
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 環境変数を型付き設定へ変換し、不正な値は起動時に検出します。
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://sns_office:sns_office@localhost:5432/sns_office"
    jwt_secret: str = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173"]
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    demo_email: str = "demo@example.com"
    demo_password: str = "DemoPassword123!"

    # 本番環境でテンプレートの秘密鍵を使い続ける設定ミスを拒否します。
    @model_validator(mode="after")
    def production_secret(self):
        if self.app_env == "production" and self.jwt_secret.startswith("replace-"):
            raise ValueError("Production requires a random JWT_SECRET")
        return self


# 検証済みの設定をプロセス内で共有し、繰り返しの読み込みを避けます。
@lru_cache
def get_settings():
    return Settings()
