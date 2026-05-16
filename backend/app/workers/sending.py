"""邮件发送 Worker

职责：
  - 从 sequence_enrollments 取待发邮件（claim_due_emails）
  - 调 EngageLab API 发送（含 open_tracking=true）
  - 回写 emails 表状态（queued → sent/failed）
  - 失败时写 error_code + error_message

并发防护：已由 TenantMessagingService.claim_due_emails 内的
email_send_locks 表（FOR UPDATE SKIP LOCKED）保证幂等，无需额外中间态。

domain_warmup_status.daily_limit 限速逻辑已在
TenantMessagingService.reserve_domain_quota 中实现（发送前检查配额）。
"""
from app.integrations.engagelab import EngageLabClient, EngageLabSendError
from app.services.tenant_messaging_service import TenantMessagingService


class SendingWorker:
    def __init__(
        self,
        *,
        service: TenantMessagingService | None = None,
        provider: EngageLabClient | None = None,
    ) -> None:
        self.service = service or TenantMessagingService()
        self.provider = provider or EngageLabClient()

    async def run_once(
        self,
        engine,
        *,
        service_instance: str,
        limit: int = 20,
    ) -> dict:
        """
        执行一轮发送任务：

        1. claim_due_emails — 从 sequence_enrollments 取到期待发邮件，写入 emails 表
           并通过 email_send_locks 防并发（FOR UPDATE SKIP LOCKED）
        2. 逐封发送：
           a. 调 EngageLab.send_email（内含 open_tracking=true，幂等键=email_id）
           b. 成功 → mark_email_sent（status=sent，写 engagelab_message_id）
           c. 失败 → mark_email_failed（status=failed，写 error_code + error_message）
        3. 返回本轮处理摘要

        限速保障：
          claim_due_emails 内调用 reserve_domain_quota，检查 domain_warmup_status.daily_limit，
          配额不足则抛出 QUOTA_EXCEEDED，该封邮件跳过（本轮不处理）。
        """
        # 步骤 1：领取到期邮件（写入 emails 表 status=queued，lock 保证并发安全）
        async with engine.begin() as conn:
            claimed = await self.service.claim_due_emails(
                conn,
                service_instance=service_instance,
                limit=limit,
            )

        processed = []
        for item in claimed["items"]:
            try:
                # 步骤 2a：调 EngageLab
                # open_tracking=True 已在 EngageLabClient.send_email 内固定设置
                # idempotency_key=email_id 确保重试不重复发
                provider_result = await self.provider.send_email(
                    {
                        "from_email": item["from_email"],
                        "from_name": item.get("from_name"),
                        "to_email": item["to_email"],
                        "to_name": item.get("to_name"),
                        "subject": item["subject"],
                        "body_html": item["body_html"],
                        "body_text": item.get("body_text"),
                        "idempotency_key": item["email_id"],
                    }
                )
                # 步骤 2b：发送成功 → status=sent
                async with engine.begin() as conn:
                    result = await self.service.mark_email_sent(
                        conn,
                        email_id=item["email_id"],
                        payload={"engagelab_message_id": provider_result["engagelab_message_id"]},
                    )
                processed.append(result | {"provider_status": "sent"})

            except EngageLabSendError as exc:
                # 步骤 2c：EngageLab 返回错误 → status=failed
                # 15 分钟后 enrollment 可重试（由 mark_email_failed 内的
                # UPDATE sequence_enrollments SET next_step_due_at = now() + 15m 驱动）
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "reason": str(exc),
                            "error_code": "ENGAGELAB_ERROR",
                            "error_message": str(exc),
                        },
                    )
                processed.append(result | {"provider_status": "failed"})

            except Exception as exc:  # pragma: no cover - 防御性兜底
                # 网络超时 / 未知异常 → 同样标记失败
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "reason": str(exc),
                            "error_code": "UNKNOWN_ERROR",
                            "error_message": str(exc),
                        },
                    )
                processed.append(result | {"provider_status": "failed"})

        return {
            "claimed_count": len(claimed["items"]),
            "processed_count": len(processed),
            "items": processed,
        }
