"""Slice 2: tenant_contacts.contact_id → clean_contact_id，解除 shared_contacts FK 依赖。

迁移内容：
1. 删除 tenant_contacts.contact_id 上的 UNIQUE 约束和 FK（shared_contacts）
2. 将列值置 NULL（旧 shared_contacts UUID 无法映射到 clean_contacts，因公司 UUID 已在 0014 重建）
3. 重命名 contact_id → clean_contact_id，新增 FK → clean_contacts(id) ON DELETE SET NULL
4. 创建部分 UNIQUE 索引（WHERE clean_contact_id IS NOT NULL）
5. 为 clean_contacts 添加 UNIQUE (clean_company_id, lower(email))，防止重复写入

注：shared_contacts 表本身保留（不删除），代码层不再引用它。

revision: 20260507_0015
down_revision: 20260507_0014
"""

from alembic import op

revision = "20260507_0015"
down_revision = "20260507_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 1. 删除旧 UNIQUE 约束（tenant_id, contact_id）
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_tenant_id_contact_id_key;

        -- 2. 删除旧 FK：contact_id → shared_contacts(id)
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_contact_id_fkey;

        -- 3. 解除 NOT NULL（先 DROP NOT NULL 再清数据，避免临时 FK 冲突）
        ALTER TABLE tenant_contacts
            ALTER COLUMN contact_id DROP NOT NULL;

        -- 4. 清空旧 UUID（shared_contacts UUID 不对应任何 clean_contacts 记录）
        UPDATE tenant_contacts SET contact_id = NULL WHERE contact_id IS NOT NULL;

        -- 5. 重命名列
        ALTER TABLE tenant_contacts RENAME COLUMN contact_id TO clean_contact_id;

        -- 6. 添加新 FK：clean_contact_id → clean_contacts(id)
        ALTER TABLE tenant_contacts
            ADD CONSTRAINT fk_tenant_contacts_clean_contact
            FOREIGN KEY (clean_contact_id) REFERENCES clean_contacts(id) ON DELETE SET NULL;

        -- 7. 部分 UNIQUE 索引（有值时才去重）
        CREATE UNIQUE INDEX uq_tenant_contacts_clean_contact
            ON tenant_contacts(tenant_id, clean_contact_id)
            WHERE clean_contact_id IS NOT NULL;

        -- 8. clean_contacts 去重索引（同公司同邮箱唯一）
        CREATE UNIQUE INDEX uq_clean_contacts_company_email
            ON clean_contacts(clean_company_id, lower(email))
            WHERE email IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP INDEX IF EXISTS uq_clean_contacts_company_email;
        DROP INDEX IF EXISTS uq_tenant_contacts_clean_contact;
        ALTER TABLE tenant_contacts DROP CONSTRAINT IF EXISTS fk_tenant_contacts_clean_contact;
        ALTER TABLE tenant_contacts RENAME COLUMN clean_contact_id TO contact_id;
        -- 注：旧数据已丢失，downgrade 仅恢复结构，不恢复数据
        ALTER TABLE tenant_contacts
            ADD CONSTRAINT tenant_contacts_contact_id_fkey
            FOREIGN KEY (contact_id) REFERENCES shared_contacts(id);
        ALTER TABLE tenant_contacts
            ADD CONSTRAINT tenant_contacts_tenant_id_contact_id_key
            UNIQUE (tenant_id, contact_id);
        """
    )
