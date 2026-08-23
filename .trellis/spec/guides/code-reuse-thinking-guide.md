# 代码复用思考指南

## 先找再写：本仓库已有的件

**后端**
- 筛选 SQL：`services/company_filter_sql.py`；联系人工具：`services/tenant_contact_utils.py`。
- 审计：`AuditService.write(conn, action=, entity_type=, entity_id=, platform_user_id=, new_value=)`。
- AI 用量：`AiUsageLogService.create_pending / complete / fail`；租户 AI 闸门：`TenantAiProviderService.assert_feature_available`。
- 时间：`utils/beijing_time.py`；清洗：`utils/html_sanitizer.py`、`utils/email_text.py`；国家：`utils/country.py`。
- 响应 / 错误：`core/responses.py`、`core/errors.py`；id：`core/ids.new_uuid()`；密文：`core/crypto.encrypt_secret / decrypt_secret`。
- worker 骨架：`SendingWorker`（注入式构造）、`run_wmt_lineage_repair_loop`（lifespan 循环 + 实例锁）。
- 只读真库脚本骨架：`scripts/schema_snapshot.py`（psycopg `read_only` + 二次校验）。

**前端**
- 原语与五件套：`@shared/ui`（导出清单 `packages/shared-ui/src/index.ts`）。
- API：`@shared/api` 按领域分文件；`queryKeys` 工厂。
- hooks：`useAuthStore`、`usePermission`、`useCursorPagination`。
- admin SSR 壳：`createPrefetchPage`、`serverApi`。
- 格式化：各 app 的 `lib/format.ts`（时间、金额；两端尚未合并，不要在表格组件里猜时区 / 单位）。

## 抽取时机

- 同一模式第二次出现且语义相同 → 抽到对应共享位置（后端 `services/<主题>_utils.py` 或 `utils/`；前端 `packages/shared-*`）。
- 只在一个 app / 一个 service 用 → 就地放，不提前抽象（KISS）。
- 抽取后至少有一个既有调用方切换过去，否则是死代码。

## 不要"复用"的

- 跨 provider 共享 `WHERE` 分支引用对方已删除的列——分支必须按 provider 拆开。
- Pattern 组件里塞 React Query / 路由 / 业务枚举——组件只管展示与受控交互。
- 把外部剪报式数据和自有数据混在一张表里而不标来源。
