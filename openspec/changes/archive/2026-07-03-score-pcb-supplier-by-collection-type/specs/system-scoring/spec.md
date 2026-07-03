# system-scoring

## ADDED Requirements

### Requirement: 「有中国 PCB 供应商」条件 SHALL 按采集类型判定

评分条件 `has_china_pcb_supplier` SHALL 判定为:公司采集类型为「精准反推」(reverse)时为真,否则为假。采集类型 MUST 复用 `collection_source.compute_collection_type` 单一真源(`data_source_tags` 含「外贸通关键词采集」→ keyword,否则(含 NULL)→ reverse),与管理端「客户数据」筛选口径一致。该条件 MUST NOT 因数据形态(jsonb 数组或其字符串形态)差异而失效。

#### Scenario: 精准反推公司命中 20 分档

- **GIVEN** 公司 `data_source_tags` 不含「外贸通关键词采集」(或为 NULL)
- **WHEN** 以含「PCB 供应商」维度的模板评分
- **THEN** 命中「A — 有中国 PCB 供应商」条件得 20 分

#### Scenario: 关键词采集公司落默认档

- **GIVEN** 公司 `data_source_tags` 含「外贸通关键词采集」
- **WHEN** 评分
- **THEN** 不命中 A 条件,落「B — 无中国 PCB 供应商」default 10 分

#### Scenario: 不再产生恒告警

- **GIVEN** 补评批次处理任意数量公司
- **WHEN** 评分执行
- **THEN** 日志不再出现「has_china_pcb_supplier 条件无法在当前数据模型下匹配」
