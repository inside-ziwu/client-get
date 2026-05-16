## Overview

本 change 只增强 Admin `/collection/peers` 同行公司页的分页控制。页面继续使用 Ant Design Table 内置分页，不引入新的通用分页组件。

## Decisions

- 分页状态由单一 `page` 改为 `{ current, pageSize }`。
- 默认每页 `20`；可选 `20 / 50 / 100`；最大值 `100`。
- Table pagination 开启 `showSizeChanger` 和 `showQuickJumper`。
- 查询参数发送当前 `page` 与 `page_size`，React Query key 同步包含两者。
- 切换筛选条件或重置筛选时回到第 1 页，并保留当前每页数量。
- 后端 `list_v3_raw_companies` 对 `page` 和 `page_size` 使用 FastAPI `Query` 约束：`page >= 1`，`1 <= page_size <= 100`。

## Data Flow

1. 用户在同行公司页切换每页数量或输入页码。
2. Ant Design Table 触发 `onChange(current, pageSize)`。
3. 页面更新分页状态。
4. React Query 以 `['admin', 'peers', current, pageSize, applied]` 重新请求。
5. API 调用 `/api/v1/raw/lixiaoyun/companies`，传入 `page` 与 `page_size`。
6. 后端按 `LIMIT page_size OFFSET (page - 1) * page_size` 返回数据与 total。

## Error Handling

- 若接口加载失败，沿用当前 `message.error('加载同行数据失败')` 与空页 fallback。
- 若用户或外部请求传入超过 100 的 `page_size`，后端返回参数校验错误，不执行大页查询。
- 若筛选后当前页可能越界，筛选提交和重置都回到第 1 页。

## Testing

- 前端源码约束测试覆盖：
  - 不再使用固定 `PAGE_SIZE` 作为请求页大小。
  - 查询 key 包含 `pageSize`。
  - 请求参数发送 `page_size: pagination.pageSize`。
  - Table pagination 开启 `showSizeChanger` 与 `showQuickJumper`。
  - 可选每页数量为 `20 / 50 / 100`。
- 后端测试或源码约束覆盖：
  - `list_v3_raw_companies` 的 `page_size` 通过 `Query(..., le=100)` 限制。

## Rollout

这是低风险 UI/API 参数约束改动，不需要数据库迁移。上线后用户刷新 Admin 页面即可使用新分页能力。
