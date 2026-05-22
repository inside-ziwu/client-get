---
title: 修复邮件模板编辑器（变量映射 + 插入交互 + 纯文本 fallback）
status: active
origin: openspec/changes/fix-email-template-editor/
created: 2026-05-22
execution_posture: tdd
---

# 修复邮件模板编辑器

## Context

邮件模板编辑器存在三个互相独立的 bug：

1. **虚假变量**：前端展示 5 个变量，后端只渲染 3 个（`product_name` 无数据源，`contact_email` 已在查询中但未传入 `_render_text()`）
2. **变量只能复制不能插入**：Badge onClick 仅 `copyVariable()`，用户需手动粘贴
3. **纯文本模式发邮件为空**：`body_text` 有内容但 `body_html` 为空，邮件客户端优先渲染空 HTML

工程审查扩展了额外修复项：
- `sample_emails`（预览）和 `claim_due_emails`（发送）变量映射不一致（预览缺 `sender_name`，发送缺 `contact_email`）
- `body_text` 转 HTML 时缺少 `html.escape()`
- 前后端各自硬编码变量列表，需建立变量合同（后端定义 → API 暴露 → 前端消费）

## Scope

**In scope:**
- 后端 `TEMPLATE_VARIABLES` 常量 + 变量列表 API
- `claim_due_emails` 和 `sample_emails` 统一 4 变量映射
- `body_text → body_html` fallback（含 `html.escape`）
- 前端消费变量 API、移除硬编码
- 变量 Badge 点击插入到光标位置（textarea + GrapesJS）
- 后端单元测试

**Not in scope:**
- 自定义变量功能
- 编辑器架构重构
- 数据库 schema 变更
- 前端测试框架搭建

## Decisions

| # | 决策 | 选择 | 来源 |
|---|------|------|------|
| D1 | 预览/发送映射 | 统一两处映射为 4 变量 | (see origin: design.md D1) |
| D2 | GrapesJS 接口 | 加 `insertVariable()` 方法，保持封装 | (see origin: design.md D2) |
| D3 | fallback 时机 | 替换前检查原始 `body_html` | (see origin: design.md D3) |
| D4 | HTML escape | `body_text` 转 HTML 时先 `html.escape()` | (see origin: design.md D3) |
| D5 | 变量合同 | 本次 PR 实现，后端定义 → API → 前端消费 | (see origin: design.md D4) |

## Implementation Units

执行姿态：TDD（先写测试，再写实现）。每个 IU 耗时 2-5 分钟。

---

### IU-1: 定义 TEMPLATE_VARIABLES 常量

**文件**: `backend/app/services/tenant_messaging_service.py`

**做什么**: 在 `TenantMessagingService` 类顶部定义类级常量：

```python
TEMPLATE_VARIABLES = [
    {"name": "company_name", "label": "公司名称"},
    {"name": "contact_name", "label": "联系人姓名"},
    {"name": "contact_email", "label": "联系人邮箱"},
    {"name": "sender_name", "label": "发件人姓名"},
]
```

**无需测试**：纯数据声明。

**预计**: ~2 min

---

### IU-2: 测试 `_render_text` 4 变量映射（RED）

**文件**: `backend/tests/test_email_template_rendering.py`（新建）

**做什么**: 编写测试，验证 `_render_text` 使用 4 变量映射时全部正确替换。

```python
def test_render_text_replaces_all_four_variables():
    svc = TenantMessagingService()
    template = "Hi {{contact_name}}, from {{company_name}}. Reply to {{contact_email}}. Best, {{sender_name}}"
    mapping = {
        "company_name": "Acme Corp",
        "contact_name": "John",
        "contact_email": "john@acme.com",
        "sender_name": "Alice",
    }
    result = svc._render_text(template, mapping)
    assert result == "Hi John, from Acme Corp. Reply to john@acme.com. Best, Alice"
```

再加一个测试：变量值为 `None` 时替换为空字符串。

**预期**: GREEN（`_render_text` 本身逻辑已正确，这里验证合同）

**预计**: ~3 min

---

### IU-3: 测试 body_text fallback 逻辑（RED）

**文件**: `backend/tests/test_email_template_rendering.py`

**做什么**: 编写 fallback 函数的测试用例：

```python
def test_fallback_converts_body_text_to_html_when_body_html_empty():
    # body_html 为空 → body_text 转为 HTML
    result = _body_html_fallback(body_html="", body_text="Hello\nWorld")
    assert "<br>" in result
    assert "Hello" in result
    assert "World" in result

def test_fallback_escapes_html_special_chars():
    result = _body_html_fallback(body_html="  ", body_text="<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result

def test_fallback_noop_when_body_html_has_content():
    original = "<p>Hello</p>"
    result = _body_html_fallback(body_html=original, body_text="ignored")
    assert result == original
```

**预期**: RED（`_body_html_fallback` 还不存在）

**预计**: ~3 min

---

### IU-4: 实现 body_text fallback 函数（GREEN）

**文件**: `backend/app/services/tenant_messaging_service.py`

**做什么**: 在 `TenantMessagingService` 中添加静态方法：

```python
@staticmethod
def _body_html_fallback(body_html: str, body_text: str) -> str:
    if (body_html or "").strip():
        return body_html
    import html
    escaped = html.escape(body_text or "")
    return f"<p>{escaped}</p>".replace("\n", "<br>")
```

**验证**: 运行 IU-3 的测试 → GREEN

**预计**: ~3 min

---

### IU-5: 修复 `claim_due_emails` 变量映射 + 加 fallback

**文件**: `backend/app/services/tenant_messaging_service.py` (~line 1428)

**做什么**:

1. 在 `_render_text` 调用之前，加 fallback：
   ```python
   raw_body_html = row["body_html"]
   body_html_tpl = self._body_html_fallback(raw_body_html, row["body_text"] or "")
   ```

2. 构建统一映射 dict（加入 `contact_email`）：
   ```python
   var_mapping = {
       "company_name": row["company_name"],
       "contact_name": row["contact_name"],
       "contact_email": row["to_email"],
       "sender_name": row["sender_name"],
   }
   ```

3. 三处 `_render_text` 调用改用 `body_html_tpl` 和 `var_mapping`。

**验证**: 运行全部测试 → GREEN

**预计**: ~4 min

---

### IU-6: 修复 `sample_emails` 变量映射

**文件**: `backend/app/services/tenant_messaging_service.py` (~line 1094)

**做什么**: `sample_emails` 当前把整个 `recipient` dict 传给 `_render_text`。改为构建显式映射：

```python
plan = preview["plan"]
var_mapping = {
    "company_name": recipient["company_name"],
    "contact_name": recipient["contact_name"],
    "contact_email": recipient["contact_email"],
    "sender_name": plan.get("sender_name", ""),
}
```

替换 `self._render_text(first_template["subject"], recipient)` 为 `self._render_text(first_template["subject"], var_mapping)`，`body_text` 同理。

**验证**: 运行测试 → GREEN

**预计**: ~3 min

---

### IU-7: 新增变量列表 API endpoint

**文件**: `backend/app/api/tenant/messaging.py`

**做什么**: 添加新路由：

```python
@router.get("/email-templates/variables")
async def list_template_variables(
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    return success_response(TenantMessagingService.TEMPLATE_VARIABLES)
```

注意：该路由必须放在 `/email-templates/{template_id}` 之前，否则 `variables` 会被当作 `template_id` 匹配。

**验证**: `curl` 或 pytest 调用

**预计**: ~2 min

---

### IU-8: 前端 — 新增 `getVariables()` API 方法

**文件**: `frontend/packages/shared-api/src/tenant/email-templates.ts`

**做什么**: 在 `emailTemplatesApi` return 中添加：

```typescript
getVariables: () =>
  client.get<ApiResponse<Array<{ name: string; label: string }>>>('/api/v1/email-templates/variables'),
```

**预计**: ~2 min

---

### IU-9: 前端 — 消费变量 API，移除硬编码

**文件**: `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

**做什么**:

1. 删除 `VARIABLES` 常量（line 48-54）
2. 用 React Query 从 API 获取变量列表：
   ```typescript
   const { data: variablesData } = useQuery({
     queryKey: ['tenant', 'template-variables'],
     queryFn: () => tenantApi.emailTemplates.getVariables(),
   });
   const variables = variablesData?.data?.data ?? [];
   ```
3. 将页面中所有 `VARIABLES` 引用替换为 `variables`
4. `saveTemplate` 中 `variables: VARIABLES.filter(...)` 也改用 `variables`
5. 更新 label 文案："变量（点击复制）" → "变量（点击插入）"

**验证**: dev server 启动 → 页面正确显示 4 个变量

**预计**: ~5 min

---

### IU-10: 前端 — textarea 光标插入函数

**文件**: `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

**做什么**:

1. 为 HTML 和纯文本 textarea 添加 ref：
   ```typescript
   const htmlTextareaRef = useRef<HTMLTextAreaElement>(null);
   const textTextareaRef = useRef<HTMLTextAreaElement>(null);
   ```

2. 实现插入函数：
   ```typescript
   const insertAtCursor = (
     ref: React.RefObject<HTMLTextAreaElement>,
     text: string,
     field: 'body_html' | 'body_text',
   ) => {
     const el = ref.current;
     if (!el) return;
     const start = el.selectionStart;
     const end = el.selectionEnd;
     const before = el.value.slice(0, start);
     const after = el.value.slice(end);
     setForm((p) => ({ ...p, [field]: before + text + after }));
     requestAnimationFrame(() => {
       el.selectionStart = el.selectionEnd = start + text.length;
       el.focus();
     });
   };
   ```

3. 将 `ref` 绑定到 Textarea 组件上。

**预计**: ~4 min

---

### IU-11: 前端 — GrapesJS `insertVariable()` 方法

**文件**: `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`

**做什么**:

1. 扩展 `GrapesEmailEditorHandle` 接口：
   ```typescript
   export interface GrapesEmailEditorHandle {
     getHtml: () => string;
     getDesign: () => unknown;
     insertVariable: (text: string) => boolean;
   }
   ```

2. 在 `useImperativeHandle` 中实现：
   ```typescript
   insertVariable: (text: string) => {
     const editor = editorRef.current;
     if (!editor) return false;
     const selected = editor.getSelected();
     if (!selected) return false;
     const rte = editor.RichTextEditor;
     const rteToolbar = rte?.getToolbarEl();
     if (!rteToolbar || rteToolbar.style.display === 'none') return false;
     document.execCommand('insertText', false, text);
     return true;
   },
   ```

**预计**: ~4 min

---

### IU-12: 前端 — 变量 Badge onClick 分发逻辑

**文件**: `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`

**做什么**: 替换 `copyVariable()` 函数为 `handleVariableClick()`：

```typescript
const handleVariableClick = (name: string) => {
  const placeholder = `{{${name}}}`;
  if (editorMode === 'html') {
    insertAtCursor(htmlTextareaRef, placeholder, 'body_html');
  } else if (editorMode === 'text') {
    insertAtCursor(textTextareaRef, placeholder, 'body_text');
  } else {
    // 可视化模式
    const inserted = editorRef.current?.insertVariable(placeholder);
    if (!inserted) {
      void navigator.clipboard.writeText(placeholder);
      toast.info('请先在编辑器中选中文本区域，变量已复制到剪贴板');
    }
  }
};
```

更新 Badge 的 `onClick` 从 `copyVariable(v.name)` 改为 `handleVariableClick(v.name)`。

**预计**: ~3 min

---

## Dependencies & Sequencing

```
IU-1 ──→ IU-2（测试需要引用 TEMPLATE_VARIABLES）
IU-3 ──→ IU-4（RED → GREEN）
IU-1 + IU-4 ──→ IU-5（claim_due_emails 需要常量 + fallback）
IU-1 ──→ IU-6（sample_emails 映射修复）
IU-1 ──→ IU-7（API 返回 TEMPLATE_VARIABLES）
IU-7 ──→ IU-8（前端 API 方法）
IU-8 ──→ IU-9（前端消费 API）
IU-10（可与 IU-9 并行）
IU-11（可与 IU-9 并行）
IU-9 + IU-10 + IU-11 ──→ IU-12（组装分发逻辑）
```

**执行顺序**: IU-1 → IU-2 → IU-3 → IU-4 → IU-5 → IU-6 → IU-7 → IU-8 → IU-9 → IU-10 → IU-11 → IU-12

## Test Scenarios

### 后端（自动化）

| 场景 | 文件 | IU |
|------|------|----|
| 4 变量全部正确替换 | `test_email_template_rendering.py` | IU-2 |
| 变量值为 None 时替换为空 | `test_email_template_rendering.py` | IU-2 |
| body_html 空 → body_text 转 HTML | `test_email_template_rendering.py` | IU-3 |
| body_text 含 `<>&` 特殊字符时正确 escape | `test_email_template_rendering.py` | IU-3 |
| body_html 有内容时不触发 fallback | `test_email_template_rendering.py` | IU-3 |

### 前端（手动 QA）

| 场景 | IU |
|------|----|
| 变量列表显示 4 个（无 product_name） | IU-9 |
| HTML 模式：点击 Badge → 变量插入 textarea 光标位置 | IU-12 |
| 纯文本模式：同上 | IU-12 |
| 可视化模式：RTE 激活时插入到光标位置 | IU-12 |
| 可视化模式：RTE 未激活时 → toast + 复制 | IU-12 |

## Risks

| 风险 | 缓解 |
|------|------|
| GrapesJS RTE 检测方式可能因版本不同而失效 | `insertVariable` 返回 boolean，失败自动 fallback |
| `document.execCommand('insertText')` 已标记为 deprecated | GrapesJS RTE 内部仍依赖 execCommand，当前安全；长期需跟踪 |
| 变量 API 路由与 `{template_id}` 冲突 | 将 `/variables` 路由声明放在 `/{template_id}` 之前 |
| `requestAnimationFrame` 在 React 严格模式下的 textarea 光标恢复 | 通过 `rAF` 延迟到 DOM 更新后再设置 selection |
