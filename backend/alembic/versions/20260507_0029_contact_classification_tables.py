"""联系人职位分类：等级、类别、关键词三张表 + 视图。

迁移内容：
1. 创建 position_classification_levels（等级表，如 A/B/X）
2. 创建 position_classification_categories（类别表，从属于等级）
3. 创建 position_classification_keywords（关键词表，从属于类别）
4. 创建视图 v_tenant_contact_classified（实时分类）
5. 插入初始种子数据（A/B/X 三个等级及 executive 类别关键词）

revision: 20260507_0029
down_revision: 20260507_0016
"""

from alembic import op

revision = "20260507_0029"
down_revision = "20260507_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 1. 等级表：A/B/X 等
        CREATE TABLE position_classification_levels (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name         text NOT NULL,
            display_name text NOT NULL,
            sort_order   int  NOT NULL DEFAULT 0,
            is_sendable  bool NOT NULL DEFAULT true,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now()
        );

        -- 2. 类别表：从属于等级（如 executive、purchasing 等）
        CREATE TABLE position_classification_categories (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            level_id     uuid NOT NULL REFERENCES position_classification_levels(id) ON DELETE CASCADE,
            name         text NOT NULL,
            display_name text NOT NULL,
            sort_order   int  NOT NULL DEFAULT 0,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idx_pos_cat_level ON position_classification_categories(level_id);

        -- 3. 关键词表：从属于类别，用于匹配联系人职位字符串
        CREATE TABLE position_classification_keywords (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            category_id uuid NOT NULL REFERENCES position_classification_categories(id) ON DELETE CASCADE,
            keyword     text NOT NULL,
            created_at  timestamptz NOT NULL DEFAULT now(),
            UNIQUE(category_id, keyword)
        );
        CREATE INDEX idx_pos_kw_cat ON position_classification_keywords(category_id);

        -- 4. 视图：对 clean_contacts 中的 position 字段实时分类
        CREATE VIEW v_tenant_contact_classified AS
        SELECT
            tc.id         AS contact_id,
            cl.id         AS level_id,
            ca.id         AS category_id,
            cl.is_sendable
        FROM clean_contacts tc
        JOIN LATERAL (
            SELECT pck.category_id, pcc.level_id
            FROM position_classification_keywords pck
            JOIN position_classification_categories pcc ON pcc.id = pck.category_id
            WHERE lower(tc.position) LIKE '%%' || pck.keyword || '%%'
            ORDER BY pcc.sort_order DESC
            LIMIT 1
        ) matched ON true
        JOIN position_classification_categories ca ON ca.id = matched.category_id
        JOIN position_classification_levels cl ON cl.id = matched.level_id;

        -- 5. 初始种子数据：三个等级
        INSERT INTO position_classification_levels (name, display_name, sort_order, is_sendable) VALUES
            ('A', 'A级（决策层）', 100, true),
            ('B', 'B级（采购层）', 80,  true),
            ('X', 'X级（不投递）', 10,  false);

        -- A级类别：高管/决策层
        INSERT INTO position_classification_categories (level_id, name, display_name, sort_order)
        SELECT id, 'executive', '高管/决策层', 100
        FROM position_classification_levels WHERE name = 'A';

        -- A级类别：高管的关键词
        INSERT INTO position_classification_keywords (category_id, keyword)
        SELECT c.id, kw
        FROM position_classification_categories c,
             UNNEST(ARRAY['ceo','owner','founder','president','director','总经理','董事','老板','创始人']) AS kw
        WHERE c.name = 'executive';

        -- B级类别：采购/贸易
        INSERT INTO position_classification_categories (level_id, name, display_name, sort_order)
        SELECT id, 'purchasing', '采购/贸易层', 100
        FROM position_classification_levels WHERE name = 'B';

        -- B级类别：采购的关键词
        INSERT INTO position_classification_keywords (category_id, keyword)
        SELECT c.id, kw
        FROM position_classification_categories c,
             UNNEST(ARRAY['buyer','purchasing','procurement','sourcing','采购','贸易','外贸']) AS kw
        WHERE c.name = 'purchasing';

        -- X级类别：无效/不可触达
        INSERT INTO position_classification_categories (level_id, name, display_name, sort_order)
        SELECT id, 'invalid', '无效/不可触达', 100
        FROM position_classification_levels WHERE name = 'X';

        -- X级类别：无效的关键词
        INSERT INTO position_classification_keywords (category_id, keyword)
        SELECT c.id, kw
        FROM position_classification_categories c,
             UNNEST(ARRAY['intern','实习','student','学生']) AS kw
        WHERE c.name = 'invalid';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 降级顺序：先删视图，再按 FK 依赖从子表到父表删除
        DROP VIEW IF EXISTS v_tenant_contact_classified;
        DROP TABLE IF EXISTS position_classification_keywords CASCADE;
        DROP TABLE IF EXISTS position_classification_categories CASCADE;
        DROP TABLE IF EXISTS position_classification_levels CASCADE;
        """
    )
