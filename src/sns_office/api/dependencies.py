# 概要: リクエストごとにDBセッションと認証ユーザーを解決し、業務Serviceへ渡します。
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from sns_office.core.exceptions import DomainError
from sns_office.db.session import get_db
from sns_office.services.auth import AuthService
from sns_office.services.business import BusinessService

DB = Annotated[Session, Depends(get_db, scope="function")]
bearer = HTTPBearer(auto_error=False)


# Bearer TokenとDBのセッション失効状態から、現在の利用者を特定します。
def current_user(
    db: DB,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer),
    ],
):
    if credentials is None:
        raise DomainError(401, "UNAUTHENTICATED", "Authentication is required")
    return AuthService(db).authenticate(credentials.credentials)


# 認証済み利用者と追跡用request_idを付けたServiceを生成します。
def business(request: Request, db: DB, user=Depends(current_user)):
    return BusinessService(db, user, request.state.request_id)


Service = Annotated[BusinessService, Depends(business)]
