## Context

邮件模板编辑器（`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`）提供三种编辑模式：可视化（GrapesJS）、HTML、纯文本。模板变量以 `{{variable_name}}` 格式嵌入，后端在 `claim_due_emails` 时通过 `_render_text()` 做简单字符串替换。

当前问题：
1. 前端定义了 5 个变量，后端只渲染 3 个（`company_name`、`contact_name`、`sender_name`）
2. 变量只能复制到剪贴板，无法直接插入编辑器
3. 纯文本模式写入 `body_text`，但 `body_html` 为空时邮件客户端渲染空内容

## Goals / Non-Goals

**Goals:**
- 前端变量列表与后端渲染能力一致
- 变量 Badge 点击后直接插入到当前编辑器光标位置
- 纯文本模式创建的模板能正常显示内容

**Non-Goals:**
- 不增加自定义变量功能
- 不重构编辑器架构
- 不修改数据库 schema

## Decisions

### D1：移除 `product_name`，补充 `contact_email`，统一预览/发送映射

**选择**：从前端 VARIABLES 列表移除 `product_name`；在后端 `claim_due_emails` 和 `sample_emails` 两处渲染映射中统一使用 4 个变量（`company_name`、`contact_name`、`contact_email`、`sender_name`）。

**理由**：
- `product_name` 在数据模型中无任何来源，无法填充
- `contact_email` 的数据在查询中已取出（`shc.email AS to_email`），只需加入渲染映射
- `sample_emails`（预览路径）传的是完整 recipient dict，包含 `contact_email` 但缺少 `sender_name`；`claim_due_emails`（发送路径）反过来——两处映射不一致会导致预览和发送效果不同

**替代方案**：只改发送路径不改预览——但预览和发送不一致本身就是 bug。

### D2：变量插入到光标位置（封装 insertVariable 方法）

**选择**：根据当前编辑模式，采用不同插入策略：
- **HTML / 纯文本 textarea**：获取 textarea 的 `selectionStart` / `selectionEnd`，在光标位置插入变量文本，然后更新 React state
- **GrapesJS 可视化编辑器**：在 `GrapesEmailEditorHandle` 接口上新增 `insertVariable(text: string): boolean` 方法，内部处理 RTE 插入逻辑。返回 `true` 表示成功，`false` 表示 RTE 未激活，上层做 fallback（复制 + toast 提示）

**理由**：
- textarea 插入是标准 DOM 操作，成熟可靠
- GrapesJS 组件封装 `insertVariable()` 而非暴露整个 editor 实例，保持组件边界清晰
- `insertVariable` 向后兼容——admin 端也使用了 GrapesEmailEditor，新增方法不影响现有调用者

**替代方案**：暴露 `getEditor()` 返回完整 editor 实例——但上层代码会直接耦合 GrapesJS 内部 API，升级时易破坏。

### D3：纯文本 fallback 放在后端发送时（替换前检查 + HTML escape）

**选择**：在 `claim_due_emails` 中，在调用 `_render_text()` **之前**检查原始模板的 `body_html`。当原始 `body_html` 为空或仅含空白时：
1. 对 `body_text` 做 `html.escape()` 转义特殊字符
2. 将换行转为 `<br>`，包裹在 `<p>` 标签中
3. 赋值为 `body_html`，然后正常走渲染流程

**理由**：
- 放在后端确保所有发送路径都受到保护
- 在替换**前**检查：避免因运行时变量值为空而误触发 fallback（同一模板对不同收件人行为应一致）
- `html.escape()` 防止纯文本中的 `<`、`&` 等字符破坏生成的 HTML 结构
- 不修改前端保存逻辑，避免"纯文本"模式的语义被改变

**替代方案**：
- 在替换后检查——但行为会依赖运行时变量值，同一模板可能对不同收件人走不同路径
- 在前端保存时同步 `body_text → body_html`——混淆两个字段职责，且遗漏存量模板

### D4：建立模板变量合同

**选择**：在后端 `TenantMessagingService` 中定义 `TEMPLATE_VARIABLES` 常量（包含 name + label），新增 API endpoint 暴露给前端。前端从 API 获取变量列表，删除硬编码 `VARIABLES` 数组。

**理由**：当前前后端各自硬编码变量列表，是本次 bug 的根因。建立单一数据源（后端定义 → API 暴露 → 前端消费）从根本上防止未来再出现前后端不一致。

**替代方案**：只修复当前不一致，不建合同——但下次加变量时可能重复同样的问题。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| GrapesJS 插入变量可能因编辑器状态（未选中组件/未激活 RTE）失败 | Fallback 为复制行为 + toast 提示"请在编辑器中选中文本区域后再插入" |
| `body_text` 转 HTML 可能丢失格式意图 | 仅做最小转换（escape + 换行→`<br>`），不猜测用户意图 |
| `body_text` 含特殊字符时生成错误 HTML | 转换前先 `html.escape()` 转义 |
| `contact_email` 变量新增后，旧模板中若已有 `{{contact_email}}` 占位符会突然开始被替换 | 这是正确行为——之前是 bug（不替换），现在修复后反而正常了 |
| 变量列表 API 请求失败 | 前端可 fallback 到硬编码默认值（降级方案） |
