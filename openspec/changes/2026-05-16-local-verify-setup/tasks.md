## 1. 脚本核心逻辑

- [ ] 1.1 创建 `scripts/local-verify.sh`：参数解析（tenant/admin/both, --reset-db, --remote-api, --allow-prod-api, --db-name）
- [ ] 1.2 脚本开头用 `git rev-parse --show-toplevel` 定位仓库根目录，所有相对路径基于它
- [ ] 1.3 实现分支名 → DB 名转换逻辑（小写、非法字符替换为下划线、截断到 63 字节、碰撞时加 hash 后缀）
- [ ] 1.4 实现 Docker PG 启动：先 `docker container inspect clientget-postgres` 检测状态，已运行则跳过，已停止则 `docker start`，不存在则 `docker compose -f backend/docker-compose.yml up -d postgres` 并等待 healthcheck
- [ ] 1.5 实现 DB 创建/重置：通过 `docker exec clientget-postgres psql` 执行 createdb；`--reset-db` 时先 `pg_terminate_backend` 断开活动连接再 dropdb + createdb
- [ ] 1.6 实现迁移链路：`SYNC_DATABASE_URL=.../clientget_<slug> uv run alembic upgrade head`（从 backend/ 目录执行）
- [ ] 1.7 实现 seed 链路：`DATABASE_URL=.../clientget_<slug> uv run python scripts/bootstrap_platform_admin.py` → `seed_demo_data.py`
- [ ] 1.8 实现后端启动：`DATABASE_URL=... SYNC_DATABASE_URL=... uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`（后台，PID 记录）
- [ ] 1.9 实现前端启动：从 frontend/ 目录执行 `pnpm --filter @clientget/admin dev` 或 `pnpm --filter @clientget/tenant dev`（端口由 package.json 控制：admin=3000, tenant=3001）
- [ ] 1.10 实现 `--remote-api` 模式：跳过 DB/后端，设置 NEXT_PUBLIC_API_BASE_URL + NEXT_PUBLIC_ADMIN_API_BASE_URL，检测生产域名

## 2. 稳健性

- [ ] 2.1 端口冲突检测：启动前检查 5432/8000/3000/3001 是否被占用，打印占用进程信息
- [ ] 2.2 信号处理：trap SIGINT/SIGTERM，清理后端/前端子��程（PG 容器保留）
- [ ] 2.3 依赖����：脚本开头检测 docker、uv、pnpm 是否可用，缺失时报错退出并提示安装方式
- [ ] 2.4 打印启动摘要：登录 URL、测试账号（admin@example.com / change-me-now + owner@acme.example.com / ChangeMe123!）

## 3. Docker Compose 确认

- [ ] 3.1 ��认 `backend/docker-compose.yml` 中 postgres 服务 healthcheck 配置正确（已有）
- [ ] 3.2 确认 postgres 数据卷持久化配置正确（已有 clientget_postgres_data volume）

## 4. 前端 API 配置修复（--remote-api 前置）

- [x] 4.1 admin `next.config.ts`：rewrites destination 改为环境变量降级链 `ADMIN_API_REWRITE_TARGET → NEXT_PUBLIC_ADMIN_API_BASE_URL → NEXT_PUBLIC_API_BASE_URL → 'http://localhost:8000'`
- [x] 4.2 shared-api `client.ts`：移除 `import.meta.env.VITE_API_BASE_URL` fallback
- [x] 4.3 shared-api `tenant/auth.ts`：login URL 改用相对路径（不依赖 VITE 环境变量）
- [x] 4.4 清理 `vite-env-shim.d.ts`（admin + tenant）和 `shared-api/src/vite-env.d.ts` 中的 VITE_API_BASE_URL 声明

## 5. 验证

- [ ] 4.1 在干净状态执行 `scripts/local-verify.sh tenant`，确认全链路通过
- [ ] 4.2 测试 `--reset-db` 重建数据库后正常启动
- [ ] 4.3 测试 Ctrl-C ��出无孤儿进程
- [ ] 4.4 测试端口被占用时的错误提示（包括 5432��
- [ ] 4.5 在不同 branch 名下验证 DB 名��离
- [ ] 4.6 测试 `--remote-api` 模式启动，验证 API 请求指向远端
- [ ] 4.7 测试 `--remote-api` 加生产域名被拒绝
- [ ] 4.8 测试容器已存在但已停��时能正确 start
- [ ] 4.9 测试���赖缺���（卸载 docker/uv/pnpm 其一）时的报错提示
- [ ] 4.10 启动后���证登录：curl 后端 /health、确认 demo 账号可登录
