## Context

优选客户页需要从占位实现升级为完整的群组管理页面。后端 groups CRUD 和 group_members 管理 API 已全部就绪，前端公司列表页已实现完整的筛选/表格/详情/群组操作。核心思路是最大化复用现有代码。

现有代码资产：
- 后端 `groups` 表 + `group_members` 表（`03_database/schema.sql:936-960`）
- 后端群组 API：CRUD + batch-add + batch-remove（`ops.py:304-398`）
- 后端 `companies_page()` 已有 25+ 字段、33 个筛选参数、分页排序（`tenant_query_service.py:136-388`）
- 前端 `groups.ts` API 客户端已完整（`shared-api/src/tenant/groups.ts`）
- 前端公司列表页（`companies/page.tsx`）有可复用的筛选逻辑和 CompanyDetail 组件

## Goals / Non-Goals

**Goals:**
- 后端 `GET /companies` 支持 `group_id` 过滤，复用全部现有逻辑
- 前端实现左右分栏布局的优选客户页
- 抽取 CompanyDetail 和 CompanyFilters 为共享组件
- 「从公司列表添加」弹窗支持完整筛选和多选

**Non-Goals:**
- 不改 groups 表结构
- 不引入 auto_rules 功能
- 不做移动端适配

## Decisions

### D1: 后端 group_id 过滤实现

在 `companies_page()` 方法中，当 `group_id` 参数存在时，追加 JOIN 和 WHERE 条件：

```sql
-- 现有查询的 FROM 子句已有：
FROM tenant_companies tc
JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id

-- 当 group_id 传入时，追加：
JOIN group_members gm ON gm.tenant_company_id = tc.id AND gm.group_id = :group_id
```

路由层只需在 `GET /companies` 加一个 `group_id: str | None = Query(None)` 参数并透传。

### D2: 前端页面结构

```
curated-customers/
  page.tsx                  # 主页面：左右分栏 + 群组状态管理
  add-company-modal.tsx     # 从公司列表添加弹窗

components/
  company-detail.tsx        # 从 companies/ 移出（共享）
  company-filters.tsx       # 从 companies/page.tsx 提取（共享）
```

### D3: 左侧群组面板数据流

```
┌─ GroupPanel ─────────────────────────────────┐
│                                               │
│  useQuery(['groups'])                         │
│    → tenantApi.groups.list()                  │
│    → 渲染群组列表                              │
│                                               │
│  selectedGroupId (state)                      │
│    → 点击群组项切换                             │
│    → 传给右侧面板作为 group_id 参数             │
│                                               │
│  新建群组:                                     │
│    → 弹窗输入 name + description               │
│    → tenantApi.groups.create()                │
│    → invalidate ['groups']                    │
│    → 自动选中新群组                             │
│                                               │
│  编辑群组 (hover 图标 / 标题区按钮):            │
│    → 弹窗编辑 name + description               │
│    → tenantApi.groups.update()                │
│    → invalidate ['groups']                    │
│                                               │
│  删除群组 (hover 图标 / 标题区按钮):            │
│    → 二次确认弹窗："仅删除群组，不影响公司数据"   │
│    → tenantApi.groups.delete()                │
│    → invalidate ['groups']                    │
│    → 选中第一个剩余群组                         │
└───────────────────────────────────────────────┘
```

### D4: 右侧公司列表数据流

```
┌─ CompanyList ────────────────────────────────┐
│                                               │
│  useQuery(['companies', { group_id, ...}])   │
│    → tenantApi.companies.list({              │
│         group_id: selectedGroupId,            │
│         page, page_size, ...filters           │
│       })                                      │
│    → 完全复用公司列表的字段/分页/排序           │
│                                               │
│  查看详情:                                     │
│    → setDetailId(company.id)                  │
│    → 打开 CompanyDetail Drawer                │
│                                               │
│  移除:                                        │
│    → 确认弹窗："将该公司从当前群组移除？"        │
│    → 直接用 company.tc_id 调 batch-remove     │
│    → invalidate companies + groups            │
└───────────────────────────────────────────────┘
```

### D5: 「从公司列表添加」弹窗数据流

```
┌─ AddCompanyModal ────────────────────────────┐
│                                               │
│  props: { groupId, open, onClose }           │
│                                               │
│  数据源:                                      │
│    → tenantApi.companies.list({              │
│         ...filters, page, page_size           │
│       })                                      │
│    → 不带 group_id，查全部公司                 │
│                                               │
│  已在群组的公司标记:                           │
│    → tenantApi.companies.list({              │
│         group_id: groupId                     │
│       })                                      │
│    → 或后端返回中带标记字段                    │
│    → 取全部公司的 tc_id 集合 ∩ 群组成员集合    │
│    → 交集中的公司 → checkbox 禁选 + 灰色行     │
│                                               │
│  选择 + 添加:                                 │
│    → selectedTcIds (state)                    │
│    → tenantApi.groups.batchAddMembers(        │
│         groupId, selectedTcIds                │
│       )                                       │
│    → invalidate companies + groups            │
│    → onClose()                                │
└───────────────────────────────────────────────┘
```

**关于已在群组中的公司禁选实现**：

有两种方案：
- **方案 A**: 前端两次请求（全部公司 + 群组内公司），前端做交集判断
- **方案 B**: 后端在 `companies_page` 返回中追加 `in_group_ids` 字段（当 `check_group_id` 参数传入时）

推荐方案 A——简单直接，无需改后端额外逻辑。群组成员数量有限（通常 < 200），前端取一次群组成员 tc_id 列表做 Set 判断即可。

### D6: 移除操作直接用 tc_id

后端 `batch-remove` 实际读取 `tenant_company_ids`（非 `member_ids`），右侧表格的 companies API 已返回 `tc_id` 字段。前端移除时直接传 `tc_id` 数组即可，无需额外的 `group_member_id`。

前端 `groups.ts` 的 `batchRemoveMembers` 需修复：`{ member_ids }` → `{ tenant_company_ids }`。

### D7: CompanyDetail 抽取策略

当前 `company-detail.tsx`（266 行）的 Props：
```typescript
interface Props {
  company: Company;
  onGroupAdd: (tcId: string, name: string) => void;
  onSaved: () => void;
}
```

抽取时 `onGroupAdd` 改为 optional——在优选客户页中，公司已在群组里，不需要"加入群组"按钮（或改为"加入其他群组"）。

移动路径：`companies/company-detail.tsx` → `components/company-detail.tsx`，原位置改为 re-export。

### D8: CompanyFilters 抽取范围

从 `companies/page.tsx` 提取的筛选逻辑包括：
- `FilterValues` 类型定义
- 筛选 UI 组件（2 行布局：搜索+多选+单选 / 范围输入+按钮）
- `buildParams()` 函数（将 FilterValues 转为 API query params）
- filters API 调用（`tenantApi.companies.filters()`）

抽取为 `components/company-filters.tsx`，接收 `onApply(filters)` 回调。

### D9: 添加弹窗多选状态规则

- **翻页保留选中**：用户在第 1 页勾选的公司，翻到第 2 页后仍保留（用 `Set<string>` 存 tc_id）
- **重新筛选清空选中**：点击「查询」按钮后清空已选项（筛选条件变化导致数据集变化，保留旧选择会造成困惑）
- **禁选项不可被选中**：已在群组中的公司 checkbox 始终禁用，不会进入 selectedTcIds
- **提交后刷新**：批量添加成功后，invalidate 右侧群组公司列表 + 群组列表（更新 member_count），关闭弹窗
