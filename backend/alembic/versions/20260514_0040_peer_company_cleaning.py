"""新增同行公司清洗层（peer_companies + keywords + sources + contacts）。

revision: 20260514_0040
down_revision: 20260511_0039

设计参考: openspec/changes/peer-cleaning-v2/design.md
- D4: 移除冗余 idx_peer_companies_identity（UNIQUE 约束已提供索引）
- D6: peer_company_contacts.raw_company_id REFERENCES lixiaoyun_raw_companies(id)
- D11: email 索引用 lower(trim())，phone 用 COALESCE(phone, '')
"""

from alembic import op

revision = "20260514_0040"
down_revision = "20260511_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE lixiaoyun_raw_companies
            ALTER COLUMN source_id DROP NOT NULL;

        -- ── peer_companies 主表 ──
        CREATE TABLE peer_companies (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          identity_type text NOT NULL CHECK (identity_type IN ('website_host','source_id')),
          identity_value text NOT NULL,
          identity_source text NOT NULL,
          identity_confidence numeric(3,2) NOT NULL DEFAULT 1.00,
          identity_rule_version text NOT NULL DEFAULT 'peer-cleaning-v1',
          merge_reason text,
          name text,
          english_name text,
          domain text,
          website_host text,
          source_id text,
          esdate date,
          legalperson text,
          uncid text,
          reg_capital text,
          employee_scale text,
          reg_address text,
          contact_count int NOT NULL DEFAULT 0,
          conflict_count int NOT NULL DEFAULT 0,
          first_seen_at timestamptz NOT NULL DEFAULT now(),
          last_seen_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (identity_type, identity_value)
        );

        -- D4: 不创建 idx_peer_companies_identity，UNIQUE 约束已提供索引
        CREATE INDEX idx_peer_companies_website_host ON peer_companies(website_host);
        CREATE INDEX idx_peer_companies_source_id ON peer_companies(source_id);
        CREATE INDEX idx_peer_companies_english_name ON peer_companies(english_name);
        CREATE INDEX idx_peer_companies_last_seen_at ON peer_companies(last_seen_at DESC);
        CREATE TRIGGER set_updated_at BEFORE UPDATE ON peer_companies
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

        -- ── peer_company_keywords 关联表 ──
        CREATE TABLE peer_company_keywords (
          id bigserial PRIMARY KEY,
          peer_company_id uuid NOT NULL REFERENCES peer_companies(id) ON DELETE CASCADE,
          keyword_master_id uuid NOT NULL REFERENCES keyword_master(id) ON DELETE CASCADE,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (peer_company_id, keyword_master_id)
        );
        CREATE INDEX idx_peer_company_keywords_keyword_peer
          ON peer_company_keywords(keyword_master_id, peer_company_id);

        -- ── peer_company_sources 来源映射 ──
        CREATE TABLE peer_company_sources (
          id bigserial PRIMARY KEY,
          peer_company_id uuid NOT NULL REFERENCES peer_companies(id) ON DELETE CASCADE,
          raw_company_id bigint NOT NULL REFERENCES lixiaoyun_raw_companies(id) ON DELETE CASCADE,
          source_id text,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (raw_company_id)
        );
        CREATE INDEX idx_peer_company_sources_peer ON peer_company_sources(peer_company_id);
        CREATE INDEX idx_peer_company_sources_source_id ON peer_company_sources(source_id);

        -- ── peer_company_contacts 联系人清洗表（D3 + D6 + D11）──
        CREATE TABLE peer_company_contacts (
          id bigserial PRIMARY KEY,
          peer_company_id uuid NOT NULL REFERENCES peer_companies(id) ON DELETE CASCADE,
          email text,
          name text,
          position text,
          phone text,
          mobile text,
          source_contact_id text,
          raw_company_id bigint REFERENCES lixiaoyun_raw_companies(id),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        -- 三级条件唯一索引（D3 + D11）
        -- 第一级：按 email 去重（规范化 lower(trim())）
        CREATE UNIQUE INDEX idx_pcc_email
          ON peer_company_contacts(peer_company_id, lower(trim(email)))
          WHERE email IS NOT NULL AND trim(email) <> '';

        -- 第二级：无 email 时按 source_contact_id 去重
        CREATE UNIQUE INDEX idx_pcc_source_contact
          ON peer_company_contacts(peer_company_id, source_contact_id)
          WHERE source_contact_id IS NOT NULL AND source_contact_id <> ''
            AND (email IS NULL OR trim(email) = '');

        -- 第三级：无 email 且无 source_contact_id 时按 name+phone 去重
        -- D11: COALESCE(phone, '') 让 NULL phone 参与去重
        CREATE UNIQUE INDEX idx_pcc_name_phone
          ON peer_company_contacts(peer_company_id, name, COALESCE(phone, ''))
          WHERE (email IS NULL OR trim(email) = '')
            AND (source_contact_id IS NULL OR source_contact_id = '');

        CREATE INDEX idx_pcc_peer ON peer_company_contacts(peer_company_id);
        CREATE TRIGGER set_updated_at BEFORE UPDATE ON peer_company_contacts
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP TABLE IF EXISTS peer_company_contacts;
        DROP TABLE IF EXISTS peer_company_sources;
        DROP TABLE IF EXISTS peer_company_keywords;
        DROP TABLE IF EXISTS peer_companies;
        """
    )
