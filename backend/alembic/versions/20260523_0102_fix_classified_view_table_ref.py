"""修正 v_tenant_contact_classified 视图：clean_contacts → waimaotong_clean_contacts。

原视图（20260507_0029）引用已废弃的 clean_contacts 表，
该表在 20260519_0045 被 waimaotong_clean_contacts 取代，但视图未同步更新。

revision: 20260523_0102
down_revision: 20260523_0101
"""

from alembic import op

revision = "20260523_0102"
down_revision = "20260523_0101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP VIEW IF EXISTS v_tenant_contact_classified;

        CREATE VIEW v_tenant_contact_classified AS
        SELECT
            tc.id         AS contact_id,
            cl.id         AS level_id,
            ca.id         AS category_id,
            cl.is_sendable
        FROM waimaotong_clean_contacts tc
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
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP VIEW IF EXISTS v_tenant_contact_classified;

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
        """
    )
