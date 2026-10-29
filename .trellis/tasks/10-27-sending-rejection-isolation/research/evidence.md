# 只读取证结论（2026-10-27）

## 结论
此次不能用“跳过坏邮箱”修复。前三封已经取得 EngageLab 成功返回的 message id，失败发生在本地发送成功回写；随后第四封进入 quota_deferred，使域名暂停到北京时间次日零点。前三封不是三次限流。第四封的上游具体业务错误码未保留，无法仅凭 quota_deferred 区分真实余额/日额度不足与字符串误分类。

## 原始证据的安全摘要
没有将联系人邮箱、message id 原值、SQL 参数或原始日志放入本文件。浏览器导出仅临时解析长度及 SQL 位置，临时文件已删除。

Sealos 北京区“外贸SaaS” → clientget-sending-worker；pod 为 clientget-sending-worker-54c496495b-dbnkl，镜像 tag 2026.10.25-r1，页面显示重启 0 次。日志条目时间、email id 与生产库同批记录对应，确认是 B。未把镜像 tag 当作精确 Git SHA 的证明。

日志时间选择器此次显示 America/Los_Angeles，并非旧 spec 所称固定 UTC。北京时间 10 月 27 日 09:00 对应 UTC 10 月 27 日 01:00、洛杉矶 10 月 26 日 18:00。两天均查精确两分钟窗口，不以关键词搜索 _msg 占位符。

| UTC 日期时间 | 日志结果 | 证据 |
|---|---|---|
| 10-26 01:00:05.926 | retry_scheduled / failed | UPDATE emails 的 engagelab_message_id 参数长 107，varchar(100) 报错 |
| 10-26 01:00:10.424 | retry_scheduled / failed | 同一 SQL，ID 长 101 |
| 10-26 01:00:14.749 | retry_scheduled / failed | 同一 SQL，ID 长 101 |
| 10-26 01:00:19.078 | deferred_for_quota | resume_at=2026-10-26T16:00:00Z |
| 10-27 01:00:02.458 | retry_scheduled / failed | 同一 SQL，ID 长 107 |
| 10-27 01:00:06.745 | retry_scheduled / failed | 同一 SQL，ID 长 101 |
| 10-27 01:00:10.714 | retry_scheduled / failed | 同一 SQL，ID 长 101 |
| 10-27 01:00:14 附近 | deferred_for_quota | resume_at=2026-10-27T16:00:00Z |

错误类型：asyncpg.exceptions.StringDataRightTruncationError；错误内容：value too long for type character varying(100)。SQL 是 mark_email_sent 内 UPDATE emails SET engagelab_message_id=...，不是调用服务商抛出的拒发异常。

生产查询先设置 conn.read_only=True 并 SHOW transaction_read_only=on；全程只读，时间窗裁剪与实例过滤。
- emails.engagelab_message_id 实际类型 character varying，最大长度 100。
- B 在北京 10-26、10-27 各三条 failed，sent_at 和 provider id 均空；这是回写事务回滚结果，不能据此判定服务商未接单。
- B 对应两天 domain_daily_usage.reserved_count=0、daily_limit=2800，本地额度未耗尽；不能由此推断服务商余额充足。
- 27 日第四条锁 locked_at=01:00:13.720Z、released_at=01:00:14.674Z，status=released、email_id=NULL、attempt_count=0；吻合配额延期删邮件路径。
- 最新查询已看到北京 10-28 零点后 8 条 delivered；它不否定此前全天暂停，也不证明下一个窗口已恢复正常。
- A 在北京 10-26 有 5000 条带 sent_at 的邮件，说明两个实例应分别排查；不能据 A 正常证明 B 的服务商账号正常。

## 代码因果链
1. backend/app/workers/sending.py:145 起先 await provider.send_email，取得非空 id 后调用 mark_email_sent。
2. backend/app/services/tenant_messaging_service.py:2058 起：锁置 sent 与邮件/序列/计数推进在同一事务，ID 超长使整个事务回滚。
3. backend/app/workers/sending.py:276 起：通用 Exception 分支将本地回写错误当成发送临时失败，调用 mark_email_failed；释放额度、允许锁重抢、安排重发。服务商已接单，因此存在重复发送风险，不能以现有幂等键声明“绝无重复”。
4. 第四封单独进入配额分支（sending.py:175）；首次明确配额就可熔断。前三次 SQL 异常不会增加 domain_rate_limit_hits。
5. _defer_for_quota 删除本次邮件并释放锁，导致仪表盘仅剩三条 failed；域名内存暂停使后续不再领取。
6. email_reconciliation_service.py:33 只选 status=sent 且非空 provider id，无法自动修复这些 failed+无 id 的历史记录。
7. run_sending_worker.py 未调用 configure_logging；_log 使用 logger.info。默认 Python logging 级别使事件日志可能不输出；本次导出有 print 的轮次结果，但没有原始配额错误，不能承诺从现有库中恢复它。

## 既有先例与外部契约
- backend/alembic/versions/20260701_0002_email_events_provider_event_id_text.py 已为 webhook 事件 ID 做过 TEXT 扩容，并明确记载真实 message id 可因邮箱长度超过 100。本次 emails 字段漏改。
- EngageLab 官方发送接口文档：https://www.engagelab.com/docs/email/rest-api/deliverlies 。返回 email_ids；业务错误体含 code/message；文档的请求去重字段为 request_id，1 小时有效。当前 _build_request_body 发送 idempotency_key，不应假定等价或跨日去重有效。此项需要模拟测试与契约确认，不能借此断言本次实际重复投递次数。

## 验证
既有 backend/tests/test_sending_worker.py：32 passed，1 个既有 bleach NoCssSanitizerWarning。该 mock 测试集未覆盖真实字段长度和接单后事务失败，不能当作本次缺陷不存在的证明。
