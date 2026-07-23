import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.ai_usage_log_service import AiUsageLogService
from app.services.tenant_ai_provider_service import TenantAiProviderService


class IntelligenceService:
    def __init__(self) -> None:
        self.ai_provider = TenantAiProviderService()
        self.usage_logs = AiUsageLogService()

    async def list_articles(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT p.id AS publication_id, p.status AS publication_status, p.has_summary, p.read_at, p.created_at AS published_to_tenant_at,
                       a.id AS article_id, a.created_at AS article_created_at, a.title, a.url, a.author, a.published_at,
                       a.content_summary, a.ai_category, a.ai_tags, a.ai_relevance_score
                FROM intelligence_article_publications p
                JOIN intelligence_articles a ON a.id = p.article_id AND a.created_at = p.article_created_at
                WHERE p.tenant_id = :tenant_id
                ORDER BY p.created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [self._serialize_article(row) for row in result.mappings().all()]

    async def get_article(self, conn: AsyncConnection, tenant_id: str, article_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT p.id AS publication_id, p.status AS publication_status, p.has_summary, p.read_at, p.created_at AS published_to_tenant_at,
                       a.id AS article_id, a.created_at AS article_created_at, a.title, a.url, a.author, a.published_at,
                       a.content_summary, a.content_raw, a.ai_category, a.ai_tags, a.ai_relevance_score
                FROM intelligence_article_publications p
                JOIN intelligence_articles a ON a.id = p.article_id AND a.created_at = p.article_created_at
                WHERE p.tenant_id = :tenant_id AND p.article_id = :article_id
                ORDER BY p.created_at DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "article_id": article_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="文章不存在或未发布给当前租户", status_code=404)
        return self._serialize_article(row, include_content=True)

    async def mark_article_status(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        article_id: str,
        status: str,
    ) -> dict:
        await conn.execute(
            text(
                """
                UPDATE intelligence_article_publications
                SET status = :status,
                    read_at = CASE WHEN :status = 'read' THEN now() ELSE read_at END,
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND article_id = :article_id
                """
            ),
            {"tenant_id": tenant_id, "article_id": article_id, "status": status},
        )
        return {"article_id": article_id, "status": status}

    async def get_subscriptions(self, conn: AsyncConnection, tenant_id: str, user_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, industry_tags, min_relevance, notify_enabled, created_at, updated_at
                FROM intelligence_subscriptions
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return [
            {
                "id": str(row["id"]),
                "industry_tags": row["industry_tags"],
                "min_relevance": float(row["min_relevance"]),
                "notify_enabled": row["notify_enabled"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def put_subscriptions(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> list[dict]:
        existing = await conn.execute(
            text(
                """
                SELECT id
                FROM intelligence_subscriptions
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        row = existing.mappings().first()
        if row is None:
            await conn.execute(
                text(
                    """
                    INSERT INTO intelligence_subscriptions
                      (id, tenant_id, user_id, industry_tags, min_relevance, notify_enabled)
                    VALUES
                      (:id, :tenant_id, :user_id, CAST(:industry_tags AS jsonb), :min_relevance, :notify_enabled)
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "industry_tags": self._to_json(payload.get("industry_tags", [])),
                    "min_relevance": payload.get("min_relevance", 0.5),
                    "notify_enabled": payload.get("notify_enabled", True),
                },
            )
        else:
            await conn.execute(
                text(
                    """
                    UPDATE intelligence_subscriptions
                    SET industry_tags = CAST(:industry_tags AS jsonb),
                        min_relevance = :min_relevance,
                        notify_enabled = :notify_enabled,
                        updated_at = now()
                    WHERE id = :id
                    """
                ),
                {
                    "id": row["id"],
                    "industry_tags": self._to_json(payload.get("industry_tags", [])),
                    "min_relevance": payload.get("min_relevance", 0.5),
                    "notify_enabled": payload.get("notify_enabled", True),
                },
            )
        return await self.get_subscriptions(conn, tenant_id, user_id)

    async def publish_article(self, conn: AsyncConnection, *, payload: dict) -> dict:
        article_id = payload.get("id") or str(new_uuid())
        created_at = self._parse_datetime(payload.get("created_at")) if payload.get("created_at") else datetime.now(timezone.utc)
        source_id = payload.get("source_id")
        status = "processed"
        await conn.execute(
            text(
                """
                INSERT INTO intelligence_articles
                  (id, created_at, source_id, title, url, author, published_at, content_raw, content_summary,
                   ai_category, ai_tags, ai_relevance_score, ai_model_id, ai_usage_log_id, status)
                VALUES
                  (:id, :created_at, :source_id, :title, :url, :author, :published_at, :content_raw, :content_summary,
                   :ai_category, CAST(:ai_tags AS jsonb), :ai_relevance_score, NULL, NULL, :status)
                ON CONFLICT (id, created_at) DO UPDATE
                SET title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    author = EXCLUDED.author,
                    published_at = EXCLUDED.published_at,
                    content_raw = EXCLUDED.content_raw,
                    content_summary = EXCLUDED.content_summary,
                    ai_category = EXCLUDED.ai_category,
                    ai_tags = EXCLUDED.ai_tags,
                    ai_relevance_score = EXCLUDED.ai_relevance_score,
                    status = EXCLUDED.status
                """
            ),
            {
                "id": article_id,
                "created_at": created_at,
                "source_id": source_id,
                "title": payload["title"],
                "url": payload.get("url"),
                "author": payload.get("author"),
                "published_at": self._parse_datetime(payload.get("published_at")) if payload.get("published_at") else created_at,
                "content_raw": payload.get("content_raw"),
                "content_summary": self._build_summary(payload.get("content_raw")),
                "ai_category": payload.get("ai_category"),
                "ai_tags": self._to_json(payload.get("ai_tags", [])),
                "ai_relevance_score": payload.get("ai_relevance_score", 0.7),
                "status": status,
            },
        )

        candidate_rows = await conn.execute(
            text(
                """
                SELECT s.id AS subscription_id, s.tenant_id, s.user_id, s.industry_tags, s.min_relevance, s.notify_enabled
                FROM intelligence_subscriptions s
                JOIN users u ON u.id = s.user_id AND u.status = 'active'
                JOIN tenants t ON t.id = s.tenant_id AND t.status = 'active'
                """
            )
        )
        by_tenant: dict[str, list[dict]] = defaultdict(list)
        article_tags = {str(item).lower() for item in payload.get("ai_tags", [])}
        relevance = float(payload.get("ai_relevance_score", 0.7))
        for row in candidate_rows.mappings().all():
            subscription_tags = {str(item).lower() for item in (row["industry_tags"] or [])}
            if subscription_tags and article_tags and not (subscription_tags & article_tags):
                continue
            if relevance < float(row["min_relevance"]):
                continue
            by_tenant[str(row["tenant_id"])].append(dict(row))

        published = 0
        with_summary = 0
        for tenant_id, subscriptions in by_tenant.items():
            has_summary = False
            usage_log_id = None
            model_id = None
            try:
                await self.ai_provider.assert_feature_available(conn, tenant_id=tenant_id)
                model = await self._get_model(conn)
                estimated_cost = Decimal(str(payload.get("estimated_cost", "1.0")))
                usage_log_id = await self.usage_logs.create_pending(
                    conn,
                    tenant_id=tenant_id,
                    model_id=model["id"],
                    usage_type="intelligence_summary",
                    estimated_cost=estimated_cost,
                    idempotency_key=f"intelligence-usage:{tenant_id}:{article_id}",
                    entity_type="intelligence_article",
                    entity_id=article_id,
                )
                provider_usage = {"input_tokens": 400, "output_tokens": 100, "total_tokens": 500}
                await self.usage_logs.complete(
                    conn,
                    usage_log_id=usage_log_id,
                    provider_request_id=f"heuristic-intel-{new_uuid()}",
                    provider_response=provider_usage,
                    actual_cost=estimated_cost,
                    response_usage=provider_usage,
                )
                has_summary = True
                model_id = model["id"]
                with_summary += 1
            except AppError as exc:
                if exc.code not in {
                    "OPENROUTER_NOT_CONFIGURED",
                    "INSUFFICIENT_BALANCE",
                    "OPENROUTER_BALANCE_UNKNOWN",
                    "INVALID_OPENROUTER_API_KEY",
                    "OPENROUTER_PROVIDER_ERROR",
                }:
                    raise

            first_subscription = subscriptions[0]
            await conn.execute(
                text(
                    """
                    INSERT INTO intelligence_article_publications
                      (id, tenant_id, article_id, article_created_at, status, has_summary, matched_by, subscription_id)
                    VALUES
                      (:id, :tenant_id, :article_id, :article_created_at, 'unread', :has_summary, 'subscription', :subscription_id)
                    ON CONFLICT (tenant_id, article_id) DO UPDATE
                    SET has_summary = EXCLUDED.has_summary,
                        updated_at = now()
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "article_id": article_id,
                    "article_created_at": created_at,
                    "has_summary": has_summary,
                    "subscription_id": first_subscription["subscription_id"],
                },
            )
            published += 1
            await conn.execute(
                text(
                    """
                    UPDATE intelligence_articles
                    SET status = 'published',
                        ai_model_id = COALESCE(:ai_model_id, ai_model_id),
                        ai_usage_log_id = COALESCE(:ai_usage_log_id, ai_usage_log_id)
                    WHERE id = :article_id AND created_at = :created_at
                    """
                ),
                {
                    "article_id": article_id,
                    "created_at": created_at,
                    "ai_model_id": model_id,
                    "ai_usage_log_id": usage_log_id,
                },
            )
            for subscription in subscriptions:
                if not subscription["notify_enabled"]:
                    continue
                await conn.execute(
                    text(
                        """
                        INSERT INTO notifications
                          (id, tenant_id, user_id, title, content, category, entity_type, entity_id, is_read)
                        VALUES
                          (:id, :tenant_id, :user_id, :title, :content, 'intelligence', 'intelligence_article', :entity_id, false)
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "tenant_id": tenant_id,
                        "user_id": subscription["user_id"],
                        "title": payload["title"],
                        "content": "有新的行业情报已发布。",
                        "entity_id": article_id,
                    },
                )

        return {
            "article_id": article_id,
            "published_tenants": published,
            "tenants_with_summary": with_summary,
            "created_at": created_at.isoformat(),
        }

    async def _get_model(self, conn: AsyncConnection) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT m.id
                FROM ai_scene_defaults s
                JOIN ai_models m ON m.id = s.model_id
                WHERE s.scene = 'intelligence_summary' AND m.is_active = true
                  AND s.instance_id = :instance_id
                LIMIT 1
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="VALIDATION_ERROR", message="当前没有可用情报模型", status_code=422)
        return {"id": str(row["id"])}

    def _build_summary(self, content_raw: str | None) -> str | None:
        if not content_raw:
            return None
        normalized = " ".join(content_raw.split())
        return normalized[:240]

    def _serialize_article(self, row, *, include_content: bool = False) -> dict:
        item = {
            "publication_id": str(row["publication_id"]),
            "article_id": str(row["article_id"]),
            "article_created_at": row["article_created_at"].isoformat(),
            "title": row["title"],
            "url": row["url"],
            "author": row["author"],
            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            "status": row["publication_status"],
            "has_summary": row["has_summary"],
            "content_summary": row["content_summary"] if row["has_summary"] else None,
            "ai_category": row["ai_category"],
            "ai_tags": row["ai_tags"],
            "ai_relevance_score": float(row["ai_relevance_score"]) if row["ai_relevance_score"] is not None else None,
            "read_at": row["read_at"].isoformat() if row["read_at"] else None,
            "published_to_tenant_at": row["published_to_tenant_at"].isoformat()
            if row["published_to_tenant_at"]
            else None,
        }
        if include_content:
            item["content_raw"] = row.get("content_raw")
        return item

    def _parse_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)
