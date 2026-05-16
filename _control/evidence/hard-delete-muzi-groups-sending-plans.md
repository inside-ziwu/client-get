# hard-delete-muzi-groups-sending-plans 执行证据

记录时间：2026-05-11 06:24:49 CST

## 本地实现验证

- `cd backend && .venv/bin/python -m ruff check app/services/tenant_hard_delete_service.py scripts/hard_delete_zhaokui_test_data.py tests/test_tenant_hard_delete_operations.py`
  - 结果：`All checks passed!`
- `cd backend && .venv/bin/python -m pytest tests/test_tenant_hard_delete_operations.py tests/test_sending_plan_creation.py -q`
  - 结果：`16 passed in 1.57s`

## 本地 dry-run

命令：

```bash
cd backend
.venv/bin/python scripts/hard_delete_zhaokui_test_data.py --tenant-slug t-019dc238
```

结果摘要：

- tenant：`019dc238-c4c9-7de8-842f-8d46731481c1` / `t-019dc238` / `赵奎`
- `muzi_candidates_count`: `2`
- 候选：
  - tenant_company_id `1147`, clean_company_id `1115`, name `muzi`, country `USA`
  - tenant_company_id `1148`, clean_company_id `1131`, name `MUZI`, country `CAN`
- 预览计数：
  - tenant_companies `2`
  - tenant_contacts `1`
  - groups `1`
  - group_members `1`
  - sending_plans `1`
  - sequence_steps `1`
  - sending_plan_recipients `1`
  - sequence_enrollments `1`
  - emails `1`
  - email_events `1`
  - email_send_locks `1`
  - company_scores `0`
  - scoring_jobs `0`
- plan_ids：
  - `019e13fb-55a5-7514-a429-1a2ef7099bec`

结论：

- 本地 dry-run 已完成，只读预览输出正常。
- 本地 `clientget` 初始不满足默认执行门禁：`muzi` 精确匹配候选数量为 2，不是唯一候选。
- 用户随后确认这 2 个候选均为手工创建测试数据，因此通过显式候选 ID 受控步骤执行清理。

## 本地 execute

执行时间：2026-05-11 06:32:35 CST

命令：

```bash
cd backend
.venv/bin/python scripts/hard_delete_zhaokui_test_data.py \
  --tenant-slug t-019dc238 \
  --execute \
  --confirm t-019dc238 \
  --confirm-company-ids 1147,1148
```

执行结果摘要：

- deleted_tenant_company_ids：`1147`, `1148`
- deleted_plan_ids：`019e13fb-55a5-7514-a429-1a2ef7099bec`
- `verification.complete`: `true`
- `verification.remaining`：
  - tenant_companies `0`
  - groups `0`
  - group_members `0`
  - sending_plans `0`
  - sequence_steps `0`
  - sending_plan_recipients `0`
  - sequence_enrollments `0`
  - emails `0`
  - email_events `0`
  - email_send_locks `0`

删除后 dry-run：

- `muzi_candidates_count`: `0`
- `plan_ids`: `[]`
- tenant_companies、tenant_contacts、groups、group_members、sending_plans、sequence_steps、sending_plan_recipients、sequence_enrollments、emails、email_events、email_send_locks 均为 `0`

流程核验：

- 被删除发送计划 `019e13fb-55a5-7514-a429-1a2ef7099bec` 详情读取返回 `AppError`，符合现有不可访问/不存在行为。
- 后端测试子集覆盖清理后新建发送计划流程，结果见本文件“本地实现验证”。

## FK 审计摘要

只读查询 `information_schema.referential_constraints` 后确认关键依赖：

- `email_events` 依赖 `emails`
- `email_send_locks` 依赖 `sequence_enrollments`
- `emails` 依赖 `sending_plans`、`sequence_steps`、`sequence_enrollments`、`tenant_contacts`
- `sequence_enrollments` 依赖 `sending_plans`、`sending_plan_recipients`、`tenant_contacts`
- `sending_plan_recipients` 依赖 `sending_plans`、`tenant_companies`、`tenant_contacts`
- `sequence_steps` 依赖 `sending_plans`
- `group_members` 依赖 `groups`、`tenant_companies`、`tenant_contacts`
- `company_scores`、`scoring_jobs` 依赖 `tenant_companies`
- `tenant_companies`、`tenant_contacts` 依赖 `tenants`，并默认保留 clean/provider 来源数据

实现删除顺序与上述依赖一致：事件/锁/邮件/运行态先删，发送计划主表后删；群组成员先删，群组后删；评分/联系人/company 最后删。

## 生产手工执行步骤

生产执行必须由用户再次明确触发，且先确认数据库快照/备份存在。

建议顺序：

1. 确认生产 `clientget` 数据库已有可恢复快照或 `pg_dump` 备份，且备份文件大小非零。
2. 在生产连接配置下先运行 dry-run：

   ```bash
   cd backend
   .venv/bin/python scripts/hard_delete_zhaokui_test_data.py --tenant-slug t-019dc238
   ```

3. 人工核对 dry-run 输出：
   - tenant 必须是 `t-019dc238` / `赵奎`
   - `muzi_candidates_count` 必须为 `1`
   - 待删除 group、sending plan、email/event 计数符合用户确认范围
4. 只有 dry-run 符合预期时，才执行：

   ```bash
   cd backend
   .venv/bin/python scripts/hard_delete_zhaokui_test_data.py \
     --tenant-slug t-019dc238 \
     --execute \
     --confirm t-019dc238
   ```

5. 保存 execute 输出中的 `verification.remaining`；所有目标剩余计数必须为 `0`。
6. 再用租户端流程验证：公司列表/详情、群组列表、发送计划列表/详情、dashboard 计数、发送计划新建流程。

## 生产执行记录

执行时间：2026-05-11 06:38:39 CST

连接确认：

- host：`dbconn.sealosbja.site:45010`
- database：`clientget`
- user：`postgres`
- 已移除 `directConnection=true`

备份：

- 文件：`_control/evidence/database/clientget-prod-pre-hard-delete-muzi-20260511063715.dump`
- 大小：`90M`
- 格式：`pg_dump -Fc`

生产 dry-run 摘要：

- tenant：`019dc238-c4c9-7de8-842f-8d46731481c1` / `t-019dc238` / `赵奎`
- `muzi_candidates_count`: `1`
- 候选：
  - tenant_company_id `9382`, clean_company_id `9385`, name `muzi`, country `UNK`
- 预览计数：
  - tenant_companies `1`
  - tenant_contacts `1`
  - groups `2`
  - group_members `101`
  - sending_plans `1`
  - sequence_steps `1`
  - sending_plan_recipients `1`
  - sequence_enrollments `0`
  - emails `0`
  - email_events `0`
  - email_send_locks `0`
  - company_scores `0`
  - scoring_jobs `0`
- plan_ids：
  - `019e13a8-e640-732c-90d3-561c74da5cda`

生产 execute 命令：

```bash
DATABASE_URL='postgresql+asyncpg://postgres:***@dbconn.sealosbja.site:45010/clientget' \
  .venv/bin/python scripts/hard_delete_zhaokui_test_data.py \
  --tenant-slug t-019dc238 \
  --execute \
  --confirm t-019dc238
```

生产 execute 结果：

- deleted_tenant_company_ids：`9382`
- deleted_plan_ids：`019e13a8-e640-732c-90d3-561c74da5cda`
- `verification.complete`: `true`
- `verification.remaining`：
  - tenant_companies `0`
  - groups `0`
  - group_members `0`
  - sending_plans `0`
  - sequence_steps `0`
  - sending_plan_recipients `0`
  - sequence_enrollments `0`
  - emails `0`
  - email_events `0`
  - email_send_locks `0`

生产删除后复核：

- 删除后 dry-run：`muzi_candidates_count = 0`，`plan_ids = []`
- 目标表计数复核：tenant_companies `0`，groups `0`，sending_plans `0`
