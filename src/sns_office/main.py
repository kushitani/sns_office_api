# 概要: FastAPIアプリの組み立て、共通エラー応答、CORS、DBヘルスチェックを定義します。
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException

from sns_office.api.v1.routers import auth, resources
from sns_office.core.config import get_settings
from sns_office.core.exceptions import DomainError
from sns_office.db.session import engine
from sns_office.schemas.api import ErrorResponse

logger = logging.getLogger(__name__)
app = FastAPI(
    title="AI SNS OFFICE Backend API",
    version="0.1.0",
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 422, 500)},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],
)


# リクエストごとの追跡IDを発行し、応答にも同じIDと共通ヘッダーを付けます。
@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# 業務エラー・検証エラーで共通のJSON形式を組み立てます。
def error(request, status, code, message, details=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": getattr(request.state, "request_id", None),
            }
        },
        headers={"WWW-Authenticate": "Bearer"} if status == 401 else None,
    )


# Serviceからの業務例外を、指定されたHTTP状態とエラーコードに変換します。
@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return error(request, exc.status, exc.code, exc.message, exc.details)


# 不正な入力箇所だけを返し、入力値そのものや秘密情報の露出を避けます。
@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    fields = [
        {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
        for item in exc.errors()
    ]
    return error(request, 422, "VALIDATION_ERROR", "Request validation failed", {"fields": fields})


# 一意制約・外部キー等の競合を409に変換し、SQLの詳細を外部へ返しません。
@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return error(request, 409, "RESOURCE_CONFLICT", "Resource conflicts with existing data")


# 楽観ロックで検知した同時更新を409として返し、再取得を促します。
@app.exception_handler(StaleDataError)
async def stale_error(request, exc):
    return error(request, 409, "VERSION_CONFLICT", "Resource has changed; reload before editing")


# 未定義URL等のHTTP例外も共通エラー形式で返します。
@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error(request, exc.status_code, "HTTP_ERROR", str(exc.detail))


# 予期しない障害では追跡IDと例外型だけを記録し、内部情報を応答から隠します。
@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    # No exception values, SQL statements, credentials, or request bodies in logs.
    logger.error(
        "Unhandled API error type=%s request_id=%s",
        type(exc).__name__,
        getattr(request.state, "request_id", None),
    )
    return error(request, 500, "INTERNAL_ERROR", "An internal error occurred")


# DBへ実際に問い合わせ、接続できない場合はサービス利用不可を返します。
@app.get("/health", tags=["Health"])
def health():
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise DomainError(503, "DATABASE_UNAVAILABLE", "Database is unavailable") from None
    return {"status": "ok", "database": "ok", "external_integrations": "disabled"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
