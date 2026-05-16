# 03 · 运行时输入与敏感文件清单

> **目的**：列出代码运行起来需要的一切外部条件——环境变量、数据库、第三方服务、Sealos 资源、测试数据。
> **本次原则**：**绝不读取或输出 secret 内容**。仅记录文件路径、风险等级与处置建议。
> **盘点时间**：2026-05-04

## 1. 环境变量文件清单（路径与风险）

| 路径 | 类型 | 风险 | 标签 | 备注 |
| --- | --- | --- | --- | --- |
| `backend/.env` | 真实 .env | 🔴 高 | `[SENSITIVE]` | **未读取**。后端真实环境变量。需用户确认：(1) 是否在 backend 子仓库 `.gitignore` 内 (2) 是否含数据库连接、第三方 API key、JWT 签名密钥等 |
| `backend/.env.example` | 模板 | 🟢 低 | `[DOCS]` | 通常不含真实密钥；可作为字段清单参考 |
| `frontend/.env.example` | 模板 | 🟢 低 | `[DOCS]` | 前端工作区根模板 |
| `frontend/apps/tenant/.env.example` | 模板 | 🟢 低 | `[DOCS]` | tenant 应用模板 |
| `frontend/apps/admin/.env.example` | 模板 | 🟢 低 | `[DOCS]` | admin 应用模板 |
| `frontend/apps/tenant/.env.development` | 真实 dev env | 🟡 中 | `[CONFIRM?]` `[SENSITIVE?]` | **未读取**。需确认是否含开发用 API key 或仅指向本地 |
| `frontend/apps/admin/.env.development` | 真实 dev env | 🟡 中 | `[CONFIRM?]` `[SENSITIVE?]` | **未读取**，同上 |

> 📋 **本次未做的事**：未打开任何 `.env` / `.env.development` 文件；未将其内容输出到任何 markdown；未写入 memory。

> ⚠️ **建议**（不在本次执行）：
> - 在工作区根 `.gitignore` 已加入 `__pycache__/`、`node_modules/` 等通用项，但**没有显式排除** `.env`、`.env.development`、`.env.local` 等——若后续要把 backend 或 frontend 整个目录纳入根仓库，应先补全规则
> - 当前两个子仓库各自有独立 `.gitignore`，需用户单独验证

## 2. 数据库

### 2.1 类型（推测）

PostgreSQL（基于 blueprint 中多处提到 PG、Alembic、`schema.sql` 用 `partition` / RLS 等 PG 特性，未实际验证）。

### 2.2 迁移

- 工具：Alembic
- 配置：`backend/alembic.ini`
- 入口：`backend/alembic/env.py`
- 版本目录：`backend/alembic/versions/`（13 个版本，2026-04-21 ~ 2026-05-01）

### 2.3 Schema 设计

- `blueprint/03_database/schema.sql` —— 蓝图设计稿
- `backend/03_database/schema.sql` —— **MD5 与上一份相同**（重复拷贝）
- `blueprint/03_database/RLS_POLICY_MATRIX.md` —— 行级安全策略矩阵
- `blueprint/03_database/MIGRATION_ORDER_AND_NOTES.md` —— 迁移顺序

### 2.4 本地数据 dump

- 路径：`_control/inputs/database/`（**当前为空**）
- 工作区扫描中**未发现** `.dump` / `.sql.gz` / `.bak` / `.sqlite` 等数据库 dump 文件
- 需要时由用户拷贝进来；本次扫描中无需处理

---

## 3. 外部服务 / 第三方 API

> 基于 blueprint `02_architecture/BACKEND_ARCHITECTURE.md` 的提及（**未读全文，仅基于文件名+其他文件的提及**）：

| 服务 | 推测用途 | 文档线索 |
| --- | --- | --- |
| OpenRouter | AI 计费/模型路由 | `05_services/AI_BILLING_SERVICE_SPEC.md`、`13_AI_INTEGRATION_REPAIRED.md` |
| EngageLab | 邮件发送 + Webhook | `05_services/SENDING_WEBHOOK_SERVICE_SPEC.md` |
| 腾道（Tendata） | 反推海外买家富集 | `docs/spec-tendata-provider.md`、`docs/research/tendata-*` |
| 外贸通（WaiMaoTong） | 直采采集 | `docs/spec-collection-module.md`、`docs/plan-waimaotong-adapter.md` |
| 励销云（Lixiaoyun） | Stage 1 竞对查询 | `docs/spec-collection-module.md` 提及 |

> 🟡 `[CONFIRM?]` 各服务的鉴权方式、密钥位置、调用频率上限，**待用户提供**或读取 `.env` 时确认（本次不读）。

---

## 4. Sealos 部署

| 资源 | 路径 |
| --- | --- |
| 后端 Sealos 文档 | `backend/docs/SEALOS_DEPLOYMENT.md`（9KB） |
| 最佳实践 1 | `blueprint/docs/solutions/best-practices/sealos-direct-deployment-from-local-ghcr-images-2026-04-23.md` |
| 最佳实践 2 | `blueprint/docs/solutions/best-practices/sealos-devbox-clientget-deployment-with-app-launchpad-2026-04-23.md` |
| 本地资料收件箱 | `_control/inputs/sealos/`（**当前为空**） |

> 🟡 `[CONFIRM?]` 命名空间、AppLaunchpad 配置、镜像仓库地址（GHCR 还是其它）、kubeconfig 位置——**未发现 kubeconfig 文件**，可能只在用户本机 `~/.kube/config`。

---

## 5. 测试数据

- 路径：`_control/inputs/test-data/`（**当前为空**）
- 后端 `tests/` 25 个 .py 测试文件，是否使用 fixture / factory 数据，**未读代码确认**
- 演示数据脚本：`backend/scripts/seed_demo_data.py`

---

## 6. 容器与本地开发

| 文件 | 用途 |
| --- | --- |
| `backend/docker-compose.yml` | 本地开发 compose（可能含 PG 容器、redis 容器等服务定义，未读） |
| `backend/docker-compose.prod.yml` | 生产 compose |
| `backend/Dockerfile` | 后端镜像 |
| `frontend/Dockerfile.tenant` `Dockerfile.admin` | 前端镜像 |

---

## 7. 待确认（汇总到 `04-open-questions.md`）

- 🔴 `backend/.env` 是否在子仓库 .gitignore 内？是否需要轮换密钥？
- 🟡 `apps/{tenant,admin}/.env.development` 是否含敏感开发密钥？
- 🟡 `backend/docs/legacy_migration_report.json` 是否含数据库样本数据？应该入仓还是排除？
- 🟡 数据库类型确认（PG？版本？）
- 🟡 各第三方服务的鉴权方式与密钥来源
- 🟡 `_control/inputs/{database,sealos,test-data}/` 当前为空——**用户决定是否拷贝资料过来**
