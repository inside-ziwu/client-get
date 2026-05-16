# FastAPI Route Ordering Rules（自审后补充）

FastAPI/Starlette 按注册顺序匹配路由。凡是同一 HTTP 方法下存在静态段和动态段冲突时，必须先注册静态路由，再注册 `/{id}` 动态路由。

## 1. 必须注意的冲突

| Resource | 静态路由必须先注册 | 动态路由 |
|---|---|---|
| companies | `GET /companies/filters`, `GET /companies/export` | `GET /companies/{id}` |
| emails | `GET /emails/stats`, `/emails/stats/by-*`, `/emails/stats/trend` | `GET /emails/{id}` |
| email templates | `POST /email-templates/ai-generate` | `GET/PUT/DELETE /email-templates/{id}` |
| intelligence | `GET/PUT /intelligence/subscriptions` | `GET /intelligence/articles/{id}` 不直接冲突，但保持静态优先。 |
| admin tenants | `POST /tenants/{id}/suspend`, `/activate` | `GET/PATCH /tenants/{id}` 不冲突方法不同，但同 router 中仍建议动作路由先声明。 |

## 2. 推荐 router 声明顺序示例

```python
router.get('/companies/filters')(list_company_filters)
router.get('/companies/export')(export_companies)
router.get('/companies')(list_companies)
router.post('/companies')(create_company)
router.post('/companies/batch-import')(batch_import_companies)
router.get('/companies/{company_id}')(get_company)
```

## 3. 验收测试

1. `GET /companies/filters` 不应被当作 `{id}='filters'`。
2. `GET /emails/stats` 不应被当作 `{id}='stats'`。
3. `POST /email-templates/ai-generate` 不应进入 `{id}` 分支。
