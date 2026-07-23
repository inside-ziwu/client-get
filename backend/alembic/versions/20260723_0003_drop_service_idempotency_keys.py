"""拆除无调用方的通用幂等设施：service_idempotency_keys（E 节 B1，2026-07-23 拍板）。

revision: 20260723_0003
down_revision: 20260723_0002

考证：InternalIdempotencyService 实现完整但全仓零调用方（发送链路的幂等由
email_send_locks 专表承担）；表内 305 行为历史残留，已 dump 留档
（本地归档 service_idempotency_keys-20260723.sql.gz，行数核验一致）。
服务类文件随同一 PR 删除，需要时 git 历史与留档可完整复活。
"""

from alembic import op

revision = "20260723_0003"
down_revision = "20260723_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    # 不带 IF EXISTS/CASCADE：缺表或有依赖即报错回滚，人工介入
    conn.exec_driver_sql("DROP TABLE public.service_idempotency_keys")


def downgrade() -> None:
    # 定义原样取自 2026-07-23 生产快照
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE public.service_idempotency_keys (
            id uuid NOT NULL,
            service_name character varying(100) NOT NULL,
            request_id character varying(200) NOT NULL,
            endpoint character varying(200) NOT NULL,
            request_hash character varying(128),
            response_status integer,
            response_body jsonb,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (service_name, request_id, endpoint)
        )
        """
    )
