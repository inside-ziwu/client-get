"""
采集调度器：每次运行为已人工首采启动的 active 关键词按需创建 competitor_search 任务。

调度逻辑（按顺序检查，任一条件满足则跳过该关键词）：
  1. 已存在 pending/running 任务 → 跳过
  2. 今日已采集数 >= 平台关键词每日限额 → 跳过（明天再来）
  3. 上次任务使用了 skip_source_ids 且结果为 0 → 所有公司已采集完，停止调度

否则创建新任务，context.params 中携带：
  - max_competitors: 今日剩余配额
  - skip_source_ids: 已采集公司 ID 列表（供 worker 跳过）
"""

import json
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.ids import new_uuid

# 励销云每日上限是平台关键词/run 维度，不从租户关键词或租户设置继承。
_DEFAULT_DAILY_LIMIT = 1000


class CollectionSchedulerService:
    async def schedule_due_tasks(self, conn: AsyncConnection) -> dict:
        scheduled = await self._schedule_due_continuation_tasks(conn)
        result = await conn.execute(
            text(
                """
                SELECT
                  ck.id,
                  ck.tenant_id,
                  ck.keyword,
                  ck.keyword_normalized,
                  km.id::text AS keyword_master_id
                FROM collection_keywords ck
                JOIN keyword_master km
                  ON km.id = ck.keyword_master_id
                  OR km.keyword_normalized = ck.keyword_normalized
                WHERE ck.status = 'active'
                  AND ck.subscription_status = 'running'
                ORDER BY ck.keyword_normalized ASC, ck.created_at ASC
                """
            )
        )
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in result.mappings().all():
            grouped[row["keyword_normalized"]].append(dict(row))

        for keyword_normalized, items in grouped.items():
            keyword = items[0]["keyword"]
            keyword_master_id = items[0]["keyword_master_id"]
            keyword_ids = [item["id"] for item in items]
            daily_limit = _DEFAULT_DAILY_LIMIT

            # ── 1. 已有进行中任务 → 跳过 ───────────────────────────────────────
            existing = await conn.execute(
                text(
                    """
                    SELECT ct.id
                    FROM collection_tasks ct
                    JOIN collection_task_keywords ctk ON ctk.task_id = ct.id
                    WHERE ctk.keyword_id = ANY(:keyword_ids)
                      AND ct.task_type = 'competitor_search'
                      AND ct.status IN ('pending', 'running')
                    LIMIT 1
                    """
                ),
                {"keyword_ids": keyword_ids},
            )
            if existing.first() is not None:
                continue

            # ── 2. 今日已达限额 → 跳过 ────────────────────────────────────────
            today_cnt = await conn.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM lixiaoyun_raw_companies lrc
                    WHERE lrc.keyword_master_id = :keyword_master_id
                      AND lrc.created_at >= CURRENT_DATE
                    """
                ),
                {"keyword_master_id": keyword_master_id},
            )
            today_count = int(today_cnt.scalar_one() or 0)
            remaining_today = daily_limit - today_count
            if remaining_today <= 0:
                continue

            # ── 3. 上次完成任务：有 skip_ids 且新增 0 家 → 全部采完，停止 ───────
            last_task_row = await conn.execute(
                text(
                    """
                    SELECT ct.result_summary, ct.context
                    FROM collection_tasks ct
                    JOIN collection_task_keywords ctk ON ctk.task_id = ct.id
                    WHERE ctk.keyword_id = ANY(:keyword_ids)
                      AND ct.task_type = 'competitor_search'
                      AND ct.status = 'completed'
                    ORDER BY ct.created_at DESC
                    LIMIT 1
                    """
                ),
                {"keyword_ids": keyword_ids},
            )
            last_task = last_task_row.mappings().first()
            if last_task is not None:
                last_summary = last_task["result_summary"] or {}
                last_context = last_task["context"] or {}
                last_competitors = int(last_summary.get("competitors_count") or 0)
                last_had_skip = bool((last_context.get("params") or {}).get("skip_source_ids"))
                if last_competitors == 0 and last_had_skip:
                    # 所有可采集公司已处理完，不再自动调度
                    continue

            # ── 4. 查询已采集 source_id（新任务跳过重复）──────────────────────
            skip_rows = await conn.execute(
                text(
                    """
                    SELECT DISTINCT lrc.source_id
                    FROM lixiaoyun_raw_companies lrc
                    WHERE lrc.keyword_master_id = :keyword_master_id
                      AND lrc.source_id IS NOT NULL
                    """
                ),
                {"keyword_master_id": keyword_master_id},
            )
            skip_source_ids = [r["source_id"] for r in skip_rows.mappings().all()]

            # ── 5. 创建任务 ───────────────────────────────────────────────────
            task_id = str(new_uuid())
            context = {
                "params": {
                    "max_competitors": remaining_today,
                    "skip_source_ids": skip_source_ids,
                }
            }
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_tasks
                      (id, keyword, keyword_normalized, countries, countries_hash,
                       source_types, task_type, context, status, priority, scheduled_at)
                    VALUES
                      (:id, :keyword, :keyword_normalized, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search',
                       CAST(:context AS jsonb), 'pending', :priority, now())
                    """
                ),
                {
                    "id": task_id,
                    "keyword": keyword,
                    "keyword_normalized": keyword_normalized,
                    "context": json.dumps(context, ensure_ascii=False),
                    "priority": 10,
                },
            )

            # ── 6. 关联 keyword_id / tenant_id ───────────────────────────────
            linked = 0
            for item in items:
                await conn.execute(
                    text(
                        """
                        INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                        VALUES (:id, :task_id, :keyword_id, :tenant_id)
                        ON CONFLICT (task_id, keyword_id) DO NOTHING
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "task_id": task_id,
                        "keyword_id": item["id"],
                        "tenant_id": item["tenant_id"],
                    },
                )
                await conn.execute(
                    text(
                        """
                        UPDATE collection_keywords
                        SET last_scheduled_at = now(), updated_at = now()
                        WHERE id = :keyword_id
                        """
                    ),
                    {"keyword_id": item["id"]},
                )
                linked += 1

            scheduled.append(
                {
                    "task_id": task_id,
                    "run_id": None,
                    "keyword_normalized": keyword_normalized,
                    "linked_keywords": linked,
                    "max_competitors": remaining_today,
                    "skip_count": len(skip_source_ids),
                }
            )

        return {"scheduled_count": len(scheduled), "items": scheduled}

    async def _schedule_due_continuation_tasks(self, conn: AsyncConnection) -> list[dict]:
        due_runs = await conn.execute(
            text(
                """
                SELECT
                  cr.id AS run_id,
                  km.keyword,
                  km.keyword_normalized,
                  cr.cursor,
                  cr.skip_source_ids,
                  cr.daily_limit,
                  cr.request_page_size
                FROM collection_runs cr
                JOIN keyword_master km ON km.id = cr.keyword_master_id
                WHERE cr.provider = 'lixiaoyun'
                  AND cr.status = 'daily_limit_reached'
                  AND cr.next_run_at IS NOT NULL
                  AND cr.next_run_at <= now()
                  AND NOT EXISTS (
                    SELECT 1
                    FROM collection_tasks ct
                    WHERE ct.run_id = cr.id
                      AND ct.status IN ('pending', 'running')
                  )
                ORDER BY cr.next_run_at ASC
                FOR UPDATE SKIP LOCKED
                """
            )
        )
        scheduled = []
        for run in due_runs.mappings().all():
            keyword_rows = await conn.execute(
                text(
                    """
                    SELECT id, tenant_id
                    FROM collection_keywords
                    WHERE keyword_normalized = :keyword_normalized
                      AND status = 'active'
                    ORDER BY created_at ASC
                    """
                ),
                {"keyword_normalized": run["keyword_normalized"]},
            )
            items = keyword_rows.mappings().all()
            if not items:
                continue

            task_id = str(new_uuid())
            page_size = max(1, min(int(run["request_page_size"] or 10), 100))
            skip_source_ids = list(run["skip_source_ids"] or [])
            context = {
                "params": {
                    "max_competitors": page_size,
                    "daily_limit": int(run["daily_limit"] or _DEFAULT_DAILY_LIMIT),
                    "page_size": page_size,
                    "skip_source_ids": skip_source_ids,
                    "cursor": run["cursor"] or {},
                }
            }
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_tasks
                      (id, run_id, keyword, keyword_normalized, countries, countries_hash,
                       source_types, task_type, context, status, priority, scheduled_at,
                       scheduled_biz_date, batch_no, page_size, cursor_snapshot)
                    VALUES
                      (:id, :run_id, :keyword, :keyword_normalized, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search',
                       CAST(:context AS jsonb), 'pending', 10, now(),
                       (now() AT TIME ZONE 'Asia/Shanghai')::date,
                       COALESCE((
                         SELECT MAX(batch_no) + 1
                         FROM collection_tasks
                         WHERE run_id = :run_id
                       ), 1),
                       :page_size, CAST(:cursor AS jsonb))
                    """
                ),
                {
                    "id": task_id,
                    "run_id": int(run["run_id"]),
                    "keyword": run["keyword"],
                    "keyword_normalized": run["keyword_normalized"],
                    "context": json.dumps(context, ensure_ascii=False),
                    "page_size": page_size,
                    "cursor": json.dumps(run["cursor"] or {}, ensure_ascii=False),
                },
            )
            linked = 0
            for item in items:
                await conn.execute(
                    text(
                        """
                        INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                        VALUES (:id, :task_id, :keyword_id, :tenant_id)
                        ON CONFLICT (task_id, keyword_id) DO NOTHING
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "task_id": task_id,
                        "keyword_id": item["id"],
                        "tenant_id": item["tenant_id"],
                    },
                )
                linked += 1

            await conn.execute(
                text(
                    """
                    UPDATE collection_runs
                    SET status = 'running',
                        next_run_at = NULL,
                        biz_date = (now() AT TIME ZONE 'Asia/Shanghai')::date,
                        today_fetched = 0,
                        updated_at = now()
                    WHERE id = :run_id
                    """
                ),
                {"run_id": run["run_id"]},
            )
            scheduled.append(
                {
                    "task_id": task_id,
                    "run_id": str(run["run_id"]),
                    "keyword_normalized": run["keyword_normalized"],
                    "linked_keywords": linked,
                    "max_competitors": page_size,
                    "skip_count": len(skip_source_ids),
                }
            )
        return scheduled
