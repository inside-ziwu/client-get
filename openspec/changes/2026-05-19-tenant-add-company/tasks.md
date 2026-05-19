## Tasks

### Phase 1: 后端扩展

- [ ] **T1** `tenant_ops_service.py:164-184` — INSERT INTO `waimaotong_clean_companies` 扩展 5 个字段（phone, employee_size, founded_year, full_address, description），从 `payload.get()` 取值，`founded_year` 做 int 转换

### Phase 2: 前端 — Sheet 表单组件

- [ ] **T2** `companies/add-company-sheet.tsx` — 新增公司 Sheet 组件：分三组表单（基本信息 12 字段 + 联系人可选多行 + 备注），国家下拉复用 `filters()` 数据，员工规模下拉固定选项，产品标签多值输入，提交调 `tenantApi.companies.create()`，成功关闭+刷新列表

### Phase 3: 前端 — 接入列表页

- [ ] **T3** `companies/page.tsx` — PageHeader 右侧加「新增公司」按钮，控制 Sheet open 状态，传入 `onSuccess` 回调 invalidate 列表查询

### Phase 4: 验证

- [ ] **T4** 端到端验证 — 打开列表页 → 点新增公司 → 填写公司名称（必填校验）→ 填可选字段 → 添加联系人 → 提交 → 验证列表刷新且新公司出现 → 点击查看详情确认字段正确
