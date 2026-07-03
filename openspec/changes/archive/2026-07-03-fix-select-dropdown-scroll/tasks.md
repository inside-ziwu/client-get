## 1. 组件修复

- [x] 1.1 `SelectContent` 增加 `max-h-[min(24rem,var(--radix-select-content-available-height))]`,保持 popper 定位
- [x] 1.2 新增 `SelectScrollUpButton` / `SelectScrollDownButton` 并纳入 `SelectContent` 结构(shadcn 标准配方)
- [x] 1.3 admin 应用 TypeScript 编译通过;本地 dev(18 档)浏览器实测:内容区 384px、viewport 可滚、滚动到底选中「档位 18」成功

## 2. 发布

- [x] 2.1 B admin 镜像已重建并部署(instanceB-r2,后由 instanceB-r3 迭代取代)
- [x] 2.2 A admin 镜像 `2026.07.03-r1` 已构建并部署
- [x] 2.3 生产实测通过:B 管理端 19 档滚动可选(实际操作中选中过 14/18 档)
