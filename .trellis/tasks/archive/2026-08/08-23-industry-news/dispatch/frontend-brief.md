# 前端工人任务书（行业动态 · PR A · A10–A12）

你是本仓库「行业动态」功能的**前端实现工人**，运行在一个独立的 git worktree 里（协调者通过 Orca 终端读取你的输出并做评审与提交）。全部用中文沟通；注释与测试描述也用中文。

## 先读（按顺序）

1. `AGENTS.md` 与 `.trellis/spec/frontend/index.md`（按其「开发前检查清单」读完对应 spec：directory-structure、design-system、component-guidelines、state-management、type-safety、quality-guidelines）
2. `.trellis/tasks/08-23-industry-news/prd.md`（R1 租户页、R2 管理端监控页、验收 AC1–AC5）
3. `.trellis/tasks/08-23-industry-news/design.md`（v3：§4 API 契约——这是你唯一的后端依赖；§5 前端全部细节）
4. `.trellis/tasks/08-23-industry-news/implement.md`（A10、A11、A12 三行的产出与验证）
5. `.trellis/tasks/08-23-industry-news/research/design-review-frontend.md`（五件套真实契约的逐条核证：FilterBar 没有布尔 kind、TableState 空态文案不可定制、Pagination 真实签名、用 `<a target="_blank">` 而非 `window.open`、`clickedIds` 替代乐观更新、admin 预取 key 用字面量……全部照做）

## 你的范围

**只做 implement.md 的 A10–A12**：`shared-types` / `shared-api` / `queryKeys.industryNews`（只新增，不删旧 `intelligence`）、租户页 `apps/tenant/src/app/(dashboard)/industry-news/page.tsx` + 导航替换 + Vitest `test/industry-news/industry-news-page.test.tsx`、管理端 `apps/admin/src/app/(dashboard)/industry-news-sources/{page,client-page}.tsx` + 导航改名 + `ai-config/client-page.tsx` 过滤 `intelligence_summary`。**不做**：后端任何文件、PR B 的删除、spec / README 修改。

后端接口可能尚未就绪：按 design §4 的契约编码，测试全部 mock `@/lib/api`（模板 `apps/tenant/test/intelligence/intelligence-page.test.tsx`）。

## 硬规则

- **禁止 `git commit` / `git push` / 切分支**；改完留在工作区。
- 不创建 / 修改任何 `.env*`；不连接后端或数据库。
- UI 原语只从 `@shared/ui` 引入；用五件套；不散写像素列宽与颜色 class；五态可区分；图标按钮有 `aria-label`。
- 每完成一步跑门禁：`cd frontend && pnpm type-check`；改 tenant 后 `pnpm --filter @apps/tenant test`；改 admin 后 `pnpm build:admin`。失败先修再继续。

## 步骤

0. `cd frontend && pnpm install --frozen-lockfile`。
1. A10 → A11 → A12，每步按 implement.md 的验证命令收尾。
2. 全部完成后打印：

```
## 完成报告
- 改动文件清单（新增 / 修改）
- 门禁输出摘要（type-check / vitest 用例数 / build）
- 与 design 的偏离（如有，说明原因）
- 留给协调者的事项
```

遇到无法决定的问题：不要猜，打印 `## 阻塞：<问题>` 后停下等待协调者指令。不要自行扩大范围。
