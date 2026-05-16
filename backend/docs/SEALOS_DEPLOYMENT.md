# Sealos 部署指南

## 推荐架构

不要把当前仓库的 `docker compose` 直接原样搬到 Sealos。

推荐按 Sealos 官方的“数据库 + 应用管理”模型拆成 8 个部署单元：

1. Sealos `PostgreSQL`
2. `clientget-backend`
3. `clientget-collection-scheduler`
4. `clientget-collection-worker`
5. `clientget-scoring-worker`
6. `clientget-sending-worker`
7. `clientget-admin`
8. `clientget-tenant`

推荐域名：

- `api.example.com`
- `admin.example.com`
- `tenant.example.com`

前端统一使用：

```env
VITE_API_BASE_URL=https://api.example.com
```

## 官方文档

- Compose 迁移：https://sealos.run/docs/guides/app-launchpad/docker-compose-migration
- 安装应用：https://sealos.run/docs/guides/app-launchpad/create-app
- PostgreSQL：https://sealos.run/docs/guides/databases/postgresql
- 环境变量：https://sealos.run/docs/guides/app-launchpad/environments
- 自定义域名：https://sealos.run/docs/guides/app-launchpad/add-a-domain
- 证书：https://sealos.run/docs/guides/app-launchpad/custom-certificates

## 一. 创建 PostgreSQL

在 Sealos 控制台中：

1. 进入 `数据库`
2. 新建 `Postgres`
3. 建议起始配置：
   - 副本：`1`
   - CPU：`1C`
   - 内存：`2Gi`
   - 存储：`10Gi`
4. 记录以下连接信息：
   - `Host`
   - `Port`
   - `Username`
   - `Password`
5. 如果数据库中还没有 `clientget`，在 Sealos 数据库终端执行：

```sql
CREATE DATABASE clientget;
```

## 二. 构建并推送镜像

> 本节命令默认从工作区根目录 `/Users/lay/Documents/Github/client_get` 执行。

### 后端镜像

> **Apple Silicon 必须指定 `--platform linux/amd64`**，否则推上去的是 ARM64 镜像，Sealos x86_64 节点无法运行，pod 启动时报 `exec format error`。

```bash
cd backend
docker buildx build --platform linux/amd64 \
  -t ghcr.io/<your-org>/clientget-backend:<tag> \
  --push .
```

### 前端镜像

> 同上，必须加 `--platform linux/amd64`。`VITE_API_BASE_URL` 在构建期烧进 JS bundle，**不能**在运行时通过环境变量修改，修改 API 地址需要重新构建镜像。

Admin：

```bash
docker buildx build --platform linux/amd64 \
  -f frontend/Dockerfile.admin \
  --build-arg VITE_API_BASE_URL=https://api.example.com \
  -t ghcr.io/<your-org>/clientget-admin:<tag> \
  --push \
  frontend/
```

Tenant（推荐直接使用自动化脚本，见下）：

```bash
docker buildx build --platform linux/amd64 \
  -f frontend/Dockerfile.tenant \
  --build-arg VITE_API_BASE_URL=https://api.example.com \
  -t ghcr.io/<your-org>/clientget-tenant:<tag> \
  --push \
  frontend/
```

**Tenant 前端推荐使用 `frontend/deploy/push-tenant.sh`**，脚本自动生成 `YYYY.MM.DD-rN` tag、硬编码 `--platform linux/amd64`、无需手动维护版本号：

```bash
bash frontend/deploy/push-tenant.sh
# 输出完整镜像地址，复制到 Sealos 控制台即可部署
```

## 三. 部署 backend

在 Sealos `应用管理 -> 新建应用` 中创建：

- 应用名：`clientget-backend`
- 镜像：`ghcr.io/<your-org>/clientget-backend:<tag>`
- 实例：`1`
- CPU / 内存：建议 `1C / 1Gi` 起步
- 容器端口：`8000`
- 外网访问：开启
- 启动命令：

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

环境变量建议直接批量粘贴：

```env
APP_ENV=production
DEBUG=false
JWT_SECRET=<strong-secret>
JWT_EXPIRE_HOURS=24
ADMIN_EMAIL=<admin-email>
ADMIN_PASSWORD=<admin-password>
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/clientget
SYNC_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:<port>/clientget
ALLOWED_ORIGINS=https://admin.example.com,https://tenant.example.com
DATA_SOURCE_ENCRYPTION_KEY=<32-char-secret>
INTERNAL_SERVICE_SECRET=<strong-secret>
ENGAGELAB_WEBHOOK_SECRET=<strong-secret>
ENGAGELAB_BASE_URL=https://email.api.engagelab.cc
ENGAGELAB_SEND_PATH=/v1/mail/send
ENGAGELAB_API_USER=<engagelab-api-user>
ENGAGELAB_CREDENTIAL=<engagelab-api-key>
ENGAGELAB_API_KEY=
ENGAGELAB_AUTH_HEADER=Authorization
ENGAGELAB_AUTH_SCHEME=Bearer
ENGAGELAB_TIMEOUT_SECONDS=10
COLLECTION_SCHEDULER_SLEEP_SECONDS=30
COLLECTION_WORKER_SLEEP_SECONDS=10
COLLECTION_TASK_LEASE_SECONDS=300
COLLECTION_WORKER_LIMIT=20
COLLECTION_HEARTBEAT_INTERVAL_SECONDS=30
```

说明：

- Sealos 上不要继续使用 `DOCKER_DATABASE_URL`
- OpenRouter 不再使用全局环境变量；上线后在页面里按租户配置
- EngageLab 发信优先使用 `ENGAGELAB_API_USER` + `ENGAGELAB_CREDENTIAL` 生成 HTTP Basic Auth；生产 Sealos Secret 修改和真实发信必须由操作者明确触发，不随普通代码 apply 自动执行。

### backend 首次初始化

应用 running 后，进入 Sealos 终端执行：

```bash
python -m alembic -c alembic.ini upgrade head
python scripts/bootstrap_platform_admin.py
```

如果是演示环境，再额外执行：

```bash
python scripts/seed_demo_data.py
```

## 四. 部署 worker

### scoring worker

- 应用名：`clientget-scoring-worker`
- 镜像：与 backend 相同
- 外网访问：关闭
- 实例：`1`
- 启动命令：

```bash
python scripts/run_scoring_worker.py --sleep-seconds 10
```

如果 Sealos 应用管理把参数错误地合并成一个字符串，改成显式 shell 包裹，避免 `python` 把整串参数当成脚本路径：

```bash
sh -c 'python scripts/run_scoring_worker.py --sleep-seconds 10'
```

环境变量与 backend 保持一致。

### collection scheduler

- 应用名：`clientget-collection-scheduler`
- 镜像：与 backend 相同
- 外网访问：关闭
- 实例：`1`
- 启动命令：

```bash
python scripts/run_collection_scheduler_worker.py --sleep-seconds 30
```

如果 Sealos 应用管理把 `Args` 当成单个字符串传给容器，改成下面的写法，避免出现 `python: can't open file '/app/scripts/run_collection_scheduler_worker.py --sleep-seconds 30'`：

```bash
sh -c 'python scripts/run_collection_scheduler_worker.py --sleep-seconds 30'
```

环境变量与 backend 保持一致。

### collection worker

- 应用名：`clientget-collection-worker`
- 镜像：与 backend 相同
- 外网访问：关闭
- 实例：`1`
- 启动命令：

```bash
python scripts/run_collection_worker.py --sleep-seconds 10 --lease-seconds 300 --limit 20 --heartbeat-interval-seconds 30
```

如果 Sealos 应用管理会把整串参数作为一个 `Args` 元素传入，改成：

```bash
sh -c 'python scripts/run_collection_worker.py --sleep-seconds 10 --lease-seconds 300 --limit 20 --heartbeat-interval-seconds 30'
```

环境变量与 backend 保持一致，并额外建议显式配置：

```env
COLLECTION_SCHEDULER_SLEEP_SECONDS=30
COLLECTION_WORKER_SLEEP_SECONDS=10
COLLECTION_TASK_LEASE_SECONDS=300
COLLECTION_WORKER_LIMIT=20
COLLECTION_HEARTBEAT_INTERVAL_SECONDS=30
```

### sending worker

- 应用名：`clientget-sending-worker`
- 镜像：与 backend 相同
- 外网访问：关闭
- 实例：`1`
- 启动命令：

```bash
python scripts/run_sending_worker.py --sleep-seconds 10
```

如果 Sealos 应用管理错误合并参数，改成：

```bash
sh -c 'python scripts/run_sending_worker.py --sleep-seconds 10'
```

环境变量与 backend 保持一致。

## 五. 部署 Admin 前端

在 Sealos `应用管理 -> 新建应用` 中创建：

- 应用名：`clientget-admin`
- 镜像：`ghcr.io/<your-org>/clientget-admin:<tag>`
- 实例：`1`
- CPU / 内存：建议 `0.2C / 256Mi`
- 容器端口：`80`
- 外网访问：开启

这个镜像内已经使用 `deploy/nginx-spa.conf` 做了 SPA 路由回退，不需要再额外配置 Nginx。

## 六. 部署 Tenant 前端

- 应用名：`clientget-tenant`
- 镜像：`ghcr.io/<your-org>/clientget-tenant:<tag>`
- 实例：`1`
- CPU / 内存：建议 `0.2C / 256Mi`
- 容器端口：`80`
- 外网访问：开启

## 七. 绑定域名

推荐绑定：

- `api.example.com` -> `clientget-backend`
- `admin.example.com` -> `clientget-admin`
- `tenant.example.com` -> `clientget-tenant`

Sealos 的典型流程：

1. 应用先开启外网访问
2. Sealos 自动分配公网域名
3. 在 DNS 服务商将你的域名 `CNAME` 到 Sealos 分配域名
4. 回到 Sealos 绑定自定义域名

如果使用 Sealos 默认 TLS，不需要手工传证书。

## 八. 发布检查

### 后端

- `https://api.example.com/health` 返回正常
- `alembic upgrade head` 已执行
- 平台管理员已 bootstrap
- backend 日志中无连续 5xx

### Worker

- `clientget-collection-scheduler` running
- `clientget-collection-worker` running
- `clientget-scoring-worker` running
- `clientget-sending-worker` running
- 四个 worker 日志中无持续异常退出

### 前端

- Admin 登录成功
- Tenant 登录成功
- Admin 租户管理页能加载
- Tenant `Dashboard / Templates / Email Monitor / Settings -> OpenRouter` 能加载

### 第三方

- EngageLab 如果未配置，发送页应显示真实不可用态
- 需要启用 AI 的租户，已由平台管理员或租户管理员写入 OpenRouter key

## 九. 更新发布

1. 推新镜像 tag
2. 进入 Sealos 应用详情
3. 点击 `变更`
4. 替换镜像 tag
5. 保存发布

不要只用 `latest`，使用 `YYYY.MM.DD-rN` 格式固定 tag（同一天多次构建时递增 N）：

- `clientget-backend:2026.04.24-r1`
- `clientget-backend:2026.04.24-r2`

## 十. 常见坑

1. 不要把 repo 里的 `postgres` 容器一起搬上 Sealos
2. 不要使用 `DOCKER_DATABASE_URL`
3. 不要把 `localhost` 留在 `ALLOWED_ORIGINS`
4. 不要忘记执行数据库迁移和管理员初始化
5. 前端不要直接按普通静态文件托管，除非你确认托管层支持 SPA fallback
