# Pre-Deploy QA Smoke Report · v3-data-foundation

> 执行日期：2026-05-09  
> 执行范围：`pre-deploy-qa-smoke-test.md` 中可在当前环境执行的 P0/P1 项。  
> 结论：P0 通过；当前线上健康检查通过；当前线上尚未部署本次 V3 data foundation 新路由，因此新 V3 API 在线上 smoke 为 BLOCKED/未通过，需部署后重跑。

## 1. 总结

| 类别 | 结果 | 说明 |
|---|---|---|
| P0 自动化验证 | PASS | Alembic、后端测试、前端 type-check、OpenSpec validate 均通过 |
| P0 DB 结构 smoke | PASS | 业务库 `clientget` 已是 `20260508_0034`，14/14 核心表存在，关键字段齐，禁用字段不存在 |
| 前端生产构建 | PASS | admin / tenant Vite build 均通过 |
| 后端 app import | PASS | `create_app()` 可正常导入 |
| 线上健康检查 | PASS | backend `/health`、admin `/healthz`、tenant `/healthz` 均 200 |
| 线上新 V3 API smoke | BLOCKED / FAIL before deploy | 当前线上新路由返回 404，说明线上镜像尚未包含本次代码；部署后必须重跑 |
| 认证后页面/API smoke | BLOCKED | 当前未提供真实 admin/tenant 登录 token，未执行认证后页面操作 |

## 2. P0 自动化验证结果

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| P0-1 | Alembic 当前版本 | PASS | `20260508_0034 (head)` |
| P0-2 | 后端 schema/API/关键词测试 | PASS | `9 passed in 15.84s` |
| P0-3 | 前端类型检查 | PASS | `pnpm -r type-check` 全部 Done |
| P0-4 | OpenSpec strict validate | PASS | `Change 'v3-data-foundation' is valid` |
| P0-5 | OpenSpec task 状态 | PASS with pending sign-off | `29/30`，仅剩 `T-DF-92 用户签字确认` |

后端测试命令：

```bash
uv run pytest tests/test_v3_data_foundation_schema.py tests/test_v3_data_foundation_api_contract.py tests/test_keyword_service.py -v
```

结果：

```text
9 passed
```

## 3. P0 数据库结构 Smoke

| 检查项 | 结果 | 证据 |
|---|---|---|
| 目标库 Alembic 版本 | PASS | `alembic_version=20260508_0034` |
| 核心表存在 | PASS | `tables=14/14` |
| 缺失表 | PASS | `missing=none` |
| `tenant_keyword` 必需字段 | PASS | `missing_columns=none` |
| `collection_runs` 必需字段 | PASS | `missing_columns=none` |
| `collection_tasks` 必需字段 | PASS | `missing_columns=none` |
| `tenant_contacts` 必需字段 | PASS | `missing_columns=none` |
| raw company 禁用字段 | PASS | `forbidden_present=none` |
| `clean_companies` 禁用字段 | PASS | `forbidden_present=none` |
| `tenant_companies` 禁用字段 | PASS | `forbidden_present=none` |
| `tenant_contacts.tenant_company_id` | PASS | `forbidden_present=none` |

## 4. 构建与启动 Smoke

| 检查项 | 结果 | 证据 |
|---|---|---|
| admin 生产构建 | PASS | `pnpm build:admin` 成功 |
| tenant 生产构建 | PASS | `pnpm build:tenant` 成功 |
| 后端 app import | PASS | `app_import_ok True` |

## 5. 线上环境 Smoke

| 检查项 | 结果 | 证据 |
|---|---|---|
| backend health | PASS | `GET https://api.xinanpcb.com/health` → HTTP 200，`{"status":"ok"}` |
| tenant healthz | PASS | `HEAD https://tenant.xinanpcb.com/healthz` → HTTP 200 |
| admin healthz | PASS | `HEAD https://admin.xinanpcb.com/healthz` → HTTP 200 |
| admin HTML | PASS | `GET https://admin.xinanpcb.com/` 返回 SPA HTML |
| tenant HTML | PASS | `GET https://tenant.xinanpcb.com/login?slug=t-019dc236` 返回 SPA HTML |

备注：`HEAD https://admin.xinanpcb.com/` 曾超时，但 `GET` 返回 HTML 成功，`/healthz` 也为 200，因此不作为阻塞项。

## 6. 线上 API Smoke

| 路径 | 结果 | 说明 |
|---|---|---|
| `GET /admin/api/v1/collection-keywords` | PASS for auth boundary | HTTP 401 `缺少授权令牌`，说明旧兼容路由存在且鉴权生效 |
| `GET /admin/api/v1/raw/tendata/companies?page_size=1` | BLOCKED / not deployed | HTTP 404 |
| `GET /admin/api/v1/clean/companies?source_type=tendata&page_size=1` | BLOCKED / not deployed | HTTP 404 |
| `GET /api/v1/raw/tendata/companies?page_size=1` | BLOCKED / not deployed | HTTP 404 |
| `GET /api/v1/clean/companies?source_type=tendata&page_size=1` | BLOCKED / not deployed | HTTP 404 |

解释：

当前线上 backend 仍未暴露本次新增的 V3 raw/clean contract 路由。结合本地测试和 DB 结构已通过，最可能原因是线上 backend 镜像尚未更新到本次代码。该项不能算 QA 通过，必须在部署新 backend 镜像后重跑。

## 7. 未执行 / Blocked 项

| 项 | 状态 | 原因 |
|---|---|---|
| 认证后 admin raw/clean 页面操作 | BLOCKED | 当前未提供真实登录态 / token |
| 认证后 tenant 关键词、客户列表、详情、联系人页面操作 | BLOCKED | 当前未提供真实登录态 / token |
| 部署后新 V3 API smoke | BLOCKED | 当前线上尚未部署本次 backend 代码 |
| Sealos pod 日志检查 | BLOCKED | 当前没有 Sealos 控制台 / pod log 访问上下文 |

## 8. Go / No-Go 判断

| 判断 | 结论 |
|---|---|
| 是否可以说 QA 全通过 | 否 |
| 是否可以直接宣布线上可用 | 否 |
| 是否可以进入部署窗口 | 可以，前提是接受“部署后必须重跑 P1 API/UI smoke” |
| 是否需要部署后复测 | 必须 |

推荐发布顺序：

1. 备份目标业务库。
2. 部署 backend 新镜像。
3. 执行 / 确认 `alembic current` 为 `20260508_0034 (head)`。
4. 重跑线上 API smoke，尤其：
   - `GET /admin/api/v1/raw/tendata/companies?page_size=1`
   - `GET /admin/api/v1/clean/companies?source_type=tendata&page_size=1`
   - tenant keywords / companies / detail / contacts 认证后接口。
5. 部署 admin / tenant 前端新镜像。
6. 登录 admin / tenant 做页面 smoke。
7. 全部 P0/P1 通过后，再签 `QA smoke accepted for v3-data-foundation`。

