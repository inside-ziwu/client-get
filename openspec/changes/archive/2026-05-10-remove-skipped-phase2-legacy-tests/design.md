## Context

本地验证显示，直接依赖 `login_admin()` 的 10 个测试文件运行结果为 `10 passed, 9 skipped`。9 个 skipped 均来自测试文件内显式 `pytest.mark.skip`，原因是依赖已移除的 `shared_companies` 或尚未实现的 Phase 2 CRM 功能。

## Goals / Non-Goals

**Goals:**

- 删除这些当前无验证价值的 skipped legacy 测试，减少测试输出噪音。
- 保留仍能验证当前 V3 行为的测试。
- 保持改动简单，不做测试框架重构。

**Non-Goals:**

- 不恢复旧 `shared_companies` schema。
- 不实现 Phase 2 CRM、发送、评分旧链路。
- 不修改业务代码来迎合旧测试。
- 不删除仍然 pass 的测试。

## Decisions

- 直接删除整文件：这些 skipped 测试文件的有效测试内容均围绕旧 Phase 2/CRM 依赖，保留文件只会继续产生 skipped 噪音。
- 不改为 xfail：xfail 仍会保留旧行为作为未来暗示，但这些行为不属于当前 V3 schema 权威。
- 用现有 admin-login 测试集合验证：删除后重跑同一集合，确认没有由这批 legacy 文件带来的 skipped。

## Risks / Trade-offs

- [历史覆盖丢失] 旧 Phase 2 行为的测试被删除后，未来恢复相关功能时需要重新按当前 schema 设计测试。缓解：OpenSpec change 记录删除原因和范围。
- [误删仍有价值测试] 删除前只针对显式 skipped 且 skip reason 指向 `shared_companies` / Phase 2 CRM 的文件。缓解：删除后运行 admin-login 相关测试集合。
