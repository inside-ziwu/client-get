## ADDED Requirements

### Requirement: 发送 worker MUST 区分日配额耗尽与瞬时限流并按模式识别

发送 worker MUST 依据可配置的识别规则对 EngageLab 发送接口返回的错误分类，且 MUST 区分两类信号：

- **额度耗尽（触发熔断）**：错误信息不区分大小写命中额度耗尽语义关键词（已用 2026-07-02 生产日志校准：`balance is not enough`、`recharge soon`、EngageLab 错误码 `30877`；另保留 `daily quota`、`quota exceeded`、`配额`、`余额不足`、`已达上限` 兜底），或状态码命中已知配额错误码常量；
- **瞬时限流（不触发熔断）**：HTTP 429 或错误信息命中限流信号（如 `rate limit`、`too many requests`）MUST 维持临时错误分类、走既有重试链（15 分钟 / 1 小时 / 4 小时）——瞬时限流通常秒/分钟级即恢复，单次限流不得升级为整天停发。

**升级规则**：同一域名 10 分钟窗口内「瞬时限流 + 日配额」判定累计达到 3 次，MUST 视为配额耗尽并触发当天熔断。

#### Scenario: 命中额度耗尽关键词识别为配额类（2026-07-02 实测签名）

- **GIVEN** EngageLab 返回 HTTP 400，错误信息为 `{"code": 30877, "message": "mail failed to send. 552 {'code':-7,'message':'your account balance is not enough,please recharge soon',...}"}`
- **WHEN** worker 对该错误分类
- **THEN** 该错误被归类为配额类错误（`error_category='quota'`），且 `is_permanent=false`，触发该域名当天熔断

#### Scenario: 单次 429 瞬时限流走重试链不熔断

- **GIVEN** EngageLab 返回 HTTP 429，且该域名 10 分钟内首次命中限流
- **WHEN** worker 对该错误分类并处理
- **THEN** 该错误按临时失败处理（走既有重试链），该域名不熔断、继续正常领取后续邮件

#### Scenario: 短窗内连续限流升级为熔断

- **GIVEN** 某域名在 10 分钟窗口内已累计 2 次限流/配额类判定
- **WHEN** 第 3 次限流或配额类错误发生
- **THEN** 该域名按配额耗尽处理，触发当天熔断

#### Scenario: 普通业务错误不误判为配额类

- **GIVEN** EngageLab 返回 HTTP 422（无效收件人），错误信息不含配额类关键词
- **WHEN** worker 对该错误分类
- **THEN** 该错误维持现有分类（永久失败、`error_category='invalid'`），不触发熔断

### Requirement: 识别到配额耗尽后该域名 MUST 当天熔断停发

发送 worker 识别到某域名的配额耗尽后，MUST 停止该域名当天（北京时间自然日，与 EngageLab 档位配额重置周期一致）的后续发送；被熔断期间 worker MUST NOT 从该域名的队列中领取邮件。次日配额重置后 MUST 自动恢复发送，无需人工介入；恢复由下一轮领取循环被动拾起（空闲轮询为秒级，实际恢复延迟在秒级），不要求主动定时器。

熔断状态为 worker 进程内存态：重启后丢失，重启后对已耗尽域名最多多发起一次被拒的 API 调用，该错误即重新触发熔断——此为有意设计，换取免除持久化状态。

#### Scenario: 熔断后停止领取邮件

- **GIVEN** 域名 A 触发配额耗尽熔断，队列中仍有该域名的待发邮件
- **WHEN** worker 进入下一轮领取循环
- **THEN** worker 跳过域名 A，不领取、不调用 EngageLab，并记录熔断日志（含域名、触发时间、恢复时间）

#### Scenario: 次日自动恢复

- **GIVEN** 域名 A 于 7 月 2 日 23:30（北京时间）触发熔断
- **WHEN** 北京时间进入 7 月 3 日后 worker 执行下一轮领取
- **THEN** 域名 A 恢复正常领取与发送（恢复延迟不超过一个空闲轮询间隔）

#### Scenario: 熔断只影响触发域名

- **GIVEN** 域名 A 已熔断，域名 B 未触发配额耗尽
- **WHEN** worker 执行领取循环
- **THEN** 域名 B 的邮件正常发送，不受域名 A 熔断影响

#### Scenario: worker 重启后熔断状态重建

- **GIVEN** 域名 A 处于熔断中，worker 进程重启导致内存熔断状态丢失
- **WHEN** worker 重启后领取域名 A 的第一封邮件并被 EngageLab 以配额错误拒绝
- **THEN** 该域名立即重新熔断至次日，该封邮件按配额类错误处理（不标记失败、不终止 enrollment）

### Requirement: 本地日配额窗口 MUST 按北京自然日计算

`domain_daily_usage` 的读写（领取配额门、预留、释放、今日已发送统计）MUST 以北京自然日（`Asia/Shanghai`）为窗口边界，与熔断恢复周期及 EngageLab 档位周期同频。（现状：生产会话时区为 UTC，`CURRENT_DATE` 窗口在北京时间 08:00 翻转，与北京零点恢复错位 8 小时，会导致恢复被本地余量顶住或单个北京日放行近 2 倍限额。）

#### Scenario: 熔断恢复时本地窗口同步翻转

- **GIVEN** 域名 A 熔断至 7 月 3 日北京零点，7 月 2 日（北京日）的本地配额已接近用满
- **WHEN** 北京时间进入 7 月 3 日、worker 恢复领取
- **THEN** 本地配额按 7 月 3 日（北京日）的新窗口计数，恢复不被前一日余量阻塞

#### Scenario: 单个北京日不跨窗口翻倍放行

- **GIVEN** 某域名 `daily_limit = 9000`
- **WHEN** 在同一个北京自然日内持续发送
- **THEN** 本地配额门放行的发送量不超过 9000（不因 UTC 日在北京 08:00 翻转而获得第二个窗口）

### Requirement: 配额类错误 MUST NOT 产生失败记录或终止序列

配额类错误发生时：当前未发出的邮件行（`sent_at` 与 `engagelab_message_id` 均为 NULL）MUST 删除而非标记 `failed`（取件机制每次领取新建邮件行，保留旧行只会产生永久滞留的孤儿记录并使 `targets` 重复计数）；发送锁 MUST 置 `released`；本地预留配额 MUST 释放；对应 `sequence_enrollments` MUST 保持 `active`、`next_step_due_at` 推迟到次日配额重置后，且 MUST NOT 消耗 `send_attempt_count`。次日恢复后由领取流程按原步骤重新生成邮件并发送。

#### Scenario: 配额类错误不留失败记录、次日重新生成

- **GIVEN** 一封邮件发送时 EngageLab 返回配额类错误
- **WHEN** worker 处理该错误
- **THEN** 该邮件行被删除（不计入 targets/sent），对应 enrollment 保持 `active`、`send_attempt_count` 不变、`next_step_due_at` 为次日北京零点；次日领取时按原步骤重新生成邮件发送

#### Scenario: 本地预留配额正确回退

- **GIVEN** 一封邮件发送前已在 `domain_daily_usage` 预留配额
- **WHEN** 该邮件因配额类错误被 defer
- **THEN** 预留配额被释放（`reserved_count` 减一），但由于域名已熔断，释放的余量不会引发新的领取

### Requirement: 同一 enrollment 的连续配额 defer MUST 有上限

同一 enrollment 因配额类错误被连续推迟达到 3 次后，后续配额类错误 MUST 降级为临时失败处理（消耗 `send_attempt_count`、走既有重试链，重试耗尽后按既有逻辑终止）。此上限防止「永久性错误恰含泛化配额关键词」的毒药邮件每天霸占队首、逐日熔断整个域名的死循环。计数为 worker 进程内存态，重启后重置（重启最多让毒药邮件多获得一轮 defer，循环仍会被打破）。

#### Scenario: 连续第 4 次配额类错误降级为临时失败

- **GIVEN** 某 enrollment 已连续 3 次因配额类错误被推迟
- **WHEN** 该 enrollment 的邮件再次命中配额类错误
- **THEN** 按临时失败处理：`send_attempt_count` 加一、安排既有重试链，不再触发配额 defer

### Requirement: 未知 4xx 错误 MUST 默认归类为临时失败

`_classify_provider_error` 对未被显式识别的 4xx 状态码（现有显式分类 401/403/422/429 及配额类/限流规则之外）MUST 默认返回 `is_permanent=false`，走既有临时失败重试链（15 分钟 / 1 小时 / 4 小时），重试耗尽后才终止 enrollment。5xx 维持现有临时失败分类，不在本条范围内、行为不变。

#### Scenario: 未知 4xx 走重试链

- **GIVEN** EngageLab 返回 HTTP 456（未知错误码），错误信息不含配额类关键词
- **WHEN** worker 对该错误分类并处理
- **THEN** 该错误按临时失败处理，enrollment 的 `send_attempt_count` 加一并安排重试，不立即置为 `failed`

#### Scenario: 显式永久错误维持原判

- **GIVEN** EngageLab 返回 HTTP 422（无效收件人）
- **WHEN** worker 对该错误分类并处理
- **THEN** 维持永久失败行为：邮件标记 `failed`，enrollment 置为 `failed`，联系人状态按现有逻辑更新
