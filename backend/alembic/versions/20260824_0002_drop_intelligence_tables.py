"""删除遗留情报模块四表并清理其 AI 场景默认行（行业动态 PR B / B1）。

revision: 20260824_0002
down_revision: 20260824_0001

依据：`.trellis/tasks/08-23-industry-news/prd.md` R5 与 design.md §2 / §6。
遗留情报模块（订阅扇出发布 + 启发式摘要）判定无效，由行业动态
（20260824_0001 新建的三表）整体替换；服务、路由、页面随同一 PR 删除，
需要时 git 历史可完整复活。

生产实况（2026-08-23 只读核对）：
- intelligence_articles / intelligence_subscriptions /
  intelligence_article_publications 均 0 行；
- intelligence_sources 2 行测试数据：Hermes（url `www.baidu.com`，2026-04-23）
  与 vzkoo（url `https://www.vzkoo.com/read/202507211e763a8e8d43a8b9fdb2f279.html`，
  2026-04-25），无业务价值，不留档；
- ai_scene_defaults 中 scene = 'intelligence_summary' 2 行（两实例各一）。
  管理端已隐藏该场景，留着会让被它引用的模型永远删不掉，随本迁移一并删除
  （`scene` 列的 CHECK 枚举与 ai_usage_logs.usage_type 枚举不动）；
- 四表之间唯一 FK 是 publications.subscription_id → subscriptions，
  无外部表引用四表；intelligence_articles 为按 created_at 月度 RANGE 分区表，
  DROP 父表连带 articles_p_2026_04..09 与 intelligence_articles_default；
  三表的 set_updated_at 触发器与 intelligence_sources 的两条 RLS policy 随表消失。

回退事实：本迁移落地后**不可回退到本 revision 之前的镜像**——旧
`app/db/partitions.py` 启动时会对 intelligence_articles 建月分区，表不在即崩；
且生产禁止 downgrade，只能前向修复。

downgrade 仅按 2026-08-23 的 schema_snapshot.json 还原四表结构
（列 / 主键 / 唯一 / 外键 / CHECK / 索引）并重建 intelligence_articles 的
DEFAULT 分区；**不还原** set_updated_at 触发器、RLS policy、历史月分区，
也不还原已删除的 ai_scene_defaults 行。
"""

from alembic import op

revision = "20260824_0002"
down_revision = "20260824_0001"
branch_labels = None
depends_on = None

# 删除顺序：先删引用方（publications → subscriptions），再删被引用方
_TABLES_IN_DROP_ORDER = (
    "intelligence_article_publications",
    "intelligence_subscriptions",
    "intelligence_articles",
    "intelligence_sources",
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    conn.exec_driver_sql(
        "DELETE FROM public.ai_scene_defaults WHERE scene = 'intelligence_summary'"
    )
    # 不带 IF EXISTS/CASCADE：缺表或有依赖即报错回滚，人工介入
    for table in _TABLES_IN_DROP_ORDER:
        conn.exec_driver_sql(f"DROP TABLE public.{table}")


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    # 定义取自 2026-08-23 schema_snapshot.json；约束不显式命名，
    # 由 PostgreSQL 按默认规则生成与快照一致的名称
    conn.exec_driver_sql(
        """
        CREATE TABLE public.intelligence_sources (
            id uuid NOT NULL,
            tenant_id uuid REFERENCES public.tenants(id),
            name character varying(200) NOT NULL,
            source_type character varying(20) NOT NULL
                CHECK (source_type IN ('rss', 'website', 'manual')),
            url text,
            fetch_config jsonb DEFAULT '{"frequency_hours": 24}'::jsonb NOT NULL,
            industry_tags jsonb DEFAULT '[]'::jsonb NOT NULL,
            is_active boolean DEFAULT true NOT NULL,
            last_fetched_at timestamp with time zone,
            error_count integer DEFAULT 0 NOT NULL,
            deleted_at timestamp with time zone,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE public.intelligence_articles (
            id uuid NOT NULL,
            source_id uuid,
            title character varying(500) NOT NULL,
            url text,
            author character varying(200),
            published_at timestamp with time zone,
            content_raw text,
            content_summary text,
            ai_category character varying(100),
            ai_tags jsonb DEFAULT '[]'::jsonb NOT NULL,
            ai_relevance_score numeric(3,2),
            ai_model_id uuid REFERENCES public.ai_models(id),
            ai_usage_log_id uuid REFERENCES public.ai_usage_logs(id),
            status character varying(20) DEFAULT 'pending' NOT NULL
                CHECK (status IN ('pending', 'processed', 'published', 'archived')),
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE public.intelligence_articles_default
            PARTITION OF public.intelligence_articles DEFAULT
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE public.intelligence_subscriptions (
            id uuid NOT NULL,
            tenant_id uuid NOT NULL REFERENCES public.tenants(id),
            user_id uuid NOT NULL REFERENCES public.users(id),
            industry_tags jsonb DEFAULT '[]'::jsonb NOT NULL,
            min_relevance numeric(3,2) DEFAULT 0.5 NOT NULL,
            notify_enabled boolean DEFAULT true NOT NULL,
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            PRIMARY KEY (id)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE public.intelligence_article_publications (
            id uuid NOT NULL,
            tenant_id uuid NOT NULL REFERENCES public.tenants(id),
            article_id uuid NOT NULL,
            article_created_at timestamp with time zone NOT NULL,
            status character varying(20) DEFAULT 'unread' NOT NULL
                CHECK (status IN ('unread', 'read', 'starred', 'archived')),
            has_summary boolean DEFAULT true NOT NULL,
            read_at timestamp with time zone,
            matched_by character varying(30)
                CHECK (matched_by IN ('subscription', 'manual', 'system')),
            subscription_id uuid REFERENCES public.intelligence_subscriptions(id),
            created_at timestamp with time zone DEFAULT now() NOT NULL,
            updated_at timestamp with time zone DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (tenant_id, article_id)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX idx_article_publications_tenant
            ON public.intelligence_article_publications USING btree (tenant_id, status)
        """
    )
