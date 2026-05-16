先读 `docs/AGENT_PROGRESS.md`。

当前已经完成：

1. 后端仓内验收通过
2. 前端 Admin/Tenant 页面接入真实 API
3. demo seed 修正为合法登录邮箱
4. 上线前 README / env / deploy / rollback 文档已补齐
5. 前端 Vite production build 大包 warning 已处理，不再重复做相同分析
6. Docker 主机发布演练已跑通，不要再重复排查容器内 `localhost:5432` 连接失败
7. 充值/流水账本已废弃，OpenRouter 已切到“每租户一把 key”的前后端合同
8. Admin/Tenant 已有真实 OpenRouter 配置页面；不要再恢复 `/billing/*` 或充值入口
9. 采集已经拆成独立运行单元骨架：
   - `collection-scheduler`
   - `collection-worker`
   - `mark-failed` / `lease 回收` 已落地
   - Docker / Sealos 文档已纳入这两个单元
10. sending 的 `failed/released` send lock 已支持重新占用，不要再按“重试永远卡死”这个旧前提分析

如果下一轮继续，优先级如下：

1. 如果继续补完采集：
   - 接入真实 `waimao_tong` provider
   - 明确 provider credential 读取与轮换策略
   - 视情况补 `tengdao` / `lixiaoyun` adapter
   - 再跑一轮从关键词到 prospects 入库的端到端 smoke
2. 如果继续收尾上线：
   - 补真实反向代理配置样例
   - 做预发布域名下的 CORS / webhook / worker 常驻验收
   - 重新跑浏览器级 smoke，重点看 Admin 租户 OpenRouter 配置、Tenant 设置页与 AI 禁用态，以及采集监控页
3. 如果拿到真实第三方文档：
   - 更新 EngageLab 发送适配器字段映射
   - 补 OpenRouter management key / key limit 真实验收说明
4. 如果开始发布前压测或视觉验收：
   - 增加更细的浏览器级 smoke / e2e
   - 当前机器的 Playwright MCP 受 `/.playwright-mcp` 只读限制，优先换可写环境
5. 如果开始真实数据迁移：
   - 扩展 `backend/scripts/migrate_legacy.py`

进入下一轮前建议先重跑：

```bash
cd backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build postgres backend collection-scheduler collection-worker scoring-worker sending-worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python -m alembic -c alembic.ini upgrade head
uv run pytest -q
uv run python scripts/run_collection_scheduler_worker.py --once
uv run python scripts/run_collection_worker.py --once
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python scripts/seed_demo_data.py

cd ../frontend
VITE_API_BASE_URL=http://127.0.0.1:8000 pnpm build
pnpm type-check
pnpm --filter @apps/admin preview -- --host localhost --port 4173
pnpm --filter @apps/tenant preview -- --host localhost --port 4174
```

当前 demo 登录账号：

- `admin@example.com` / `change-me-now`
- `globex-pcb` / `owner@globex.example.com` / `ChangeMe123!`
- `acme-pcb` / `owner@acme.example.com` / `ChangeMe123!`
