"""邮件状态对账 Worker：调用 EngageLab API 补齐 webhook 丢失的投递状态。"""

from app.integrations.engagelab import EngageLabClient
from app.services.email_reconciliation_service import EmailReconciliationService


class ReconciliationWorker:
    def __init__(
        self,
        *,
        service: EmailReconciliationService | None = None,
        client: EngageLabClient | None = None,
    ) -> None:
        self.service = service or EmailReconciliationService()
        self.client = client or EngageLabClient()

    async def run_once(self, engine) -> dict:
        async with engine.begin() as conn:
            return await self.service.reconcile_once(conn, self.client)
