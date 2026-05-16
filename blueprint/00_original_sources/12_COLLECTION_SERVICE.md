# 12 采集服务独立部署架构

> **版本**: v1.0
> **日期**: 2026-04-17
> **输入文档**: `03_WORKFLOW_ENGINE.md`, `05_EXTERNAL_INTEGRATIONS.md`, `07_REQUIREMENTS_SPEC.md`（§0.4, 后台任务A）, `09_DATABASE_DESIGN.md`（§8 系统支撑层）, `10_API_DESIGN.md`（§7 Internal API）
> **目标读者**: AI Agent（解析部署架构）+ 后端工程师（实现采集服务）

---

## 目录

1. [架构概述](#1-架构概述)
2. [部署架构](#2-部署架构)
3. [数据源适配器](#3-数据源适配器)
4. [采集路径](#4-采集路径)
5. [任务调度与执行](#5-任务调度与执行)
6. [去重与合并策略](#6-去重与合并策略)
7. [多租户关键词汇总](#7-多租户关键词汇总)
8. [限流与账号管理](#8-限流与账号管理)
9. [错误处理与降级](#9-错误处理与降级)
10. [与主系统通信协议](#10-与主系统通信协议)
11. [监控与可观测性](#11-监控与可观测性)

---

## 1. 架构概述

### 1.1 设计原则

采集服务独立于主系统部署（见 `07_REQUIREMENTS_SPEC.md` §0.4），核心原则：

| 原则 | 说明 |
|------|------|
| **独立部署** | 单独服务器，独立进程，独立扩缩容 |
| **API 通信** | 不引入消息队列，通过 Internal API 调用主系统（见 `10_API_DESIGN.md` §7） |
| **共享采集** | 同一关键词多租户订阅时只采集一次，结果关联所有相关租户 |
| **数据源可插拔** | 适配器模式，新增数据源不改核心逻辑 |

### 1.2 系统边界

```
┌─────────────────────────────────────────┐
│              采集服务（独立部署）              │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │外贸通    │  │腾道     │  │励销云    │ │
│  │Adapter  │  │Adapter  │  │Adapter  │ │
│  │ (A01)   │  │ (B01)   │  │ (C01)   │ │
│  └────┬────┘  └────┬────┘  └────┬────┘ │
│       └──────┬─────┴──────┬─────┘       │
│              ▼            ▼             │
│       ┌────────────┐ ┌──────────┐       │
│       │ 去重/合并   │ │ 竞对反查  │       │
│       │  Pipeline  │ │ Pipeline │       │
│       └─────┬──────┘ └────┬─────┘       │
│             └──────┬──────┘             │
│                    ▼                    │
│          ┌──────────────────┐           │
│          │  Internal API    │           │
│          │  Client          │           │
│          └────────┬─────────┘           │
└───────────────────┼─────────────────────┘
                    │ HTTP (Internal API)
                    ▼
┌───────────────────────────────────────────┐
│              主系统                         │
│  /internal/api/v1/collection/*            │
│  → shared_companies / company_sources     │
│  → tenant_companies / competitor_companies│
└───────────────────────────────────────────┘
```

---

## 2. 部署架构

### 2.1 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 运行时 | Python 3.11+ | 与主系统一致 |
| 任务调度 | Prefect 3.x | 保留现有 Flow 模式，改造为多租户 |
| HTTP 客户端 | httpx (async) | 调用数据源 API + Internal API |
| 配置管理 | 环境变量 + 启动时从主系统拉取 | 凭证不本地存储 |

### 2.2 部署拓扑

```
┌──────────────────────────────────────┐
│ 采集服务器 (Collection Server)         │
│                                      │
│  ┌──────────────┐  ┌──────────────┐  │
│  │   Scheduler  │  │  Prefect     │  │
│  │  (cron/循环)  │  │  Worker      │  │
│  └──────┬───────┘  └──────┬───────┘  │
│         │                 │          │
│         └────────┬────────┘          │
│                  ▼                   │
│         ┌──────────────┐             │
│         │  Task Queue  │             │
│         │  (内存队列)   │             │
│         └──────────────┘             │
└──────────────────────────────────────┘
         │                    ▲
         │ HTTP               │ HTTP
         ▼                    │
┌──────────────────────────────────────┐
│         主系统 Internal API            │
└──────────────────────────────────────┘
```

### 2.3 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `MAIN_API_URL` | 主系统 Internal API 地址 | `http://10.0.1.10:8000/internal/api/v1` |
| `INTERNAL_API_KEY` | Internal API 认证密钥 | `sk-internal-xxx` |
| `PREFECT_API_URL` | Prefect Server 地址（如使用） | `http://10.0.1.10:4200/api` |
| `MAX_CONCURRENT_TASKS` | 最大并发采集任务数 | `5` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## 3. 数据源适配器

### 3.1 适配器接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class CollectedCompany:
    """采集到的原始公司数据"""
    source_type: str          # 'waimao_tong' | 'tengdao' | 'lixiaoyun'
    source_id: str            # 数据源内的公司唯一 ID
    name: str
    name_en: str | None
    country: str | None
    website: str | None
    industry: str | None
    employee_count: str | None
    raw_data: dict            # 原始 API 返回

@dataclass
class CollectedContact:
    """采集到的原始联系人数据"""
    source_type: str
    source_contact_id: str
    company_source_id: str    # 关联公司的 source_id
    name: str
    email: str | None
    title: str | None
    department: str | None
    phone: str | None
    linkedin_url: str | None
    raw_data: dict

class DataSourceAdapter(ABC):
    """数据源适配器基类"""

    @abstractmethod
    async def search_companies(
        self, keyword: str, countries: list[str] | None,
        page: int, page_size: int
    ) -> tuple[list[CollectedCompany], int]:
        """搜索公司，返回 (公司列表, 总页数)"""
        ...

    @abstractmethod
    async def get_company_contacts(
        self, source_id: str
    ) -> list[CollectedContact]:
        """获取公司联系人"""
        ...

    @abstractmethod
    async def get_company_detail(
        self, source_id: str
    ) -> CollectedCompany:
        """获取公司详情（富集）"""
        ...
```

### 3.2 外贸通适配器 (A01)

继承现有 `flows/utils/netease_api.py` 逻辑，改造要点：

| 现有实现 | 改造后 |
|---------|--------|
| Cookie 硬编码在 `system_config` | 启动时从主系统 `GET /collection/credentials/waimao_tong` 拉取 |
| 单账号 | 支持多账号轮换（见 §8） |
| 同步调用 | async httpx |
| 15 RPM 全局限流（deque） | 按账号独立限流（见 §8.2） |

```python
class WaimaoTongAdapter(DataSourceAdapter):
    SOURCE_TYPE = "waimao_tong"
    BASE_URL = "https://waimao.office.163.com"

    ENDPOINTS = {
        "search": "/openapi/search/company/search",
        "detail": "/openapi/search/company/detail",
        "contact": "/openapi/search/company/contact",
        "base_info": "/openapi/search/company/baseInfo",
    }

    async def search_companies(self, keyword, countries, page, page_size):
        await self.rate_limiter.acquire()
        resp = await self._signed_request("search", {
            "keyword": keyword,
            "page": page,
            "pageSize": page_size,
            **({"country": countries} if countries else {}),
        })
        companies = [self._parse_company(item) for item in resp.get("list", [])]
        total_pages = resp.get("totalPage", 0)
        return companies, total_pages
```

### 3.3 腾道适配器 (B01)

> 待集成。接口结构待确认，遵循相同适配器模式。

```python
class TengdaoAdapter(DataSourceAdapter):
    SOURCE_TYPE = "tengdao"
    # TODO: 待腾道 API 文档确认后实现
```

### 3.4 励销云适配器 (C01)

> 特殊：励销云搜索的是**中国同行公司**（competitor），非直接目标客户。

```python
class LixiaoyunAdapter(DataSourceAdapter):
    SOURCE_TYPE = "lixiaoyun"

    async def search_competitors(
        self, keyword: str, page: int, page_size: int
    ) -> tuple[list[CollectedCompany], int]:
        """搜索中国同行公司 → 写入 competitor_companies"""
        ...

    async def search_companies(self, keyword, countries, page, page_size):
        # 励销云不直接搜索海外公司，此方法不适用
        raise NotImplementedError("励销云通过竞对反查路径获取海外公司")
```

---

## 4. 采集路径

### 4.1 路径一：直接采集（外贸通 + 腾道）

```
关键词 → 外贸通 Search API → CollectedCompany[]
       → 腾道 Search API   → CollectedCompany[]
       ↓
    合并去重 (§6)
       ↓
    POST /internal/api/v1/collection/companies/batch-upsert
       ↓
    富集：对 A/B 级公司（评分后）
       → 外贸通 Detail API → 补充公司详情
       → 外贸通 Contact API → CollectedContact[]
       → POST /internal/api/v1/collection/contacts/batch-upsert
```

### 4.2 路径二：竞对反查（励销云 → 外贸通/腾道）

```
关键词 → 励销云 Search → 中国同行公司[]
       ↓
    POST /internal/api/v1/collection/competitors/batch-upsert
       ↓
    提取同行英文公司名
       ↓
    外贸通 Search(company_name_en) → CollectedCompany[]（标记"精准客户"）
    腾道 Search(company_name_en)   → CollectedCompany[]（标记"精准客户"）
       ↓
    合并去重 (§6)
       ↓
    POST /internal/api/v1/collection/companies/batch-upsert
    （raw_data 中标记 is_precise_customer = true → 评分时直接 S 级）
```

### 4.3 路径选择逻辑

```python
async def execute_keyword_task(task: dict):
    keyword = task["keyword"]
    countries = task.get("countries")
    source_types = task["source_types"]
    task_id = task["id"]
    keyword_ids = task["keyword_ids"]
    results: list[CollectedCompany] = []

    # 路径一：直接采集
    if "waimao_tong" in source_types:
        adapter = get_adapter("waimao_tong")
        companies, _ = await adapter.search_companies(keyword, countries, page=1, page_size=100)
        results.extend(companies)

    if "tengdao" in source_types:
        adapter = get_adapter("tengdao")
        companies, _ = await adapter.search_companies(keyword, countries, page=1, page_size=100)
        results.extend(companies)

    # 路径二：竞对反查
    if "lixiaoyun" in source_types:
        lxy = get_adapter("lixiaoyun")
        competitors, _ = await lxy.search_competitors(keyword, page=1, page_size=100)

        # 提交竞品公司
        await internal_client.batch_upsert_competitors(competitors)

        # 反查：用同行英文名去外贸通/腾道搜索
        for comp in competitors:
            if comp.name_en:
                if "waimao_tong" in source_types:
                    precise, _ = await get_adapter("waimao_tong").search_companies(
                        comp.name_en, countries=None, page=1, page_size=20)
                    for p in precise:
                        p.raw_data["is_precise_customer"] = True
                        p.raw_data["competitor_source_id"] = comp.source_id
                    results.extend(precise)

    # 去重 + 提交
    deduplicated = deduplicate_companies(results)  # §6
    await internal_client.batch_upsert_companies(
        deduplicated,
        task_id=task_id,
        keyword_ids=keyword_ids,
    )
```

---

## 5. 任务调度与执行

### 5.1 调度模型

改造现有 `scheduler.py`（30 秒循环）为采集服务专用调度器：

```python
class CollectionScheduler:
    """采集服务调度器"""

    def __init__(self, internal_client: InternalAPIClient):
        self.client = internal_client
        self.max_concurrent = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))

    async def run_loop(self):
        """主循环：每 60 秒拉取待执行任务"""
        while True:
            try:
                claim = await self.client.claim_tasks(
                    service_instance=os.getenv("SERVICE_INSTANCE_ID", "collection-local"),
                    limit=self.max_concurrent * 2,
                    lease_seconds=300,
                )
                lease_id = claim["lease_id"]
                tasks = claim["tasks"]
                # 按优先级排序
                tasks.sort(key=lambda t: t["priority"], reverse=True)

                # 并发执行（限制并发数）
                semaphore = asyncio.Semaphore(self.max_concurrent)
                await asyncio.gather(*[
                    self._execute_with_semaphore(semaphore, task, lease_id)
                    for task in tasks
                ])
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

            await asyncio.sleep(60)

    async def _execute_with_semaphore(self, sem, task, lease_id: str):
        async with sem:
            await self._execute_task(task, lease_id)

    async def _execute_task(self, task: dict, lease_id: str):
        task_id = task["id"]
        heartbeat = None
        try:
            heartbeat = asyncio.create_task(
                self._heartbeat_loop(task_id=task_id, lease_id=lease_id, interval_seconds=60)
            )
            await execute_keyword_task(task)
            await self.client.submit_task_result(
                task_id,
                {"status": "completed", "lease_id": lease_id}
            )
        except Exception as e:
            await self.client.submit_task_result(
                task_id,
                {"status": "failed", "lease_id": lease_id, "error_message": str(e)}
            )
        finally:
            if heartbeat:
                heartbeat.cancel()

    async def _heartbeat_loop(self, task_id: str, lease_id: str, interval_seconds: int):
        while True:
            await asyncio.sleep(interval_seconds)
            await self.client.heartbeat_task(task_id=task_id, lease_id=lease_id)
```

### 5.2 Prefect Flow 改造

现有 4 个 Flow 中，采集服务负责 **Flow 01**（关键词采集）和 **Flow 02 的富集部分**（公司详情 + 联系人获取）。

| 现有 Flow | 归属 | 改造 |
|-----------|------|------|
| Flow 01 keyword_collect | 采集服务 | 改为多数据源 + 多租户关键词汇总 |
| Flow 02 company_analysis（富集） | 采集服务 | 公司详情 + 联系人获取（独立于 LLM 评分） |
| Flow 02 company_analysis（评分） | 主系统 | 评分逻辑留在主系统（依赖评分模板 + LLM） |
| Flow 03 email_draft | 主系统 | 不变 |
| Flow 04 email_send | 主系统 | 不变 |

### 5.3 任务生命周期

```
pending → running → completed
                  → failed → pending (自动重试，max 3 次)
                  → cancelled (手动取消)
```

对应 `collection_tasks` 表状态字段（见 `09_DATABASE_DESIGN.md` §8）。

---

## 6. 去重与合并策略

### 6.1 去重规则

采集服务在提交数据前进行本地去重，主系统在 `batch-upsert` 时再做权威去重。

**两级去重**：

| 级别 | 位置 | 去重键 | 说明 |
|------|------|--------|------|
| L1 本地去重 | 采集服务内存 | `(source_type, source_id)` | 同批次内去重 |
| L2 权威去重 | 主系统 `batch-upsert` | `company_sources(source_type, source_id)` UNIQUE | 跨批次去重，由 DB 保证 |

### 6.2 跨数据源去重

同一公司可能在不同数据源有不同 ID。主系统通过以下策略关联：

| 优先级 | 匹配规则 | 说明 |
|--------|---------|------|
| 1 | `domain` 完全匹配 | 最可靠（同域名 = 同公司） |
| 2 | `name_en` 相似度 ≥ 0.85（trigram） | 辅助判断 |
| 3 | 不匹配 → 创建新记录 | 宁可多不可漏 |

> 跨数据源去重在主系统 `batch-upsert` 处理逻辑中实现（见 `10_API_DESIGN.md` §7.1）。采集服务只做 L1 级同源去重。

### 6.3 合并策略

已存在的公司（L2 命中）执行合并更新：

```python
def merge_company(existing: dict, incoming: CollectedCompany) -> dict:
    """合并策略：新数据补全空字段，不覆盖已有值"""
    merged = {**existing}
    for field in ["country", "website", "industry", "employee_count"]:
        if not merged.get(field) and getattr(incoming, field):
            merged[field] = getattr(incoming, field)

    # raw_data 深度合并（按 source_type 命名空间）
    raw = merged.get("raw_data", {})
    raw[incoming.source_type] = incoming.raw_data
    merged["raw_data"] = raw

    return merged
```

---

## 7. 多租户关键词汇总

### 7.1 汇总逻辑

> 见 `07_REQUIREMENTS_SPEC.md` 后台任务A-A1：同一关键词被多个租户配置时只采集一次，结果关联所有相关租户。

```python
async def aggregate_keywords() -> list[AggregatedKeyword]:
    """
    从主系统拉取所有租户的关键词，按 (keyword, countries) 去重，
    合并关联的 tenant_ids。
    """
    all_keywords = await internal_client.list_schedulable_keywords()

    # 按 (keyword_normalized, countries_hash) 分组
    groups: dict[str, AggregatedKeyword] = {}
    for kw in all_keywords:
        key = f"{kw['keyword'].strip().lower()}::{hash(tuple(sorted(kw.get('countries', []))))}"
        if key not in groups:
            groups[key] = AggregatedKeyword(
                keyword=kw["keyword"],
                countries=kw.get("countries"),
                source_types=set(),
                tenant_ids=set(),
                keyword_ids=[],
            )
        groups[key].tenant_ids.add(kw["tenant_id"])
        groups[key].source_types.update(kw.get("source_types", []))
        groups[key].keyword_ids.append(kw["id"])

    return list(groups.values())
```

### 7.2 结果关联

采集结果通过 `task_id + keyword_ids` 关联到所有相关租户；主系统根据本地任务和关键词归属重新解析允许写入的 `tenant_ids`：

```json
{
  "companies": [...],
  "task_id": "018f...",
  "keyword_ids": ["keyword-A-id", "keyword-B-id", "keyword-C-id"]
}
```

主系统为解析出的每个 `tenant_id` 创建 `tenant_companies` 记录（排除黑名单和竞品）。

### 7.3 lease 契约

采集服务必须把 lease 当成执行资格控制，而不是普通返回字段：

1. `claim_tasks()` 返回的 `lease_id` 绑定本次领取到的全部任务。
2. 长任务必须定期调用 `/collection/tasks/{id}/heartbeat` 续租；建议 60 秒一次，每次续租 300 秒。
3. 若主系统返回 `409 lease_expired`，当前实例必须停止回写并放弃该任务，等待重新 claim。
4. `submit_task_result()` 是最终确认接口；主系统应在同一事务内落结果、终结状态并释放 lease。

### 7.4 计费

> 每个租户独立计费，即使数据源侧只采集一次。

采集费用不计入 AI 消费余额（见 `07_REQUIREMENTS_SPEC.md` 后台任务A），由平台运营侧独立核算。

---

## 8. 限流与账号管理

### 8.1 数据源限流

| 数据源 | 限流策略 | 值 |
|--------|---------|-----|
| 外贸通 (A01) | RPM（每分钟请求数） | 15 RPM / 账号 |
| 外贸通 (A01) | 页间间隔 | 3-8 秒随机 |
| 腾道 (B01) | 待确认 | 待确认 |
| 励销云 (C01) | 待确认 | 待确认 |
| Internal API | 无严格限流 | 1000 req/min（见 `10_API_DESIGN.md` §9） |

### 8.2 账号轮换

支持每个数据源配置多个账号，轮换使用以提高吞吐：

```python
class AccountRotator:
    """数据源账号轮换器"""

    def __init__(self, credentials: list[dict]):
        self.accounts = credentials
        self.current_index = 0
        self.rate_limiters: dict[str, RateLimiter] = {
            cred["id"]: RateLimiter(rpm=cred.get("rpm_limit", 15))
            for cred in credentials
        }

    async def get_available_account(self) -> dict:
        """获取下一个可用账号（令牌桶未满的）"""
        for _ in range(len(self.accounts)):
            account = self.accounts[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.accounts)
            limiter = self.rate_limiters[account["id"]]
            if await limiter.try_acquire():
                return account
        # 所有账号都达到限流，等待
        await asyncio.sleep(1)
        return await self.get_available_account()
```

### 8.3 凭证获取

采集服务**不本地存储凭证**，每次启动和定期刷新时从主系统拉取：

```python
async def refresh_credentials(source_type: str) -> list[dict]:
    """从主系统获取数据源凭证"""
    resp = await internal_client.get(
        f"/collection/credentials/{source_type}"
    )
    return resp["credentials"]
```

对应 `10_API_DESIGN.md` §7.2 `GET /collection/credentials/{source_type}` 端点。

---

## 9. 错误处理与降级

### 9.1 重试策略

| 错误类型 | 重试次数 | 退避策略 | 说明 |
|---------|---------|---------|------|
| 网络超时 / 连接失败 | 3 次 | 指数退避（3s, 9s, 27s） | 临时网络问题 |
| HTTP 429 (Rate Limit) | 不重试 | 等到限流窗口重置 | 由 RateLimiter 控制 |
| HTTP 401 (认证失败) | 1 次 | 刷新凭证后重试 | Cookie/Token 过期 |
| HTTP 403 (禁止) | 0 次 | 标记账号异常，切换账号 | 可能被封 |
| HTTP 5xx | 2 次 | 固定间隔 5s | 数据源服务端问题 |
| Internal API 失败 | 3 次 | 指数退避（1s, 2s, 4s） | 主系统不可达 |

### 9.2 错误隔离

```
单个关键词失败 → 不影响其他关键词（隔离）
单个数据源失败 → 其他数据源继续（降级）
单个账号被封   → 轮换到下一个账号
Internal API 不可达 → 本地缓存结果，恢复后重提交
```

### 9.3 本地缓存与重提交

当主系统 Internal API 不可达时，采集结果暂存本地：

```python
CACHE_DIR = Path("/tmp/collection_cache")

async def submit_with_fallback(data: dict):
    """提交采集结果，失败时缓存本地"""
    try:
        await internal_client.batch_upsert_companies(data)
    except (httpx.ConnectError, httpx.TimeoutException):
        cache_file = CACHE_DIR / f"{uuid4()}.json"
        cache_file.write_text(json.dumps(data))
        logger.warning(f"Internal API unreachable, cached to {cache_file}")

async def flush_cache():
    """定期检查并重提交缓存的数据"""
    for cache_file in sorted(CACHE_DIR.glob("*.json")):
        data = json.loads(cache_file.read_text())
        try:
            await internal_client.batch_upsert_companies(data)
            cache_file.unlink()
        except Exception:
            break  # 仍然不可达，停止重试
```

---

## 10. 与主系统通信协议

### 10.1 Internal API 端点汇总

完整定义见 `10_API_DESIGN.md` §7。采集服务使用的端点：

| 方向 | 端点 | 用途 |
|------|------|------|
| 采集→主系统 | `POST /collection/companies/batch-upsert` | 提交采集到的公司 |
| 采集→主系统 | `POST /collection/contacts/batch-upsert` | 提交采集到的联系人 |
| 采集→主系统 | `POST /collection/competitors/batch-upsert` | 提交竞品公司 |
| 采集→主系统 | `PATCH /collection/tasks/{id}/status` | 更新任务状态 |
| 采集→主系统 | `POST /collection/tasks/{id}/result` | 提交任务结果统计 |
| 采集→主系统 | `POST /collection/tasks/{id}/heartbeat` | 续租当前任务 |
| 主系统→采集 | `POST /collection/tasks/claim` | 原子领取待执行任务（返回 lease） |
| 主系统→采集 | `GET /collection/credentials/{source_type}` | 获取凭证 |

### 10.2 认证

```
Authorization: Bearer <service-token>
X-Service-Name: collection-service
X-Service-Instance: collection-sh-01
```

不走用户 JWT。服务间认证使用按服务签发的短期签名令牌（可叠加 mTLS），不同服务身份对应不同权限范围（见 `10_API_DESIGN.md` §7）。

采集服务只能以 `collection-service` 身份访问 `/collection/*`；不得复用评分或发送服务身份。

### 10.3 批量提交规范

| 参数 | 值 | 说明 |
|------|-----|------|
| 每批最大条数 | 100 | 超过则分批提交 |
| 超时时间 | 30s | 单次 HTTP 请求超时 |
| Content-Type | `application/json` | JSON 格式 |

---

## 11. 监控与可观测性

### 11.1 关键指标

| 指标 | 类型 | 告警阈值 |
|------|------|---------|
| `collection.tasks.completed` | Counter | - |
| `collection.tasks.failed` | Counter | > 10/hour |
| `collection.companies.collected` | Counter | - |
| `collection.api.latency_ms` | Histogram | P99 > 5000ms |
| `collection.api.errors` | Counter | > 50/hour |
| `collection.cache.pending_files` | Gauge | > 100 |
| `collection.rate_limit.waiting` | Gauge | > 0（预警） |

### 11.2 日志规范

```python
# 结构化日志
logger.info("company_collected",
    extra={
        "keyword": keyword,
        "source_type": "waimao_tong",
        "companies_count": len(companies),
        "tenant_ids": tenant_ids,
        "duration_ms": elapsed_ms,
    })
```

### 11.3 健康检查

```
GET /health → 200 {"status": "ok", "version": "1.0.0", "uptime_seconds": 12345}
```

主系统可定期检查采集服务健康状态。

---

> **文档结束**
> 下一步：`13_AI_INTEGRATION.md`（AI 集成方案）
