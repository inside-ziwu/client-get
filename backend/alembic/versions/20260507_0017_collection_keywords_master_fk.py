"""collection_keywords 关联 keyword_master：数据迁移 + 外键建立。

迁移内容：
1. collection_keywords 表新增 keyword_master_id 列（FK → keyword_master）
2. 归一化现有 collection_keywords 数据 → 写入 keyword_master（去重）
3. 更新 collection_keywords.keyword_master_id
4. 将现有 (tenant_id, keyword_master_id) 组合写入 tenant_keyword

revision: 20260507_0017
down_revision: 20260507_0016
"""

from alembic import op

revision = "20260507_0017"
down_revision = "20260507_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 1. 为 collection_keywords 添加 keyword_master_id 外键列（允许 NULL，逐步迁移）
        ALTER TABLE collection_keywords
            ADD COLUMN keyword_master_id uuid REFERENCES keyword_master(id) ON DELETE SET NULL;

        -- 2. 将 collection_keywords 中所有不重复的关键词归一化后写入 keyword_master
        --    与 app.services.keyword_service.normalize_keyword 对齐：小写、标点转空格、压缩空白。
        INSERT INTO keyword_master (keyword, keyword_normalized)
        SELECT DISTINCT ON (
            trim(regexp_replace(
                regexp_replace(lower(trim(keyword)), '[^[:alnum:]_[:space:]一-鿿぀-ゟ゠-ヿ-]', ' ', 'g'),
                '[[:space:]]+', ' ', 'g'
            ))
        )
            keyword,
            trim(regexp_replace(
                regexp_replace(lower(trim(keyword)), '[^[:alnum:]_[:space:]一-鿿぀-ゟ゠-ヿ-]', ' ', 'g'),
                '[[:space:]]+', ' ', 'g'
            )) AS keyword_normalized
        FROM collection_keywords
        WHERE keyword IS NOT NULL AND trim(keyword) != ''
        ORDER BY trim(regexp_replace(
            regexp_replace(lower(trim(keyword)), '[^[:alnum:]_[:space:]一-鿿぀-ゟ゠-ヿ-]', ' ', 'g'),
            '[[:space:]]+', ' ', 'g'
        )), created_at ASC
        ON CONFLICT (keyword_normalized) DO NOTHING;

        -- 3. 回写 collection_keywords.keyword_master_id
        UPDATE collection_keywords ck
        SET keyword_master_id = km.id
        FROM keyword_master km
        WHERE trim(regexp_replace(
            regexp_replace(lower(trim(ck.keyword)), '[^[:alnum:]_[:space:]一-鿿぀-ゟ゠-ヿ-]', ' ', 'g'),
            '[[:space:]]+', ' ', 'g'
        )) = km.keyword_normalized;

        -- 4. 将现有租户-关键词关系写入 tenant_keyword（幂等）
        INSERT INTO tenant_keyword (tenant_id, keyword_master_id)
        SELECT DISTINCT ck.tenant_id, ck.keyword_master_id
        FROM collection_keywords ck
        WHERE ck.keyword_master_id IS NOT NULL
        ON CONFLICT (tenant_id, keyword_master_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 回滚：删除 collection_keywords.keyword_master_id 列
        -- 注：tenant_keyword / keyword_master 中的数据由 0016 downgrade 清理
        ALTER TABLE collection_keywords
            DROP COLUMN IF EXISTS keyword_master_id;
        """
    )
