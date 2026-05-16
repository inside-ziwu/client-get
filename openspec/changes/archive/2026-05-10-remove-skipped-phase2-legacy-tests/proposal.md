## Why

当前后端 admin-login 相关测试集合里有 9 个显式 skipped 的旧 Phase 2 / `shared_companies` 测试。这些测试依赖已移除或尚未恢复的旧 CRM 行为，会让当前验证结果长期带着无实际信号的 skipped 噪音。

## What Changes

- 删除 9 个已显式标记 skipped 的旧 Phase 2 测试文件或测试模块。
- 保留当前仍可运行并代表现行 V3 schema 的 admin、tenant、auth、settings、intelligence 测试。
- 不修改业务代码，不恢复 `shared_companies`，不实现 Phase 2 CRM 功能。
- 重新运行直接依赖 `login_admin()` 的测试集合，确认 admin 种子账号问题已排除且 skipped 数量不再由这些旧测试贡献。

## Capabilities

### New Capabilities

- `test-suite-governance`: 约束当前测试集合不保留已知无效、长期 skipped 的旧 schema 测试。

### Modified Capabilities

- 无。

## Impact

- 后端测试文件：删除旧 Phase 2 / `shared_companies` skipped 测试。
- 不影响 API、数据库 schema、业务服务或生产部署。
