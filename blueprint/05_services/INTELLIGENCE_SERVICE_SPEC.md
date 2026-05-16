# Intelligence Service Spec

## 1. Source management

Admin manages platform sources with `tenant_id = NULL`. Tenant custom sources are reserved for later.

## 2. Fetch pipeline

```text
select active sources due
fetch RSS/website/manual source
extract article
upsert intelligence_articles
match tenants by industry_tags/subscriptions
summarize with AI if billable tenants exist
publish to intelligence_article_publications
notify users if enabled
```

## 3. Billing

For each article summary:

1. Determine candidate tenants.
2. Pre-authorize per-tenant estimated share.
3. Call LLM once.
4. Settle each successful authorization.
5. Publish summary only for settled tenants; publish title/link only for insufficient balance tenants.

## 4. Tenant reads

Tenant reads from `intelligence_article_publications` joined to articles by `(article_id, article_created_at)`. Never grant app_user direct `SELECT` on `intelligence_articles` without tenant publication join.
