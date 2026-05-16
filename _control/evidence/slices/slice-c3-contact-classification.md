# Slice C3：联系人职位分类（v3-contact-classification）

**状态**: 已完成（本地验证通过）  
**签字日期**: 2026-05-07  
**执行人**: Claude Sonnet 4.6  

---

## 交付物清单

| 编号 | 文件路径 | 状态 |
|------|---------|------|
| 1 | `backend/alembic/versions/20260507_0029_contact_classification_tables.py` | 已创建，DB 验证通过 |
| 2 | `backend/app/services/contact_classification_service.py` | 已创建 |
| 3 | `backend/app/api/admin/contact_classification.py` | 已创建 |
| 4 | `backend/app/api/admin/router.py` | 已注册新 router |
| 5 | `frontend/apps/admin/src/pages/ContactClassification/index.tsx` | 已创建 |
| 6 | `frontend/apps/admin/src/router.tsx` | 已注册路由 `/contact-classification` |
| 7 | `frontend/apps/admin/src/layouts/AdminLayout.tsx` | 已添加侧边栏菜单项 |
| 8 | `frontend/packages/shared-api/src/admin/contact-classification.ts` | 已创建 |
| 9 | `frontend/packages/shared-api/src/admin/index.ts` | 已注册 contactClassification API |
| 10 | `frontend/packages/shared-api/src/index.ts` | 已导出新类型 |
| 11 | `frontend/packages/shared-api/src/query-keys.ts` | 已添加 admin.contactClassification keys |
| 12 | `backend/03_database/schema.sql` | 已追加 3 表 + 1 视图 |

## 清理工作（T-CC-40~46）

| 清理项 | 操作 |
|--------|------|
| `tenant/router.tsx` | 删除 `settings/contact-rules` 路由 |
| `tenant/layouts/TenantLayout.tsx` | 删除侧边栏菜单项 |
| `tenant/pages/Settings/ContactRules/index.tsx` | 删除整个目录 |
| `tenant/pages/Onboarding/index.tsx` | 删除 `StepContactRules` 组件、rulesQuery、STEP_DEFS 第 4 步 |
| `shared-api/src/tenant/contact-rules.ts` | 删除文件 |
| `shared-api/src/tenant/index.ts` | 删除 contactRulesApi 引用 |
| `shared-api/src/index.ts` | 删除 ContactRules/ContactRuleSet 类型导出 |
| `shared-api/src/query-keys.ts` | 删除 contactRules queryKey |
| `backend/app/api/tenant/settings.py` | 删除 GET/PUT contact-rules 端点 |

## 数据库验证

```
position_classification_levels     - 3 行（A/B/X）
position_classification_categories - 3 行（executive/purchasing/invalid）
position_classification_keywords   - 20 行（9+7+4）
v_tenant_contact_classified        - 视图创建成功
```

## 架构说明

- 3 张平台全局表（无租户隔离，平台 admin 统一管理）
- 1 个视图 `v_tenant_contact_classified`，对 `clean_contacts.position` 做 LATERAL 关键词匹配
- classify() 服务方法：按 `sort_order DESC` 优先级匹配，返回最高等级
- Admin 前端：三列布局（等级 → 类别 → 关键词），KISS 原则
- 旧 tenant contact-rules 功能（基于 JSON 规则的选人策略）已全部清理

## 已知限制

- 视图是实时计算，大量数据时建议改为物化视图（V3.2+ 考虑）
- 等级/类别目前无拖拽排序，通过 sort_order 数值控制顺序
