"""联系人职位分类服务。

负责对联系人 position 字段进行规则匹配，返回等级/类别/可发送标志。
同时提供等级树的增删改查方法，供 admin API 调用。
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


class ContactClassificationService:

    async def classify(self, conn: AsyncConnection, position: str | None) -> dict:
        """
        对职位字符串分类，返回 {level_id, category_id, is_sendable}。
        未命中返回 {level_id: None, category_id: None, is_sendable: False}。
        """
        if not position:
            return {"level_id": None, "category_id": None, "is_sendable": False}

        pos_lower = position.lower().strip()

        result = await conn.execute(
            text("""
                SELECT pck.category_id, pcc.level_id, pcl.is_sendable
                FROM position_classification_keywords pck
                JOIN position_classification_categories pcc ON pcc.id = pck.category_id
                JOIN position_classification_levels pcl ON pcl.id = pcc.level_id
                WHERE :pos LIKE '%' || pck.keyword || '%'
                ORDER BY pcl.sort_order DESC
                LIMIT 1
            """),
            {"pos": pos_lower},
        )
        row = result.mappings().first()
        if row:
            return {
                "level_id": str(row["level_id"]),
                "category_id": str(row["category_id"]),
                "is_sendable": row["is_sendable"],
            }
        return {"level_id": None, "category_id": None, "is_sendable": False}

    async def list_levels(self, conn: AsyncConnection) -> list[dict]:
        """返回完整等级树：等级 → 类别 → 关键词列表。"""
        result = await conn.execute(text("""
            SELECT
                l.id,
                l.name,
                l.display_name,
                l.sort_order,
                l.is_sendable,
                l.created_at,
                l.updated_at,
                json_agg(
                    json_build_object(
                        'id',           c.id,
                        'name',         c.name,
                        'display_name', c.display_name,
                        'sort_order',   c.sort_order,
                        'keywords', (
                            SELECT array_agg(k.keyword ORDER BY k.keyword)
                            FROM position_classification_keywords k
                            WHERE k.category_id = c.id
                        ),
                        'keyword_ids', (
                            SELECT json_agg(json_build_object('id', k.id, 'keyword', k.keyword) ORDER BY k.keyword)
                            FROM position_classification_keywords k
                            WHERE k.category_id = c.id
                        )
                    )
                    ORDER BY c.sort_order DESC
                ) FILTER (WHERE c.id IS NOT NULL) AS categories
            FROM position_classification_levels l
            LEFT JOIN position_classification_categories c ON c.level_id = l.id
            GROUP BY l.id
            ORDER BY l.sort_order DESC
        """))
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def create_level(self, conn: AsyncConnection, payload: dict) -> dict:
        """新建等级。"""
        result = await conn.execute(
            text("""
                INSERT INTO position_classification_levels
                    (name, display_name, sort_order, is_sendable)
                VALUES
                    (:name, :display_name, :sort_order, :is_sendable)
                RETURNING id, name, display_name, sort_order, is_sendable, created_at, updated_at
            """),
            {
                "name": payload["name"],
                "display_name": payload["display_name"],
                "sort_order": payload.get("sort_order", 0),
                "is_sendable": payload.get("is_sendable", True),
            },
        )
        return dict(result.mappings().first())

    async def update_level(self, conn: AsyncConnection, level_id: str, payload: dict) -> dict:
        """更新等级（名称、显示名、排序、可发送标志）。"""
        result = await conn.execute(
            text("""
                UPDATE position_classification_levels
                SET
                    name         = COALESCE(:name, name),
                    display_name = COALESCE(:display_name, display_name),
                    sort_order   = COALESCE(:sort_order, sort_order),
                    is_sendable  = COALESCE(:is_sendable, is_sendable),
                    updated_at   = now()
                WHERE id = :id
                RETURNING id, name, display_name, sort_order, is_sendable, created_at, updated_at
            """),
            {
                "id": level_id,
                "name": payload.get("name"),
                "display_name": payload.get("display_name"),
                "sort_order": payload.get("sort_order"),
                "is_sendable": payload.get("is_sendable"),
            },
        )
        row = result.mappings().first()
        if not row:
            raise ValueError(f"等级 {level_id} 不存在")
        return dict(row)

    async def delete_level(self, conn: AsyncConnection, level_id: str) -> None:
        """删除等级（CASCADE 自动删除关联类别和关键词）。"""
        await conn.execute(
            text("DELETE FROM position_classification_levels WHERE id = :id"),
            {"id": level_id},
        )

    async def create_category(self, conn: AsyncConnection, payload: dict) -> dict:
        """新建类别。"""
        result = await conn.execute(
            text("""
                INSERT INTO position_classification_categories
                    (level_id, name, display_name, sort_order)
                VALUES
                    (:level_id, :name, :display_name, :sort_order)
                RETURNING id, level_id, name, display_name, sort_order, created_at, updated_at
            """),
            {
                "level_id": payload["level_id"],
                "name": payload["name"],
                "display_name": payload["display_name"],
                "sort_order": payload.get("sort_order", 0),
            },
        )
        return dict(result.mappings().first())

    async def delete_category(self, conn: AsyncConnection, category_id: str) -> None:
        """删除类别（CASCADE 自动删除关联关键词）。"""
        await conn.execute(
            text("DELETE FROM position_classification_categories WHERE id = :id"),
            {"id": category_id},
        )

    async def add_keywords(self, conn: AsyncConnection, category_id: str, keywords: list[str]) -> list[dict]:
        """批量添加关键词（忽略已存在的，ON CONFLICT DO NOTHING）。"""
        inserted = []
        for kw in keywords:
            kw_clean = kw.strip().lower()
            if not kw_clean:
                continue
            result = await conn.execute(
                text("""
                    INSERT INTO position_classification_keywords (category_id, keyword)
                    VALUES (:category_id, :keyword)
                    ON CONFLICT (category_id, keyword) DO NOTHING
                    RETURNING id, category_id, keyword, created_at
                """),
                {"category_id": category_id, "keyword": kw_clean},
            )
            row = result.mappings().first()
            if row:
                inserted.append(dict(row))
        return inserted

    async def delete_keyword(self, conn: AsyncConnection, keyword_id: str) -> None:
        """删除单个关键词。"""
        await conn.execute(
            text("DELETE FROM position_classification_keywords WHERE id = :id"),
            {"id": keyword_id},
        )
