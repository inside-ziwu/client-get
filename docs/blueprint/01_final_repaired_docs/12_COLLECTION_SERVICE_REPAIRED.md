# 12 采集服务独立部署架构（修复版）

## 1. 目标

采集服务独立部署，负责从外贸通、腾道、励销云获取公司/联系人/竞对数据，并通过 Internal API 回写主系统。采集服务不直接连接主数据库，不决定租户归属。

## 2. 服务边界

| 职责 | 归属 |
|---|---|
| 聚合关键词、创建 collection_tasks | 主系统。 |
| claim/heartbeat/submit_result | 主系统 Internal API + 采集服务。 |
| 数据源凭证解密 | 主系统提供短期可用凭证，或采集服务内存解密；禁止本地落盘。 |
| 调用外部数据源 | 采集服务。 |
| L1 同批去重 | 采集服务。 |
| L2 权威去重与租户关联 | 主系统。 |
| 评分 | 主系统 scoring service。 |

## 3. 任务模型

任务按以下 key 聚合：

```text
(keyword_normalized, countries_hash, source_types_hash)
```

`collection_tasks` 必须包含 lease 字段：

- `lease_id`
- `lease_owner`
- `lease_expires_at`
- `attempt_count`
- `max_attempts`

`collection_task_keywords` 关联任务与租户关键词。采集结果回写时只传 `task_id`，主系统从该表反查租户。

## 4. Claim / Heartbeat / Submit 协议

### Claim

```http
POST /internal/api/v1/collection/tasks/claim
```

请求：

```json
{ "service_instance": "collection-sh-01", "limit": 5, "lease_seconds": 300 }
```

响应：

```json
{
  "data": {
    "lease_id": "...",
    "tasks": [
      {
        "id": "...",
        "keyword": "multilayer pcb",
        "countries": ["DE"],
        "source_types": ["waimao_tong", "tengdao"]
      }
    ]
  }
}
```

### Heartbeat

```http
POST /internal/api/v1/collection/tasks/{id}/heartbeat
```

必须带 `lease_id`。lease 失效返回 409，采集服务必须停止回写。

### Submit result

```http
POST /internal/api/v1/collection/tasks/{id}/submit-result
```

主系统在同一事务内：

1. 校验 lease。
2. upsert companies / contacts / competitors。
3. 写 tenant_companies。
4. 标记任务完成或失败。
5. 释放 lease。

## 5. 数据源适配器

统一接口：

```python
class DataSourceAdapter:
    async def search_companies(keyword: str, countries: list[str] | None, page: int, page_size: int): ...
    async def get_company_detail(source_id: str): ...
    async def get_company_contacts(source_id: str): ...
```

励销云额外：

```python
async def search_competitors(keyword: str, page: int, page_size: int): ...
```

## 6. 两条采集路径

### 直接采集

```text
keyword + countries -> waimao_tong/tengdao -> companies -> batch-upsert
```

### 竞对反查

```text
keyword -> lixiaoyun competitors -> competitor_companies
        -> competitor english name -> waimao_tong/tengdao precise companies
        -> companies(raw.is_precise_customer=true) -> batch-upsert
```

## 7. 去重

采集服务：同批 `(source_type, source_id)` 去重。

主系统：

1. `company_sources(source_type, source_id)` 命中则复用 company。
2. domain 命中则复用 company 并新增 source。
3. name_en trigram 相似度 >= 0.85 可复用，但需记录 match_reason。
4. 否则创建 shared_company。

## 8. 限流

默认：

| source_type | 限流 |
|---|---|
| waimao_tong | 15 RPM / account，页间 3-8 秒随机。 |
| tengdao | 待确认，默认 10 RPM / account。 |
| lixiaoyun | 待确认，默认 10 RPM / account。 |

限流配置来自 `data_sources.config` 与 `data_source_credentials.daily_quota`。

## 9. 错误处理

- 单数据源失败不应导致整个任务失败，除非所有启用数据源均失败。
- 429/403：标记账号错误计数，必要时暂停该账号。
- 401：触发凭证刷新或标记 credentials stale。
- lease expired：立即停止回写。
- submit 失败：可按 `X-Request-Id` 幂等重试。
