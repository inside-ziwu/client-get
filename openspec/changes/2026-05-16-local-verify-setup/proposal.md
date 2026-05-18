## Why

在 worktree 上开发完成后无法本地验证：开发者本地无 PostgreSQL、后端未运行、无测试账号。当前只能部署到线上才能确认功能是否正确，反馈周期太长且有生产风险。

## What Changes

- 新增 `scripts/local-verify.sh` 一键脚本，完成"PG 启动 → 迁移 → seed → 后端 → 前端"全链路
- 每个 worktree/branch 使用独立数据库（`clientget_<branch_slug>`），共享同一个 PG 容器
- 复用现有 `backend/docker-compose.yml` 中的 postgres 服务，不另起新 compose
- 支持 `--reset-db` 重建当前分支数据库
- 支持 `--remote-api <url>` 模式（仅跑前端，连指定远端 API）

## Non-Goals

- 不替代线上部署流程和 CI/CD
- 不引入新的 Docker 镜像构建（后端直接本地 uvicorn）
- 不自动同步生产数据（prod sync 保持为显式独立操作）
- 不处理移动端/响应式测试
- 不修改现有部署脚本

## Capabilities

### New Capabilities

- `local-verify`: 本地一键验证能力（Docker PG + Alembic + seed + 后端 + 前端）

### Modified Capabilities

无

## Impact

| 路径 | 变更类型 | 说明 |
|------|---------|------|
| `scripts/local-verify.sh` | 新增 | 一键本地验证脚本 |
| `backend/docker-compose.yml` | 可能微调 | 确保 postgres 服务 healthcheck 可用 |
| `frontend/.env.example` | 无变更 | 已有正确的 localhost:8000 配置 |

- 无后端代码变更、无数据库 schema 变更、无 API 变更
- 依赖现有脚本：`bootstrap_platform_admin.py`、`seed_demo_data.py`
