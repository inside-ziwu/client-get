# Wave 2 统一部署 Checklist（完整版）

> 创建日期：2026-05-07 | 版本：V3 Wave 2 | Gate 8：✅ 已签字，可上线

---

## 零、部署前准备

### 0.1 本地环境确认

```bash
# 确认 Docker 已启动
docker info

# 登录阿里云镜像仓库（如 token 过期需重新登录）
docker login crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com
```

### 0.2 生产数据库备份（必须先做）

> 在有 SYNC_DATABASE_URL 权限的环境下执行，或在 Sealos backend Pod 终端里执行：

```bash
pg_dump -Fc $SYNC_DATABASE_URL > clientget-pre-wave2-$(date +%Y%m%d%H%M).dump
ls -lh clientget-pre-wave2-*.dump   # 确认文件大小非零
```

---

## 一、构建并推送镜像

> 全部在本地执行。push 脚本会自动生成 `YYYY.MM.DD-rN` 格式 tag 并打印，**记录下来**备用。

### 1.1 Backend 镜像（API + 全部 Worker 共用）

```bash
cd /path/to/backend
bash scripts/push-backend.sh
```

输出示例（记录此 tag）：
```
✅ 推送完成: crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-backend:2026.05.07-r1
```

### 1.2 Admin 前端镜像

```bash
cd /path/to/frontend
bash deploy/push-admin.sh
```

### 1.3 Tenant 前端镜像

```bash
cd /path/to/frontend
bash deploy/push-tenant.sh
```

---

## 二、Sealos 环境变量配置

> ⚠️ **在更新镜像之前完成**。  
> 进入每个应用的「环境变量」页面逐条核对，只列 key——value 自行填写。

### 2.1 Backend API 应用

以下是所有必需的 key。**已有** = 之前已配置，只需确认存在；**🆕 Wave 2 新增** = 本次必须新加。

| Key | 状态 | 说明 |
|-----|------|------|
| `APP_ENV` | 已有 | 值为 `production` |
| `DEBUG` | 已有 | 值为 `false` |
| `DATABASE_URL` | 已有 | `postgresql+asyncpg://...` 格式 |
| `SYNC_DATABASE_URL` | 已有 | `postgresql+psycopg://...` 格式（供 alembic 使用） |
| `JWT_SECRET` | 已有 | 随机强密码 |
| `JWT_EXPIRE_HOURS` | 已有 | 默认 `24` |
| `ADMIN_EMAIL` | 已有 | 平台管理员账号 |
| `ADMIN_PASSWORD` | 已有 | 平台管理员密码 |
| `ALLOWED_ORIGINS` | 已有 | 逗号分隔，须包含 admin 前端域名和 tenant 前端域名 |
| `DATA_SOURCE_ENCRYPTION_KEY` | 已有 | 32 位十六进制字符串 |
| `INTERNAL_SERVICE_SECRET` | 已有 | 内部服务密钥 |
| `ENGAGELAB_WEBHOOK_SECRET` | 已有 | Webhook 验签密钥 |
| `ENGAGELAB_BASE_URL` | 已有 | EngageLab API 地址，如 `https://email.engagelab.cc` |
| `ENGAGELAB_API_USER` | 🆕 **Wave 2 新增** | EngageLab HTTP Basic 鉴权用户名 |
| `ENGAGELAB_CREDENTIAL` | 🆕 **Wave 2 新增** | EngageLab HTTP Basic 鉴权密码 |

> **不需要配置**：`ENGAGELAB_SENDER`（已从代码移除），`ENGAGELAB_API_KEY`（旧 Bearer 兜底，可选）

### 2.2 Sending Worker 应用

与 Backend API 共享以下 key（确认存在即可）：

| Key | 状态 | 说明 |
|-----|------|------|
| `APP_ENV` | 已有 | `production` |
| `DATABASE_URL` | 已有 | 同 backend |
| `SYNC_DATABASE_URL` | 已有 | 同 backend |
| `ENGAGELAB_BASE_URL` | 已有 | 同 backend |
| `ENGAGELAB_API_USER` | 🆕 **Wave 2 新增** | 同 backend |
| `ENGAGELAB_CREDENTIAL` | 🆕 **Wave 2 新增** | 同 backend |

> Sending Worker 的**启动命令**确认为（Sealos 应用配置里核对）：
> ```
> python scripts/run_sending_worker.py --sleep-seconds 10
> ```

### 2.3 Collection Worker 应用

| Key | 状态 |
|-----|------|
| `APP_ENV` | 已有 |
| `DATABASE_URL` | 已有 |
| `SYNC_DATABASE_URL` | 已有 |
| `COLLECTION_WORKER_SLEEP_SECONDS` | 已有（默认 10） |
| `COLLECTION_TASK_LEASE_SECONDS` | 已有（默认 300） |
| `COLLECTION_WORKER_LIMIT` | 已有（默认 20） |
| `COLLECTION_HEARTBEAT_INTERVAL_SECONDS` | 已有（默认 30） |

> 启动命令：
> ```
> python scripts/run_collection_worker.py --sleep-seconds 10 --lease-seconds 300 --limit 20 --heartbeat-interval-seconds 30
> ```

### 2.4 Collection Scheduler 应用

| Key | 状态 |
|-----|------|
| `APP_ENV` | 已有 |
| `DATABASE_URL` | 已有 |
| `SYNC_DATABASE_URL` | 已有 |
| `COLLECTION_SCHEDULER_SLEEP_SECONDS` | 已有（默认 30） |

> 启动命令：
> ```
> python scripts/run_collection_scheduler_worker.py --sleep-seconds 30
> ```

### 2.5 Scoring Worker 应用

| Key | 状态 |
|-----|------|
| `APP_ENV` | 已有 |
| `DATABASE_URL` | 已有 |
| `SYNC_DATABASE_URL` | 已有 |

> 启动命令：
> ```
> python scripts/run_scoring_worker.py --sleep-seconds 10
> ```

### 2.6 Admin 前端 / Tenant 前端

无后端环境变量。`VITE_API_BASE_URL=https://api.xinanpcb.com` 已在构建时通过 `--build-arg` 注入镜像，无需 Sealos 配置。

---

## 三、数据库迁移

> **时机**：更新 Backend 镜像之后、Worker 更新之前。  
> **方式**：Sealos 控制台 → Backend 应用 → 进入 Pod 终端

### 3.1 进入 Backend Pod 终端

Sealos 控制台 → 找到 Backend 应用 → 点「详情」→「Terminal」（或 Pod 列表里点进去）

### 3.2 执行迁移

```bash
# 先确认当前 alembic 状态
alembic current
# 期望：20260507_0015 (head)

# 执行升级
alembic upgrade head

# 验证完成
alembic current
# 期望：20260507_0021 (head) (mergepoint)
```

Wave 2 会按顺序执行 8 个迁移：

| 版本 | 内容 | 类型 |
|------|------|------|
| `0016` | keyword_master + tenant_keyword 表 | DDL |
| `0017` | collection_keywords.keyword_master_id FK + 数据回填 | DDL + DML |
| `0025` | tenant_companies 评分调整字段 + CHECK 约束 | DDL |
| `0026` | scoring_templates.industry 列 | DDL |
| `0027` | tenant_scoring_weights 表 + RLS | DDL |
| `0029` | 职位分类三级表 + v_tenant_contact_classified 视图 | DDL |
| `0020` | emails 表 D-041 追踪列（6 个） | DDL |
| `0021` | email_events 索引 + 合并双头为单 head | DDL + merge |

### 3.3 如果 Backend Pod 启动失败

> 若新镜像因迁移未完成而启动失败，执行以下步骤：
> 1. 在崩溃的 Pod 日志里确认是否有迁移相关报错
> 2. 通过「Exec」进入崩溃前的容器（或使用 `kubectl exec`）运行 `alembic upgrade head`
> 3. 回到 Sealos 重启该应用

---

## 四、Sealos 应用滚动更新顺序

> 必须按顺序，**不要并行更新**。

### Step 1：更新 Backend API

Sealos → Backend 应用 → 修改镜像 tag → 保存 → 等待 Pod Running

```
镜像：crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-backend:<一.一节的tag>
```

确认 Pod 状态为 Running 后，执行 §三 的数据库迁移。

### Step 2：更新 4 个 Worker（顺序无要求，同一镜像）

- Scoring Worker → 同一 backend 镜像 tag
- Collection Scheduler → 同一 backend 镜像 tag
- Collection Worker → 同一 backend 镜像 tag
- Sending Worker → 同一 backend 镜像 tag

### Step 3：更新 Admin 前端

```
镜像：crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-admin:<一.二节的tag>
```

### Step 4：更新 Tenant 前端

```
镜像：crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com/lay_inside/clientget-tenant:<一.三节的tag>
```

---

## 五、上线后验证

### 5.1 API 健康检查

```bash
curl https://api.xinanpcb.com/health
# 期望：{"status": "ok", ...}
```

### 5.2 D-035 渠道白名单验证

```bash
curl -X POST https://api.xinanpcb.com/api/admin/collection-keywords/trigger \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"keyword_normalized": "pcb", "channel": "waimao_tong"}'
# 期望：400 {"error": {"code": "CHANNEL_NOT_AVAILABLE"}}
```

### 5.3 Admin 前端功能确认

- [ ] 访问 Admin URL → 采集任务页 → 直采行触发按钮已禁用，Tooltip 显示"外贸通采集 V3.1+ 可用"
- [ ] 访问 Admin URL → 侧边栏出现「职位分类」菜单项 → 点进去三列布局正常渲染
- [ ] Admin → 租户管理 → 创建租户弹窗含「发件域名」和「预热档位 1-6」字段

### 5.4 Tenant 前端功能确认

- [ ] 租户端 → 邮件监控页 → 6 张统计卡（发送量/送达率/独立打开率/软退信率/举报率/退订率）正常渲染

### 5.5 Backend 日志检查

Sealos → Backend Pod → 查看最近日志，确认：
- [ ] 无 `ERROR` 级别启动报错
- [ ] 无 `EngageLabSendError`（若有邮件任务）

---

## 六、回滚方案（如需）

### 场景 A：Backend 启动失败（迁移前）

```bash
# Sealos 切回上一个镜像 tag
# 无需回滚迁移（迁移尚未执行）
```

### 场景 B：迁移执行后，Backend 异常

```bash
# 在 Pod 终端执行
alembic downgrade 20260507_0015

# 然后 Sealos 切回旧镜像
```

### 场景 C：数据正确性问题

```bash
# 1. 停所有应用（Sealos 将副本数设为 0）
# 2. 恢复 pg_dump 备份
pg_restore -d $SYNC_DATABASE_URL clientget-pre-wave2-<时间戳>.dump
# 3. Sealos 切回旧镜像，副本数恢复
```

---

## 七、完成签字

- [ ] §零 备份文件已生成，大小非零
- [ ] §一 3 个镜像推送成功，tag 已记录
- [ ] §二 ENGAGELAB_API_USER + ENGAGELAB_CREDENTIAL 已在 Backend 和 Sending Worker 中配置
- [ ] §三 `alembic current` 输出 `20260507_0021 (head) (mergepoint)`
- [ ] §四 7 个 Sealos 应用全部 Running
- [ ] §五 全部验证项通过
- [ ] `_control/v3/06-v3-release-manifest.md` §1 镜像 tag 已回填
