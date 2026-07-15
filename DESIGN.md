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
  control-width-small:
    width: 160px
  control-width-medium:
    width: 224px
  control-width-large:
    width: 320px
  table-column-small:
    width: 96px
  table-column-medium:
    width: 144px
  table-column-large:
    width: 224px
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
├─ FilterBar：查询 / 重置；高频页可启用紧凑常驻 ┤
├─ 批量操作栏（有选择时出现，不引起横向跳动） ──┤
├─ DataTable：sticky header + horizontal scroll ─┤
└─ Pagination：总数/页大小          跳页/前后页 ─┘

移动端
┌─ 标题与描述 ────────────────────────────────┐
├─ 主操作（必要时占满一行）───────────────────┤
├─ FilterBar：一列；是否折叠由业务频率显式决定 ┤
├─ 批量操作栏，允许换行 ──────────────────────┤
├─ DataTable：保留表格语义，横向滚动 ─────────┤
└─ Pagination：上下两行，不横向挤压 ──────────┘
```

### 响应式规则

| 范围         | 规则                                               |
| ------------ | -------------------------------------------------- |
| `< 640px`    | 单列筛选；头部操作换行；分页上下堆叠；表格横向滚动 |
| `640–1023px` | 默认 2 列；紧凑模式按语义宽度自动换行；详情用 Sheet |
| `>= 1024px`  | 默认 4 列；紧凑模式不拉伸控件；完整分页             |

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
type WidthPreset = "small" | "medium" | "large";
type WidthSpec = WidthPreset | { custom: number };
type FilterDraftShape<T extends object> = Record<keyof T, FilterDraftValue>;
type KeysMatching<T, V> = {
  [K in keyof T]-?: T[K] extends V ? Extract<K, string> : never;
}[keyof T];

interface FilterFieldRenderContext<T extends FilterDraftShape<T>> {
  values: T;
  setValue: <K extends keyof T>(name: K, value: T[K]) => void;
  disabled: boolean;
}

interface BaseFilterField {
  label: string;
  placeholder?: string;
  advanced?: boolean;
  width?: WidthSpec;
}

type FilterField<T extends FilterDraftShape<T>> =
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
      searchPlaceholder?: string;
    })
  | (BaseFilterField & {
      name: Extract<keyof T, string>;
      kind: "custom";
      render: (context: FilterFieldRenderContext<T>) => React.ReactNode;
    });

interface FilterBarProps<T extends FilterDraftShape<T>> {
  values: T;
  fields: ReadonlyArray<FilterField<T>>;
  onChange: (next: T) => void;
  onSubmit: (draft: T) => void;
  onReset: () => void;
  isSubmitting?: boolean;
  appliedCount?: number;
  layout?: "grid" | "compact";
  collapseAdvanced?: boolean;
  optionStateMode?: "disabled" | "inspectable";
  actionsPlacement?: "footer" | "inline";
}
```

交互契约：

- 输入只改变 draft；提交后父页面原子地更新 applied filters、`page=1` 并清空跨页 selection。
- draft 中 text/select/number/date 一律保存 string，multiSelect 保存 string[]；number 在提交时由页面校验并转换，date 使用 `YYYY-MM-DD`。空值统一为 `""` 或 `[]`。
- Enter 等同“查询”；“重置”同时清空 draft、applied filters、页码和 selection，只触发一次新查询。
- 默认 `advanced=true` 的字段在窄屏收起；入口展示已应用条件数量。高频业务页可显式设置 `collapseAdvanced=false`，全部条件在同一容器常驻，不允许按桌面/移动端暗中改变业务可见性。
- `layout="compact"` 使用统一宽度契约并自动换行：`small=160px`、`medium=224px`、`large=320px`，字段未声明 `width` 时一律取 `medium`，不再按 text/select/number/custom 类型随机分配默认值。特殊复杂控件可显式使用 `{ custom: number }`，单位固定为 px；`<640px` 统一占满容器，不产生页面级横向滚动。
- 原始 Input、SelectTrigger 和 MultiSelect 只负责填满字段容器，宽度由 FilterBar 单点拥有；禁止页面传任意 Tailwind 宽度 class 或使用 `!important` 抢占布局。
- `actionsPlacement="inline"` 仅在全部字段位于同一容器时让“重置 / 查询”参与紧凑换行并跟随最后一个条件；存在独立高级条件区时自动回退到底部操作区。
- 每个 select/multiSelect 自己声明 option loading/empty，与列表 loading/empty 分开表达。multiSelect 可通过 `searchPlaceholder` 区分触发器占位与弹层搜索对象。
- `optionStateMode="inspectable"` 时，loading/empty 不禁用 multiSelect 触发器：弹层显示转圈加“正在加载选项…”或“暂无可选项”，ready 数据返回后在已打开弹层原位更新；默认 `disabled` 模式保持向后兼容。
- `custom` 是范围输入等复杂字段的逃生口，不允许借此在页面重建整套 FilterBar。min/max 等同一业务维度应优先合并为单标签、单边框的范围控件，同时保留两个独立的可访问名称和底层查询字段。

### DataTable

职责：基于列类型统一对齐、格式、宽度、选择、sticky 行为和状态行。它不做服务端排序、分页、请求和业务 mutation。

```ts
type WidthPreset = "small" | "medium" | "large";
type WidthSpec = WidthPreset | { custom: number };
type ColumnAlignment = "left" | "center" | "right";
type StatusTone = "neutral" | "success" | "warning" | "info" | "danger";

interface BaseDataTableColumn {
  id: string;
  header: React.ReactNode;
  width?: WidthSpec;
  align?: ColumnAlignment;
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

DataTable 与 FilterBar 共用 `WidthSpec` 形状，但使用表格列自己的物理 token：`small=96px`、`medium=144px`、`large=224px`。未声明 `width` 的列默认取 `medium`；少数特殊列可用 `{ custom: number }`，不接受任意宽度 class。相同语义名表示组件族内的相对密度，不强迫表格列与表单控件使用相同像素值。

表头与单元格始终使用同一对齐方式。默认按列类型决定：text/date 左对齐、number 右对齐、status/boolean 居中、actions 右对齐；业务列可用 `align` 显式覆盖。禁止分别给表头或单元格追加零散 `text-*` class。

| type      | 默认行为                                                           |
| --------- | ------------------------------------------------------------------ |
| `text`    | 左对齐、截断、Tooltip、空值 `-`                                    |
| `number`  | 右对齐、tabular numbers、空值 `-`                                  |
| `date`    | 左对齐、不换行；必须由 `format` 或 `render` 明确时区/格式          |
| `status`  | 居中；从 `statusMap` 输出带文字的语义 Badge；未知值回退 neutral     |
| `boolean` | 居中；`readOnly` 用 Badge，`interactive` 用 Switch；必须提供可访问 label |
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

## Auto Plan

本计划于 2026-07-14 基于设计提交 `63cbae8` 和 `origin/main@72deaa0` 生成。它是实施顺序与验收边界；Phase A 的 token alias、原子层补强与 Pattern 五件套已合并，Phase B 双页打样已实现并等待用户走查，Phase C 尚未开始。

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

### Phase A：shared-ui Pattern 基建

范围只允许 `frontend/packages/shared-ui`。不修改任何 app 页面，不修改旧 `--background`、`--primary`、`--ring` 等全局语义变量，不新增表格引擎依赖。

#### A0 · 基线与 token alias

修改：

- `src/theme/globals.css`：追加 `--ui-*` 目标变量，覆盖 canvas、surface、border、语义 tone、radius、spacing 和三档列宽；旧变量保持原值。
- `src/theme/tailwind-preset.ts`：追加静态 `ui-*` color、typography、radius、column width alias；保留旧映射。

约束：

- Phase A 只是 additive alias，不能让尚未迁移的页面提前变成白底黑按钮。
- DataTable 列宽使用静态 class map；禁止模板拼接 Tailwind class。
- `DESIGN.md` 继续保持 `status: proposed`。

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

#### Gate A

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

### T-21 合并门

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

### Phase B：双页打样

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
- 每行删除使用 inline AlertDialog，标题含模板名，destructive pending 防重复；失败不伪装成功。
- query 初载、empty、error/retry 和 refetch 分开；不借迁移改 endpoint、payload 或业务校验。

#### Gate B：打样走查与 API 冻结

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

只有用户走查确认后：

1. 冻结五件套 public API。
2. 将 DESIGN.md `status` 从 `proposed` 调整为 `adopting`，表示新页面必须遵守但存量仍在迁移。
3. 开始 Phase C；走查前不批量迁页。

### Phase C：存量迁移批次

以下是 T-21 合并前的 provisional 基线：20 个 route-level 列表页中，T-21 删除 3 页、Phase B 迁 2 页，Phase C 剩 15 页。T-21 合并后的复扫结果优先于此数字。

终验中的“手写表格清零”专指 app 内原生小写 `<table>`。非列表详情页和向导中已经使用 shared-ui 原子 `<Table>` 的小型展示表可以保留，例如 work-schedule 的 country/rule-set 详情和 send-plan wizard；它们不属于五件套列表页，也不计入 raw table 门禁。

#### C1 · 简单 Admin（2 页）

- `frontend/apps/admin/src/app/(dashboard)/intelligence-sources/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/scoring-templates/client-page.tsx`

重点：CRUD 状态、inline delete、query data 镜像清理；scoring-templates 把 industry 明确拆成 draft/applied，使“查询”恢复真实语义，但不改 API。

#### C2 · 简单 Tenant（3 页）

- `frontend/apps/tenant/src/app/(dashboard)/intelligence/page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

重点：替换 app-local DataTable；保留 templates 双 Tab 和 mutation、team 当前账号保护与状态 pending；所有行提供稳定 getRowId。

#### C3 · 交互配置与发送计划（4 页）

- `frontend/apps/admin/src/app/(dashboard)/ai-config/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/warmup-rules/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/work-schedule/client-page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`
- 关联：`frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/page.tsx`
- 清理：`frontend/apps/tenant/src/components/pages/page-kit.tsx` 的 DataTable export

重点：ListPage 只承载列表区域，不吞并同页编辑器；配置表通过 column render 保留输入行为；send-plans 用显式详情链接替代整行点击。C3 必须在 C2 合并后执行；确认 C2 已迁完 intelligence/team/templates、T-21 已删除 keywords、send-plan 详情也完成迁移后，才能删除本地 DataTable export。PageHeader/SearchBar 保留。

#### C4 · 宽表与复杂筛选（5 页）

- `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/collection/peers-cleaned/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/collection/peers/client-page.tsx`
- `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx`
- `frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`
- 关联：`frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`

重点：四个 collection 页的接口与类型必须以 T-21 合并后代码为准；筛选、宽表、分页、详情 Sheet 和嵌套表逐页保真。curated-customers 同时覆盖群组侧栏、群组 CRUD、添加公司弹窗与公司详情。

#### C5 · tenants 巨型页（1 页）

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

前四条必须零结果；这里不要求非列表场景的 shared-ui `<Table>` 清零。DESIGN lint 必须 0 error / 0 warning。不要用全仓 `w-[Npx]` 作为门禁，因为 Sheet 宽度仍是本文件明确排除的 known gap；只禁止表格列继续引入任意像素宽度。

最终还需：

- 双端 type-check/build 和 shared-ui/tenant tests 通过。
- 390 / 768 / 1440 视口回归通过。
- DESIGN.md `status` 从 `adopting` 调整为 `active`。
- T-23 移入 TODO“已销账”，写明五件套、打样、全量 grep 与走查证据。
- HANDBOOK 仅在功能矩阵或行为口径实际变化时更新；纯视觉迁移不伪造产品行为变化。

### 明确不吸收

- T-17：query-key 工厂全量收敛、tenant auth client 与路由守卫。
- T-12：Admin 前端测试基建与全量页面测试。
- T-11：OpenAPI 生成类型和 shared types 全量替换。
- Sheet 宽度 token、暗色模式、后端 API/数据库行为、信息架构重做。
- T-21 已删除页面的任何恢复或迁移。

## Known Gaps

- Phase A 已新增 `--ui-*` CSS variables、Tailwind alias 与 Pattern 五件套；Phase B 两个打样页已消费新 token，但用户走查尚未完成，`status` 继续保持 `proposed`。确认后才分批替换存量全局语义色。
- Sheet 宽度目前仍有大量任意像素值；应另立宽度 token，但不扩入本次五件套实现。
- Badge tone 与 AlertDialogAction destructive variant 已在 Phase A 补齐；Phase B 已将 multiSelect 的搜索文案与 loading/empty 可查看状态纳入公共 API，选项请求 error/retry 仍由业务包装层表达。
- 暗色模式不在本期范围。
- T-21 已合并且目标页面已删除；Phase B 创建独立分支后仍须基于最新 main 复扫页面与分页数量，再冻结 Phase C 清单。
