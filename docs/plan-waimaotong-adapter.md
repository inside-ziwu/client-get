# 外贸通 (WaiMaoTong) Adapter 实现规划 (v2)

**日期**: 2026-04-30
**状态**: 待实现
**优先级**: P0 — 当前 collect() 是 501 占位符，外贸通完全不可用

---

## 一、核心定位（先纠正）

外贸通是一条**独立的直接关键词搜索链路**，与 Lixiaoyun→Tendata 的竞对反查链路**没有任何耦合**。

```
关键词 → 外贸通 SEARCH（分页公司列表）
       ↓
       外贸通 DETAIL（每家公司详情：domain/industry/phone/...）
       ↓
       外贸通 CONTACT（每家公司联系人邮箱）
       ↓
       提交到主系统 submit_result → tenant_companies + shared_contacts
```

不参与 `buyer_lookup` 任务，不参与竞对反查路径。原始 repo 里的 `BASEINFO` 接口仅用于"采购商 ID 补全"（公司名→ID 反查），属于辅助能力，本次不做。

---

## 二、原始代码三个核心端点

### 2.1 SEARCH（关键词搜索）

```
POST https://waimao.office.163.com/globalSearch/api/globalSearch/v1/search

Body:
{
    "searchType": "product",
    "product": "<keyword>",
    "page": 1,
    "size": 100,
    "country": ["DE", "US"] | ["全球"],
    "hasEmail": true,         # 必须：只要有邮件的
    "hasCustomsData": true,   # 必须：只要有海关数据的
    "hasDomain": true,        # 必须：只要有域名的
    "allMatchQuery": false,
    "filterCustomer": false,
    "filterEdm": false,
    "sortField": "default",
    "version": 1,
    ...其他默认参数
}
```

**响应路径**：`data.pageableResult.data[]` 公司列表，`data.pageableResult.total` 总数

**单条公司字段**：
```
id          → 公司 ID（外贸通主键，可能等于 domain）
name        → 公司全名
recommendShowName → 备用名
domain      → 域名
country     → 国家代码
tags / tagList / sourceTags → 标签列表
realId      → 真实 ID（用于补全 sys_company_id）
```

### 2.2 DETAIL（公司详情）

```
GET /globalSearch/api/globalSearch/v1/detail/new?id=<id>&product=&version=1
```

**响应路径**：`data` 对象，包含 `domain`, `phone`, `industry`, `employeeSize`, `foundedYear`, `productList[]`, `overviewDescription`, `address`/`location`

### 2.3 CONTACT（联系人）

```
POST /globalSearch/api/globalSearch/getContactPage

Body: {"id": "<company_id>", "page": 1, "size": 100, "isHidden": false}
```

**响应路径**：`data.content[]` 或 `data.list[]`

**联系人字段**：
```
id            → 联系人 ID
name          → 姓名
position      → 职位
emails[].address → 邮箱列表（取第一个）
```

### 2.4 认证与签名

- **Cookie**: `QIYE_TOKEN=...; QIYE_SESS=...; _deviceId=...; qiye_uid=...`
- **签名**: 每个请求附带 `sign + timestamp` 查询参数
  ```
  sign_str = secret_key
           + "".join(f"{k}={v}" for k, v in sorted(params.items()) if v not in (None, ""))
           + secret_key
  sign = MD5(sign_str).upper()
  ```
- **公共查询参数**（每个请求都附加）：`_host, _device=chrome, _system=web, _appName=sirius-web-waimao, _version=1.361.4, _deviceId`
- **失效检测**: HTTP 401 → 凭证过期；403/429 → 限流

### 2.5 限流规格

| 项 | 值 |
|---|---|
| API 调用上限 | 15 RPM/账号 |
| 页间延迟 | 3-8 秒随机 |
| 限流响应 | HTTP 403/429 或 code 字段 = "403"/"429" |

---

## 三、新项目接入方式（关键设计）

### 3.1 任务流（无需改调度器）

现有 `CollectionSchedulerService.schedule_due_tasks()` 已经按 `collection_keywords.source_types` 分组创建任务。当租户在关键词配置中勾选 `waimao_tong`，调度器会自动把 `waimao_tong` 加入 `task.source_types`。

现有 `CollectionProviderRouter.collect(task)` 已经对每个 source_type 独立调用 provider：

```python
for source_type in task.source_types:
    provider = self.providers.get(source_type)
    result = await provider.collect(task)
    payload.companies.extend(result.companies)
    payload.contacts.extend(result.contacts)
```

**结论**：调度器和路由器都不用改，**只需把 `WaiMaoTongCollectionProvider.collect()` 写满**，外贸通就能跑通。

### 3.2 task_type 复用

外贸通响应 `task_type=competitor_search`（命名不准确但功能 OK），把 `task.keyword` 和 `task.countries` 用作 SEARCH 输入。

完成后由于 `payload.competitors=[]`，主系统的 `submit_result()` **不会**自动创建 buyer_lookup 任务（看 `collection_service.py` 的逻辑：`if task_type=='competitor_search' and competitors`），所以外贸通跑完不会触发腾道反查。这是我们要的——两条链路互不干扰。

### 3.3 数据形态映射

| 外贸通字段 | CollectionPayload 字段 |
|---|---|
| `company.id` | `source_id`（必填，无则降级用 `domain`，再无则跳过） |
| `company.name` / `recommendShowName` | `name` |
| `company.name` | `name_en`（外贸通本身就是英文公司名） |
| `company.country` | `country` |
| `company.domain` | `website` (拼 `https://`) |
| `detail.industry` | `industry` |
| `<整个 search+detail 响应>` | `raw_data`（保留原始数据用于追溯） |

```python
# Contacts
{
    "source_type": "waimao_tong",
    "source_contact_id": contact["id"],
    "company_source_type": "waimao_tong",
    "company_source_id": <company.id>,
    "name": contact["name"],
    "email": contact["emails"][0]["address"],
    "title": contact["position"],
    "raw_data": <整个 contact 响应>
}
```

---

## 四、实现任务拆解

### 凭证侧（主系统后端）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| C1 | 新增 Internal API `GET /internal/collection/credentials/{source_type}` | `app/api/internal/collection.py` | 返回该 source_type 下 active 的凭证列表，scope=`collection:read` |
| C2 | 确认 `data_source_credentials` 表能存 cookie + secret_key + device_id；不够则加字段或用 JSONB `raw_config` | `alembic/versions/` | secret_key 和 device_id 各自独立字段更清晰 |
| C3 | Admin 端凭证录入界面（如已存在则只确认外贸通可填这三个值） | 前端 + admin API | 已经有数据源配置页，确认字段就行 |

### Provider 侧（采集服务）

| # | 任务 | 文件 | 说明 |
|---|---|---|---|
| P1 | 实现 MD5 签名 `_generate_sign()` | `waimaotong.py` | 移植原始 `generate_sign`，纯函数 |
| P2 | 实现异步令牌桶 `AsyncTokenBucket(rpm=15)` | `waimaotong.py` 或 `_rate_limit.py` | 替代原始 `deque + 线程锁` |
| P3 | 实现 `_signed_request()` async | `waimaotong.py` | httpx.AsyncClient + 限流 + 签名注入 + 重试 |
| P4 | 实现 `_search_companies(keyword, countries, page)` | `waimaotong.py` | 包装 SEARCH，返回 `(companies[], total)` |
| P5 | 实现 `_get_company_detail(company_id)` | `waimaotong.py` | 包装 DETAIL |
| P6 | 实现 `_get_contacts(company_id)` | `waimaotong.py` | 包装 CONTACT |
| P7 | 实现 `WaiMaoTongCollectionProvider.collect(task)` 主流程 | `waimaotong.py` | 见下文 |
| P8 | 修改 `CollectionProviderRouter.__init__` 给外贸通传入凭证 | `router.py` | 一行改动 |
| P9 | Worker 启动时拉取并定期刷新外贸通凭证 | `run_collection_worker.py` | 启动时 + 每 30 分钟 |

### collect() 主流程伪代码

```python
async def collect(self, task: CollectionTask) -> CollectionPayload:
    if not self._credentials:
        raise AppError(code="NO_CREDENTIAL", ...)

    payload = CollectionPayload()
    seen_ids: set[str] = set()      # L1 去重
    companies_to_enrich: list[dict] = []

    # Phase 1: 分页 SEARCH
    page = 1
    while True:
        if page > MAX_PAGES_PER_TASK:           # 配额上限
            break

        await self._rate_limiter.acquire()
        resp = await self._search_companies(
            keyword=task.keyword,
            countries=task.countries or ["全球"],
            page=page,
            page_size=100,
        )

        if self._is_credential_error(resp):
            raise AppError(code="CREDENTIAL_EXPIRED", ...)
        if self._is_rate_limited(resp):
            raise AppError(code="RATE_LIMITED", ...)

        items = resp["data"]["pageableResult"]["data"]
        if not items:
            break

        for item in items:
            cid = str(item.get("id") or item.get("domain") or "").strip()
            if not cid or cid in seen_ids:
                continue
            seen_ids.add(cid)
            companies_to_enrich.append(item)

        total = resp["data"]["pageableResult"].get("total", 0)
        if total and page * 100 >= total:
            break

        page += 1
        await asyncio.sleep(random.uniform(3, 8))     # 页间延迟

    # Phase 2: 对每家公司 DETAIL + CONTACT 富集
    for item in companies_to_enrich:
        cid = str(item.get("id") or item.get("domain"))

        await self._rate_limiter.acquire()
        detail = await self._get_company_detail(cid)
        await self._rate_limiter.acquire()
        contacts_resp = await self._get_contacts(cid)

        # 合并 search + detail → company payload
        company = self._build_company(item, detail)
        payload.companies.append(company)

        # 解析 contacts → contact payload
        for contact in self._extract_contacts(contacts_resp):
            mapped = self._build_contact(cid, contact)
            if mapped:
                payload.contacts.append(mapped)

    return payload
```

### 错误处理策略

| 错误 | 行为 |
|---|---|
| `NO_CREDENTIAL` | 抛 → Worker `mark_failed(retryable=False)` |
| HTTP 401 | 抛 `CREDENTIAL_EXPIRED` → 主系统通知管理员 |
| HTTP 403/429 或 code=429 | 抛 `RATE_LIMITED` → Worker `mark_failed(retryable=True)`，下次 claim 重试 |
| HTTP 5xx / 超时 | 指数退避重试 3 次（3s/9s/27s），仍失败按 5xx 抛错 |
| 单个公司 DETAIL/CONTACT 失败 | 跳过该公司富集，保留 search 阶段的基本信息 |
| 公司无 ID 又无 domain | 跳过该公司不入库 |
| 联系人无邮箱 | 跳过该联系人 |

---

## 五、不在本次范围

| 项 | 原因 |
|---|---|
| `BASEINFO` 接口（采购商 ID 补全） | 主流程不依赖；未来如果出现「外部公司名→外贸通补全 ID」场景再加 |
| 浏览器自动刷新 Cookie（原始 repo 用 Playwright） | 改为通过 Admin 手动录入；主系统通过 `CREDENTIAL_EXPIRED` 通知触达管理员 |
| 多账号轮换 | Phase 1 单账号；后续按需扩展 `AccountRotator` |
| 关键词级别的 daily_limit / 进度持久化 | 原始 repo 在 `keyword_list` 表上做了进度跟踪；新项目用 task lease 已经够，配额由 RPM 限流兜底 |
| LLM 评分 (Flow 02 后半段) | 评分留在主系统的 `scoring_service`，本次不动 |

---

## 六、验收标准

1. 租户在 keyword 配置勾选 `waimao_tong` → 调度器创建 task → Worker 路由到 `WaiMaoTongCollectionProvider`
2. `collect()` 对单个关键词的 task 返回非空 `CollectionPayload(companies=[...], contacts=[...])`
3. 60 秒内 API 调用次数不超过 15 次
4. 提交到主系统后，`shared_companies` 出现 source_type='waimao_tong' 的记录，`tenant_companies` 出现关联记录
5. 凭证失效时，管理员收到站内通知，任务标记 failed
6. 单测覆盖：签名生成、限流器、payload 映射、错误处理路径

---

## 七、实施顺序建议

1. **C1 + C2 + C3**：先把凭证通道打通（约半天），可以 mock 凭证给 Provider 跑
2. **P1 + P2**：签名 + 限流（纯函数，单测先行）
3. **P3**：HTTP 客户端
4. **P4 → P5 → P6**：三个端点逐个包装，每个都用 fixture 写单测
5. **P7**：collect() 主流程组装
6. **P8 + P9**：接入 router + worker
7. 联调：用真实凭证跑一个真实关键词，验证端到端

总工作量：人工 2-3 天，AI 辅助 1-2 小时。

---

## 八、关键风险

| 风险 | 缓解 |
|---|---|
| 签名算法服务端有变更 | 单测覆盖签名计算；联调时如失败立即对照原始 repo 排查 |
| Cookie session 频繁过期 | `CREDENTIAL_EXPIRED` 快速通知；后续支持多账号 |
| SEARCH 单关键词命中过多导致超时 | `MAX_PAGES_PER_TASK` 限制（建议 10 页 = 1000 公司） |
| DETAIL/CONTACT 占用大量 RPM 配额 | 每个公司至少 3 次调用（search+detail+contact），1000 公司=3000 次 ÷ 15 RPM ≈ 200 分钟。需要在 task lease 设计上确保心跳能撑住，或者拆分为多个小 task |
