# Phase 0A+0C: @shared/ui 重构 + Admin 切换

> 完整规划见 `../../openspec/changes/tenant-nextjs-rewrite/design.md`（D-2 节）

## 目标

将 Admin 本地的 23 个 shadcn 组件提取到 `packages/shared-ui/`，让 Admin 和未来的 Tenant-next 共用同一套基础组件。

## 当前状态

- Admin 的 23 个 shadcn 组件在 `apps/admin/src/components/ui/`
- `packages/shared-ui/` 当前绑定 antd + react-router-dom（全部要删）
- Admin 的 `cn()` 工具函数在 `apps/admin/src/lib/utils.ts`
- Admin 的 CSS 变量在 `apps/admin/src/app/globals.css`
- Admin 的 tailwind 配置在 `apps/admin/tailwind.config.ts`

## 执行步骤

### Step 1: 重写 packages/shared-ui

1. **重写 `packages/shared-ui/package.json`**：
   - 删除所有 antd / @ant-design/icons / react-router-dom 依赖
   - 新增依赖：@radix-ui/react-alert-dialog, @radix-ui/react-avatar, @radix-ui/react-checkbox, @radix-ui/react-collapsible, @radix-ui/react-dialog, @radix-ui/react-dropdown-menu, @radix-ui/react-label, @radix-ui/react-scroll-area, @radix-ui/react-select, @radix-ui/react-separator, @radix-ui/react-slot, @radix-ui/react-switch, @radix-ui/react-tabs, @radix-ui/react-tooltip, clsx, tailwind-merge, class-variance-authority, lucide-react, react-day-picker, tailwindcss-animate
   - peerDependencies 保留 react + react-dom ^19，删除 react-router-dom
   - 保留 @shared/types 依赖（StatusTag 等业务组件需要）

2. **创建目录结构**：
   ```
   packages/shared-ui/src/
   ├── components/     ← 从 Admin 复制的 23 个 shadcn 组件
   ├── lib/utils.ts    ← cn() 函数
   ├── theme/
   │   ├── globals.css         ← CSS 变量（从 Admin globals.css 的 :root 部分提取）
   │   └── tailwind-preset.ts  ← 共享 Tailwind preset
   └── index.ts        ← 统一导出
   ```

3. **复制 Admin 的 23 个 ui 组件**到 `packages/shared-ui/src/components/`：
   - 所有组件文件保持原样复制
   - 每个组件内的 `@/lib/utils` import 改为 `../lib/utils`

4. **创建 `packages/shared-ui/src/lib/utils.ts`**：
   ```ts
   import { type ClassValue, clsx } from 'clsx'
   import { twMerge } from 'tailwind-merge'
   export function cn(...inputs: ClassValue[]) {
     return twMerge(clsx(inputs))
   }
   ```

5. **创建 `packages/shared-ui/src/theme/tailwind-preset.ts`**：
   从 `apps/admin/tailwind.config.ts` 提取 theme.extend 部分为 preset：
   ```ts
   import type { Config } from 'tailwindcss'
   import tailwindcssAnimate from 'tailwindcss-animate'
   const sharedPreset: Partial<Config> = {
     darkMode: ['class'],
     theme: { extend: { colors: { /* 从 admin tailwind.config 复制 */ }, borderRadius: { /* 同上 */ } } },
     plugins: [tailwindcssAnimate],
   }
   export default sharedPreset
   ```

6. **创建 `packages/shared-ui/src/theme/globals.css`**：
   从 `apps/admin/src/app/globals.css` 提取 `:root` CSS 变量部分（`--background` 到 `--radius`），以及 `* { @apply border-border; }` 和 body 基础样式。不包含 `.admin-page` 等 Admin 特有的 class。

7. **重写 StatusTag / RatingTag / ContactStatusTag**：
   - 当前在 `packages/shared-ui/src/` 某处，绑定 antd Tag 组件
   - 改为用 Badge 组件 + Tailwind class 实现
   - 保持相同的 props 接口（接收 status / rating 类型，输出对应颜色的标签）

8. **创建 `packages/shared-ui/src/index.ts`**：
   - 导出所有 23 个 shadcn 组件
   - 导出 StatusTag / RatingTag / ContactStatusTag
   - 导出 cn 函数
   - 不再导出 AppLayout / RequireAuth / PermissionGate / AIAccessGuard（直接删除这些文件）

9. **更新 `packages/shared-ui/tsconfig.json`**

### Step 2: Admin 切换到 @shared/ui

1. **修改 `apps/admin/tailwind.config.ts`**：
   ```ts
   import sharedPreset from '@shared/ui/theme/tailwind-preset'
   export default {
     presets: [sharedPreset],
     content: [
       './src/**/*.{ts,tsx}',
       '../../packages/shared-ui/src/**/*.{ts,tsx}',
     ],
     // 移除 theme.extend 中已在 preset 里的部分
     // 保留 Admin 特有的扩展（如有）
   }
   ```

2. **批量替换 Admin 中所有 `@/components/ui/xxx` 导入为 `@shared/ui`**：
   - `import { Button } from '@/components/ui/button'` → `import { Button } from '@shared/ui'`
   - 涉及约 18 个文件、21 种组件导入
   - grep 确认：`grep -r "@/components/ui/" apps/admin/src/ --include="*.tsx" --include="*.ts"`

3. **删除 `apps/admin/src/components/ui/` 目录**

4. **验证**：
   - `pnpm dev`（Admin）能正常启动
   - `pnpm build`（Admin）构建通过
   - 页面功能不变

## 约束

- 不改 Admin 的业务页面逻辑，只改 import 路径
- 不改 @shared/types 和 @shared/api
- `apps/admin/src/lib/utils.ts` 保留（Admin 可能有其他 util），但 cn() 改为从 @shared/ui re-export
- StatusTag 等业务标签组件保持相同的 props 接口
