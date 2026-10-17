# 概要: 将来のAI・SNS・通知連携の契約と、推論を行わないMock AI実装を定義します。
from typing import Protocol


# AIProviderの外部連携契約またはMock実装です。実サービスへの接続は今回行いません。
class AIProvider(Protocol):
    mode: str

    # 実推論を行わず、Mockであることが明確なタスク結果を返します。
    def execute(self, task_type: str, data: dict) -> dict: ...


# SNSProviderの外部連携契約またはMock実装です。実サービスへの接続は今回行いません。
class SNSProvider(Protocol):
    # 将来のSNS投稿Adapterが実装する契約です。冪等キーを受け取り、重複投稿を防ぎます。
    def publish(self, account_id: str, content: dict, idempotency_key: str) -> dict: ...

    # 将来のSNS Adapterがアカウント実績を取得するための契約です。
    def collect_metrics(self, account_id: str) -> list[dict]: ...


# NotificationProviderの外部連携契約またはMock実装です。実サービスへの接続は今回行いません。
class NotificationProvider(Protocol):
    # 将来の通知Adapterが宛先へ通知を配信するための契約です。
    def deliver(self, user_id: str, message: dict) -> None: ...


# MockAIProviderの外部連携契約またはMock実装です。実サービスへの接続は今回行いません。
class MockAIProvider:
    mode = "MOCK"

    # 実推論を行わず、Mockであることが明確なタスク結果を返します。
    def execute(self, task_type: str, data: dict) -> dict:
        return {
            "mock": True,
            "task_type": task_type,
            "message": "Mock task completed; no AI inference was performed",
        }
