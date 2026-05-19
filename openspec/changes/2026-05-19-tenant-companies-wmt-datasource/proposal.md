## Why

tenant 端公司列表当前从 `clean_companies` + `tenant_companies` 取数据，admin 端客户数据页面从 `waimaotong_clean_companies` / `waimaotong_clean_contacts` 取数据。两套表完全独立、无关联，导致 tenant 和 admin 看到的客户数据不一致。

需要将 tenant 端数据源切到 `waimaotong_clean_companies` / `waimaotong_clean_contacts`，使两端展示完全相同的客户数据。

## What Changes

- tenant 端所有公司查询（列表、详情、筛选项、导出、**潜客列表**）从 `clean_companies` 切到 `waimaotong_clean_companies`
- tenant 端联系人**读写**全部从 `clean_contacts` 切到 `waimaotong_clean_contacts`（通过 `sys_company_id` 关联）
- `tenant_companies` 桥接表保留，FK 从 `clean_companies.id` 改为指向 `waimaotong_clean_companies.id`，继续承载租户私有状态（score、business_status、note、tags、visibility_status）
- `tenant_contacts` 桥接表保留，FK 从 `clean_contacts.id` / `clean_companies.id` 改为指向 wmt 表
- 写操作（创建公司、批量导入、黑名单）目标表从 `clean_companies` 改为 `waimaotong_clean_companies`
- 创建公司时去重策略从 `(name_normalized, country_iso3) UNIQUE` 改为用 wmt 现有字段（domain 优先，回退 company_name + country）
- `clean_company_sources` 来源追溯不再用于 tenant 端，改用 wmt 表的 `data_source_tags` 字段
- 确认 `wmt_clean_contacts.sys_company_id` 索引存在，不存在则补建
- 公司详情页 `_matched_tenant_keywords` 功能暂时移除（依赖 `clean_company_keywords`，需 fan_out pipeline 统一改造后恢复）
- migration 中重建 `tenant_companies` 关联：基于 `company_name` + `country_iso3` 匹配 wmt 表记录，更新 FK

## Non-Goals

- 不删除 `clean_companies` / `clean_contacts` / `clean_company_sources` 表（admin 端其他功能可能仍在使用）
- 不修改 admin 端的 wmt-clean-companies API 和页面
- 不迁移 `tenant_companies` 已有数据到新 FK（migration 中重建关联，见 D6）
- 允许对 `waimaotong_clean_companies` 添加必要索引/约束（见 D7），但不改动已有列结构
- 不改造 fan_out keyword pipeline（关键词匹配功能本次暂时移除，见 D8）

## Capabilities

### Modified Capabilities

- `tenant-companies-list`: 公司列表数据源切换到 wmt 表
- `tenant-companies-detail`: 公司详情数据源切换到 wmt 表
- `tenant-companies-contacts`: 联系人数据源切换到 wmt 表
- `tenant-companies-filters`: 筛选项数据源切换到 wmt 表
- `tenant-companies-export`: 导出数据源切换到 wmt 表
- `tenant-companies-create`: 写入目标切换到 wmt 表
- `tenant-companies-import`: 批量导入目标切换到 wmt 表
- `tenant-companies-blacklist`: 黑名单操作适配 wmt 表

### New Capabilities

无

## Impact

| 路径 | 变更类型 | 说明 |
|------|---------|------|
| `backend/app/services/tenant_query_service.py` | 重写 | 所有 SQL 从 `clean_companies` 改为 `waimaotong_clean_companies`；包括 companies_page、v3_company_detail、v3_company_contacts、prospects；`_company_sources` 替换为 data_source_tags；`_matched_tenant_keywords` 暂时移除 |
| `backend/app/services/tenant_ops_service.py` | 重写 | 创建/导入/黑名单/筛选项/导出/get_company/company_contacts/_ensure_contact_from_payload 全部改为 wmt 表 |
| `backend/app/services/tenant_messaging_service.py` | 修改 | 12 处 clean_companies/clean_contacts 引用改为 wmt 表 |
| `backend/app/workers/fan_out.py` | 修改 | 5 处 clean_companies 引用，需确认是否在本次范围内（关键词 pipeline 暂不改造则标注 TODO） |
| `backend/app/services/webhook_service.py` | 修改 | 1 处引用适配 |
| `backend/app/services/tenant_hard_delete_service.py` | 修改 | 1 处引用适配 |
| `backend/app/services/keyword_service.py` | 修改 | 2 处引用适配 |
| `backend/alembic/versions/` | 新增 | migration：tenant_companies FK 改指向 wmt 表 + 关联重建；tenant_contacts FK 适配；wmt_clean_contacts.sys_company_id 索引；wmt 表去重约束 |
| `backend/tests/test_v3_data_foundation_api_contract.py` | 修改 | 适配新表结构的 4 个现有测试 |
| `frontend/packages/shared-api/src/tenant/companies.ts` | 修改 | `Company` 类型字段适配 wmt 字段（grade、score 等新增，部分字段名变化） |
| `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` | 修改 | 展示列适配新字段 |

## Risks

1. **字段映射不对齐**：`clean_companies` 和 `waimaotong_clean_companies` 字段名、类型差异大，逐个映射容易遗漏
2. **tenant_companies 关联重建**：现有 `clean_company_id` 全部指向旧表，migration 需基于 name+country 匹配重建（D6），匹配率可能不 100%
3. **wmt 表无 migration 管理**：表由外部流程导入，schema 不受 alembic 控制，写入操作需确认字段兼容性
4. **联系人关联链路变化**：从直接 FK (`clean_company_id`) 变为间接 (`sys_company_id`)，查询需额外一跳
5. **sys_company_id 数据质量**：wmt 表外部导入，`sys_company_id` 可能存在 NULL 或重复值，联系人关联查询需做防御性处理
6. **blacklist 历史数据语义变化**：`company_blacklist.shared_company_id` 现存值指向 clean_companies.id，切换后新值指向 wmt 表 id，现有黑名单条目需随 migration 一并重建
7. **关键词匹配功能暂时缺失**：`_matched_tenant_keywords` 依赖 `clean_company_keywords` 表（fan_out worker 写入），本次移除后需后续统一改造 pipeline 恢复

## Field Mapping Reference

```
clean_companies (旧)             waimaotong_clean_companies (新)
────────────────────             ───────────────────────────────
name                        →    company_name
name_normalized             →    (无直接对应，写入时需处理)
country_iso3                →    country_iso3 (✓ 兼容)
website                     →    website / domain
industry_desc               →    industry
industry_tags (text[])      →    (无，industry 是 text)
product_tags (text[])       →    product_tags (text[]) ✓
employee_num                →    employee_size / company_size
incorporation_date (date)   →    founded_year (int，仅年份)
reg_capital                 →    (无)
trade_amount_3y_usd         →    trade_amount_3y_usd ✓
trade_count                 →    trade_count ✓
contacts_count              →    contacts_count ✓
(无)                        →    grade (wmt 独有)
(无)                        →    score (wmt 独有)
(无)                        →    email_priority (wmt 独有)
(无)                        →    english_name (wmt 独有)
(无)                        →    sub_industry (wmt 独有)
(无)                        →    full_address (wmt 独有)
(无)                        →    description (wmt 独有)
```

## Engineering Review Decisions

D1: 联系人读写也一起切到 wmt_clean_contacts，公司+联系人统一数据源
D2: 创建公司去重用 wmt 现有字段（domain 优先，回退 company_name + country），不加 name_normalized
D3: prospects 查询和 _company_sources 一并改掉，不留残留引用
D4: 实施时确认 wmt_clean_contacts.sys_company_id 索引，不存在则补建
D5: 影响范围扩展到 7 个后端文件（含 tenant_messaging_service、fan_out、webhook_service、tenant_hard_delete_service、keyword_service），一次改完
D6: migration 中重建 tenant_companies 关联（基于 company_name + country_iso3 匹配 wmt 表），而非清空
D7: 允许对 wmt 表添加索引和去重约束（如 domain UNIQUE），Non-Goals 相应调整
D8: 暂时移除 _matched_tenant_keywords 功能，彻底切断 clean_company_keywords 依赖；后续 fan_out pipeline 统一改造后恢复

### Design Review Decisions (第二轮)

D9: create_company 去重用 pg_advisory_xact_lock 防并发（hashtext(domain+name+country)）
D10: migration 中未匹配的 tenant_companies 直接 DELETE，不做安全网
D11: tenant_contacts 全表清空，不做逐条匹配重建
D12: API 响应 key 硬约束不变（company_name → name 等），后端映射，前端零改动
D13: sub_industries 过滤器用精确匹配 `= ANY()`，同时匹配 wc.industry 和 wc.sub_industry 两列（保持双列语义）
D14: tenant_contacts 全表清空的合规风险（退订/退信状态丢失）已知悉，接受风险
D15: advisory lock hash key 不拆分，接受低概率并发风险
