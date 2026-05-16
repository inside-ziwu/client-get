from alembic import op

# revision identifiers, used by Alembic.
revision = "20260423_0005"
down_revision = "20260422_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE data_sources DROP CONSTRAINT IF EXISTS data_sources_source_type_check")
    op.execute("ALTER TABLE data_source_credentials DROP CONSTRAINT IF EXISTS data_source_credentials_source_type_check")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE data_sources ADD CONSTRAINT data_sources_source_type_check "
        "CHECK (source_type IN ('waimao_tong','tengdao','lixiaoyun'))"
    )
    op.execute(
        "ALTER TABLE data_source_credentials ADD CONSTRAINT data_source_credentials_source_type_check "
        "CHECK (source_type IN ('waimao_tong','tengdao','lixiaoyun'))"
    )
