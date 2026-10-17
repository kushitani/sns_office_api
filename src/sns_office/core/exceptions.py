# 概要: 業務上のエラーをHTTP状態・識別コード・説明とともに伝える例外を定義します。
# HTTP層へ業務エラーの種類と説明を伝え、統一応答へ変換できるようにします。
class DomainError(Exception):
    # この処理で使用する依存オブジェクトやエラー情報を保持します。
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
