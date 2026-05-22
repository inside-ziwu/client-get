## ADDED Requirements

### Requirement: Admin MUST synchronize active platform email templates to matching tenants

The system MUST allow an authenticated platform admin to synchronize one active platform email template to **active** tenants whose industry matches the template industry.

API request:
- Method: `POST`
- Path: `POST /api/admin/config/email-templates/{template_id}/sync`
- Path field: `template_id` string, required
- Body: empty object or omitted

API response:
- `template_id`: string
- `template_name`: string
- `industry`: string
- `target_tenant_count`: number
- `created_count`: number
- `skipped_count`: number
- `created`: array of `{ tenant_id, tenant_name, email_template_id }`
- `skipped`: array of `{ tenant_id, tenant_name, reason }`

#### Scenario: 同步到同行业缺失租户

- **GIVEN** an active platform email template with industry `LED照明`
- **AND** two tenants with `status = 'active'` have industry `LED照明`
- **AND** neither tenant has a non-deleted copy of this platform template
- **WHEN** the platform admin triggers synchronization for the template
- **THEN** the system creates one tenant email template copy for each matching tenant
- **AND** the response reports `target_tenant_count` as `2`, `created_count` as `2`, and `skipped_count` as `0`

#### Scenario: 未启用模板不可同步

- **GIVEN** a platform email template exists but `is_active` is false
- **WHEN** the platform admin triggers synchronization for the template
- **THEN** the system rejects the sync action
- **AND** no tenant email template copy is created

#### Scenario: suspended/archived 租户不参与同步

- **GIVEN** an active platform email template with industry `LED照明`
- **AND** one tenant with `status = 'active'` and one with `status = 'suspended'` both have industry `LED照明`
- **WHEN** the platform admin triggers synchronization for the template
- **THEN** the system only creates a copy for the active tenant
- **AND** the suspended tenant does not appear in `created` or `skipped`

#### Scenario: 软删除的副本不阻止新同步

- **GIVEN** an active platform email template with industry `PCB`
- **AND** a matching active tenant has a tenant email template linked to this platform template but with `deleted_at IS NOT NULL`
- **WHEN** the platform admin triggers synchronization for the template
- **THEN** the system creates a new copy for that tenant
- **AND** the existing soft-deleted copy is not modified

### Requirement: Synchronization MUST be idempotent and preserve tenant copies

The system MUST skip tenants that already have a non-deleted copy linked to the platform template, and MUST NOT update or overwrite existing tenant email template content. Concurrent sync requests MUST NOT create duplicate copies (enforced by partial unique index).

#### Scenario: 已有副本被跳过

- **GIVEN** an active platform email template with industry `PCB`
- **AND** a matching active tenant already has a non-deleted tenant email template whose platform template id points to it
- **WHEN** the platform admin triggers synchronization for the template
- **THEN** the system does not modify the existing tenant email template
- **AND** the response includes that tenant in `skipped` with reason `already_exists`

#### Scenario: 重复同步不会创建重复副本

- **GIVEN** a platform admin has already synchronized an active platform email template to all matching tenants
- **WHEN** the platform admin triggers synchronization for the same template again
- **THEN** the system creates no additional tenant email template copies
- **AND** the response reports all matching tenants as skipped

#### Scenario: 同步写入审计记录

- **GIVEN** an active platform email template
- **WHEN** the platform admin triggers synchronization for the template
- **THEN** the system writes an audit record containing the platform user, template id, and sync summary

### Requirement: Admin UI MUST expose sync action and result summary

The Admin platform email template list MUST provide a synchronization action for each template (direct button, no confirmation dialog) and MUST show the operation result summary after completion.

#### Scenario: 管理员看到同步结果

- **GIVEN** a platform admin is viewing the platform email template list
- **WHEN** the admin clicks the sync button for an active template and the API succeeds
- **THEN** the UI shows a success summary containing the created and skipped counts
- **AND** the template list remains usable without a full page reload

#### Scenario: 同步失败时展示错误

- **GIVEN** a platform admin is viewing the platform email template list
- **WHEN** the admin clicks the sync button and the API returns an error
- **THEN** the UI shows an error message
- **AND** the UI does not claim that tenant copies were created
