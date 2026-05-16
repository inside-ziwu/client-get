# Phase 1 编码任务拆分

**版本**: v1.0  
**日期**: 2026-04-30  
**对应 Spec**: `docs/spec-collection-module.md` v1.4 §8.1  
**Phase 1 范围**: 外贸通直采 + 腾道反推（Lixiaoyun Stage1 + 腾道 Stage2）+ 清洗（PG Outbox）+ Admin UI

---

## 总览

```
[T-1] base.py + DB Schema   ←─ 所有人等这个
        │
        ├─→ [T-2] 腾道 Provider     ┐
        ├─→ [T-3] 外贸通 Provider    ├─→ [T-5] Worker + 清洗管道  ─→  [T-6] Admin UI
        └─→ [T-4] 励销云改造         ┘
```

**总工时估算（单人串行）**: ~14 天  
**多人并行（2-3 人）**: ~9-10 天（关键路径 = T-1 → 任一 Provider → T-5 → T-6）

---

## T-1: base.py 接口契约 + DB Schema Migration

**依赖**: 无（Phase 1 起点）  
**估时**: 1.5 天  
**可并行**: ❌（其他所有任务都等这个）  
**PR 数**: 建议 2 个 PR

### T-1.A: base.py 接口契约改造

**工作内容**：
- `backend/app/integrations/collection/base.py`：
  - `CollectionTask` 加 `params: dict | None = None`
  - `CollectionTask` 移除 `countries: list[str]`
  - `CollectionPayload` 保留 `companies / contacts / competitors` 三 list（兼容现有 worker）
  - 文档注释说明每条 dict 必须含 `target_table` 字段告诉 Worker 路由
- 新增 `backend/app/core/errors.py` 中 `CredentialExpiredError` 异常类（继承 `AppError`，code=`CREDENTIAL_EXPIRED`，status_code=503）
- 同步更新 `lixiaoyun.py` 中 `AppError(code="CREDENTIAL_EXPIRED")` 改为 `raise CredentialExpiredError(...)` 保持兼容

**验收 checklist**：
- [ ] `pytest backend/tests/integrations/collection/test_base.py` 通过
- [ ] 现有 lixiaoyun.py 单测全绿（接口改造未破坏现有调用）
- [ ] 类型检查 `mypy backend/app/integrations/collection/` 无错误
- [ ] 任意 Provider 可通过 `task.params.get('max_competitors')` 安全读取参数
- [ ] CollectionPayload 各 list 中 dict 缺失 `target_table` 时 Worker 抛 `ValueError`（通过类型守卫，T-5 实现）

**估时**: 0.5 天

---

### T-1.B: DB Schema Migration（big-bang）

**工作内容**：
- 新增 Alembic migration 脚本（一个原子 migration）：
  - **Drop** 旧表：`shared_companies`、`company_sources`、`competitor_companies`
  - **Create** `waimaotong_raw_companies`：含 `collection_type ENUM('direct_search','reverse_lookup')`、`(source_id) UNIQUE`
  - **Create** `tendata_raw_companies`：`tid PRIMARY KEY`、字段贴合 `spec-tendata-provider.md` §2.4
  - **Create** `lixiaoyun_raw_companies`：无 `tenant_id`，`task_id` FK 到 `collection_tasks`、`(source_id) UNIQUE`
  - **Create** `clean_companies`：`UNIQUE(name_normalized, country_iso3)` + `UNIQUE(domain) WHERE domain IS NOT NULL`
  - **Create** `tenant_companies`：`UNIQUE(tenant_id, clean_company_id)`、`matched_keywords TEXT[] DEFAULT '{}'`、GIN 索引 `USING GIN(matched_keywords)`
  - **Create** `cleanup_queue`：`UNIQUE(raw_table, raw_row_id)`、`status ENUM('pending','processing','done','failed')`、部分索引 `WHERE status='pending'`
  - **Alter** `collection_keywords`：移除 `source_types` / `countries`；新增 `subscription_status`、`current_page` / `total_pages` / `today_pages` / `last_run_date` / `daily_page_limit`、`stage1_*` / `stage2_*` 系列字段、`total_companies` / `total_contacts` / `error_msg` / `started_at`
  - **Alter** `data_source_credentials`：新增 `raw_config JSONB DEFAULT '{}'`
- 新增 PG 函数 `normalize_company_name(text) RETURNS text`（按 spec §3.6 算法）
- 新增 Python 工具 `backend/app/utils/country.py`：`to_iso3(name_or_iso2: str) -> str`，使用 `pycountry` 库

**验收 checklist**：
- [ ] `alembic upgrade head` 在空 DB 上成功执行
- [ ] `alembic downgrade -1` 能完整回滚
- [ ] PG 函数 `SELECT normalize_company_name('Filtermation Mfg. Sdn Bhd')` 返回 `'FILTERMATION'`
- [ ] PG 函数对 spec §3.6 列出的 3 个示例输出全部正确
- [ ] `to_iso3('Malaysia')` → `'MYS'`、`to_iso3('IN')` → `'IND'`、`to_iso3('CHN')` → `'CHN'`（透传）
- [ ] 6 张新表创建后 `\d+ tablename` 显示约束符合预期
- [ ] `cleanup_queue` 部分索引 `WHERE status='pending'` 可被 `EXPLAIN` 命中

**估时**: 1 天

---

## T-2: 腾道 Provider 重写

**依赖**: T-1.A（base.py 接口契约）  
**估时**: 3.5 天  
**可并行**: ✅（与 T-3、T-4 并行）  
**PR 数**: 建议 1 个大 PR（7 接口逻辑紧密耦合）

**工作内容**：
- `backend/app/integrations/collection/tendata.py` **完全重写**（删除现有 open-api 实现）
- 实现 7 接口链路（按 `spec-tendata-provider.md` §2.3）：
  - T1 Search → BRIEF → T3 → VOT → STATS → T4-LI / T4-NET / T4-MORE
  - 鉴权：从凭证读取 `token` UUID + `userId` + `JSESSIONID`
  - 两个子域：`data.tendata.cn` + `bizr.tendata.cn`
  - 401 检测路径（HTTP 401 / response `code=401`）→ `raise CredentialExpiredError`
- 字段映射（按 `tendata-field-mapping.md` v1.3 的 15 字段）
- 联系人 3 分支调用 + 按 `email` 去重（按 `spec-tendata-provider.md` §2.5）
- BRIEF 失败时跳过该公司（不入库 raw 表）
- 输出 `CollectionPayload.companies`，每条 dict 含 `target_table='tendata_raw_companies'` + `tid` + 15 字段

**单测**（基于 `docs/research/captures/tengdao_*_response.json`）：
- T1 Search mock → 返回买家列表
- BRIEF mock → 解析出 tid/aliases/website/linkedins
- T3 mock → 解析出 incorporationDate/employeeNum/industryDesc
- VOT mock → 解析 total_sumOfMoney_sum / total_trades_sum
- STATS mock → 解析 exporter.results[]
- T4 三分支 mock → 联系人去重（用 POSIFLOW 真实数据：linkedin+more 同 email 合并 + internet 独立）
- 401 mock → 抛 `CredentialExpiredError`
- BRIEF 失败 mock → 跳过该公司，不抛异常

**验收 checklist**：
- [ ] 用 POSIFLOW RETAIL PRIVATE LIMITED 抓包数据 mock 跑通完整链路，输出 15 个字段
- [ ] 联系人去重：3 分支共 3 条 → 去重后 2 条（POSIFLOW 真实场景）
- [ ] 联系人统一格式 6 字段（姓名/职位/邮箱/重要程度/来源描述/是否验证）正确映射
- [ ] BRIEF 失败时该公司不出现在 payload 中（仅日志记录）
- [ ] 401 触发 `CredentialExpiredError`
- [ ] `target_table` 字段正确为 `tendata_raw_companies`
- [ ] `country_iso3` 字段已转换（如 `MYS` / `IND`）
- [ ] 单测覆盖率 ≥ 80%

**估时**: 3.5 天

---

## T-3: 外贸通 Provider 实现

**依赖**: T-1.A  
**估时**: 2.5 天  
**可并行**: ✅  
**PR 数**: 1 个 PR

**工作内容**：
- `backend/app/integrations/collection/waimaotong.py` 全新实现（当前是 stub）
- 参考 `docs/plan-waimaotong-adapter.md` v2 已完成的接口规划
- 实现 3 接口：
  - SEARCH（关键词分页搜索）
  - DETAIL（每家公司详情）
  - CONTACT（每家公司联系人邮箱）
- 鉴权：Cookie + 签名密钥 + device_id（HMAC-MD5 签名）
- 凭证从 `data_source_credentials.raw_config` 读取（`secret_key` / `device_id`）
- 401 检测：HTTP 401 + 响应体 `success=false` → `CredentialExpiredError`
- 429 检测：HTTP 429 / response `code="429"` → 限流退避
- 输出 `CollectionPayload.companies`，每条 dict 含 `target_table='waimaotong_raw_companies'` + `collection_type='direct_search'` + 字段集
- 输出 `CollectionPayload.contacts`，每条 dict 含 `target_table='shared_contacts'`（注：spec v1.4 待确认 shared_contacts 是否保留，T-5 时定）

**单测**：
- SEARCH mock → 分页正确（含 hasEmail/hasCustomsData/hasDomain 必填）
- DETAIL mock → 字段提取
- CONTACT mock → 邮箱列表
- HMAC 签名计算 → 单测验证签名值
- 401 / 429 错误分类

**验收 checklist**：
- [ ] HMAC 签名算法对原始 repo 测试用例输出一致
- [ ] mock 跑通 SEARCH→DETAIL→CONTACT 三接口
- [ ] 各错误分类正确（401 / 429 / 5xx 各自对应不同行为）
- [ ] `target_table` + `collection_type='direct_search'` 字段正确
- [ ] `country_iso3` 转换正确（外贸通可能返国名/ISO2）
- [ ] 单测覆盖率 ≥ 80%

**估时**: 2.5 天

---

## T-4: 励销云 Provider 改造（R-3 P1 4 项）

**依赖**: T-1.A  
**估时**: 0.5 天  
**可并行**: ✅  
**PR 数**: 1 个 PR

**工作内容**（按 `docs/research/lixiaoyun-r3-review.md` P1 项）：
- `backend/app/integrations/collection/lixiaoyun.py` 改造：
  - **P1-1**: 删除 line 222-223 fallback 逻辑，英文名为空时**原样写入**（`name_en = gs_info.get("entNameEng") or ""`，不 fallback 中文）
  - **P1-2**: `collect()` 增加 `max_competitors` 参数（从 `task.params` 读取，默认 30）；分页累计达到上限即 break
  - **P1-3**: `collect()` 增加 `skip_source_ids: set[str]` 参数（从 `task.params` 读取）；分页结果中 `source_id` 命中即跳过
  - **P1-4**: 输出 `CollectionPayload.competitors`，每条 dict 含 `target_table='lixiaoyun_raw_companies'`、`task_id`（Worker 注入）
- P2-1: `raw_data` dict 抽出独立列字段（`source_id` / `name` / `english_name` / `domain` / `esdate` / `legalperson` / `uncid` / `reg_capital` / `employee_scale` / `reg_address`），其余进 `raw_payload` JSONB
- P2-2: 联系人**仅归档**到 `raw_payload.lx_contacts`，**不写入** `shared_contacts` list

**单测调整**：
- 加 max_competitors 截断测试
- 加 skip_source_ids 跳过测试
- 加英文名为空时输出空字符串（不 fallback）测试

**验收 checklist**：
- [ ] `task.params={'max_competitors': 5}` 时输出最多 5 条
- [ ] `task.params={'skip_source_ids': {'abc','def'}}` 时输出不含这些 ID
- [ ] 英文名为空时 `company_name_en == ""`（不为中文名）
- [ ] payload 中 contacts list 为空（联系人在 competitors[].raw_payload.lx_contacts 内）
- [ ] `target_table='lixiaoyun_raw_companies'` 正确
- [ ] 现有单测全绿

**估时**: 0.5 天

---

## T-5: Worker 路由 + 清洗管道（PG Outbox）

**依赖**: T-2 + T-3 + T-4 全部到位（集成测试需要）  
**估时**: 3 天  
**可并行**: ❌（关键路径）  
**PR 数**: 建议 2-3 个 PR

### T-5.A: Worker submit_result 路由 + cleanup_queue 入队

**工作内容**：
- `backend/app/services/collection_service.py` 中 `submit_result` 函数改造：
  - 按每条 dict 的 `target_table` 字段路由到对应 raw 表
  - 在**单事务**内完成「INSERT raw → INSERT cleanup_queue」
  - 加 `WHERE lease_id = :lease_id` 守护（spec §3.3）
  - 入队语句用 `ON CONFLICT (raw_table, raw_row_id) DO NOTHING` 幂等
- `country_iso3` 字段在写入前调用 `to_iso3()` 转换
- 处理 raw 表的 `source_id` UNIQUE 冲突：直接 `ON CONFLICT DO UPDATE` 更新 `raw_payload` + `last_seen_at`

**验收 checklist**：
- [ ] 同事务原子性：人为制造 cleanup_queue 入队失败 → raw 表也不留行
- [ ] 重复 submit 同一 source_id：raw 表不增行，仅更新；cleanup_queue 不增行
- [ ] `lease_id` 不匹配时 INSERT 失败（lease 守护生效）
- [ ] target_table 缺失时抛 ValueError
- [ ] country 字段写入时已统一为 ISO3

**估时**: 1 天

---

### T-5.B: 清洗服务 worker

**工作内容**：
- 新增 `backend/app/services/cleanup_service.py`：
  - 循环：每 1-2 秒拉一批
  - SQL：`SELECT ... FROM cleanup_queue WHERE status='pending' ORDER BY id LIMIT 100 FOR UPDATE SKIP LOCKED`
  - 标 `status='processing'` → 处理 → 标 `done`/`failed`
  - 处理逻辑：
    - 若 `raw_table='lixiaoyun_raw_companies'` → 直接标 `done`（不进 clean）
    - 否则：UPSERT `clean_companies` + UPSERT `tenant_companies` + array_append `matched_keywords`
  - 失败时：`status='failed'`、`attempts++`、`last_error`
  - 定时任务：每 5 分钟把 `attempts < 3 AND status='failed'` 的行 reset 回 `pending`
- 单实例先跑通；多实例并发等 SKIP LOCKED 自然支持

**UPSERT clean_companies 逻辑**：
```sql
INSERT INTO clean_companies (name_normalized, country_iso3, domain, sources, ...)
VALUES (normalize_company_name(:name), :country, :domain, ARRAY[:source_table], ...)
ON CONFLICT (name_normalized, country_iso3)
DO UPDATE SET
  sources = array_append(clean_companies.sources, EXCLUDED.sources[1])
            FILTER (WHERE NOT clean_companies.sources @> EXCLUDED.sources),
  last_updated = NOW(),
  -- 字段合并策略：domain/website/etc 取非空
  ...;
```

**UPSERT tenant_companies 逻辑**：
```sql
-- 反查该 raw 行关联的所有租户
SELECT tenant_id FROM collection_task_keywords WHERE task_id = :task_id;
-- 对每个租户：
INSERT INTO tenant_companies (tenant_id, clean_company_id, matched_keywords, ...)
VALUES (:tenant_id, :clean_id, ARRAY[:keyword], ...)
ON CONFLICT (tenant_id, clean_company_id)
DO UPDATE SET
  matched_keywords = (
    SELECT ARRAY(SELECT DISTINCT unnest(tenant_companies.matched_keywords || ARRAY[EXCLUDED.matched_keywords[1]]))
  ),
  last_action_at = NOW();
```

**验收 checklist**：
- [ ] 单实例消费 100 条 pending 全部处理
- [ ] 处理失败的行 status='failed' + attempts++
- [ ] attempts >= 3 的失败行不再 reset
- [ ] 励销云 raw 行直接标 done，不进 clean
- [ ] 同公司不同来源（外贸通+腾道）合并为单 clean 行，sources 数组包含两源
- [ ] 多租户共享同关键词：每个租户都有 tenant_companies 行
- [ ] 同租户不同关键词命中同公司：matched_keywords 数组追加，行不重复
- [ ] 重放（手动 reset status=pending）后结果幂等

**估时**: 1.5 天

---

### T-5.C: 集成测试

**工作内容**：
- `backend/tests/integration/test_phase1_e2e.py`：
  - 端到端跑外贸通直采：mock SEARCH/DETAIL/CONTACT → submit_result → cleanup_queue → clean_companies → tenant_companies
  - 端到端跑腾道反推：mock 励销云 Stage1 + 腾道 7 接口 → 同链路
  - 跨天恢复测试：跑到 daily limit 暂停 → 调时间 → 续跑
  - 写竞争测试：lease 失效后旧 worker 不能再写

**验收 checklist**：
- [ ] e2e 测试全绿
- [ ] 跨天恢复测试通过
- [ ] 写竞争测试通过

**估时**: 0.5 天

---

## T-6: Admin UI

**依赖**: T-5 完成  
**估时**: 3 天  
**可并行**: 内部 5 个子页面可并行  
**PR 数**: 5 个小 PR（每个页面一个）

### T-6.A: 凭证录入页（3 套）

**工作内容**：
- Admin 后台新页面 `/admin/data-sources/credentials`
- 三个 tab：外贸通 / 腾道 / 励销云
- 每个 tab 表单：根据 `data_source_credentials` schema 渲染（含 `raw_config` JSONB 编辑器）
- 提交 → 调 Internal API 写入 + 加密

**验收 checklist**：
- [ ] 三套凭证可录入/更新
- [ ] secret 字段加密存储
- [ ] raw_config JSONB 字段可编辑

**估时**: 0.5 天

---

### T-6.B: 关键词列表 + 启动按钮

**工作内容**：
- 新页面 `/admin/collection/keywords`
- 关键词列表（per row）：keyword / status / today/total 进度（直采+反推三路）/ 累计公司数 / 累计联系人数 / last_run_date / error_msg
- 行级操作：启动 / 停止 / 重置 / 重试

**验收 checklist**：
- [ ] 列表加载 < 1 秒（关键词 < 1000）
- [ ] 启动操作触发状态机 not_started → pending
- [ ] 停止/重置/重试操作正确
- [ ] 三路进度字段独立显示

**估时**: 0.5 天

---

### T-6.C: 采集进度页 + 顶部汇总面板

**工作内容**：
- 同页或独立页 `/admin/collection/dashboard`
- 顶部汇总：今日新增公司数 / 今日新增联系人数 / 今日推进的 running 关键词数 / paused / error
- 关键词 timeline / 进度条
- 按字段更新时间渲染（无 SSE/WebSocket）

**验收 checklist**：
- [ ] 顶部汇总数字与 DB 实际计数一致
- [ ] 进度可视化清晰

**估时**: 0.5 天

---

### T-6.D: 数据归档浏览页（3 raw + 1 clean）

**工作内容**：
- 4 个 tab：waimaotong_raw / tendata_raw / lixiaoyun_raw / clean_companies
- 每个 tab：分页列表 + 按 keyword/country/source_id 筛选
- 行点击查看详情（raw_payload JSONB 美化展示）

**验收 checklist**：
- [ ] 4 张表都可浏览
- [ ] 筛选生效
- [ ] raw_payload JSONB 详情可展开查看

**估时**: 1 天

---

### T-6.E: 清洗管道健康页

**工作内容**：
- 新页面 `/admin/collection/cleanup-health`
- 4 个指标面板（按 spec §5.4.1）：
  - cleanup_queue pending 数
  - 最早 pending 时长
  - failed 累积数（attempts >= 3）
  - 每分钟处理量
- 3 个对账差集列表（按 spec §5.4.2 三条 SQL 渲染）
- 报警阈值显示（颜色变红）

**验收 checklist**：
- [ ] 4 个指标实时刷新（按页面 refresh，无需 push）
- [ ] 阈值超限时 UI 报警颜色
- [ ] 3 个对账列表可展开查看具体行
- [ ] 差集 A 在正常情况永远为空（事务原子性证明）

**估时**: 0.5 天

---

## 关键路径与里程碑

| 里程碑 | 完成标志 | 累计天数（关键路径） |
|---|---|---|
| M1 | T-1 完成（base.py + schema） | 1.5 天 |
| M2 | 任意 1 个 Provider 完成（建议腾道，最复杂） | 5 天 |
| M3 | 全部 3 个 Provider 完成 | 5 天（并行）|
| M4 | T-5 集成测试通过 | 8 天 |
| M5 | Phase 1 整体上线（含 Admin UI） | ~11 天 |

**多人并行策略**（理想情况 3 人）：
- 人 A：T-1 → T-5
- 人 B：T-2（腾道）→ T-6.D
- 人 C：T-3（外贸通）→ T-6.B/E
- T-4（励销云）任何空闲时间插入

---

## 风险与缓解

| 风险 | 概率 | 缓解 |
|---|---|---|
| 腾道 Cookie 失效频次未知 | 中 | T-2 实现 401 自动停源 + 通知；运营手动更新 |
| 外贸通签名算法在新版本变更 | 低 | T-3 单测保护；签名错误时 401/403 触发凭证失效流程 |
| 清洗 UPSERT 性能瓶颈 | 低 | 单实例 1-2s/批 100 = 6000/分钟 ≫ 实际写入率 |
| 励销云 entstatus 编码理解错误 | 低 | T-4 时抓包对比 [1] vs [3] 验证 |
| `normalize_company_name()` 白名单不全导致重复 | 中 | T-1 时收集尽可能多的尾部词；后续遇到重复时迭代 |
| Admin UI 跟不上后端进度 | 低 | T-6 5 个子页面独立，可分人并行 |

---

## 不在 Phase 1 范围（明确）

- ❌ 外贸通反推路径（Phase 2 R-2 后做）
- ❌ BASEINFO 采购商 ID 补全（Phase 2）
- ❌ 高级实体匹配（trigram / 向量）
- ❌ Prometheus / Grafana 集成
- ❌ 自动化告警（邮件/IM）
- ❌ 多账号轮换 AccountRotator
- ❌ 历史数据迁移（dev 期 big-bang drop）
