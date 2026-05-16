# Source Traceability

## 1. Major source decisions

| Final decision | Source input | Repair |
|---|---|---|
| Admin/Tenant API split | 10 API, 11 frontend architecture | Kept and made canonical. |
| Tenant route no slug, API path has slug | 10 API canonical, 11 architecture | Kept. |
| Roles admin/operator/viewer | 07 requirements, 10 API | Kept; platform_admin separated. |
| Platform-level OpenRouter | business-flows V3.2, 07, 13 | Kept; no tenant keys. |
| RLS multi-tenancy | 09 DB, 06 gap | Kept; stricter connection lifecycle added. |
| Dynamic warmup | 07 final requirements | Kept; default 50/100/200/500/1000/4000. |
| Collection via API not MQ | 07 global decision, 12 collection | Kept. |
| AI balance depletion behavior | 07 requirements, 13 AI | Kept; `/ai-capabilities` added. |
| Sending plan only sends | 07 requirements | Kept; old 9-state plan deprecated. |
| Reply visible in system | 07 requirements | Kept but EngageLab inbound remains open question. |

## 2. Conflicts resolved

| Conflict | Resolution |
|---|---|
| business-flows says company name unique; later docs say source ID primary | Use `company_sources(source_type, source_id)` plus domain/name cross-source merge. |
| business-flows mentions self-service recharge; 07 says Phase 1 manual | Phase 1 manual recharge only. |
| warmup fixed date ladder vs dynamic metrics | Dynamic metrics with configurable levels. |
| platform admin role vs tenant enum | `platform_users` separate from tenant `user_roles`. |
| group members by contacts vs business requires company groups | group member uses `tenant_company_id`, optional contact override. |
| partition table unique used for send idempotency | add `email_send_locks`. |
| AI direct charge after call | use preauthorization + settlement. |
| collection service supplied tenant_ids | main system resolves tenants from task-keyword relationship. |

## 3. Original source package

All originals are preserved in `00_original_sources/`.
