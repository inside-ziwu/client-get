## 1. Backend Raw Contacts API

- [x] 1.1 Extend `list_v3_raw_company_contacts` to support `provider == "tendata"` by querying `tendata_raw_contacts`.
- [x] 1.2 Return payload-light Tendata contact fields: id, raw_company_id, source_contact_id, name, position, email, phone, mobile when available, and created_at.
- [x] 1.3 Preserve existing Lixiaoyun contacts behavior and existing unsupported-provider behavior.
- [x] 1.4 Add or update backend tests for `/api/v1/raw/tendata/companies/{raw_company_id}/contacts`.

## 2. Frontend Tendata Table

- [x] 2.1 Remove Tendata main-table columns `补详情`, `贸易`, and status-column `联系人`.
- [x] 2.2 Remove the hard-coded `采集方式` column that renders `tendata`.
- [x] 2.3 Verify the remaining Tendata table still shows contact count, company identity, country, industry, product tags, scale, trade amount/count, supplier count, keyword, update time, and actions.

## 3. Frontend Tendata Detail Drawer

- [x] 3.1 Load raw contacts when a Tendata raw company detail drawer opens.
- [x] 3.2 Render a contacts table with name, position, email, phone/mobile, and created_at.
- [x] 3.3 Add an empty state for raw companies with zero raw contacts.
- [x] 3.4 Replace the old “raw only returns contact count” copy with copy that distinguishes raw provider contacts from clean/tenant contacts.
- [x] 3.5 Ensure contact loading and table rendering do not affect the raw company list pagination.

## 4. Verification

- [x] 4.1 Run backend test(s) covering Tendata raw contacts API.
- [x] 4.2 Run frontend typecheck/build or the repo-standard admin verification command.
- [x] 4.3 Manually verify `admin/collection/tendata`: hidden columns are gone, `采集方式` is gone, and a raw company with contacts displays contact rows in the drawer.
