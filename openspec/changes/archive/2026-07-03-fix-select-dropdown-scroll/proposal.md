# fix-select-dropdown-scroll

## Why

管理端「租户管理 → 域名/预热档位」的下拉在预热档位增至 19 档后撑破视口,底部档位无法选中。根因在共享组件 `frontend/packages/shared-ui/src/components/select.tsx`:Radix Select 封装缺少内容区最大高度约束和滚动按钮(Radix Viewport 默认隐藏滚动条,依赖 ScrollUp/DownButton 提供滚动),任何选项较多的下拉都会复现。

## What Changes

- `SelectContent` 增加最大高度:`min(24rem, var(--radix-select-content-available-height))`,超出即在 Viewport 内滚动(滚轮/键盘可用)
- 按 shadcn 标准配方补 `SelectScrollUpButton` / `SelectScrollDownButton`(悬停自动滚动的上下箭头)
- 共享组件修复,admin/tenant 两个前端所有下拉一并受益;调用方零改动

## Non-Goals

- 不改预热档位数据或档位数量
- 不改各页面的 Select 用法
- 不引入搜索/虚拟滚动等增强

## Impact

| 范围 | 影响 |
|------|------|
| 前端共享包 | shared-ui select.tsx 一个文件 |
| 部署 | 需重建 admin 前端镜像(A、B 两实例);tenant 镜像随下次常规构建带上 |
