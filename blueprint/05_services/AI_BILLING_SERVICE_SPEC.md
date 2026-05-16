# AI Billing Service Spec

## 1. Public service methods

```python
class AIService:
    async def generate_email_templates(tenant_id, user_id, request) -> list[GeneratedTemplate]: ...
    async def score_company_dimensions(tenant_id, tenant_company_id, dimensions) -> ScoreResult: ...
    async def summarize_article(article_id, tenant_ids) -> SummaryResult: ...
    async def analyze_email_performance(tenant_id, user_id, filters) -> AnalysisResult: ...

class BillingService:
    async def authorize_ai_budget(tenant_id, amount, idempotency_key, context) -> UUID: ...
    async def settle_ai_usage(authorization_txn_id, response_usage, actual_cost, context) -> UUID: ...
    async def release_ai_authorization(authorization_txn_id, reason) -> UUID: ...
```

## 2. Authorization pseudo-code

```python
async def authorize_ai_budget(conn, tenant_id, estimated_cost, idem_key):
    existing = await find_transaction_by_idempotency_key(conn, tenant_id, idem_key)
    if existing:
        return existing.id

    row = await conn.fetchrow('''
      UPDATE tenants
      SET balance = balance - $1, updated_at = now()
      WHERE id = $2 AND balance >= $1
      RETURNING balance AS balance_after
    ''', estimated_cost, tenant_id)
    if not row:
        raise InsufficientBalance

    return await insert_balance_transaction(... type='hold', amount=-estimated_cost ...)
```

## 3. Settlement rules

- actual == estimated: mark usage settled_exact, no new balance movement.
- actual > estimated: atomic deduct delta, insert consumption delta transaction.
- actual < estimated: add delta back, insert release/refund transaction.
- provider failed: add full estimated back, insert release transaction, update AI attempt log to `released_full` with `actual_cost=0`; no billable usage is counted.

## 4. Idempotency

- `idempotency_key` format: `{scene}:{tenant_id}:{entity_id}:{nonce}`.
- Settlement idempotent by `authorization_transaction_id`.
- A provider response must be stored or passed to retry settlement; never call provider twice for same authorization.


## 5. AI attempt log lifecycle

Each AI call creates an `ai_usage_logs` attempt row before the provider call:

1. `authorized`: hold was created, provider not called yet.
2. `provider_called`: request was sent; provider response must be persisted or held for settlement retry.
3. `settled_exact` / `settled_charge` / `settled_release`: provider returned billable usage and local settlement completed.
4. `released_full`: provider failed without billable output; full hold released; `actual_cost=0`.
5. `settlement_failed`: provider returned billable output but local settlement failed; retry settlement only, never call provider again.
