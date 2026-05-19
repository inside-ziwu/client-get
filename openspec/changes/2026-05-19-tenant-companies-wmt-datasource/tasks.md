## 任务分解

依赖关系：T1 → T2/T3 可并行 → T4 → T5 → T6 → T7

---

### T1: Migration — FK 变更 + 索引 + 关联重建

**文件**: `backend/alembic/versions/` (新增)

- [ ] 创建 alembic migration 脚本
- [ ] wmt 表索引补建：`wmt_clean_contacts.sys_company_id`、`wmt_clean_companies.domain`、`wmt_clean_companies(company_name, country_iso3)`
- [ ] 删除 `tenant_companies.clean_company_id` 旧 FK 约束
- [ ] 重建 `tenant_companies` 关联：基于 `clean_companies.name` + `country_iso3` 匹配 `waimaotong_clean_companies` 记录，更新 `clean_company_id`
- [ ] 直接删除未匹配的 `tenant_companies` 记录（Review D3：不做安全网）
- [ ] 清空 `tenant_contacts` 全表（Review D4：不做逐条匹配）
- [ ] 重建 `company_blacklist.shared_company_id` 关联
- [ ] 新建 `tenant_companies.clean_company_id` 索引（不加 FK 约束，避免阻碍 wmt 导入流程）

**验收**: migration up/down 均可执行；`tenant_companies.clean_company_id` 全部指向 `waimaotong_clean_companies.id`

---

### T2: tenant_query_service.py — 读查询全面切换

**文件**: `backend/app/services/tenant_query_service.py`

- [ ] `companies_page()`：JOIN 改为 `waimaotong_clean_companies wc`；SELECT 列映射（见 design 第 2 节）；WHERE 过滤器适配（见 design 第 3 节）；**API 响应 key 必须不变**（Review D5：`company_name` → 返回 `name`）
- [ ] `v3_company_detail()`：JOIN 改为 wmt；SELECT 列映射；`_company_sources()` 替换为 `data_source_tags` 列直接读取；`_matched_tenant_keywords()` 调用移除，返回空列表
- [ ] `v3_company_contacts()`：改为查 `waimaotong_clean_contacts`，通过 `sys_company_id` 子查询关联
- [ ] `prospects()`：JOIN 改为 wmt；过滤器中 `clean_company_sources` 子查询改为 `data_source_tags &&`；`incorporation_date` 改为 `founded_year` 直接比较
- [ ] `_company_sources()`：改为从 wmt 表 `data_source_tags` 读取，或内联到 `v3_company_detail()` 中
- [ ] `_matched_tenant_keywords()`：整个方法标注为废弃或删除，详情返回 `matched_keywords: []`
- [ ] 游标分页 `cc.id < :cursor` 改为 `wc.id < :cursor`

**验收**: 所有 `/api/v1/companies` 读接口返回 wmt 数据；筛选器全部工作；分页正常

---

### T3: tenant_ops_service.py — 写操作全面切换

**文件**: `backend/app/services/tenant_ops_service.py`

- [ ] `create_company()`：目标表改为 `waimaotong_clean_companies`；去重逻辑改为 domain 优先 + name+country 回退（应用层 SELECT-then-INSERT + `pg_advisory_xact_lock` 防并发，Review D2）；`tenant_companies` INSERT 保持不变（`clean_company_id` 指向 wmt id）
- [ ] `_ensure_contact_from_payload()`：写入目标改为 `waimaotong_clean_contacts`；通过 `sys_company_id` 关联；去重约束需确认
- [ ] `get_company()`：JOIN 改为 wmt；SELECT 列映射
- [ ] `company_contacts()`：JOIN 改为 `waimaotong_clean_contacts`
- [ ] `blacklist_company()`：`shared_company_id` 改为取 wmt company id
- [ ] `companies_filters()`：JOIN 改为 wmt
- [ ] `export_companies()`：JOIN 改为 wmt；导出列适配

**验收**: 创建公司写入 wmt 表；导入、黑名单均正常；筛选项和导出返回正确数据

---

### T4: 周边服务适配

**文件**: 多个

- [ ] `tenant_messaging_service.py`：12 处 `clean_companies`/`clean_contacts` 引用全部改为 wmt 表，字段名跟随映射
- [ ] `webhook_service.py`：1 处引用适配
- [ ] `tenant_hard_delete_service.py`：1 处引用适配
- [ ] `keyword_service.py`：2 处引用适配
- [ ] `fan_out.py`：标注 TODO（D8 暂不改造 keyword pipeline）

**验收**: grep 整个 backend 目录，tenant 侧代码不再有 `clean_companies` / `clean_contacts` 的活跃引用（fan_out.py TODO 除外）

---

### T5: 前端适配

**文件**: `frontend/packages/shared-api/src/tenant/companies.ts`、`frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

- [ ] Company 类型更新：确认后端返回字段映射后的 key 名（推荐后端做映射保持兼容）
- [ ] 新增字段按需加入类型定义（`english_name`、`sub_industry`、`description` 等）
- [ ] 公司列表页展示列确认：`grade`、`score`、`domain` 等已有列是否需要调整
- [ ] 筛选器参数确认：`employee_scale[]` 值域、`sources[]` 值域是否因 wmt 数据变化
- [ ] 详情页 `matched_keywords` 空列表兼容处理

**验收**: 列表/详情/筛选器/导出在浏览器中正常工作

---

### T6: 测试适配

**文件**: `backend/tests/test_v3_data_foundation_api_contract.py`

- [ ] 5 个现有 tenant 端测试适配新表结构（含 `test_tenant_company_detail_rejects_invisible_clean_company`）
- [ ] `_seed_visible_company()` fixture 重写：INSERT 改为 `waimaotong_clean_companies`；移除 `clean_company_sources` 和 `clean_company_keywords` 插入
- [ ] 联系人测试 fixture 从 `clean_contacts` 改为 `waimaotong_clean_contacts`（通过 `sys_company_id` 关联）
- [ ] 断言适配：`sources` 从对象数组改为字符串数组；`matched_keywords` 断言改为空列表；filter 参数名更新（`industry_tags` → `sub_industries`，`employee_num` → `employee_scale`，`incorporation_date_from` → `founded_year_from`）；移除 `reg_capital_min`
- [ ] 验证去重逻辑（domain 优先 + name+country 回退 + advisory lock）
- [ ] 验证 `data_source_tags` 来源展示

**验收**: 全部测试通过

---

### T7: 端到端验证

- [ ] 本地启动后端 + 前端，用 wmt 数据验证公司列表页
- [ ] 验证筛选器各项（国家、行业、规模、来源、分数范围、成立年份）
- [ ] 验证公司详情页（字段展示、联系人列表、来源标签）
- [ ] 验证创建公司（去重逻辑、写入 wmt 表）
- [ ] 验证黑名单操作
- [ ] 验证导出
- [ ] 验证潜客列表
- [ ] grep 确认无 `clean_companies` 残留引用（fan_out TODO 除外）

**验收**: 所有功能路径正常，无 clean_companies 活跃依赖
