# Grok 4.7 实施交接

## 先读与执行边界
阅读顺序：research/evidence.md → prd.md → design.md → 本文件。用户已批准在本 worktree 做本地实现和验证。生产迁移、修数、真实发信和部署仍需另一次明确授权。

**不能实施的错误方案：**把前三个联系人 invalid、跳过所有失败邮件、删除域名熔断、仅在 catch 中 continue、截断 message id、直接重发历史 failed。

## 1. 建立失败测试（先复现后修复）
使用合成数据：107/101 字符 ID，可包含 example.com，禁止复制生产 ID。
- 真实 PostgreSQL 分区父表和当前分区 varchar(100) 写入 107 字符应复现 22001；迁移后完整写入，不能截断。
- mock provider 成功返回 107 字符、mark_email_sent 抛 DB 异常：复现现有错误调用 mark_email_failed；修改后断言无外部二次发送、无失败重试、无额度回退。
- provider 三次成功+本地写库异常，与第四次明确 quota 拒绝分开；前三次不能累计限流，第四次单独触发暂停。

## 2. 数据库迁移与契约
涉及 backend/alembic/versions/<新revision>.py，参照 20260701_0002_email_events_provider_event_id_text.py。
1. 查看当前 head、自省 emails 分区与 email_send_locks CHECK/索引/FK；不要修改旧 revision。
2. 一个新 revision：emails.engagelab_message_id TEXT；锁新增 design.md 定义的四列及三个状态；兼容现有数据，时间列可空。
3. 检查 DTO/schema/SQL/webhook/reconciliation 是否有长度 100 假定；完整值等值匹配，不截断。
4. migration downgrade 有长 ID 或新状态待恢复时明确拒绝，不删除事实；开发库验证失败会完整回滚。
5. 更新 docs/database-schema.md 和 backend spec 的相关契约；不把本轮取证摘要中的原始客户数据写入文档。

## 3. 服务层事务和恢复
负责文件 backend/app/services/tenant_messaging_service.py；可把新增恢复逻辑拆成专用 service，避免改无关业务。
- 新增 begin_dispatch：CAS locked→dispatching，记录时间，确认 rowcount=1 才能外发。
- 新增 record_provider_acceptance：短事务保存完整回执、时间并 dispatching→accepted_pending，可幂等重入；不同回执覆盖同一尝试必须拒绝并告警。
- mark_email_sent 接受 accepted_pending 的锁；现有内部回调路径仍需兼容 locked（若调用方不是新版 worker，必须核对其接单证据，禁止绕过幂等）。回执→邮件/联系人/序列/计划计数在一次事务内只推进一次。
- 新增 finalize_pending：分页选择本实例 accepted_pending，按尝试加锁恢复；不调用 send_email；保留 webhook 已到达的 delivered/opened 状态。
- provider 明确失败路径支持 dispatching CAS；额度以 claim 时 quota_usage_date 释放，重复处理不二次扣减。
- stale 回收：locked 仅在确认没有外发时回收；旧版遗留 locked 保守隔离；dispatching 超时转 uncertain；accepted_pending 不可释放为可重抢状态。
- 领取失败时继续下一个可发送收件人；held 状态不能把整个计划反复卡在首行，验证当前候选扫描范围足够继续选取后续行。
- 新/改 service SQL 显式 tenant_id + tenants.instance_id；触及的平台表同时 instance_id。补上对应路径现有省略过滤的位置，保留跨实例反向断言。

## 4. Worker 错误边界
负责 backend/app/workers/sending.py、backend/scripts/run_sending_worker.py。
- 把 provider 调用 try/except 与接单回写 try/except 拆开；禁止一个通用 catch 同时覆盖“未接单”与“已接单”。
- 先提交 begin_dispatch，再调用 provider；有 id 后先持久化 receipt，再 finalize。
- 已接单回写异常只触发本地恢复，不调用 mark_email_failed、defer_email_for_quota 或 send_email。
- 结果不确定进入 uncertain；明确 provider 拒绝才走分类；恢复循环每轮先有限处理 pending（建议最多 20），失败只重试本地事务并退避，不能饿死正常发送。
- record receipt 的有限重试 1/5/30 秒；失败记录安全事件，留下 dispatching/uncertain 持久闸门；重启不能丢防重能力。
- 初始化 configure_logging；轮次输出和 logger 都走安全字段白名单。不要输出 str(SQLAlchemyError) 或完整回执。

## 5. Provider 分类
负责 backend/app/integrations/engagelab.py、worker 分类函数及新测试。
- 解析结构化 code/message/http_status/Retry-After，兼容非 JSON、空 body、2xx 无 id。
- 为本次确证的数据库错误新增独立 internal_finalize 分类，不当成 provider reject。
- 收件人永久/临时错误按 design.md 行为矩阵处理；映射中每个业务码必须有来源和合成 fixture，未确认码不假设永久。
- 保留真实 quota/429 保护。此次不改“限流暂停到午夜”口径；后续若优化为短冷却，单独评审。
- 核实官方 request_id 契约并添加请求体测试；不要声称当前 idempotency_key 提供服务商去重。若采用 request_id，明确仅是有限时间防线，持久锁负责跨日防重。不得用真实发送测试该契约。

## 6. 测试矩阵与命令
重点新增/扩展 backend/tests/test_sending_worker.py、provider HTTP mock 测试、迁移真库测试、发送恢复/隔离测试。合成场景至少包括：

| 场景 | 必须断言 |
|---|---|
| ID 长 100/101/107/512 | 完整入库且 webhook/对账匹配，不截断 |
| provider 成功、finalize 失败 | send 一次；pending 可恢复；额度不释放；attempt 不增加 |
| provider 成功、receipt DB 暂不可用、进程退出 | 重启后 dispatching/uncertain 不重发；未落回执需只读核实 |
| 已提交 receipt 后崩溃 | 重启只 finalize，计划/序列/额度不重复推进 |
| 超时/断连/2xx 无 id | 不自动重发，不标 invalid |
| 三个永久拒绝+第四个成功 | 第四个能发；无域名熔断；错误收件人不再领取 |
| 三个本地回写错误+第四个 quota | 只有第四个触发配额行为，前三个仍待本地恢复 |
| 重复成功/失败回调与 webhook 抢跑 | 不重复计数/释放额度；不倒退 delivered/opened |
| 跨租户与 A/B 实例 | 无状态、锁、恢复扫描串扰 |
| 跨北京午夜、收件人非工作日 | 释放原占用日；发送窗口仍遵守原规则 |
| 真实 429/额度拒绝 | 原保护仍生效；恢复点和熔断原因可检索 |
| 日志异常含邮箱、凭证、SQL 参数 | 输出中均不出现；只留安全错误码与长度 |

命令：
```bash
cd backend
uv run pytest -q tests/test_sending_worker.py
uv run pytest -q
uv run ruff check app/integrations/engagelab.py app/workers/sending.py app/services/tenant_messaging_service.py scripts/run_sending_worker.py
```
新增文件加入 ruff 目标。上述 mock 门禁不能替代 Neon 开发库的分区/状态机/隔离验证；按 quality-guidelines.md 事务断言、ROLLBACK、复核零残留。禁止运行连接生产配置的 run_sending_worker.py --once。

## 7. 历史与发布检查（另行执行）
1. 默认 dry-run 抽取事故时间窗的长 ID 回写失败尝试，安全关联 provider 接单信息；检查 A 对照组，不只 B。
2. 输出按 enrollment+step 汇总的接单/重试/待核实计数；实际重复投递必须查 provider 状态，不能用三次重试推算。
3. 单独设计修复事务，不能调用旧锁闸门后假装修复成功；核实序列只推进一次、计划计数口径、真实接单日额度。
4. 提交给用户具体 SQL、影响数和共享库锁影响；收到该次批准后才执行。
5. 正式发布先避免旧新 worker 混跑，迁移后核对所有分区字段类型，再更新 worker。只读观察自然业务发送；未经授权不主动发送探针。
6. 验收应看到长 ID 完整落库、sent_at 可追踪、pending 可恢复、无 22001/异常重发。若仍 quota_deferred，检查新增 provider_code 决定账号余额/额度或分类问题，不能宣称扩列消除了配额限制。
7. 回滚保留 TEXT，恢复/隔离新锁状态后再回滚 worker；不能先降级类型导致再次失败。

## 本轮交付与未执行项
已完成：取证、本 worktree 内的迁移文件、接单/回写分离、拒发分类、安全日志、测试和默认 dry-run 工具。主审指出的三处也已补上：运行中节流回收确认未外发的新锁、`finalize_not_before` 租约/退避，以及用持久化接单时间做发送事实。未执行且仍未授权：生产迁移、生产修数、真实发信、部署。第四封上游具体配额错误码在现有输出中缺失，不伪造结论。共享开发库已做事务内预演并回滚，没有执行 `alembic upgrade` 提交。预演中父表和当时 6 个分区都变为 text，107 字符等值匹配成功，截断到 100 字符不匹配；锁可写入 `dispatching` 和 107 字符回执。存在超长 ID 时降级会拒绝。回滚后列类型仍是 `varchar(100)`，新列、演练行和合成 ID 残留都是 0。开发库事故窗口 dry-run 为 0 行，不能代替生产事故行。

2026-10-28 又在同一开发库、同一事务内借入外键并插入 25 条恢复样本：未外发新锁按占用日退回额度一次，旧锁和 dispatching / uncertain / accepted_pending 保持原状态；前 20 条推迟后，第 21 条用接单时间完成回写，重复回写不再推进。回执重试没有改写第一次接单时间。事务回滚后独立只读复核：`engagelab_message_id` 仍是 `varchar(100)`，五个新列数量为 0，状态约束不含新状态，合成 ID 和演练邮件为 0，default 实例锁仍是预演前的 1 行。未在共享库提交迁移，因此没有做跨连接 `SKIP LOCKED`。

同日上线前验证未通过。可销毁本地 PostgreSQL 16.15 上的真实 Alembic 升级、降级保护和双连接租约检查已完成，记录在 `research/prelaunch-verification.md`。阻塞项是非末步 `mark_email_sent` 被 asyncpg 拒绝，产品代码未改。本次验证不是上线授权。

## 非末步参数类型修复（2026-10-28）
范围只限 `mark_email_sent` 非末步 enrollment 更新：给 `:send_at` 明确 `timestamptz`，消除 asyncpg 把同一参数同时推断成 interval 和 timestamptz 的错误。`provider_accepted_at` 仍是发送事实，下一步间隔仍从该时刻计算，租户过滤和 CAS 幂等不改。不改迁移、不改 worker 领取、不改末步分支。

修复前在库 `prelaunch_f36204c45b83` 复现失败：锁保持 `accepted_pending`，`sent_count` 为 0。修复后在库 `prelaunch_0a77777d2315` 通过：非末步推进到第 2 步，下一步到期为接单时间加 3 天；两连接并发和随后重复执行只推进一次；前 20 条退避后第 21 条按接单时间回写；末步仍一次完成。两库都已删除。全量 `514 passed, 9 skipped`。这条代码阻塞已清零。上线仍未授权。
