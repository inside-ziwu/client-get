# Tasks: fix-tenant-warmup-level-hardcode

## 1. Schema 放开档位上限

- [x] 1.1 修改 `backend/app/schemas/tenants.py` `TenantCreateRequest.warmup_level`：去掉 `le=6`，保留 `ge=1`，description 改为"起始预热档位（以当前实例激活预热规则的档位为准，默认 1）"

## 2. 服务层按激活规则校验并写入真实日限

- [x] 2.1 修改 `backend/app/services/tenant_service.py` `create_tenant`：删除档位钳制 `max(1, min(6, …))` 与硬编码日限映射 `_warmup_daily_limits`
- [x] 2.2 `sender_domain` 非空时，事务内按 design.md D2 的 SQL 查询当前实例激活规则档位（`instance_id` + `is_active = true` + `level = :warmup_level`，`ORDER BY wr.updated_at DESC LIMIT 1`）
- [x] 2.3 查不到时 `raise AppError(code="VALIDATION_ERROR", status_code=422)`，消息指引检查当前实例激活预热规则与档位配置（确认 `tenant_service` 已 import `AppError`，缺则补）
- [x] 2.4 查到时以真实 `daily_limit` 写入 `domain_warmup_status`，INSERT 补充 `warmup_rule_id`、`level_changed_at = now()` 两列，保留 `ON CONFLICT (tenant_id, domain) DO NOTHING` 与 `verification_status = 'pending'`

## 3. 测试

- [x] 3.1 新增 `backend/tests/test_tenant_create_warmup.py`（AsyncMock 风格，参照 `test_domain_crud_service.py`），覆盖 spec 场景：档位存在（7 档）→ INSERT 参数含真实 `daily_limit` / `warmup_rule_id` / `warmup_level=7`；档位不存在（99）→ 抛 `AppError` 422 且无 `domain_warmup_status` INSERT；无激活规则 → 422；`sender_domain` 为空 → 不做档位查询、不 INSERT
- [x] 3.2 同文件补 schema 用例：`TenantCreateRequest` 接受 `warmup_level=7`，拒绝 `warmup_level=0`
- [x] 3.3 检查既有测试对 `create_tenant` 的 `conn.execute` 调用序 mock 是否受新增查询影响（如 `test_tenant_instance_isolation.py`），受影响则同步修正

## 4. 验证

- [x] 4.1 运行后端测试：`cd backend && python -m pytest tests/test_tenant_create_warmup.py tests/test_tenant_instance_isolation.py tests/test_domain_crud_service.py -q`，全部通过
- [x] 4.2 全量回归：`cd backend && python -m pytest -q`，无新增失败
- [x] 4.3 对照 spec 场景逐条核对实现（`openspec/changes/fix-tenant-warmup-level-hardcode/specs/tenant-domain-warmup-bootstrap/spec.md`），输出「原始需求 → 已实现/未实现」对照
