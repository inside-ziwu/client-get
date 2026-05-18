## S1: 一键启动完整本地环境

**Given** 开发者在任意 worktree/branch 上，本地有 Docker 可用，脚本可从仓库任意目录执行
**When** 执行 `scripts/local-verify.sh tenant` 或 `scripts/local-verify.sh admin` 或 `scripts/local-verify.sh both`
**Then**
- 脚本自动定位仓库根目录（`git rev-parse --show-toplevel`）
- PG 容器启动并通过 healthcheck（检测 5432 端口是否被占用）
- 创建当前分支专属数据库 `clientget_<branch_slug>`（已存在则跳过）
- DB 名规则：小写、非法字符替换为下划线、截断到 63 字节、碰撞时加 hash 后缀
- Alembic 迁移执行到 head
- 平台管理员初始化完成（bootstrap_platform_admin）
- Demo 数据 seed 完成（seed_demo_data）
- 后端 uvicorn 在 localhost:8000 启动
- 对应前端 dev server 启动（admin=3000, tenant=3001）
- 终端打印登录地址和测试账号信息
- 后端 /health 端点响应正常

**备注：** 并行 worktree 只隔离数据库，不支持同时运行服务（端口固定 8000/3000/3001）

## S2: 每个 worktree 独立数据库

**Given** 两个 worktree 分别在 branch `feat-a` 和 `feat-b`
**When** 各自执行 `scripts/local-verify.sh tenant`
**Then**
- `feat-a` 使用 `clientget_feat_a` 数据库
- `feat-b` 使用 `clientget_feat_b` 数据库
- 两者 schema 互不影响

## S3: 重置数据库

**Given** 当前分支数据库已存在但 schema 损坏或需要干净状态
**When** 执行 `scripts/local-verify.sh tenant --reset-db`
**Then**
- 终止当前分支数据库的所有活动连接（`pg_terminate_backend`）
- 删除当前分支专属数据库
- 重新创建并完成迁移 + seed
- 后续流程正常启动

## S4: 仅前端连远端 API

**Given** 开发者只改了前端代码，需要连接已有后端
**When** 执行 `scripts/local-verify.sh tenant --remote-api http://staging.example.com`
**Then**
- 不启动 PG、不迁移、不启动后端
- 前端 dev server 启动，NEXT_PUBLIC_API_BASE_URL + NEXT_PUBLIC_ADMIN_API_BASE_URL 指向指定 URL
- admin rewrites、tenant API client 均通过环境变量解析，所有路由指向远端
- 如果 URL 包含生产域名，脚本报错并要求显式 `--allow-prod-api` 确认

**前端配置修复（已完成）：**
- admin `next.config.ts` rewrites 改为环境变量降级链（对齐 tenant 模式）
- shared-api 清除 `VITE_API_BASE_URL` / `import.meta.env` 残留
- tenant/auth.ts login 改用相对路径

## S5: 端口冲突处理

**Given** 5432、8000 或 3000/3001 端口已被占用
**When** 执行脚本
**Then**
- 脚本检测端口占用（5432 用于 PG、8000 用于后端、3000/3001 用于前端）
- 打印清晰错误信息（哪个端口被哪个进程占用）
- 脚本退出，不强制 kill

## S6: 优雅退出

**Given** 脚本正在运行（后端+前端）
**When** 用户按 Ctrl-C
**Then**
- 后端进程被终止
- 前端进程被终止
- PG 容器保留运行（数据持久化，下次启动更快）
- 无孤儿进程残留
