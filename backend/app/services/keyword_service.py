"""关键词归一化与主表查询服务。"""

import re
import unicodedata

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


def normalize_keyword(raw: str) -> str:
    """将输入文本归一化为标准关键词形式。

    处理步骤：
    1. strip() 去除首尾空白
    2. 全角转半角并 lower() 转小写
    3. 移除非语义分隔符（空格、点、下划线）
    4. 保留可能承载语义的符号，例如 `-` 和 `+`

    Args:
        raw: 原始关键词字符串

    Returns:
        归一化后的字符串
    """
    s = unicodedata.normalize("NFKC", raw).strip().lower()
    s = re.sub(r"[\s._]+", "", s)
    return s


async def lookup_keyword_master(
    conn: AsyncConnection,
    keyword_normalized: str,
) -> dict | None:
    """查询 keyword_master 表，返回命中情况及统计数据。

    Args:
        conn: 异步数据库连接
        keyword_normalized: 已归一化的关键词

    Returns:
        命中时返回 dict:
            {
                "matched": True,
                "keyword_master_id": str,
                "keyword": str,
                "company_count": int,       # 关联 clean_companies 数量
                "tenant_count": int,        # 订阅该关键词的租户数量
            }
        未命中时返回 None
    """
    result = await conn.execute(
        text(
            """
            SELECT
                km.id::text                     AS keyword_master_id,
                km.keyword,
                -- 关联的 clean_companies：通过 collection_keywords 追溯
                COALESCE(
                    (
                        SELECT COUNT(DISTINCT ck.id)
                        FROM collection_keywords ck
                        WHERE ck.keyword_master_id = km.id
                    ), 0
                )                               AS company_count,
                -- 订阅该关键词的租户数量
                COALESCE(
                    (
                        SELECT COUNT(DISTINCT tk.tenant_id)
                        FROM tenant_keyword tk
                        WHERE tk.keyword_master_id = km.id
                    ), 0
                )                               AS tenant_count
            FROM keyword_master km
            WHERE km.keyword_normalized = :kn
            LIMIT 1
            """
        ),
        {"kn": keyword_normalized},
    )
    row = result.mappings().first()
    if row is None:
        return None

    return {
        "matched": True,
        "keyword_master_id": row["keyword_master_id"],
        "keyword": row["keyword"],
        "company_count": int(row["company_count"]),
        "tenant_count": int(row["tenant_count"]),
    }


async def get_or_create_keyword_master(
    conn: AsyncConnection,
    *,
    keyword: str,
    keyword_normalized: str,
) -> str:
    """获取或创建 keyword_master 记录，返回 id（str）。

    幂等：通过 ON CONFLICT DO NOTHING + 二次 SELECT 保证。

    Args:
        conn: 异步数据库连接
        keyword: 原始关键词（展示用）
        keyword_normalized: 归一化后的关键词（唯一键）

    Returns:
        keyword_master.id 的字符串形式
    """
    # 先尝试插入（幂等）
    await conn.execute(
        text(
            """
            INSERT INTO keyword_master (keyword, keyword_normalized)
            VALUES (:keyword, :keyword_normalized)
            ON CONFLICT (keyword_normalized) DO NOTHING
            """
        ),
        {"keyword": keyword, "keyword_normalized": keyword_normalized},
    )
    # 查出 id
    result = await conn.execute(
        text(
            """
            SELECT id::text FROM keyword_master WHERE keyword_normalized = :kn
            """
        ),
        {"kn": keyword_normalized},
    )
    return result.scalar_one()


async def bind_tenant_keyword(
    conn: AsyncConnection,
    *,
    tenant_id: str,
    keyword_master_id: str,
    keyword_raw: str | None = None,
    created_by: str | None = None,
) -> bool:
    """将租户与 keyword_master 绑定（幂等），并恢复已软删订阅。

    Args:
        conn: 异步数据库连接
        tenant_id: 租户 UUID（str）
        keyword_master_id: keyword_master UUID（str）
        keyword_raw: 租户原始输入；为空时使用 keyword_master.keyword
        created_by: 创建人；恢复已删除行时会更新为最近操作人

    Returns:
        True 表示新建了关联，False 表示已有行被恢复或保持不变
    """
    result = await conn.execute(
        text(
            """
            INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, created_by, status)
            SELECT
              :tenant_id,
              :keyword_master_id,
              COALESCE(:keyword_raw, km.keyword),
              :created_by,
              'active'
            FROM keyword_master km
            WHERE km.id = :keyword_master_id
            ON CONFLICT (tenant_id, keyword_master_id) DO NOTHING
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "keyword_master_id": keyword_master_id,
            "keyword_raw": keyword_raw,
            "created_by": created_by,
        },
    )
    if result.first() is not None:
        return True

    await conn.execute(
        text(
            """
            UPDATE tenant_keyword
            SET keyword_raw = COALESCE(:keyword_raw, keyword_raw),
                created_by = COALESCE(:created_by, created_by),
                status = 'active'
            WHERE tenant_id = :tenant_id
              AND keyword_master_id = :keyword_master_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "keyword_master_id": keyword_master_id,
            "keyword_raw": keyword_raw,
            "created_by": created_by,
        },
    )
    return False
