---
version: alpha
name: ClientGet Product UI
description: 面向 Admin 与 Tenant 双端后台的列表页设计系统；以克制、清晰、可扫描为核心。
status: proposed
colors:
  primary: "#111111"
  primary-active: "#242424"
  primary-disabled: "#E5E7EB"
  on-primary: "#FFFFFF"
  foreground: "#111111"
  body: "#374151"
  muted-foreground: "#6B7280"
  background: "#FFFFFF"
  surface-soft: "#F8F9FA"
  surface-card: "#F5F5F5"
  border: "#E5E7EB"
  border-soft: "#F3F4F6"
  success-surface: "#ECFDF5"
  success-foreground: "#047857"
  warning-surface: "#FFF7ED"
  warning-foreground: "#C2410C"
  info-surface: "#F5F3FF"
  info-foreground: "#6D28D9"
  danger-surface: "#FEF2F2"
  danger-foreground: "#B91C1C"
  overlay: "rgba(17, 17, 17, 0.48)"
typography:
  page-title:
    fontFamily: "ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0
  section-title:
    fontFamily: "ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0
  body:
    fontFamily: "ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  body-strong:
    fontFamily: "ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: 0
  caption:
    fontFamily: "ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0
  numeric:
    fontFamily: "ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
    fontFeature: "tnum"
rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px
spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 20px
  xl: 24px
  xxl: 32px
components:
  page-canvas:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.body}"
  page-description:
    backgroundColor: "{colors.background}"
    textColor: "{colors.muted-foreground}"
    typography: "{typography.body}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.md}"
    padding: 0 16px
    height: 40px
  button-primary-active:
    backgroundColor: "{colors.primary-active}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.md}"
    padding: 0 16px
    height: 40px
  button-primary-disabled:
    backgroundColor: "{colors.primary-disabled}"
    textColor: "{colors.body}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.md}"
    padding: 0 16px
    height: 40px
  button-destructive:
    backgroundColor: "{colors.danger-foreground}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.md}"
    padding: 0 16px
    height: 40px
  input:
    backgroundColor: "{colors.background}"
    textColor: "{colors.body}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 0 12px
    height: 40px
  input-focused:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 0 12px
    height: 40px
  list-page:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    typography: "{typography.body}"
    padding: 0
  filter-bar:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.body}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 16px
  table-shell:
    backgroundColor: "{colors.background}"
    textColor: "{colors.body}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
  table-header:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.muted-foreground}"
    typography: "{typography.caption}"
    padding: 8px 12px
    height: 36px
  table-row:
    backgroundColor: "{colors.background}"
    textColor: "{colors.body}"
    typography: "{typography.body}"
    padding: 8px 12px
    height: 40px
  table-row-active:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.foreground}"
    typography: "{typography.body}"
    padding: 8px 12px
    height: 40px
  table-divider:
    backgroundColor: "{colors.border}"
    height: 1px
  table-divider-soft:
    backgroundColor: "{colors.border-soft}"
    height: 1px
  table-column-sm:
    width: 96px
  table-column-md:
    width: 144px
  table-column-lg:
    width: 224px
  table-column-xl:
    width: 320px
  table-state:
    backgroundColor: "{colors.background}"
    textColor: "{colors.muted-foreground}"
    typography: "{typography.body}"
    padding: 48px 16px
  pagination:
    backgroundColor: "{colors.background}"
    textColor: "{colors.muted-foreground}"
    typography: "{typography.body}"
    padding: 12px 16px
    height: 56px
  badge-neutral:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.body}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 8px
  badge-success:
    backgroundColor: "{colors.success-surface}"
    textColor: "{colors.success-foreground}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 8px
  badge-warning:
    backgroundColor: "{colors.warning-surface}"
    textColor: "{colors.warning-foreground}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 8px
  badge-info:
    backgroundColor: "{colors.info-surface}"
    textColor: "{colors.info-foreground}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 8px
  badge-danger:
    backgroundColor: "{colors.danger-surface}"
    textColor: "{colors.danger-foreground}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 8px
  dialog-overlay:
    backgroundColor: "{colors.overlay}"
    textColor: "{colors.on-primary}"
  card-outline:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.lg}"
    padding: 20px
---

# ClientGet Design System

## Overview

ClientGet 的 Admin 与 Tenant 是高频业务后台，不是营销站。界面首先服务于快速扫描、准确判断和低风险操作；视觉上采用白色画布、近黑主操作、浅灰分层和少量语义色，避免用装饰性颜色争夺注意力。

本文件是 T-23 的**目标设计与组件契约**，当前状态为 `proposed`。YAML token 是目标值，不代表 `shared-ui` 已完成迁移；实施时必须按 Phase A → B → C 顺序落地并回归，不能只改全局颜色后宣称完成。

设计语言参考 [Cal.com DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/cal/DESIGN.md) 的克制单色操作层、白画布与柔和圆角，但不照搬其营销页字体和大留白。文件结构遵循 [Google Labs DESIGN.md](https://github.com/google-labs-code/design.md) 规范。

### 设计原则

1. **内容先于容器**：卡片只用于表达分组，不为每一块内容套一层阴影。
2. **单一主操作**：一个页面头部最多一个黑色主按钮，其余操作降为 outline、ghost 或文字操作。
3. **状态不靠猜**：加载、刷新、空数据、筛选无结果、失败必须可区分。
4. **表格适合扫描**：数字右对齐、时间不换行、操作固定在右侧，空值统一为 `-`。
5. **双端同语法**：Admin 与 Tenant 共用 Pattern 组件，不在 app 内复制布局和分页。

### 当前实现与目标的边界

| 维度     | 当前实现                        | T-23 目标                              |
| -------- | ------------------------------- | -------------------------------------- |
| 页面底色 | `bg-background` 为浅灰          | 白画布，浅灰仅用于筛选栏、表头与弱分层 |
| 主操作   | 深蓝 `primary`                  | 近黑 `#111111`，彩色不用于主 CTA       |
| 圆角     | 全局基准 8px                    | 控件 8px、内容容器 12px，分层定义      |
| 列表组件 | 原子 Table + app 内手写列表     | shared-ui Pattern 五件套               |
| 暗色模式 | preset 声明 class，实际无 token | 本期不声明支持暗色模式                 |

## Colors

### 中性色

- `{colors.background}` 是页面与表格默认画布。
- `{colors.surface-soft}` 用于筛选栏、sticky 表头和弱分区；不用于整页铺底。
- `{colors.surface-card}` 用于悬停、选中行和中性 Badge，不叠加重阴影。
- `{colors.border}` 是控件和容器边界，`{colors.border-soft}` 是表格行分隔线。
- `{colors.foreground}` 只承载标题、关键数值和强操作；正文使用 `{colors.body}`，说明文字使用 `{colors.muted-foreground}`。

### 操作色

- `{colors.primary}` 只用于页面主操作、选中控件和必要的强焦点。
- 链接默认保持正文色并以下划线或上下文说明表达可点击，不批量染蓝。
- destructive 操作使用 `{colors.danger-foreground}`，必须同时有文字或图标语义，不能只靠红色。
- 所有交互元素的 `focus-visible` 使用 2px `{colors.foreground}` ring + 2px 白色 offset；输入框聚焦时边界同步变为 `{colors.foreground}`。不得用 `outline: none` 移除键盘焦点。

### 语义色

语义 Badge 使用浅色背景 + 深色文字，限定为 success、warning、info、danger、neutral 五种 tone。业务状态先映射到 tone，页面不得直接散写 emerald、violet、orange class。

## Typography

中文后台采用系统 sans 字体，不引入 Cal Sans。标题保持 600，不使用 700/800 制造层级；层级主要由字号、位置和留白表达。

| Token                        | 用途                                       |
| ---------------------------- | ------------------------------------------ |
| `{typography.page-title}`    | 页面一级标题，双端统一 20px                |
| `{typography.section-title}` | 卡片标题、弹层标题                         |
| `{typography.body}`          | 表格、筛选项、正文                         |
| `{typography.body-strong}`   | 主按钮、关键单元格                         |
| `{typography.caption}`       | 表头、Badge、辅助标签                      |
| `{typography.numeric}`       | 数量、金额、评分；同时启用 tabular numbers |

文案使用中文全称，避免不必要缩写。时间、金额和数量必须由页面通过 `format` 明确调用各端既有的统一 formatter，不能在 DataTable 内隐式猜测时区或单位。合并 Admin/Tenant formatter 不属于 T-23。

## Layout

### 页面骨架

页面使用单一纵向 `gap-5` 节奏。禁止在 `.admin-page` / `.tenant-page` 外再叠 `space-y-*`，也禁止由 Card 外边距参与页面节奏。

```text
桌面
┌─ 标题 + 描述 ─────────────────────────── 主操作 ┐
├─ FilterBar：常用条件 / 更多条件 / 查询 / 重置 ─┤
├─ 批量操作栏（有选择时出现，不引起横向跳动） ──┤
├─ DataTable：sticky header + horizontal scroll ─┤
└─ Pagination：总数/页大小          跳页/前后页 ─┘

移动端
┌─ 标题与描述 ────────────────────────────────┐
├─ 主操作（必要时占满一行）───────────────────┤
├─ FilterBar：一列，更多条件默认收起 ─────────┤
├─ 批量操作栏，允许换行 ──────────────────────┤
├─ DataTable：保留表格语义，横向滚动 ─────────┤
└─ Pagination：上下两行，不横向挤压 ──────────┘
```

### 响应式规则

| 范围         | 规则                                               |
| ------------ | -------------------------------------------------- |
| `< 640px`    | 单列筛选；头部操作换行；分页上下堆叠；表格横向滚动 |
| `640–1023px` | 2 列筛选；保留简化后的分页；详情继续用 Sheet       |
| `>= 1024px`  | 4 列基础筛选；完整分页；更宽的详情与操作区域       |

宽表不转换为信息卡瀑布流，因为公司、联系人和发送计划需要跨行比较。移动端允许横向滚动；selection 始终位于第一列，操作列固定在可见区域右侧。

### 列宽与密度

- 列宽只有 `sm=96px`、`md=144px`、`lg=224px`、`xl=320px` 四档；checkbox 列和少数图标列由组件保留固定窄宽。
- 页面不得出现新的 `w-[Npx]`、`min-w-[Npx]` 列宽。表格最小宽度由列 token 汇总计算。
- 表头水平 padding 12px、垂直 padding 8px；数据行同密度，默认最小高度 40px。
- 超长文本单行截断，DOM 保留完整文本，并在 hover/focus 时显示 Tooltip。

## Elevation & Depth

| 层级     | 表现                        | 使用位置                               |
| -------- | --------------------------- | -------------------------------------- |
| Flat     | 无阴影                      | 页面、筛选栏内部、表格正文             |
| Hairline | 1px border                  | 输入框、表格外框、Dialog/Sheet 边界    |
| Soft     | `0 1px 2px rgba(0,0,0,.05)` | 需要从白画布分离的浮层或 sticky 操作列 |
| Overlay  | `{colors.overlay}`          | Dialog、Sheet 遮罩                     |

不使用玻璃拟态、渐变背景、重投影或多层嵌套 Card。sticky 表头的层级靠浅灰背景和边界表达，不靠明显阴影。

## Shapes

- 输入框、按钮、分页控件使用 `{rounded.md}`（8px）。
- 筛选容器、表格外框、Card 使用 `{rounded.lg}`（12px）。
- Badge 使用 `{rounded.pill}`；Checkbox、Switch 保持各自原生几何。
- 弹层最大使用 `{rounded.xl}`（16px），业务页面不使用更大的“消费级”圆角。

## Components

Pattern 组件统一放在 `frontend/packages/shared-ui/src/components/`，通过 `@shared/ui` 根入口导出。组件不得依赖 React Query、路由、具体 API 类型或业务状态枚举；页面负责取数和 mutation，Pattern 只负责展示、受控交互和布局。

### ListPage

职责：统一标题区、筛选区、批量操作区、内容区和分页区的纵向节奏。不请求数据，不强制 Card，不持有筛选或分页状态。

```ts
interface ListPageProps {
  title: string;
  description?: string;
  primaryAction?: React.ReactNode;
  filters?: React.ReactNode;
  selectionToolbar?: React.ReactNode;
  children: React.ReactNode;
  pagination?: React.ReactNode;
  className?: string;
}
```

规则：

- `primaryAction` 是页面唯一主操作；多个次操作放 DropdownMenu。
- `selectionToolbar` 出现时占用预留位置或平滑插入，不覆盖表头。
- 采用 ListPage 的列表页移除 `.admin-page` / `.tenant-page` 外层与额外 `space-y-*` 叠加；这两个全局类仍服务非列表页，本任务不删除其定义。

### FilterBar

职责：用声明式 schema 渲染筛选控件，固定“查询 + 重置”交互。它只管理受控 draft，不构造 API 参数，也不直接修改 applied filters。

```ts
type FilterDraftValue = string | readonly string[];
type FilterDraft = Record<string, FilterDraftValue>;
type KeysMatching<T, V> = {
  [K in keyof T]-?: T[K] extends V ? Extract<K, string> : never;
}[keyof T];

interface FilterFieldRenderContext<T extends FilterDraft> {
  values: T;
  setValue: <K extends keyof T>(name: K, value: T[K]) => void;
  disabled: boolean;
}

interface BaseFilterField {
  label: string;
  placeholder?: string;
  advanced?: boolean;
}

type FilterField<T extends FilterDraft> =
  | (BaseFilterField & {
      name: KeysMatching<T, string>;
      kind: "text" | "number" | "date";
    })
  | (BaseFilterField & {
      name: KeysMatching<T, string>;
      kind: "select";
      options: ReadonlyArray<{ label: string; value: string }>;
      optionState?: "ready" | "loading" | "empty";
    })
  | (BaseFilterField & {
      name: KeysMatching<T, readonly string[]>;
      kind: "multiSelect";
      options: ReadonlyArray<{ label: string; value: string }>;
      optionState?: "ready" | "loading" | "empty";
    })
  | (BaseFilterField & {
      name: Extract<keyof T, string>;
      kind: "custom";
      render: (context: FilterFieldRenderContext<T>) => React.ReactNode;
    });

interface FilterBarProps<T extends FilterDraft> {
  values: T;
  fields: ReadonlyArray<FilterField<T>>;
  onChange: (next: T) => void;
  onSubmit: (draft: T) => void;
  onReset: () => void;
  isSubmitting?: boolean;
  appliedCount?: number;
}
```

交互契约：

- 输入只改变 draft；提交后父页面原子地更新 applied filters、`page=1` 并清空跨页 selection。
- draft 中 text/select/number/date 一律保存 string，multiSelect 保存 string[]；number 在提交时由页面校验并转换，date 使用 `YYYY-MM-DD`。空值统一为 `""` 或 `[]`。
- Enter 等同“查询”；“重置”同时清空 draft、applied filters、页码和 selection，只触发一次新查询。
- `advanced=true` 的字段在窄屏默认收起；入口展示已应用条件数量。
- 每个 select/multiSelect 自己声明 option loading/empty，与列表 loading/empty 分开表达。
- `custom` 是范围输入等复杂字段的逃生口，不允许借此在页面重建整套 FilterBar。

### DataTable

职责：基于列类型统一对齐、格式、宽度、选择、sticky 行为和状态行。它不做服务端排序、分页、请求和业务 mutation。

```ts
type ColumnWidth = "sm" | "md" | "lg" | "xl";
type StatusTone = "neutral" | "success" | "warning" | "info" | "danger";

interface BaseDataTableColumn {
  id: string;
  header: React.ReactNode;
  width: ColumnWidth;
}

type DataTableColumn<T> =
  | (BaseDataTableColumn & {
      type: "text" | "number";
      value: keyof T | ((row: T) => unknown);
      render?: (row: T) => React.ReactNode;
      format?: (value: unknown, row: T) => React.ReactNode;
    })
  | (BaseDataTableColumn & {
      type: "date";
      value: keyof T | ((row: T) => unknown);
    } & (
        | {
            format: (value: unknown, row: T) => React.ReactNode;
            render?: (row: T) => React.ReactNode;
          }
        | {
            render: (row: T) => React.ReactNode;
            format?: (value: unknown, row: T) => React.ReactNode;
          }
      ))
  | (BaseDataTableColumn & {
      type: "status";
      value: keyof T | ((row: T) => unknown);
      statusMap: Record<string, { label: string; tone: StatusTone }>;
      render?: (row: T) => React.ReactNode;
    })
  | (BaseDataTableColumn & {
      type: "boolean";
      value: keyof T | ((row: T) => unknown);
      getBooleanLabel: (row: T) => string;
    } & (
        | { booleanMode: "readOnly" }
        | {
            booleanMode: "interactive";
            onBooleanChange: (row: T, next: boolean) => void;
            isBooleanDisabled?: (row: T) => boolean;
          }
      ))
  | (BaseDataTableColumn & {
      type: "actions";
      render: (row: T) => React.ReactNode;
    });

interface DataTableSelection<T> {
  selectedKeys: ReadonlySet<string>;
  isRowDisabled?: (row: T) => boolean;
  onToggleRow: (row: T) => void;
  onTogglePage: (rows: readonly T[]) => void;
}

interface DataTableProps<T> {
  data: readonly T[];
  columns: ReadonlyArray<DataTableColumn<T>>;
  getRowId: (row: T) => string;
  entityName: string;
  state?: TableStateSpec;
  isRefreshing?: boolean;
  stickyHeader?: boolean;
  selection?: DataTableSelection<T>;
  stickyActions?: boolean;
  className?: string;
}
```

列类型默认行为：

| type      | 默认行为                                                           |
| --------- | ------------------------------------------------------------------ |
| `text`    | 左对齐、截断、Tooltip、空值 `-`                                    |
| `number`  | 右对齐、tabular numbers、空值 `-`                                  |
| `date`    | 不换行；必须由 `format` 或 `render` 明确时区/格式                  |
| `status`  | 从 `statusMap` 输出带文字的语义 Badge；未知值回退 neutral          |
| `boolean` | `readOnly` 用 Badge，`interactive` 用 Switch；必须提供可访问 label |
| `actions` | 右对齐；`render` 必填，是否固定由 DataTable 的 stickyActions 控制  |

补充规则：

- 单元格解析优先级固定为 `render > format > 类型默认格式`。`render` 是 RatingTag、链接和组合操作的必要逃生口，但不能覆盖列宽与对齐纪律。
- 默认 sticky header 开启；只有嵌套小表或打印视图可以显式关闭。
- `stickyActions` 默认开启并覆盖所有断点；嵌套小表可显式关闭。固定列使用不透明背景、边界和轻阴影，不能遮住横向滚动内容。
- selection 的 key 一律取自 DataTable 的 `getRowId`，避免两套身份函数分叉；它只代表当前页，`onTogglePage` 必须排除 `isRowDisabled` 的行。换页、筛选和 pageSize 变化后的清空策略由父页面在回调中执行。
- 有旧数据的 refetch 保留现有行，以弱提示“更新中…”和 `aria-busy` 表达；禁止退回整表 loading。
- Table 只能有一个滚动容器和一个外框，避免现有原子 Table wrapper 与 DataTable 双边框、双滚动。
- 首版不提供整行点击。详情入口使用有焦点态的显式链接或按钮，避免补造 Enter/Space 和互动子元素排除规则。

### TableState

职责：在合法的 `<tbody>` 中渲染 loading、empty、filtered-empty 和 error，避免把 `<div>` 塞到 table 外伪装状态。

```ts
type TableStateSpec =
  | { kind: "loading" }
  | { kind: "empty"; filtered?: boolean; onResetFilters?: () => void }
  | { kind: "error"; description?: string; onRetry?: () => void };

interface TableStateProps {
  state: TableStateSpec;
  entityName: string;
  colSpan: number;
}
```

标准文案：

- loading：`正在加载{实体}…`
- 首次空态：`暂无{实体}`
- 筛选无结果：`没有符合当前条件的{实体}`，可提供“重置筛选”
- error：`{实体}加载失败`，可提供“重试”

列表 loading 默认使用文字，不强制骨架屏。不得 catch 请求错误后返回空数组；这会把失败伪装成“暂无数据”。错误描述必须面向用户，不透传原始异常或响应体。

### Pagination

职责：统一总数、pageSize、跳页和前后页逻辑。采用受控、原子更新，避免 `setPageSize` 与 `setPage` 两次更新产生瞬时错误请求。

```ts
interface PaginationValue {
  page: number;
  pageSize: number;
}

interface PaginationBaseProps {
  value: PaginationValue;
  onChange: (next: PaginationValue) => void;
  pageSizeOptions?: readonly number[];
  isDisabled?: boolean;
}

type PaginationProps = PaginationBaseProps &
  (
    | {
        mode: "total";
        total: number;
        showPageJump?: boolean;
      }
    | {
        mode: "unknownTotal";
        hasNextPage: boolean;
      }
  );
```

交互契约：

- `mode="total"`：`pageCount = max(1, ceil(total / pageSize))`；`total=0` 时显示第 1/1 页且前后按钮均禁用。跳页在 Enter 或 blur 提交；空值/NaN 恢复当前页，越界 clamp。
- `mode="unknownTotal"`：隐藏总数、总页数与跳页，只显示当前页、上一页和下一页；上一页按 `page=1` 禁用，下一页按 `hasNextPage` 禁用。
- pageSize 改变时一次性发出 `{ page: 1, pageSize: next }`。
- 默认 pageSize options 为 `[20, 50, 100]`；迁移时允许页面显式保留既有 500/1000 选项，不借 UI 重构改变业务能力。
- 接口同时返回 total + has_more 时，只在 total 可靠时采用 total 模式；total 缺失或不可靠时采用 unknownTotal，禁止混合两套上限。
- 页码、筛选或 pageSize 改变后，父页面负责清空 selection。

### 状态、布尔与危险操作

- 只读布尔状态用 Badge；用户可直接切换的状态用 Switch，pending 时 disabled 并保留当前视觉状态。
- 删除、拉黑等危险操作必须把 `AlertDialogTrigger` 内联绑定到当前行，不使用共享 `deleteTarget` 弹窗。
- 确认标题包含对象名，Action 使用 destructive variant；pending 文案为“删除中…”或对应动词，禁止关闭和重复提交。
- 失败时保留对话框或给出明确 toast；成功后关闭、刷新数据并把焦点还给合理位置。
- 图标按钮必须有 `aria-label` 和 Tooltip。

### 打样与迁移边界

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

## Do's and Don'ts

### Do

- 改任何 UI 前先读本文件，并优先组合 `@shared/ui`。
- 用列类型表达 number/date/status/boolean/actions，让一致性来自组件默认值。
- 保留用户当前上下文：refetch 不清空旧行，mutation pending 有可见反馈。
- 为表格、筛选、分页和危险操作覆盖键盘与屏幕阅读器语义。
- 每迁一页净删除手写布局、分页和状态判断代码。

### Don't

- 不在页面散写任意像素列宽、彩色 Badge class 或另一套分页。
- 不把请求、React Query、路由跳转或业务 mutation 塞进 Pattern 组件。
- 不把 loading、error 与 empty 合并成 `items.length === 0`。
- 不把可交互布尔值渲染成看似可点但不可操作的 Badge。
- 不在一个页面放多个黑色主按钮，不用彩色 CTA 争夺主操作。
- 不借设计系统迁移改变 API 行为、删除业务选项或重做信息架构。

## Iteration Guide

1. Phase A 先新增目标 token/alias 和五件套，不重映射现有 `background`、`primary` 等全局语义变量，也不迁业务页；为纯组件状态建立 Vitest。
2. Phase B 只迁 tenant companies 与 admin email-templates，进行桌面/移动端用户走查。
3. 根据打样反馈冻结 API；组件 API 未冻结前不批量迁页。
4. Phase C 按“简单 Admin → 简单 Tenant → 宽表 → tenants 巨型页”分批迁移，每批独立验证。
5. tenants 页迁移时按 Tab 拆分 984 行组件，并移除 query data 拷贝进 local state 的反模式；不改变行为。
6. 每批检查：无新增 raw `<table>`、无手写分页、无页面级任意列宽、无 `space-y-*` 与 ListPage gap 叠加。

## Known Gaps

- 本文件尚未对应到 CSS variables、Tailwind preset 和组件实现；`status: proposed` 解除前不得声称视觉迁移完成。Phase B 先让打样页消费新 token，确认后才分批替换存量全局语义色。
- Sheet 宽度目前仍有大量任意像素值；应另立宽度 token，但不扩入本次五件套实现。
- Badge 尚无完整 tone，AlertDialogAction 尚无标准 destructive variant；Phase A 需要补齐原子层后再实现列类型。
- 暗色模式不在本期范围。
- 当前页面与分页数量来自 T-21 合并前基线，Phase C 开始前必须复扫。
