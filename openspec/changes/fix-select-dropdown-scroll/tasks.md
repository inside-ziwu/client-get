## 1. 组件修复

- [x] 1.1 `SelectContent` 增加 `max-h-[min(24rem,var(--radix-select-content-available-height))]`,保持 popper 定位
- [x] 1.2 新增 `SelectScrollUpButton` / `SelectScrollDownButton` 并纳入 `SelectContent` 结构(shadcn 标准配方)
- [x] 1.3 admin 应用 TypeScript 编译通过;本地 dev(18 档)浏览器实测:内容区 384px、viewport 可滚、滚动到底选中「档位 18」成功

## 2. 发布

- [ ] 2.1 合入 main 后重建 Instance B admin 镜像(api_url 指向 B 后端)并更新容器
- [ ] 2.2 重建 Instance A admin 镜像(默认 api_url)供 A 更新
- [ ] 2.3 在 B 管理端确认预热档位下拉可滚动、19 档全部可选
