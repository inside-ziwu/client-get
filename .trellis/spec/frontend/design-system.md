---
version: alpha
name: ClientGet Product UI
description: 面向 Admin 与 Tenant 双端后台的列表页设计系统；以克制、清晰、可扫描为核心。
status: adopting
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
    width: 64px
  table-column-medium:
    width: 96px
  table-column-large:
    width: 144px
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

# ClientGet Design System（设计系统）

> 本文自仓库根 `DESIGN.md` 整体迁入（2026-08-23），是 Admin 与 Tenant 列表页设计系统的**目标设计**；组件公开 API 与列表交互口径见 [component-guidelines.md](./component-guidelines.md)。frontmatter 的 YAML token 是目标值。

## Overview

ClientGet 的 Admin 与 Tenant 是高频业务后台，不是营销站。界面首先服务于快速扫描、准确判断和低风险操作；视觉上采用白色画布、近黑主操作、浅灰分层和少量语义色，避免用装饰性颜色争夺注意力。

本文件是列表页设计系统的**目标设计与组件契约**：Pattern 五件套的公开 API 已冻结（见 [component-guidelines.md](./component-guidelines.md)），新建或迁移的列表页必须遵守本文件。YAML token 是目标值，不代表全量存量页面已经完成迁移，不能只改全局颜色后宣称完成；存量页面的迁移批次与完成状态见 [PROGRESS-2026-Q3.md](../../../PROGRESS-2026-Q3.md)。

设计语言参考 [Cal.com DESIGN.md](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/cal/DESIGN.md) 的克制单色操作层、白画布与柔和圆角，但不照搬其营销页字体和大留白。文件结构遵循 [Google Labs DESIGN.md](https://github.com/google-labs-code/design.md) 规范。

### 设计原则

1. **内容先于容器**：卡片只用于表达分组，不为每一块内容套一层阴影。
2. **单一主操作**：一个页面头部最多一个黑色主按钮，其余操作降为 outline、ghost 或文字操作。
3. **状态不靠猜**：加载、刷新、空数据、筛选无结果、失败必须可区分。
4. **表格适合扫描**：数字右对齐、时间不换行、操作固定在右侧，空值统一为 `-`。
5. **双端同语法**：Admin 与 Tenant 共用 Pattern 组件，不在 app 内复制布局和分页。



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


| Token                        | 用途                            |
| ---------------------------- | ----------------------------- |
| `{typography.page-title}`    | 页面一级标题，双端统一 20px              |
| `{typography.section-title}` | 卡片标题、弹层标题                     |
| `{typography.body}`          | 表格、筛选项、正文                     |
| `{typography.body-strong}`   | 主按钮、关键单元格                     |
| `{typography.caption}`       | 表头、Badge、辅助标签                 |
| `{typography.numeric}`       | 数量、金额、评分；同时启用 tabular numbers |


文案使用中文全称，避免不必要缩写。时间、金额和数量必须由页面通过 `format` 明确调用各端既有的统一 formatter，不能在 DataTable 内隐式猜测时区或单位；Admin/Tenant formatter 的合并统一不在列表页设计系统范围内。

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


| 范围           | 规则                             |
| ------------ | ------------------------------ |
| `< 640px`    | 单列筛选；头部操作换行；分页上下堆叠；表格横向滚动      |
| `640–1023px` | 默认 2 列；紧凑模式按语义宽度自动换行；详情用 Sheet |
| `>= 1024px`  | 默认 4 列；紧凑模式不拉伸控件；完整分页          |


宽表不转换为信息卡瀑布流，因为公司、联系人和发送计划需要跨行比较。移动端允许横向滚动；selection 始终位于第一列，操作列固定在可见区域右侧。

### 列宽与密度

- 列宽只有 `small=64px`、`medium=96px`、`large=144px` 三档（与 `globals.css` 的 `--ui-table-column-*` 一致；原 96/144/224/320 四档已于 2026-07-24 收紧）；checkbox 列和少数图标列由组件保留固定窄宽。
- 页面不得出现新的 `w-[Npx]`、`min-w-[Npx]` 列宽。表格最小宽度由列 token 汇总计算。
- 表头水平 padding 12px、垂直 padding 8px；数据行同密度，默认最小高度 40px。
- 超长文本单行截断，DOM 保留完整文本，并在 hover/focus 时显示 Tooltip。



## Elevation & Depth


| 层级       | 表现                          | 使用位置                     |
| -------- | --------------------------- | ------------------------ |
| Flat     | 无阴影                         | 页面、筛选栏内部、表格正文            |
| Hairline | 1px border                  | 输入框、表格外框、Dialog/Sheet 边界 |
| Soft     | `0 1px 2px rgba(0,0,0,.05)` | 需要从白画布分离的浮层或 sticky 操作列  |
| Overlay  | `{colors.overlay}`          | Dialog、Sheet 遮罩          |


不使用玻璃拟态、渐变背景、重投影或多层嵌套 Card。sticky 表头的层级靠浅灰背景和边界表达，不靠明显阴影。

## Shapes

- 输入框、按钮、分页控件使用 `{rounded.md}`（8px）。
- 筛选容器、表格外框、Card 使用 `{rounded.lg}`（12px）。
- Badge 使用 `{rounded.pill}`；Checkbox、Switch 保持各自原生几何。
- 弹层最大使用 `{rounded.xl}`（16px），业务页面不使用更大的“消费级”圆角。

## Do's and Don'ts



### Do

- 改任何 UI 前先读本文件与 component-guidelines.md，并优先组合 `@shared/ui`。
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
