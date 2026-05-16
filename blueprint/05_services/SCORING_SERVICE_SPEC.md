# Scoring Service Spec

## 1. Trigger

- T+1 scheduled scoring for complete companies.
- Manual trigger after data import.
- Recharge trigger for `llm_pending=true` companies.

## 2. Eligibility

A company can be scored when:

```text
tenant_companies.data_status = 'complete'
AND business_status in ('pending_score','scoring')
AND deleted_at is null
```

Precise customer from lixiaoyun path may receive S grade immediately but still creates score record.

## 3. Scoring pipeline

```text
load tenant active scoring template version
for each dimension:
  if type=rule: evaluate rules
  if type=llm: call AIService if capability available, else mark pending
calculate weighted total
map grade thresholds
insert company_scores
update tenant_companies grade/total_score/business_status
```

## 4. Rule dimension format

```json
{
  "id": "export_frequency",
  "name": "进出口频次",
  "type": "rule",
  "weight": 20,
  "rules": [
    { "condition": "trade_count_gte", "value": 10, "score": 100 },
    { "condition": "default", "score": 20 }
  ]
}
```

## 5. LLM dimension format

```json
{
  "id": "product_match",
  "name": "产品/行业匹配度",
  "type": "llm",
  "weight": 20,
  "prompt_template": "...",
  "expected_json_schema": { "score": "number", "reasoning": "string" }
}
```

## 6. Pending behavior

If AI balance insufficient:

- rule dimensions still calculate.
- score record may be partial with `llm_pending=true`.
- `tenant_companies.business_status` remains `pending_score` or `scored` depending product decision. Recommended: keep `pending_score` when LLM dimension is required by active template.
- notification to tenant admin: balance_low.
