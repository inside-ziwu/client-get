## Tasks

### Phase 1: 后端 — companies API 加 group_id 支持

- [x] **T1** `tenant_query_service.py` — `companies_page()` 加 `group_id` 可选参数，当传入时 JOIN `group_members` 过滤
- [x] **T2** `ops.py` — `GET /companies` 路由加 `group_id: str | None = Query(None)` 参数，透传给 service

### Phase 2: 前端 — 共享组件抽取

- [x] **T3** 抽取 `CompanyDetail` — 从 `companies/company-detail.tsx` 移到 `components/company-detail.tsx`，`onGroupAdd` 改 optional，原位置 re-export
- [x] **T4** 抽取 `CompanyFilters` — 从 `companies/page.tsx` 提取 FilterValues 类型、筛选 UI、buildParams()、filters API 调用到 `components/company-filters.tsx`
- [x] **T5** `shared-api/src/tenant/companies.ts` — list 参数类型加 `group_id?: string`

### Phase 3: 前端 — 优选客户页

- [x] **T6** 左侧群组面板 — 群组列表 + 选中态 + 新建弹窗 + hover 编辑/删除图标 + 空状态引导
- [x] **T7** 右侧群组公司表格 — 调 companies API（带 group_id）+ 表头字段对齐公司列表 + 分页 + 查看详情 Drawer + 移除确认弹窗
- [x] **T8** 群组编辑弹窗 — 编辑 name + description
- [x] **T9** 群组删除确认弹窗 — 二次确认 + "仅删除群组，不影响公司数据"说明
- [x] **T10** 右侧标题区操作按钮 — 编辑/删除按钮（调 T8/T9 弹窗）

### Phase 4: 前端 — 从公司列表添加弹窗

- [x] **T11** `add-company-modal.tsx` — 弹窗基础结构 + CompanyFilters 筛选区 + 公司列表表格（多选 checkbox）+ 分页
- [x] **T12** 已在群组禁选 — 请求群组内公司 tc_id 集合，匹配的行 checkbox 禁选 + 灰色样式 + "已添加"标记
- [x] **T13** 批量添加 — 选中后调 `groups.batchAddMembers()`，成功后 invalidate 刷新 + 关闭弹窗

### Phase 0: 前置修复

- [x] **T0** `shared-api/src/tenant/groups.ts` — 修复 `batchRemoveMembers` 字段名：`{ member_ids }` → `{ tenant_company_ids }`

### Phase 5: 验证

- [x] **T14** 端到端测试 — 新建群组 → 添加公司 → 查看详情 → 移除 → 编辑群组 → 删除群组
- [x] **T15** 后端集成测试 — `companies_page(group_id=...)` 路径的 pytest 集成测试
