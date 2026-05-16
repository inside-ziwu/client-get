# Owner Open Questions

这些问题不阻塞 P0 开发；本包已经给出默认实现。Owner 确认后可调整。

## Q1. EngageLab 是否支持 inbound/reply 解析？

默认：先实现 delivery/open/click/bounce/unsubscribe webhook；reply 字段预留。若 EngageLab 支持 inbound，则接入 reply body。

## Q2. 预热档位是否最终固定为 50/100/200/500/1000/4000？

默认：采用 07 修复后的动态指标驱动 6 档，默认上限如上。

## Q3. Phase 1 是否完全不做租户自助充值？

默认：不做。Admin 手动充值；Tenant 只读余额/流水。

## Q4. 腾道、励销云 API 文档是否已有？

默认：先实现 adapter interface 和 placeholder；外贸通先落地。

## Q5. 情报源抓取是否允许无 AI 摘要直接发布？

默认：允许。AI 失败或余额不足时发布标题和原文链接。

## Q6. 平台官方模板是“只读共享”还是“创建租户时复制”？

默认：平台模板可直接只读展示；租户也可 clone 为自有模板。创建租户时可复制常用模板到 `email_templates(source_type='platform_copy')`，但实现上需要避免平台后续修改影响租户副本。
