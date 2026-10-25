# 公司列表采集类型新增 Instantly

## 背景

客户库新增海外买家来源 Instantly，`waimaotong_clean_companies.data_source_tags` 中以 `"Instantly"` 标记，平台无法单独筛出。Instantly 是与关键词采集并列的独立来源（2026-10-25 用户拍板）。

## 需求

1. 租户端公司列表、后台客户库的「采集类型」下拉新增「Instantly」，位于「关键词采集」之后。
2. 选「Instantly」：筛出 `data_source_tags @> '["Instantly"]'::jsonb` 的公司（不受手工录入等优先级影响）。
3. 多标签公司在各自选项下都出现：关键词采集 / 精准反推 / 手工录入原规则不变。
4. 「来源待确认」排除带 Instantly 标签的公司。
5. 列表「采集类型」列与详情抽屉显示全部类型，如「关键词采集、Instantly」「手工录入、Instantly」；只有 Instantly 时显示「Instantly」。
6. 单值 `collection_type` 语义不变（评分引擎「有中国 PCB 供应商」依赖它）。

## 不做

- 联系人表 `source='instantly'` 区分来源。

## 验收

- 截至 10-22 全库：含 Instantly 606 家（仅 Instantly 428、关键词+Instantly 177、腾道+Instantly 1）；按租户以 `tenant_companies` 上架情况核对。
- 后端单测覆盖：仅 Instantly、关键词+Instantly、腾道+Instantly、手工+Instantly、来源待确认排除 Instantly。
- 前端多标签显示测试；type-check 通过。
