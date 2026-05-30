import json
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.audit_service import AuditService


class AdminWorkScheduleService:
    def __init__(self) -> None:
        self.audit = AuditService()

    async def list_rule_sets(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT wrs.id, wrs.name, wrs.work_days, wrs.time_segments, wrs.is_default,
                       wrs.created_at, wrs.updated_at, count(c.iso3) AS country_count
                FROM work_rule_sets wrs
                LEFT JOIN countries c ON c.rule_set_id = wrs.id
                GROUP BY wrs.id
                ORDER BY wrs.is_default DESC, wrs.created_at DESC
                """
            )
        )
        return [self._serialize_rule_set(row) for row in result.mappings().all()]

    async def get_rule_set(self, conn: AsyncConnection, rule_set_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT wrs.id, wrs.name, wrs.work_days, wrs.time_segments, wrs.is_default,
                       wrs.created_at, wrs.updated_at, count(c.iso3) AS country_count
                FROM work_rule_sets wrs
                LEFT JOIN countries c ON c.rule_set_id = wrs.id
                WHERE wrs.id = :rule_set_id
                GROUP BY wrs.id
                """
            ),
            {"rule_set_id": rule_set_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="规则集不存在", status_code=404)
        item = self._serialize_rule_set(row)
        item["countries"] = await self._list_countries_for_rule_set(conn, rule_set_id)
        return item

    async def create_rule_set(self, conn: AsyncConnection, *, payload: dict, platform_user_id: str) -> dict:
        self._validate_rule_payload(payload)
        rule_set_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO work_rule_sets (id, name, work_days, time_segments, is_default)
                VALUES (:id, :name, CAST(:work_days AS int[]), CAST(:time_segments AS jsonb), false)
                """
            ),
            {
                "id": rule_set_id,
                "name": payload["name"].strip(),
                "work_days": payload["work_days"],
                "time_segments": self._to_json(payload["time_segments"]),
            },
        )
        created = await self.get_rule_set(conn, rule_set_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="work_rule_set",
            entity_id=rule_set_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def update_rule_set(
        self,
        conn: AsyncConnection,
        *,
        rule_set_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_rule_set(conn, rule_set_id)
        merged = {
            "name": payload.get("name", before["name"]),
            "work_days": payload.get("work_days", before["work_days"]),
            "time_segments": payload.get("time_segments", before["time_segments"]),
        }
        self._validate_rule_payload(merged)
        await conn.execute(
            text(
                """
                UPDATE work_rule_sets
                SET name = :name,
                    work_days = CAST(:work_days AS int[]),
                    time_segments = CAST(:time_segments AS jsonb),
                    updated_at = now()
                WHERE id = :rule_set_id
                """
            ),
            {
                "rule_set_id": rule_set_id,
                "name": merged["name"].strip(),
                "work_days": merged["work_days"],
                "time_segments": self._to_json(merged["time_segments"]),
            },
        )
        after = await self.get_rule_set(conn, rule_set_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="work_rule_set",
            entity_id=rule_set_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_rule_set(self, conn: AsyncConnection, *, rule_set_id: str, platform_user_id: str) -> None:
        before = await self.get_rule_set(conn, rule_set_id)
        if before["is_default"]:
            raise AppError(code="VALIDATION_ERROR", message="默认规则不能删除", status_code=422)
        await conn.execute(text("DELETE FROM work_rule_sets WHERE id = :rule_set_id"), {"rule_set_id": rule_set_id})
        await self.audit.write(
            conn,
            action="delete",
            entity_type="work_rule_set",
            entity_id=rule_set_id,
            platform_user_id=platform_user_id,
            old_value=before,
        )

    async def list_countries(
        self,
        conn: AsyncConnection,
        *,
        search: str | None = None,
        has_rule_set: bool | None = None,
    ) -> list[dict]:
        where_clauses: list[str] = []
        params: dict[str, object] = {}
        if search:
            where_clauses.append("(c.iso3 ILIKE :query OR c.name_zh ILIKE :query OR c.name_en ILIKE :query)")
            params["query"] = f"%{search}%"
        if has_rule_set is True:
            where_clauses.append("c.rule_set_id IS NOT NULL")
        elif has_rule_set is False:
            where_clauses.append("c.rule_set_id IS NULL")
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        result = await conn.execute(
            text(
                f"""
                SELECT c.iso3, c.name_zh, c.name_en, c.timezone, c.rule_set_id,
                       wrs.name AS rule_set_name, count(ch.id) AS holiday_count,
                       c.created_at, c.updated_at
                FROM countries c
                LEFT JOIN work_rule_sets wrs ON wrs.id = c.rule_set_id
                LEFT JOIN country_holidays ch ON ch.country_iso3 = c.iso3
                {where_sql}
                GROUP BY c.iso3, wrs.name
                ORDER BY c.name_zh ASC, c.iso3 ASC
                """
            ),
            params,
        )
        return [self._serialize_country(row) for row in result.mappings().all()]

    async def get_country(self, conn: AsyncConnection, iso3: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT c.iso3, c.name_zh, c.name_en, c.timezone, c.rule_set_id,
                       wrs.name AS rule_set_name, count(ch.id) AS holiday_count,
                       c.created_at, c.updated_at
                FROM countries c
                LEFT JOIN work_rule_sets wrs ON wrs.id = c.rule_set_id
                LEFT JOIN country_holidays ch ON ch.country_iso3 = c.iso3
                WHERE c.iso3 = :iso3
                GROUP BY c.iso3, wrs.name
                """
            ),
            {"iso3": iso3.upper()},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="国家不存在", status_code=404)
        item = self._serialize_country(row)
        item["holidays"] = await self.list_holidays(conn, iso3=iso3)
        return item

    async def update_country(
        self,
        conn: AsyncConnection,
        *,
        iso3: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_country(conn, iso3)
        timezone = payload.get("timezone", before["timezone"])
        self._validate_timezone(timezone)
        rule_set_id = payload.get("rule_set_id", before["rule_set_id"])
        if rule_set_id:
            await self._ensure_rule_set_exists(conn, rule_set_id)
        await conn.execute(
            text(
                """
                UPDATE countries
                SET timezone = :timezone,
                    rule_set_id = CAST(:rule_set_id AS uuid),
                    updated_at = now()
                WHERE iso3 = :iso3
                """
            ),
            {"iso3": iso3.upper(), "timezone": timezone, "rule_set_id": rule_set_id},
        )
        after = await self.get_country(conn, iso3)
        await self.audit.write(
            conn,
            action="update",
            entity_type="country",
            entity_id=None,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def update_country_timezone(
        self,
        conn: AsyncConnection,
        *,
        iso3: str,
        timezone: str,
        platform_user_id: str,
    ) -> dict:
        return await self.update_country(
            conn,
            iso3=iso3,
            payload={"timezone": timezone},
            platform_user_id=platform_user_id,
        )

    async def assign_countries_to_rule_set(
        self,
        conn: AsyncConnection,
        *,
        rule_set_id: str,
        iso3_list: list[str],
        platform_user_id: str,
    ) -> list[dict]:
        await self._ensure_rule_set_exists(conn, rule_set_id)
        countries = [item.upper() for item in iso3_list]
        await self._ensure_countries_exist(conn, countries)
        await conn.execute(
            text(
                """
                UPDATE countries
                SET rule_set_id = :rule_set_id, updated_at = now()
                WHERE iso3 = ANY(CAST(:countries AS char(3)[]))
                """
            ),
            {"rule_set_id": rule_set_id, "countries": countries},
        )
        after = await self._list_countries_for_rule_set(conn, rule_set_id)
        await self.audit.write(
            conn,
            action="assign",
            entity_type="work_rule_set_country",
            entity_id=rule_set_id,
            platform_user_id=platform_user_id,
            new_value=after,
        )
        return after

    async def remove_country_from_rule_set(
        self,
        conn: AsyncConnection,
        *,
        rule_set_id: str,
        iso3: str,
        platform_user_id: str,
    ) -> dict:
        await self._ensure_rule_set_exists(conn, rule_set_id)
        await self._ensure_countries_exist(conn, [iso3.upper()])
        await conn.execute(
            text(
                """
                UPDATE countries
                SET rule_set_id = NULL, updated_at = now()
                WHERE iso3 = :iso3 AND rule_set_id = :rule_set_id
                """
            ),
            {"iso3": iso3.upper(), "rule_set_id": rule_set_id},
        )
        item = await self.get_country(conn, iso3)
        await self.audit.write(
            conn,
            action="remove",
            entity_type="work_rule_set_country",
            entity_id=None,
            platform_user_id=platform_user_id,
            new_value=item,
        )
        return item

    async def list_holidays(self, conn: AsyncConnection, *, iso3: str, year: int | None = None) -> list[dict]:
        year_clause = "AND EXTRACT(YEAR FROM date) = :year" if year is not None else ""
        params: dict[str, object] = {"iso3": iso3.upper()}
        if year is not None:
            params["year"] = year
        result = await conn.execute(
            text(
                f"""
                SELECT id, country_iso3, date, name, source, created_at
                FROM country_holidays
                WHERE country_iso3 = :iso3
                  {year_clause}
                ORDER BY date ASC
                """
            ),
            params,
        )
        return [self._serialize_holiday(row) for row in result.mappings().all()]

    async def create_holiday(
        self,
        conn: AsyncConnection,
        *,
        iso3: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        await self._ensure_countries_exist(conn, [iso3.upper()])
        holiday_id = str(new_uuid())
        holiday_date = self._parse_date(payload["date"])
        try:
            await conn.execute(
                text(
                    """
                    INSERT INTO country_holidays (id, country_iso3, date, name, source)
                    VALUES (:id, :iso3, :date, :name, :source)
                    """
                ),
                {
                    "id": holiday_id,
                    "iso3": iso3.upper(),
                    "date": holiday_date,
                    "name": payload.get("name"),
                    "source": payload.get("source", "manual"),
                },
            )
        except Exception as exc:
            if "country_holidays_country_iso3_date_key" in str(exc):
                raise AppError(code="DUPLICATE_HOLIDAY", message="该日期已存在假日", status_code=409) from exc
            raise
        created = await self._get_holiday(conn, holiday_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="country_holiday",
            entity_id=holiday_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def update_holiday(
        self,
        conn: AsyncConnection,
        *,
        holiday_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self._get_holiday(conn, holiday_id)
        holiday_date = self._parse_date(payload["date"]) if payload.get("date") else before["date"]
        await conn.execute(
            text(
                """
                UPDATE country_holidays
                SET date = :date,
                    name = :name,
                    source = :source
                WHERE id = :holiday_id
                """
            ),
            {
                "holiday_id": holiday_id,
                "date": holiday_date,
                "name": payload.get("name", before["name"]),
                "source": payload.get("source", before["source"]),
            },
        )
        after = await self._get_holiday(conn, holiday_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="country_holiday",
            entity_id=holiday_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_holiday(self, conn: AsyncConnection, *, holiday_id: str, platform_user_id: str) -> None:
        before = await self._get_holiday(conn, holiday_id)
        await conn.execute(text("DELETE FROM country_holidays WHERE id = :holiday_id"), {"holiday_id": holiday_id})
        await self.audit.write(
            conn,
            action="delete",
            entity_type="country_holiday",
            entity_id=holiday_id,
            platform_user_id=platform_user_id,
            old_value=before,
        )

    async def get_default_rule(self, conn: AsyncConnection) -> dict:
        result = await conn.execute(text("SELECT id FROM work_rule_sets WHERE is_default = true LIMIT 1"))
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="默认规则不存在", status_code=404)
        return await self.get_rule_set(conn, str(row["id"]))

    async def update_default_rule(self, conn: AsyncConnection, *, payload: dict, platform_user_id: str) -> dict:
        default_rule = await self.get_default_rule(conn)
        payload = {**payload, "name": payload.get("name", default_rule["name"])}
        return await self.update_rule_set(
            conn,
            rule_set_id=default_rule["id"],
            payload=payload,
            platform_user_id=platform_user_id,
        )

    async def _list_countries_for_rule_set(self, conn: AsyncConnection, rule_set_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT c.iso3, c.name_zh, c.name_en, c.timezone, c.rule_set_id,
                       wrs.name AS rule_set_name, count(ch.id) AS holiday_count,
                       c.created_at, c.updated_at
                FROM countries c
                LEFT JOIN work_rule_sets wrs ON wrs.id = c.rule_set_id
                LEFT JOIN country_holidays ch ON ch.country_iso3 = c.iso3
                WHERE c.rule_set_id = :rule_set_id
                GROUP BY c.iso3, wrs.name
                ORDER BY c.name_zh ASC, c.iso3 ASC
                """
            ),
            {"rule_set_id": rule_set_id},
        )
        return [self._serialize_country(row) for row in result.mappings().all()]

    async def _ensure_rule_set_exists(self, conn: AsyncConnection, rule_set_id: str) -> None:
        result = await conn.execute(text("SELECT 1 FROM work_rule_sets WHERE id = :id"), {"id": rule_set_id})
        if result.scalar_one_or_none() is None:
            raise AppError(code="NOT_FOUND", message="规则集不存在", status_code=404)

    async def _ensure_countries_exist(self, conn: AsyncConnection, iso3_list: list[str]) -> None:
        if not iso3_list:
            return
        result = await conn.execute(
            text("SELECT iso3 FROM countries WHERE iso3 = ANY(CAST(:countries AS char(3)[]))"),
            {"countries": iso3_list},
        )
        found = {row["iso3"] for row in result.mappings().all()}
        missing = sorted(set(iso3_list) - found)
        if missing:
            raise AppError(code="NOT_FOUND", message=f"国家不存在：{', '.join(missing)}", status_code=404)

    async def _get_holiday(self, conn: AsyncConnection, holiday_id: str) -> dict:
        result = await conn.execute(
            text("SELECT id, country_iso3, date, name, source, created_at FROM country_holidays WHERE id = :id"),
            {"id": holiday_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="假日不存在", status_code=404)
        return self._serialize_holiday(row)

    def _validate_rule_payload(self, payload: dict) -> None:
        if not payload.get("name") or not payload["name"].strip():
            raise AppError(code="VALIDATION_ERROR", message="规则集名称不能为空", status_code=422)
        work_days = payload.get("work_days") or []
        if not work_days or any(day < 0 or day > 6 for day in work_days):
            raise AppError(code="VALIDATION_ERROR", message="工作日必须在 0-6 范围内", status_code=422)
        segments = payload.get("time_segments") or []
        if not segments:
            raise AppError(code="VALIDATION_ERROR", message="至少需要一个发送时段", status_code=422)
        normalized = []
        for segment in segments:
            start = self._minute_of_day(segment.get("start"))
            end = self._minute_of_day(segment.get("end"))
            if start == end:
                raise AppError(code="VALIDATION_ERROR", message="发送时段开始和结束不能相同", status_code=422)
            normalized.extend(self._expanded_segments(start, end))
        normalized.sort()
        for index in range(1, len(normalized)):
            if normalized[index][0] < normalized[index - 1][1]:
                raise AppError(code="VALIDATION_ERROR", message="发送时段不能重叠", status_code=422)

    def _expanded_segments(self, start: int, end: int) -> list[tuple[int, int]]:
        if start < end:
            return [(start, end)]
        return [(start, 24 * 60), (0, end)]

    def _minute_of_day(self, value: str | None) -> int:
        if not value:
            raise AppError(code="VALIDATION_ERROR", message="发送时段格式错误", status_code=422)
        try:
            parsed = datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise AppError(code="VALIDATION_ERROR", message="发送时段格式必须为 HH:MM", status_code=422) from exc
        return parsed.hour * 60 + parsed.minute

    def _validate_timezone(self, value: str) -> None:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise AppError(code="VALIDATION_ERROR", message="无效的 IANA 时区", status_code=422) from exc

    def _parse_date(self, value: str | date) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    def _serialize_rule_set(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "work_days": list(row["work_days"]),
            "time_segments": row["time_segments"],
            "is_default": row["is_default"],
            "country_count": row.get("country_count", 0),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_country(self, row) -> dict:
        return {
            "iso3": row["iso3"],
            "name_zh": row["name_zh"],
            "name_en": row["name_en"],
            "timezone": row["timezone"],
            "rule_set_id": str(row["rule_set_id"]) if row["rule_set_id"] else None,
            "rule_set_name": row["rule_set_name"],
            "holiday_count": row.get("holiday_count", 0),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_holiday(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "country_iso3": row["country_iso3"],
            "date": row["date"].isoformat(),
            "name": row["name"],
            "source": row["source"],
            "created_at": row["created_at"].isoformat(),
        }

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)
