# T-23 列表页设计系统实施进度（2026 Q3）

> 本文件是 T-23（#59）列表页设计系统迁移的**纯执行跟踪文档**：实施计划、批次边界与完成状态全部记录于此，按周更新；T-23 销账后整个文件可归档删除。永久设计契约与五件套组件 API 见 [design-system.md](.trellis/spec/frontend/design-system.md)；本文与代码不符时，以代码 + 测试为准。
>
> 最后更新：2026-07-22。

## 状态速览

| 阶段 | 范围 | 状态 |
| ---- | ---- | ---- |
| Phase A：shared-ui 基建 | token alias、原子层补强、五件套、组件测试 | ✅ 已合并 |
| Gate A | 组件测试 + 双端 type-check/build | ✅ 通过 |
| T-21 合并门 | 采集页删除合并、页面/API 复扫 | ✅ 已合并 |
| Phase B：双页打样 | Tenant companies + Admin email-templates | ✅ 2026-07-15 通过用户走查 |
| 五件套 API 冻结 | 公开契约见 .trellis/spec/frontend/component-guidelines.md「公开 API 冻结」 | ✅ 2026-07-15（组件提交 `38becd5`） |
| Phase C1：简单 Admin（2 页） | intelligence-sources、scoring-templates | ✅ 2026-07-15 完成，走查通过 |
| Phase C2：简单 Tenant（3 页） | intelligence、settings/team、templates | ✅ 2026-07-15 完成，人工 Gate 通过 |
| Phase C3：交互配置与发送计划（4 页） | ai-config、warmup-rules、work-schedule、send-plans + page-kit DataTable 清理 | ⬜ 未启动（前置：C2 已合并） |
| Phase C4：宽表与复杂筛选（5 页） | 四个 collection 页 + curated-customers | ⬜ 未启动 |
| Phase C5：tenants 巨型页（1 页） | admin `/tenants` 拆 Tab 迁移 | ⬜ 未启动 |
| 最终验收与销账 | 全仓 grep 门禁、`status` → `active`、#59 关闭 | ⬜ 未启动 |

[design-system.md](.trellis/spec/frontend/design-system.md) frontmatter 的 `status` 当前为 `adopting`：新建或迁移的列表页必须遵守设计契约，存量页面仍按下方批次分批迁移，不能只改全局颜色后宣称完成。C5 与最终验收完成后 `status` 调整为 `active`。

## 当前实现与目标的边界

> 自设计系统文件（原 DESIGN.md）Overview 迁入。「当前实现」指尚未迁移页面的存量形态，随 C3–C5 推进逐步消失。

| 维度     | 当前实现                        | T-23 目标                              |
| -------- | ------------------------------- | -------------------------------------- |
| 页面底色 | `bg-background` 为浅灰          | 白画布，浅灰仅用于筛选栏、表头与弱分层 |
| 主操作   | 深蓝 `primary`                  | 近黑 `#111111`，彩色不用于主 CTA       |
| 圆角     | 全局基准 8px                    | 控件 8px、内容容器 12px，分层定义      |
| 列表组件 | 原子 Table + app 内手写列表     | shared-ui Pattern 五件套               |
| 暗色模式 | preset 声明 class，实际无 token | 本期不声明支持暗色模式                 |

## 迭代顺序

> 自设计系统文件（原 DESIGN.md）Iteration Guide 迁入。

1. Phase A 先新增目标 token/alias 和五件套，不重映射现有 `background`、`primary` 等全局语义变量，也不迁业务页；为纯组件状态建立 Vitest。
2. Phase B 只迁 tenant companies 与 admin email-templates，进行桌面/移动端用户走查。
3. 根据打样反馈冻结 API；组件 API 未冻结前不批量迁页。
4. Phase C 按“简单 Admin → 简单 Tenant → 宽表 → tenants 巨型页”分批迁移，每批独立验证。
5. tenants 页迁移时按 Tab 拆分 984 行组件，并移除 query data 拷贝进 local state 的反模式；不改变行为。
6. 每批检查：无新增 raw `<table>`、无手写分页、无页面级任意列宽、无 `space-y-*` 与 ListPage gap 叠加。

## Auto Plan

本计划于 2026-07-14 基于设计提交 `63cbae8` 和 `origin/main@72deaa0` 生成，是实施顺序与验收边界；各阶段最新完成状态以上方「状态速览」为准。

### 交付拓扑

```text
设计/计划分支合并
        │
        ▼
Phase A：shared-ui 纯新增基建 ─────────────┐
        │                                  │
        ▼                                  │
Gate A：组件测试 + 双端构建                 │
                                           ├─► Phase B：双页打样
T-21 合并 ─► rebase ─► 页面/API 复扫 ──────┘          │
                                                      ▼
                                            用户走查 + API 冻结
                                                      │
                    ├───────────┬──────────────────────┤
                    ▼           ▼                      ▼
                   C1          C2                     C4
                                 │                      │
                                 ▼                      │
                                C3                      │
                    └────────────┴──────────┬───────────┘
                                                      ▼
                                             C5：tenants 巨型页
                                                      │
                                                      ▼
                                           全仓验收 + T-23 销账
```

分支与 PR 建议：

| 交付             | 分支                           | 合并前提                         |
| ---------------- | ------------------------------ | -------------------------------- |
| 设计与 auto-plan | `docs/t23-list-design-system`  | DESIGN lint 通过、用户确认       |
| Phase A          | `feat/t23-list-patterns`       | 设计分支已合并                   |
| Phase B          | `feat/t23-list-pilots`         | Phase A 与 T-21 均已合并         |
| Phase C1–C5      | 每批一个 `refactor/t23-*` 分支 | Phase B 走查通过；C3 额外等待 C2 |

不在一个长期分支同时堆积组件、两个打样页和十五个存量页面；每个 PR 必须能独立回滚。

### Phase A：shared-ui Pattern 基建（✅ 已合并）

范围只允许 `frontend/packages/shared-ui`。不修改任何 app 页面，不修改旧 `--background`、`--primary`、`--ring` 等全局语义变量，不新增表格引擎依赖。

#### A0 · 基线与 token alias

修改：

- `src/theme/globals.css`：追加 `--ui-*` 目标变量，覆盖 canvas、surface、border、语义 tone、radius、spacing 和三档列宽；旧变量保持原值。
- `src/theme/tailwind-preset.ts`：追加静态 `ui-*` color、typography、radius、column width alias；保留旧映射。

约束：

- Phase A 只是 additive alias，不能让尚未迁移的页面提前变成白底黑按钮。
- DataTable 列宽使用静态 class map；禁止模板拼接 Tailwind class。
- `DESIGN.md`（现 `.trellis/spec/frontend/design-system.md`）继续保持 `status: proposed`。

#### A1 · 原子层补强

修改：

- `src/components/badge.tsx`：保留 legacy variant，新增 neutral/success/warning/info/danger tone，并导出公共 tone 类型。
- `src/components/alert-dialog.tsx`：AlertDialogAction 新增 `variant="destructive"`，默认行为不变。
- `src/components/multi-select.tsx`：接受 readonly value/options，增加 disabled；FilterBar 使用时固定 `allowCreate=false`。

实现前必须先决定 Badge 的类型形态：tone 与 legacy variant 应互斥，避免同一 Badge 同时收到两套视觉意图。

#### A2 · 五件套实现顺序

新增并从 `src/index.ts` 根入口导出：

1. `src/components/list-page.tsx`
2. `src/components/table-state.tsx`
3. `src/components/pagination.tsx`
4. `src/components/filter-bar.tsx`
5. `src/components/data-table.tsx`

依赖规则：

- TableState 先于 DataTable；Badge、Switch、Checkbox、Tooltip 先于类型列渲染。
- DataTable 自己拥有唯一 scroll shell 和原生语义 table；不复用当前自带 wrapper 的 `Table`，避免双边框与双滚动。
- 首版只允许一个 actions 列；发现多个 actions 列时立即给出明确错误。
- FilterBar 不接请求、不构造 API params；option error/retry 先由业务包装层表达，打样后再决定是否进入公共 API。
- `FilterDraft = Record<string, ...>` 先做最小 TypeScript compile spike；若具体对象类型不满足约束，应修订为映射/自引用约束并同步本文件，禁止用 `any` 绕过。
- Pagination 的 Enter + blur 必须去重；DataTable 的全选必须排除 disabled rows。
- 文本 Tooltip 只应在实际 overflow 时进入键盘序列；如需 ResizeObserver，测试中显式 mock。

#### A3 · 自动测试

新增：

- `test/list-page.test.tsx`
- `test/table-state.test.tsx`
- `test/pagination.test.tsx`
- `test/filter-bar.test.tsx`
- `test/data-table.test.tsx`
- `test/primitives.test.tsx`

覆盖：

- loading / empty / filtered-empty / error / retry。
- total / unknownTotal 分页、pageSize 原子更新、跳页 clamp 与 Enter/blur 去重。
- draft/applied 提交边界、reset 单次触发、advanced fields、异步选项状态。
- 五类列默认值、`render > format > default`、status fallback、boolean aria、sticky、selection disabled/indeterminate。
- Badge 新 tone 与旧 variant 回归、destructive AlertDialogAction、readonly/disabled MultiSelect。

不新增 `user-event` 或其他测试依赖，沿用现有 Testing Library + `fireEvent`。

#### Gate A（✅ 通过）

在 `frontend` 目录执行：

```bash
pnpm install --frozen-lockfile
pnpm --filter @shared/ui test
pnpm --filter @shared/ui type-check
pnpm type-check
pnpm build:admin
pnpm build:tenant
```

当前独立 worktree 没有 node_modules，安装依赖是验证前置，不是代码变更。`pnpm lint` 当前为失效脚本（T-10），不得伪装成通过门禁。

Gate A 还要求：app 目录零改动、锁文件零改动、旧 shared-ui 消费者视觉行为不变。

### T-21 合并门（✅ 已完成）

Phase B 开始前必须：

1. T-21 合并进 main。
2. Phase B 分支 rebase 最新 main。
3. 确认 `/collection-tasks`、`/data-sources`、`/settings/keywords` 已删除。
4. 重新扫描保留的 collection 浏览页、raw table、本地 DataTable 和手写分页。
5. 只根据合并后的代码调整 Phase C 清单，不恢复 T-21 删除的页面或类型。

复扫命令：

```bash
rg -l -g '*.tsx' '<table|<Table[ >]|<DataTable|上一页|下一页' \
  frontend/apps/admin/src frontend/apps/tenant/src | sort

rg -n "from '@/components/pages/page-kit'" \
  frontend/apps/tenant/src -g '*.tsx'

rg -n 'adminApi\.collection\.|Lixiaoyun|Waimaotong|WmtClean' \
  frontend/apps/admin/src/app/\(dashboard\)/collection
```

### Phase B：双页打样（✅ 2026-07-15 通过走查并冻结 API）

#### B0 · 独立 preflight 缺陷

代码盘点发现两项既有功能缺陷：

- Admin 邮件模板的 `bodyHtml/bodyText` 没有在打开创建/编辑时同步初始化；不编辑正文直接保存可能提交空正文，预览也可能读取旧 `form.body_html`。
- Company contacts API 当前返回 `Record<string, unknown>`，详情页读取 `title`，而实际字段使用 `position`。

这两项不藏进视觉重构 diff。实施前先复现；确认后各自用独立 fix commit/PR 修复并补相应回归验证。T-23 的打样提交只在修复后的基线上迁 UI。

同样不得顺手吸收：T-17 query-key 全量收敛、T-12 Admin Vitest 基建、T-11 shared types 生成化。SSR 与 client 现有 query key 已一致时保持不动。

#### B1 · Tenant companies

主要文件：

- `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`
- 新增同目录 `company-list-filter-bar.tsx`
- 可选拆分同目录 `company-list-columns.tsx`
- `frontend/apps/tenant/src/components/company-detail.tsx`

迁移内容：

- 用 ListPage、FilterBar、DataTable、TableState、Pagination 替换页面壳、raw table 和手写分页。
- 业务包装层复用现有 `FilterValues`、`EMPTY_FILTERS`、`buildParams`、`countryZh`；暂不改 `components/company-filters.tsx` 的现有 UI，因为 curated-customers 仍在消费。
- 保留现有 16 个业务筛选字段、默认 pageSize=50 和 `[20, 50, 100, 500, 1000]`；进口额、进口次数、联系人、成立年份的起止字段分别合并为 4 个一体式范围控件，界面共呈现 12 个业务控件，底层参数不变。
- 16 个条件属于高频业务筛选，全部常驻；FilterBar 使用 compact 语义宽度自动换行，不使用四等分拉伸，也不提供“更多条件”折叠。关键词为 224px；国家、细分行业、产品标签、采集类型、群组状态、大模型评级、模板评级为 160px；范围控件为 256px。移动端全部全宽，范围内部两端始终并排。
- 公司列表长文本列左对齐；国家、采集类型、员工规模、成立、两种评级与评分、联系人数、入库时间和操作列居中。操作列使用 `medium=144px`，内部以 14px/500、32px 高的轻量文字按钮常驻展示“详情 / 群组 / 拉黑”；拉黑默认中性、hover/focus 显示 danger 色，仍经二次确认。按钮组必须居中，不能只给单元格设置 `text-center` 后仍保留 `justify-end`。
- “重置 / 查询”参与筛选区同一换行流并跟随最后一个条件；1920px 主工作区中基础条件占第一排，范围条件与操作按钮占第二排。
- 未选择统一显示“不限”；multiSelect 弹层分别使用“搜索国家 / 搜索细分行业 / 搜索产品标签 / 搜索评级”。远程选项加载中允许打开查看状态，空数组显示“暂无可选项”。
- 父页分持 draft/applied；submit/reset/pageSize/page change 原子更新页码并清空 selection。
- 保留 selection + 17 个数据列、详情 Sheet、新增公司、群组与拉黑能力；selection key 统一使用 `tc_id`，详情请求继续使用业务需要的 `id`。
- 拉黑改为每行 inline AlertDialogTrigger；destructive pending 时禁止重复提交与关闭。
- 初始 loading、保留旧行的 refetch、首次 empty、filtered-empty、error/retry 分开呈现。
- 公司详情中的联系人 raw table 一并迁为嵌套 DataTable，`stickyHeader=false`、`stickyActions=false`。
- 新增 `frontend/apps/tenant/test/companies/companies-page.test.tsx`，覆盖 draft/applied、reset、分页原子更新、selection 清空与 TableState；公司详情联系人状态沿用同目录既有 `company-detail.test.tsx` 覆盖。

不改变 collection_type、API 参数、群组写入、blacklist 或联系人编辑语义。

#### B2 · Admin email-templates

主要文件：

- `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/email-templates/page.tsx` 仅核对 SSR/client query key，不为“统一风格”改写服务器预取。

迁移内容：

- 用 ListPage、DataTable、TableState 替换页面壳和 raw table；API 当前返回全量，本页不新增 Pagination。
- 保留 7 列、变量最多显示 3 个、只读状态 Badge、日期、CRUD、富文本、变量插入和预览。
- 操作列使用 `medium=144px`，表头、单元格和内部按钮组全部居中；编辑、删除均使用与 Tenant 公司列表一致的 14px/500、32px 高文字按钮，不使用图标。删除默认中性、hover/focus 显示 danger 色。
- 每行删除使用 inline AlertDialog，标题含模板名，destructive pending 防重复；失败不伪装成功。
- query 初载、empty、error/retry 和 refetch 分开；不借迁移改 endpoint、payload 或业务校验。

#### Gate B：打样走查与 API 冻结（✅ 已通过）

自动验证：

```bash
# cwd: frontend/
pnpm --filter @shared/ui test
pnpm --filter @apps/tenant test
pnpm type-check
pnpm build:admin
pnpm build:tenant

# cwd: 仓库根目录
npx @google/design.md lint DESIGN.md
```

不为 T-23 单独搭建 Admin Vitest；Admin 页面以 shared-ui 测试、type-check、build 和人工走查覆盖，完整测试基建仍归 T-12。

人工走查使用 390 / 768 / 1440 三档视口，覆盖：

- 单一横向滚动、sticky header/action、筛选常驻/折叠配置、紧凑控件宽度、分页移动端换行。
- 键盘 focus、Enter 查询/跳页、Space 操作、Tooltip 和 `aria-busy`。
- initial loading、旧行 refetch、首次空、筛选空、断网重试、慢请求、mutation 连点。
- companies 的新增/详情/群组/拉黑/编辑；email templates 的创建/编辑/删除/富文本/变量/预览。

Gate B 已于 2026-07-15 通过：

1. 五件套 public API 已冻结，冻结面见 [component-guidelines.md](.trellis/spec/frontend/component-guidelines.md) Components 章节。
2. 设计系统文件 `status` 已从 `proposed` 调整为 `adopting`，表示新页面必须遵守但存量仍在迁移。
3. Phase C 可以开始；每批仍须按本节回归门槛独立验证。

### 打样与迁移边界

> 自设计系统文件（原 DESIGN.md）Components 迁入。

Phase B 固定打样两页：

1. **Tenant companies**：验证复杂 FilterBar、18 列宽表、selection、批量栏、sticky header/actions、详情 Sheet 和完整 Pagination。
2. **Admin email-templates**：验证简单列表、只读状态、变量标签、日期、行内编辑/删除和 TableState。

不选择 scoring-templates 作为首个 Admin 打样，因为它当前把输入值直接放进 queryKey，点击“查询”的交互语义不真实；可在后续迁移中用来验证 draft/applied 修正。

T-21 合并前，T-23 不迁移以下文件：

- Admin `/collection-tasks` 与 `/data-sources`：T-21 将整页删除。
- Admin dashboard redirect 与导航：T-21 将修改入口和“采集”分组。
- Tenant `/settings/keywords` 与 onboarding 相关文案：T-21 将删除或改写。

现有 `frontend/apps/tenant/src/components/pages/page-kit.tsx` 的本地 `DataTable` 不作为新 API 基础。Phase C 迁移其消费者后删除本地 DataTable export；其中 PageHeader 仍被新建、编辑和详情页使用，应保留或单独拆文件，不能随列表迁移误删。列表页头部由 ListPage 承载，禁止长期并存两个同名 DataTable。

T-21 合并后必须重新扫描页面数量、手写 `<table>`、分页复制点和保留的 collection 浏览页，再锁定 Phase C 清单。

### Phase C：存量迁移批次（进行中：C1、C2 已完成）

以下是 T-21 合并前的 provisional 基线：20 个 route-level 列表页中，T-21 删除 3 页、Phase B 迁 2 页，Phase C 剩 15 页。T-21 合并后的复扫结果优先于此数字。

终验中的“手写表格清零”专指 app 内原生小写 `<table>`。非列表详情页和向导中已经使用 shared-ui 原子 `<Table>` 的小型展示表可以保留，例如 work-schedule 的 country/rule-set 详情和 send-plan wizard；它们不属于五件套列表页，也不计入 raw table 门禁。

#### C1 · 简单 Admin（2 页）（✅ 已完成）

- `frontend/apps/admin/src/app/(dashboard)/intelligence-sources/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/scoring-templates/client-page.tsx`

重点：CRUD 状态、inline delete、query data 镜像清理；scoring-templates 把 industry 明确拆成 draft/applied，使“查询”恢复真实语义，但不改 API。

状态（2026-07-15）：两页已迁移至 ListPage/DataTable/FilterBar/TableState，清除原生 `<table>` 与 query data 镜像；列表状态统一为可操作 Switch，新增/编辑/删除与批量导入具备 pending 防重复；scoring-templates 的行业筛选已拆为 draft/applied。A 实例真实页面走查与 production build 已通过，T-23 仍待 C2–C5 和最终全仓门禁后销账。

#### C2 · 简单 Tenant（3 页）（✅ 已完成）

- `frontend/apps/tenant/src/app/(dashboard)/intelligence/page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

重点：替换 app-local DataTable；保留 templates 双 Tab 和 mutation、team 当前账号保护与状态 pending；所有行提供稳定 getRowId。

状态（2026-07-15）：三页已迁移至 ListPage/DataTable/TableState，保留 templates 双 Tab、编辑器与全部 mutation，team 当前账号保护和行级状态 pending；team 新增成员操作框使用控件宽度契约：姓名/角色 `small`、邮箱 `medium`，列表本身保持姓名 `medium`、邮箱 `large`。所有表格均使用稳定 getRowId；Tenant 17 个测试文件共 56 项测试、A 实例只读页面走查与用户人工 Gate 均已通过。平台模板“预览”误调用复制接口的既存行为已独立登记 T-28，不纳入本次纯列表迁移。

#### C3 · 交互配置与发送计划（4 页）（⬜ 未启动）

- `frontend/apps/admin/src/app/(dashboard)/ai-config/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/warmup-rules/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/work-schedule/client-page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`
- 关联：`frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`
- 清理：`frontend/apps/tenant/src/components/pages/page-kit.tsx` 的 DataTable export

重点：ListPage 只承载列表区域，不吞并同页编辑器；配置表通过 column render 保留输入行为；send-plans 用显式详情链接替代整行点击。C3 必须在 C2 合并后执行；确认 C2 已迁完 intelligence/team/templates、T-21 已删除 keywords、send-plan 详情也完成迁移后，才能删除本地 DataTable export。PageHeader/SearchBar 保留。

#### C4 · 宽表与复杂筛选（5 页）（⬜ 未启动）

- `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/collection/peers-cleaned/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/collection/peers/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`
- 关联：`frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`

重点：四个 collection 页的接口与类型必须以 T-21 合并后代码为准；筛选、宽表、分页、详情 Sheet 和嵌套表逐页保真。curated-customers 同时覆盖群组侧栏、群组 CRUD、添加公司弹窗与公司详情。

#### C5 · tenants 巨型页（1 页）（⬜ 未启动）

- `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx`

拆分基础信息、域名、团队、OpenRouter 四个 Tab 子组件；主列表与域名/团队嵌套表迁入五件套；移除租户列表的 query data → local state 镜像。搜索使用 draft/applied。详情加载方式和 query key 不在本批顺手现代化，保留创建、状态、删除、域名和团队 CRUD 行为。

不设置机械行数门槛，但主文件应显著缩小且每个 Tab 能独立阅读和测试。

#### 每批验证

```bash
# cwd: frontend/
pnpm --filter @shared/ui test
pnpm --filter @apps/tenant test
pnpm type-check
pnpm build:admin
pnpm build:tenant

# cwd: 仓库根目录（也可在子目录执行）
git diff --check
```

每批只走查本批页面及共享组件回归；C4 额外走查横向滚动与 sticky action，C5 额外走查全部 Tab 与 CRUD。

### 最终验收与销账

```bash
# cwd: 仓库根目录
rg -n -g '*.tsx' '<table' frontend/apps/admin/src frontend/apps/tenant/src
rg -n -g '*.tsx' '上一页|下一页' frontend/apps/admin/src frontend/apps/tenant/src
rg -n -g '*.tsx' 'className="(?:admin-page|tenant-page)[^"]*space-y-' \
  frontend/apps/admin/src frontend/apps/tenant/src
rg -n 'export function DataTable' \
  frontend/apps/tenant/src/components/pages/page-kit.tsx
npx @google/design.md lint DESIGN.md
```

前四条必须零结果；这里不要求非列表场景的 shared-ui `<Table>` 清零。DESIGN lint 必须 0 error / 0 warning。不要用全仓 `w-[Npx]` 作为门禁，因为 Sheet 宽度仍是明确排除的 known gap；只禁止表格列继续引入任意像素宽度。

最终还需：

- 双端 type-check/build 和 shared-ui/tenant tests 通过。
- 390 / 768 / 1440 视口回归通过。
- 设计系统文件 `status` 从 `adopting` 调整为 `active`。
- T-23（#59）关闭销账，issue 附五件套、打样、全量 grep 与走查证据。
- README 仅在功能矩阵或行为口径实际变化时更新；纯视觉迁移不伪造产品行为变化。

### 明确不吸收

- T-17：query-key 工厂全量收敛、tenant auth client 与路由守卫。
- T-12：Admin 前端测试基建与全量页面测试。
- T-11：OpenAPI 生成类型和 shared types 全量替换。
- Sheet 宽度 token、暗色模式、后端 API/数据库行为、信息架构重做。
- T-21 已删除页面的任何恢复或迁移。

## 附录：列表页与筛选交互行为口径

> 2026-08-23 已迁入 [.trellis/spec/frontend/component-guidelines.md](.trellis/spec/frontend/component-guidelines.md)「列表页与筛选交互行为口径」，本文不再保留副本。

## Known Gaps

- 存量页面仍须按 C3–C5 分批迁移（进度见「状态速览」），不能因五件套与打样页已就绪就一次性替换全局语义色。
- Sheet 宽度目前仍有大量任意像素值；应另立宽度 token，但不扩入本次五件套实现。
- Badge tone 与 AlertDialogAction destructive variant 已在 Phase A 补齐；Phase B 已将 multiSelect 的搜索文案与 loading/empty 可查看状态纳入公共 API，选项请求 error/retry 仍由业务包装层表达。
- 暗色模式不在本期范围。
- T-21 已合并且目标页面已删除；C3–C5 各批开工前仍须基于最新 main 复扫页面、raw table 与分页数量（命令见「T-21 合并门」），再确认该批清单。
