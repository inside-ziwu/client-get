import logging
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.services.collection_source import compute_collection_type

logger = logging.getLogger(__name__)


def _parse_employee_num(raw: str | int | None) -> int | None:
    """解析 employee_size 字段，支持 '140K+', '11 to 25', '450+', '3202' 等格式。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    s = str(raw).strip().lower().replace(",", "").replace("+", "").replace("~", "")
    if "k" in s:
        try:
            return int(float(s.replace("k", "")) * 1000)
        except (ValueError, TypeError):
            return None
    if " to " in s:
        parts = s.split(" to ")
        try:
            return (int(parts[0]) + int(parts[1])) // 2
        except (ValueError, TypeError, IndexError):
            return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _to_float(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _match_condition(condition: dict, company_data: dict) -> bool:
    ctype = condition.get("condition", "")

    if ctype == "default":
        return True

    if ctype == "factory_type_in":
        values = condition.get("value", [])
        if isinstance(values, str):
            values = [values]
        company_type = company_data.get("company_type_analysis") or ""
        return any(v.lower() in company_type.lower() for v in values) if values else False

    if ctype == "employee_num_range":
        num = _parse_employee_num(company_data.get("employee_size"))
        if num is None:
            return False
        cmin = condition.get("min")
        cmax = condition.get("max")
        if cmin is not None and num < cmin:
            return False
        if cmax is not None and num > cmax:
            return False
        return True

    if ctype == "trade_amount_3y_usd_range":
        amount = _to_float(company_data.get("trade_amount_3y_usd"))
        if amount is None:
            return False
        cmin = condition.get("min")
        cmax = condition.get("max")
        if cmin is not None and amount < cmin:
            return False
        if cmax is not None and amount > cmax:
            return False
        return True

    if ctype == "trade_count_range":
        count = company_data.get("trade_count")
        if count is None:
            return False
        try:
            count = int(count)
        except (ValueError, TypeError):
            return False
        cmin = condition.get("min")
        cmax = condition.get("max")
        if cmin is not None and count < cmin:
            return False
        if cmax is not None and count > cmax:
            return False
        return True

    if ctype == "has_contact":
        contacts = company_data.get("contacts_count")
        return contacts is not None and int(contacts) > 0

    if ctype == "source_table_contains":
        value = condition.get("value", "")
        tags = company_data.get("data_source_tags") or []
        if isinstance(tags, str):
            import json as _json
            try:
                tags = _json.loads(tags)
            except (ValueError, TypeError):
                tags = []
        source_tags = company_data.get("source_tags") or []
        all_tags = list(tags) + list(source_tags)
        tag_map = {
            "tendata_raw_companies": "腾道",
            "waimaotong_raw_companies": "外贸通",
        }
        target = tag_map.get(value, value)
        return any(target in str(t) for t in all_tags)

    if ctype == "has_china_pcb_supplier":
        # 业务口径（2026-07-03 确认）：采集类型为「精准反推」(reverse) ⇔ 有中国 PCB 供应商。
        # 采集类型判定复用 collection_source.compute_collection_type 单一真源。
        tags = company_data.get("data_source_tags")
        if isinstance(tags, str):
            import json as _json

            try:
                tags = _json.loads(tags)
            except (ValueError, TypeError):
                tags = None
        return compute_collection_type(tags) == "reverse"

    logger.warning("未知评分条件类型: %s，该维度得分 0", ctype)
    return False


def evaluate_company(
    dimensions: list[dict],
    grade_thresholds: dict,
    company_data: dict,
) -> dict:
    """纯计算函数：根据维度规则和公司数据计算评分。"""
    dimension_scores = []
    total_score = 0

    for dim in dimensions:
        dim_type = dim.get("type", "rule")
        if dim_type == "llm":
            dimension_scores.append({"key": dim.get("key", ""), "score": 0, "matched_condition": None, "skipped": "llm"})
            continue

        conditions = dim.get("conditions", dim.get("rules", []))
        matched = False
        for cond in conditions:
            if _match_condition(cond, company_data):
                score = int(cond.get("score", 0))
                total_score += score
                dimension_scores.append({
                    "key": dim.get("key", dim.get("id", "")),
                    "score": score,
                    "matched_condition": cond.get("label", cond.get("condition", "")),
                })
                matched = True
                break

        if not matched:
            dimension_scores.append({"key": dim.get("key", dim.get("id", "")), "score": 0, "matched_condition": None})

    grade = "D"
    for g in ["S", "A", "B", "C", "D"]:
        threshold = grade_thresholds.get(g, 0)
        if isinstance(threshold, str):
            threshold = int(threshold)
        if total_score >= threshold:
            grade = g
            break

    return {"total_score": total_score, "grade": grade, "dimension_scores": dimension_scores}


class ScoringEngineService:

    async def score_tenant_company(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        tenant_company_id: int | str,
    ) -> dict | None:
        """查询租户模板和公司数据，评分并写入 company_scores。"""
        tmpl = await conn.execute(text("""
            SELECT id, dimensions, grade_thresholds, version
            FROM scoring_templates
            WHERE tenant_id = CAST(:tenant_id AS uuid) AND is_active = true
            LIMIT 1
        """), {"tenant_id": tenant_id})
        tmpl_row = tmpl.mappings().first()
        if tmpl_row is None:
            return None

        version_row = await conn.execute(text("""
            SELECT id FROM scoring_template_versions
            WHERE template_id = CAST(:template_id AS uuid) AND tenant_id = CAST(:tenant_id AS uuid)
            ORDER BY version DESC LIMIT 1
        """), {"template_id": str(tmpl_row["id"]), "tenant_id": tenant_id})
        ver = version_row.mappings().first()
        version_id = str(ver["id"]) if ver else None

        company = await conn.execute(text("""
            SELECT wc.employee_size, wc.trade_amount_3y_usd, wc.trade_count,
                   wc.contacts_count, wc.data_source_tags, wc.source_tags,
                   wc.company_type_analysis, wc.industry
            FROM tenant_companies tc
            JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
            WHERE tc.id = CAST(:tc_id AS bigint) AND tc.tenant_id = CAST(:tenant_id AS uuid)
        """), {"tc_id": int(tenant_company_id), "tenant_id": tenant_id})
        company_row = company.mappings().first()
        if company_row is None:
            return None

        company_data = dict(company_row)
        result = evaluate_company(tmpl_row["dimensions"], tmpl_row["grade_thresholds"], company_data)

        import json
        await conn.execute(text("""
            INSERT INTO company_scores
                (id, tenant_id, tenant_company_id, template_id, template_version_id,
                 total_score, grade, dimension_scores, scored_at, created_at)
            VALUES
                (gen_random_uuid(), CAST(:tenant_id AS uuid), CAST(:tc_id AS bigint),
                 CAST(:template_id AS uuid), CAST(:version_id AS uuid),
                 :total_score, :grade, CAST(:dim_scores AS jsonb), now(), now())
            ON CONFLICT (tenant_company_id, template_version_id) WHERE is_retry = false
            DO UPDATE SET
                total_score = EXCLUDED.total_score,
                grade = EXCLUDED.grade,
                dimension_scores = EXCLUDED.dimension_scores,
                template_version_id = EXCLUDED.template_version_id,
                scored_at = now()
        """), {
            "tenant_id": tenant_id,
            "tc_id": int(tenant_company_id),
            "template_id": str(tmpl_row["id"]),
            "version_id": version_id,
            "total_score": result["total_score"],
            "grade": result["grade"],
            "dim_scores": json.dumps(result["dimension_scores"]),
        })

        return result

    async def score_clean_company(
        self,
        conn: AsyncConnection,
        *,
        clean_company_id: int | str,
    ) -> dict | None:
        """用平台模板评分，结果写入 waimaotong_clean_companies。"""
        tmpl = await conn.execute(text("""
            SELECT dimensions, grade_thresholds
            FROM platform_scoring_templates
            WHERE is_active = true
              AND instance_id = :instance_id
            ORDER BY updated_at DESC LIMIT 1
        """), {"instance_id": get_settings().instance_id})
        tmpl_row = tmpl.mappings().first()
        if tmpl_row is None:
            return None

        company = await conn.execute(text("""
            SELECT employee_size, trade_amount_3y_usd, trade_count,
                   contacts_count, data_source_tags, source_tags,
                   company_type_analysis, industry
            FROM waimaotong_clean_companies
            WHERE id = CAST(:id AS bigint)
        """), {"id": int(clean_company_id)})
        company_row = company.mappings().first()
        if company_row is None:
            return None

        company_data = dict(company_row)
        result = evaluate_company(tmpl_row["dimensions"], tmpl_row["grade_thresholds"], company_data)

        await conn.execute(text("""
            UPDATE waimaotong_clean_companies
            SET system_grade = :grade, system_score = :score
            WHERE id = CAST(:id AS bigint)
        """), {
            "grade": result["grade"],
            "score": result["total_score"],
            "id": int(clean_company_id),
        })

        return result

    async def rescore_tenant_all(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
    ) -> int:
        """对指定租户的所有公司重新评分。返回评分数量。"""
        tmpl = await conn.execute(text("""
            SELECT id, dimensions, grade_thresholds, version
            FROM scoring_templates
            WHERE tenant_id = CAST(:tenant_id AS uuid) AND is_active = true
            LIMIT 1
        """), {"tenant_id": tenant_id})
        tmpl_row = tmpl.mappings().first()
        if tmpl_row is None:
            return 0

        version_row = await conn.execute(text("""
            SELECT id FROM scoring_template_versions
            WHERE template_id = CAST(:template_id AS uuid) AND tenant_id = CAST(:tenant_id AS uuid)
            ORDER BY version DESC LIMIT 1
        """), {"template_id": str(tmpl_row["id"]), "tenant_id": tenant_id})
        ver = version_row.mappings().first()
        version_id = str(ver["id"]) if ver else None

        companies = await conn.execute(text("""
            SELECT tc.id AS tc_id, wc.employee_size, wc.trade_amount_3y_usd, wc.trade_count,
                   wc.contacts_count, wc.data_source_tags, wc.source_tags,
                   wc.company_type_analysis, wc.industry
            FROM tenant_companies tc
            JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
            WHERE tc.tenant_id = CAST(:tenant_id AS uuid)
        """), {"tenant_id": tenant_id})

        import json
        count = 0
        for row in companies.mappings().all():
            company_data = dict(row)
            tc_id = company_data.pop("tc_id")
            result = evaluate_company(tmpl_row["dimensions"], tmpl_row["grade_thresholds"], company_data)

            await conn.execute(text("""
                INSERT INTO company_scores
                    (id, tenant_id, tenant_company_id, template_id, template_version_id,
                     total_score, grade, dimension_scores, scored_at, created_at)
                VALUES
                    (gen_random_uuid(), CAST(:tenant_id AS uuid), CAST(:tc_id AS bigint),
                     CAST(:template_id AS uuid), CAST(:version_id AS uuid),
                     :total_score, :grade, CAST(:dim_scores AS jsonb), now(), now())
                ON CONFLICT (tenant_company_id, template_version_id) WHERE is_retry = false
                DO UPDATE SET
                    total_score = EXCLUDED.total_score,
                    grade = EXCLUDED.grade,
                    dimension_scores = EXCLUDED.dimension_scores,
                    template_version_id = EXCLUDED.template_version_id,
                    scored_at = now()
            """), {
                "tenant_id": tenant_id,
                "tc_id": int(tc_id),
                "template_id": str(tmpl_row["id"]),
                "version_id": version_id,
                "total_score": result["total_score"],
                "grade": result["grade"],
                "dim_scores": json.dumps(result["dimension_scores"]),
            })
            count += 1

        return count
