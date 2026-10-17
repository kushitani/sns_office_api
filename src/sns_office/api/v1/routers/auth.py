# 概要: 認証APIの入出力を定義し、登録・ログイン・トークン操作をAuthServiceへ委譲します。
from fastapi import APIRouter, Depends, Response

from sns_office.api.dependencies import DB, current_user
from sns_office.schemas.api import Login, Refresh, Register, TokenOut, UserOut
from sns_office.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


# 認証処理をAuthServiceへ委譲し、トークンを含む応答のキャッシュを防ぎます。
@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: Register, db: DB, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return AuthService(db).register(data)


# 認証処理をAuthServiceへ委譲し、トークンを含む応答のキャッシュを防ぎます。
@router.post("/login", response_model=TokenOut)
def login(data: Login, db: DB, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return AuthService(db).login(data)


# 認証処理をAuthServiceへ委譲し、トークンを含む応答のキャッシュを防ぎます。
@router.post("/refresh", response_model=TokenOut)
def refresh(data: Refresh, db: DB, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return AuthService(db).refresh(data.refresh_token)


# Logoutの入力と認証ユーザーをServiceへ渡し、対象セッションの失効を依頼します。
@router.post("/logout", status_code=204)
def logout(data: Refresh, db: DB, user=Depends(current_user)):
    AuthService(db).logout(data.refresh_token, user)


# 認証済み利用者の公開プロフィールだけを返します。
@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user
