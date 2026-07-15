"""物理删除 T-21 已退役的采集子系统表。

revision: 20260714_0001
down_revision: 20260708_0002

生产库已确认缺少四张 collection 表，因此仅这四张允许 IF EXISTS；
其余表必须严格存在，以便新的结构漂移让迁移整体失败并回滚。
"""

from alembic import op

revision = "20260714_0001"
down_revision = "20260708_0002"
branch_labels = None
depends_on = None

OPTIONAL_TABLES = (
    "collection_task_keywords",
    "collection_tasks",
    "collection_runs",
    "collection_keywords",
)

REQUIRED_TABLES = (
    "data_source_credentials",
    "data_sources",
    "peer_company_contacts",
    "peer_company_sources",
    "peer_company_keywords",
    "peer_companies",
    "clean_company_keywords",
    "clean_company_sources",
    "clean_contacts",
    "clean_companies",
    "tenant_keyword",
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")

    for table in OPTIONAL_TABLES:
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS public.{table}")
    for table in REQUIRED_TABLES:
        conn.exec_driver_sql(f"DROP TABLE public.{table}")


def downgrade() -> None:
    raise RuntimeError("T-21 Phase B 迁移不可逆：请从加密备份恢复或创建前向迁移")
