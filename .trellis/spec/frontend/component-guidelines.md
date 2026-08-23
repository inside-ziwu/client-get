# 组件与列表页契约

> 本文的 Components 章节自仓库根 `DESIGN.md` 迁入，列表交互口径自 `PROGRESS-2026-Q3.md` 附录迁入（2026-08-23）。设计令牌与视觉原则见 [design-system.md](./design-system.md)。

## 基本规则

- UI 原语一律来自 `@shared/ui`（导出清单：`frontend/packages/shared-ui/src/index.ts`），不在 app 内重复造；需要新原语先加到 shared-ui 再用。
- 列表页统一用五件套 ListPage / FilterBar / DataTable / TableState / Pagination，页面负责取数与 mutation，Pattern 只负责展示、受控交互和布局。
- 五件套公开 API 已冻结：改签名属于 API 变更，走分支 + PR，并同步两端所有调用方。

## Components（五件套公开 API，2026-07-15 冻结）

Pattern 组件统一放在 `frontend/packages/shared-ui/src/components/`，通过 `@shared/ui` 根入口导出。组件不得依赖 React Query、路由、具体 API 类型或业务状态枚举；页面负责取数和 mutation，Pattern 只负责展示、受控交互和布局。

### 公开 API 冻结（2026-07-15）

双页打样（Tenant companies 与 Admin email-templates）四轮人工 Gate 通过后，五件套在组件提交 `38becd5` 的公开契约正式冻结：

- ListPage：`ListPage`、`ListPageProps`
- FilterBar：`FilterBar`、`FilterBarProps`、`FilterField`、`FilterFieldRenderContext`、`FilterDraftValue`、`FilterDraft`、`KeysMatching`
- DataTable：`DataTable`、`DataTableProps`、`DataTableColumn`、`DataTableSelection`、`StatusTone`、`ColumnAlignment`
- TableState：`TableState`、`TableStateProps`、`TableStateSpec`
- Pagination：`Pagination`、`PaginationProps`、`PaginationValue`
- 两个组件族共用的宽度契约：`WidthPreset`、`WidthSpec`

冻结后允许不改变默认行为的向后兼容可选项，但禁止在存量迁移中删除、改名、收窄类型或针对单页复制分叉组件。确需破坏性调整时，必须先更新本节契约、补回归测试并重新进行双打样页级别的人工走查 Gate；内部实现可以在契约和行为不变的前提下演进。

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
- 采用 ListPage 的列表页移除 `.admin-page` / `.tenant-page` 外层与额外 `space-y-*` 叠加；这两个全局类仍服务非列表页，不删除其定义。



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

DataTable 与 FilterBar 共用 `WidthSpec` 形状，但使用表格列自己的物理 token：`small=64px`、`medium=96px`、`large=144px`（`globals.css` 的 `--ui-table-column-*`，2026-07-24 收紧）。未声明 `width` 的列默认取 `medium`；少数特殊列可用 `{ custom: number }`，不接受任意宽度 class。相同语义名表示组件族内的相对密度，不强迫表格列与表单控件使用相同像素值。

表头与单元格始终使用同一对齐方式。默认按列类型决定：text/date 左对齐、number 右对齐、status/boolean 居中、actions 右对齐；业务列可用 `align` 显式覆盖。禁止分别给表头或单元格追加零散 `text-*` class。


| type      | 默认行为                                                           |
| --------- | -------------------------------------------------------------- |
| `text`    | 左对齐、截断、Tooltip、空值 `-`                                          |
| `number`  | 右对齐、tabular numbers、空值 `-`                                     |
| `date`    | 左对齐、不换行；必须由 `format` 或 `render` 明确时区/格式                        |
| `status`  | 居中；从 `statusMap` 输出带文字的语义 Badge；未知值回退 neutral                  |
| `boolean` | 居中；`readOnly` 用 Badge，`interactive` 用 Switch；必须提供可访问 label     |
| `actions` | 右对齐；`render` 必填，是否固定由 DataTable 的 stickyActions 控制；业务页可显式覆盖为居中 |


补充规则：

- 单元格解析优先级固定为 `render > format > 类型默认格式`。`render` 是 RatingTag、链接和组合操作的必要逃生口，但不能覆盖列宽与对齐纪律。
- 同一行存在两个及以上常驻操作时，采用 Ant ProTable 式轻量文字按钮，文字与表格正文共用 14px 基线并使用 500 字重，通过 32px 高点击区域和统一间距表达可操作性。行内操作不得传 `Button size="sm"`，避免重新注入 12px `text-xs`；也禁止退回 `h-auto p-0` 的裸文字。低频操作才进入更多菜单；业务要求常驻的破坏操作默认保持中性色，hover/focus 再切换 danger 色，强危险色保留给二次确认按钮。
- 页面级“新增/创建”主操作统一使用 `CreateButton`：固定 40px 高、近黑主色和左侧 Plus 图标，页面不得自行散写颜色、尺寸或决定是否显示图标。非新增语义的主操作不使用 `CreateButton`；同页次操作使用 outline，并仅在图标能明确表达业务语义时保留图标。
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

## 列表页与筛选交互行为口径

- **公司列表行操作**：右侧固定操作列居中常驻“详情 / 群组 / 拉黑”三个与列表正文同为 14px/500、32px 高的轻量文字按钮，不使用更多菜单；拉黑默认中性、hover/focus 显示危险色。拉黑仍必须经过二次确认，提交期间禁止重复操作和关闭弹窗。
- **列表刷新反馈**：翻页或查询刷新期间保留旧行与分页上下文；表格使用独立状态行显示“更新中…”，不得覆盖固定表头或行操作。
- **平台邮件模板行操作**：操作列居中常驻“编辑 / 删除”两个与列表正文同为 14px/500、32px 高的文字按钮，不使用图标；删除默认中性、hover/focus 显示危险色，并保留二次确认。
- **平台配置状态**：评分模板与动态源列表统一使用可操作 Switch（`type: 'boolean'` 列 + `interactive`），提交期间禁用当前行；编辑器统一显示“状态 + Switch + 启用/停用”。评分模板行业输入只更新草稿，点击「查询」或按 Enter 后才应用，重置同时清空草稿与已应用条件。
- **页面级新增操作**：已迁移列表页统一使用 shared-ui `CreateButton`：40px 高、近黑主色、左侧 Plus 图标；页面不得自行散写主按钮颜色、尺寸或决定是否显示新增图标。非新增语义不使用该组件，同页次操作使用 outline。
- **Tenant 简单列表**：行业动态、团队与模板统一使用 shared-ui ListPage/DataTable/TableState；列宽只使用 `small/medium/large/{ custom }` 契约，短枚举与操作居中，时间不换行，行操作提交期间只禁用当前行。团队新增成员操作框按控件契约使用姓名/角色 `small`、邮箱 `medium`，不与列表列宽混用。模板保留“我的模板/平台模板库”双 Tab 与原有编辑、预览、复制、克隆、测试发送、删除行为；平台模板“预览”当前存在误复制风险（#65，修复前勿用于只读核验）。
- **公司筛选交互**：16 项查询条件常驻，并按业务语义合并呈现为 12 个控件：进口额、进口次数、联系人、成立年份各使用一体式起止范围；关键词使用 `medium`，国家、细分行业、产品标签、采集类型、群组状态与两种评级显式使用 `small`，范围组件显式使用 256px 自定义宽度。查询/重置跟随最后一个条件，1920px 主工作区保持两排。未选择统一显示“不限”，单选条件可单独选回“不限”而无需整体重置。远程多选加载时可打开并显示转圈与“正在加载选项…”，接口返回后原位刷新；空数组显示“暂无可选项”。FilterBar 内的多选保持 40px 单行紧凑展示：单项显示标签并截断，多项显示“已选 N 项”，取消选择在弹层内完成；弹层复选框固定 16px，不随长标签压缩。每次打开多选弹层时，已选项按选择顺序置顶并与其余选项分隔；本次打开期间顺序冻结，避免勾选后跳动，关闭再打开才按最新状态重排；搜索时只显示匹配结果，不强制分组。
