# score-pcb-supplier-by-collection-type

## Why

评分模板「PCB 供应商」维度的 `has_china_pcb_supplier` 条件(20 分,识别最优质客户)此前因数据缺口恒判 False:所有公司落 default 10 分,「已从中国采购 PCB」的高价值客户识别失效,且每评一家公司刷一条 WARNING(补评批次日志刷屏)。

业务口径(2026-07-03 用户确认):**采集类型 = 精准反推 ⇔ 有中国 PCB 供应商;采集类型 ≠ 精准反推 ⇔ 没有**。采集类型判定已有单一真源 `collection_source.compute_collection_type`(data_source_tags 含「外贸通关键词采集」→ keyword,否则 → reverse/精准反推),且三条评分路径的查询均已获取 `data_source_tags`,零查询改动即可接入。

## What Changes

- `has_china_pcb_supplier` 条件实现为:`compute_collection_type(data_source_tags) == "reverse"`
- 沿用管理端筛选的既有口径:`data_source_tags` 为 NULL 视为 reverse(精准反推)
- 移除该条件的恒告警(日志刷屏随之消失);未知条件类型的告警保留
- 存量 system_score/system_grade 不自动重算(见 tasks 2.2 决策项)

## Non-Goals

- 不改评分模板配置(维度与分值不变)
- 不改采集类型口径本身

## Impact

| 范围 | 影响 |
|------|------|
| 评分引擎 | 条件评估一处 + 单元测试 |
| 评分结果 | 精准反推公司该维度 10 → 20 分;新评分即时生效,存量待决策是否重算 |
| 日志 | 补评批次不再刷 WARNING |
