## 1. 前端分页状态

- [x] 1.1 为 Admin 同行公司页增加 RED 测试，锁定 `20 / 50 / 100`、`showSizeChanger`、`showQuickJumper`、`page_size: pagination.pageSize`
- [x] 1.2 将 `PeersData` 的固定 `PAGE_SIZE` 改为分页状态 `{ current, pageSize }`
- [x] 1.3 更新 React Query key 与请求参数，使 `page` / `page_size` 都来自分页状态
- [x] 1.4 更新 Table pagination：开启每页数量选择、页码快跳、中文总数区间展示
- [x] 1.5 搜索和重置筛选时回到第 1 页，保留当前 `pageSize`

## 2. 后端参数保护

- [x] 2.1 为 Admin V3 raw companies 接口增加 RED 测试或源码约束，要求 `page_size <= 100`
- [x] 2.2 在 `list_v3_raw_companies` 路由参数上增加 `Query` 校验：`page >= 1`、`1 <= page_size <= 100`
- [x] 2.3 确认既有服务层 `LIMIT/OFFSET` 继续消费校验后的 `page_size`

## 3. 验证

- [x] 3.1 运行新增前端分页约束测试
- [x] 3.2 运行新增后端参数约束测试
- [x] 3.3 运行 Admin typecheck/build，确认页面类型无回归
- [x] 3.4 如本地 Admin 可启动，打开 `/collection/peers` 手工确认每页切换和跳页控件可见：Admin dev server 已启动到 `http://localhost:3002/`；浏览器访问 `/collection/peers` 被真实登录页拦截，未进入登录态内页面，分页控件以源码约束测试 + typecheck 验证。
