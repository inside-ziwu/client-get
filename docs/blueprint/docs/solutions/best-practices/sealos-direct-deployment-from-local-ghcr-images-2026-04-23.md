---
title: Sealos 通过本地构建私有镜像（GHCR / 阿里云 ACR）直接部署 ClientGet 正式环境
date: 2026-04-23
last_updated: 2026-04-24
category: best-practices
module: clientget_deployment
problem_type: best_practice
component: development_workflow
severity: medium
applies_when:
  - 本地才是主要开发环境，不使用 DevBox 承载正式运行
  - 需要把 backend、admin、tenant 和 workers 拆成独立 Sealos 应用
  - 使用 GHCR 或阿里云 ACR 私有镜像和 Sealos PostgreSQL
  - 国内网络访问 GHCR 不稳定，需要切换到阿里云 ACR
tags: [sealos, ghcr, acr, aliyun, deployment, app-launchpad, amd64, healthz, workers, docker-buildx]
---

# Sealos 通过本地构建私有镜像（GHCR / 阿里云 ACR）直接部署 ClientGet 正式环境

## Context
最终跑通的不是 DevBox 路线，而是：本地开发、本地构建镜像、推送到私有仓库（GHCR 或阿里云 ACR），再在 Sealos 应用管理中直接部署正式环境。

**registry 选型**：GHCR（`ghcr.io/inside-ziwu/`）适合国际环境；阿里云 ACR（`crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/`）在国内网络更稳定，Sealos 节点拉取速度更快。两者可并用，也可只用 ACR。

会话历史补充确认了以下高频踩坑点：(session history)

- 默认在 Apple Silicon 上直接 `docker build` 推送的镜像是 `linux/arm64`，Sealos 节点无法正常拉起；必须显式指定 `--platform linux/amd64`。
- Sealos 同时填写 `Registry` 字段和完整镜像地址时，会把镜像拼成 `ghcr.io/ghcr.io/...` 或 `crpi-xxx.../crpi-xxx.../...`，直接导致拉取失败。
- PostgreSQL 服务地址是对的，但数据库名一度误填成 `clientgetdb`；实际业务数据库名是 `clientget`。
- sending worker 没复制完整环境变量时，会回退去连 `localhost:5432`，表现成 worker 连本地数据库失败。
- 企业 VPN / 代理会拦截 `docker login` 到 ACR 的 TLS 握手，表现为 DNS 解析到 `198.18.0.x`（被劫持 IP）；解法是关闭 VPN 后刷新 DNS，或切换到手机热点再执行 push。(session history)

## Guidance

### 通用原则
1. 以镜像作为正式交付物，不以源码目录作为正式交付物。backend、admin、tenant 分别构建镜像；4 个 worker 复用 backend 镜像。
2. 在 Apple Silicon 本机构建正式镜像时，必须显式输出 `linux/amd64`。

### 推送到 GHCR

```bash
docker buildx build --platform linux/amd64 \
  -t ghcr.io/inside-ziwu/clientget-backend:<tag> \
  --push \
  backend/
```

需要先 `docker login ghcr.io` 并使用 GitHub PAT（`write:packages` 权限）。

### 推送到阿里云 ACR

**第一步：登录 ACR**

```bash
docker login crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com
# 用户名：阿里云账号（如 RAM 子账号）
# 密码：固定密码（在 ACR 控制台”访问凭证”中设置）
```

> **踩坑**：如果开启了企业 VPN，`docker login` 可能因 TLS 拦截失败。关闭 VPN 后运行 `sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder` 刷新 DNS，或直接切换到手机热点执行。(session history)

**第二步：构建并推送**

前端镜像需要在构建时传入 `VITE_API_BASE_URL`（构建期变量，烧进 JS bundle，无法运行期修改）：

```bash
# Admin 前端
docker buildx build --platform linux/amd64 \
  --build-arg VITE_API_BASE_URL=https://api.xinanpcb.com \
  -t crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-admin:<tag> \
  --push \
  -f frontend/Dockerfile.admin \
  frontend/

# Tenant 前端
docker buildx build --platform linux/amd64 \
  --build-arg VITE_API_BASE_URL=https://api.xinanpcb.com \
  -t crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-tenant:<tag> \
  --push \
  -f frontend/Dockerfile.tenant \
  frontend/

# Backend
docker buildx build --platform linux/amd64 \
  -t crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-backend:<tag> \
  --push \
  backend/
```

### 自动化部署脚本 push-tenant.sh

手动拼命令容易遗漏 `--platform` 或用错 tag 格式。`frontend/deploy/push-tenant.sh` 封装了完整流程：自动生成 `YYYY.MM.DD-rN` tag、硬编码 `--platform linux/amd64`、传入 `VITE_API_BASE_URL`，并维护 `.tenant-rev` 状态文件实现当天内自动累加修订号。

```bash
# 用法：在 repo 根目录执行
bash frontend/deploy/push-tenant.sh
# 输出：✅ 推送完成: crpi-xxx.../clientget-tenant:2026.04.24-r2
# 将打印的 tag 复制到 Sealos 控制台镜像字段，保存即部署。
```

脚本核心逻辑（`.tenant-rev` 文件记录 `TODAY:REV`，每天重置为 r1，当天累加）：

```bash
#!/usr/bin/env bash
set -euo pipefail

REGISTRY="crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com"
REPO="lay_inside/clientget-tenant"
API_URL="https://api.xinanpcb.com"
DOCKERFILE="Dockerfile.tenant"
REV_FILE="$(dirname "$0")/.tenant-rev"

TODAY=$(date +%Y.%m.%d)

if [[ -f "$REV_FILE" ]]; then
  SAVED=$(cat "$REV_FILE")
  SAVED_DATE="${SAVED%%:*}"
  SAVED_REV="${SAVED##*:}"
else
  SAVED_DATE=""
  SAVED_REV=0
fi

if [[ "$SAVED_DATE" == "$TODAY" ]]; then
  REV=$((SAVED_REV + 1))
else
  REV=1
fi

TAG="${TODAY}-r${REV}"
FULL_IMAGE="${REGISTRY}/${REPO}:${TAG}"

cd "$(dirname "$0")/.."

docker buildx build \
  --platform linux/amd64 \
  -f "${DOCKERFILE}" \
  --build-arg VITE_API_BASE_URL="${API_URL}" \
  -t "${FULL_IMAGE}" \
  --push \
  .

echo "${TODAY}:${REV}" > "$REV_FILE"
echo "✅ 推送完成: ${FULL_IMAGE}"
```

> `.tenant-rev` 是本地构建机状态文件，应加入 `.gitignore`，不提交。

**层缓存复用**：同一版本若已推送到 GHCR，再推到 ACR 时所有层均 CACHED，整个 push 约 2-3 秒完成，无需重新 build。

**同时推送两个 registry**（一条命令，两个 `-t`）：

```bash
docker buildx build --platform linux/amd64 \
  --build-arg VITE_API_BASE_URL=https://api.xinanpcb.com \
  -t ghcr.io/inside-ziwu/clientget-admin:<tag> \
  -t crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-admin:<tag> \
  --push \
  -f frontend/Dockerfile.admin \
  frontend/
```

### Sealos 配置要点
3. 私有镜像在 Sealos 中必须绑定可拉取凭证（image pull secret）；缺少凭证时典型报错是 `401 Unauthorized` 或 `FailedToRetrieveImagePullSecret`。
4. 如果 Sealos 页面有单独的 `Registry` 字段，镜像名**不要再带** registry 前缀；否则会出现重复拼接（如 `ghcr.io/ghcr.io/...`）。
5. backend、admin、tenant 优先使用镜像自己的默认 `CMD`，在 Sealos 的”运行命令 / 命令参数”里留空更稳。
6. backend 的数据库连接串必须指向 Sealos PostgreSQL 服务地址，而不是 `localhost`。区分”数据库服务名”和”真实数据库名”：服务 host 是 `clientgetdb-postgresql.ns-3umexz0o.svc:5432`，真实数据库名是 `clientget`。
7. backend 首次 running 后，必须补两步初始化：

```bash
python -m alembic -c alembic.ini upgrade head
python scripts/bootstrap_platform_admin.py
```

8. admin 和 tenant 的健康检查路径是 `/healthz`，不是 `/health`（`/health` 是 backend 的）。
9. admin 页面路由没有 `/admin`；`/admin` 只是 backend API 前缀，管理端页面入口访问 `/` 或 `/login`。
10. admin/tenant 的登录联调必须等正式域名闭环完成后再测：`api.xinanpcb.com` 可访问、前端构建时写入正确 API 域名、backend 的 `ALLOWED_ORIGINS` 包含前端域名。
11. 4 个 worker 都应复用 backend 的完整环境变量，并关闭外网访问；不要只拷数据库地址的子集，否则容易回退默认值。

## Why This Matters
这条路线解决的不是”把容器拉起来”这么简单，而是把正式环境里最容易反复踩的坑一次性收口：

- 镜像架构不对，Sealos 根本起不来。
- 私有仓库凭证没配对，应用会卡在拉镜像阶段。
- 数据库名、host、CORS、构建期变量没理顺时，backend 可能健康检查正常，但前端和 worker 仍然不可用。
- worker 没有完整继承 backend 环境变量时，问题会伪装成”数据库挂了”，实际上只是应用回退到了默认值。
- 国内网络下 GHCR 拉取不稳定时，及时切换到 ACR 可以避免部署卡死，但如果没有文档记录 ACR 推送流程和踩坑点，每次都需要重新摸索。

## When to Apply
- 本地才是主要开发环境，不准备长期依赖 DevBox 承载生产流程。
- 目标平台是 Sealos 应用管理，而不是原样搬运 `docker compose`。
- 需要把 backend、admin、tenant、workers 拆成独立正式单元。
- 使用私有仓库（GHCR 或阿里云 ACR），通过 image pull secret 拉取镜像。
- Sealos 从 GHCR 拉取镜像超时或失败，需要切换到 ACR。

## Examples

**tag 命名规范**：`<service>:<YYYY.MM.DD>-r<N>`，例如 `2026.04.23-r3`。

**GHCR 镜像**：
- `ghcr.io/inside-ziwu/clientget-backend:2026.04.23-r3`
- `ghcr.io/inside-ziwu/clientget-admin:2026.04.23-r3`
- `ghcr.io/inside-ziwu/clientget-tenant:2026.04.23-r2`

**阿里云 ACR 镜像**：
- `crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-backend:2026.04.23-r3`
- `crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-admin:2026.04.23-r3`
- `crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-tenant:2026.04.23-r2`

**健康检查**：
- backend：`https://api.xinanpcb.com/health`
- admin / tenant：`https://admin.xinanpcb.com/healthz`、`https://tenant.xinanpcb.com/healthz`

**sending worker 的典型正确命令**：

```bash
python scripts/run_sending_worker.py --sleep-seconds 10
```

- 如果 worker 日志里出现 `127.0.0.1:5432` 或 `localhost:5432`，优先检查是否完整复制了 backend 环境变量，而不是先怀疑 Sealos PostgreSQL 本身。

## Related
- 现有 DevBox 路线经验：
  `docs/solutions/best-practices/sealos-devbox-clientget-deployment-with-app-launchpad-2026-04-23.md`
- backend 部署说明：
  `backend/docs/SEALOS_DEPLOYMENT.md`
