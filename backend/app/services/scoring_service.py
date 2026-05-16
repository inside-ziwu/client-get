import json
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.ai_usage_log_service import AiUsageLogService
from app.services.tenant_ai_provider_service import TenantAiProviderService


class ScoringService:
    retry_delay_seconds = 900

    def __init__(self) -> None:
        self.ai_provider = TenantAiProviderService()
        self.usage_logs = AiUsageLogService()

    async def trigger_scoring(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str | None = None,
        tenant_company_ids: list[str] | None = None,
        pending_only: bool = False,
        mode: str = "inline",
    ) -> dict:
        if mode not in {"inline", "enqueue"}:
            raise AppError(code="VALIDATION_ERROR", message="mode 仅支持 inline 或 enqueue", status_code=422)
        if mode == "enqueue":
            return await self.enqueue_jobs(
                conn,
                tenant_id=tenant_id,
                tenant_company_ids=tenant_company_ids,
                pending_only=pending_only,
                source="trigger",
            )

        company_ids = await self._eligible_company_ids(
            conn,
            tenant_id=tenant_id,
            tenant_company_ids=tenant_company_ids,
            pending_only=pending_only,
        )
        scored = []
        for company_id in company_ids:
            scored.append(await self.score_company(conn, tenant_company_id=company_id))
        return {"mode": "inline", "scored_count": len(scored), "items": scored}

    async def enqueue_jobs(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str | None = None,
        tenant_company_ids: list[str] | None = None,
        pending_only: bool = False,
        source: str = "system",
    ) -> dict:
        company_ids = await self._eligible_company_ids(
            conn,
            tenant_id=tenant_id,
            tenant_company_ids=tenant_company_ids,
            pending_only=pending_only,
        )
        items = []
        for company_id in company_ids:
            item = await self._enqueue_job(conn, tenant_company_id=company_id, source=source)
            if item is not None:
                items.append(item)
        return {"mode": "enqueue", "enqueued_count": len(items), "items": items}

    async def claim_jobs(
        self,
        conn: AsyncConnection,
        *,
        service_instance: str,
        limit: int,
        lease_seconds: int,
    ) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, tenant_id, tenant_company_id, status, attempt_count
                FROM scoring_jobs
                WHERE (status = 'pending' AND (lease_expires_at IS NULL OR lease_expires_at <= now()))
                   OR (status = 'leased' AND lease_expires_at <= now())
                ORDER BY created_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
                """
            ),
            {"limit": limit},
        )
        items = []
        for row in result.mappings().all():
            lease_id = str(new_uuid())
            updated = await conn.execute(
                text(
                    """
                    UPDATE scoring_jobs
                    SET status = 'leased',
                        lease_id = :lease_id,
                        lease_owner = :lease_owner,
                        lease_expires_at = now() + make_interval(secs => :lease_seconds),
                        attempt_count = attempt_count + 1,
                        updated_at = now()
                    WHERE id = :job_id
                    RETURNING id, tenant_id, tenant_company_id, lease_id, lease_owner, lease_expires_at, attempt_count
                    """
                ),
                {
                    "job_id": row["id"],
                    "lease_id": lease_id,
                    "lease_owner": service_instance,
                    "lease_seconds": lease_seconds,
                },
            )
            claimed = updated.mappings().one()
            items.append(
                {
                    "job_id": str(claimed["id"]),
                    "tenant_id": str(claimed["tenant_id"]),
                    "tenant_company_id": str(claimed["tenant_company_id"]),
                    "lease_id": str(claimed["lease_id"]),
                    "lease_owner": claimed["lease_owner"],
                    "lease_expires_at": claimed["lease_expires_at"].isoformat(),
                    "attempt_count": claimed["attempt_count"],
                }
            )
        return {"items": items}

    async def submit_job_result(
        self,
        conn: AsyncConnection,
        *,
        job_id: str,
        lease_id: str,
        score_result: dict | None = None,
        error: str | None = None,
        retryable: bool = False,
    ) -> dict:
        job = await self._load_job_for_update(conn, job_id)
        self._assert_job_lease(job, lease_id)

        if error:
            if retryable:
                await conn.execute(
                    text(
                        """
                        UPDATE scoring_jobs
                        SET status = 'pending',
                            lease_id = NULL,
                            lease_owner = NULL,
                            lease_expires_at = now() + make_interval(secs => :delay_seconds),
                            last_error = :last_error,
                            updated_at = now()
                        WHERE id = :job_id
                        """
                    ),
                    {
                        "job_id": job_id,
                        "delay_seconds": self.retry_delay_seconds,
                        "last_error": error,
                    },
                )
                return {"job_id": job_id, "status": "pending", "retryable": True, "reason": error}

            await conn.execute(
                text(
                    """
                    UPDATE scoring_jobs
                    SET status = 'failed',
                        lease_id = NULL,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        last_error = :last_error,
                        completed_at = now(),
                        updated_at = now()
                    WHERE id = :job_id
                    """
                ),
                {"job_id": job_id, "last_error": error},
            )
            return {"job_id": job_id, "status": "failed", "reason": error}

        if score_result is None:
            score_result = await self.prepare_score_result(conn, tenant_company_id=str(job["tenant_company_id"]))
        persisted = await self.persist_score_result(conn, score_result=score_result)
        next_status = "completed"
        await conn.execute(
            text(
                """
                UPDATE scoring_jobs
                SET status = 'completed',
                    lease_id = NULL,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    last_error = NULL,
                    completed_at = now(),
                    updated_at = now()
                WHERE id = :job_id
                """
            ),
            {"job_id": job_id},
        )
        return {"job_id": job_id, "status": next_status, "result": persisted}

    async def prepare_score_result(
        self,
        conn: AsyncConnection,
        *,
        tenant_company_id: str,
    ) -> dict:
        row = await self._load_company_context(conn, tenant_company_id)
        template = await self._load_active_template(conn, str(row["tenant_id"]))
        template_version_id = await self._resolve_template_version_id(conn, template)

        dimension_scores = []
        total_score = Decimal("0")
        llm_pending = False
        llm_scores = []
        llm_reasoning_parts = []
        llm_model_id = None
        llm_usage_log_id = None

        for dimension in template["dimensions"]:
            # 新格式：dimension.conditions 存在，使用绝对分制
            if "conditions" in dimension:
                dim_score = Decimal(str(self._evaluate_conditions(dimension["conditions"], row)))
                dimension_scores.append(
                    {
                        "key": dimension.get("key", dimension.get("id")),
                        "name": dimension.get("name"),
                        "type": "rule",
                        "score": float(dim_score),
                    }
                )
                total_score += dim_score
                continue

            # 旧格式兼容：dimension.type + weight + rules
            weight = Decimal(str(dimension.get("weight", 0)))
            if dimension.get("type") == "rule":
                raw_score = Decimal(str(self._evaluate_rule_dimension(dimension.get("rules", []), row)))
                weighted = (raw_score * weight) / Decimal("100")
                dimension_scores.append(
                    {
                        "id": dimension["id"],
                        "name": dimension.get("name"),
                        "type": "rule",
                        "raw_score": float(raw_score),
                        "weighted_score": float(weighted),
                    }
                )
                total_score += weighted
                continue

            llm_result = await self._evaluate_llm_dimension(
                conn,
                tenant_id=str(row["tenant_id"]),
                user_id=None,
                tenant_company_id=tenant_company_id,
                tenant_industry=row["tenant_industry"],
                company_industry=row["industry_desc"],
                dimension=dimension,
            )
            if llm_result["pending"]:
                llm_pending = True
                dimension_scores.append(
                    {
                        "id": dimension["id"],
                        "name": dimension.get("name"),
                        "type": "llm",
                        "pending": True,
                        "reason": llm_result["reason"],
                    }
                )
                continue
            raw_score = llm_result["score"]
            weighted = (raw_score * weight) / Decimal("100")
            total_score += weighted
            llm_scores.append(raw_score)
            llm_reasoning_parts.append(llm_result["reasoning"])
            llm_model_id = llm_result["model_id"]
            llm_usage_log_id = llm_result["usage_log_id"]
            dimension_scores.append(
                {
                    "id": dimension["id"],
                    "name": dimension.get("name"),
                    "type": "llm",
                    "raw_score": float(raw_score),
                    "weighted_score": float(weighted),
                    "reasoning": llm_result["reasoning"],
                }
            )

        grade = self._map_grade(total_score, template["grade_thresholds"])
        llm_score = (sum(llm_scores) / len(llm_scores)) if llm_scores else None
        llm_reasoning = " ".join(llm_reasoning_parts) if llm_reasoning_parts else None

        return {
            "tenant_id": str(row["tenant_id"]),
            "tenant_company_id": tenant_company_id,
            "template_id": template["id"],
            "template_version_id": template_version_id,
            "total_score": total_score,
            "grade": grade,
            "dimension_scores": dimension_scores,
            "llm_pending": llm_pending,
            "llm_score": llm_score,
            "llm_reasoning": llm_reasoning,
            "llm_model_id": llm_model_id,
            "llm_usage_log_id": llm_usage_log_id,
        }

    async def persist_score_result(self, conn: AsyncConnection, *, score_result: dict) -> dict:
        tenant_company_id = int(score_result["tenant_company_id"])
        latest = await conn.execute(
            text(
                """
                SELECT id, retry_count
                FROM company_scores
                WHERE tenant_company_id = :tenant_company_id AND template_version_id = :template_version_id AND is_retry = false
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {
                "tenant_company_id": tenant_company_id,
                "template_version_id": score_result["template_version_id"],
            },
        )
        latest_row = latest.mappings().first()
        score_id = str(new_uuid())
        is_retry = latest_row is not None
        retry_count = (latest_row["retry_count"] + 1) if latest_row is not None else 0
        related_score_id = str(latest_row["id"]) if latest_row is not None else None

        await conn.execute(
            text(
                """
                INSERT INTO company_scores
                  (id, tenant_id, tenant_company_id, template_id, template_version_id, total_score, grade, dimension_scores,
                   llm_pending, llm_score, llm_reasoning, llm_model_id, llm_usage_log_id, is_retry, retry_count, related_score_id)
                VALUES
                  (:id, :tenant_id, :tenant_company_id, :template_id, :template_version_id, :total_score, :grade,
                   CAST(:dimension_scores AS jsonb), :llm_pending, :llm_score, :llm_reasoning, :llm_model_id,
                   :llm_usage_log_id, :is_retry, :retry_count, :related_score_id)
                """
            ),
            {
                "id": score_id,
                "tenant_id": score_result["tenant_id"],
                "tenant_company_id": tenant_company_id,
                "template_id": score_result["template_id"],
                "template_version_id": score_result["template_version_id"],
                "total_score": score_result["total_score"],
                "grade": score_result["grade"],
                "dimension_scores": self._to_json(score_result["dimension_scores"]),
                "llm_pending": score_result["llm_pending"],
                "llm_score": score_result["llm_score"],
                "llm_reasoning": score_result["llm_reasoning"],
                "llm_model_id": score_result["llm_model_id"],
                "llm_usage_log_id": score_result["llm_usage_log_id"],
                "is_retry": is_retry,
                "retry_count": retry_count,
                "related_score_id": related_score_id,
            },
        )

        final_score = max(0.0, min(100.0, float(score_result["total_score"])))

        await conn.execute(
            text(
                """
                UPDATE tenant_companies
                SET model_score = :model_score,
                    score = :score,
                    updated_at = now()
                WHERE id = :tenant_company_id
                """
            ),
            {
                "tenant_company_id": tenant_company_id,
                "model_score": final_score,
                "score": final_score,
            },
        )

        return {
            "score_id": score_id,
            "tenant_company_id": str(tenant_company_id),
            "grade": score_result["grade"],
            "total_score": final_score,
            "llm_pending": score_result["llm_pending"],
        }

    async def score_company(self, conn: AsyncConnection, *, tenant_company_id: str) -> dict:
        prepared = await self.prepare_score_result(conn, tenant_company_id=tenant_company_id)
        return await self.persist_score_result(conn, score_result=prepared)

    async def _eligible_company_ids(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str | None = None,
        tenant_company_ids: list[str] | None = None,
        pending_only: bool = False,
    ) -> list[str]:
        if tenant_id is None:
            result = await conn.execute(
                text(
                    """
                    SELECT tc.id
                    FROM tenant_companies tc
                    WHERE tc.visibility_status = 'visible'
                      AND tc.data_status = 'ready'
                    """
                )
            )
        else:
            result = await conn.execute(
                text(
                    """
                    SELECT tc.id
                    FROM tenant_companies tc
                    WHERE tc.tenant_id = :tenant_id
                      AND tc.visibility_status = 'visible'
                      AND tc.data_status = 'ready'
                    """
                ),
                {"tenant_id": tenant_id},
            )
        all_ids = [str(row[0]) for row in result.all()]
        if tenant_company_ids:
            requested = set(tenant_company_ids)
            all_ids = [company_id for company_id in all_ids if company_id in requested]
        if pending_only:
            pending_result = await conn.execute(
                text(
                    """
                    SELECT DISTINCT tenant_company_id
                    FROM company_scores
                    WHERE llm_pending = true
                    """
                )
            )
            pending_ids = {str(row[0]) for row in pending_result.all()}
            all_ids = [company_id for company_id in all_ids if company_id in pending_ids]
        return all_ids

    async def _enqueue_job(self, conn: AsyncConnection, *, tenant_company_id: str, source: str) -> dict | None:
        company = await conn.execute(
            text(
                """
                SELECT tenant_id
                FROM tenant_companies
                WHERE id = :tenant_company_id
                  AND visibility_status = 'visible'
                """
            ),
            {"tenant_company_id": tenant_company_id},
        )
        company_row = company.mappings().first()
        if company_row is None:
            raise AppError(code="NOT_FOUND", message="待评分公司不存在", status_code=404)
        inserted = await conn.execute(
            text(
                """
                INSERT INTO scoring_jobs
                  (id, tenant_id, tenant_company_id, status, payload)
                VALUES
                  (:id, :tenant_id, :tenant_company_id, 'pending', CAST(:payload AS jsonb))
                ON CONFLICT DO NOTHING
                RETURNING id, tenant_id, tenant_company_id, status, created_at
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": company_row["tenant_id"],
                "tenant_company_id": tenant_company_id,
                "payload": self._to_json({"source": source}),
            },
        )
        row = inserted.mappings().first()
        if row is None:
            return None
        return {
            "job_id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "tenant_company_id": str(row["tenant_company_id"]),
            "status": row["status"],
            "created_at": row["created_at"].isoformat(),
        }

    async def _load_job_for_update(self, conn: AsyncConnection, job_id: str):
        result = await conn.execute(
            text(
                """
                SELECT id, tenant_id, tenant_company_id, status, lease_id, lease_owner, lease_expires_at, attempt_count
                FROM scoring_jobs
                WHERE id = :job_id
                FOR UPDATE
                """
            ),
            {"job_id": job_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="评分任务不存在", status_code=404)
        return row

    def _assert_job_lease(self, job, lease_id: str) -> None:
        if job["status"] != "leased":
            raise AppError(code="LEASE_INVALID", message="评分任务当前不处于 leased 状态", status_code=409)
        if str(job["lease_id"]) != lease_id:
            raise AppError(code="LEASE_INVALID", message="lease_id 不匹配", status_code=409)
        expires_at = job["lease_expires_at"]
        if expires_at is None or expires_at <= self._now_from_row(expires_at):
            raise AppError(code="LEASE_INVALID", message="lease 已过期", status_code=409)

    def _now_from_row(self, value):
        return datetime.now(value.tzinfo or timezone.utc)

    async def _load_company_context(self, conn: AsyncConnection, tenant_company_id: str):
        result = await conn.execute(
            text(
                """
                SELECT tc.id, tc.tenant_id, tc.data_status, tc.business_status,
                       cc.industry_desc, cc.industry_tags, cc.product_tags,
                       cc.country_iso3, cc.website,
                       cc.employee_num, cc.trade_amount_3y_usd, cc.trade_count,
                       cc.contacts_count, cc.pcb_suppliers,
                       ARRAY(
                         SELECT ccs.source_type
                         FROM clean_company_sources ccs
                         WHERE ccs.clean_company_id = cc.id
                         ORDER BY ccs.source_type
                       ) AS source_types,
                       t.industry AS tenant_industry
                FROM tenant_companies tc
                JOIN clean_companies cc ON cc.id = tc.clean_company_id
                JOIN tenants t ON t.id = tc.tenant_id
                WHERE tc.id = CAST(CAST(:tenant_company_id AS text) AS bigint)
                  AND tc.visibility_status = 'visible'
                """
            ),
            {"tenant_company_id": tenant_company_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="待评分公司不存在", status_code=404)
        return row

    async def _load_active_template(self, conn: AsyncConnection, tenant_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, version, dimensions, grade_thresholds
                FROM scoring_templates
                WHERE tenant_id = :tenant_id AND is_active = true
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="VALIDATION_ERROR", message="当前租户没有启用中的评分模板", status_code=422)
        return {
            "id": str(row["id"]),
            "version": row["version"],
            "dimensions": row["dimensions"],
            "grade_thresholds": row["grade_thresholds"],
        }

    async def _resolve_template_version_id(self, conn: AsyncConnection, template: dict) -> str:
        result = await conn.execute(
            text(
                """
                SELECT id
                FROM scoring_template_versions
                WHERE template_id = :template_id AND version = :version
                LIMIT 1
                """
            ),
            {"template_id": template["id"], "version": template["version"]},
        )
        row = result.mappings().first()
        if row is not None:
            return str(row["id"])
        fallback_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO scoring_template_versions
                  (id, tenant_id, template_id, version, dimensions, grade_thresholds, change_reason)
                SELECT :id, tenant_id, id, version, dimensions, grade_thresholds, 'autofix missing version row'
                FROM scoring_templates
                WHERE id = :template_id
                """
            ),
            {
                "id": fallback_id,
                "template_id": template["id"],
            },
        )
        return fallback_id

    def _evaluate_conditions(self, conditions: list[dict], row) -> int:
        """新格式评分：从 conditions 列表中找到第一个匹配的条件，返回其 score。"""
        for cond in conditions:
            ct = cond.get("condition")

            if ct == "default":
                return int(cond.get("score", 0))

            if ct == "factory_type_in":
                values = [str(v).lower() for v in (cond.get("value") or [])]
                factory_type = (self._row_get(row, "industry_desc") or "").lower()
                if factory_type and factory_type in values:
                    return int(cond.get("score", 0))

            elif ct == "employee_num_range":
                num = row["employee_num"]
                if num is not None:
                    num = int(num)
                    min_v = cond.get("min")
                    max_v = cond.get("max")
                    ok = True
                    if min_v is not None and num < int(min_v):
                        ok = False
                    if max_v is not None and num >= int(max_v):
                        ok = False
                    if ok:
                        return int(cond.get("score", 0))

            elif ct == "trade_amount_3y_usd_range":
                amount = row["trade_amount_3y_usd"]
                if amount is not None:
                    amount = float(amount)
                    min_v = cond.get("min")
                    max_v = cond.get("max")
                    ok = True
                    if min_v is not None and amount < float(min_v):
                        ok = False
                    if max_v is not None and amount >= float(max_v):
                        ok = False
                    if ok:
                        return int(cond.get("score", 0))

            elif ct == "trade_count_range":
                count = row["trade_count"]
                if count is not None:
                    count = int(count)
                    min_v = cond.get("min")
                    max_v = cond.get("max")
                    ok = True
                    if min_v is not None and count < int(min_v):
                        ok = False
                    if max_v is not None and count >= int(max_v):
                        ok = False
                    if ok:
                        return int(cond.get("score", 0))

            elif ct == "has_contact":
                contacts_count = row["contacts_count"] or 0
                if int(contacts_count) > 0:
                    return int(cond.get("score", 0))

            elif ct == "source_table_contains":
                value = str(cond.get("value", ""))
                sources = row["source_types"] or []
                if value and value in sources:
                    return int(cond.get("score", 0))

            elif ct == "has_china_pcb_supplier":
                suppliers = [str(item).lower() for item in (row["pcb_suppliers"] or [])]
                if any("china" in item or "中国" in item for item in suppliers):
                    return int(cond.get("score", 0))

        return 0

    def _row_get(self, row, key: str):
        try:
            return row[key]
        except KeyError:
            return None

    def _evaluate_rule_dimension(self, rules: list[dict], row) -> int:
        for rule in rules:
            condition = rule.get("condition")
            if condition == "default":
                return int(rule.get("score", 0))
            if condition == "employee_count_gte":
                employee_count = self._extract_number(row["employee_num"])
                if employee_count is not None and employee_count >= int(rule.get("value", 0)):
                    return int(rule.get("score", 0))
            if condition == "data_completeness_gte":
                contacts_count = int(row["contacts_count"] or 0)
                if contacts_count > 0 and float(rule.get("value", 0)) <= 1:
                    return int(rule.get("score", 0))
            if condition == "country_in":
                values = set(rule.get("value", []))
                if row["country_iso3"] in values:
                    return int(rule.get("score", 0))
            if condition == "has_domain":
                if row["website"]:
                    return int(rule.get("score", 0))
            if condition == "industry_contains":
                expected = str(rule.get("value", "")).lower()
                industry = (row["industry_desc"] or "").lower()
                tags = [str(item).lower() for item in (row["industry_tags"] or [])]
                if expected and (expected in industry or expected in tags):
                    return int(rule.get("score", 0))
            if condition == "product_keyword_contains":
                expected = str(rule.get("value", "")).lower()
                keywords = [str(item).lower() for item in (row["product_tags"] or [])]
                if expected and any(expected in item for item in keywords):
                    return int(rule.get("score", 0))
        return 0

    async def _evaluate_llm_dimension(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str | None,
        tenant_company_id: str,
        tenant_industry: str,
        company_industry: str | None,
        dimension: dict,
    ) -> dict:
        try:
            await self.ai_provider.assert_feature_available(conn, tenant_id=tenant_id)
            model = await self._get_model(conn)
            estimated_cost = Decimal(str(dimension.get("estimated_cost", "1.0")))
        except AppError as exc:
            if exc.code in {
                "OPENROUTER_NOT_CONFIGURED",
                "INSUFFICIENT_BALANCE",
                "OPENROUTER_BALANCE_UNKNOWN",
                "INVALID_OPENROUTER_API_KEY",
                "OPENROUTER_PROVIDER_ERROR",
            }:
                return {"pending": True, "reason": self._provider_pending_reason(exc.code)}
            raise

        usage_log_id = await self.usage_logs.create_pending(
            conn,
            tenant_id=tenant_id,
            model_id=model["id"],
            usage_type="scoring",
            estimated_cost=estimated_cost,
            idempotency_key=f"scoring-usage:{tenant_company_id}:{dimension['id']}",
            user_id=user_id,
            entity_type="tenant_company",
            entity_id=tenant_company_id,
        )
        provider_usage = {"input_tokens": 200, "output_tokens": 120, "total_tokens": 320}
        await self.usage_logs.complete(
            conn,
            usage_log_id=usage_log_id,
            provider_request_id=f"heuristic-score-{new_uuid()}",
            provider_response=provider_usage,
            actual_cost=estimated_cost,
            response_usage=provider_usage,
        )
        tenant_lower = (tenant_industry or "").lower()
        company_lower = (company_industry or "").lower()
        matched = tenant_lower and company_lower and tenant_lower in company_lower
        score = Decimal("85") if matched else Decimal("60")
        reasoning = "行业匹配度较高" if matched else "行业信息有限，给出中性分"
        return {
            "pending": False,
            "score": score,
            "reasoning": reasoning,
            "model_id": model["id"],
            "usage_log_id": usage_log_id,
        }

    async def _get_model(self, conn: AsyncConnection) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT m.id
                FROM ai_scene_defaults s
                JOIN ai_models m ON m.id = s.model_id
                WHERE s.scene = 'scoring' AND m.is_active = true
                LIMIT 1
                """
            )
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="VALIDATION_ERROR", message="当前没有可用评分模型", status_code=422)
        return {"id": str(row["id"])}

    def _map_grade(self, total_score: Decimal, thresholds: dict) -> str:
        ordered = sorted(
            ((grade, Decimal(str(score))) for grade, score in thresholds.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        for grade, threshold in ordered:
            if total_score >= threshold:
                return grade
        return "D"

    @staticmethod
    def score_to_grade(score: int) -> str:
        """C6：固定档位等级映射（用于 UI 展示等简单场景，不依赖模板阈值）。"""
        if score >= 90:
            return "S"
        if score >= 70:
            return "A"
        if score >= 50:
            return "B"
        if score >= 30:
            return "C"
        return "D"

    def _extract_number(self, value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"\d+", value)
        return int(match.group()) if match else None

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _provider_pending_reason(self, error_code: str) -> str:
        mapping = {
            "OPENROUTER_NOT_CONFIGURED": "not_configured",
            "INSUFFICIENT_BALANCE": "insufficient_balance",
            "OPENROUTER_BALANCE_UNKNOWN": "balance_unknown",
            "INVALID_OPENROUTER_API_KEY": "invalid_api_key",
            "OPENROUTER_PROVIDER_ERROR": "provider_error",
        }
        return mapping.get(error_code, "provider_error")
