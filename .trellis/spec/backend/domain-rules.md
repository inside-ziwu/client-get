# 关键行为口径与多实例约束

> 这些是散落在代码里的重要业务决策，改动相关逻辑前先对照；要改口径必须经用户拍板并同步本文。产品定位与「明确不做」清单见 [AGENTS.md](../../../AGENTS.md) §0。

## 付费根基

客户付费的根基是两条能力，任何改动不得削弱：**租户数据隔离**（实施细则见 [database-guidelines.md](./database-guidelines.md)）与**邮件发送可靠**——不重复发送、遵守收件人时区与工作日窗口、保护发信域名信誉（实施细则见 [workers.md](./workers.md)）。

## 行为口径

| 口径 | 规则 |
|---|---|
| 发送间隔 | 固定 **3 秒**（worker fallback 与新建计划默认 `[3,3]`） |
| 收件人选取 | 按联系人等级排序选取，**单公司上限 8 人**；排除 unsubscribed / bounced / invalid |
| 发送窗口 | 按**收件人国家**的工作日历（工作日 + 节假日 + 时区）决定；不在窗口内则顺延 |
| 配额熔断 | 同域名连续 3 次配额错误 → 熔断至北京时间次日凌晨；10 分钟窗口内 3 次 429 → 限流熔断 |
| 发送幂等键 | `enrollment_id:step_id` |
| 状态对账 | webhook 为主，对账 worker 约每 10 分钟主动查询兜底 |
| 仪表盘统计 | 邮件统计**排除 failed**；「已评分公司」只计入租户当前活跃模板的最新版本分数 |
| 租户评分 | 确定性规则引擎（非 AI），结果归租户所有；平台模板只是创建租户时的默认种子。「AI 评级 / 邮件生成 / 情报摘要」当前为启发式桩（#46） |
| 采集类型 | `manual` 看 `source_id LIKE 'manual-%'`；`keyword` 看精确标签「外贸通关键词采集」；`reverse` 看精确「腾道」标签或非空 `source_competitor`；其余为 `unknown`。优先级 manual > keyword > reverse |
| PCB 供应商评分 | 只有显式 `reverse` 才视为「有中国 PCB 供应商」；keyword / manual / unknown 均为否 |
| 域名验证 | **当前为假验证**：点击即置 verified，不做任何 DNS 校验（#47，勿向客户承诺） |
| 预热升档 | 仅手动调整，无自动升档（#48） |
| 计划完成 | 全部 enrollment 终态后自动置 completed（`services/sending_plan_completion.py`） |
| 客户池修复 | 300 秒 / 轮，共享全池但排除手工私有行（`source_id LIKE 'manual-%'`）；按实例 + PCB 行业隔离，幂等可重复执行 |
| 时间基准 | 生产数据库会话时区 UTC；熔断恢复等业务锚点用北京时间 |

列表页与筛选的 UI 交互口径见 [../frontend/component-guidelines.md](../frontend/component-guidelines.md)。

## 多实例（Instance A / B）

同一套代码 + 共享底层数据库，按 `CLIENTGET_INSTANCE_ID` 区分实例（Instance A 的合法取值就是 `default`；生产必须显式设置，见 `core/config.py`）。

> **硬性声明：A、B 共用同一个物理 PostgreSQL `clientget` 数据库，不是两套独立数据库。** `instance_id` 只提供逻辑数据边界；repair、评分、发送和所有批量操作仍竞争同一套连接、CPU、I/O 与锁。即使只操作 B，也必须同时审计 A 的在途发送负载，不能把 B 当成无影响的测试库。

- 每实例独立 JWT secret，token 带 `iid` claim；管理员、租户、认证、worker 任务按实例隔离。
- `waimaotong_clean_companies` / `waimaotong_clean_contacts` 公池跨实例共享；`tenant_companies` 关系按实例的租户隔离，手工录入行不跨租户分发。
- 新实例初始化：`backend/scripts/init_instance.py`（创建实例管理员）。
- 前端按构建时注入的 API 地址区分实例，前端代码无实例概念。
- 各实例当前的运营状态与负责人尚未确认（#66），它也卡着 #61 的 schema 基准决策。

## 认证

JWT HS256，三种 kind（platform / tenant / service）；租户 token 校验 slug 与 URL 一致、角色与 DB 实时比对；多实例用 `iid` claim。refresh token 走 httpOnly cookie，`COOKIE_DOMAIN` 按实例配置——Sealos 域名下必须写后端完整主机名（见 [../frontend/quality-guidelines.md](../frontend/quality-guidelines.md)「部署与联调的坑」）。
