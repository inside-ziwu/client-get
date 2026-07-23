"""C6：租户评分维度权重服务。

支持租户对评分模板各维度自定义权重（upsert）。
注意：当前评分引擎并未读取此表——「计算最终分时覆盖默认权重」是设计意图、
尚未接线（2026-07-23 E 节盘点核实，拍板保留待接线，见 schema_notes.md）。
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError


class TenantScoringWeightsService:
    """管理 tenant_scoring_weights 表的 CRUD。"""

    async def list_weights(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        template_id: str | None = None,
    ) -> list[dict]:
        """获取租户自定义权重列表，可按模板过滤。"""
        where = "tenant_id = :tenant_id"
        params: dict = {"tenant_id": tenant_id}
        if template_id:
            where += " AND template_id = :template_id"
            params["template_id"] = template_id

        result = await conn.execute(
            text(
                f"""
                SELECT id, tenant_id, template_id, dimension, weight, updated_at
                FROM tenant_scoring_weights
                WHERE {where}
                ORDER BY template_id, dimension
                """
            ),
            params,
        )
        return [
            {
                "id": str(row["id"]),
                "tenant_id": str(row["tenant_id"]),
                "template_id": str(row["template_id"]),
                "dimension": row["dimension"],
                "weight": float(row["weight"]),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def upsert_weights(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        payload: dict,
    ) -> dict:
        """
        批量 upsert 租户维度权重。

        payload 格式：
        {
            "template_id": "<uuid>",
            "weights": [{"dimension": "company_type", "weight": 1.5}, ...]
        }
        """
        template_id = payload.get("template_id")
        weights = payload.get("weights", [])

        if not template_id:
            raise AppError("VALIDATION_ERROR", "template_id 不能为空")
        if not isinstance(weights, list):
            raise AppError("VALIDATION_ERROR", "weights 必须是列表")

        upserted = []
        for item in weights:
            dimension = item.get("dimension")
            weight = item.get("weight")
            if not dimension:
                raise AppError("VALIDATION_ERROR", "每条权重记录必须含 dimension 字段")
            if weight is None or float(weight) < 0:
                raise AppError("VALIDATION_ERROR", f"维度 {dimension} 的 weight 必须 >= 0")

            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_scoring_weights
                        (tenant_id, template_id, dimension, weight)
                    VALUES (:tenant_id, :template_id, :dimension, :weight)
                    ON CONFLICT (tenant_id, template_id, dimension) DO UPDATE
                        SET weight = EXCLUDED.weight,
                            updated_at = now()
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "template_id": template_id,
                    "dimension": dimension,
                    "weight": float(weight),
                },
            )
            upserted.append(dimension)

        return {
            "template_id": template_id,
            "upserted_count": len(upserted),
            "dimensions": upserted,
        }
