---
title: "fix: tenant 公司列表中文化与表格轻量优化"
type: fix
status: active
date: 2026-05-21
origin: openspec/changes/2026-05-21-tenant-company-list-ui-polish/
depth: lightweight
---

# fix: tenant 公司列表中文化与表格轻量优化

## Summary

本计划基于当前 OpenSpec change，对 tenant 端公司列表做一次小范围前端修正：国家展示统一中文化，移除电话列，并在不改变现有功能的前提下优化表格可扫读性。实现只触达 tenant 前端页面和共享的公司筛选/国家展示工具，不改后端 API、数据库或 admin 端。

## Requirements

- R1. 国家字段必须向租户端用户展示中文标签，`TUR`、`RUS` 等 ISO3 代码不得裸露在列表中。
- R2. tenant 公司列表必须移除“电话”列，并同步修正空状态列数与表格宽度。
- R3. 公司列表现有筛选、批量选择、详情、群组、拉黑、新增公司和分页能力必须保持不变。
- R4. 复用公司国家展示能力的优选客户页和添加公司弹窗不得继续漏出已知国家代码。
- R5. 页面视觉优化应沿用现有 shadcn/Tailwind 风格，不引入新的设计系统或无关抽象。

## Scope Boundaries

- 不修改后端 API、数据库 schema、数据清洗或采集逻辑。
- 不修改 admin 端页面。
- 不新增依赖，不引入新的国家数据包。
- 不重构整个表格组件体系；只做当前页面需要的轻量整理。
- 不修改 `docs/` 下历史文档。

## Context & Research

### Relevant Code and Patterns

- `frontend/apps/tenant/src/components/company-filters.tsx`：已有 `COUNTRY_ZH`、`countryZh()`、`buildParams()` 和筛选 UI，是国家展示中文化的集中入口。
- `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`：tenant 公司列表主页面，当前表头包含“电话”，行内渲染 `row.phone`，空状态 `colSpan` 按旧列数设置。
- `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`：优选客户群组公司表格当前也有“电话”列，应按公司列表字段口径同步检查。
- `frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`：从公司列表添加弹窗复用 `countryZh()`，表格本身不展示电话列。
- `frontend/apps/tenant/src/app/globals.css` 与 `frontend/packages/shared-ui/src/theme/globals.css`：现有租户端视觉语言是冷静、浅色、数据密集的后台界面，适合小幅增强表格层级而非重做风格。
- `frontend/package.json` 与 `frontend/apps/tenant/package.json`：可用验证包括 `pnpm --filter @apps/tenant type-check`、`pnpm --filter @apps/tenant build`，tenant 开发服务端口为 3001。

### Institutional Learnings

- 未发现与本次纯前端表格/国家标签改造直接相关的 `docs/solutions/` 经验文档。

### External References

- 不需要外部研究。现有代码模式清晰，任务不涉及新框架、外部 API、安全、支付、隐私或持久化数据变更。

## Key Technical Decisions

- 国家中文化集中放在 `countryZh()`：所有已复用该函数的位置自动受益，避免在页面里散落映射逻辑。
- 国家映射采用本地常量扩展：本次只需覆盖常见 ISO3/英文名和截图暴露的缺口，不引入额外依赖，符合 KISS。
- 未识别国家使用中文兜底：面向租户端不再直接显示 `TUR` 这类代码；必要时可显示“未知国家”，避免 UI 中英文/代码混杂。
- 公司列表与优选客户群组表格字段口径保持一致：主列表移除电话列时，复用该字段口径的群组公司列表也同步移除，避免同一用户路径出现两套列表语义。
- 设计优化限定为表格层级与交互状态：使用 sticky 表头、稳定列宽、轻量 hover、紧凑操作区，不引入新组件体系。

## Open Questions

### Resolved During Planning

- 是否需要后端返回中文国家名：不需要。当前前端已有国家展示入口，纯展示问题应在前端完成。
- 是否需要移除共享 API 类型里的 `phone` 字段：不需要。只是不在列表展示，详情或其他页面后续仍可能使用该字段。
- 是否需要完整移动端重构：不需要。本 change 只保证当前后台桌面/宽屏列表不明显错位。

### Deferred to Implementation

- 未知国家兜底是否保留原始值作为 tooltip：实现时根据现有 Tooltip 使用成本决定；默认只显示中文兜底，避免额外复杂度。
- 表格最小宽度的最终数值：实现时根据移除电话列后的截图微调，以不拥挤、不产生无谓横向滚动为准。

## Implementation Units

### U1. 国家中文化入口增强

**Goal:** 让 tenant 公司相关列表使用稳定中文国家标签，覆盖截图中已暴露的 `TUR`、`RUS` 和主要 ISO3 国家代码。

**Requirements:** R1, R4

**Dependencies:** None

**Files:**
- Modify: `frontend/apps/tenant/src/components/company-filters.tsx`
- Test: `frontend/apps/tenant/src/components/company-filters.tsx`

**Approach:**
- 扩展 `COUNTRY_ZH`，补齐主要 ISO3 代码与常见英文国家名，至少包含 `TUR -> 土耳其`、`RUS -> 俄罗斯`。
- 保留现有中文值直出能力，避免“越南”“印度”这类已是中文的值被误判。
- 调整 `countryZh()` 兜底：空值仍为 `-`；未知的短代码/英文值返回中文兜底，而不是直接返回原始代码。
- 国家筛选下拉仍使用原始值作为 `value`，只改变 `label`，确保筛选参数不变。

**Patterns to follow:**
- 现有 `COUNTRY_ZH` 常量和 `countryZh()` 函数模式。
- `CompanyFilters` 中 `countryOpts = ... { label: countryZh(v), value: v }` 的 value/label 分离模式。

**Test scenarios:**
- Happy path: 输入 `TUR`，页面展示为 `土耳其`。
- Happy path: 输入 `RUS`，页面展示为 `俄罗斯`。
- Happy path: 输入 `United States`，页面展示为 `美国`。
- Edge case: 输入空值或 `null`，展示为 `-`。
- Edge case: 输入未知三字母代码，展示中文兜底，不裸露原始代码。
- Integration: 国家筛选选项 label 中文化，但提交的筛选参数仍是原始国家值。

**Verification:**
- tenant 公司列表、优选客户页、添加公司弹窗中已知国家均显示中文。
- TypeScript 检查无新增错误。

---

### U2. 公司列表移除电话列

**Goal:** 从 tenant 公司列表主页面移除电话字段，减少横向拥挤并修正列数相关布局。

**Requirements:** R2, R3

**Dependencies:** U1

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**Approach:**
- 从表头数组删除“电话”。
- 删除行内 `row.phone` 对应单元格。
- 修正空状态 `colSpan`，使其等于当前实际列数。
- 根据列数减少调整表格 `min-w`，让移除电话列后的横向滚动更轻。
- 保持行级 `详情`、`群组`、`拉黑` 操作与批量选择逻辑不变。

**Patterns to follow:**
- 当前页面原生 `<table>` + `Checkbox` + `Button` 的实现方式。
- 当前 `dash()` 空值展示函数。

**Test scenarios:**
- Happy path: 表头不再出现“电话”。
- Happy path: 每行不再渲染电话单元格。
- Happy path: 点击公司名仍打开详情 Drawer。
- Happy path: 勾选公司后批量操作栏仍出现，加入群组入口仍可用。
- Edge case: 空列表或加载中时，空状态横跨完整表格且不发生错位。

**Verification:**
- 公司列表页面视觉检查确认电话列消失。
- 现有筛选、分页、详情、群组、拉黑入口仍可操作。

---

### U3. 相邻公司表格口径同步

**Goal:** 保证优选客户页的群组公司表格与主公司列表字段口径一致，并继续复用中文国家标签。

**Requirements:** R2, R4

**Dependencies:** U1, U2

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`
- Review: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`

**Approach:**
- 从优选客户群组公司表格表头删除“电话”。
- 删除对应 `row.phone` 单元格。
- 修正空状态 `colSpan` 与表格 `min-w`。
- 添加公司弹窗已不展示电话列，只检查其国家展示是否由 U1 覆盖。

**Patterns to follow:**
- `curated-customers/page.tsx` 当前右侧表格与分页结构。
- `add-company-modal.tsx` 当前紧凑表格结构。

**Test scenarios:**
- Happy path: 优选客户页群组公司表格不再出现“电话”列。
- Happy path: 群组公司列表中的 `TUR`、`RUS` 展示为中文。
- Happy path: 从公司列表添加弹窗中的国家选项和表格国家展示为中文。
- Edge case: 群组内暂无公司时，空状态列数正确。

**Verification:**
- 优选客户页和添加弹窗截图检查无电话列回漏、无国家代码回漏。

---

### U4. 表格视觉与交互轻量优化

**Goal:** 在现有设计系统内提升公司列表的可扫读性，不改变信息架构或行为。

**Requirements:** R3, R5

**Dependencies:** U2, U3

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`
- Modify: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`

**Approach:**
- 表头使用 sticky 行，滚动时保持上下文。
- 公司名列保持较高识别度，必要时使用稳定宽度与截断。
- 操作区保持 `详情`、`群组`、`拉黑` 三个动作，但通过紧凑间距、稳定宽度和弱化非危险操作降低视觉噪音。
- 行 hover 使用现有 `muted` 系列颜色，避免新增色彩体系。
- 不引入共享 DataTable 抽象；当前两个页面差异仍然较多，抽象会增加不必要成本。

**Patterns to follow:**
- `frontend/apps/tenant/src/app/globals.css` 的页面间距与标题风格。
- `frontend/packages/shared-ui/src/theme/globals.css` 的色彩 token。
- 现有 `curated-customers/page.tsx` 已使用 sticky 表头的做法。

**Test scenarios:**
- Happy path: 宽屏下表格层级清晰，表头、公司名、操作区易扫描。
- Edge case: 长公司名、长域名、长行业文本不会撑破布局。
- Edge case: 横向滚动时表格内容不重叠，按钮文本不挤压。
- Integration: 视觉优化不改变筛选、分页、详情 Drawer、群组和拉黑状态流。

**Verification:**
- 浏览器截图检查主公司列表、优选客户页、添加公司弹窗。
- 没有明显文本重叠、列错位、按钮溢出。

---

### U5. 验证与 OpenSpec 收尾

**Goal:** 完成本 change 对应的静态验证、视觉验证和任务状态更新。

**Requirements:** R1, R2, R3, R4, R5

**Dependencies:** U1, U2, U3, U4

**Files:**
- Modify: `openspec/changes/2026-05-21-tenant-company-list-ui-polish/tasks.md`

**Approach:**
- 运行 tenant 前端类型检查，优先验证没有 TS 层回归。
- 如依赖或环境允许，运行 tenant build。
- 启动 tenant 前端并用浏览器检查 `/companies`、`/curated-customers` 和添加公司弹窗。
- 将 `tasks.md` 中已完成项勾选。
- 完成汇报按“原始需求 → 已实现/未实现”输出对照。

**Patterns to follow:**
- 当前 `frontend/package.json` 和 `frontend/apps/tenant/package.json` 的脚本约定。
- 本仓库 OpenSpec change 的任务勾选格式。

**Test scenarios:**
- Integration: tenant 类型检查通过。
- Integration: tenant build 通过；若失败，失败原因与本次改动关系明确。
- Manual: 公司列表中截图对应的国家不再显示 `TUR`。
- Manual: 公司列表和优选客户群组表格均无“电话”列。
- Manual: 详情、群组、拉黑、分页等现有入口仍可见且无明显 UI 破损。

**Verification:**
- 验证结果记录在最终汇报中。
- `tasks.md` 状态与实际完成情况一致。

## System-Wide Impact

- **API surface parity:** 不改变 API 请求或响应字段；`phone` 字段仍可存在于类型与详情数据中，只是不在列表展示。
- **State lifecycle risks:** 不改变 React Query key、筛选参数、选择状态或 mutation 流程。
- **UI consistency:** 公司列表和优选客户群组公司表格采用一致字段口径，添加公司弹窗保持紧凑选择场景字段。
- **Unchanged invariants:** tenant 数据权限、群组操作、拉黑操作、详情 Drawer 和新增公司 Sheet 均不在本 change 范围内改变。

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| 国家映射不完整，后续仍出现代码 | 补齐主要国家 ISO3，并用中文兜底阻止原始代码裸露 |
| 兜底隐藏原始值影响排查 | 本次面向租户端展示优先；如需排查可在后续加 tooltip 或详情调试信息 |
| 移除列后表格 `colSpan` 遗漏导致空状态错位 | U2/U3 明确列数同步，视觉验证覆盖空状态 |
| 视觉优化顺手扩大成表格重构 | 明确不抽象 DataTable，不改变数据流和操作流 |

## Documentation / Operational Notes

- 不需要用户文档或运维说明。
- 不需要发布开关或数据库迁移。
- 若最终验证需要真实数据，优先使用本地/远端测试环境；生产同步或上线动作必须由用户另行明确触发。

## Sources & References

- Origin change: `openspec/changes/2026-05-21-tenant-company-list-ui-polish/`
- Related code: `frontend/apps/tenant/src/components/company-filters.tsx`
- Related code: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`
- Related code: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`
- Related code: `frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`
- Related prior plan: `docs/plans/2026-05-19-004-feat-tenant-companies-page-upgrade-plan.md`
- Related prior plan: `docs/plans/2026-05-19-005-feat-curated-customers-page-plan.md`
