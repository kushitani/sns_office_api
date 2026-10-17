# 概要: 登録・ログイン・トークン更新・失効を扱い、資格情報を安全に保存します。
from datetime import timedelta

from sns_office.core.config import get_settings
from sns_office.core.exceptions import DomainError
from sns_office.core.security import (
    access_token,
    aware,
    decode_access,
    new_refresh,
    password_hash,
    token_digest,
    utcnow,
)
from sns_office.models.entities import AuditLog, RefreshToken, User
from sns_office.repositories.store import Repository


# 認証とセッションのライフサイクルをHTTP処理から分離します。
class AuthService:
    # この処理で使用する依存オブジェクトやエラー情報を保持します。
    def __init__(self, db):
        self.repo = Repository(db)
        self.db = db

    # 操作主体・対象・時刻を追跡できる監査レコードを、業務変更と同じDBへ記録します。
    def audit(self, user, action, resource_id):
        self.repo.add(
            AuditLog, actor_id=user.id, action=action, resource_type="auth", resource_id=resource_id
        )

    # 新しいRefresh Tokenのハッシュを保存し、対応するAccess Tokenとともに返します。
    def issue(self, user):
        settings = get_settings()
        raw = new_refresh()
        session = self.repo.add(
            RefreshToken,
            user_id=user.id,
            token_hash=token_digest(raw),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
        return {
            "access_token": access_token(user.id, session.id),
            "refresh_token": raw,
            "token_type": "bearer",
            "expires_in": settings.access_token_minutes * 60,
        }

    # 重複メールを拒否し、パスワードをハッシュ化して利用者と初回セッションを作成します。
    def register(self, data):
        email = str(data.email).lower()
        if self.repo.one(User, User.email == email):
            raise DomainError(409, "EMAIL_EXISTS", "Email is already registered")
        user = self.repo.add(
            User, email=email, name=data.name, password_hash=password_hash.hash(data.password)
        )
        self.audit(user, "auth.register", user.id)
        return self.issue(user)

    # 認証情報を照合し、成功した利用者へ新しいセッションを発行します。
    def login(self, data):
        user = self.repo.one(User, User.email == str(data.email).lower())
        # Same costly verification path when the email is unknown.
        stored = user.password_hash if user else DUMMY_HASH
        valid = password_hash.verify(data.password, stored)
        if user is None or not valid:
            raise DomainError(401, "UNAUTHENTICATED", "Invalid or expired credentials")
        self.audit(user, "auth.login", user.id)
        return self.issue(user)

    # 更新対象のトークンを行ロックし、二重更新と期限切れ・失効済みの利用を防ぎます。
    def refresh_row(self, raw):
        row = self.repo.one(RefreshToken, RefreshToken.token_hash == token_digest(raw), lock=True)
        if row is None or row.revoked_at or aware(row.expires_at) <= utcnow():
            raise DomainError(401, "UNAUTHENTICATED", "Invalid or expired credentials")
        return row

    # 旧Refresh Tokenを失効させてから新しいトークンペアへ交換します。
    def refresh(self, raw):
        row = self.refresh_row(raw)
        row.revoked_at = utcnow()
        user = self.repo.get(User, row.user_id)
        self.audit(user, "auth.refresh", row.id)
        return self.issue(user)

    # 本人の対象セッションを失効させ、対応するAccess Tokenも使用できなくします。
    def logout(self, raw, user):
        row = self.repo.one(RefreshToken, RefreshToken.token_hash == token_digest(raw), lock=True)
        if row is None or row.user_id != user.id:
            raise DomainError(401, "UNAUTHENTICATED", "Invalid or expired credentials")
        row.revoked_at = utcnow()
        self.audit(user, "auth.logout", row.id)

    # JWTだけでなくDBのセッション状態も調べ、Logout後のアクセスを拒否します。
    def authenticate(self, token):
        claims = decode_access(token)
        session = self.repo.one(
            RefreshToken, RefreshToken.id == claims["sid"], RefreshToken.user_id == claims["sub"]
        )
        if session is None or session.revoked_at or aware(session.expires_at) <= utcnow():
            raise DomainError(401, "UNAUTHENTICATED", "Invalid or expired credentials")
        user = self.repo.one(User, User.id == claims["sub"])
        if user is None:
            raise DomainError(401, "UNAUTHENTICATED", "Invalid or expired credentials")
        return user


DUMMY_HASH = password_hash.hash("unused-timing-equalization-password")
