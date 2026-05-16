# Collection Service Spec

See also `01_final_repaired_docs/12_COLLECTION_SERVICE_REPAIRED.md`.

## 1. Main system responsibilities

- Aggregate active `collection_keywords` into `collection_tasks`.
- Expose Internal APIs for claim/heartbeat/submit.
- Own credentials encryption and masked/short-lived credential response.
- Upsert shared companies/contacts/competitors.
- Link results to tenants through `collection_task_keywords`.

## 2. External collection worker responsibilities

- Claim tasks with service JWT.
- Execute adapters.
- L1 dedupe.
- Periodic heartbeat.
- Submit normalized results.
- Stop immediately when lease expired.

## 3. Task creation algorithm

```python
async def schedule_collection_tasks():
    keywords = await list_active_keywords_due()
    groups = group_by(keyword_normalized, countries_hash, source_types_hash)
    for group in groups:
        task = upsert_pending_task(group)
        sync_collection_task_keywords(task.id, group.keyword_ids)
```

## 4. Submit result transaction

```text
BEGIN
  validate task.status='running'
  validate lease_id and lease_expires_at > now()
  for each company:
    upsert shared_company + company_source
  for each contact:
    upsert shared_contact
  for each competitor:
    upsert competitor for each tenant
  resolve tenant_ids from collection_task_keywords
  for each tenant/company:
    if not blacklisted and not competitor:
      upsert tenant_company
  mark task completed
COMMIT
```

## 5. Normalized payload

```json
{
  "lease_id": "...",
  "companies": [
    {
      "source_type": "waimao_tong",
      "source_id": "abc123",
      "name": "ABC GmbH",
      "name_en": "ABC GmbH",
      "country": "DE",
      "website": "https://abc.de",
      "industry": "PCB",
      "raw_data": { "is_precise_customer": false }
    }
  ],
  "contacts": [
    {
      "source_type": "waimao_tong",
      "source_contact_id": "c1",
      "company_source_type": "waimao_tong",
      "company_source_id": "abc123",
      "name": "John Doe",
      "email": "john@abc.de",
      "title": "Purchasing Manager",
      "raw_data": {}
    }
  ],
  "competitors": []
}
```
