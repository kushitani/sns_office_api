# 概要: パスワードのハッシュ化、UTC時刻、JWTとRefresh Tokenに関する共通処理を提供します。
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from sns_office.core.config import get_settings
from sns_office.core.exceptions import DomainError

password_hash = PasswordHash.recommended()


# 保存・有効期限の判定に使う、タイムゾーン付きUTC現在時刻を返します。
def utcnow():
    return datetime.now(timezone.utc)


# SQLite等でタイムゾーンが外れた日時をUTCとして補い、期限比較を可能にします。
def aware(value: datetime):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


# DB照合用のハッシュを作ります。Refresh Tokenの平文は保存しません。
def token_digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


# 推測が困難なランダム値をRefresh Tokenとして生成します。
def new_refresh():
    return secrets.token_urlsafe(48)


# 利用者とセッションを紐付け、有効期限・発行元・対象APIを含むJWTを発行します。
def access_token(user_id: str, session_id: str):
    settings = get_settings()
    return jwt.encode(
        {
            "sub": user_id,
            "sid": session_id,
            "type": "access",
            "iat": utcnow(),
            "exp": utcnow() + timedelta(minutes=settings.access_token_minutes),
            "iss": "sns-office",
            "aud": "sns-office-api",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


# 署名と必須claimを検証し、不正・期限切れの場合は統一された認証エラーにします。
def decode_access(token: str):
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer="sns-office",
            audience="sns-office-api",
            options={"require": ["sub", "sid", "type", "exp", "iat"]},
        )
        if claims["type"] != "access":
            raise ValueError()
        return claims
    except (jwt.PyJWTError, ValueError):
        raise DomainError(401, "UNAUTHENTICATED", "Invalid or expired credentials") from None
